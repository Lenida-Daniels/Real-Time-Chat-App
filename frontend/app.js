document.addEventListener("DOMContentLoaded", () => {
  const chatMessages = document.getElementById('chat-messages');
  const chatsList = document.getElementById('chats-list');
  const msgInput = document.getElementById('message-input');
  const imageInput = document.getElementById('image-input');
  const sendBtn = document.getElementById('send-btn');
  const voiceBtn = document.getElementById('voice-btn');
  const attachBtn = document.querySelector('.attach-btn');
  const typingStatus = document.getElementById('typing-status');

  // Configuration
  const API_BASE_URL = 'http://localhost:8000';
  const WS_URL = 'ws://localhost:8000/ws/chat';
  const CHANNEL = 'general';
  
  console.log('🚀 Chat app starting...');
  console.log('API Base URL:', API_BASE_URL);
  console.log('WebSocket URL:', WS_URL);
  
  // User authentication management
  let currentUser = null;
  let username = null;
  
  // Check if user is authenticated
  function checkAuthentication() {
    const userData = localStorage.getItem('chat_user');
    
    if (!userData) {
      // Redirect to authentication page
      window.location.href = 'auth.html';
      return false;
    }
    
    try {
      currentUser = JSON.parse(userData);
      username = currentUser.username;
      return true;
    } catch (error) {
      console.error('Error parsing user data:', error);
      localStorage.removeItem('chat_user');
      window.location.href = 'auth.html';
      return false;
    }
  }
  
  // User will be set after authentication check
  
  // WebSocket connection
  let websocket = null;
  let isConnected = false;
  let typingTimer = null;

  // Sample contacts (will be populated from API)
  let contacts = [
    { name: "Group Chat", avatar: "https://i.pravatar.cc/50?img=5", lastMessage: "Welcome to the chat!", time: "now", online: true, isGroup: true },
  ];
  
  let onlineUsers = [];

  // WebSocket connection management
  function connectWebSocket() {
    const wsUrl = `${WS_URL}?username=${encodeURIComponent(username)}&channel=${CHANNEL}`;
    console.log('Attempting to connect to:', wsUrl);
    
    try {
      websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log('✅ Connected to chat server');
        isConnected = true;
        updateConnectionStatus(true);
        loadChatHistory();
        loadOnlineUsers();
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 Received message:', data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };
      
      websocket.onclose = (event) => {
        console.log('🔌 Disconnected from chat server. Code:', event.code, 'Reason:', event.reason);
        isConnected = false;
        updateConnectionStatus(false);
        
        // Don't reconnect if it was a clean close
        if (event.code !== 1000) {
          console.log('🔄 Attempting to reconnect in 3 seconds...');
          setTimeout(connectWebSocket, 3000);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        isConnected = false;
        updateConnectionStatus(false);
        showNotification('Connection error. Check if backend is running on port 8000.');
      };
      
    } catch (error) {
      console.error('❌ Error creating WebSocket connection:', error);
      showNotification('Failed to create WebSocket connection.');
      setTimeout(connectWebSocket, 3000);
    }
  }
  
  // Handle incoming WebSocket messages
  function handleWebSocketMessage(data) {
    switch (data.type) {
      case 'message':
        // Only display messages from other users to avoid duplicates
        if (data.sender !== username) {
          displayMessage({
            text: data.content,
            image: data.message_type === 'image' ? data.content : null,
            audio: data.message_type === 'audio' ? data.content : null,
            timestamp: new Date(data.timestamp),
            sent: false,
            sender: data.sender,
            message_type: data.message_type
          });
        }
        break;
        
      case 'user_joined':
        if (data.username !== username) {
          showNotification(`${data.username} joined the chat`);
          loadOnlineUsers();
        }
        break;
        
      case 'user_left':
        if (data.username !== username) {
          showNotification(`${data.username} left the chat`);
          loadOnlineUsers();
        }
        break;
        
      case 'typing_status':
        if (data.username !== username) {
          updateTypingStatus(data.username, data.is_typing);
        }
        break;
        
      case 'message_deleted':
        removeMessage(data.message_id);
        break;
        
      default:
        console.log('Unknown message type:', data.type);
    }
  }
  
  // Update connection status in UI
  function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('typing-status');
    if (connected) {
      statusElement.textContent = `✅ Connected as ${username}`;
      statusElement.style.color = 'rgba(255,255,255,0.8)';
      statusElement.style.cursor = 'pointer';
      statusElement.onclick = changeUsername;
    } else {
      statusElement.textContent = '🔄 Connecting... (Check console for errors)';
      statusElement.style.color = '#ff6b6b';
      statusElement.style.cursor = 'pointer';
      statusElement.onclick = () => {
        console.log('Manual reconnection attempt...');
        connectWebSocket();
      };
    }
  }
  
  // Function to logout
  function logout() {
    if (confirm('Are you sure you want to logout?')) {
      localStorage.removeItem('chat_user');
      if (websocket) {
        websocket.close();
      }
      window.location.href = 'auth.html';
    }
  }
  
  // Make functions global
  window.logout = logout;
  window.openProfileSettings = openProfileSettings;
  window.openGroupSettings = openGroupSettings;
  window.closeModal = closeModal;
  
  // Modal functions
  function openProfileSettings() {
    // Populate current user data
    document.getElementById('profile-display-name').value = currentUser.display_name || '';
    document.getElementById('profile-avatar').value = currentUser.avatar_url || '';
    document.getElementById('profile-phone').value = currentUser.phone_number || '';
    
    document.getElementById('profile-modal').style.display = 'flex';
  }
  
  function openGroupSettings() {
    // For now, use default group settings
    document.getElementById('group-name').value = 'Group Chat';
    document.getElementById('group-description').value = 'General discussion group';
    document.getElementById('group-image').value = 'https://i.pravatar.cc/150?u=group';
    
    document.getElementById('group-modal').style.display = 'flex';
  }
  
  function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
  }
  
  // Profile form handler
  document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const displayName = document.getElementById('profile-display-name').value.trim();
    const avatarUrl = document.getElementById('profile-avatar').value.trim();
    const phoneNumber = document.getElementById('profile-phone').value.trim();
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/profile/${currentUser.username}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          display_name: displayName,
          avatar_url: avatarUrl,
          phone_number: phoneNumber
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Update local user data
        currentUser = { ...currentUser, ...data.user };
        localStorage.setItem('chat_user', JSON.stringify(currentUser));
        
        // Update UI
        document.querySelector('.user-info span').textContent = currentUser.display_name;
        document.querySelector('.profile-pic').src = currentUser.avatar_url;
        
        showNotification('Profile updated successfully!');
        closeModal('profile-modal');
      } else {
        showNotification(data.message || 'Failed to update profile');
      }
      
    } catch (error) {
      console.error('Error updating profile:', error);
      showNotification('Error updating profile. Please try again.');
    }
  });
  
  // Group form handler
  document.getElementById('group-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const groupName = document.getElementById('group-name').value.trim();
    const groupDescription = document.getElementById('group-description').value.trim();
    const groupImage = document.getElementById('group-image').value.trim();
    
    try {
      // For now, just update the UI (you can implement actual group update later)
      document.querySelector('.contact-details h3').textContent = groupName;
      document.querySelector('.contact-pic').src = groupImage || 'https://i.pravatar.cc/40?u=group';
      
      showNotification('Group settings updated!');
      closeModal('group-modal');
      
    } catch (error) {
      console.error('Error updating group:', error);
      showNotification('Error updating group. Please try again.');
    }
  });
  
  // Close modal when clicking outside
  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      e.target.style.display = 'none';
    }
  });
  
  // Initialize chat list
  function initializeChatList() {
    chatsList.innerHTML = '';
    contacts.forEach((contact, index) => {
      const chatItem = document.createElement('div');
      chatItem.className = `chat-item ${index === 0 ? 'active' : ''}`;
      chatItem.innerHTML = `
        <img src="${contact.avatar}" alt="${contact.name}" class="chat-avatar">
        <div class="chat-info">
          <div class="chat-name">${contact.name}</div>
          <div class="chat-last-message">${contact.lastMessage}</div>
        </div>
        <div class="chat-time">${contact.time}</div>
      `;
      chatsList.appendChild(chatItem);
    });
    
    // Add online users section
    if (onlineUsers.length > 0) {
      const onlineSection = document.createElement('div');
      onlineSection.innerHTML = `
        <div style="padding: 10px 16px; color: rgba(255,255,255,0.7); font-size: 12px; font-weight: bold;">
          ONLINE (${onlineUsers.length})
        </div>
      `;
      chatsList.appendChild(onlineSection);
      
      onlineUsers.forEach(user => {
        if (user.username !== username) {
          const userItem = document.createElement('div');
          userItem.className = 'chat-item';
          userItem.innerHTML = `
            <img src="https://i.pravatar.cc/50?u=${user.username}" alt="${user.username}" class="chat-avatar">
            <div class="chat-info">
              <div class="chat-name">${user.username}</div>
              <div class="chat-last-message">Online</div>
            </div>
            <div class="chat-time">🟢</div>
          `;
          chatsList.appendChild(userItem);
        }
      });
    }
  }

  // API functions
  async function loadChatHistory() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/history/${CHANNEL}`);
      const data = await response.json();
      
      // Clear existing messages
      chatMessages.innerHTML = '';
      
      // Display messages
      data.messages.forEach(message => {
        displayMessage({
          text: message.content,
          timestamp: new Date(message.timestamp),
          sent: message.sender === username,
          sender: message.sender,
          message_type: message.message_type,
          message_id: message.message_id
        });
      });
      
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }
  
  async function loadOnlineUsers() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/online/${CHANNEL}`);
      const data = await response.json();
      onlineUsers = data.online_users || [];
      initializeChatList();
    } catch (error) {
      console.error('Error loading online users:', error);
    }
  }
  
  // Display message function
  function displayMessage(msg) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${msg.sent ? 'sent' : ''}`;
    if (msg.message_id) {
      messageDiv.setAttribute('data-message-id', msg.message_id);
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Add sender name for received messages
    if (!msg.sent && msg.sender) {
      const senderDiv = document.createElement('div');
      senderDiv.style.fontSize = '12px';
      senderDiv.style.fontWeight = 'bold';
      senderDiv.style.marginBottom = '4px';
      senderDiv.style.color = msg.sent ? 'rgba(255,255,255,0.8)' : '#6c5ce7';
      senderDiv.textContent = msg.sender;
      bubble.appendChild(senderDiv);
    }
    
    if (msg.text) {
      const textDiv = document.createElement('div');
      textDiv.textContent = msg.text;
      bubble.appendChild(textDiv);
    }
    
    if (msg.image) {
      const img = document.createElement('img');
      img.src = msg.image;
      img.style.maxWidth = '200px';
      img.style.borderRadius = '8px';
      img.style.marginTop = '4px';
      bubble.appendChild(img);
    }
    
    if (msg.audio) {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = msg.audio;
      audio.style.marginTop = '4px';
      bubble.appendChild(audio);
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date(msg.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    bubble.appendChild(timeDiv);
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.parentElement.scrollTop = chatMessages.parentElement.scrollHeight;
  }

  // Send message function
  function sendMessage() {
    const text = msgInput.value.trim();
    if (!text && !imageInput.files[0]) return;
    
    if (!isConnected) {
      showNotification('Not connected to server. Please wait...');
      return;
    }
    
    if (text) {
      // Display message immediately for better UX
      displayMessage({
        text: text,
        timestamp: new Date(),
        sent: true,
        sender: username,
        message_type: 'text'
      });
      
      // Send via WebSocket
      const message = {
        type: 'message',
        sender: username,
        content: text,
        channel: CHANNEL,
        message_type: 'text'
      };
      
      websocket.send(JSON.stringify(message));
      msgInput.value = '';
      
      // Stop typing indicator
      sendTypingStatus(false);
    }
    
    if (imageInput.files[0]) {
      const file = imageInput.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        // Display image immediately
        displayMessage({
          image: reader.result,
          timestamp: new Date(),
          sent: true,
          sender: username,
          message_type: 'image'
        });
        
        const message = {
          type: 'message',
          sender: username,
          content: reader.result,
          channel: CHANNEL,
          message_type: 'image'
        };
        
        websocket.send(JSON.stringify(message));
      };
      reader.readAsDataURL(file);
      imageInput.value = '';
    }
    
    // Show voice button when input is empty
    toggleSendVoiceButton();
  }
  
  // Send typing status
  function sendTypingStatus(isTyping) {
    if (!isConnected) return;
    
    const message = {
      type: isTyping ? 'typing_start' : 'typing_stop',
      sender: username,
      channel: CHANNEL
    };
    
    websocket.send(JSON.stringify(message));
  }
  
  // Update typing status display
  function updateTypingStatus(username, isTyping) {
    const statusElement = document.getElementById('typing-status');
    
    if (isTyping) {
      statusElement.textContent = `${username} is typing...`;
    } else {
      statusElement.textContent = 'Connected - Click here for group info';
    }
  }
  
  // Show notification
  function showNotification(message) {
    // Create a simple notification
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #6c5ce7;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 1000;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
  }
  
  // Remove message from UI
  function removeMessage(messageId) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (messageElement) {
      messageElement.remove();
    }
  }

  // Toggle between send and voice button
  function toggleSendVoiceButton() {
    if (msgInput.value.trim()) {
      sendBtn.style.display = 'flex';
      voiceBtn.style.display = 'none';
    } else {
      sendBtn.style.display = 'none';
      voiceBtn.style.display = 'flex';
    }
  }

  // Event listeners
  msgInput.addEventListener('input', () => {
    toggleSendVoiceButton();
    
    // Send typing indicator
    if (isConnected) {
      sendTypingStatus(true);
      
      // Clear previous timer
      if (typingTimer) {
        clearTimeout(typingTimer);
      }
      
      // Stop typing after 2 seconds of inactivity
      typingTimer = setTimeout(() => {
        sendTypingStatus(false);
      }, 2000);
    }
  });

  msgInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  attachBtn.addEventListener('click', () => {
    imageInput.click();
  });

  // Voice recording
  let mediaRecorder;
  let isRecording = false;
  
  voiceBtn.addEventListener('click', async () => {
    if (!isConnected) {
      showNotification('Not connected to server. Please wait...');
      return;
    }
    
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        const chunks = [];
        
        mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
        mediaRecorder.onstop = () => {
          const blob = new Blob(chunks, { type: 'audio/webm' });
          const reader = new FileReader();
          reader.onload = () => {
            // Display audio message immediately
            displayMessage({
              audio: reader.result,
              timestamp: new Date(),
              sent: true,
              sender: username,
              message_type: 'audio'
            });
            
            const message = {
              type: 'message',
              sender: username,
              content: reader.result,
              channel: CHANNEL,
              message_type: 'audio'
            };
            
            websocket.send(JSON.stringify(message));
          };
          reader.readAsDataURL(blob);
          stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        voiceBtn.style.backgroundColor = '#ff4444';
        voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
        
        // Auto stop after 60 seconds
        setTimeout(() => {
          if (isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            voiceBtn.style.backgroundColor = '#6c5ce7';
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
          }
        }, 60000);
        
      } catch (error) {
        console.error('Error accessing microphone:', error);
        showNotification('Could not access microphone. Please check permissions.');
      }
    } else {
      mediaRecorder.stop();
      isRecording = false;
      voiceBtn.style.backgroundColor = '#6c5ce7';
      voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
  });

  // Initialize application
  async function initializeApp() {
    // Check authentication first
    if (!checkAuthentication()) {
      return; // Will redirect to auth page
    }
    
    initializeChatList();
    toggleSendVoiceButton();
    connectWebSocket();
    
    // Update profile info
    document.querySelector('.user-info span').textContent = currentUser.display_name || currentUser.username;
    document.querySelector('.profile-pic').src = currentUser.avatar_url;
    
    // Show welcome message and test backend connection
    setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();
        console.log('✅ Backend API test successful:', data);
        showNotification(`Welcome back, ${currentUser.display_name || currentUser.username}!`);
      } catch (error) {
        console.error('❌ Backend API test failed:', error);
        showNotification('Warning: Cannot reach backend API. Check if server is running.');
      }
    }, 1000);
  }
  
  // Handle page visibility change to manage connection
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      // Page is hidden, could pause some activities
    } else {
      // Page is visible, ensure connection is active
      if (!isConnected) {
        connectWebSocket();
      }
    }
  });
  
  // Handle page unload
  window.addEventListener('beforeunload', () => {
    if (websocket && isConnected) {
      websocket.close();
    }
  });
  
  // Start the application
  initializeApp();
});
