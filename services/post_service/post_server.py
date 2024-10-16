from flask import Flask, jsonify, request, abort
import psycopg2
from psycopg2 import pool
import os
import requests
from loguru import logger
from dotenv import load_dotenv
import redis
import requests
import threading


'''
    post_server
        API endpoints:
            - '/get_post_info', methods=['GET']
            - '/insert_post', methods=['POST']
'''


# Load environment variables from a .env file
# load_dotenv()

app = Flask(__name__)

# Fetch database credentials from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'impressions_db')
DB_USER = os.getenv('DB_USER', 'your_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
PROFILE_SERVICE_URL = os.getenv('PROFILE_SERVICE_URL', 'http://profile_service:5002')
PORT=os.getenv('PORT',"5001")


redis_client = redis.StrictRedis(host='redis_server', port=6379, db=0)
# Initial state variables
count = 0
profile_service_status = "Unknown"
cached_value = {}


# Subscribe to the profile_service_status channel
pubsub = redis_client.pubsub()
pubsub.subscribe('profile_service_status')

# Create a connection pool (minconn: minimum connections, maxconn: maximum connections)
connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

# Function to get a connection from the pool
def get_db_connection():
    try:
        # Get a connection from the pool
        conn = connection_pool.getconn()
        if conn:
            return conn
    except Exception as e:
        print(f"Error getting connection: {e}")
        abort(500)

# Function to release the connection back to the pool
def release_db_connection(conn):
    if conn:
        connection_pool.putconn(conn)


def redis_listener():
    logger.info("Starting Redis listener...")
    global profile_service_status,count
    for message in pubsub.listen():
        # Check if the message is from the 'profile_service_status' channel
        if message['type'] == 'message' and message['channel'] == b'profile_service_status':
            if message['data'].decode('utf-8') in ["UP","DOWN"]:
                profile_service_status=message['data'].decode('utf-8')
                count=0
                logger.info(f" profile_service_status: updated to {profile_service_status}")
        else:
            logger.info(f"Ignored message from channel: {message['channel']}")
    return


def get_user_info_gracefully(user_id : str):
    global count, profile_service_status, cached_value
    
    # Check service status or retry logic
    if profile_service_status == "Unknown" or profile_service_status == "UP" or count == 2:
        try:
            # Hit the profile_service to fetch user info
            logger.info(f"Hitting profile_service for user_id: {user_id}")
            user_response = requests.get(f'{PROFILE_SERVICE_URL}/get_user_info', params={'user_id': user_id})
            user_response.raise_for_status()  # Raise exception if the response is not 2xx

            user_info = user_response.json()
            # Cache the fetched user info
            cached_value[user_id] = user_info

            # Broadcast that profile_service is "UP" after successful fetch
            redis_client.publish('profile_service_status', 'UP')
            count = 0  # Reset the count

            return user_info

        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to profile_service for user_id: {user_id}, broadcasting status as Down")

            # Broadcast that profile_service is "Down"
            redis_client.publish('profile_service_status', 'Down')
            count = 0  # Reset the count
            # Return cached value if available
            return cached_value.get(user_id,"No Idea")

    else:
        # Return cached value if service is Down
        logger.info(f"Returning cached value as profile_service is {profile_service_status}")
        count += 1
        return cached_value.get(user_id,"No Idea")
    


# Route to get post info
@app.route('/get_post_info', methods=['GET'])
def get_post_info():
    logger.debug("Got a new request to get_post_info")
    post_id = request.args.get('post_id')
    
    if not post_id:
        return jsonify({'error': 'post_id is required'}), 400
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        logger.debug("Hitting the database to fetch post information")
        # Fetch post information from Post_table
        cur.execute('SELECT post_id, user_id, title, content FROM Post_table WHERE post_id = %s', (post_id,))
        post = cur.fetchone()
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_info = {
            'post_id': post[0],
            'title': post[2],
            'content': post[3]
        }
        
        user_id = post[1]
        
        logger.debug(f"Hitting the {PROFILE_SERVICE_URL} to fetch user information")
        # Fetch user information from profile service
        post_info['author']=get_user_info_gracefully(user_id)
        # Combine post and user info
        logger.debug(f"Combining post and user info")
        
        return jsonify(post_info), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

# Route to insert a new post
@app.route('/insert_post', methods=['POST'])
def insert_post():
    logger.debug("Got a new request to insert_post")
    data = request.json
    user_id = data.get('user_id')
    title=data.get('title')
    content = data.get('content')
    
    if not user_id or not content or not title:
        return jsonify({'error': 'user_id , title and content  are required'}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Start a transaction
        conn.autocommit = False
        logger.debug("Hitting the database to insert new post")
        # Insert new post into Post_table
        cur.execute(
            'INSERT INTO Post_table (user_id,title, content) VALUES (%s, %s,%s) RETURNING post_id',
            (user_id, title,content)
        )
        
        post_id = cur.fetchone()[0]
        
        # Insert the new post_id into Score_table with an initial score (e.g., score = 0)
        cur.execute(
            'INSERT INTO Score_table (post_id, last_updated) VALUES (%s, NOW())',
            (post_id,)  # Initialize score with 0
        )
        
        # Commit transaction
        conn.commit()
        
        return jsonify({'message': 'Post inserted successfully', 'post_id': post_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == '__main__':
    listener_thread = threading.Thread(target=redis_listener)
    listener_thread.start()
    print("Thread started on post_service")
    app.run(host='0.0.0.0', port=int(PORT))
