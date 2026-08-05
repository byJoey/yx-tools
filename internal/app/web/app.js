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
  system: {},      // 运行环境信息（是否支持 crontab 等）
  pool: 1000,      // 候选 IP 数量，0 表示不限
  httping: false,  // 用真实 HTTP 请求测延迟
  noDL: false,     // 跳过下载测速
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
  // 选了地区必须走真实连接，测法要跟着锁上
  if (typeof setPing === 'function') setPing(state.picked.length > 0 || state.httping);
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
    sample_size: state.pool,
    // 只有点了「全部」这一档才穷举网段内每个 IP
    test_all: $('#segPool button[data-pool="0"]').classList.contains('on'),
    httping: state.httping,
    disable_dl: state.noDL,
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
    setPing(!!c.httping);
    setDL(!!c.disable_dl);
    if (c.sample_size != null) {
      const custom = !POOL_PRESETS.includes(c.sample_size);
      if (custom) $('#inPool').value = c.sample_size;
      setPool(c.sample_size, { custom });
    }
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
    if (r.count) download('proxy');
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

// ── 延迟测法与下载测速 ────────────────────────────
function setPing(on) {
  state.httping = on;
  document.querySelectorAll('#segPing button').forEach(b =>
    b.classList.toggle('on', (b.dataset.ping === 'http') === on));
  const forced = state.picked.length > 0;
  $('#pingNote').textContent = on
    ? (forced ? '选了地区就得走真实连接，才能读出机房代码'
              : '走完整 HTTP 请求，含 TLS 握手和服务端响应，更接近实际体验')
    : '只做 TCP 握手，快，但数字偏低';
  // 选了地区时锁死在真实连接，避免给出无效选项
  $('#segPing button[data-ping="tcp"]').disabled = forced;
}

function setDL(off) {
  state.noDL = off;
  document.querySelectorAll('#segDL button').forEach(b =>
    b.classList.toggle('on', (b.dataset.dl === 'off') === off));
  $('#dlNote').textContent = off
    ? '只排延迟，不下载，快很多但看不出带宽'
    : '测完延迟再下载大文件，测出真实速度';
}

// ── 候选 IP 数量 ──────────────────────────────────
const POOL_PRESETS = [500, 1000, 2000, 0];

// 高亮某一档。isCustom 为真时高亮「自定义」并展开输入框
function markPool(n, isCustom) {
  document.querySelectorAll('#segPool button').forEach(b => {
    const on = b.dataset.pool === 'custom' ? isCustom
      : (!isCustom && +b.dataset.pool === n);
    b.classList.toggle('on', on);
  });
  $('#inPool').classList.toggle('hidden', !isCustom);
}

function setPool(n, opt) {
  opt = opt || {};
  state.pool = n;
  markPool(n, !!opt.custom);
  const note = $('#poolNote');
  if ($('#inIPText').value.trim() !== '') {
    note.textContent = '用你填的自定义 IP 段，不走官方段';
  } else if (n === 0) {
    note.textContent = '穷举网段内每个 IP，量很大、很慢';
  } else {
    note.textContent = `从 Cloudflare 官方 IP 段里随机抽 ${n} 个来测延迟`;
  }
}

// 切到自定义档：沿用输入框已有的值，没有就拿当前值打底
function pickCustomPool() {
  const box = $('#inPool');
  if (!box.value) box.value = state.pool || 1000;
  setPool(Math.max(1, +box.value || 1), { custom: true });
  box.focus();
}

function syncPoolNote() {
  setPool(state.pool, { custom: !$('#inPool').classList.contains('hidden') });
}

// ── 下载结果文件 ──────────────────────────────────
function download(kind) {
  const a = document.createElement('a');
  a.href = '/api/download?kind=' + encodeURIComponent(kind);
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ── 自定义 IP 段文件导入 ──────────────────────────
function importIPFile(file) {
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) {
    toast('文件太大，最多 8MB', 'err');
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const lines = String(reader.result)
      .split(/\r?\n/)
      .map(l => l.trim())
      .filter(l => l && !l.startsWith('#'));
    if (!lines.length) {
      toast('文件里没有可用的 IP', 'err');
      return;
    }
    $('#inIPText').value = lines.join('\n');
    $('#ipFileName').textContent = file.name + ' · ' + lines.length + ' 条';
    $('.more').open = true;
    syncPoolNote();
    toast('已导入 ' + lines.length + ' 条', 'ok');
  };
  reader.onerror = () => toast('读取文件失败', 'err');
  reader.readAsText(file);
}

// ── 定时任务 ──────────────────────────────────────
async function loadCron() {
  const box = $('#cronList');
  box.innerHTML = '';
  try {
    const jobs = await api('/api/cron');
    if (!jobs || !jobs.length) {
      box.innerHTML = '<div class="empty" style="padding:14px">还没有定时任务</div>';
      $('#cronHint').textContent = '';
      return;
    }
    $('#cronHint').textContent = jobs.length + ' 条';
    jobs.forEach(j => {
      const row = document.createElement('div');
      row.className = 'cron-item';
      const b = document.createElement('b');
      b.textContent = j.schedule;
      const sp = document.createElement('span');
      sp.textContent = j.command;
      sp.title = j.command;
      row.appendChild(b);
      row.appendChild(sp);
      box.appendChild(row);
    });
  } catch (e) {
    box.innerHTML = '';
    const d = document.createElement('div');
    d.className = 'empty';
    d.style.padding = '14px';
    d.textContent = e.message;
    box.appendChild(d);
  }
}

function openCron() {
  if (!state.system.cron_supported) {
    toast('当前系统没有 crontab，请用系统自带的计划任务', 'err');
    return;
  }
  if (!$('#cronArgs').value.trim()) {
    // 用当前左侧参数拼一条命令，省得手打
    const parts = ['test', '-n', String(+$('#inCount').value || 10)];
    const sl = $('#inSpeed').value.trim();
    if (sl) parts.push('-sl', sl);
    if (state.picked.length) parts.push('-colo', state.picked.join(','));
    $('#cronArgs').value = parts.join(' ');
  }
  $('#cronMask').classList.remove('hidden');
  loadCron();
}

async function addCron() {
  const schedule = $('#cronSchedule').value.trim();
  const args = $('#cronArgs').value.trim();
  if (!schedule) { toast('请选择或填写执行频率', 'err'); return; }
  if (!args) { toast('请填写命令参数', 'err'); return; }
  try {
    await api('/api/cron', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schedule, args, replace: $('#cronReplace').checked }),
    });
    toast('定时任务已添加', 'ok');
    loadCron();
  } catch (e) { toast(e.message, 'err'); }
}

async function removeCron() {
  try {
    const r = await api('/api/cron', { method: 'DELETE' });
    toast(r.count ? `已清掉 ${r.count} 条` : '没有本工具的任务', 'ok');
    loadCron();
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
  document.querySelectorAll('#segPool button').forEach(b => {
    b.onclick = () => {
      if (b.dataset.pool === 'custom') pickCustomPool();
      else setPool(+b.dataset.pool);
    };
  });
  document.querySelectorAll('#segPing button').forEach(b => {
    b.onclick = () => { if (!b.disabled) setPing(b.dataset.ping === 'http'); };
  });
  document.querySelectorAll('#segDL button').forEach(b => {
    b.onclick = () => setDL(b.dataset.dl === 'off');
  });
  $('#inPool').addEventListener('input', e => {
    const v = +e.target.value;
    setPool(v > 0 ? v : 0, { custom: true });
  });
  $('#inIPText').addEventListener('input', syncPoolNote);
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
  $('#btnDownload').onclick = () => download('result');

  $('#inIPFile').addEventListener('change', e => {
    importIPFile(e.target.files && e.target.files[0]);
    e.target.value = '';
  });

  $('#btnCron').onclick = openCron;
  $('#btnCronClose').onclick = () => $('#cronMask').classList.add('hidden');
  $('#cronMask').onclick = e => { if (e.target === $('#cronMask')) $('#cronMask').classList.add('hidden'); };
  $('#btnCronAdd').onclick = addCron;
  $('#btnCronRemove').onclick = removeCron;
  document.querySelectorAll('#cronPresets button').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('#cronPresets button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      $('#cronSchedule').value = b.dataset.cron;
    };
  });
  $('#cronSchedule').addEventListener('input', () => {
    document.querySelectorAll('#cronPresets button').forEach(b =>
      b.classList.toggle('on', b.dataset.cron === $('#cronSchedule').value.trim()));
  });

  try { state.system = await api('/api/system') || {}; } catch (_) {}
  if (!state.system.cron_supported) $('#btnCron').classList.add('hidden');

  await loadConfig();
  try {
    const st = await api('/api/status');
    if (st.running) { setRunning(true); }
    if (st.count) { state.results = await api('/api/results'); renderTable(); }
  } catch (_) {}
  connectEvents();
})();
