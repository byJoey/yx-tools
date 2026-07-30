'use strict';

const $ = s => document.querySelector(s);
const state = {
  colos: [],       // 全部机场码
  picked: [],      // 已选机场码
  results: [],     // 测速结果
  sortKey: '',
  sortDir: 'desc',
  running: false,
  hasToken: false,
};

// ── 提示 ──────────────────────────────────────────
function toast(msg, kind) {
  const el = document.createElement('div');
  el.className = 'toast' + (kind ? ' ' + kind : '');
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity .3s';
    setTimeout(() => el.remove(), 300);
  }, 3600);
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) {}
  if (!r.ok) throw new Error((data && data.error) || text || ('HTTP ' + r.status));
  return data;
}

// ── 机场码选择 ────────────────────────────────────
function renderChips() {
  const box = $('#coloChips');
  box.innerHTML = '';
  state.picked.forEach(code => {
    const c = state.colos.find(x => x.code === code);
    const el = document.createElement('div');
    el.className = 'chip';
    el.innerHTML = `<b>${code}</b>${c ? c.name : ''}<span>&times;</span>`;
    el.querySelector('span').onclick = () => {
      state.picked = state.picked.filter(x => x !== code);
      renderChips();
    };
    box.appendChild(el);
  });
}

function renderColoList(q) {
  const list = $('#coloList');
  q = (q || '').trim().toLowerCase();
  if (!q) { list.classList.remove('show'); return; }
  const hit = state.colos.filter(c =>
    c.code.toLowerCase().includes(q) || c.name.includes(q) ||
    c.country.includes(q) || c.region.includes(q)
  ).slice(0, 40);
  list.innerHTML = '';
  if (!hit.length) { list.classList.remove('show'); return; }
  hit.forEach(c => {
    const el = document.createElement('div');
    el.className = 'colo-item';
    el.innerHTML = `<span>${c.name} <code>${c.code}</code></span><code>${c.country}</code>`;
    el.onclick = () => {
      if (!state.picked.includes(c.code)) state.picked.push(c.code);
      $('#coloSearch').value = '';
      list.classList.remove('show');
      renderChips();
    };
    list.appendChild(el);
  });
  list.classList.add('show');
}

// ── 结果表 ────────────────────────────────────────
function fmtSpeed(v) {
  const cls = v >= 5 ? 'g' : v >= 1 ? 'y' : 'r';
  return `<span class="${cls}">${v.toFixed(2)}</span>`;
}
function fmtDelay(v) {
  const cls = v <= 100 ? 'g' : v <= 250 ? 'y' : 'r';
  return `<span class="${cls}">${v.toFixed(0)}</span>`;
}

function visibleRows() {
  const q = $('#filterText').value.trim().toLowerCase();
  let rows = state.results;
  if (q) {
    rows = rows.filter(r =>
      r.ip.toLowerCase().includes(q) ||
      (r.colo || '').toLowerCase().includes(q) ||
      (r.colo_name || '').includes(q)
    );
  }
  if (state.sortKey) {
    const k = state.sortKey, dir = state.sortDir === 'asc' ? 1 : -1;
    rows = rows.slice().sort((a, b) => {
      let x = k === 'loss' ? a.loss_rate : a[k];
      let y = k === 'loss' ? b.loss_rate : b[k];
      if (typeof x === 'string') return x.localeCompare(y) * dir;
      return (x - y) * dir;
    });
  }
  return rows;
}

function renderTable() {
  const rows = visibleRows();
  const tb = $('#tbody');
  tb.innerHTML = '';
  $('#emptyBox').classList.toggle('hidden', rows.length > 0);
  rows.forEach((r, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td class="c-idx">${i + 1}</td>` +
      `<td class="mono">${r.ip}</td>` +
      `<td class="c-num mono">${r.port}</td>` +
      `<td class="c-num mono">${fmtDelay(r.delay)}</td>` +
      `<td class="c-num mono">${fmtSpeed(r.speed)}</td>` +
      `<td class="c-num mono">${(r.loss_rate * 100).toFixed(0)}%</td>` +
      `<td>${r.colo_name || '-'}${r.colo ? ' <code style="opacity:.6">' + r.colo + '</code>' : ''}</td>` +
      `<td class="c-act"><button class="copy" title="复制 IP:端口">⧉</button></td>`;
    tr.querySelector('.copy').onclick = () => {
      navigator.clipboard.writeText(`${r.ip}:${r.port}`).then(
        () => toast('已复制 ' + r.ip + ':' + r.port, 'ok'),
        () => toast('复制失败', 'err')
      );
    };
    tb.appendChild(tr);
  });
  $('#statResult').textContent = '结果 ' + state.results.length;
}

// ── 运行状态 ──────────────────────────────────────
function setRunning(on) {
  state.running = on;
  $('#btnStart').classList.toggle('hidden', on);
  $('#btnStop').classList.toggle('hidden', !on);
  $('#statusDot').className = 'dot' + (on ? ' run' : '');
  $('#progressFill').className = on ? 'indet' : 'idle';
}

function connectEvents() {
  const es = new EventSource('/api/events');
  es.onmessage = ev => {
    let e;
    try { e = JSON.parse(ev.data); } catch (_) { return; }
    if (e.message) $('#statusText').textContent = e.message;
    if (e.type === 'done') {
      state.results = e.results || [];
      renderTable();
      setRunning(false);
      toast(`测速完成，${state.results.length} 个结果`, 'ok');
    } else if (e.type === 'error') {
      setRunning(false);
      $('#statusDot').className = 'dot err';
      toast(e.message || '测速失败', 'err');
    } else if (e.type === 'progress') {
      setRunning(true);
    }
  };
  es.onerror = () => { /* 浏览器会自动重连 */ };
}

// ── 启动测速 ──────────────────────────────────────
async function start() {
  const opts = {
    colo: state.picked.join(','),
    ipv6: $('#segIPv button.on').dataset.v === '6',
    count: +$('#inCount').value || 10,
    speed_limit: +$('#inSpeed').value || 0,
    delay_limit: +$('#inDelay').value || 1000,
    threads: +$('#inThread').value || 200,
    port: +$('#inPort').value || 443,
    test_url: $('#inURL').value.trim(),
    ip_text: $('#inIPText').value.trim(),
    disable_dl: $('#inNoDL').checked,
    test_all: $('#inAll').checked,
  };
  try {
    await api('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(opts),
    });
    setRunning(true);
    $('#statusDot').className = 'dot run';
    $('#statusText').textContent = '正在启动…';
  } catch (e) {
    toast(e.message, 'err');
  }
}

// ── 配置弹窗 ──────────────────────────────────────
async function loadConfig() {
  try {
    const c = await api('/api/config');
    $('#cfgDomain').value = c.worker_domain || '';
    $('#cfgUUID').value = c.uuid || '';
    $('#cfgRepo').value = c.github_repo || '';
    $('#cfgPath').value = c.github_path || 'cloudflare_ips.txt';
    state.hasToken = !!c.has_github_token;
    $('#tokenHint').textContent = state.hasToken ? '已保存' : '';
    // 回填上次的测速参数
    if (c.count) $('#inCount').value = c.count;
    if (c.speed_limit != null) $('#inSpeed').value = c.speed_limit;
    if (c.delay_limit) $('#inDelay').value = c.delay_limit;
    if (c.threads) { $('#inThread').value = c.threads; $('#threadVal').textContent = c.threads; }
    if (c.port) $('#inPort').value = c.port;
    if (c.test_url) $('#inURL').value = c.test_url;
    if (c.ipv6) {
      document.querySelectorAll('#segIPv button').forEach(b =>
        b.classList.toggle('on', b.dataset.v === '6'));
    }
    if (c.colo) {
      state.picked = c.colo.split(',').map(s => s.trim()).filter(Boolean);
      renderChips();
    }
  } catch (_) {}
}

async function saveConfig() {
  const body = {
    worker_domain: $('#cfgDomain').value.trim(),
    uuid: $('#cfgUUID').value.trim(),
    github_repo: $('#cfgRepo').value.trim(),
    github_path: $('#cfgPath').value.trim(),
  };
  const tok = $('#cfgToken').value.trim();
  if (tok) body.github_token = tok;
  try {
    await api('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    $('#cfgToken').value = '';
    $('#mask').classList.add('hidden');
    toast('配置已保存', 'ok');
    loadConfig();
  } catch (e) { toast(e.message, 'err'); }
}

// ── 导出与上报 ────────────────────────────────────
async function genProxy() {
  try {
    const r = await api('/api/proxy-list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ limit: +$('#cfgLimit').value || 0 }),
    });
    toast(`已生成 ${r.file}，共 ${r.count} 条`, 'ok');
  } catch (e) { toast(e.message, 'err'); }
}

async function uploadAPI() {
  const domain = $('#cfgDomain').value.trim();
  const uuid = $('#cfgUUID').value.trim();
  if (!domain || !uuid) {
    $('#mask').classList.remove('hidden');
    toast('请先填写 Worker 域名和 UUID', 'err');
    return;
  }
  try {
    const r = await api('/api/upload/api', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_domain: domain, uuid: uuid,
        limit: +$('#cfgLimit').value || 10,
        clear: $('#cfgClear').checked,
      }),
    });
    toast(`已上报 ${r.count} 个 IP`, 'ok');
  } catch (e) { toast(e.message, 'err'); }
}

async function uploadGitHub() {
  const repo = $('#cfgRepo').value.trim();
  if (!repo || (!state.hasToken && !$('#cfgToken').value.trim())) {
    $('#mask').classList.remove('hidden');
    toast('请先填写 GitHub 仓库和 Token', 'err');
    return;
  }
  try {
    const r = await api('/api/upload/github', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo: repo,
        token: $('#cfgToken').value.trim(),
        path: $('#cfgPath').value.trim(),
        limit: +$('#cfgLimit').value || 10,
      }),
    });
    toast(`已上传 ${r.count} 个 IP 到 GitHub`, 'ok');
  } catch (e) { toast(e.message, 'err'); }
}

// ── 初始化 ────────────────────────────────────────
(async function init() {
  try { state.colos = await api('/api/colos'); } catch (_) {}

  $('#coloSearch').addEventListener('input', e => renderColoList(e.target.value));
  $('#coloSearch').addEventListener('focus', e => renderColoList(e.target.value));
  document.addEventListener('click', e => {
    if (!e.target.closest('.colo-box')) $('#coloList').classList.remove('show');
  });

  document.querySelectorAll('#segIPv button').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('#segIPv button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
    };
  });

  $('#inThread').addEventListener('input', e => { $('#threadVal').textContent = e.target.value; });
  $('#btnStart').onclick = start;
  $('#btnStop').onclick = () => api('/api/cancel', { method: 'POST' }).catch(() => {});
  $('#filterText').addEventListener('input', renderTable);

  document.querySelectorAll('thead th[data-sort]').forEach(th => {
    th.onclick = () => {
      const k = th.dataset.sort;
      if (state.sortKey === k) {
        state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        state.sortKey = k;
        state.sortDir = (k === 'delay' || k === 'loss') ? 'asc' : 'desc';
      }
      document.querySelectorAll('thead th').forEach(x => x.removeAttribute('data-dir'));
      th.setAttribute('data-dir', state.sortDir);
      renderTable();
    };
  });

  $('#btnConfig').onclick = () => $('#mask').classList.remove('hidden');
  $('#btnCfgClose').onclick = () => $('#mask').classList.add('hidden');
  $('#btnCfgSave').onclick = saveConfig;
  $('#mask').onclick = e => { if (e.target === $('#mask')) $('#mask').classList.add('hidden'); };
  $('#btnProxy').onclick = genProxy;
  $('#btnUploadAPI').onclick = uploadAPI;
  $('#btnUploadGH').onclick = uploadGitHub;

  await loadConfig();
  try {
    const st = await api('/api/status');
    if (st.running) { setRunning(true); }
    if (st.count) { state.results = await api('/api/results'); renderTable(); }
  } catch (_) {}
  connectEvents();
})();
