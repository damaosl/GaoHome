/**
 * 端到端测试：起假上游 + 启动 高岛的眼睛，通过代理验证四种模式。
 * 运行：node scripts/e2e.mjs（需先 npm run build）
 */
import http from 'node:http';
import { spawn } from 'node:child_process';

const UP = 9101, PROXY = 9102, API = 9103;

const upstream = http.createServer((req, res) => {
  const json = (o) => { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)); };
  const text = (s) => { res.writeHead(200, { 'content-type': 'text/plain' }); res.end(s); };
  switch (req.url) {
    case '/replace': return json({ real: 1 });
    case '/append': return json({ real: 1 });
    case '/modify': return json({ user: { name: 'Alice' }, secret: 'x' });
    case '/redirect': return text('should-not-be-reached');
    case '/target': return text('target-reached');
    default: return text('unknown');
  }
});

const listen = (s, port) => new Promise((r) => s.listen(port, () => r()));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, path, body) {
  const res = await fetch(`http://127.0.0.1:${API}${path}`, {
    method,
    headers: body !== undefined ? { 'content-type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

function viaProxy(fullUrl) {
  return new Promise((resolve, reject) => {
    const u = new URL(fullUrl);
    const req = http.request(
      { host: '127.0.0.1', port: PROXY, path: fullUrl, method: 'GET', headers: { host: u.host } },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
      },
    );
    req.on('error', reject);
    req.end();
  });
}

let failed = 0;
function check(name, cond, detail) {
  if (cond) console.log(`  ✓ ${name}`);
  else { failed++; console.error(`  ✗ ${name}`, detail ?? ''); }
}

async function waitForApi() {
  for (let i = 0; i < 50; i++) {
    try { await api('GET', '/api/meta'); return; } catch { await sleep(200); }
  }
  throw new Error('API 未就绪');
}

await listen(upstream, UP);

const child = spawn('node', ['dist/index.js', '-p', String(PROXY), '-a', String(API)], {
  cwd: process.cwd(),
  env: { ...process.env, MOCKFEED_DATA: '/tmp/高岛的眼睛-e2e-rules.json' },
  stdio: 'ignore',
});
await waitForApi();

try {
  // 1. replace 截止更改
  await api('POST', '/api/rules', {
    name: '替换', enabled: true,
    match: { pattern: '/replace', type: 'substring', methods: [], phase: 'response' },
    action: { mode: 'replace', status: 200, contentType: 'application/json', headers: {}, body: '{"fake":true}' },
  });
  const r1 = await viaProxy(`http://127.0.0.1:${UP}/replace`);
  check('replace：截止原始反馈，返回假反馈', r1.body === '{"fake":true}', r1.body);

  // 2. append 追加（json 合并）
  await api('POST', '/api/rules', {
    name: '追加', enabled: true,
    match: { pattern: '/append', type: 'substring', methods: [], phase: 'response' },
    action: { mode: 'append', where: 'json', value: '{"extra":2}' },
  });
  const r2 = await viaProxy(`http://127.0.0.1:${UP}/append`);
  check('append：原始反馈保留且新增字段', r2.body.includes('"real"') && r2.body.includes('"extra": 2'), r2.body);

  // 3. modify 改返回值
  await api('POST', '/api/rules', {
    name: '改值', enabled: true,
    match: { pattern: '/modify', type: 'substring', methods: [], phase: 'response' },
    action: { mode: 'modify', patches: [{ op: 'set', path: 'user.name', value: '"Bob"' }, { op: 'delete', path: 'secret' }] },
  });
  const r3 = await viaProxy(`http://127.0.0.1:${UP}/modify`);
  check('modify：字段改值 + 删除', r3.body.includes('"Bob"') && !r3.body.includes('secret'), r3.body);

  // 4. guide 引导（请求方向重定向）
  await api('POST', '/api/rules', {
    name: '引导', enabled: true,
    match: { pattern: '/redirect', type: 'substring', methods: [], phase: 'request' },
    action: { mode: 'guide', redirectTo: `http://127.0.0.1:${UP}/target` },
  });
  const r4 = await viaProxy(`http://127.0.0.1:${UP}/redirect`);
  check('guide：请求被引导到新目标', r4.body === 'target-reached', r4.body);

  // 5. 日志记录
  const logs = await api('GET', '/api/logs');
  check('日志记录了 4 条流量', logs.length === 4, logs.length);
  check('日志标记了改写', logs.filter((l) => l.modified).length === 4, logs.map((l) => l.modified));
} finally {
  child.kill();
  upstream.close();
}

if (failed > 0) { console.error(`\n${failed} 项失败`); process.exit(1); }
console.log('\n端到端全部通过');
