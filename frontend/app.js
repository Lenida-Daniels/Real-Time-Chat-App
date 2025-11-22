document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById('chat-form');
  const chatMessages = document.getElementById('chat-messages');
  const usersList = document.getElementById('users-list');
  const msgInput = document.getElementById('message-input');
  const imageInput = document.getElementById('image-input');
  const voiceBtn = document.getElementById('voice-btn');
  const typingIndicator = document.getElementById('typing-indicator');

  const username = "You";
  const avatar = "https://i.pravatar.cc/40?img=1";

  // 15 custom users with avatars
  const userNames = [
    "Hattie","Zoey","Joy","Shalom","Blessed",
    "Rutherford","Willy","Henry","Job","Joe",
    "May","Judy","Smith","Seth","Tabitha"
  ];

  const users = userNames.map((name, index) => ({
    name: name,
    avatar: `https://i.pravatar.cc/40?img=${index+1}`,
    lastSeen: new Date()
  }));

  // Render sidebar with users
  function updateUsersList() {
    usersList.innerHTML = '';
    users.forEach(u => {
      const li = document.createElement('li');
      const img = document.createElement('img');
      img.src = u.avatar;
      const span = document.createElement('span');
      span.innerText = `${u.name} (Last: ${u.lastSeen.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})})`;
      li.appendChild(img);
      li.appendChild(span);
      usersList.appendChild(li);
    });
  }
  updateUsersList();

  // Typing indicator
  msgInput.addEventListener('input', () => {
    typingIndicator.innerText = `You are typing...`;
    setTimeout(() => typingIndicator.innerText = '', 2000);
  });

  // Display message function
  function displayMessage(msg) {
    const div = document.createElement('div');
    div.classList.add('message');
    if(msg.you) div.classList.add('you');

    const avatarImg = document.createElement('img');
    avatarImg.src = msg.avatar;
    avatarImg.classList.add('avatar');

    const bubble = document.createElement('div');
    bubble.classList.add('bubble');

    if(msg.text) bubble.innerText = msg.text;
    if(msg.image){
      const img = document.createElement('img');
      img.src = msg.image;
      bubble.appendChild(img);
    }
    if(msg.audio){
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = msg.audio;
      bubble.appendChild(audio);
    }

    const time = document.createElement('span');
    time.classList.add('time');
    time.innerText = new Date(msg.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    bubble.appendChild(time);

    div.appendChild(avatarImg);
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Send text/image
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = msgInput.value.trim();
    if(!text && !imageInput.files[0]) return;

    if(text){
      displayMessage({sender:username, avatar:avatar, text, timestamp:new Date(), you:true});
      msgInput.value='';
    }

    if(imageInput.files[0]){
      const file = imageInput.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        displayMessage({sender:username, avatar:avatar, image:reader.result, timestamp:new Date(), you:true});
      };
      reader.readAsDataURL(file);
      imageInput.value='';
    }
  });

  // Voice recording (5 seconds)
  let mediaRecorder;
  voiceBtn.addEventListener('click', async () => {
    if(!mediaRecorder || mediaRecorder.state === 'inactive'){
      const stream = await navigator.mediaDevices.getUserMedia({audio:true});
      mediaRecorder = new MediaRecorder(stream);
      const chunks = [];
      mediaRecorder.ondataavailable = e => chunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks,{type:'audio/mp3'});
        const reader = new FileReader();
        reader.onload = () => {
          displayMessage({sender:username, avatar:avatar, audio:reader.result, timestamp:new Date(), you:true});
        };
        reader.readAsDataURL(blob);
      };
      mediaRecorder.start();
      setTimeout(()=> mediaRecorder.stop(),5000);
    }
  });

  // Demo: random messages from other users
  setInterval(() => {
    const u = users[Math.floor(Math.random() * users.length)];
    u.lastSeen = new Date();
    updateUsersList();
    displayMessage({sender:u.name, avatar:u.avatar, text:`Hello from ${u.name}`, timestamp:new Date(), you:false});
  }, 4000);
});
