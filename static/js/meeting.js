const socket = io();

// State
let localStream;
let roomId;
let peers = {}; // sid -> RTCPeerConnection
let isAudioMuted = false;
let isVideoMuted = false;

// DOM Elements
const joinScreen = document.getElementById('join-screen');
const meetingScreen = document.getElementById('meeting-screen');
const joinBtn = document.getElementById('joinBtn');
const roomInput = document.getElementById('roomInput');
const videoGrid = document.getElementById('video-grid');
const localVideo = document.getElementById('localVideo');
const previewVideo = document.getElementById('previewVideo');

// Controls
const micBtn = document.getElementById('micBtn');
const camBtn = document.getElementById('camBtn');
const previewMicBtn = document.getElementById('previewMicBtn');
const previewCamBtn = document.getElementById('previewCamBtn');

const ICE_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// --- Initialization & Preview ---

async function initPreview() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        updateMediaUI('video', true);
        updateMediaUI('audio', true);
    } catch (error) {
        console.warn('Could not access media devices.', error);
        
        try {
            // Attempt #2: Audio Only
            localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
            isVideoMuted = true;
            updateMediaUI('video', false);
            updateMediaUI('audio', true);
        } catch (e2) {
            console.error('No media devices found.', e2);
            alert('No microphone or camera found. You will join in View-Only mode!');
            localStream = null;
        }
    }

    if (localStream) {
        previewVideo.srcObject = localStream;
        localVideo.srcObject = localStream;
    }
}

initPreview();

// --- Controls ---

function toggleAudio() {
    if (!localStream) return;
    isAudioMuted = !isAudioMuted;
    localStream.getAudioTracks()[0].enabled = !isAudioMuted;
    updateMediaUI('audio', !isAudioMuted);
}

function toggleVideo() {
    if (!localStream) return;
    isVideoMuted = !isVideoMuted;
    localStream.getVideoTracks()[0].enabled = !isVideoMuted;
    updateMediaUI('video', !isVideoMuted);
}

function updateMediaUI(type, active) {
    if (type === 'audio') {
        const icon = active ? 'mic' : 'mic_off';
        [micBtn, previewMicBtn].forEach(btn => {
            if (btn) {
                btn.classList.toggle('active', active);
                btn.querySelector('span').innerText = icon;
            }
        });
    } else {
        const icon = active ? 'videocam' : 'videocam_off';
        [camBtn, previewCamBtn].forEach(btn => {
            if (btn) {
                btn.classList.toggle('active', active);
                btn.querySelector('span').innerText = icon;
            }
        });
        
        // Handle the "Camera is off" overlay in lobby
        const label = document.getElementById('no-preview-label');
        if (label) {
            label.style.display = active ? 'none' : 'flex';
        }
    }
}

// --- Join Event ---

joinBtn.addEventListener('click', () => {
    roomId = roomInput.value.trim();
    if (!roomId) return;

    // Switch Screens
    joinScreen.classList.add('hidden');
    meetingScreen.classList.add('active');

    // Emit Join event
    socket.emit('join_meeting', { room: roomId });
});

// --- WebRTC Core ---

socket.on('user-joined', async (data) => {
    const peerSid = data.sid;
    console.log('User joined:', peerSid);
    
    addVideoElement(peerSid, null);
    
    const pc = createPeerConnection(peerSid);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    
    socket.emit('signal', {
        room: roomId,
        to: peerSid,
        data: pc.localDescription
    });
});

socket.on('signal', async (message) => {
    const peerSid = message.sid;
    const signalData = message.data;
    if (peerSid === socket.id) return;
    
    let pc = peers[peerSid];
    if (!pc) {
        addVideoElement(peerSid, null);
        pc = createPeerConnection(peerSid);
    }

    if (signalData.type === 'offer') {
        await pc.setRemoteDescription(new RTCSessionDescription(signalData));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        socket.emit('signal', { room: roomId, to: peerSid, data: pc.localDescription });
    } else if (signalData.type === 'answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(signalData));
    } else if (signalData.candidate) {
        try {
            await pc.addIceCandidate(new RTCIceCandidate(signalData));
        } catch (e) {
            console.error('ICE candidate error', e);
        }
    }
});

function createPeerConnection(peerSid) {
    const pc = new RTCPeerConnection(ICE_SERVERS);
    peers[peerSid] = pc;

    if (localStream) {
        localStream.getTracks().forEach(track => pc.addTrack(track, localStream));
    }

    pc.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('signal', { room: roomId, to: peerSid, data: event.candidate });
        }
    };

    pc.ontrack = event => {
        addVideoElement(peerSid, event.streams[0]);
    };

    pc.oniceconnectionstatechange = () => {
        if (['disconnected', 'failed', 'closed'].includes(pc.iceConnectionState)) {
            removeVideoElement(peerSid);
            pc.close();
            delete peers[peerSid];
        }
    };

    return pc;
}

// --- Dynamic UI ---

function addVideoElement(peerSid, stream) {
    let wrapper = document.getElementById(`container-${peerSid}`);
    if (wrapper) {
        if (stream) wrapper.querySelector('video').srcObject = stream;
        return;
    }

    wrapper = document.createElement('div');
    wrapper.className = 'video-wrapper';
    wrapper.id = `container-${peerSid}`;

    const video = document.createElement('video');
    video.id = `video-${peerSid}`;
    video.autoplay = true;
    video.playsInline = true;
    if (stream) video.srcObject = stream;

    const label = document.createElement('div');
    label.className = 'user-tag';
    label.innerText = `Guest User`;

    wrapper.appendChild(video);
    wrapper.appendChild(label);
    videoGrid.appendChild(wrapper);
}

function removeVideoElement(peerSid) {
    const wrapper = document.getElementById(`container-${peerSid}`);
    if (wrapper) wrapper.remove();
}
