/**
 * 高岛的眼睛 — 核心类型定义（P0）
 *
 * 所有模块共享的数据契约。规则描述「在什么方向、匹配什么流量、
 * 用哪种模式注入什么样的假反馈」。
 */

/** URL 匹配方式 */
export type MatchType = 'substring' | 'regex' | 'glob';

/** 反馈方向：请求方向（去程）或 响应方向（回程/反馈） */
export type Phase = 'request' | 'response';

/** 动作模式 */
export type ActionMode = 'guide' | 'replace' | 'append' | 'modify';

export interface MatchSpec {
  /** 匹配目标 URL（含 host + path + query） */
  pattern: string;
  /** 匹配方式，默认 substring */
  type: MatchType;
  /** 限定 HTTP 方法，空数组表示不限 */
  methods: string[];
  /** 方向：request = 去程拦截，response = 反馈拦截 */
  phase: Phase;
}

/** JSON 字段级补丁：修改返回值 */
export interface JsonPatch {
  op: 'set' | 'merge' | 'delete';
  /** 点号路径，如 "user.name" 或 "items.0.id" */
  path: string;
  /** 原始 JSON 字符串，运行时尝试解析，失败则按字符串处理 */
  value?: string;
}

/**
 * 引导：把请求重定向到另一个目标（反馈来源被引导到自定义方向）
 */
export interface GuideAction {
  mode: 'guide';
  redirectTo: string;
}

/**
 * 截止更改：完全切断原始反馈，返回自定义假反馈
 */
export interface ReplaceAction {
  mode: 'replace';
  status: number;
  contentType?: string;
  headers: Record<string, string>;
  body: string;
}

/**
 * 追加：在原始反馈之上附加额外内容（不破坏原反馈）
 * - body   : 在响应体末尾拼接文本
 * - json   : 把 value 作为 JSON 对象合并进原 JSON（新增/覆盖字段）
 * - header : 新增/覆盖一个响应头
 */
export interface AppendAction {
  mode: 'append';
  where: 'body' | 'json' | 'header';
  /** header 模式下为头名，json 模式下忽略（整体合并） */
  key?: string;
  value: string;
}

/**
 * 修改返回值：对 JSON 返回体做字段级增删改
 */
export interface ModifyAction {
  mode: 'modify';
  patches: JsonPatch[];
}

export type RuleAction = GuideAction | ReplaceAction | AppendAction | ModifyAction;

export interface Rule {
  id: string;
  name: string;
  enabled: boolean;
  match: MatchSpec;
  action: RuleAction;
  note?: string;
}

/** 运行时归一化后的请求 */
export interface ProxyRequest {
  method: string;
  /** 完整 URL，含协议与 host */
  url: string;
  headers: Record<string, string>;
  body: string;
}

/** 运行时归一化后的响应 */
export interface ProxyResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
  /** 响应体是否为文本类（可安全做字符串/JSON 操作） */
  text: boolean;
  contentType: string;
}

/** 动作执行结果：proxy 核心据此决定下一步 */
export type RequestActionResult =
  | { kind: 'passthrough' }
  | { kind: 'redirect'; url: string }
  | { kind: 'respond'; response: ProxyResponse };

export type ResponseActionResult =
  | { kind: 'passthrough'; response: ProxyResponse }
  | { kind: 'replace'; response: ProxyResponse };

/** 流量日志条目 */
export interface LogEntry {
  id: string;
  ts: number;
  method: string;
  url: string;
  phase: Phase;
  status: number;
  matchedRules: string[];
  /** 是否被改写了反馈 */
  modified: boolean;
  durationMs: number;
}
