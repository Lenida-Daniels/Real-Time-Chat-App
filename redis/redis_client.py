# connect python to redis 

import redis

# Initialize Redis client
redis_client = redis.Redis(
    host="localhost",# connect to Redis running on the same machine
    port=6379, # default is 6379
    db=0, #Redis supports multiple logical databases (numbered 0..N). 0 is the default.
    decode_responses=True # automatically decode bytes to strings, saves you from calling .decode() everywhere.
)

def test_connection():
    try:
        redis_client.ping()
        print("Connected to Redis!")
    except Exception as e:
        print("Redis connection failed:", e)
