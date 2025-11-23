"""
Message models for the Real-Time Chat Application.

This module defines Pydantic models for:
- Message structure validation
- API request/response schemas
- WebSocket message formats
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    """
    Schema for creating a new message.
    Used when client sends a message via WebSocket or REST API.
    """
    sender: str
    content: str
    channel: str = "general"  # Default channel
    message_type: str = "text"  # text, image, audio


class Message(BaseModel):
    """
    Complete message model with timestamp.
    Used for storing and retrieving messages from Redis.
    """
    sender: str
    content: str
    channel: str
    message_type: str
    timestamp: datetime
    message_id: Optional[str] = None


class MessageResponse(BaseModel):
    """
    API response model for message operations.
    """
    success: bool
    message: str
    data: Optional[dict] = None


class ChatHistory(BaseModel):
    """
    Model for chat history response.
    """
    messages: List[Message]
    total_count: int
    channel: str


class UserCreate(BaseModel):
    """
    Schema for creating a new user account.
    """
    username: str
    phone_number: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class User(BaseModel):
    """
    Complete user model with all details.
    """
    username: str
    phone_number: str
    display_name: str
    avatar_url: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class UserLogin(BaseModel):
    """
    Schema for user login.
    """
    username: str
    phone_number: str


class GroupCreate(BaseModel):
    """
    Schema for creating a new group.
    """
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_by: str


class Group(BaseModel):
    """
    Complete group model.
    """
    id: str
    name: str
    description: Optional[str] = None
    image_url: str
    created_by: str
    created_at: datetime
    members: List[str] = []
    admins: List[str] = []


class GroupUpdate(BaseModel):
    """
    Schema for updating group information.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProfileUpdate(BaseModel):
    """
    Schema for updating user profile.
    """
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None


class UserStatus(BaseModel):
    """
    Model for user online status.
    """
    username: str
    display_name: str
    phone_number: str
    status: str  # online, offline, typing
    last_seen: datetime