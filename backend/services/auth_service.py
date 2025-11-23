"""
Authentication and user management service.

This service handles:
- User registration with username and phone number
- User login and validation
- User profile management
- Phone number verification (placeholder)
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_redis.redis_client import redis_client
from models.message import User, UserCreate, UserLogin, UserStatus


class AuthService:
    """
    Service class for user authentication and management.
    """
    
    def __init__(self):
        self.redis_client = redis_client
    
    def _generate_user_id(self, username: str, phone: str) -> str:
        """Generate unique user ID from username and phone."""
        return hashlib.md5(f"{username}:{phone}".encode()).hexdigest()[:12]
    
    def _generate_avatar_url(self, username: str) -> str:
        """Generate avatar URL for user."""
        return f"https://i.pravatar.cc/150?u={username}"
    
    async def register_user(self, user_data: UserCreate) -> Optional[User]:
        """
        Register a new user with username and phone number.
        
        Args:
            user_data: UserCreate object with registration details
            
        Returns:
            User: Complete user object if registration successful, None if failed
        """
        try:
            # Check if username already exists
            if await self.username_exists(user_data.username):
                return None
            
            # Check if phone number already exists
            if await self.phone_exists(user_data.phone_number):
                return None
            
            # Create user object
            user = User(
                username=user_data.username,
                phone_number=user_data.phone_number,
                display_name=user_data.display_name or user_data.username,
                avatar_url=user_data.avatar_url or self._generate_avatar_url(user_data.username),
                created_at=datetime.utcnow(),
                last_login=None,
                is_active=True
            )
            
            # Store user in Redis
            user_key = f"user:{user.username}"
            user_json = user.model_dump_json()
            self.redis_client.set(user_key, user_json)
            
            # Store phone number mapping for lookup
            phone_key = f"phone:{user.phone_number}"
            self.redis_client.set(phone_key, user.username)
            
            # Add to users list
            self.redis_client.sadd("users:all", user.username)
            
            return user
            
        except Exception as e:
            print(f"Error registering user: {e}")
            return None
    
    async def login_user(self, login_data: UserLogin) -> Optional[User]:
        """
        Login user with username and phone number.
        
        Args:
            login_data: UserLogin object with credentials
            
        Returns:
            User: User object if login successful, None if failed
        """
        try:
            # Get user by username
            user = await self.get_user(login_data.username)
            
            if not user:
                return None
            
            # Verify phone number matches
            if user.phone_number != login_data.phone_number:
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            await self.update_user(user)
            
            return user
            
        except Exception as e:
            print(f"Error logging in user: {e}")
            return None
    
    async def get_user(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username to lookup
            
        Returns:
            User: User object if found, None if not found
        """
        try:
            user_key = f"user:{username}"
            user_json = self.redis_client.get(user_key)
            
            if not user_json:
                return None
            
            user_dict = json.loads(user_json)
            # Convert datetime strings back to datetime objects
            user_dict['created_at'] = datetime.fromisoformat(user_dict['created_at'])
            if user_dict.get('last_login'):
                user_dict['last_login'] = datetime.fromisoformat(user_dict['last_login'])
            
            return User(**user_dict)
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone_number: Phone number to lookup
            
        Returns:
            User: User object if found, None if not found
        """
        try:
            phone_key = f"phone:{phone_number}"
            username = self.redis_client.get(phone_key)
            
            if not username:
                return None
            
            return await self.get_user(username)
            
        except Exception as e:
            print(f"Error getting user by phone: {e}")
            return None
    
    async def username_exists(self, username: str) -> bool:
        """
        Check if username already exists.
        
        Args:
            username: Username to check
            
        Returns:
            bool: True if username exists, False otherwise
        """
        try:
            user_key = f"user:{username}"
            return self.redis_client.exists(user_key) > 0
        except Exception as e:
            print(f"Error checking username: {e}")
            return False
    
    async def phone_exists(self, phone_number: str) -> bool:
        """
        Check if phone number already exists.
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            bool: True if phone exists, False otherwise
        """
        try:
            phone_key = f"phone:{phone_number}"
            return self.redis_client.exists(phone_key) > 0
        except Exception as e:
            print(f"Error checking phone: {e}")
            return False
    
    async def update_user(self, user: User) -> bool:
        """
        Update user information.
        
        Args:
            user: Updated user object
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            user_key = f"user:{user.username}"
            user_json = user.model_dump_json()
            self.redis_client.set(user_key, user_json)
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    async def get_all_users(self) -> List[User]:
        """
        Get all registered users.
        
        Returns:
            List[User]: List of all users
        """
        try:
            usernames = self.redis_client.smembers("users:all")
            users = []
            
            for username in usernames:
                user = await self.get_user(username)
                if user:
                    users.append(user)
            
            return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    async def suggest_usernames(self, base_username: str) -> List[str]:
        """
        Suggest alternative usernames if the requested one is taken.
        
        Args:
            base_username: Base username to generate suggestions from
            
        Returns:
            List[str]: List of suggested usernames
        """
        suggestions = []
        
        # Add numbers
        for i in range(1, 100):
            suggestion = f"{base_username}{i}"
            if not await self.username_exists(suggestion):
                suggestions.append(suggestion)
                if len(suggestions) >= 5:
                    break
        
        # Add underscores with numbers
        for i in range(1, 50):
            suggestion = f"{base_username}_{i}"
            if not await self.username_exists(suggestion):
                suggestions.append(suggestion)
                if len(suggestions) >= 8:
                    break
        
        return suggestions[:5]  # Return top 5 suggestions


# Create global instance
auth_service = AuthService()