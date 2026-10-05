/**
 * 高岛的眼睛 — 代理核心（P0）
 *
 * HTTP 正向代理 + HTTPS MITM 拦截管道：
 *   1. HTTP 请求 / 解密后的 HTTPS 请求统一进入 handleForward
 *   2. 请求方向规则：guide(重定向) / replace(截止短路)
 *   3. 转发到（可能被重定向的）目标
 *   4. 响应方向规则：guide(302 引导) / replace(截止更改) / append(追加) / modify(改返回值)
 *
 * CONNECT 隧道仅在「目标主机命中某条启用规则」时才做 MITM，
 * 其余域名直接透传（保留真实证书，不产生告警）。
 */
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';
import { randomUUID } from 'node:crypto';
import { minimatch } from 'minimatch';
import { matchRules } from '../rules/matcher.js';
import { applyRequestAction, applyResponseAction, isTextContentType } from './apply.js';
import { ensureCA, getHostCert } from './ca.js';
import type {
  LogEntry,
  MatchType,
  ProxyRequest,
  ProxyResponse,
  Rule,
} from '../types.js';

const MAX_BODY = 10 * 1024 * 1024; // 可缓冲的请求/响应体上限（10MB）

export interface ProxyHooks {
  getRules: () => Rule[];
  onLog: (entry: LogEntry) => void;
}

function flattenHeaders(h: http.IncomingHttpHeaders): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(h)) {
    if (v === undefined) continue;
    out[k] = Array.isArray(v) ? v.join(', ') : String(v);
  }
  return out;
}

function bufferStream(stream: NodeJS.ReadableStream, maxBytes: number): Promise<Buffer | null> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    let over = false;
    stream.on('data', (c: Buffer) => {
      size += c.length;
      if (over) return;
      if (size <= maxBytes) chunks.push(c);
      else {
        over = true;
        chunks.length = 0;
      }
    });
    stream.on('end', () => resolve(over ? null : Buffer.concat(chunks)));
    stream.on('error', reject);
  });
}

interface UpstreamResult {
  status: number;
  headers: Record<string, string>;
  rawHeaders: http.IncomingHttpHeaders;
  body: Buffer;
  text: boolean;
  contentType: string;
}

function forward(
  targetUrl: string,
  method: string,
  headers: Record<string, string>,
  body: Buffer,
  insecure: boolean,
): Promise<UpstreamResult> {
  return new Promise((resolve, reject) => {
    let u: URL;
    try {
      u = new URL(targetUrl);
    } catch (e) {
      reject(e);
      return;
    }
    const isHttps = u.protocol === 'https:';
    const mod = isHttps ? https : http;

    const outHeaders: Record<string, string> = {
      ...headers,
      host: u.host,
      'accept-encoding': 'identity', // 确保上游不压缩，便于改写正文
    };
    delete outHeaders['proxy-connection'];
    delete outHeaders['proxy-authorization'];

    const req = mod.request(
      {
        protocol: u.protocol,
        hostname: u.hostname,
        port: u.port || (isHttps ? 443 : 80),
        path: u.pathname + u.search,
        method,
        headers: outHeaders,
        rejectUnauthorized: !insecure,
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (c: Buffer) => chunks.push(c));
        res.on('end', () => {
          const buf = Buffer.concat(chunks);
          const ct = String(res.headers['content-type'] ?? '');
          const ce = String(res.headers['content-encoding'] ?? '').toLowerCase();
          const text = isTextContentType(ct) && (!ce || ce === 'identity');
          resolve({
            status: res.statusCode ?? 200,
            headers: flattenHeaders(res.headers),
            rawHeaders: res.headers,
            body: buf,
            text,
            contentType: ct,
          });
        });
        res.on('error', reject);
      },
    );
    req.on('error', reject);
    if (body.length) req.write(body);
    req.end();
  });
}

/** 提取模式中的主机段（substring / glob 用） */
function patternHost(pattern: string): string {
  return pattern.replace(/^[a-z]+:\/\//i, '').split('/')[0];
}

/** 判断某主机是否需要 MITM 拦截 */
function hostShouldIntercept(rules: Rule[], hostname: string): boolean {
  const probeUrls = [hostname, `https://${hostname}`, `https://${hostname}/`];
  return rules.some((r) => {
    if (!r.enabled) return false;
    const p = r.match.pattern;
    const t: MatchType = r.match.type;
    if (t === 'regex') {
      // 正则无法可靠提取主机，用主机相关的若干形式试探
      try {
        const re = new RegExp(p);
        return probeUrls.some((u) => re.test(u));
      } catch {
        return false;
      }
    }
    const hostPart = patternHost(p);
    if (!hostPart) return false;
    if (t === 'glob') return minimatch(hostname, hostPart);
    return (
      hostname === hostPart ||
      hostname.endsWith('.' + hostPart) ||
      hostPart === '*' ||
      hostname.includes(hostPart) ||
      hostPart.includes(hostname)
    );
  });
}

function send(
  res: http.ServerResponse,
  status: number,
  headers: Record<string, string> | http.OutgoingHttpHeaders,
  body: Buffer,
  modified: boolean,
): void {
  const h: http.OutgoingHttpHeaders = { ...headers };
  if (modified) {
    h['content-length'] = String(body.length);
    delete h['transfer-encoding'];
    delete h['content-encoding'];
    delete h['etag'];
  }
  try {
    res.writeHead(status, h);
    res.end(body);
  } catch {
    try {
      res.end();
    } catch {
      /* 客户端已断开 */
    }
  }
}

export function createProxyServer(
  hooks: ProxyHooks,
  opts: { insecure?: boolean } = {},
): http.Server {
  ensureCA();
  const insecure = opts.insecure ?? false;

  async function handleForward(
    clientReq: http.IncomingMessage,
    clientRes: http.ServerResponse,
    protocol: 'http' | 'https',
    mitmHostname?: string,
    mitmPort?: number,
  ): Promise<void> {
    const start = Date.now();
    const method = clientReq.method ?? 'GET';
    const matched: string[] = [];
    let modified = false;

    let url: string;
    if (protocol === 'https' && mitmHostname) {
      const portStr = mitmPort && mitmPort !== 443 ? `:${mitmPort}` : '';
      url = `https://${mitmHostname}${clientReq.url ?? '/'}`;
    } else if (clientReq.url && /^https?:\/\//i.test(clientReq.url)) {
      url = clientReq.url; // 绝对形式（普通 HTTP 正向代理）
    } else {
      url = `http://${clientReq.headers.host ?? 'localhost'}${clientReq.url ?? '/'}`;
    }

    const reqHeaders = flattenHeaders(clientReq.headers);
    const bodyBuf = (await bufferStream(clientReq, MAX_BODY)) ?? Buffer.alloc(0);
    const reqData: ProxyRequest = { method, url, headers: reqHeaders, body: bodyBuf.toString('utf8') };

    try {
      // ── 请求方向 ──
      let targetUrl = url;
      let shortCircuit: ProxyResponse | null = null;
      for (const r of matchRules(hooks.getRules(), { url, method, phase: 'request' })) {
        const result = applyRequestAction(r, reqData);
        if (result.kind === 'passthrough') continue;
        matched.push(r.name);
        if (result.kind === 'redirect') {
          targetUrl = result.url;
          modified = true;
        } else if (result.kind === 'respond') {
          shortCircuit = result.response;
          modified = true;
          break;
        }
      }

      if (shortCircuit) {
        send(clientRes, shortCircuit.status, shortCircuit.headers, Buffer.from(shortCircuit.body), true);
        hooks.onLog({
          id: randomUUID(), ts: start, method, url, phase: 'request',
          status: shortCircuit.status, matchedRules: matched, modified: true,
          durationMs: Date.now() - start,
        });
        return;
      }

      // ── 转发 ──
      let up: UpstreamResult;
      try {
        up = await forward(targetUrl, method, reqHeaders, bodyBuf, insecure);
      } catch (e) {
        const msg = `Bad Gateway: ${(e as Error).message}`;
        send(clientRes, 502, { 'content-type': 'text/plain' }, Buffer.from(msg), true);
        hooks.onLog({
          id: randomUUID(), ts: start, method, url, phase: 'response',
          status: 502, matchedRules: matched, modified: false,
          durationMs: Date.now() - start,
        });
        return;
      }

      // ── 响应方向 ──
      let finalStatus = up.status;
      let finalHeaders: Record<string, string> = up.headers;
      let finalRawHeaders: http.IncomingHttpHeaders = up.rawHeaders;
      let finalBody = up.body;
      let finalText = up.text;

      for (const r of matchRules(hooks.getRules(), { url, method, phase: 'response' })) {
        const mode = r.action.mode;
        // 追加/改返回值只对文本体有意义；二进制或压缩体跳过
        if (!finalText && (mode === 'append' || mode === 'modify')) continue;

        const cur: ProxyResponse = {
          status: finalStatus,
          headers: finalHeaders,
          body: finalText ? finalBody.toString('utf8') : '',
          text: finalText,
          contentType: finalHeaders['content-type'] ?? '',
        };
        const result = applyResponseAction(r, cur, reqData);
        matched.push(r.name);
        if (result.kind === 'replace') {
          finalStatus = result.response.status;
          finalHeaders = result.response.headers;
          finalRawHeaders = result.response.headers;
          finalBody = Buffer.from(result.response.body);
          finalText = true;
          modified = true;
        } else {
          finalStatus = result.response.status;
          finalHeaders = result.response.headers;
          finalRawHeaders = result.response.headers;
          finalBody = Buffer.from(result.response.body);
          finalText = result.response.text;
          modified = true;
        }
      }

      const outHeaders: http.OutgoingHttpHeaders = modified
        ? { ...finalHeaders }
        : { ...finalRawHeaders };
      send(clientRes, finalStatus, outHeaders, finalBody, modified);

      hooks.onLog({
        id: randomUUID(), ts: start, method, url, phase: 'response',
        status: finalStatus, matchedRules: matched, modified,
        durationMs: Date.now() - start,
      });
    } catch (err) {
      if (!clientRes.headersSent) {
        send(clientRes, 500, { 'content-type': 'text/plain' }, Buffer.from(`高岛的眼睛 error: ${(err as Error).message}`), true);
      }
      try {
        clientRes.end();
      } catch {
        /* ignore */
      }
    }
  }

  function handleConnect(
    clientReq: http.IncomingMessage,
    clientSocket: net.Socket,
    head: Buffer,
  ): void {
    const hostname = (clientReq.url ?? '').split(':')[0];
    const port = parseInt((clientReq.url ?? '').split(':')[1]) || 443;

    if (!hostname || !hostShouldIntercept(hooks.getRules(), hostname)) {
      // 透传隧道：不拦截，客户端见到真实证书
      const upstream = net.connect(port, hostname, () => {
        clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        if (head && head.length) upstream.write(head);
        upstream.pipe(clientSocket);
        clientSocket.pipe(upstream);
      });
      upstream.on('error', () => {
        try {
          clientSocket.destroy();
        } catch {
          /* ignore */
        }
      });
      clientSocket.on('error', () => {
        try {
          upstream.destroy();
        } catch {
          /* ignore */
        }
      });
      return;
    }

    // MITM 拦截
    const tlsServer = new tls.Server({
      SNICallback: (servername, cb) => {
        try {
          const c = getHostCert(servername || hostname);
          cb(null, tls.createSecureContext({ key: c.key, cert: c.cert }));
        } catch (e) {
          cb(e as Error);
        }
      },
    });

    tlsServer.on('secureConnection', (tlsSocket) => {
      const httpServer = http.createServer((req, res) => {
        void handleForward(req, res, 'https', hostname, port);
      });
      httpServer.emit('connection', tlsSocket);
    });
    tlsServer.on('clientError', (_err, socket) => {
      try {
        socket.destroy();
      } catch {
        /* ignore */
      }
    });

    clientSocket.write('HTTP/1.1 200 Connection Established\r\nProxy-Agent: 高岛的眼睛\r\n\r\n');
    tlsServer.emit('connection', clientSocket);
  }

  const server = http.createServer((req, res) => {
    void handleForward(req, res, 'http');
  });
  server.on('connect', (req, socket, head) => handleConnect(req, socket as net.Socket, head));
  server.on('clientError', (_err, socket) => {
    try {
      socket.destroy();
    } catch {
      /* ignore */
    }
  });

  return server;
}
