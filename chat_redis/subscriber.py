#Create Function to SUBSCRIBE to Chat Channels
import json #convert incoming JSON strings back into Python dicts.
from .redis_client import redis_client

# FastAPI will often iterate over this generator to forward messages to WebSocket clients.
# Creates a PubSub object from the Redis client. This object manages subscriptions and listens for messages.
pubsub = redis_client.pubsub()
def subscribe_to_channel(channel: str): 
    """
    Subscribe to a Redis pub/sub channel.
    """
    pubsub = redis_client.pubsub() # Create a PubSub object from the Redis client. This object manages subscriptions and listens for messages.
    pubsub.subscribe(channel) # Redis will start sending incoming messages to this PubSub.

    for message in pubsub.listen(): # This is a blocking call that waits for new messages. Each message is itself a dict with keys like 'type', 'pattern', 'channel', and 'data'.
        if message['type'] == 'message': # filters to only actual published messages.
            yield json.loads(message['data'])

            #message['data'] is the JSON string we published earlier. 
            # json.loads(...) converts it back to a Python dict.
            #  yield returns that dict to the caller while the generator stays open to receive more messages.

 #FastAPI will use this to stream messages to frontend.

 # NOTE
#  this subscriber is synchronous/blocking, it uses the blocking listen() iterator.
#  That is fine if the FastAPI integration runs it in a background thread or process.
#  If you prefer async/non-blocking behavior, you would use redis.asyncio and an async loop.