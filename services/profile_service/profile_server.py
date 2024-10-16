# profile_service.py

from flask import Flask, jsonify, request, abort
import psycopg2
from psycopg2 import pool
import os
import requests
from loguru import logger
from dotenv import load_dotenv


'''
    Profile_server
        API endpoints:
            - /get_user_info', methods=['GET']
            - '/insert_new_user', methods=['POST']
'''


# Load environment variables from a .env file
# load_dotenv()

app = Flask(__name__)

# Fetch database credentials from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'impressions_db')
DB_USER = os.getenv('DB_USER', 'your_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
PORT=os.getenv('PORT',"5002")


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

# Route to get post info
@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    
    logger.info(f"Got a new request to get_user_info")
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        logger.info(f"Fetching user info for user_id: {user_id}")

        # Fetch user information from User_table
        cur.execute('SELECT user_id, user_name FROM User_table WHERE user_id = %s', (user_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_info = {
            'user_id': user[0],
            'user_name': user[1]
        }
        
        return jsonify(user_info), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

# Route to insert a new user
@app.route('/insert_new_user', methods=['POST'])
def insert_new_user():
    logger.info(f"Got a new request to insert_new_user")
    
    data = request.json
    user_name = data.get('user_name')
    
    if not user_name:
        return jsonify({'error': 'user_name is required'}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Start a transaction
        conn.autocommit = False
        logger.info(f"Inserting new user: {user_name}")
        # Insert new user into User_table
        cur.execute(
            'INSERT INTO User_table (user_name) VALUES (%s) RETURNING user_id',
            (user_name,)
        )
        
        user_id = cur.fetchone()[0]
        
        # Commit transaction
        conn.commit()
        
        return jsonify({'user_id': user_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(PORT))
