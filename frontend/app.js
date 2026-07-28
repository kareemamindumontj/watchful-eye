const API = '';
let autoRefresh = true;
let refreshTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  try {
    initTabs();
    initLive();
    initHistory();
    initSummary();
    setInterval(() => {
      const el = document.getElementById('timestamp');
      if (el) el.textContent = new Date().toLocaleTimeString();
    }, 1000);
  } catch (e) {
    console.error('Init error:', e);
  }
});

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

  function refreshScreen() {
    if (img) img.src = '/api/screen?' + Date.now();
  }
  if (btnRefresh) btnRefresh.addEventListener('click', refreshScreen);
  if (btnWebcam) {
    btnWebcam.addEventListener('click', () => {
      const modal = document.getElementById('webcam-modal');
      const wcImg = document.getElementById('webcam-img');
      if (wcImg) wcImg.src = '/api/webcam?' + Date.now();
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
  if (btnAuto) btnAuto.addEventListener('click', toggleAuto);
  function startAutoRefresh() {
    stopAutoRefresh();
    refreshTimer = setInterval(() => {
      if (img) img.src = '/api/screen?' + Date.now();
    }, 3000);
  }
  function stopAutoRefresh() {
    if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  }
  startAutoRefresh();
}

async function loadHistory() {
  try {
    const res = await fetch(API + '/api/sessions');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('sessions-list');
    if (list) {
      list.innerHTML = '';
      if (data.sessions && data.sessions.length) {
        const all = [...data.sessions].reverse();
        all.slice(0, 10).forEach(s => {
          const card = document.createElement('div');
          card.className = 'session-card';
          const thumb = s.webcam ? `<img class="webcam-thumb" src="data:image/jpeg;base64,${s.webcam}" alt="">` : '';
          card.innerHTML = `${thumb}<div class="date">${s.boot_time || 'Unknown'}</div><div class="meta">${s.duration || '?'} min · ${s.activity_count || 0} activities</div>`;
          list.appendChild(card);
        });
      } else {
        list.innerHTML = '<div class="session-card">No sessions yet.</div>';
      }
    }
    const shotsRes = await fetch(API + '/api/screenshots');
    if (!shotsRes.ok) return;
    const shotsData = await shotsRes.json();
    const grid = document.getElementById('screenshots-grid');
    if (grid) {
      grid.innerHTML = '';
      if (shotsData.screenshots) {
        const all = [...shotsData.screenshots].reverse();
        all.slice(0, 12).forEach((shot, i) => {
          const idx = shotsData.screenshots.length - 1 - i;
          const img = document.createElement('img');
          img.src = API + '/api/screenshot?idx=' + idx;
          img.loading = 'lazy';
          grid.appendChild(img);
        });
      }
    }
  } catch (e) { console.error('History error:', e); }
}

async function loadSummary() {
  try {
    const res = await fetch(API + '/api/sessions');
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('summary-text');
    if (el) el.textContent = data.latest_summary || 'No summary yet.';
  } catch (e) { console.error('Summary error:', e); }
}

function initSummary() {
  const btn = document.getElementById('btn-summarize');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.textContent = 'Generating...';
      btn.disabled = true;
      try {
        const res = await fetch(API + '/api/sessions');
        if (!res.ok) return;
        const data = await res.json();
        const sessions = data.sessions;
        if (sessions && sessions.length) {
          const last = sessions[sessions.length - 1];
          const sRes = await fetch(API + '/api/session/' + last.id + '/summary');
          if (sRes.ok) {
            const sData = await sRes.json();
            const el = document.getElementById('summary-text');
            if (el) el.textContent = sData.summary || 'No summary.';
          }
        }
      } catch (e) { console.error('Generate error:', e); }
      btn.textContent = 'Generate Summary';
      btn.disabled = false;
    });
  }
}
