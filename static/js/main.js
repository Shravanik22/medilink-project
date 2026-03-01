/* ============================================================
   MediLink – main.js
   Global interactive features: toasts, modals, animations, tables
   ============================================================ */

// ── Toast System ─────────────────────────────────────────────
const Toast = (() => {
  const container = (() => {
    let c = document.querySelector('.toast-container');
    if (!c) {
      c = document.createElement('div');
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  })();

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const titles = { success: 'Success', error: 'Error', info: 'Info', warning: 'Warning' };

  function show(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-body">
        <div class="toast-title">${titles[type] || 'Notification'}</div>
        <div class="toast-msg">${message}</div>
      </div>
      <button class="toast-close" onclick="this.closest('.toast').remove()">×</button>
      <div class="toast-progress" style="animation-duration:${duration}ms"></div>
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'slideInRight .3s ease reverse';
      setTimeout(() => toast.remove(), 280);
    }, duration);
    return toast;
  }

  return { show,
    success: (m, d) => show(m, 'success', d),
    error:   (m, d) => show(m, 'error',   d),
    info:    (m, d) => show(m, 'info',    d),
    warning: (m, d) => show(m, 'warning', d),
  };
})();

// ── Modal System ─────────────────────────────────────────────
const Modal = (() => {
  function open(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  }
  function close(id) {
    const el = id ? document.getElementById(id) : document.querySelector('.modal-overlay.show');
    if (el) {
      el.classList.remove('show');
      document.body.style.overflow = '';
    }
  }
  // Close on overlay click
  document.addEventListener('click', e => {
    if (e.target.classList.contains('modal-overlay')) close();
  });
  // Close on ESC
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
  });
  return { open, close };
})();

// ── Page Loader ───────────────────────────────────────────────
const Loader = (() => {
  let el;
  function getEl() {
    if (!el) {
      el = document.querySelector('.page-loader');
      if (!el) {
        el = document.createElement('div');
        el.className = 'page-loader';
        el.innerHTML = `<div class="loader-spinner"></div><div class="loader-text">Loading…</div>`;
        document.body.appendChild(el);
      }
    }
    return el;
  }
  return {
    show: (text = 'Loading…') => {
      const l = getEl();
      l.querySelector('.loader-text').textContent = text;
      l.classList.add('show');
    },
    hide: () => getEl().classList.remove('show'),
  };
})();

// ── Count-up Animation ────────────────────────────────────────
function animateCountUp(el, target, duration = 1200) {
  const start = 0;
  const startTime = performance.now();
  const isFloat = String(target).includes('.');
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = start + (target - start) * ease;
    el.textContent = isFloat ? current.toFixed(1) : Math.round(current).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function initCountUps() {
  const els = document.querySelectorAll('[data-count]');
  if (!els.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        animateCountUp(el, parseFloat(el.dataset.count));
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.3 });
  els.forEach(el => observer.observe(el));
}

// ── Sortable Tables ───────────────────────────────────────────
function initSortableTables() {
  document.querySelectorAll('table.sortable').forEach(table => {
    const headers = table.querySelectorAll('thead th[data-col]');
    headers.forEach(th => {
      th.style.cursor = 'pointer';
      th.innerHTML += ' <span class="sort-icon">↕</span>';
      th.addEventListener('click', () => {
        const col    = th.dataset.col;
        const asc    = th.dataset.sortDir !== 'asc';
        th.dataset.sortDir = asc ? 'asc' : 'desc';
        headers.forEach(h => { h.querySelector('.sort-icon').textContent = '↕'; });
        th.querySelector('.sort-icon').textContent = asc ? '↑' : '↓';
        const tbody = table.querySelector('tbody');
        const rows  = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => {
          const aVal = a.querySelector(`td:nth-child(${parseInt(col)+1})`)?.textContent.trim() || '';
          const bVal = b.querySelector(`td:nth-child(${parseInt(col)+1})`)?.textContent.trim() || '';
          const aNum = parseFloat(aVal.replace(/[^0-9.]/g,''));
          const bNum = parseFloat(bVal.replace(/[^0-9.]/g,''));
          if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
          return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        });
        rows.forEach(r => tbody.appendChild(r));
      });
    });
  });
}

// ── Drag-and-Drop File Upload ─────────────────────────────────
function initDropZones() {
  document.querySelectorAll('.drop-zone').forEach(zone => {
    const input = zone.querySelector('input[type=file]');
    const text  = zone.querySelector('.dz-selected');

    zone.addEventListener('click', () => input && input.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files[0] && input) {
        input.files = e.dataTransfer.files;
        if (text) text.textContent = e.dataTransfer.files[0].name;
        zone.classList.add('has-file');
        input.dispatchEvent(new Event('change'));
      }
    });
    if (input) {
      input.addEventListener('change', () => {
        if (input.files[0] && text) {
          text.textContent = input.files[0].name;
          zone.classList.add('has-file');
        }
      });
    }
  });
}

// ── AJAX Form Submit ──────────────────────────────────────────
async function ajaxSubmit(form, btn) {
  const origText = btn.innerHTML;
  btn.innerHTML = `<span class="spinner"></span> Processing…`;
  btn.disabled  = true;
  const fd = new FormData(form);
  try {
    const res  = await fetch(form.action || location.href, {
      method: 'POST', body: fd
    });
    const data = await res.json();
    if (data.success) {
      Toast.success(data.message);
      if (data.redirect) setTimeout(() => location.href = data.redirect, 800);
    } else {
      Toast.error(data.message || 'An error occurred.');
    }
    return data;
  } catch (err) {
    Toast.error('Network error. Please try again.');
    return { success: false };
  } finally {
    btn.innerHTML = origText;
    btn.disabled  = false;
  }
}

// ── JSON POST helper ──────────────────────────────────────────
async function postJSON(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

// ── Sidebar active link ───────────────────────────────────────
function initSidebarActive() {
  const path = location.pathname;
  document.querySelectorAll('.sidebar .nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && path.startsWith(href)) item.classList.add('active');
  });
}

// ── Confirm dialog ────────────────────────────────────────────
function confirmAction(message) {
  return new Promise(resolve => {
    const d = document.createElement('div');
    d.className = 'modal-overlay show';
    d.innerHTML = `
      <div class="modal" style="max-width:380px">
        <div class="modal-header"><h3>⚠️ Confirm</h3></div>
        <div class="modal-body"><p style="font-size:15px;color:var(--text-muted)">${message}</p></div>
        <div class="modal-footer">
          <button class="btn btn-outline" id="confNo">Cancel</button>
          <button class="btn btn-danger" id="confYes">Confirm</button>
        </div>
      </div>`;
    document.body.appendChild(d);
    d.querySelector('#confYes').onclick = () => { d.remove(); resolve(true); };
    d.querySelector('#confNo').onclick  = () => { d.remove(); resolve(false); };
  });
}

// ── Flash messages as toasts ──────────────────────────────────
function initFlashMessages() {
  document.querySelectorAll('[data-flash]').forEach(el => {
    const type = el.dataset.flash || 'info';
    Toast.show(el.textContent, type);
    el.remove();
  });
}

// ── Animate page elements ─────────────────────────────────────
function initPageAnimations() {
  const els = document.querySelectorAll('.stat-card, .card, .feature-card, .metric-card');
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, i * 60);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  els.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .4s ease, transform .4s ease';
    obs.observe(el);
  });
}

// ── Search filter for tables ──────────────────────────────────
function initTableSearch(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

// ── Init all ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initCountUps();
  initSortableTables();
  initDropZones();
  initSidebarActive();
  initFlashMessages();
  initPageAnimations();
});

window.Toast    = Toast;
window.Modal    = Modal;
window.Loader   = Loader;
window.postJSON = postJSON;
window.confirmAction = confirmAction;
window.ajaxSubmit    = ajaxSubmit;
window.initTableSearch = initTableSearch;
