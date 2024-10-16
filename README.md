# Toy Circuit Breaker System with Redis Pub-Sub

This project demonstrates a **prototypical circuit breaker system** using a Redis pub-sub mechanism for **service health monitoring**. The system consists of multiple services, including **Profile Service**, **Post Service**, **Feed Service**, and **Transaction Database**, all of which are orchestrated using Docker and Docker Compose. A Redis server is used to handle the pub-sub for monitoring the health of the **Profile Service**, which is consumed by other services like Post and Feed.

## Requirements:
    - Docker and Docker Compose

## Project Structure

```bash
├── Readme.md                   # Project documentation
├── docker-compose.yml           # Docker Compose file to orchestrate services
├── services
│   ├── feed_service             # Feed Service
│   │   ├── Dockerfile
│   │   ├── feed_server.py       # Flask API for fetching and submittingimpressions
│   │   └── requirements.txt     # Dependencies for feed service
│   ├── post_service             # Post Service
│   │   ├── Dockerfile
│   │   ├── post_server.py       # Flask API for handling posts
│   │   ├── requirements.txt     # Dependencies for post service
│   └── profile_service          # Profile Service
│       ├── Dockerfile
│       ├── profile_server.py    # Flask API for user profile management
│       ├── requirements.txt     # Dependencies for profile service
│   
├── simulate_user.py             # Script to simulate user interaction with the system
├── test_circuit_breaker.py      # Script to test circuit breaker behavior
├── transactional_db             # PostgreSQL transactional database
    ├── Dockerfile
    └── init.sql                 # SQL to initialize the database

```

## Overview Services

1. Profile Service: Manages user profiles, offering endpoints to fetch user info and insert new users.
2. Post Service: Handles the creation and retrieval of posts, interacts with the Profile Service for user information.
3. Feed Service: Fetches trending posts and submits impressions. It also interacts with the Profile Service for user info.
4. Transactional Database: A PostgreSQL instance to store posts, user profiles, impressions, and scores.
5. Redis Server: Used for pub-sub communication to monitor the health of the Profile Service.

## Circuit Breaker Mechanism

The Post Service and Feed Service subscribe to the profile_service_status channel, broadcasting the health status of the Profile Service. Before hitting the Profile Service, each service checks the current status to avoid making calls if the service is down.

If the status is "Unknown" or "UP", the services proceed to hit the Profile Service. If the request fails, the service broadcasts a "DOWN" status and falls back to cached data.


# Endpoints

### Profile Service
    - GET /get_user_info?user_id=<user_id>
        Returns user information for a given user ID.

    - POST /insert_new_user
        Inserts a new user into the system. Expects a JSON body with user_name.

### Post Service
    - GET /get_post_info?post_id=<post_id>
        Returns post information for a given post ID.

    - POST /insert_post
        Inserts a new post into the system. Expects a JSON body with user_id, title, and content.

### Feed Service
    - GET /fetch_feed
        Fetches the top 10 posts from the score table.
    - POST /submit_impression
        Submits an impression for a post and updates the score.
    - GET /get_trending_user_info
        Fetches the the top 10 users based on the Trending.


## Testing

### Simulate User Interaction:

You can simulate user actions like creating a user and posting by running the simulate_user.py script:

```bash
python3 simulate_user.py
```

### Test Circuit Breaker:

The test_circuit_breaker.py script can be used to simulate failures and test how the circuit breaker behaves:

```bash
python3 test_circuit_breaker.py
```



