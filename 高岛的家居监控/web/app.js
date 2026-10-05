/* 高岛的家居监控 —— 看板逻辑（极简，无任何外部依赖） */
"use strict";

const $ = (s) => document.querySelector(s);
const MAX_BUFFER = 5000;

let entries = [];        // 前端缓冲（新 → 旧）
let paused = false;
let ws = null;
let wsTimer = null;
let countNew = 0;        // 本次会话新接收条数

/* ---------- 工具 ---------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmtBytes(n) {
  n = Number(n) || 0;
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
  return (n / 1048576).toFixed(2) + " MB";
}
function fmtTime(s) {
  if (!s) return "-";
  const d = new Date(s);
  return isNaN(d) ? "-" : d.toLocaleTimeString("zh-CN", { hour12: false });
}
function prettyBody(text) {
  if (!text) return "";
  try {
    const j = JSON.parse(text);
    return JSON.stringify(j, null, 2);
  } catch (e) { return text; }
}
function methodClass(m) {
  const M = (m || "").toUpperCase();
  return ["GET", "POST", "PUT", "DELETE"].includes(M) ? "m-" + M : "m-other";
}
function statusClass(s) {
  s = Number(s) || 0;
  if (s >= 200 && s < 300) return "s-2";
  if (s >= 300 && s < 400) return "s-3";
  if (s >= 400 && s < 500) return "s-4";
  if (s >= 500) return "s-5";
  return "s-0";
}

/* ---------- WebSocket ---------- */
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    $("#wsState").textContent = "WS: 已连接";
    $("#liveDot").classList.add("on");
    ws && ws.send(JSON.stringify({ event: "pong" }));
  };
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.event === "init") {
      entries = msg.data.entries || [];
      applyStats(msg.data.stats);
      renderAll();
    } else if (msg.event === "entry") {
      countNew++;
      entries.unshift(msg.data);
      if (entries.length > MAX_BUFFER) entries.length = MAX_BUFFER;
      bumpCounters(msg.data);
      if (!paused) renderAll();
      else $("#feedMeta").textContent = `已暂停 · 缓冲 ${entries.length} 条`;
      addFeedback(msg.data);
    }
  };
  ws.onclose = () => {
    $("#wsState").textContent = "WS: 已断开，2 秒后重连…";
    $("#liveDot").classList.remove("on");
    $("#liveDot").classList.add("err");
    wsTimer = setTimeout(connectWS, 2000);
  };
  ws.onerror = () => ws && ws.close();
}

/* ---------- 统计 ---------- */
const local = { total: 0, errors: 0, alerts: 0, warns: 0 };
function bumpCounters(e) {
  local.total++;
  if (e.status >= 400) local.errors++;
  if (e.level === "alert") local.alerts++;
  if (e.level === "warn") local.warns++;
  $("#stTotal").textContent = local.total;
  $("#stErrors").textContent = local.errors;
  $("#stAlerts").textContent = local.alerts;
  $("#stWarns").textContent = local.warns;
}
function applyStats(st) {
  if (!st) return;
  $("#stAvg").textContent = st.avg_ms != null ? st.avg_ms + " ms" : "-";
  $("#stTraffic").textContent = fmtBytes(st.traffic);
}
function refreshStats() {
  fetch("/api/stats").then(r => r.json()).then(d => {
    if (d.code === 0) {
      applyStats(d);
      local.total = Math.max(local.total, d.total);
      local.errors = Math.max(local.errors, d.errors);
      local.alerts = Math.max(local.alerts, d.alerts);
      local.warns = Math.max(local.warns, d.warns);
      $("#stTotal").textContent = local.total;
      $("#stErrors").textContent = local.errors;
      $("#stAlerts").textContent = local.alerts;
      $("#stWarns").textContent = local.warns;
    }
  }).catch(() => {});
}

/* ---------- 筛选与渲染 ---------- */
function filters() {
  const st = $("#fStatus").value;
  const lv = $("#fLevel").value;
  const host = $("#fHost").value.trim().toLowerCase();
  const q = $("#fSearch").value.trim().toLowerCase();
  const m = $("#fMethod").value;
  return (e) => {
    if (m && e.method !== m) return false;
    if (st !== "") {
      const s = Number(e.status) || 0;
      const cls = s === 0 ? 0 : Math.floor(s / 100);
      if (cls !== Number(st)) return false;
    }
    if (lv && e.level !== lv) return false;
    if (host && !(e.host || "").toLowerCase().includes(host)) return false;
    if (q) {
      const hay = [e.url, e.host, e.path, e.response_body, e.request_body, e.content_type]
        .map(x => (x || "").toLowerCase()).join("\n");
      if (!hay.includes(q)) return false;
    }
    return true;
  };
}

function renderAll() {
  const f = filters();
  const list = entries.filter(f).slice(0, 800);
  const ul = $("#feedList");
  ul.innerHTML = "";
  $("#feedEmpty").style.display = entries.length ? "none" : "block";
  for (const e of list) ul.appendChild(row(e));
  $("#listCount").textContent = `显示 ${list.length} / 缓冲 ${entries.length}`;
  $("#feedMeta").textContent = paused ? "" : `本次会话 +${countNew}`;
}

function row(e) {
  const li = document.createElement("li");
  li.dataset.id = e.id;
  li.innerHTML = `
    <span class="lv ${esc(e.level || "info")}"></span>
    <span class="m-badge ${methodClass(e.method)}">${esc(e.method || "-")}</span>
    <span class="s-badge ${statusClass(e.status)}">${e.status || "-"}</span>
    <div class="entry-main">
      <div class="entry-url">${esc(e.host || "")}${esc(e.path || "")}</div>
      <div class="entry-meta">
        ${e.duration_ms != null ? esc(e.duration_ms + " ms") : "-"} ·
        ${esc(fmtBytes(e.size_response))} ·
        ${esc(fmtTime(e.timestamp || e.created_at))} ·
        ${esc(e.platform || "?")}
      </div>
    </div>`;
  li.onclick = () => {
    document.querySelectorAll("#feedList li").forEach(x => x.classList.remove("active"));
    li.classList.add("active");
    loadDetail(e.id);
  };
  return li;
}

  /* ---------- 加载历史（超出内存缓冲的旧数据） ---------- */
  let loadingMore = false;
  function loadMore() {
    if (loadingMore) return;
    loadingMore = true;
    const params = new URLSearchParams({
      offset: String(entries.length), limit: "200",
      method: $("#fMethod").value, status: $("#fStatus").value,
      host: $("#fHost").value.trim(), search: $("#fSearch").value.trim(),
      level: $("#fLevel").value,
    });
    fetch(`/api/entries?${params}`).then(r => r.json()).then(d => {
      loadingMore = false;
      if (d.code !== 0 || !d.entries.length) {
        $("#btnMore").textContent = d.total <= entries.length ? "↓ 已到最早记录" : "↓ 加载历史";
        return;
      }
      const have = new Set(entries.map(x => x.id));
      for (const e of d.entries) if (!have.has(e.id)) entries.push(e);
      renderAll();
    }).catch(() => { loadingMore = false; });
  }

  /* ---------- 详情 ---------- */
  let curEntry = null;
  let curSub = "request";

function loadDetail(id) {
  fetch(`/api/entries/${id}`).then(r => r.json()).then(d => {
    if (d.code !== 0) return;
    curEntry = d.entry;
    renderDetail();
  }).catch(() => {});
}

function kvTable(headers) {
  const keys = Object.keys(headers || {});
  if (!keys.length) return `<div class="empty">（无）</div>`;
  return `<table class="kv">` + keys.map(k =>
    `<tr><td>${esc(k)}</td><td>${esc(headers[k])}</td></tr>`).join("") + `</table>`;
}

function renderDetail() {
  const e = curEntry;
  if (!e) return;
  const box = $("#tabDetail");
  box.innerHTML = `
    <div class="d-summary">
      <div style="display:flex;gap:10px;align-items:center">
        <span class="m-badge ${methodClass(e.method)}">${esc(e.method)}</span>
        <span class="s-badge ${statusClass(e.status)}">${e.status || "-"}</span>
        <b style="font-size:13px">${esc(e.status_text || "")}</b>
      </div>
      <div class="u">${esc(e.url)}</div>
      <div class="d-meta">
        <span>耗时 <b>${esc(e.duration_ms)} ms</b></span>
        <span>响应 <b>${esc(fmtBytes(e.size_response))}</b></span>
        <span>请求 <b>${esc(fmtBytes(e.size_request))}</b></span>
        <span>服务器 <b>${esc(e.server_ip || "-")}</b></span>
        <span>协议 <b>${esc(e.http_version || "-")}</b></span>
        <span>平台 <b>${esc(e.platform || "-")}</b></span>
        <span>规则 <b>${esc(e.rule || "-")}</b></span>
      </div>
    </div>
    <div class="sub-tabs">
      <button class="sub-tab ${curSub === "request" ? "active" : ""}" data-s="request">请求</button>
      <button class="sub-tab ${curSub === "response" ? "active" : ""}" data-s="response">响应</button>
    </div>
    <div id="subBody"></div>
    ${(e.feedback && e.feedback.length) ? `
      <div style="margin:14px 0 8px;font-size:12px;color:var(--dim)">分析反馈（${e.feedback.length}）</div>
      ${e.feedback.map(fb => `
        <div class="fb-card ${esc(fb.level || "info")}">
          <div class="fb-head"><span class="t">${esc(fb.title)}</span></div>
          <div class="fb-detail">${esc(fb.detail)}</div>
        </div>`).join("")}
    ` : `<div style="margin:14px 0;font-size:12px;color:var(--dim)">分析反馈：未发现异常</div>`}`;
  box.querySelectorAll(".sub-tab").forEach(b =>
    b.onclick = () => { curSub = b.dataset.s; renderDetail(); });
  const body = box.querySelector("#subBody");
  if (curSub === "request") {
    body.innerHTML = `<div style="margin-bottom:8px;font-size:12px;color:var(--dim)">请求头</div>` +
      kvTable(e.request_headers) +
      `<div style="margin:12px 0 8px;font-size:12px;color:var(--dim)">请求体</div>` +
      (e.request_body ? `<pre class="body">${esc(prettyBody(e.request_body))}</pre>` : `<div class="empty">（无请求体）</div>`);
  } else {
    body.innerHTML = `<div style="margin-bottom:8px;font-size:12px;color:var(--dim)">响应头</div>` +
      kvTable(e.response_headers) +
      `<div style="margin:12px 0 8px;font-size:12px;color:var(--dim)">响应体${e.body_encoding === "base64" ? "（二进制，base64）" : ""}</div>` +
      (e.response_body ? `<pre class="body">${esc(prettyBody(e.response_body))}</pre>` : `<div class="empty">（无响应体）</div>`);
  }
}

/* ---------- 反馈面板 ---------- */
function addFeedback(e) {
  if (!e.feedback || !e.feedback.length) return;
  if ($("#fbBadge")) {
    const n = parseInt($("#fbBadge").textContent || "0") + e.feedback.length;
    $("#fbBadge").textContent = n;
  }
}
function renderFeedback() {
  const box = $("#tabFeedback");
  box.innerHTML = "";
  fetch("/api/feedback?limit=200").then(r => r.json()).then(d => {
    const items = (d.items || []).filter(x => Array.isArray(x.feedback) && x.feedback.length);
    if (!items.length) {
      box.innerHTML = `<div class="empty">暂无反馈。发现异常（错误码 / 慢响应 / 敏感数据等）会自动出现在这里。</div>`;
      return;
    }
    for (const it of items) {
      for (const fb of it.feedback) {
        const card = document.createElement("div");
        card.className = "fb-card " + (fb.level || "info");
        card.innerHTML = `
          <div class="fb-head"><span class="t">${esc(fb.title || "")}</span>
          <span style="color:var(--dim);font-size:11px;font-weight:400">${esc(fmtTime(it.created_at))}</span></div>
          <div class="fb-detail">${esc(fb.detail || "")}</div>
          <div class="fb-src">${esc(it.method)} ${esc(it.status || "-")} · ${esc(it.url || "")}</div>`;
        card.onclick = () => loadDetail(it.id);
        box.appendChild(card);
      }
    }
  }).catch(() => {});
}

/* ---------- 事件绑定 ---------- */
function bind() {
  ["fMethod", "fStatus", "fLevel", "fHost", "fSearch"].forEach(id =>
    $("#" + id).addEventListener("input", renderAll));

  $("#btnPause").onclick = () => {
    paused = !paused;
    $("#btnPause").textContent = paused ? "▶ 继续" : "⏸ 暂停";
    renderAll();
  };

  $("#btnMore").onclick = loadMore;

  /* ---------- 独立抓包 ---------- */
  function refreshCapture() {
    fetch("/api/capture/status").then(r => r.json()).then(d => {
      const running = d.running;
      $("#btnCapture").textContent = running ? "■ 停止抓包" : "独立抓包";
      $("#btnCapture").classList.toggle("on", running);
      $("#capState").textContent = running
        ? `内置代理: 127.0.0.1:${d.port} · HTTPS证书: ${d.cert}`
        : "";
    }).catch(() => {});
  }

  $("#btnCapture").onclick = () => {
    fetch("/api/capture/status").then(r => r.json()).then(d => {
      const target = d.running ? "/api/capture/stop" : "/api/capture/start";
      fetch(target, { method: "POST" }).then(r2 => r2.json()).then(res => {
        refreshCapture();
        if (res.running) {
          alert("独立抓包已启动！\n\n把需要抓包的设备/浏览器代理设为:\n  127.0.0.1:" + res.port +
            "\n\nHTTPS 解密需安装证书（首次启动自动生成）:\n  " + res.cert);
        }
      });
    });
  };

  $("#btnClear").onclick = () => {
    if (!confirm("清空全部抓包数据？（仅清除本工具数据库中的记录）")) return;
    fetch("/api/clear", { method: "POST" }).then(r => r.json()).then(() => {
      entries = [];
      local.total = local.errors = local.alerts = local.warns = 0;
      countNew = 0;
      renderAll();
      refreshStats();
    });
  };

  document.querySelectorAll(".tab").forEach(t =>
    t.onclick = () => {
      document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      $("#tabDetail").classList.toggle("hidden", t.dataset.tab !== "detail");
      $("#tabFeedback").classList.toggle("hidden", t.dataset.tab !== "feedback");
      if (t.dataset.tab === "feedback") {
        renderFeedback();
        $("#fbBadge").textContent = "0";
      }
    });
}

/* ---------- 启动 ---------- */
bind();
connectWS();
setInterval(refreshStats, 5000);
setInterval(refreshCapture, 5000);
setInterval(() => { if (ws && ws.readyState === 1) ws.send(JSON.stringify({ event: "pong" })); }, 25000);
