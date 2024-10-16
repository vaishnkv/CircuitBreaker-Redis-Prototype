import requests
import json
from faker import Faker
import random



# Base URLs for the services
PROFILE_SERVICE_URL = "http://localhost:5002"
POST_SERVICE_URL = "http://localhost:5001"
FEED_SERVICE_URL="http://localhost:5003"

# Initialize Faker
fake = Faker()


# List of choices for random selection
choices = ["UP", "DOWN"]

class User:

    @staticmethod
    def create_new_user(user_name):
        url = f"{PROFILE_SERVICE_URL}/insert_new_user"
        data = {'user_name': user_name}
        response = requests.post(url, json=data)

        if response.status_code == 201:
            user_id = response.json().get('user_id')
            print(f"New user created: ID = {user_id}, Name = {user_name}")
            return user_id
        else:
            print(f"Error creating user: {response.json()}")
            return None
    @staticmethod
    def get_user_info(user_id):
        url = f"{PROFILE_SERVICE_URL}/get_user_info?user_id={user_id}"
        response = requests.get(url)

        if response.status_code == 200:
            user_info = response.json()
            print(f"User Info: {user_info}")
        else:
            print(f"Error fetching user info: {response.json()}")
    @staticmethod
    def create_new_post(user_id,title, content):
        url = f"{POST_SERVICE_URL}/insert_post"
        data = {
            'user_id': user_id,
            'title':title,
            'content': content
        }
        response = requests.post(url, json=data)

        if response.status_code == 201:
            post_id = response.json().get('post_id')
            print(f"New post created: ID = {post_id},Title = {title}, Content = {content}")
            return post_id
        else:
            print(f"Error creating post: {response.json()}")
            return None
    @staticmethod
    def get_post_info(post_id):
        url = f"{POST_SERVICE_URL}/get_post_info?post_id={post_id}"
        response = requests.get(url)

        if response.status_code == 200:
            post_info = response.json()
            print(f"Post Info: {post_info}")
        else:
            print(f"Error fetching post info: {response.json()}")
    # Fetch feed (top N posts)
    @staticmethod
    def fetch_feed():
        url = f'{FEED_SERVICE_URL}/fetch_feed'
        try:
            response = requests.get(url)
            feed = response.json()
            print(f"Feed: {json.dumps(feed, indent=4)}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching feed: {e}")

    # Submit an impression for a post
    @staticmethod
    def submit_impression(post_id, user_id, impression_type):
        url = f'{FEED_SERVICE_URL}/submit_impression'
        data = {
            'post_id': post_id,
            'user_id': user_id,
            'impression_type': impression_type
        }
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            print(f"Impression submitted successfully for post_id: {post_id}, user_id: {user_id}")
        except requests.exceptions.RequestException as e:
            print(f"Error submitting impression: {e}")

    @staticmethod
    def get_trending_users():
        url = f'{FEED_SERVICE_URL}/get_trending_user_info'
        try:
            response = requests.get(url)
            feed = response.json()
            print(f"Feed: {json.dumps(feed, indent=4)}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching feed: {e}")



def do_sequence_of_actions():
    # Simulate user interactions
    # user_id = User.create_new_user(fake.name())
    # if user_id:
    #     User.get_user_info(user_id)
    #     post_id = User.create_new_post(user_id,fake.job(), fake.sentence())
    
    post_id="1"
    if post_id:
        User.get_post_info(post_id)
    User.get_trending_users()
    


if __name__ == "__main__":
    
    for _ in range(1):
        do_sequence_of_actions()