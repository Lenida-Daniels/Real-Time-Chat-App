# Define the Message Structure
from datetime import datetime # To timestamp messages with a standard format.

def create_message(sender: str, content: str, channel: str):
    return {
        "sender": sender, # who sent the message
        "content": content, # the message text
        "channel": channel, # channel or room id the message belongs to (helps consumers route messages)
        "timestamp": datetime.utcnow().isoformat() # the exact time message was created
    }

# using datetime.utcnow().isoformat() so all systems use UTC.
#This is the message format sent to Redis