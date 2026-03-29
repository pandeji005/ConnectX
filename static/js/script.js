// ============================================================
// THEME — Apply instantly (no flicker) — also called from inline script
// ============================================================
function applyTheme(theme) {
    const isDark = (theme === 'dark');
    if (isDark) {
        document.body.classList.add('dark-mode');
        document.documentElement.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
        document.documentElement.classList.remove('dark-mode');
    }
    // Clean up any anti-flicker classes
    document.body.classList.remove('dark-mode-pending');
    document.documentElement.classList.remove('dark-mode-pending');
}

// ============================================================
// DOMContentLoaded — Wire up all interactive elements
// ============================================================
document.addEventListener('DOMContentLoaded', function () {

    // --- Theme Toggle ---
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    const themeButtons = document.querySelectorAll('.theme-toggle');
    themeButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const isDark = !document.body.classList.contains('dark-mode');
            const newTheme = isDark ? 'dark' : 'light';
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    });

    // --- Sidebar Collapse/Expand (VSCode style) ---
    const sidebar = document.getElementById('app-sidebar');
    const collapseBtn = document.getElementById('sidebar-collapse-btn');

    if (sidebar) {
        // Restore sidebar state
        const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (sidebarCollapsed) sidebar.classList.add('collapsed');

        if (collapseBtn) {
            collapseBtn.addEventListener('click', function () {
                sidebar.classList.toggle('collapsed');
                localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
            });
        }

        // Click logo when collapsed → expand
        const sidebarLogo = document.getElementById('sidebar-logo');
        if (sidebarLogo) {
            sidebarLogo.addEventListener('click', function () {
                if (sidebar.classList.contains('collapsed')) {
                    sidebar.classList.remove('collapsed');
                    localStorage.setItem('sidebarCollapsed', 'false');
                }
            });
        }
    }

    // --- Password Toggle (eye icon) ---
    document.querySelectorAll('.password-toggle').forEach(btn => {
        btn.addEventListener('click', function () {
            const input = this.closest('.password-wrapper').querySelector('input');
            const isHidden = input.type === 'password';
            input.type = isHidden ? 'text' : 'password';
            // swap icon
            this.querySelector('.eye-open').style.display = isHidden ? 'none' : 'block';
            this.querySelector('.eye-closed').style.display = isHidden ? 'block' : 'none';
        });
    });

    // --- Global Chat: Enter to send ---
    const chatInput = document.getElementById('global-chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendGlobalMessage();
        });

        // @mention autocomplete
        chatInput.addEventListener('input', handleMentionInput);
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeMentionDropdown();
        });
    }

    // --- Bot Chat Enter ---
    const botInput = document.getElementById('bot-chat-input');
    if (botInput) {
        botInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendBotMessage();
        });
    }

    // Scroll global chat to bottom
    const msgArea = document.getElementById('global-messages');
    if (msgArea) msgArea.scrollTop = msgArea.scrollHeight;

    // --- Hero Carousel ---
    initCarousel();

    // --- Notify dropdown close on outside click ---
    document.addEventListener('click', function(e) {
        const drop = document.getElementById('notif-drop');
        if (drop && !drop.contains(e.target) && !e.target.closest('[data-notif-toggle]')) {
            drop.classList.add('hidden');
        }
        // close mention dropdown
        const mentionDrop = document.getElementById('mention-dropdown');
        if (mentionDrop && !mentionDrop.contains(e.target) && e.target !== chatInput) {
            closeMentionDropdown();
        }
        // close profile dropdown
        const profileDropdown = document.getElementById('profile-dropdown');
        if (profileDropdown && !profileDropdown.contains(e.target) && e.target.id !== 'profile-drop-toggle') {
            profileDropdown.classList.remove('show');
        }
    });

    // --- Profile Dropdown Toggle ---
    const profileToggle = document.getElementById('profile-drop-toggle');
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileToggle && profileDropdown) {
        profileToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('show');
        });
    }
});

// ============================================================
// HERO CAROUSEL
// ============================================================
let carouselIndex = 0;
let carouselTimer = null;

function initCarousel() {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.carousel-dot');
    if (!slides.length) return;

    function showSlide(idx) {
        slides.forEach((s, i) => {
            s.classList.toggle('active', i === idx);
        });
        dots.forEach((d, i) => {
            d.classList.toggle('active', i === idx);
        });
        carouselIndex = idx;
    }

    showSlide(0);
    carouselTimer = setInterval(() => {
        showSlide((carouselIndex + 1) % slides.length);
    }, 3200);

    // Dots clickable
    dots.forEach((dot, i) => {
        dot.addEventListener('click', () => {
            clearInterval(carouselTimer);
            showSlide(i);
            carouselTimer = setInterval(() => {
                showSlide((carouselIndex + 1) % slides.length);
            }, 3200);
        });
    });
}

// ============================================================
// AI BOT CHAT
// ============================================================
let lastSender = null;
let isChatOpen = false;

function toggleChat() {
    const chatbox = document.getElementById('chatbox');
    isChatOpen = !isChatOpen;
    if (isChatOpen) {
        chatbox.classList.add('show');
        showGreeting();
    } else {
        chatbox.classList.remove('show');
    }
}

function showGreeting() {
    const chatBody = document.getElementById('chat-body');
    chatBody.innerHTML = '';
    lastSender = null;
    showTyping();
    setTimeout(() => {
        removeTyping();
        addBotMessage('Hi there 👋');
        showTyping();
        setTimeout(() => {
            removeTyping();
            addBotMessage('Welcome to ConnectX! How can I help you today?');
            addOptions();
        }, 700);
    }, 700);
}

function addBotMessage(text) {
    const chatBody = document.getElementById('chat-body');
    let wrapper;
    if (lastSender !== 'bot') {
        wrapper = document.createElement('div');
        wrapper.className = 'message-block';
        wrapper.innerHTML = `
          <div class="message-row bot">
            <div class="avatar bot-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1" fill="currentColor"/></svg>
            </div>
            <div class="message-group"><div class="messages"></div></div>
          </div>
          <div class="timestamp" style="margin-left:44px;text-align:left;"></div>
        `;
        chatBody.appendChild(wrapper);
    } else {
        wrapper = chatBody.lastElementChild;
    }
    const msg = document.createElement('div');
    msg.className = 'bot-message';
    msg.innerHTML = text;
    wrapper.querySelector('.messages').appendChild(msg);
    wrapper.querySelector('.timestamp').innerText = getTime();
    lastSender = 'bot';
    chatBody.scrollTop = chatBody.scrollHeight;
}

function addUserMessage(text) {
    const chatBody = document.getElementById('chat-body');
    let wrapper;
    if (lastSender !== 'user') {
        wrapper = document.createElement('div');
        wrapper.className = 'message-block';
        wrapper.innerHTML = `
          <div class="message-row user">
            <div class="message-group"><div class="messages"></div></div>
            <div class="avatar user-avatar" style="background:rgba(35,131,226,0.15);color:#2383e2;font-weight:600;font-size:12px;">U</div>
          </div>
          <div class="timestamp" style="margin-right:44px;text-align:right;"></div>
        `;
        chatBody.appendChild(wrapper);
    } else {
        wrapper = chatBody.lastElementChild;
    }
    const msg = document.createElement('div');
    msg.className = 'user-message';
    msg.innerText = text;
    wrapper.querySelector('.messages').appendChild(msg);
    wrapper.querySelector('.timestamp').innerText = getTime();
    lastSender = 'user';
    chatBody.scrollTop = chatBody.scrollHeight;
}

function getTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function addOptions() {
    const chatBody = document.getElementById('chat-body');
    let options = [
        { label: 'View Tasks', value: 'view_tasks' },
        { label: 'Add Task', value: 'add_task' },
        { label: 'Delete Task', value: 'delete_task' },
        { label: 'Project Status', value: 'project_status' },
        { label: 'Help', value: 'help' },
        { label: 'Exit', value: 'exit' }
    ];

    // Filter options based on role
    if (window.currentUserRole === 'team_member') {
        options = options.filter(opt => !['add_task', 'delete_task'].includes(opt.value));
    }

    const container = document.createElement('div');
    container.className = 'options-container';
    options.forEach(opt => {
        const btn = document.createElement('div');
        btn.className = 'option-chip';
        btn.innerText = opt.label;
        btn.onclick = (e) => {
            e.stopPropagation();
            container.remove();
            handleUserAction(opt.label, opt.value);
        };
        container.appendChild(btn);
    });
    chatBody.appendChild(container);
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Prevent chatbox clicks from bubbling
const chatboxEl = document.getElementById('chatbox');
if (chatboxEl) chatboxEl.addEventListener('click', e => e.stopPropagation());

function handleUserAction(label, action) {
    if (label !== null) addUserMessage(label);
    showTyping();
    fetch('/chat-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
    })
    .then(res => res.json())
    .then(data => {
        setTimeout(() => {
            removeTyping();
            
            // Handle specialized commands from backend
            if (typeof data.response === 'string' && data.response.startsWith('COMMAND:')) {
                const cmd = data.response.replace('COMMAND:', '');
                
                if (cmd.startsWith('REDIRECT:')) {
                    const url = cmd.replace('REDIRECT:', '');
                    addBotMessage("🚀 Redirecting you to the reports page...");
                    setTimeout(() => window.location.href = url, 1200);
                    return;
                }
                
                if (cmd === 'MODAL:ADD_TASK') {
                    addBotMessage("📝 I've opened the task creation window for you.");
                    showAddTaskModal();
                } else if (cmd === 'MODAL:DELETE_TASK') {
                    addBotMessage("🗑️ I've opened the task deletion window for you.");
                    showDeleteTaskModal();
                } else if (cmd === 'MODAL:VIEW_PROJECT_TASKS') {
                    addBotMessage("📋 I've opened the viewer so you can check any project's tasks.");
                    showViewProjectTasksModal();
                }
            } else {
                addBotMessage(data.response);
            }

            if (action === 'exit') return;
            setTimeout(() => {
                addBotMessage('Is there anything else I can help with?');
                addOptions();
            }, 700);
        }, 800);
    });
}

function showTyping() {
    const chatBody = document.getElementById('chat-body');
    const typing = document.createElement('div');
    typing.className = 'message-row bot';
    typing.id = 'typing-indicator';
    typing.innerHTML = `
      <div class="avatar bot-avatar" style="font-size:16px;">🤖</div>
      <div class="bot-message typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>`;
    chatBody.appendChild(typing);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTyping() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
}

function sendBotMessage() {
    const input = document.getElementById('bot-chat-input');
    const text = input.value.trim();
    if (text) { handleUserAction(text, text); input.value = ''; }
}

// ============================================================
// SOCKET.IO — GLOBAL CHAT
// ============================================================
const socket = (typeof io !== 'undefined') ? io() : null;

if (socket) {
    socket.on('connect', () => {
        if (window.location.pathname === '/global_chat') {
            socket.emit('join', { room: 'global' });
        }
    });

    socket.on('receive_message', (data) => {
        if (window.location.pathname !== '/global_chat') return;
        const msgArea = document.getElementById('global-messages');
        if (!msgArea) return;
        const isMe = data.sender === (window.currentUser || '');
        // highlight @mentions
        const text = data.text.replace(/@(\w+)/g, '<span class="mention-tag">@$1</span>');
        const html = `
            <div class="msg-bubble ${isMe ? 'my-message' : 'other-message'}">
                <div class="msg-sender">${data.sender}</div>
                <div class="message-text">${text}</div>
                <div class="message-time">${data.timestamp}</div>
            </div>
            <div style="clear:both;"></div>`;
        msgArea.insertAdjacentHTML('beforeend', html);
        msgArea.scrollTop = msgArea.scrollHeight;
    });
}

function sendGlobalMessage() {
    const input = document.getElementById('global-chat-input');
    const text = input.value.trim();
    if (text && socket) {
        socket.emit('send_message', { room: 'global', project_id: null, text: text });
        input.value = '';
        closeMentionDropdown();
    }
}

// ============================================================
// @MENTION AUTOCOMPLETE
// ============================================================
let mentionUsers = [];
let mentionActive = false;
let mentionStart = -1;

function fetchUsers() {
    if (mentionUsers.length) return Promise.resolve(mentionUsers);
    return fetch('/users_list')
        .then(r => r.json())
        .then(data => { mentionUsers = data; return data; });
}

function handleMentionInput(e) {
    const input = e.target;
    const val = input.value;
    const cursor = input.selectionStart;

    // Find the @ before cursor
    let atIdx = -1;
    for (let i = cursor - 1; i >= 0; i--) {
        if (val[i] === '@') { atIdx = i; break; }
        if (val[i] === ' ') break;
    }

    if (atIdx === -1) { closeMentionDropdown(); return; }

    const query = val.substring(atIdx + 1, cursor).toLowerCase();
    mentionStart = atIdx;
    mentionActive = true;

    fetchUsers().then(users => {
        const filtered = users.filter(u => u.username.toLowerCase().startsWith(query));
        if (!filtered.length) { closeMentionDropdown(); return; }
        showMentionDropdown(filtered);
    });
}

function showMentionDropdown(users) {
    let drop = document.getElementById('mention-dropdown');
    if (!drop) return;
    drop.innerHTML = '';
    users.forEach(u => {
        const item = document.createElement('div');
        item.className = 'mention-item';
        item.innerHTML = `<div class="mention-avatar">${u.username[0].toUpperCase()}</div><span>${u.username}</span>`;
        item.addEventListener('mousedown', (e) => {
            e.preventDefault();
            insertMention(u.username);
        });
        drop.appendChild(item);
    });
    drop.classList.add('visible');
}

function insertMention(username) {
    const input = document.getElementById('global-chat-input');
    const val = input.value;
    const cursor = input.selectionStart;
    const before = val.substring(0, mentionStart);
    const after = val.substring(cursor);
    input.value = before + '@' + username + ' ' + after;
    input.focus();
    const newPos = mentionStart + username.length + 2;
    input.setSelectionRange(newPos, newPos);
    closeMentionDropdown();
}

function closeMentionDropdown() {
    const drop = document.getElementById('mention-dropdown');
    if (drop) drop.classList.remove('visible');
    mentionActive = false;
    mentionStart = -1;
}

function showAddTaskModal(projectId = null, redirectTo = null) {
    // Fetch users and projects first to populate selects
    Promise.all([
        fetch('/users_list').then(r => r.json()),
        fetch('/api/reports/data').then(r => r.json()) // Reusing this for projects list
    ]).then(([users, reportsData]) => {
        const projects = reportsData.projects;
        let userOpts = users.map(u => `<option value="${u.id}">${u.username}</option>`).join('');
        let projectOpts = projects.map(p => {
            const selected = (projectId && p.id == projectId) ? 'selected' : '';
            return `<option value="${p.id}" ${selected}>${p.title}</option>`;
        }).join('');
        
        const redirectInput = redirectTo ? `<input type="hidden" name="redirect_to" value="${redirectTo}">` : '';

        const content = `
            <div class="modal-header">
                <h3>Assign New Task</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <form action="/create_task" method="POST">
                ${redirectInput}
                <div class="modal-body">
                    <div class="modal-form-group">
                        <label>Task Title</label>
                        <input type="text" name="title" class="modal-input" placeholder="e.g. Design Homepage" required>
                    </div>
                    <div class="modal-form-group">
                        <label>Description</label>
                        <textarea name="description" class="modal-input modal-textarea" placeholder="Detailed instructions..."></textarea>
                    </div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div style="flex: 1;">
                            <label style="display:block; margin-bottom:6px; font-size:12px; font-weight:600;">Assign To (Optional)</label>
                            <select name="assigned_to" class="modal-input">
                                <option value="">Unassigned</option>
                                ${userOpts}
                            </select>
                        </div>
                        <div style="flex: 1;">
                            <label style="display:block; margin-bottom:6px; font-size:12px; font-weight:600;">Project</label>
                            <select name="project_id" class="modal-input">${projectOpts}</select>
                        </div>
                    </div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div style="flex: 1;">
                            <label style="display:block; margin-bottom:6px; font-size:12px; font-weight:600;">Deadline</label>
                            <input type="date" name="deadline" class="modal-input">
                        </div>
                        <div style="flex: 1;">
                            <label style="display:block; margin-bottom:6px; font-size:12px; font-weight:600;">Due Time</label>
                            <input type="time" name="due_time" class="modal-input">
                        </div>
                    </div>
                    <div class="modal-form-group">
                        <label>Priority</label>
                        <select name="priority" class="modal-input">
                            <option value="Low">Low</option>
                            <option value="Medium" selected>Medium</option>
                            <option value="High">High</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Task</button>
                </div>
            </form>
        `;
        openModal(content);
    });
}

function showDeleteTaskModal() {
    fetch('/api/tasks').then(r => r.json()).then(tasks => {
        if (!tasks.length) {
            addBotMessage("⚠️ You don't have any tasks that can be deleted.");
            return;
        }

        let taskOpts = tasks.map(t => `<option value="${t.id}">[ID: ${t.id}] ${t.title} (${t.status})</option>`).join('');

        const content = `
            <div class="modal-header">
                <h3>Delete Task</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <form onsubmit="event.preventDefault(); if(confirm('Are you sure you want to delete this task?')) window.location.href='/delete_task/' + document.getElementById('task-id-del').value;">
                <div class="modal-body">
                    <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">Please select the task you wish to permanently remove.</p>
                    <div class="modal-form-group">
                        <label>Select Task</label>
                        <select id="task-id-del" class="modal-input" required>
                            <option value="" disabled selected>Choose a task...</option>
                            ${taskOpts}
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-danger" style="background:#ff4444; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;">Delete Permanently</button>
                </div>
            </form>
        `;
        openModal(content);
    });
}
function showViewProjectTasksModal() {
    fetch('/api/reports/data').then(r => r.json()).then(data => {
        const projects = data.projects;
        let projectListHtml = projects.map(p => `
            <div class="project-task-item" onclick="fetchAndShowProjectTasks(${p.id}, '${p.title.replace(/'/g, "\\'")}')" 
                 style="padding: 12px; border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 8px; cursor: pointer; background: var(--hover-bg); transition: all 0.2s;">
                <div style="font-weight:600; font-size:14px; color:var(--text-color);">${p.title}</div>
                <div style="font-size:12px; color:var(--text-muted);">${p.done}/${p.total} tasks completed</div>
            </div>
        `).join('');

        const content = `
            <div class="modal-header">
                <h3>View Project Tasks</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="project-tasks-modal-body">
                <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">Select a project to view its current tasks.</p>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${projectListHtml || '<p style="text-align:center; padding:20px;">No projects found.</p>'}
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeModal()">Close</button>
            </div>
        `;
        openModal(content);
    });
}

function fetchAndShowProjectTasks(projectId, projectTitle) {
    const body = document.getElementById('project-tasks-modal-body');
    const spinner = `<div style="text-align:center; padding:40px;"><div style="margin: 0 auto 16px; width:24px; height:24px; border:3px solid var(--border-color); border-top-color:#2383e2; border-radius:50%; animation: spin 1s linear infinite;"></div>Loading tasks for ${projectTitle}...</div>`;
    body.innerHTML = spinner;
    
    fetch(`/api/project/${projectId}/tasks`)
        .then(r => r.json())
        .then(tasks => {
            const taskHtml = tasks.map(t => `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 12px; border-bottom: 1px solid var(--border-color); margin-bottom: 8px;">
                    <div style="flex: 1;">
                        <div style="font-weight:600; font-size:14px; color:var(--text-color); margin-bottom: 2px;">${t.title}</div>
                        <div style="font-size:11px; color:var(--text-muted);">Assigned to: <span style="color:#2383e2; font-weight:500;">${t.assigned_to}</span></div>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-pill ${t.status === 'Done' ? 'status-active' : ''}" style="font-size: 10px; padding: 2px 8px; border-radius: 20px; text-transform: uppercase;">${t.status}</span>
                    </div>
                </div>
            `).join('');

            body.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                    <button onclick="showViewProjectTasksModal()" class="btn-outline" style="padding: 4px 8px; font-size: 11px;">← Back</button>
                    <h4 style="margin:0; font-size:15px; color:var(--text-color);">${projectTitle}</h4>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${taskHtml || '<p style="text-align:center; padding:20px; color:var(--text-muted);">No tasks in this project yet.</p>'}
                </div>
            `;
        })
        .catch(err => {
            body.innerHTML = `<p style="color:#ff4444; text-align:center; padding:20px;">Error loading tasks. Please try again.</p>`;
        });
}
