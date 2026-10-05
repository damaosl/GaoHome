/* 高岛的眼睛 — 控制台逻辑（与极简主题同风格，纯原生 JS） */
(() => {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const MODE_LABEL = {
    guide: '引导',
    replace: '截止更改',
    append: '追加',
    modify: '改返回值',
  };

  async function api(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: body !== undefined ? { 'content-type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  /* ── 主题 ── */
  function applyTheme(dark) {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('高岛的眼睛.dark', dark ? '1' : '0');
  }
  const savedDark = localStorage.getItem('高岛的眼睛.dark');
  applyTheme(savedDark !== null ? savedDark === '1' : window.matchMedia('(prefers-color-scheme: dark)').matches);
  $('#theme-toggle').addEventListener('click', () => applyTheme(!document.body.classList.contains('dark')));

  /* ── 元信息 ── */
  async function loadMeta() {
    try {
      const m = await api('GET', '/api/meta');
      $('#meta-chip').textContent = `代理 :${m.proxyPort} · 规则 ${m.ruleCount}`;
    } catch (e) {
      $('#meta-chip').textContent = '连接失败';
    }
  }

  /* ── 一键代理 ── */
  async function renderProxy() {
    try {
      const data = await api('GET', '/api/proxy');
      $('#proxy-targets').innerHTML = data.targets.map((t) => {
        const st = data.status[t.id] || { enabled: false, server: '' };
        return `
          <li class="proxy-target">
            <div class="proxy-info">
              <div class="proxy-name">${esc(t.name)}</div>
              <div class="proxy-desc">${esc(t.desc)}${st.enabled && st.server ? ` · <span class="server">${esc(st.server)}</span>` : ''}</div>
            </div>
            <label class="switch" title="开启/关闭">
              <input type="checkbox" ${st.enabled ? 'checked' : ''} data-proxy="${esc(t.id)}" />
              <span class="track"></span>
            </label>
          </li>`;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  }

  $('#proxy-targets').addEventListener('change', async (ev) => {
    const t = ev.target.closest('[data-proxy]');
    if (!t) return;
    try {
      await api('POST', '/api/proxy', { target: t.dataset.proxy, enable: t.checked });
    } catch (e) {
      alert('设置代理失败：' + e.message);
    }
    await renderProxy();
  });

  /* ── 规则列表 ── */
  async function renderRules() {
    try {
      const rules = await api('GET', '/api/rules');
      const ul = $('#rules');
      $('#rules-empty').hidden = rules.length > 0;
      ul.innerHTML = rules.map((r) => `
        <li class="rule ${r.enabled ? '' : 'disabled'}">
          <div class="rule-top">
            <span class="rule-name">${esc(r.name)}</span>
            <span class="badge phase-${esc(r.match.phase)}">${r.match.phase === 'request' ? '去程' : '反馈'}</span>
            <span class="badge">${esc(r.match.type)}</span>
            ${r.match.methods.length ? `<span class="badge">${esc(r.match.methods.join(','))}</span>` : ''}
            <span class="badge">${esc(MODE_LABEL[r.action.mode] || r.action.mode)}</span>
            <label class="switch" title="启用/停用">
              <input type="checkbox" ${r.enabled ? 'checked' : ''} data-toggle="${esc(r.id)}" />
              <span class="track"></span>
            </label>
          </div>
          <div class="rule-pattern">${esc(r.match.pattern)}</div>
          <div class="rule-summary">${esc(summary(r))}</div>
          <div class="rule-foot">
            <button class="btn ghost" data-edit="${esc(r.id)}">编辑</button>
            <button class="btn ghost danger" data-del="${esc(r.id)}">删除</button>
          </div>
        </li>
      `).join('');
    } catch (e) {
      console.error(e);
    }
  }

  function summary(r) {
    const a = r.action;
    switch (a.mode) {
      case 'guide': return `重定向 → ${a.redirectTo}`;
      case 'replace': return `${a.status} · ${truncate(a.body, 40)}`;
      case 'append': return a.where === 'header' ? `响应头 ${a.key}=${truncate(a.value, 30)}` : `${a.where} += ${truncate(a.value, 30)}`;
      case 'modify': return `${a.patches.length} 个字段补丁`;
      default: return '';
    }
  }
  function truncate(s, n) {
    s = String(s ?? '');
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  /* ── 流量日志 ── */
  let lastLogHead = null;
  async function renderLogs() {
    try {
      const logs = await api('GET', '/api/logs');
      const head = logs[0] ? logs[0].id : '';
      if (head === lastLogHead) return; // 无新流量则跳过渲染
      lastLogHead = head;
      const ul = $('#logs');
      $('#logs-empty').hidden = logs.length > 0;
      ul.innerHTML = logs.map((l) => `
        <li class="log">
          <span class="dot ${l.modified ? 'hit' : ''}" title="${l.modified ? '已改写' : '透传'}"></span>
          <span class="method">${esc(l.method)}</span>
          <span class="url">${esc(l.url)}</span>
          <span class="status ${l.status >= 400 ? 'err' : ''}">${l.status}</span>
        </li>
      `).join('');
    } catch (e) {
      console.error(e);
    }
  }

  /* ── 规则事件 ── */
  $('#rules').addEventListener('click', async (ev) => {
    const t = ev.target.closest('[data-toggle]');
    if (t) {
      try {
        await api('POST', `/api/rules/${encodeURIComponent(t.dataset.toggle)}/toggle`);
        await renderRules();
      } catch (e) { alert(e.message); }
      return;
    }
    const ed = ev.target.closest('[data-edit]');
    if (ed) { openEdit(ed.dataset.edit); return; }
    const del = ev.target.closest('[data-del]');
    if (del) {
      if (!confirm('确定删除这条规则？')) return;
      try {
        await api('DELETE', `/api/rules/${encodeURIComponent(del.dataset.del)}`);
        await renderRules();
      } catch (e) { alert(e.message); }
    }
  });

  $('#clear-logs').addEventListener('click', async () => {
    await api('DELETE', '/api/logs');
    lastLogHead = null;
    await renderLogs();
  });

  /* ── 弹窗与表单 ── */
  const modal = $('#modal');
  const actionFields = $('#action-fields');
  let editingId = null;

  function actionFieldsHtml(mode, a = {}) {
    switch (mode) {
      case 'guide':
        return `<label>重定向目标 URL
          <input id="f-redirectTo" value="${esc(a.redirectTo ?? '')}" placeholder="https://another.example.com/..." />
        </label>`;
      case 'replace':
        return `
          <div class="grid-2">
            <label>状态码 <input id="f-status" type="number" value="${a.status ?? 200}" /></label>
            <label>Content-Type <input id="f-contentType" value="${esc(a.contentType ?? 'application/json')}" placeholder="application/json" /></label>
          </div>
          <label>响应体
            <textarea id="f-body" placeholder='{"ok":false,"fake":true}'>${esc(a.body ?? '')}</textarea>
          </label>
          <label>响应头（JSON，可选）
            <textarea id="f-headers" class="hint" placeholder='{"X-Fake":"1"}'>${esc(a.headers ? JSON.stringify(a.headers) : '')}</textarea>
          </label>`;
      case 'append':
        return `
          <label>追加位置
            <select id="f-where">
              <option value="body" ${a.where === 'body' ? 'selected' : ''}>正文末尾 (body)</option>
              <option value="json" ${a.where === 'json' ? 'selected' : ''}>JSON 合并字段 (json)</option>
              <option value="header" ${a.where === 'header' ? 'selected' : ''}>响应头 (header)</option>
            </select>
          </label>
          <label id="f-key-wrap" ${a.where === 'header' ? '' : 'hidden'}>响应头名
            <input id="f-key" value="${esc(a.key ?? '')}" placeholder="X-Extra" />
          </label>
          <label>追加内容
            <textarea id="f-value" placeholder="body: 文本片段；json: {"field":123}；header: 值">${esc(a.value ?? '')}</textarea>
          </label>
          <p class="hint">json 位置会把内容作为对象合并进原始反馈；body 位置直接拼接文本。</p>`;
      case 'modify':
        return `
          <label>字段补丁（JSON 数组）
            <textarea id="f-patches" class="hint">${esc(a.patches ? JSON.stringify(a.patches, null, 2) : '[{"op":"set","path":"user.name","value":"\\"Bob\\""}]')}</textarea>
          </label>
          <p class="hint">op: set(设值) / merge(合并) / delete(删除)；path 用点号，如 user.name、items.0.id；value 为 JSON 字符串。</p>`;
      default:
        return '';
    }
  }

  function openModal(mode, rule) {
    editingId = rule ? rule.id : null;
    $('#modal-title').textContent = rule ? '编辑规则' : '新增规则';
    $('#f-id').value = rule ? rule.id : '';
    $('#f-name').value = rule ? rule.name : '';
    $('#f-type').value = rule ? rule.match.type : 'substring';
    $('#f-phase').value = rule ? rule.match.phase : 'response';
    $('#f-pattern').value = rule ? rule.match.pattern : '';
    $('#f-methods').value = rule ? rule.match.methods.join(',') : '';
    $('#f-mode').value = rule ? rule.action.mode : mode;
    $('#f-note').value = rule ? (rule.note || '') : '';
    renderActionFields(rule ? rule.action : {});
    modal.hidden = false;
  }

  function renderActionFields(a = {}) {
    actionFields.innerHTML = actionFieldsHtml($('#f-mode').value, a);
    const where = $('#f-where');
    if (where) {
      const syncKey = () => {
        $('#f-key-wrap').hidden = where.value !== 'header';
      };
      where.addEventListener('change', syncKey);
      syncKey();
    }
  }

  $('#f-mode').addEventListener('change', () => renderActionFields());

  $('#add-rule').addEventListener('click', () => openModal('replace'));
  $('#modal-close').addEventListener('click', () => { modal.hidden = true; });
  $('#modal-cancel').addEventListener('click', () => { modal.hidden = true; });
  modal.addEventListener('click', (ev) => { if (ev.target === modal) modal.hidden = true; });

  function collectAction() {
    const mode = $('#f-mode').value;
    switch (mode) {
      case 'guide':
        return { mode, redirectTo: $('#f-redirectTo').value.trim() };
      case 'replace': {
        const headers = {};
        const raw = $('#f-headers').value.trim();
        if (raw) Object.assign(headers, JSON.parse(raw));
        return {
          mode,
          status: Number($('#f-status').value) || 200,
          contentType: $('#f-contentType').value.trim() || undefined,
          headers,
          body: $('#f-body').value,
        };
      }
      case 'append': {
        const where = $('#f-where').value;
        return {
          mode,
          where,
          key: where === 'header' ? $('#f-key').value.trim() : undefined,
          value: $('#f-value').value,
        };
      }
      case 'modify':
        return { mode, patches: JSON.parse($('#f-patches').value || '[]') };
      default:
        throw new Error('未知模式');
    }
  }

  async function openEdit(id) {
    try {
      const rules = await api('GET', '/api/rules');
      const r = rules.find((x) => x.id === id);
      if (r) openModal(r.action.mode, r);
    } catch (e) { alert(e.message); }
  }

  $('#rule-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const payload = {
      name: $('#f-name').value.trim(),
      match: {
        pattern: $('#f-pattern').value.trim(),
        type: $('#f-type').value,
        phase: $('#f-phase').value,
        methods: $('#f-methods').value.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
      },
      action: collectAction(),
      note: $('#f-note').value.trim() || undefined,
    };
    try {
      if (editingId) {
        await api('PUT', `/api/rules/${encodeURIComponent(editingId)}`, payload);
      } else {
        await api('POST', '/api/rules', payload);
      }
      modal.hidden = true;
      await renderRules();
      await loadMeta();
    } catch (e) {
      alert('保存失败：' + e.message);
    }
  });

  /* ── 启动 ── */
  loadMeta();
  renderProxy();
  renderRules();
  renderLogs();
  setInterval(renderLogs, 2000);
})();
