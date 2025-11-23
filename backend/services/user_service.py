"""
User service for managing user sessions and online status.

This service handles:
- User session management
- Online/offline status tracking
- Typing indicators
- User presence in channels
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Set
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_redis.redis_client import redis_client
from models.message import UserStatus


class UserService:
    """
    Service class for user management using Redis.
    """
    
    def __init__(self):
        self.redis_client = redis_client
        self.online_users: Dict[str, Set[str]] = {}  # channel -> set of usernames
        self.user_sessions: Dict[str, str] = {}  # websocket_id -> username
    
    async def add_user_to_channel(self, username: str, channel: str, websocket_id: str = None) -> bool:
        """
        Add user to a channel and mark as online.
        
        Args:
            username: User's display name
            channel: Channel name to join
            websocket_id: WebSocket connection ID (optional)
            
        Returns:
            bool: True if user was added successfully
        """
        try:
            # Store user session if websocket_id provided
            if websocket_id:
                self.user_sessions[websocket_id] = username
            
            # Add to online users in memory
            if channel not in self.online_users:
                self.online_users[channel] = set()
            self.online_users[channel].add(username)
            
            # Store in Redis with expiration
            user_key = f"user:{username}:status"
            user_data = {
                "username": username,
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "channel": channel
            }
            
            # Store user status in Redis (expires in 1 hour)
            self.redis_client.setex(user_key, 3600, json.dumps(user_data))
            
            # Add to channel users set
            channel_users_key = f"channel:{channel}:users"
            self.redis_client.sadd(channel_users_key, username)
            self.redis_client.expire(channel_users_key, 3600)
            
            return True
        except Exception as e:
            print(f"Error adding user to channel: {e}")
            return False
    
    async def remove_user_from_channel(self, username: str, channel: str, websocket_id: str = None) -> bool:
        """
        Remove user from channel and update status.
        
        Args:
            username: User's display name
            channel: Channel name to leave
            websocket_id: WebSocket connection ID (optional)
            
        Returns:
            bool: True if user was removed successfully
        """
        try:
            # Remove from session tracking
            if websocket_id and websocket_id in self.user_sessions:
                del self.user_sessions[websocket_id]
            
            # Remove from online users in memory
            if channel in self.online_users and username in self.online_users[channel]:
                self.online_users[channel].discard(username)
            
            # Update user status in Redis
            user_key = f"user:{username}:status"
            user_data = {
                "username": username,
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "channel": channel
            }
            
            # Store offline status (expires in 24 hours)
            self.redis_client.setex(user_key, 24 * 3600, json.dumps(user_data))
            
            # Remove from channel users set
            channel_users_key = f"channel:{channel}:users"
            self.redis_client.srem(channel_users_key, username)
            
            return True
        except Exception as e:
            print(f"Error removing user from channel: {e}")
            return False
    
    async def get_online_users(self, channel: str) -> List[UserStatus]:
        """
        Get list of online users in a channel.
        
        Args:
            channel: Channel name
            
        Returns:
            List[UserStatus]: List of online users with their status
        """
        try:
            channel_users_key = f"channel:{channel}:users"
            usernames = self.redis_client.smembers(channel_users_key)
            
            online_users = []
            for username in usernames:
                user_key = f"user:{username}:status"
                user_data_str = self.redis_client.get(user_key)
                
                if user_data_str:
                    try:
                        user_data = json.loads(user_data_str)
                        user_status = UserStatus(
                            username=user_data["username"],
                            status=user_data["status"],
                            last_seen=datetime.fromisoformat(user_data["last_seen"])
                        )
                        online_users.append(user_status)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            return online_users
        except Exception as e:
            print(f"Error getting online users: {e}")
            return []
    
    async def set_user_typing(self, username: str, channel: str, is_typing: bool = True) -> bool:
        """
        Set user typing status.
        
        Args:
            username: User's display name
            channel: Channel name
            is_typing: Whether user is typing or not
            
        Returns:
            bool: True if status was updated successfully
        """
        try:
            typing_key = f"typing:{channel}:{username}"
            
            if is_typing:
                # Set typing status with 10 second expiration
                self.redis_client.setex(typing_key, 10, "typing")
            else:
                # Remove typing status
                self.redis_client.delete(typing_key)
            
            return True
        except Exception as e:
            print(f"Error setting typing status: {e}")
            return False
    
    async def get_typing_users(self, channel: str) -> List[str]:
        """
        Get list of users currently typing in a channel.
        
        Args:
            channel: Channel name
            
        Returns:
            List[str]: List of usernames currently typing
        """
        try:
            pattern = f"typing:{channel}:*"
            keys = self.redis_client.keys(pattern)
            
            typing_users = []
            for key in keys:
                # Extract username from "typing:channel:username"
                parts = key.split(':')
                if len(parts) >= 3:
                    username = parts[2]
                    typing_users.append(username)
            
            return typing_users
        except Exception as e:
            print(f"Error getting typing users: {e}")
            return []
    
    def get_username_by_websocket(self, websocket_id: str) -> str:
        """
        Get username associated with a WebSocket connection.
        
        Args:
            websocket_id: WebSocket connection ID
            
        Returns:
            str: Username or None if not found
        """
        return self.user_sessions.get(websocket_id)
    
    async def cleanup_expired_users(self) -> int:
        """
        Clean up expired user sessions and typing indicators.
        
        Returns:
            int: Number of expired entries cleaned up
        """
        try:
            cleaned_count = 0
            
            # Clean up expired typing indicators
            typing_pattern = "typing:*"
            typing_keys = self.redis_client.keys(typing_pattern)
            
            for key in typing_keys:
                # Check if key still exists (Redis auto-expires them)
                if not self.redis_client.exists(key):
                    cleaned_count += 1
            
            # Clean up offline users from channel sets
            channel_pattern = "channel:*:users"
            channel_keys = self.redis_client.keys(channel_pattern)
            
            for channel_key in channel_keys:
                usernames = self.redis_client.smembers(channel_key)
                for username in usernames:
                    user_key = f"user:{username}:status"
                    user_data_str = self.redis_client.get(user_key)
                    
                    if not user_data_str:
                        # User data expired, remove from channel
                        self.redis_client.srem(channel_key, username)
                        cleaned_count += 1
            
            return cleaned_count
        except Exception as e:
            print(f"Error cleaning up expired users: {e}")
            return 0


# Create global instance
user_service = UserService()