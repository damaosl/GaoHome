/**
 * 高岛的眼睛 — 动作执行器（P0）
 *
 * 四种注入模式的纯逻辑实现：
 *   guide   引导 —— 请求方向重定向到自定义目标；响应方向返回 302 引导
 *   replace 截止更改 —— 完全切断原始反馈，返回自定义假反馈
 *   append  追加 —— 在原始反馈上附加额外内容
 *   modify  改返回值 —— 对 JSON 返回体做字段级增删改
 */
import type {
  AppendAction,
  JsonPatch,
  ProxyRequest,
  ProxyResponse,
  RequestActionResult,
  ResponseActionResult,
  Rule,
  RuleAction,
} from '../types.js';

const TEXT_CT = ['text/', 'application/json', 'application/xml', 'application/javascript', 'application/x-www-form-urlencoded'];

export function isTextContentType(ct: string): boolean {
  return TEXT_CT.some((t) => ct.toLowerCase().includes(t));
}

function buildResponse(status: number, headers: Record<string, string>, body: string, contentType?: string): ProxyResponse {
  const ct = contentType ?? headers['content-type'] ?? '';
  return {
    status,
    headers,
    body,
    contentType: ct,
    text: isTextContentType(ct),
  };
}

/** 尝试把字符串解析为 JSON 值，失败则原样返回字符串 */
export function parseValue(raw: string): unknown {
  const s = raw.trim();
  if (s === '') return s;
  try {
    return JSON.parse(s);
  } catch {
    return raw;
  }
}

function parseJsonBody(body: string): { ok: boolean; value: unknown } {
  try {
    return { ok: true, value: JSON.parse(body) };
  } catch {
    return { ok: false, value: null };
  }
}

/** 把 "a.b.0.c" 拆成路径段 */
function splitPath(path: string): string[] {
  return path
    .split('.')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function getByPath(obj: unknown, path: string): { found: boolean; parent: unknown; key: string | number } {
  const segs = splitPath(path);
  if (segs.length === 0) return { found: false, parent: null, key: '' };
  let cur: any = obj;
  for (let i = 0; i < segs.length - 1; i++) {
    if (cur === null || typeof cur !== 'object') return { found: false, parent: cur, key: segs[segs.length - 1] };
    const seg = segs[i];
    cur = cur[seg];
  }
  const last = segs[segs.length - 1];
  const idx = /^\d+$/.test(last) ? Number(last) : last;
  return { found: true, parent: cur, key: idx };
}

function setByPath(obj: unknown, path: string, value: unknown): unknown {
  const segs = splitPath(path);
  if (segs.length === 0) return obj;
  const root: any = obj === null || typeof obj !== 'object' ? {} : obj;
  let cur = root;
  for (let i = 0; i < segs.length - 1; i++) {
    const seg = segs[i];
    const nextIsIndex = /^\d+$/.test(segs[i + 1]);
    if (cur[seg] === null || typeof cur[seg] !== 'object') {
      cur[seg] = nextIsIndex ? [] : {};
    }
    cur = cur[seg];
  }
  const last = segs[segs.length - 1];
  const idx = /^\d+$/.test(last) ? Number(last) : last;
  cur[idx] = value;
  return root;
}

function deleteByPath(obj: unknown, path: string): unknown {
  const { found, parent, key } = getByPath(obj, path);
  if (!found) return obj;
  if (parent === null || typeof parent !== 'object') return obj;
  if (Array.isArray(parent) && typeof key === 'number') {
    parent.splice(key, 1);
  } else {
    delete (parent as any)[key];
  }
  return obj;
}

function deepMerge(target: any, source: any): any {
  if (source === null || typeof source !== 'object') return source;
  if (target === null || typeof target !== 'object') target = {};
  for (const k of Object.keys(source)) {
    const sv = source[k];
    if (sv !== null && typeof sv === 'object' && !Array.isArray(sv)) {
      target[k] = deepMerge(target[k] ?? {}, sv);
    } else {
      target[k] = sv;
    }
  }
  return target;
}

function applyPatch(obj: unknown, patch: JsonPatch): unknown {
  switch (patch.op) {
    case 'set':
      return setByPath(obj, patch.path, parseValue(patch.value ?? ''));
    case 'merge': {
      const target = getByPath(obj, patch.path);
      const merged = parseValue(patch.value ?? '');
      const next = deepMerge(
        typeof target.found && target.parent !== null ? target.parent : obj,
        merged,
      );
      if (target.found && target.parent !== null && typeof target.parent === 'object') {
        const key: any = target.key;
        (target.parent as any)[key] = next;
        return obj;
      }
      return next;
    }
    case 'delete':
      return deleteByPath(obj, patch.path);
    default:
      return obj;
  }
}

function applyAppend(res: ProxyResponse, action: AppendAction): ProxyResponse {
  const headers = { ...res.headers };
  switch (action.where) {
    case 'header': {
      if (action.key) headers[action.key.toLowerCase()] = action.value;
      return { ...res, headers };
    }
    case 'json': {
      const parsed = parseJsonBody(res.body);
      const extra = parseValue(action.value);
      if (parsed.ok && extra !== null && typeof extra === 'object') {
        const merged = deepMerge(parsed.value, extra);
        const body = JSON.stringify(merged, null, 2);
        headers['content-length'] = Buffer.byteLength(body).toString();
        return { ...res, headers, body, contentType: res.contentType || 'application/json', text: true };
      }
      // 非 JSON 原体则退化为文本追加
      return { ...res, headers, body: res.body + action.value };
    }
    case 'body':
    default: {
      const body = res.body + action.value;
      headers['content-length'] = Buffer.byteLength(body).toString();
      return { ...res, headers, body };
    }
  }
}

function applyModify(res: ProxyResponse, patches: JsonPatch[]): ProxyResponse {
  const parsed = parseJsonBody(res.body);
  if (!parsed.ok) return res; // 非 JSON 无法做字段级修改，保持原样
  let cur = parsed.value;
  for (const p of patches) cur = applyPatch(cur, p);
  const body = JSON.stringify(cur, null, 2);
  const headers = { ...res.headers, 'content-length': Buffer.byteLength(body).toString() };
  return { ...res, headers, body, text: true };
}

/** 请求方向动作 */
export function applyRequestAction(rule: Rule, req: ProxyRequest): RequestActionResult {
  const action: RuleAction = rule.action;
  switch (action.mode) {
    case 'guide':
      return { kind: 'redirect', url: action.redirectTo };
    case 'replace':
      return {
        kind: 'respond',
        response: buildResponse(action.status, action.headers, action.body, action.contentType),
      };
    case 'append':
    case 'modify':
    default:
      // 追加/改返回值需要响应方向，请求方向忽略
      return { kind: 'passthrough' };
  }
}

/** 响应方向动作 */
export function applyResponseAction(rule: Rule, res: ProxyResponse, _req: ProxyRequest): ResponseActionResult {
  const action: RuleAction = rule.action;
  switch (action.mode) {
    case 'guide': {
      // 引导：返回 302 把客户端引导到自定义方向
      const headers = { ...res.headers, location: action.redirectTo };
      return {
        kind: 'replace',
        response: buildResponse(302, headers, '', 'text/plain'),
      };
    }
    case 'replace':
      return {
        kind: 'replace',
        response: buildResponse(action.status, action.headers, action.body, action.contentType),
      };
    case 'append':
      return { kind: 'passthrough', response: applyAppend(res, action) };
    case 'modify':
      return { kind: 'passthrough', response: applyModify(res, action.patches) };
    default:
      return { kind: 'passthrough', response: res };
  }
}
