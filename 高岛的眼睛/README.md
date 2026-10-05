# 高岛的眼睛

极简假反馈拦截工具。传入一个应用 / 接口 / 插件（把它的流量指向本工具），
在其产生反馈时按「方向」拦截，并注入自定义假反馈。支持四种注入模式。

## 特性

- **方向拦截**：`request`（去程）/ `response`（反馈方向）分别命中规则
- **四种模式**：
  | 模式 | 说明 |
  |---|---|
  | `guide` 引导 | 请求重定向到自定义目标；反馈方向则返回 302 引导 |
  | `replace` 截止更改 | 完全切断原始反馈，返回自定义假反馈（含状态码/头/体） |
  | `append` 追加 | 在原始反馈上附加内容（正文末尾 / JSON 合并字段 / 响应头） |
  | `modify` 改返回值 | 对 JSON 返回体做字段级 `set` / `merge` / `delete` |
- **HTTPS MITM**：自动生成本地 CA，按域名签发证书；无匹配规则的域名自动透传
- **一键代理**：在控制台选择目标应用（系统代理 / 命令行工具），一键开关其代理指向本工具
- **极简 Web 控制台**：规则管理 + 实时流量日志，主题统一（亮/暗）
- **零配置持久化**：规则存于 `data/rules.json`

## 快速开始

```bash
npm install
npm run build
npm start              # 代理 :8888，控制台 :8787
# 或开发模式
npm run dev
```

1. 打开控制台 http://127.0.0.1:8787
2. 把要拦截的应用 / 接口 / 插件流量指向代理 `127.0.0.1:8888`
   - 一键代理：控制台顶部「一键代理」选择目标应用，开启即可自动指向
   - 手动：浏览器用系统代理或插件（SwitchyOmega 等）；接口/插件设其 HTTP(S) 代理；
     命令行 `curl -x http://127.0.0.1:8888 ...`
3. 在控制台「+ 新增」创建规则
4. 拦截 HTTPS 时，下载并信任 CA 证书（控制台右上角「下载 CA 证书」）

## 规则结构

```jsonc
{
  "name": "伪造用户信息",
  "enabled": true,
  "match": {
    "pattern": "api.example.com/user",   // substring | regex | glob
    "type": "substring",
    "methods": [],                        // 留空不限，如 ["GET","POST"]
    "phase": "response"                   // response=反馈方向，request=去程方向
  },
  "action": { "mode": "replace", "status": 200, "contentType": "application/json",
              "headers": {}, "body": "{\"fake\":true}" }
}
```

### 各模式 action 示例

```jsonc
// guide 引导
{ "mode": "guide", "redirectTo": "https://another.example.com/v2" }

// replace 截止更改
{ "mode": "replace", "status": 200, "contentType": "application/json",
  "headers": { "X-Fake": "1" }, "body": "{\"ok\":false,\"reason\":\"mock\"}" }

// append 追加（body / json / header）
{ "mode": "append", "where": "json", "value": "{\"extra\":123}" }
{ "mode": "append", "where": "body", "value": "\n<!-- injected -->" }
{ "mode": "append", "where": "header", "key": "X-Extra", "value": "1" }

// modify 改返回值（点号路径，value 为 JSON 字符串）
{ "mode": "modify", "patches": [
    { "op": "set",    "path": "user.name", "value": "\"Bob\"" },
    { "op": "merge",  "path": "meta",      "value": "{\"mock\":true}" },
    { "op": "delete", "path": "secret" }
] }
```

## 命令行

```
npm start -- [选项]
  -p, --proxy-port <port>   代理端口（默认 8888）
  -a, --api-port <port>     控制台端口（默认 8787）
  -k, --insecure            忽略上游 HTTPS 证书校验
  -h, --help                帮助

环境变量：
  MOCKFEED_DATA   规则持久化文件路径（默认 ./data/rules.json）
```

## 目录结构（按模块优先级 P0→P2）

```
src/
├── types.ts            P0 规则模型 / 动作 / 运行类型契约
├── rules/
│   ├── matcher.ts      P0 匹配引擎（URL/方法/方向 + 优先级排序）
│   └── store.ts        P1 规则存储（CRUD + JSON 持久化 + 校验）
├── proxy/
│   ├── apply.ts        P0 动作执行器（guide/replace/append/modify）
│   ├── ca.ts           P0 CA 证书 + 按域名签发
│   ├── server.ts       P0 代理核心（HTTP 转发 + HTTPS MITM 管道）
│   └── system-proxy.ts P1 一键代理（系统代理 / 环境变量代理）
├── api/server.ts       P1 控制 REST API + 静态 UI
├── log.ts              P2 流量日志（环形缓冲）
├── config.ts           P2 CLI 参数
└── index.ts            P2 入口组装
ui/                     极简 Web 控制台（与主题同风格）
scripts/                冒烟测试 + 端到端测试
```

## 测试

```bash
npm run typecheck         # 类型检查
npx tsx scripts/smoke.ts  # 单元冒烟（匹配引擎 + 四模式）
node scripts/e2e.mjs      # 端到端（需先 npm run build）
```

## 参考

调研了以下同类实现，借鉴其拦截管道与规则模型设计：
- [soundcloud/intervene](https://github.com/soundcloud/intervene) — 配置文件式 mock
- [borgius/proxy-rules](https://github.com/borgius/proxy-rules) — 响应体重写管道、按规则决定是否 MITM
- [dougwithseismic/node-mitm-proxy](https://github.com/dougwithseismic/node-mitm-proxy) — 规则匹配 + 动作 + CA + Web UI
