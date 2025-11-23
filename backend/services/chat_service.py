"""
Chat service for handling message operations and Redis integration.

This service manages:
- Message publishing to Redis channels
- Message storage in Redis lists
- Chat history retrieval
- Real-time message broadcasting
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_redis.redis_client import redis_client
from chat_redis.publisher import publish_message
from models.message import Message, MessageCreate


class ChatService:
    """
    Service class for chat operations using Redis as the backend.
    """
    
    def __init__(self):
        self.redis_client = redis_client
        self.default_channel = "general"
    
    async def save_message(self, message_data: MessageCreate) -> Message:
        """
        Save a message to Redis and return the complete message object.
        
        Args:
            message_data: MessageCreate object with message details
            
        Returns:
            Message: Complete message object with timestamp and ID
        """
        # Create complete message object
        message = Message(
            sender=message_data.sender,
            content=message_data.content,
            channel=message_data.channel,
            message_type=message_data.message_type,
            timestamp=datetime.utcnow(),
            message_id=str(uuid.uuid4())
        )
        
        # Store in Redis list for chat history
        message_key = f"chat:{message.channel}:messages"
        message_json = message.model_dump_json()
        
        # Add to list (LPUSH adds to beginning, so newest messages are first)
        self.redis_client.lpush(message_key, message_json)
        
        # Keep only last 1000 messages per channel
        self.redis_client.ltrim(message_key, 0, 999)
        
        # Set expiration for the message list (30 days)
        self.redis_client.expire(message_key, 30 * 24 * 60 * 60)
        
        return message
    
    async def publish_message(self, message: Message) -> bool:
        """
        Publish message to Redis pub/sub channel for real-time broadcasting.
        
        Args:
            message: Complete message object to broadcast
            
        Returns:
            bool: True if published successfully
        """
        try:
            # Convert message to dict for JSON serialization
            message_dict = {
                "sender": message.sender,
                "content": message.content,
                "channel": message.channel,
                "message_type": message.message_type,
                "timestamp": message.timestamp.isoformat(),
                "message_id": message.message_id
            }
            
            # Publish to Redis channel
            channel_name = f"chat:{message.channel}"
            publish_message(channel_name, message_dict)
            
            return True
        except Exception as e:
            print(f"Error publishing message: {e}")
            return False
    
    async def get_chat_history(self, channel: str = None, limit: int = 50) -> List[Message]:
        """
        Retrieve chat history from Redis.
        
        Args:
            channel: Channel name (defaults to general)
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Message]: List of messages in chronological order
        """
        if not channel:
            channel = self.default_channel
            
        message_key = f"chat:{channel}:messages"
        
        try:
            # Get messages from Redis list (LRANGE gets from list)
            # Get from end to beginning to maintain chronological order
            message_strings = self.redis_client.lrange(message_key, 0, limit - 1)
            
            messages = []
            for msg_str in reversed(message_strings):  # Reverse to get chronological order
                try:
                    message_dict = json.loads(msg_str)
                    # Convert timestamp string back to datetime
                    message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp'])
                    messages.append(Message(**message_dict))
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing message: {e}")
                    continue
            
            return messages
        except Exception as e:
            print(f"Error retrieving chat history: {e}")
            return []
    
    async def get_active_channels(self) -> List[str]:
        """
        Get list of active chat channels.
        
        Returns:
            List[str]: List of channel names that have messages
        """
        try:
            # Find all chat message keys
            pattern = "chat:*:messages"
            keys = self.redis_client.keys(pattern)
            
            # Extract channel names from keys
            channels = []
            for key in keys:
                # Extract channel name from "chat:channel_name:messages"
                parts = key.split(':')
                if len(parts) >= 3:
                    channel_name = parts[1]
                    channels.append(channel_name)
            
            return channels
        except Exception as e:
            print(f"Error getting active channels: {e}")
            return [self.default_channel]
    
    async def delete_message(self, message_id: str, channel: str) -> bool:
        """
        Delete a specific message from chat history.
        
        Args:
            message_id: ID of the message to delete
            channel: Channel where the message exists
            
        Returns:
            bool: True if message was deleted successfully
        """
        message_key = f"chat:{channel}:messages"
        
        try:
            # Get all messages
            message_strings = self.redis_client.lrange(message_key, 0, -1)
            
            # Find and remove the message with matching ID
            for i, msg_str in enumerate(message_strings):
                try:
                    message_dict = json.loads(msg_str)
                    if message_dict.get('message_id') == message_id:
                        # Remove the message at this index
                        # Redis doesn't have direct index removal, so we use a placeholder
                        placeholder = f"__DELETED__{uuid.uuid4()}"
                        self.redis_client.lset(message_key, i, placeholder)
                        self.redis_client.lrem(message_key, 1, placeholder)
                        return True
                except json.JSONDecodeError:
                    continue
            
            return False
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False


# Create global instance
chat_service = ChatService()