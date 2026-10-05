/**
 * 高岛的眼睛 — 流量日志（P2）
 *
 * 内存环形缓冲，记录每次拦截的流量与命中的规则。
 */
import type { LogEntry } from './types.js';

const MAX_ENTRIES = 500;
const entries: LogEntry[] = [];

export function addLog(entry: LogEntry): LogEntry {
  entries.push(entry);
  if (entries.length > MAX_ENTRIES) entries.shift();
  return entry;
}

export function listLogs(): LogEntry[] {
  return [...entries].reverse();
}

export function clearLogs(): void {
  entries.length = 0;
}
