const API = 'https://raw.githubusercontent.com/kareemamindumontj/watchful-eye/master';
let autoRefresh = true;
let refreshTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  try {
    initTabs();
    initLive();
    initHistory();
    initSummary();
  } catch (e) { console.error('Init error:', e); }
});

function updateTimestamp() {
  const el = document.getElementById('timestamp');
  if (el) el.textContent = new Date().toLocaleTimeString();
}

function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
      tab.classList.add('active');
      const el = document.getElementById('tab-' + tab.dataset.tab);
      if (el) el.classList.add('active');
      if (tab.dataset.tab === 'history') loadHistory();
      if (tab.dataset.tab === 'summary') loadSummary();
    });
  });
}

function initLive() {
  const img = document.getElementById('live-screen');
  const btnRefresh = document.getElementById('btn-refresh');
  const btnWebcam = document.getElementById('btn-webcam');
  const btnAuto = document.getElementById('btn-autorefresh');

  async function refreshFromJSON() {
    try {
      const r = await fetch(API + '/data/state.json?' + Date.now());
      if (!r.ok) return;
      const state = await r.json();
      if (state.screen && img) img.src = state.screen;
      document.getElementById('update-indicator').textContent = state.ts ? 'Last: ' + state.ts : 'Live';
    } catch (e) { /* silent */ }
  }

  function refreshScreen() {
    if (img) img.src = API + '/latest_screen.jpg?' + Date.now();
  }

  if (btnRefresh) btnRefresh.addEventListener('click', refreshFromJSON);

  if (btnWebcam) {
    btnWebcam.addEventListener('click', async () => {
      const modal = document.getElementById('webcam-modal');
      const wcImg = document.getElementById('webcam-img');
      try {
        const r = await fetch(API + '/data/state.json?' + Date.now());
        if (r.ok) {
          const state = await r.json();
          if (state.webcam && wcImg) wcImg.src = state.webcam;
        }
      } catch (e) { /* silent */ }
      if (modal) modal.classList.remove('hidden');
    });
  }

  const closeBtn = document.getElementById('btn-close-webcam');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      const modal = document.getElementById('webcam-modal');
      if (modal) modal.classList.add('hidden');
    });
  }

  function toggleAuto() {
    autoRefresh = !autoRefresh;
    if (btnAuto) btnAuto.classList.toggle('active');
    const ind = document.getElementById('update-indicator');
    if (ind) ind.classList.toggle('paused');
    if (autoRefresh) startAutoRefresh();
    else stopAutoRefresh();
  }

  if (btnAuto) {
    btnAuto.addEventListener('click', toggleAuto);
    btnAuto.textContent = 'Auto (3s)';
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    refreshTimer = setInterval(refreshFromJSON, 3000);
  }

  function stopAutoRefresh() {
    if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  }

  setInterval(updateTimestamp, 1000);
  refreshFromJSON();
  startAutoRefresh();
}

async function loadHistory() {
  try {
    const r = await fetch(API + '/data/history.json?' + Date.now());
    if (!r.ok) throw new Error('No history');
    const data = await r.json();
    const list = document.getElementById('sessions-list');
    if (list) {
      list.innerHTML = '';
      if (data.sessions && data.sessions.length) {
        data.sessions.slice().reverse().slice(0, 10).forEach(s => {
          const card = document.createElement('div');
          card.className = 'session-card';
          card.innerHTML = '<div class="date">' + (s.boot_time || 'Unknown') + '</div><div class="meta">' + (s.duration || '?') + ' min &middot; ' + (s.activity_count || 0) + ' activities</div>';
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div class="session-card">No sessions yet.</div>';
      }
    }
  } catch (e) {
    const el = document.getElementById('sessions-list');
    if (el) el.innerHTML = '<div class="session-card">Waiting for data...</div>';
  }
}

async function loadSummary() {
  try {
    const r = await fetch(API + '/data/session.json?' + Date.now());
    if (!r.ok) throw new Error('No data');
    const data = await r.json();
    const el = document.getElementById('summary-text');
    if (el) el.textContent = data.summary || 'No summary yet.';
  } catch (e) {
    const el = document.getElementById('summary-text');
    if (el) el.textContent = 'Waiting for data from laptop...';
  }
}

function initSummary() {
  const btn = document.getElementById('btn-summarize');
  if (btn) btn.style.display = 'none';
}
