# Real-Time-Chat-App
## Project Structure
real_time_chat_app/
│
├── backend/                         # FastAPI backend + Redis integration
│   ├── main.py                      # FastAPI WebSocket endpoints (frontend <-> Redis)
│   ├── requirements.txt             # Python dependencies for backend
│   ├── redis_layer/                 # Your Redis messaging layer
│   │   ├── redis_client.py          # Connects Python to Redis (shared connection)
│   │   ├── publisher.py             # Publishes messages to Redis channels
│   │   ├── subscriber.py            # Subscribes/listens to Redis channels
│   │   └── message_model.py         # Creates consistent chat message format
│   └── utils/                       # Optional helpers
│       └── connections.py           # Additional helper functions
│
├── frontend/                        # Frontend UI files
│   ├── index.html                   # Chat UI: input box, send button, messages list
│   ├── style.css                    # Styling for chat app
│   └── script.js                    # JS: WebSocket connection, send/receive messages
│
└── README.md                        # Overview, setup instructions, team info
