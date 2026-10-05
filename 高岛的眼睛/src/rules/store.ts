/**
 * 高岛的眼睛 — 规则存储（P1）
 *
 * 内存规则表 + JSON 文件持久化。提供 CRUD、启停切换与轻量校验。
 */
import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import type { AppendAction, GuideAction, JsonPatch, ModifyAction, ReplaceAction, Rule } from '../types.js';

const DATA_FILE = process.env.MOCKFEED_DATA ?? path.join(process.cwd(), 'data', 'rules.json');

let rules: Rule[] = [];
let loaded = false;

function ensureLoaded(): void {
  if (loaded) return;
  loaded = true;
  try {
    if (fs.existsSync(DATA_FILE)) {
      const parsed = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
      if (Array.isArray(parsed)) rules = parsed;
    }
  } catch (e) {
    console.error('[高岛的眼睛] 读取规则文件失败，使用空规则表：', (e as Error).message);
  }
}

function persist(): void {
  try {
    fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
    fs.writeFileSync(DATA_FILE, JSON.stringify(rules, null, 2));
  } catch (e) {
    console.error('[高岛的眼睛] 保存规则失败：', (e as Error).message);
  }
}

/** 轻量校验：结构不合法时抛出带中文说明的 Error */
export function validateRule(input: unknown): asserts input is Rule {
  const r = input as Rule;
  if (!r || typeof r !== 'object') throw new Error('规则必须是对象');
  if (!r.match || typeof r.match.pattern !== 'string' || !r.match.pattern) {
    throw new Error('缺少匹配模式 match.pattern');
  }
  if (!['substring', 'regex', 'glob'].includes(r.match.type)) {
    throw new Error('match.type 必须是 substring / regex / glob');
  }
  if (!['request', 'response'].includes(r.match.phase)) {
    throw new Error('match.phase 必须是 request / response');
  }
  const a = r.action;
  if (!a || typeof a !== 'object') throw new Error('缺少动作 action');
  switch (a.mode) {
    case 'guide':
      if (typeof (a as GuideAction).redirectTo !== 'string') throw new Error('guide 动作需要 redirectTo');
      break;
    case 'replace': {
      const ra = a as ReplaceAction;
      if (typeof ra.status !== 'number') throw new Error('replace 动作需要 status');
      break;
    }
    case 'append': {
      const aa = a as AppendAction;
      if (!['body', 'json', 'header'].includes(aa.where)) throw new Error('append.where 必须是 body / json / header');
      if (aa.where === 'header' && !aa.key) throw new Error('append header 需要 key');
      break;
    }
    case 'modify': {
      const ma = a as ModifyAction;
      if (!Array.isArray(ma.patches)) throw new Error('modify 动作需要 patches 数组');
      for (const p of ma.patches as JsonPatch[]) {
        if (!['set', 'merge', 'delete'].includes(p.op)) throw new Error('补丁 op 必须是 set / merge / delete');
        if (typeof p.path !== 'string') throw new Error('补丁需要 path');
      }
      break;
    }
    default:
      throw new Error(`未知动作模式：${(a as { mode?: string }).mode}`);
  }
}

export function getRules(): Rule[] {
  ensureLoaded();
  return rules;
}

export function getRule(id: string): Rule | undefined {
  ensureLoaded();
  return rules.find((r) => r.id === id);
}

export function addRule(input: Omit<Rule, 'id'>): Rule {
  ensureLoaded();
  validateRule(input);
  const rule: Rule = { ...input, id: randomUUID() };
  rules.push(rule);
  persist();
  return rule;
}

export function updateRule(id: string, patch: Partial<Rule>): Rule {
  ensureLoaded();
  const idx = rules.findIndex((r) => r.id === id);
  if (idx < 0) throw new Error('规则不存在');
  const merged = { ...rules[idx], ...patch, id };
  validateRule(merged);
  rules[idx] = merged;
  persist();
  return merged;
}

export function deleteRule(id: string): boolean {
  ensureLoaded();
  const idx = rules.findIndex((r) => r.id === id);
  if (idx < 0) return false;
  rules.splice(idx, 1);
  persist();
  return true;
}

export function setRuleEnabled(id: string, enabled: boolean): Rule {
  ensureLoaded();
  const idx = rules.findIndex((r) => r.id === id);
  if (idx < 0) throw new Error('规则不存在');
  rules[idx] = { ...rules[idx], enabled };
  persist();
  return rules[idx];
}

export function getDataFile(): string {
  return DATA_FILE;
}
