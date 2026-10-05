# 高岛的家居监控

与小黄鸟（Reqable / HttpCanary 的继任者）协同工作的实时抓包监控看板：
接收抓包数据 → 实时分析 → 自动反馈 → 极简看板展示重要数据。
支持网页和 App 的流量，双模式抓包：

| 模式 | 说明 |
|---|---|
| **小黄鸟联动模式**（推荐） | Reqable 通过官方「报告服务器」把抓到的每个会话 POST 到本工具，实时分析展示 |
| **独立抓包模式** | 内置 mitmproxy 代理（127.0.0.1:8888），不依赖 Reqable 也能抓网页 / App |

> 注：老版「小黄鸟」HttpCanary 已停止更新，其继任者 **Reqable v2.20+**（全平台）才支持上报服务器功能。

---

## 快速开始

```bash
# 1. 安装依赖（已装可跳过）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 启动
python main.py                     # 桌面窗口（默认，图标 app.ico）
python main.py --mode browser      # 用系统浏览器打开看板
python main.py --mode server       # 仅后台服务
```

看板地址 `http://127.0.0.1:8090/`，上报接口 `http://127.0.0.1:8090/report`。

## 模式一：小黄鸟联动（Reqable 上报服务器）

**桌面端（Windows/Mac/Linux）：**
1. 打开 Reqable → 菜单「工具」→「报告服务器」
2. 添加配置：
   - 名称：任意（如 `高岛家居监控`）
   - URL 规则：`*`（抓全部；也可按需，如 `https://*.takashima.com/*`）
   - 接收地址：`http://127.0.0.1:8090/report`
   - 压缩：建议 `gzip`（brotli / zstd 同样支持）
3. 开启 Reqable 抓包，每个会话完成后会自动上报并实时出现在看板

**手机端（Android/iOS）：**
1. Reqable App → `⋮` →「更多」→「上报服务器」，按同样参数配置
2. 接收地址改为电脑局域网 IP，如 `http://192.168.1.10:8090/report`（手机与电脑同一 WiFi）
3. 如手机连不上，可用 `python main.py --mode server` 启动并在防火墙放行 8090 端口（默认 127.0.0.1 仅本机可访问）

## 模式二：独立抓包（内置代理）

1. 看板工具栏点击「独立抓包」按钮（或 `POST /api/capture/start`）
2. 把要抓包的设备/浏览器代理设为 `127.0.0.1:8888`：
   - 网页：系统代理或浏览器插件（SwitchyOmega 等）
   - App：手机 WiFi 代理指向电脑的 `电脑IP:8888`
3. HTTPS 解密需安装证书（首次启动自动生成）：
   `C:\Users\<用户>\.mitmproxy\mitmproxy-ca-cert.cer`
   手机安装后需在系统里信任该 CA（Android 7+ 需装为用户证书并信任）
4. 抓完点「停止抓包」即释放 8888 端口

## 实时反馈（分析引擎自动检出）

| 等级 | 规则 |
|---|---|
| 🔴 告警 | 5xx 服务器错误、凭证出现在 URL、同主机错误风暴（60s 内 ≥5 次 5xx） |
| 🟡 警告 | 4xx / 401 / 403、响应 >3s、响应体 >1MB、外网明文 HTTP、响应含敏感字段（token/password/secret 等）、Cookie 缺 HttpOnly / Secure、无响应状态 |

反馈实时显示在「反馈」面板与每条记录的详情中。

## API 一览

| 接口 | 说明 |
|---|---|
| `POST /report` | 上报接收（Reqable / 内置代理共用），支持 gzip/br/zstd |
| `GET /api/health` | 健康检查 |
| `GET /api/entries?method=&status=&host=&search=&level=&limit=&offset=` | 查询历史（筛选 + 分页） |
| `GET /api/entries/{id}` | 单条详情 |
| `GET /api/stats` | 概览统计（总数/错误/告警/流量/TOP 域名） |
| `GET /api/feedback` | 最近反馈 |
| `POST /api/clear` | 清空数据 |
| `POST /api/capture/start` / `stop` / `GET /api/capture/status` | 独立抓包控制 |
| `WS /ws` | 实时推送（init 回放 + entry 事件） |

## 目录结构

```
高岛的家居监控/
├─ main.py                 入口（window / browser / server 三模式）
├─ requirements.txt
├─ app/
│  ├─ config.py            全局配置
│  ├─ models.py            数据模型
│  ├─ har_parser.py        HAR 解析规范化
│  ├─ receiver.py          上报接收（联动核心）
│  ├─ analyzer.py          分析反馈引擎
│  ├─ database.py          SQLite 持久化
│  ├─ broadcaster.py       WebSocket 实时广播
│  ├─ server.py            FastAPI 组装
│  └─ capture/             独立抓包（mitmproxy 插件 + 进程管理）
├─ web/                    极简前端（无外部依赖，离线可用）
├─ res/app.ico             应用图标
└─ data/capture.db         抓包数据库（自动创建）
```

## 技术栈

Python 3.12 · FastAPI · uvicorn · SQLite · WebSocket · mitmproxy 12 · pywebview · 纯 HTML/CSS/JS 前端
