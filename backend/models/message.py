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


class UserStatus(BaseModel):
    """
    Model for user online status.
    """
    username: str
    status: str  # online, offline, typing
    last_seen: datetime