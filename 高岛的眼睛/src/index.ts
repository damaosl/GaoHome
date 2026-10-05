/**
 * 高岛的眼睛 — 入口（P2）
 *
 * 组装：代理核心 + 控制 API/UI + 规则存储 + 日志。
 */
import { parseArgs } from './config.js';
import { createProxyServer } from './proxy/server.js';
import { createApiServer } from './api/server.js';
import { getRules } from './rules/store.js';
import { addLog } from './log.js';
import { getCACertPath } from './proxy/ca.js';

const config = parseArgs(process.argv);

const proxy = createProxyServer({ getRules, onLog: addLog }, { insecure: config.insecure });
const api = createApiServer({ proxyPort: config.proxyPort, version: config.version });

proxy.listen(config.proxyPort, () => {
  console.log('');
  console.log('  高岛的眼睛 — 极简假反馈拦截工具');
  console.log('  ────────────────────────────────');
  console.log(`  代理端口   http://127.0.0.1:${config.proxyPort}   ← 应用/接口/插件指向这里`);
  console.log(`  控制台     http://127.0.0.1:${config.apiPort}   ← 打开这里管理规则`);
  console.log(`  CA 证书    ${getCACertPath()}`);
  console.log('  ────────────────────────────────');
  console.log('  提示：拦截 HTTPS 需先在系统/浏览器信任上述 CA 证书');
  console.log('');
});

api.listen(config.apiPort, () => {
  /* 控制台已就绪 */
});

proxy.on('error', (err) => {
  console.error('[高岛的眼睛] 代理错误：', err.message);
  process.exit(1);
});
api.on('error', (err) => {
  console.error('[高岛的眼睛] 控制台错误：', err.message);
  process.exit(1);
});
