# Create Function to PUBLISH Chat Messages
import json #Redis Pub/Sub transmits strings, so serialize message dict to JSON.
from .redis_client import redis_client

#a function that other code (FastAPI) will call when a message should be broadcast.
def publish_message(channel: str, message: dict):
    """
    Publish a chat message to a given channel.
    """
    redis_client.publish(channel, json.dumps(message)) # converts the Python message dict to a JSON string.
    """
    json.dumps(message) is the payload
    It takes your Python dict (the message)
    Converts it into a JSON string
    Sends that string to Redis as the message body
    Any subscriber listening on that channel will receive it."""

    return True
 #FastAPI will call this function when a user sends a message.