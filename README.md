# Real-Time Chat Application (React + FastAPI + Redis/Memurai)

Below is a clean, complete, copy‑ready documentation of the project structure and how everything works. Use this directly in your README.

---

# 📦 PROJECT STRUCTURE OVERVIEW

```
chat-app/
│
├── backend/
│   ├── main.py
│   ├── redis_client.py
│   ├── requirements.txt
│   │
│   ├── models/
│   │   └── message.py
│   │
│   └── services/
│       ├── chat_service.py
│       └── user_service.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   │
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       │
│       ├── components/
│       │   ├── ChatWindow.jsx
│       │   ├── MessageInput.jsx
│       │   └── MessageBubble.jsx
│       │
│       ├── services/
│       │   ├── api.js
│       │   └── websocket.js
│       │
│       └── styles/
│           └── chat.css
│
└── redis/
    ├── redis_client.py
    ├── publisher.py
    ├── subscriber.py
    └── message_model.py
```

---

# 🧠 SYSTEM OVERVIEW — HOW IT WORKS

This real‑time chat app runs on **three layers**:

---

## ⭐ 1. FRONTEND (React)

Responsible for:

* Connecting to the WebSocket
* Sending messages instantly
* Receiving messages instantly
* Displaying chat history

### Main components:

**ChatWindow.jsx** — Renders list of messages.
**MessageInput.jsx** — Text field + send button.
**MessageBubble.jsx** — UI for each message.
**websocket.js** — Manages WebSocket connection.
**api.js** — Fetches chat history from REST API.

### What the frontend actually does:

1. Opens WebSocket connection: `ws://localhost:8000/ws/chat`
2. Sends user messages → backend
3. Receives broadcasted messages from backend
4. Updates the UI instantly

---

## ⭐ 2. BACKEND (FastAPI)

The backend is the **brain** of the whole system.

### Backend does:

* Provides a **WebSocket endpoint** for real-time chat
* Provides **REST API endpoints** (to fetch history)
* Connects to **Redis/Memurai** and handles Pub/Sub
* Broadcasts messages to all connected users

### Key backend files:

**main.py**

* Creates WebSocket `/ws/chat`
* Listens for new messages
* Publishes messages to Redis
* Subscribes to Redis channel
* Sends messages back to all clients

**redis_client.py**

* Creates connection to Redis/Memurai

**chat_service.py**

* Saves messages to Redis list
* Publishes/receives messages
* Loads chat history

**message.py**

* Defines message schema (sender, text, timestamp)

---

## ⭐ 3. REDIS / MEMURAI MEMORY STORE

Stores data **in-memory** for ultra-fast operations.

### Responsibilities:

* Cache chat messages
* Handle Pub/Sub communication
* Deliver messages to backend instantly

### How Redis/Memurai works here:

1. Backend receives message
2. Publishes to channel `chat_channel`
3. All subscribers (FastAPI instances) receive it
4. FastAPI pushes message to connected WebSocket clients

---

# 🔁 END‑TO‑END DATA FLOW

### ✔ Step 1 — User sends message on React

React → WebSocket → FastAPI

### ✔ Step 2 — FastAPI publishes to Redis

FastAPI → Redis Pub/Sub

### ✔ Step 3 — Redis broadcasts

Redis → FastAPI (subscriber)

### ✔ Step 4 — FastAPI sends to all connected clients

FastAPI → All WebSocket clients

### ✔ Step 5 — React updates instantly

UI refreshes immediately without reload.

---

# 📂 DETAILED RESPONSIBILITIES (File-by-file)

## FRONTEND

| File                | Description                                 |
| ------------------- | ------------------------------------------- |
| `App.jsx`           | Main layout, renders chat window + input    |
| `ChatWindow.jsx`    | Displays messages coming from WebSocket     |
| `MessageInput.jsx`  | Allows users to type/send messages          |
| `MessageBubble.jsx` | UI container for each message               |
| `api.js`            | REST API calls (load history, send message) |
| `websocket.js`      | WebSocket connection logic                  |
| `chat.css`          | Styles for chat interface                   |

---

## BACKEND

| File              | Description                            |
| ----------------- | -------------------------------------- |
| `main.py`         | FastAPI app. REST + WebSocket logic    |
| `redis_client.py` | Connection to Redis/Memurai            |
| `chat_service.py` | Publish, subscribe, save/load messages |
| `user_service.py` | (Optional) handles user login/IDs      |
| `message.py`      | Message schema model                   |

---

## REDIS

| File                     | Description                            |
| ------------------------ | -------------------------------------- |
| `redis_client.py`        | Connection to Redis/Memurai            |
| `publisher.py`           | Publishes messages to Redis channels   |
| `subscriber.py`          | Subscribes/listens to Redis channels   |
| `message_model.py`       | Creates consistent chat message format |

---

# 🛠 HOW TO RUN THE PROJECT LOCALLY

## Backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend

```
cd frontend
npm install
npm run dev
```

## Redis/Memurai

### For Windows (Memurai):

* Install Memurai
* Run using: `memurai.exe`

### For Linux/Mac (Redis):

```
redis-server
```

---

# 🙌 WHY THIS STRUCTURE IS GOOD

* Very clean separation of concerns
* Frontend, backend, and storage all isolated
* Easy collaboration for multi-person teams
* Suitable for both learning and scaling later
* Works with Redis or Memurai (Windows-compatible)

---

# END OF DOCUMENT

Let me know if you want:

* Full code templates
* Diagrams
* Team roles for 6 members
* Full markdown README styling with emojis and table of contents
