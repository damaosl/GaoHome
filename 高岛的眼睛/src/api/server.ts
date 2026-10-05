/**
 * 高岛的眼睛 — 控制 API 与静态 UI（P1）
 *
 * REST 接口（规则 CRUD、日志、元信息、CA 证书下载）+ 极简 Web UI 静态服务。
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {
  addRule, deleteRule, getDataFile, getRule, getRules, setRuleEnabled, updateRule, validateRule,
} from '../rules/store.js';
import { clearLogs, listLogs } from '../log.js';
import { getCACertPath } from '../proxy/ca.js';
import { getProxyStatus, setEnvProxy, setSystemProxy } from '../proxy/system-proxy.js';
import type { Rule } from '../types.js';

const UI_DIR = path.join(process.cwd(), 'ui');

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function sendJson(res: http.ServerResponse, status: number, data: unknown): void {
  const body = JSON.stringify(data);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(body);
}

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    const chunks: Buffer[] = [];
    req.on('data', (c: Buffer) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
  });
}

function serveStatic(res: http.ServerResponse, urlPath: string): void {
  let rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
  // 防目录穿越
  const file = path.normalize(path.join(UI_DIR, rel));
  if (!file.startsWith(UI_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }
  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
      res.end('Not Found');
      return;
    }
    const ext = path.extname(file).toLowerCase();
    res.writeHead(200, { 'content-type': MIME[ext] ?? 'application/octet-stream' });
    res.end(data);
  });
}

export function createApiServer(opts: { proxyPort: number; version: string }): http.Server {
  return http.createServer(async (req, res) => {
    const method = req.method ?? 'GET';
    const url = new URL(req.url ?? '/', 'http://localhost');
    const p = url.pathname;

    try {
      // ── API ──
      if (p === '/api/meta') {
        sendJson(res, 200, {
          name: '高岛的眼睛',
          version: opts.version,
          proxyPort: opts.proxyPort,
          caCertPath: getCACertPath(),
          dataFile: getDataFile(),
          ruleCount: getRules().length,
        });
        return;
      }

      if (p === '/api/ca.crt') {
        const cert = fs.readFileSync(getCACertPath());
        res.writeHead(200, {
          'content-type': 'application/x-x509-ca-cert',
          'content-disposition': 'attachment; filename="高岛的眼睛-ca.crt"',
        });
        res.end(cert);
        return;
      }

      if (p === '/api/rules' && method === 'GET') {
        sendJson(res, 200, getRules());
        return;
      }
      if (p === '/api/rules' && method === 'POST') {
        const raw = await readBody(req);
        let input: Omit<Rule, 'id'>;
        try {
          input = JSON.parse(raw);
          validateRule(input);
        } catch (e) {
          sendJson(res, 400, { error: (e as Error).message });
          return;
        }
        sendJson(res, 201, addRule(input));
        return;
      }

      const ruleMatch = p.match(/^\/api\/rules\/([^/]+)$/);
      if (ruleMatch) {
        const id = decodeURIComponent(ruleMatch[1]);
        if (method === 'PUT') {
          const raw = await readBody(req);
          try {
            const patch = JSON.parse(raw) as Partial<Rule>;
            sendJson(res, 200, updateRule(id, patch));
          } catch (e) {
            sendJson(res, 400, { error: (e as Error).message });
          }
          return;
        }
        if (method === 'DELETE') {
          const ok = deleteRule(id);
          sendJson(res, ok ? 200 : 404, { ok });
          return;
        }
      }

      const toggleMatch = p.match(/^\/api\/rules\/([^/]+)\/toggle$/);
      if (toggleMatch && method === 'POST') {
        const id = decodeURIComponent(toggleMatch[1]);
        const rule = getRule(id);
        if (!rule) {
          sendJson(res, 404, { error: '规则不存在' });
          return;
        }
        sendJson(res, 200, setRuleEnabled(id, !rule.enabled));
        return;
      }

      if (p === '/api/logs' && method === 'GET') {
        sendJson(res, 200, listLogs());
        return;
      }
      if (p === '/api/logs' && method === 'DELETE') {
        clearLogs();
        sendJson(res, 200, { ok: true });
        return;
      }

      // ── 一键代理 ──
      if (p === '/api/proxy' && method === 'GET') {
        sendJson(res, 200, await getProxyStatus('127.0.0.1', opts.proxyPort));
        return;
      }
      if (p === '/api/proxy' && method === 'POST') {
        const body = JSON.parse((await readBody(req)) || '{}') as { target?: string; enable?: boolean };
        const enable = !!body.enable;
        if (body.target === 'system') {
          await setSystemProxy(enable, '127.0.0.1', opts.proxyPort);
        } else if (body.target === 'env') {
          await setEnvProxy(enable, '127.0.0.1', opts.proxyPort);
        } else {
          sendJson(res, 400, { error: '未知目标：target 必须是 system 或 env' });
          return;
        }
        sendJson(res, 200, await getProxyStatus('127.0.0.1', opts.proxyPort));
        return;
      }

      if (p.startsWith('/api/')) {
        sendJson(res, 404, { error: 'Not Found' });
        return;
      }

      // ── 静态 UI ──
      if (method === 'GET') {
        serveStatic(res, p);
        return;
      }

      res.writeHead(405);
      res.end();
    } catch (e) {
      sendJson(res, 500, { error: (e as Error).message });
    }
  });
}
