/**
 * 高岛的眼睛 — 规则匹配引擎（P0）
 *
 * 负责「命中判定」：给定一条流量（URL / 方法 / 方向），
 * 找出所有应该生效的规则，并按优先级排序。
 */
import { minimatch } from 'minimatch';
import type { MatchType, Phase, Rule } from '../types.js';

/** 匹配 URL */
export function matchesUrl(url: string, pattern: string, type: MatchType): boolean {
  if (!pattern) return false;
  switch (type) {
    case 'regex':
      try {
        return new RegExp(pattern).test(url);
      } catch {
        return false;
      }
    case 'glob':
      return minimatch(url, pattern);
    case 'substring':
    default:
      return url.includes(pattern);
  }
}

/** 匹配方法（空数组 = 不限） */
export function matchesMethod(method: string, methods: string[]): boolean {
  if (!methods || methods.length === 0) return true;
  return methods.some((m) => m.toUpperCase() === method.toUpperCase());
}

/** 匹配类型优先级：精确性越高越靠前（regex > glob > substring 兜底） */
const TYPE_PRIORITY: Record<MatchType, number> = {
  regex: 3,
  glob: 2,
  substring: 1,
};

/**
 * 命中判定：返回该方向下所有命中的启用规则，按优先级降序排列。
 * 优先级：匹配方式精确性 → 方法限制数量 → 模式长度（更具体优先）。
 */
export function matchRules(
  rules: Rule[],
  input: { url: string; method: string; phase: Phase },
): Rule[] {
  return rules
    .filter((r) => {
      if (!r.enabled) return false;
      if (r.match.phase !== input.phase) return false;
      if (!matchesMethod(input.method, r.match.methods)) return false;
      return matchesUrl(input.url, r.match.pattern, r.match.type);
    })
    .sort((a, b) => {
      const pa = TYPE_PRIORITY[a.match.type];
      const pb = TYPE_PRIORITY[b.match.type];
      if (pa !== pb) return pb - pa;
      const ma = a.match.methods.length;
      const mb = b.match.methods.length;
      if (ma !== mb) return mb - ma;
      return b.match.pattern.length - a.match.pattern.length;
    });
}
