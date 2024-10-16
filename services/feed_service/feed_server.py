# feed_service.py
from flask import Flask, request, jsonify, abort
import os
import psycopg2
from psycopg2 import pool
from loguru import logger
import requests
import redis
import threading
from typing import List

app = Flask(__name__)

'''
feed service:
    Endpoints:
        - '/fetch_feed', methods=['GET']
        - '/submit_impression', methods=['POST']

'''


# Fetch database credentials from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'impressions_db')
DB_USER = os.getenv('DB_USER', 'your_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
PROFILE_SERVICE_URL = os.getenv('PROFILE_SERVICE_URL', 'http://profile_service:5002')
PORT = os.getenv('PORT', '5003')


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

#  a function that will always running as a seperate thread
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

# Example API Endpoint: Fetching posts from Score_table

def get_trending_users_gracefully(user_ids : List[str]) :
    global count, profile_service_status, cached_value
    
    trending_users = []
        
    if profile_service_status == "Unknown" or profile_service_status == "UP" or count == 2:
        try:
            # Try to fetch data for all user_ids from profile_service
            for user_id in user_ids:
                user_service_url = f'{PROFILE_SERVICE_URL}/get_user_info?user_id={user_id}'
                logger.info(f"Hitting profile_service for user_id: {user_id}")
                
                # Request user info from profile_service
                response = requests.get(user_service_url)
                response.raise_for_status()  # Will raise an exception for any error responses
                
                user_info = response.json()
                trending_users.append(user_info)
                
                # Cache the fetched user info
                cached_value[user_id] = user_info

            # Broadcast that profile_service is "UP" after successful fetch
            redis_client.publish('profile_service_status', 'UP')
            count = 0  # Reset count after successful hit
            
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to profile_service, broadcasting status as Down")
            
            # Broadcast that profile_service is "Down"
            redis_client.publish('profile_service_status', 'Down')
            count = 0  # Reset count
            # Return cached values if service is down
            trending_users = [cached_value.get(user_id) for user_id in user_ids if user_id in cached_value]
    
    else:
        # If profile_service is "Down", return cached values and increment the count
        logger.info(f"Returning cached values as profile_service is {profile_service_status}")
        trending_users = [cached_value.get(user_id) for user_id in user_ids if user_id in cached_value]
        count += 1

    return trending_users



@app.route('/fetch_feed', methods=['GET'])
def fetch_feed():
    logger.info(f"Got a new request to fetch_feed")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get N from query parameters, default to 10 if not provided
        N = 10
        logger.info(f"Fetching top {N} posts from Score_table")
        # Fetch top N post_ids from Score_table, ordered by score
        cur.execute('SELECT post_id FROM Score_table ORDER BY score DESC LIMIT %s', (N,))
        posts = cur.fetchall()

        top_posts = [{'post_id': post[0]} for post in posts]

        return jsonify({'top_posts': top_posts}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if conn:
            release_db_connection(conn)

# Example API Endpoint: Submitting impressions and updating Score_table
@app.route('/submit_impression', methods=['POST'])
def submit_impression():
    global cached_value
    logger.info(f"Got a new request to submit_impression")
    logger.info(f"message is {cached_value}")
    data = request.json
    post_id = data.get('post_id')
    user_id = data.get('user_id')
    impression_type = data.get('impression_type')

    if not post_id or not user_id or not impression_type:
        return jsonify({'error': 'post_id, user_id, and impression_type are required'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Start a transaction
        conn.autocommit = False
        logger.info('Starting transaction')
        logger.info(f"Hitting the database to update Score_table")
        # Insert into Impression_table
        cur.execute(
            'INSERT INTO Impression_table (post_id, user_id, impression_type, time_of_impression) '
            'VALUES (%s, %s, %s, NOW())',
            (post_id, user_id, impression_type)
        )

        # Update score in Score_table based on impression type
        if impression_type == 'UP':
            cur.execute('UPDATE Score_table SET score = score + 1 WHERE post_id = %s', (post_id,))
        elif impression_type == 'DOWN':
            cur.execute('UPDATE Score_table SET score = score - 1 WHERE post_id = %s', (post_id,))
        else:
            raise ValueError("Invalid impression_type. Must be 'UP' or 'DOWN'.")

        # Commit the transaction
        conn.commit()

        return jsonify({'message': 'Impression submitted successfully'}), 201

    except Exception as e:
        if conn:
            conn.rollback()  # Roll back the transaction if any error occurs
        return jsonify({'error': str(e)}), 500

    finally:
        if conn:
            release_db_connection(conn)

@app.route('/get_trending_user_info', methods=['GET'])
def get_trending_user_info():
    logger.info(f"Got a new request to get_trending_user_info")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get N from query parameters, default to 10 if not provided
        N = 10
        logger.info(f"Fetching top {N} posts from Score_table")

        # Step 1: Fetch top N post_ids from Score_table ordered by score
        cur.execute('SELECT post_id FROM Score_table ORDER BY score DESC LIMIT %s', (N,))
        top_posts = cur.fetchall()

        if not top_posts:
            return jsonify({'message': 'No trending posts found'}), 404

        # Step 2: Fetch user_ids corresponding to post_ids from Post_table
        post_ids = [post[0] for post in top_posts]
        cur.execute('SELECT user_id FROM Post_table WHERE post_id IN %s', (tuple(post_ids),))
        user_ids = cur.fetchall()
        user_ids=[user_id[0] for user_id in user_ids]
        logger.info(f"User ids {user_ids}")
        
        
        if not user_ids:
            return jsonify({'message': 'No users found for trending posts'}), 404
        
        # Step 3: Hit the user_service to get user info for each user_id
        trending_users=get_trending_users_gracefully(user_ids)
        # Step 4: Return the list of trending user info as JSON
        return jsonify({'trending_users': trending_users}), 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if conn:
            release_db_connection(conn)



# Start the Flask app
if __name__ == '__main__':
    
    listener_thread = threading.Thread(target=redis_listener)
    listener_thread.start()
    app.run(host='0.0.0.0', port=int(PORT))
