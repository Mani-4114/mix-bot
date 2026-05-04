// TODO: After deploying backend to Render, replace the URL below with your Render service URL
// e.g. 'https://mix-bot-backend.onrender.com/api'
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/api'
    : 'https://mix-bot-backend.onrender.com/api';

// State
let conversationHistory = [];
let currentChatSessionId = null;

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('mixbot_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

// DOM Elements
const recipeContainer = document.getElementById('recipe-container');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const historyList = document.getElementById('history-list');

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
});

// New Chat functionality
document.getElementById('new-chat-btn').addEventListener('click', () => {
    conversationHistory = [];
    currentChatSessionId = null;
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <p>Hello! I'm MixBot. Tell me what's in your bar, or ask me for a surprise cocktail recipe!</p>
        </div>
    `;
    recipeContainer.innerHTML = '';
    chatInput.value = '';
});

// Mix Cocktail / Chat functionality
chatSend.addEventListener('click', async (e) => {
    const text = chatInput.value.trim();
    if (!text) return;
    
    appendMessage(text, 'user-message');
    chatInput.value = '';
    
    const botMsgDiv = appendMessage("Mixing up a response...", 'bot-message');

    try {
        const req = {
            message: text,
            conversation_history: conversationHistory
        };
        const res = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(req)
        });
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || "Failed to communicate with bot");
        }
        
        let formattedText = data.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\n/g, '<br>');
        botMsgDiv.innerHTML = `<p>${formattedText}</p>`;
        
        // Don't save fallback error messages to history
        const isErrorFallback = data.text.includes("MixBot is currently taking a quick break") || data.text.includes("MixBot encountered an error");
        
        if (!isErrorFallback) {
            conversationHistory.push({ role: "user", text });
            conversationHistory.push({ role: "model", text: data.text });
            
            // Save to LocalStorage (User isolated)
            const email = localStorage.getItem("mixbot_token") ? (localStorage.getItem("mixbot_user_name") || "user") : "anon";
            const storageKey = `mixbot_chats_${email}`;
            let sessions = JSON.parse(localStorage.getItem(storageKey) || '[]');
            if (!currentChatSessionId) {
                currentChatSessionId = Date.now();
                sessions.push({
                    id: currentChatSessionId,
                    title: text.substring(0, 30) + (text.length > 30 ? '...' : ''),
                    created_at: new Date().toISOString(),
                    history: conversationHistory
                });
            } else {
                const session = sessions.find(s => String(s.id) === String(currentChatSessionId));
                if (session) {
                    session.history = conversationHistory;
                }
            }
            localStorage.setItem(storageKey, JSON.stringify(sessions));
            
            // Sync to backend
            try {
                const syncReq = {
                    session_id: currentChatSessionId.toString(),
                    title: text.substring(0, 30) + (text.length > 30 ? '...' : ''),
                    history_json: JSON.stringify(conversationHistory)
                };
                await fetch(`${API_URL}/chat_sessions`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(syncReq)
                });
            } catch (e) {
                console.error("Failed to sync chat session", e);
            }
            
            // Refresh history panel
            loadHistory();
        }
        
    } catch (e) {
        botMsgDiv.innerHTML = `<p style="color: #ff6b6b;"><strong>System Error:</strong> ${e.message}</p>`;
    }
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        chatSend.click();
    }
});

function appendMessage(text, cls) {
    const div = document.createElement('div');
    div.className = `message ${cls}`;
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\n/g, '<br>');
    div.innerHTML = `<p>${formattedText}</p>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

// History
async function loadHistory() {
    let combined = [];
    try {
        const res = await fetch(`${API_URL}/history`, { headers: getAuthHeaders() });
        const apiData = await res.json();
        apiData.forEach(d => {
            // Append Z to correctly parse as UTC if not present
            let correctedDate = d.created_at;
            if (!correctedDate.endsWith('Z')) correctedDate += 'Z';
            combined.push({
                type: 'recipe',
                title: d.recipe.name,
                created_at: correctedDate,
                data: d.recipe
            });
        });
    } catch(e) {
        console.error("Could not load API history", e);
    }
    
    const email = localStorage.getItem("mixbot_token") ? (localStorage.getItem("mixbot_user_name") || "user") : "anon";
    const storageKey = `mixbot_chats_${email}`;
    const sessions = JSON.parse(localStorage.getItem(storageKey) || '[]');
    sessions.forEach(s => combined.push({
        type: 'chat',
        id: s.id,
        title: s.title,
        created_at: s.created_at,
        data: s.history
    }));
    
    // Sort combined history by created at descending
    combined.sort((a,b) => new Date(b.created_at) - new Date(a.created_at));

    if (combined.length === 0) {
        historyList.innerHTML = '<p style="color: var(--text-muted); text-align: center; margin-top: 2rem;">No history found.</p>';
        return;
    }
    
    historyList.innerHTML = combined.map(item => {
        const dateStr = new Date(item.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', timeZoneName: 'short' });
        if (item.type === 'recipe') {
            const safeData = encodeURIComponent(JSON.stringify(item.data));
            return `
            <div class="history-item" onclick="renderHistoryRecipe('${safeData}')">
                <h4>🍹 ${item.title}</h4>
                <p>${dateStr}</p>
            </div>
            `;
        } else {
            return `
            <div class="history-item" onclick="loadChatSession('${item.id}')">
                <h4>💬 ${item.title}</h4>
                <p>${dateStr}</p>
            </div>
            `;
        }
    }).join('');
}

window.loadChatSession = function(id) {
    const email = localStorage.getItem("mixbot_token") ? (localStorage.getItem("mixbot_user_name") || "user") : "anon";
    const storageKey = `mixbot_chats_${email}`;
    const sessions = JSON.parse(localStorage.getItem(storageKey) || '[]');
    const session = sessions.find(s => String(s.id) === String(id));
    if (!session) {
        alert("Session not found in localStorage! ID: " + id + ", Keys available: " + sessions.map(s=>s.id).join(", "));
        return;
    }
    
    currentChatSessionId = id;
    conversationHistory = session.history;
    
    chatMessages.innerHTML = '';
    session.history.forEach(m => {
        const div = document.createElement('div');
        div.className = `message ${m.role === 'user' ? 'user-message' : 'bot-message'}`;
        let formattedText = m.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>').replace(/\n/g, '<br>');
        div.innerHTML = `<p>${formattedText}</p>`;
        chatMessages.appendChild(div);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
    recipeContainer.innerHTML = '';
};

window.renderHistoryRecipe = function(encodedRecipe) {
    try {
        const r = JSON.parse(decodeURIComponent(encodedRecipe));
        recipeContainer.innerHTML = `
            <div class="recipe-card glass-panel" style="margin-top: 1rem;">
                <div class="recipe-header">
                    <h3>${r.name}</h3>
                    <div class="badges">
                        <span class="badge">${r.difficulty || 'Normal'}</span>
                        <span class="badge">${r.glassware || 'Glass'}</span>
                    </div>
                </div>
                <div class="recipe-body">
                    <div class="recipe-list">
                        <h4>Ingredients</h4>
                        <ul>
                            ${(r.ingredients || []).map((ing, i) => `<li><strong>${r.measurements && r.measurements[i] ? r.measurements[i] : ''}</strong> ${ing}</li>`).join('')}
                        </ul>
                        <p style="margin-top: 1rem;"><strong>Garnish:</strong> ${r.garnish || 'None'}</p>
                    </div>
                    <div class="recipe-list">
                        <h4>Instructions</h4>
                        <ol>
                            ${(r.instructions || []).map(step => `<li>${step}</li>`).join('')}
                        </ol>
                    </div>
                </div>
                <div class="flavor-profile">
                    <strong>Flavor Profile:</strong> <p>${r.flavor_profile || 'Balanced'}</p>
                </div>
            </div>
        `;
        recipeContainer.scrollIntoView({ behavior: 'smooth' });
    } catch(e) {
        console.error("Failed to parse history recipe", e);
    }
};

document.getElementById('clear-history').addEventListener('click', async () => {
    await fetch(`${API_URL}/history/clear`, { method: 'POST', headers: getAuthHeaders() });
    const email = localStorage.getItem("mixbot_token") ? (localStorage.getItem("mixbot_user_name") || "user") : "anon";
    const storageKey = `mixbot_chats_${email}`;
    localStorage.removeItem(storageKey);
    localStorage.removeItem('mixbot_chats'); // Fallback for old sessions
    loadHistory();
    document.getElementById('new-chat-btn').click();
});

// Auth Logic
let isRegistering = false;

function updateAuthUI() {
    const token = localStorage.getItem('mixbot_token');
    const name = localStorage.getItem('mixbot_user_name');
    const isAdmin = localStorage.getItem('mixbot_is_admin') === 'true';

    if (token) {
        document.getElementById('show-login-btn').style.display = 'none';
        document.getElementById('show-register-btn').style.display = 'none';
        document.getElementById('logout-btn').style.display = 'block';
        document.getElementById('user-greeting').style.display = 'block';
        document.getElementById('user-greeting').innerText = `Welcome, ${name}`;
        
        document.getElementById('main-app').style.display = 'grid';
        document.getElementById('login-required-msg').style.display = 'none';

        if (isAdmin) {
            document.getElementById('admin-panel-btn').style.display = 'block';
        } else {
            document.getElementById('admin-panel-btn').style.display = 'none';
        }
    } else {
        document.getElementById('show-login-btn').style.display = 'block';
        document.getElementById('show-register-btn').style.display = 'block';
        document.getElementById('logout-btn').style.display = 'none';
        document.getElementById('user-greeting').style.display = 'none';
        document.getElementById('admin-panel-btn').style.display = 'none';
        
        document.getElementById('main-app').style.display = 'none';
        document.getElementById('login-required-msg').style.display = 'block';
    }
}

document.getElementById('show-login-btn').addEventListener('click', () => {
    isRegistering = false;
    document.getElementById('auth-modal-title').innerText = 'Login';
    document.getElementById('auth-submit-btn').innerText = 'Login';
    document.getElementById('auth-register-fields').style.display = 'none';
    document.getElementById('auth-error').style.display = 'none';
    document.getElementById('auth-modal').style.display = 'flex';
});

document.getElementById('show-register-btn').addEventListener('click', () => {
    isRegistering = true;
    document.getElementById('auth-modal-title').innerText = 'Register';
    document.getElementById('auth-submit-btn').innerText = 'Register';
    document.getElementById('auth-register-fields').style.display = 'flex';
    document.getElementById('auth-error').style.display = 'none';
    document.getElementById('auth-modal').style.display = 'flex';
});

document.getElementById('close-auth-modal').addEventListener('click', () => {
    document.getElementById('auth-modal').style.display = 'none';
});

document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('mixbot_token');
    localStorage.removeItem('mixbot_user_name');
    localStorage.removeItem('mixbot_is_admin');
    currentChatSessionId = null;
    conversationHistory = [];
    document.getElementById('recipe-container').innerHTML = '';
    document.getElementById('chat-messages').innerHTML = '';
    updateAuthUI();
    loadHistory(); // Reload history (will fallback to anonymous session)
});

document.getElementById('auth-submit-btn').addEventListener('click', async () => {
    const errorEl = document.getElementById('auth-error');
    errorEl.style.display = 'none';
    
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value;
    
    let payload = { email, password };
    if (isRegistering) {
        payload.name = document.getElementById('auth-name').value.trim();
        if (!payload.name) {
            errorEl.innerText = "Name is required.";
            errorEl.style.display = 'block';
            return;
        }
    }

    if (!email || !password) {
        errorEl.innerText = "Email and Password are required.";
        errorEl.style.display = 'block';
        return;
    }

    const endpoint = isRegistering ? '/auth/register' : '/auth/login';
    
    try {
        const res = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || "Authentication failed");
        }
        
        localStorage.setItem('mixbot_token', data.access_token);
        localStorage.setItem('mixbot_user_name', data.name);
        localStorage.setItem('mixbot_is_admin', data.is_admin);
        
        document.getElementById('auth-modal').style.display = 'none';
        updateAuthUI();
        loadHistory(); // Load authenticated user's history
        
    } catch(e) {
        errorEl.innerText = e.message;
        errorEl.style.display = 'block';
    }
});

// Google Auth Callback
window.handleGoogleLogin = async function(response) {
    const errorEl = document.getElementById('auth-error');
    errorEl.style.display = 'none';
    const token = response.credential;
    try {
        const res = await fetch(`${API_URL}/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Google Auth failed");
        
        localStorage.setItem('mixbot_token', data.access_token);
        localStorage.setItem('mixbot_user_name', data.name);
        localStorage.setItem('mixbot_is_admin', data.is_admin);
        
        document.getElementById('auth-modal').style.display = 'none';
        updateAuthUI();
        loadHistory();
    } catch (e) {
        errorEl.innerText = e.message;
        errorEl.style.display = 'block';
    }
};

// Init
updateAuthUI();
