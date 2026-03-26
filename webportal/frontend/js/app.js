/* ═══════════════════════════════════════════════════════
   QR Attendance — Shared JavaScript
   ═══════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:5000/api';

// ── Auth helpers ─────────────────────────────────────
function getToken()  { return localStorage.getItem('token'); }
function setToken(t) { localStorage.setItem('token', t); }
function clearToken(){ localStorage.removeItem('token'); localStorage.removeItem('admin'); }
function getAdmin()  { try { return JSON.parse(localStorage.getItem('admin')); } catch { return null; } }
function setAdmin(a) { localStorage.setItem('admin', JSON.stringify(a)); }

function requireAuth() {
    if (!getToken()) { window.location.href = 'login.html'; return false; }
    return true;
}

// ── API fetch wrapper ────────────────────────────────
async function api(endpoint, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        if (res.status === 401) {
            clearToken();
            window.location.href = 'login.html';
            return null;
        }

        // Handle file downloads
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('text/csv') || contentType.includes('application/pdf')) {
            if (!res.ok) throw new Error('Download failed');
            const blob = await res.blob();
            const disposition = res.headers.get('content-disposition') || '';
            let filename = 'report';
            const match = disposition.match(/filename=(.+)/);
            if (match) filename = match[1];
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename; a.click();
            URL.revokeObjectURL(url);
            return { downloaded: true };
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Request failed');
        return data;
    } catch (err) {
        console.error('API Error:', err);
        throw err;
    }
}

// ── Toast notifications ──────────────────────────────
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Loading overlay ──────────────────────────────────
function showLoading() {
    let overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="loading-spinner"></div>';
        document.body.appendChild(overlay);
    }
    overlay.classList.add('show');
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) overlay.classList.remove('show');
}

// ── Sidebar ──────────────────────────────────────────
function initSidebar() {
    const toggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Highlight active nav item
    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === currentPage) {
            item.classList.add('active');
        }
    });

    // Set admin name
    const admin = getAdmin();
    const nameEl = document.getElementById('adminName');
    if (admin && nameEl) nameEl.textContent = admin.name || 'Admin';
}

// ── Logout ───────────────────────────────────────────
function logout() {
    clearToken();
    window.location.href = 'login.html';
}

// ── Pagination renderer ──────────────────────────────
const _pageCallbacks = {};
function _paginateTo(id, page) { if (_pageCallbacks[id]) _pageCallbacks[id](page); }

function renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container) return;

    _pageCallbacks[containerId] = onPageChange;

    if (totalPages <= 0) {
        container.innerHTML = '<span class="pagination-info">No results</span>';
        return;
    }

    let html = `<span class="pagination-info">Page ${currentPage} of ${totalPages}</span>`;
    html += '<div class="pagination-buttons">';
    html += `<button ${currentPage <= 1 ? 'disabled' : ''} onclick="_paginateTo('${containerId}',${currentPage - 1})">‹</button>`;

    const range = 2;
    let start = Math.max(1, currentPage - range);
    let end = Math.min(totalPages, currentPage + range);

    if (start > 1) {
        html += `<button onclick="_paginateTo('${containerId}',1)">1</button>`;
        if (start > 2) html += '<button disabled>…</button>';
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="_paginateTo('${containerId}',${i})">${i}</button>`;
    }

    if (end < totalPages) {
        if (end < totalPages - 1) html += '<button disabled>…</button>';
        html += `<button onclick="_paginateTo('${containerId}',${totalPages})">${totalPages}</button>`;
    }

    html += `<button ${currentPage >= totalPages ? 'disabled' : ''} onclick="_paginateTo('${containerId}',${currentPage + 1})">›</button>`;
    html += '</div>';

    container.innerHTML = html;
}

// ── Percentage bar ───────────────────────────────────
function pctBar(value) {
    const cls = value >= 75 ? 'pct-high' : value >= 50 ? 'pct-mid' : 'pct-low';
    return `<div class="pct-bar ${cls}">
        <div class="bar"><div class="fill" style="width:${value}%"></div></div>
        <span class="value">${value}%</span>
    </div>`;
}

// ── Modal helpers ────────────────────────────────────
function openModal(id) {
    document.getElementById(id).classList.add('show');
}
function closeModal(id) {
    document.getElementById(id).classList.remove('show');
}

// ── Debounce ─────────────────────────────────────────
function debounce(fn, ms = 400) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
