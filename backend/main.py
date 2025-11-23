"""
FastAPI Real-Time Chat Application

This is the main FastAPI application that provides:
- WebSocket endpoints for real-time messaging
- REST API endpoints for chat history and user management
- Integration with Redis for message storage and pub/sub
- CORS support for frontend integration

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List
import sys
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.message import Message, MessageCreate, MessageResponse, ChatHistory, User, UserCreate, UserLogin, Group, GroupCreate, GroupUpdate, ProfileUpdate
from services.chat_service import chat_service
from services.user_service import user_service
from services.auth_service import auth_service
from services.group_service import group_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_redis.subscriber import subscribe_to_channel


# Initialize FastAPI app
app = FastAPI(
    title="Real-Time Chat API",
    description="FastAPI backend for real-time chat application with Redis integration",
    version="1.0.0"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time messaging.
    
    Handles:
    - Active WebSocket connections
    - Broadcasting messages to connected clients
    - User session management
    """
    
    def __init__(self):
        # Store active connections: {websocket_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user info: {websocket_id: {"username": str, "channel": str}}
        self.connection_info: Dict[str, Dict[str, str]] = {}
    
    async def connect(self, websocket: WebSocket, username: str, channel: str = "general") -> str:
        """
        Accept WebSocket connection and register user.
        
        Args:
            websocket: WebSocket connection object
            username: User's display name
            channel: Channel to join (default: general)
            
        Returns:
            str: Unique connection ID
        """
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_info[connection_id] = {
            "username": username,
            "channel": channel
        }
        
        # Add user to channel
        await user_service.add_user_to_channel(username, channel, connection_id)
        
        print(f"User {username} connected to channel {channel} (ID: {connection_id})")
        
        # Notify other users about new connection
        await self.broadcast_user_joined(username, channel, connection_id)
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Remove WebSocket connection and clean up user session.
        
        Args:
            connection_id: Connection ID to remove
        """
        if connection_id in self.active_connections:
            # Get user info before removing
            user_info = self.connection_info.get(connection_id, {})
            username = user_info.get("username", "Unknown")
            channel = user_info.get("channel", "general")
            
            # Remove from active connections
            del self.active_connections[connection_id]
            del self.connection_info[connection_id]
            
            # Remove user from channel
            await user_service.remove_user_from_channel(username, channel, connection_id)
            
            print(f"User {username} disconnected from channel {channel}")
            
            # Notify other users about disconnection
            await self.broadcast_user_left(username, channel, connection_id)
    
    async def send_personal_message(self, message: str, connection_id: str):
        """
        Send message to a specific WebSocket connection.
        
        Args:
            message: JSON message string
            connection_id: Target connection ID
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to {connection_id}: {e}")
                # Remove broken connection
                await self.disconnect(connection_id)
    
    async def broadcast_to_channel(self, message: str, channel: str, exclude_connection: str = None):
        """
        Broadcast message to all users in a specific channel.
        
        Args:
            message: JSON message string
            channel: Target channel name
            exclude_connection: Connection ID to exclude from broadcast
        """
        disconnected_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            # Check if connection is in the target channel
            user_info = self.connection_info.get(connection_id, {})
            if user_info.get("channel") == channel and connection_id != exclude_connection:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    print(f"Error broadcasting to {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
        
        # Clean up broken connections
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)
    
    async def broadcast_user_joined(self, username: str, channel: str, exclude_connection: str = None):
        """
        Broadcast user joined notification to channel.
        """
        message = {
            "type": "user_joined",
            "username": username,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel(json.dumps(message), channel, exclude_connection)
    
    async def broadcast_user_left(self, username: str, channel: str, exclude_connection: str = None):
        """
        Broadcast user left notification to channel.
        """
        message = {
            "type": "user_left",
            "username": username,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel(json.dumps(message), channel, exclude_connection)
    
    async def broadcast_typing_status(self, username: str, channel: str, is_typing: bool, exclude_connection: str = None):
        """
        Broadcast typing status to channel.
        """
        message = {
            "type": "typing_status",
            "username": username,
            "channel": channel,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel(json.dumps(message), channel, exclude_connection)


# Create global connection manager
manager = ConnectionManager()


# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, username: str, channel: str = "general"):
    """
    WebSocket endpoint for real-time chat communication.
    
    Query Parameters:
        username: User's display name
        channel: Channel to join (optional, defaults to 'general')
    
    Message Types Handled:
        - message: Regular chat message
        - typing_start: User started typing
        - typing_stop: User stopped typing
    """
    connection_id = await manager.connect(websocket, username, channel)
    
    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")
                
                if message_type == "message":
                    # Handle regular chat message
                    await handle_chat_message(message_data, connection_id, channel)
                
                elif message_type == "typing_start":
                    # Handle typing indicator
                    await user_service.set_user_typing(username, channel, True)
                    await manager.broadcast_typing_status(username, channel, True, connection_id)
                
                elif message_type == "typing_stop":
                    # Handle stop typing
                    await user_service.set_user_typing(username, channel, False)
                    await manager.broadcast_typing_status(username, channel, False, connection_id)
                
            except json.JSONDecodeError:
                # Handle plain text messages (backward compatibility)
                message_data = {
                    "type": "message",
                    "content": data,
                    "sender": username,
                    "channel": channel
                }
                await handle_chat_message(message_data, connection_id, channel)
                
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        print(f"WebSocket error for {username}: {e}")
        await manager.disconnect(connection_id)


async def handle_chat_message(message_data: dict, connection_id: str, channel: str):
    """
    Handle incoming chat message from WebSocket.
    
    Args:
        message_data: Message data dictionary
        connection_id: WebSocket connection ID
        channel: Channel name
    """
    try:
        # Create message object
        message_create = MessageCreate(
            sender=message_data.get("sender", "Anonymous"),
            content=message_data.get("content", ""),
            channel=channel,
            message_type=message_data.get("message_type", "text")
        )
        
        # Save message to Redis
        message = await chat_service.save_message(message_create)
        
        # Publish message to Redis pub/sub for broadcasting
        await chat_service.publish_message(message)
        
        # Broadcast to WebSocket connections in the same channel
        broadcast_message = {
            "type": "message",
            "sender": message.sender,
            "content": message.content,
            "channel": message.channel,
            "message_type": message.message_type,
            "timestamp": message.timestamp.isoformat(),
            "message_id": message.message_id
        }
        
        await manager.broadcast_to_channel(
            json.dumps(broadcast_message), 
            channel, 
            exclude_connection=connection_id
        )
        
    except Exception as e:
        print(f"Error handling chat message: {e}")


# REST API Endpoints

@app.get("/", response_model=dict)
async def root():
    """
    Root endpoint - API health check.
    """
    return {
        "message": "Real-Time Chat API is running!",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/chat?username=YourName&channel=general",
            "chat_history": "/api/chat/history/{channel}",
            "online_users": "/api/users/online/{channel}",
            "channels": "/api/chat/channels"
        }
    }


@app.get("/api/chat/history/{channel}", response_model=ChatHistory)
async def get_chat_history(channel: str, limit: int = 50):
    """
    Get chat history for a specific channel.
    
    Args:
        channel: Channel name
        limit: Maximum number of messages to retrieve (default: 50)
    
    Returns:
        ChatHistory: Chat history with messages and metadata
    """
    try:
        messages = await chat_service.get_chat_history(channel, limit)
        
        return ChatHistory(
            messages=messages,
            total_count=len(messages),
            channel=channel
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")


@app.get("/api/users/online/{channel}")
async def get_online_users(channel: str):
    """
    Get list of online users in a channel.
    
    Args:
        channel: Channel name
    
    Returns:
        dict: List of online users with their status
    """
    try:
        online_users = await user_service.get_online_users(channel)
        return {
            "channel": channel,
            "online_users": [user.model_dump() for user in online_users],
            "count": len(online_users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving online users: {str(e)}")


@app.get("/api/chat/channels")
async def get_active_channels():
    """
    Get list of active chat channels.
    
    Returns:
        dict: List of active channels
    """
    try:
        channels = await chat_service.get_active_channels()
        return {
            "channels": channels,
            "count": len(channels)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving channels: {str(e)}")


@app.post("/api/chat/message", response_model=MessageResponse)
async def send_message(message_data: MessageCreate):
    """
    Send a message via REST API (alternative to WebSocket).
    
    Args:
        message_data: Message data
    
    Returns:
        MessageResponse: Success response with message details
    """
    try:
        # Save message
        message = await chat_service.save_message(message_data)
        
        # Publish message
        await chat_service.publish_message(message)
        
        # Broadcast to WebSocket connections
        broadcast_message = {
            "type": "message",
            "sender": message.sender,
            "content": message.content,
            "channel": message.channel,
            "message_type": message.message_type,
            "timestamp": message.timestamp.isoformat(),
            "message_id": message.message_id
        }
        
        await manager.broadcast_to_channel(
            json.dumps(broadcast_message), 
            message.channel
        )
        
        return MessageResponse(
            success=True,
            message="Message sent successfully",
            data=message.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@app.delete("/api/chat/message/{message_id}")
async def delete_message(message_id: str, channel: str):
    """
    Delete a specific message.
    
    Args:
        message_id: ID of the message to delete
        channel: Channel where the message exists
    
    Returns:
        MessageResponse: Success response
    """
    try:
        success = await chat_service.delete_message(message_id, channel)
        
        if success:
            # Broadcast deletion to WebSocket connections
            delete_message = {
                "type": "message_deleted",
                "message_id": message_id,
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.broadcast_to_channel(
                json.dumps(delete_message), 
                channel
            )
            
            return MessageResponse(
                success=True,
                message="Message deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Message not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting message: {str(e)}")


# Authentication Endpoints

@app.post("/api/auth/register", response_model=dict)
async def register_user(user_data: UserCreate):
    """
    Register a new user with username and phone number.
    
    Args:
        user_data: User registration data
    
    Returns:
        dict: Registration result with user data or error
    """
    try:
        # Check if username exists
        if await auth_service.username_exists(user_data.username):
            suggestions = await auth_service.suggest_usernames(user_data.username)
            return {
                "success": False,
                "message": "Username already exists",
                "suggestions": suggestions
            }
        
        # Check if phone exists
        if await auth_service.phone_exists(user_data.phone_number):
            return {
                "success": False,
                "message": "Phone number already registered"
            }
        
        # Register user
        user = await auth_service.register_user(user_data)
        
        if user:
            return {
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "username": user.username,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "created_at": user.created_at.isoformat()
                }
            }
        else:
            return {
                "success": False,
                "message": "Registration failed"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")


@app.post("/api/auth/login", response_model=dict)
async def login_user(login_data: UserLogin):
    """
    Login user with username and phone number.
    
    Args:
        login_data: Login credentials
    
    Returns:
        dict: Login result with user data or error
    """
    try:
        user = await auth_service.login_user(login_data)
        
        if user:
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "username": user.username,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "phone_number": user.phone_number,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            }
        else:
            return {
                "success": False,
                "message": "Invalid username or phone number"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@app.get("/api/auth/check-username/{username}")
async def check_username(username: str):
    """
    Check if username is available.
    
    Args:
        username: Username to check
    
    Returns:
        dict: Availability status and suggestions if taken
    """
    try:
        exists = await auth_service.username_exists(username)
        
        if exists:
            suggestions = await auth_service.suggest_usernames(username)
            return {
                "available": False,
                "message": "Username already taken",
                "suggestions": suggestions
            }
        else:
            return {
                "available": True,
                "message": "Username is available"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking username: {str(e)}")


@app.get("/api/users/all")
async def get_all_users():
    """
    Get all registered users (for admin or development).
    
    Returns:
        dict: List of all users
    """
    try:
        users = await auth_service.get_all_users()
        return {
            "users": [{
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at.isoformat(),
                "is_active": user.is_active
            } for user in users],
            "count": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")


# Profile Management Endpoints

@app.put("/api/profile/{username}")
async def update_profile(username: str, profile_data: ProfileUpdate):
    """
    Update user profile.
    
    Args:
        username: Username to update
        profile_data: Profile update data
    
    Returns:
        dict: Updated profile information
    """
    try:
        user = await auth_service.get_user(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        if profile_data.display_name is not None:
            user.display_name = profile_data.display_name
        if profile_data.avatar_url is not None:
            user.avatar_url = profile_data.avatar_url
        if profile_data.phone_number is not None:
            # Check if new phone number is already taken
            if await auth_service.phone_exists(profile_data.phone_number):
                existing_user = await auth_service.get_user_by_phone(profile_data.phone_number)
                if existing_user and existing_user.username != username:
                    return {
                        "success": False,
                        "message": "Phone number already in use by another account"
                    }
            user.phone_number = profile_data.phone_number
        
        # Save updated user
        success = await auth_service.update_user(user)
        
        if success:
            return {
                "success": True,
                "message": "Profile updated successfully",
                "user": {
                    "username": user.username,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "phone_number": user.phone_number
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to update profile"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


# Group Management Endpoints

@app.post("/api/groups/create")
async def create_group(group_data: GroupCreate):
    """
    Create a new group.
    
    Args:
        group_data: Group creation data
    
    Returns:
        dict: Created group information
    """
    try:
        group = await group_service.create_group(group_data)
        
        if group:
            return {
                "success": True,
                "message": "Group created successfully",
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "image_url": group.image_url,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat(),
                    "members": group.members,
                    "admins": group.admins
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to create group"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")


@app.put("/api/groups/{group_id}")
async def update_group(group_id: str, update_data: GroupUpdate, updated_by: str):
    """
    Update group information.
    
    Args:
        group_id: Group ID to update
        update_data: Update data
        updated_by: Username of user making the update
    
    Returns:
        dict: Updated group information
    """
    try:
        group = await group_service.update_group(group_id, update_data, updated_by)
        
        if group:
            return {
                "success": True,
                "message": "Group updated successfully",
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "image_url": group.image_url,
                    "members": group.members,
                    "admins": group.admins
                }
            }
        else:
            return {
                "success": False,
                "message": "Failed to update group or insufficient permissions"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating group: {str(e)}")


@app.get("/api/groups/{group_id}")
async def get_group(group_id: str):
    """
    Get group information.
    
    Args:
        group_id: Group ID to retrieve
    
    Returns:
        dict: Group information
    """
    try:
        group = await group_service.get_group(group_id)
        
        if group:
            return {
                "success": True,
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "image_url": group.image_url,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat(),
                    "members": group.members,
                    "admins": group.admins
                }
            }
        else:
            raise HTTPException(status_code=404, detail="Group not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving group: {str(e)}")


@app.get("/api/users/{username}/groups")
async def get_user_groups(username: str):
    """
    Get all groups for a user.
    
    Args:
        username: Username to get groups for
    
    Returns:
        dict: List of user's groups
    """
    try:
        groups = await group_service.get_user_groups(username)
        
        return {
            "groups": [{
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "image_url": group.image_url,
                "created_by": group.created_by,
                "member_count": len(group.members),
                "is_admin": username in group.admins
            } for group in groups],
            "count": len(groups)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user groups: {str(e)}")


# Background task for cleanup
async def cleanup_task():
    """
    Background task to clean up expired user sessions and typing indicators.
    Runs every 5 minutes.
    """
    while True:
        try:
            cleaned_count = await user_service.cleanup_expired_users()
            if cleaned_count > 0:
                print(f"Cleaned up {cleaned_count} expired user entries")
        except Exception as e:
            print(f"Error in cleanup task: {e}")
        
        # Wait 5 minutes before next cleanup
        await asyncio.sleep(300)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event - initialize background tasks.
    """
    print("🚀 Real-Time Chat API starting up...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws/chat")
    print("🌐 API documentation: http://localhost:8000/docs")
    
    # Start background cleanup task
    asyncio.create_task(cleanup_task())


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event - cleanup resources.
    """
    print("🛑 Real-Time Chat API shutting down...")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )