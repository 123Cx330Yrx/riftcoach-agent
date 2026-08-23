# 8E Live Workbench Integration Walkthrough

> 状态：本地 implementation/evidence 已完成，exact-SHA 公共 CI 待闭环。整个 8E 仍为
> `in_progress / coverage planned`；本文只覆盖真实 API/SSE 接线批。

## 1. 问题与原理

### 1.1 这批到底解决什么

Batch D 的 `Rift Command Center` 已经有真实 React 页面、状态视觉和交互，但默认数据仍来自 fixture。
把它改成 `fetch()` 并不等于接线完成，因为一张页面同时依赖玩家档案、最新任务、run、Product State、
Summary、Markdown report、Evidence、Training 和 SSE。用户切换档案时，旧请求或旧事件还可能晚到。

本批解决两个核心问题：

1. **服务器身份恢复**：浏览器只拿 `player_profile_id`，由 owner-scoped locator 找到该档案最新的
   conversation-bound recent review task/run；不信 URL 或 localStorage 猜 run。
2. **异步结果归属**：每个 HTTP response 和 SSE event 必须匹配当前 generation、profile、task、run；
   不匹配就丢弃或 fail closed，不能把 A 玩家的内容显示在 B 玩家标题下。

### 1.2 对 Agent 产品有什么意义

Agent 产品不是只显示模型正文。它还要把执行状态、质量门、证据、个性化计划和失败边界组合给用户。
因此要分清三条状态线：

- Task/SSE：任务运行到哪里；
- Product State：内容能否 published、degraded、rejected 或仍 not-ready；
- Client resource：浏览器网络、decoder、重连或身份完整性是否正常。

SSE 断线不是“质量拒绝”，decoder 失败也不是“Agent 判断失败”。把三条线混在一起，会生成一个看似
完整、实际语义错误的产品。

## 2. 做了什么，没有做什么

### 2.1 已实现

- owner-scoped `GET /player-profiles/{id}/reviews/recent/latest`；
- `GET /runs/{run_id}/recent-summary`；
- Evidence public projection 的严格嵌套 Pydantic/OpenAPI schema；
- composition 与 Linux package 接线；
- profiles/latest/task/events/product/run/summary/report/evidence/training 的手写 exact decoder；
- same-origin、有 body/content-type/error 上限的 API client；
- generation + AbortController + profile/task/run identity guard；
- 每个 selection 最多一个原生 EventSource，支持 cursor replay、terminal reload、switch/unmount close；
- fixture/live 共用 view model 与确定性 adapter；
- 默认 live、只有显式 `?scenario=` 才进入 fixture；
- verified report 的 React 原生转义纯文本显示、真实 Training 字段与 observed read-only 边界；
- deterministic HTTP/SSE browser server 与 no-remote-I/O E2E。

### 2.2 明确未实现

- 正式 Auth/RSO、浏览器 token、CORS 扩张；
- 反向代理、HTTPS、backup/restore、部署或公网发布；
- 电影感 `Rift Awakening` 入口、完整 Rift Timeline、完整 Training 页面；
- OP.GG useful-breadth gate；
- Riot + Data Dragon + official patch + OP.GG → Training → live UI 的完整真实 golden slice；
- 本批真实 Riot、OP.GG、Provider、LLM 调用或 8B holdout 重跑。

## 3. 设计与实现

### 3.1 后端：只补 identity seam，不建第二真源

`LatestProfileReviewService` 使用独立 repository port。PostgreSQL repository 先证明 profile 对 owner 可见、
relationship active 且存在成功 link，再只查询 schema 2.0、`recent_review`、相同 relationship 的最新 task。
排序固定为 `created_at DESC, task_id DESC`；最新失败任务不会被旧成功任务越过。

API 层才生成 relative links。locator 不返回 owner、PUUID、payload、execution target、worker 或 Artifact path。
Recent Summary 继续复用既有 `RunQueryService` 和 owner/run binding；active、failed、rejected、cross-owner 与
integrity failure 保持不同的 body-free HTTP code。

Evidence storage/fusion wire 没有迁移。`EvidenceSnapshotResponse.projection` 只是由自由 object 收紧为
`EvidencePublicProjectionResponse`，严格覆盖 sources、matches、joins、conflicts、gaps 和 claims；未知字段、
坏 enum、digest 或 timestamp 在 HTTP model boundary 被拒绝。

### 3.2 前端：wire、控制面、view、组件四层分开

```text
unknown HTTP/SSE bytes
  → exact wire decoder
  → generation/profile/task/run identity assertion
  → deterministic adapter
  → immutable WorkbenchView
  → React components
```

组件不直接 fetch，也不认识 snake_case。fixture 和 live 最终映射到同一个 view model，但 fixture-only 的
`2/5`、完成百分比、next action、战术 headline、结构化 verdict/strength/priority 没有进入 live view。

`ApiClient` 只接受 safe relative endpoint，并统一添加 `/api`。浏览器默认 fetch 必须绑定全局 receiver；
直接把原生 fetch 保存为对象方法会在 Chromium 触发 `Illegal invocation`，因此使用
`globalThis.fetch.bind(globalThis)`。生产网络入口仍只允许 client 与 EventSource 两个批准 seam。

### 3.3 SSE 生命周期

```text
idle → connecting → live → terminal → close → authoritative reload
                    └─ transient error → reconnecting
profile switch / unmount ───────────────────────→ close
```

事件必须是 `task.lifecycle`、不超过 64 KiB，并通过 exact decoder。duplicate cursor 忽略，跳号允许；
task/run/Last-Event-ID mismatch 关闭流并 fail closed。terminal event 不直接把页面“猜成 published”，而是关闭
stream，再重读 task 和 Product State，最后按 authoritative state 加载内容。

### 3.4 Report 与 Training 的真实性取舍

计划原本候选为 `react-markdown@10.1.0`。实现验证中 JS gzip 达到 `156.52 kB`，超过 150 kB 硬门，因此按
ADR-0062 移除该依赖，回到 React 原生转义纯文本。当前 `SafeMarkdown` 不是完整 Markdown renderer：它保留
换行和原文，HTML/link/image 都只作为不可执行文本，不产生 `<a>`、`<img>`、`<script>` 或 raw HTML。

self Training 只显示后端 plan title/objective 和一个真实 metric 的 baseline/target/current/trend/sample
count；无 progress 是合法 `insufficient data`。observed 永不请求个人 Training endpoint，只显示公开学习
对象的 read-only 边界。

## 4. 代码地图

| 位置 | 职责 |
|---|---|
| `app/product/latest_review.py` | locator models、port、service 与安全错误 |
| `app/persistence/latest_review_repository.py` | owner/relationship/schema-2.0 latest PostgreSQL query |
| `app/api/live_workbench_models.py` | locator HTTP DTO 与 relative links |
| `app/api/main.py` | locator、Recent Summary 薄 routes 与错误投影 |
| `app/api/evidence_models.py` | typed Evidence public HTTP models |
| `app/api/composition.py` | PostgreSQL locator 与 Run Summary composition proxy |
| `web/src/api/decoders.ts` | unknown → exact wire decoders |
| `web/src/api/client.ts` | bounded same-origin HTTP client |
| `web/src/api/taskEventStream.ts` | EventSource/cursor/binding/terminal lifecycle |
| `web/src/workbench/liveController.ts` | generation、abort、selection、reload 与 fail-closed reducer |
| `web/src/workbench/adapters.ts` | wire/fixture → shared view 的确定性映射 |
| `web/src/app/App.tsx` | 显式 fixture 与默认 live 的 React composition |
| `web/tests/support/liveApiServer.mjs` | deterministic allowlisted HTTP/SSE browser fixture server |

## 5. 数据与控制流

### 5.1 初次加载

```text
GET profiles
  → select URL-valid profile or first profile
  → GET latest locator
      ├─ null: selected-profile empty + self Training / observed read-only
      └─ task/run:
          → task + product-state + event page + self-only Training
          ├─ active: render lifecycle + open one EventSource
          └─ terminal: load run + summary + report + evidence by Product State
```

### 5.2 切换 profile

1. generation 加一；
2. abort 旧 fetch、close 旧 EventSource、清空旧内容；
3. 用新 profile 重新定位 latest task/run；
4. response/event 只有四重 identity 全匹配才可进入当前 view；
5. observed 路径不发 Training plan/progress 请求。

### 5.3 active 到 terminal

1. 初始 task=`running`、Product State=`not_ready`；
2. event page 给出已有 durable lifecycle；
3. EventSource 从 `next_cursor` 后接续；
4. terminal event 关闭 stream；
5. 重读 task/product-state；
6. published/degraded 才读 verified report/summary，Evidence 按状态要求读取；
7. client reconnect 状态清零，但不会改写服务器 publication。

## 6. 验证证据

本地实现关闭门：

- 后端聚焦：`58 passed, 1 warning`；package/composition：`59 passed, 1 warning`；
- 完整 pytest：`1939 passed, 1 skipped, 1 warning, 127 subtests passed`；唯一 skip 为 Windows symlink；
- PostgreSQL 17 CI-equivalent collection：`200 passed, 1 warning`，已把 locator repository 纳入公共 job；
- Alembic 0011 `head → base → head` 可逆，`alembic check` 无新操作；
- 前端 typecheck 通过，unit `12 files / 66 passed`；
- Playwright `17 passed`：active SSE→published、degraded/rejected/empty、profile switch、server-list URL selection、Training 边界、
  1440/1024/390/320、keyboard/focus、reduced-motion、axe critical/serious 0、remote request 0；
- production build：JS gzip `122.01 kB`、CSS gzip `11.35 kB`；official npm audit `0 vulnerabilities`；
- RAG development/independent holdout 全阈值，Harness `published / 0 revisions`；
- compileall、pip check、6 YAML、SDK/Secret/tracked-data、governance、`git diff --check` 通过；
- 隔离 Linux Compose package schema `1.6`，Memory Context 3 records、terminal assistant 0、外部调用 0，
  非 root/image exclusion 通过，临时 container/volume/network 已清理。

公共完成门仍是同一 implementation/evidence SHA 的 GitHub Actions `pytest`、`postgres-migrations`、
`packaging-smoke` 三 job 全部 success；在它们完成前，本批只称“本地完成”。

## 7. 运行手册

```powershell
# 后端聚焦
.\.venv\Scripts\python.exe -m pytest `
  tests\test_latest_profile_review_service.py `
  tests\test_latest_profile_review_repository_postgres.py `
  tests\test_live_workbench_api.py `
  tests\test_evidence_product_api.py `
  tests\test_evidence_product_api_postgres.py `
  tests\test_api_composition.py -q

# 前端合同与浏览器
npm.cmd --prefix web ci --ignore-scripts
npm.cmd --prefix web run typecheck
npm.cmd --prefix web run test:unit
npm.cmd --prefix web run build
npm.cmd --prefix web run test:e2e

# 完整回归；本机真库运行时 Alembic 与 pytest 使用同一 URL
$env:DATABASE_URL = $env:RIFTCOACH_TEST_DATABASE_URL
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check

# 治理与 diff
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

本地开发默认访问 `/api` 并由 Vite 只转发到 allowlisted localhost target。fixture 预览必须显式使用
`/?scenario=published` 等 query；无 `scenario` 的 `/` 是 live 模式。

## 8. 失败、安全与边界

- latest locator、所有内容和 Training 都保持 owner/relationship binding；cross-owner 返回安全 404；
- 浏览器不保存 owner、PUUID、Key、RSO token、Prompt/Context 或 raw upstream body；
- HTTP body、Markdown、SSE event 均有限长；错误只显示 allowlisted safe code；
- decoder 遇到 extra key、unknown enum、坏时间/digest/UUID/non-finite number 不做 best effort；
- profile switch 先清空旧内容，宁可短暂 loading 也不 stale-while-revalidate 串号；
- Product State、SSE transport、client error 分离；断线不冒充 rejected；
- deterministic server 证明真实 HTTP/SSE 组合，但不是 Riot/OP.GG live 调用或公网容量证据；
- 纯文本 report fallback 安全且轻量，但不能宣传成完整 Markdown 富文本能力；
- 本批没有正式 Auth、CSP/HTTPS/限流、backup/restore、生产 SSE 压测或部署。

### 本批修复的真实 Bad Cases

1. 原生 fetch 作为对象方法调用触发 Chromium `Illegal invocation`；增加 receiver 回归并绑定 global fetch。
2. exact OpenAPI path 测试漏登记两条新 route；更新合同，不删除 exact-path 守门。
3. 重复本地 E2E 使用固定 ledger id 污染 terminal/request count；改用每次唯一 test identity。
4. Windows 10-worker 压测使页面与截图整体资源饥饿；本地封顶 4 worker，CI 继续 1 worker。
5. package smoke 在 task 已 failed 后写 Evidence，被 production repository 正确拒绝；改为 claim 后、故意
   no-I/O failure 前写入，保留 failed terminal 与 Evidence write invariant。
6. 提交前 diff 审查发现 locator route 插入使 `/player-profiles` 的 generic exception 映射错位；增加
   RuntimeError 红灯后恢复 body-free 503，并删除 locator 尾部的重复异常分支。
7. `boundedText()` 原先在 `response.text()` 全量缓冲后才检查实际字节；无 Content-Length 的流不是真正
   有界。新红灯证明旧路径丢失 `api_body_too_large`，现逐 chunk 累计并在越界时 cancel reader。
8. invalid profile selection 原先直接显示 error、没有关闭 active stream；现在任何 selection 都先开启新
   generation、abort/close，再按 server profile list 决定是否继续。
9. Controller 已有 `initialProfileId`，但默认 App 漏接设计中的 URL candidate；现在只把
   `player_profile_id` 与 owner-scoped profile list exact match，URL 仍不能决定 task/run 或 observed Training。

## 9. 面试表述

可以这样讲：

> 我没有把静态 React 页面直接改成散落的 fetch，而是先做 owner-scoped profile→latest task/run locator，
> 再把 HTTP/SSE unknown input 经过 exact decoder 和 generation/profile/task/run identity guard，映射成统一
> Workbench view。切换玩家会 abort 旧请求并关闭旧 EventSource；SSE terminal 只触发 authoritative reload，
> 不直接猜 publication。报告、Evidence 和 Training 只展示后端可证明的字段。

不能说：已经有正式登录、生产部署、完整 Timeline/Training、全量 OP.GG 能力、生产 SLA，或已经完成
Riot/Data Dragon/patch/OP.GG→Training→UI 的真实 golden slice。
