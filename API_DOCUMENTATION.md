# Real-Time Chat API Documentation

## Overview

This FastAPI application provides a complete real-time chat system with WebSocket support and Redis integration.

## Base URL
```
http://localhost:8000
```

## WebSocket Endpoint

### Connect to Chat
```
ws://localhost:8000/ws/chat?username=YourName&channel=general
```

**Query Parameters:**
- `username` (required): User's display name
- `channel` (optional): Channel to join (default: "general")

**Message Types:**

#### Send Message
```json
{
  "type": "message",
  "sender": "username",
  "content": "Hello world!",
  "channel": "general",
  "message_type": "text"
}
```

#### Typing Indicators
```json
{
  "type": "typing_start",
  "sender": "username",
  "channel": "general"
}
```

```json
{
  "type": "typing_stop",
  "sender": "username", 
  "channel": "general"
}
```

**Received Message Types:**

#### Regular Message
```json
{
  "type": "message",
  "sender": "username",
  "content": "Hello world!",
  "channel": "general",
  "message_type": "text",
  "timestamp": "2024-01-01T12:00:00",
  "message_id": "uuid"
}
```

#### User Events
```json
{
  "type": "user_joined",
  "username": "newuser",
  "channel": "general",
  "timestamp": "2024-01-01T12:00:00"
}
```

```json
{
  "type": "user_left",
  "username": "olduser", 
  "channel": "general",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### Typing Status
```json
{
  "type": "typing_status",
  "username": "someuser",
  "channel": "general", 
  "is_typing": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

## REST API Endpoints

### Health Check
```http
GET /
```

**Response:**
```json
{
  "message": "Real-Time Chat API is running!",
  "version": "1.0.0",
  "endpoints": {
    "websocket": "/ws/chat?username=YourName&channel=general",
    "chat_history": "/api/chat/history/{channel}",
    "online_users": "/api/users/online/{channel}",
    "channels": "/api/chat/channels"
  }
}
```

### Get Chat History
```http
GET /api/chat/history/{channel}?limit=50
```

**Parameters:**
- `channel` (path): Channel name
- `limit` (query, optional): Max messages to retrieve (default: 50)

**Response:**
```json
{
  "messages": [
    {
      "sender": "username",
      "content": "Hello!",
      "channel": "general",
      "message_type": "text",
      "timestamp": "2024-01-01T12:00:00",
      "message_id": "uuid"
    }
  ],
  "total_count": 1,
  "channel": "general"
}
```

### Get Online Users
```http
GET /api/users/online/{channel}
```

**Response:**
```json
{
  "channel": "general",
  "online_users": [
    {
      "username": "user1",
      "status": "online",
      "last_seen": "2024-01-01T12:00:00"
    }
  ],
  "count": 1
}
```

### Get Active Channels
```http
GET /api/chat/channels
```

**Response:**
```json
{
  "channels": ["general", "random", "tech"],
  "count": 3
}
```

### Send Message (REST)
```http
POST /api/chat/message
Content-Type: application/json

{
  "sender": "username",
  "content": "Hello via REST!",
  "channel": "general",
  "message_type": "text"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": {
    "sender": "username",
    "content": "Hello via REST!",
    "channel": "general",
    "message_type": "text",
    "timestamp": "2024-01-01T12:00:00",
    "message_id": "uuid"
  }
}
```

### Delete Message
```http
DELETE /api/chat/message/{message_id}?channel=general
```

**Parameters:**
- `message_id` (path): ID of message to delete
- `channel` (query): Channel where message exists

**Response:**
```json
{
  "success": true,
  "message": "Message deleted successfully"
}
```

## Message Types

### Text Message
```json
{
  "message_type": "text",
  "content": "Hello world!"
}
```

### Image Message
```json
{
  "message_type": "image", 
  "content": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
}
```

### Audio Message
```json
{
  "message_type": "audio",
  "content": "data:audio/webm;base64,GkXfo59ChoEBQveBAULygQ..."
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request format"
}
```

### 404 Not Found
```json
{
  "detail": "Message not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error retrieving chat history: Connection failed"
}
```

## Rate Limiting

Currently no rate limiting is implemented. In production, consider:
- Message rate limiting per user
- Connection limits per IP
- File upload size limits

## Security Considerations

### Current Implementation
- CORS enabled for all origins (development only)
- No authentication required
- No message encryption

### Production Recommendations
- Implement JWT authentication
- Add message encryption
- Restrict CORS origins
- Add rate limiting
- Validate file uploads
- Sanitize message content

## Redis Data Structure

### Message Storage
```
Key: chat:{channel}:messages
Type: List
Value: JSON message objects
TTL: 30 days
```

### User Status
```
Key: user:{username}:status  
Type: String
Value: JSON user status object
TTL: 1 hour (online), 24 hours (offline)
```

### Channel Users
```
Key: channel:{channel}:users
Type: Set
Value: Usernames
TTL: 1 hour
```

### Typing Indicators
```
Key: typing:{channel}:{username}
Type: String
Value: "typing"
TTL: 10 seconds
```

## Development

### Running the API
```bash
# Start Redis
redis-server

# Install dependencies
cd backend
pip install -r requirements.txt

# Run FastAPI
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive Swagger documentation.

### Testing WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat?username=testuser');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'message',
    sender: 'testuser',
    content: 'Hello!',
    channel: 'general'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};
```

## Monitoring

### Health Checks
- GET `/` - API health
- `redis-cli ping` - Redis health
- WebSocket connection test

### Logs
- Backend logs: `logs/backend.log`
- Redis logs: Check Redis configuration
- Browser console for frontend errors

## Deployment

### Environment Variables
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
API_HOST=0.0.0.0
API_PORT=8000
```

### Docker Support
Consider containerizing with Docker for production deployment.

### Scaling
- Use Redis Cluster for horizontal scaling
- Load balance FastAPI instances
- Consider using Redis Streams for message persistence