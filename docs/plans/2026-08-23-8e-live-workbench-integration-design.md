# 8E Live Workbench API/SSE Integration 设计

> 本文是 Batch D 静态工作台之后的真实数据接线设计门。它不会把“设计完成”写成 API/SSE 已实现，
> 也不会提前进入 Auth/部署或其余五模块。

## 1. 初学者教学

### 1.1 具体问题

现在的 React 页面像一辆已经完成内饰、仪表盘和安全提示的展示车：按钮、状态、移动端和动效都是真的，
但仪表读的是受控样例。接真实后端不能简单理解为“把 fixture 换成 fetch”。页面一次要组合 profile、task、
run、Summary、report、Evidence、Training 和 SSE；它们可能在不同时间成功、失败或过期。

最危险的错误不是页面打不开，而是：用户切换到观察对象后，旧账号的 Summary 晚到并显示在新标题下；
或者 SSE 断线被误画成“报告被质量门拒绝”。本设计首先解决服务器身份和状态归属，然后才加载内容。

### 1.2 Agent / 软件原则

1. **服务器身份是根**：profile→latest task/run 必须来自 owner-scoped 查询，不信 URL/localStorage 猜测。
2. **wire contract 不等于 view model**：HTTP JSON 先严格解码，再映射成 UI 需要的形状。
3. **异步结果必须带归属**：每个 response/event 同时绑定 generation、profile、task、run，晚到结果丢弃。
4. **控制面和内容面分开**：SSE/task 说明“运行到哪”，Product State 说明“内容能否展示”。
5. **不从文本发明结构**：Markdown 报告可以安全展示，但不能猜成后端不存在的 verdict/next-session 字段。

### 1.3 本检查点做与不做

本设计冻结 latest locator、Recent Summary endpoint、typed Evidence wire model、前端 decoder/adapter、
EventSource 生命周期、Training 真实字段和测试门。后续实施才写代码。

不做 Riot/OP.GG 新调用、自动 Evidence refresh、玩家创建入口、正式 Auth/RSO、完整 Timeline/Training、
部署或作品集 README。

### 1.4 视觉连续性为什么也属于接线设计

旧日志最终冻结了三种视觉职责：`Rift Awakening` 负责电影感入口，`Esports Intelligence` 负责长期电竞
分析工作台，`Void Holographic Lab` 只作受限 Hero 实验。推荐组合是
`Cinematic Portal → Broadcast Workbench`，而不是从三者硬选一个。

Batch D 的 `Rift Command Center` 是 `Esports Intelligence` 的第一版静态纵切；本批把它接到真实数据时，
必须保持 A/B 共享的深海军蓝/黑曜石、Hextech 青蓝、克制金色、Rift 路径与 Coach Core 语言，同时把动效
预算留在正确位置：入口大胆、工作台克制、关键数据交互精准。接 API 不应删除氛围层或退回普通后台；
同样也不能为维持截图效果保留后端不存在的 headline、session 进度或完整 Timeline。

这三个方向与 Batch D 的“工作台优先 / 入口优先 / Timeline 优先”施工三案不同。施工顺序只回答先验证
哪个消费者，不会改写最终视觉组合。C 的 3D/WebGL 仍要单独 Bad Case、性能和可访问性门，本批不安装。

## 2. 现有代码事实与缺口

| 已有事实 | 可直接复用 | 当前缺口 |
|---|---|---|
| `GET /player-profiles` | PUUID-free profile/region/role/verification | 没有 profile→latest task/run |
| `GET /tasks/{id}`、events、SSE | owner-scoped task 与 cursor lifecycle | 前端尚无 decoder/stream lifecycle |
| `GET /runs/{id}`、`/report` | verified run metadata 与 Markdown | Summary 没有 endpoint；fixture Coach 结构不是 wire truth |
| `/product-state` | published/degraded/rejected/not_ready | 必须与 client/SSE error 分层 |
| `/evidence` | immutable snapshot 与 public projection | HTTP `projection` 仍是自由 object |
| Training plan/progress | self-only typed plan/event/trend | fixture session completion/next action无法推导 |
| Batch D React | 四态、Drawer、responsive/a11y | `fixture_mode` 与 live view 尚未分离 |

## 3. 高层架构

```text
┌──────────────────────────── Browser ────────────────────────────┐
│ App mode                                                        │
│ ├─ explicit ?scenario=... → fixture adapter → WorkbenchView    │
│ └─ default live → LiveWorkbenchController                       │
│       ├─ ApiClient → exact wire decoders                        │
│       ├─ profile/task/run generation guard                      │
│       ├─ EventSource lifecycle                                  │
│       └─ wire adapters → WorkbenchView → existing components    │
└──────────────────────────────┬───────────────────────────────────┘
                               │ same-origin /api
┌──────────────────────────── FastAPI ─────────────────────────────┐
│ existing profiles/task/run/report/product/evidence/training     │
│ + latest profile review locator                                 │
│ + recent-summary route                                          │
│ + typed Evidence HTTP projection                                │
└──────────────────────────────┬───────────────────────────────────┘
                               │
       PostgreSQL task identity + immutable file/run artifacts
```

不创建 Workbench 聚合数据库表、第二缓存或新队列。浏览器组合的是多个已有事实源，但只在统一 identity
guard 通过后形成一个不可变 `WorkbenchView` snapshot。

## 4. 后端合同

### 4.1 Latest profile review

```json
{
  "schema_version": "1.0",
  "player_profile_id": "uuid",
  "latest_review": {
    "task_id": "uuid",
    "run_id": "review_...",
    "status": "running",
    "created_at": "...Z",
    "updated_at": "...Z",
    "publication_status": null,
    "report_available": false,
    "links": {
      "task": "/tasks/...",
      "events": "/tasks/.../events",
      "stream": "/tasks/.../events/stream",
      "run": "/runs/...",
      "summary": "/runs/.../recent-summary",
      "report": "/runs/.../report",
      "product_state": "/runs/.../product-state",
      "evidence": "/runs/.../evidence"
    }
  }
}
```

`latest_review` 可以为 `null`，这表示合法空状态，不是 404。查询必须同时约束 owner、active relationship、
visible schema-2 task、relationship identity 和 task kind；不接受客户端传 owner/conversation/subject。

### 4.2 Recent Summary

`GET /runs/{run_id}/recent-summary` wire shape 复用 `RecentSummaryView`，字段保持 snake_case 和现有严格
数学校验。HTTP 状态：

| 条件 | 状态/安全 code |
|---|---|
| unknown/cross-owner run | 404 `run_not_found` |
| queued/running/recovery | 409 `run_not_ready` |
| failed/cancelled | 409 `run_not_available` |
| rejected/no published report | 409 `report_not_available` |
| wrong skill/Artifact/Trace mismatch | 500 `run_integrity_failed` |
| valid published/degraded recent review | 200 typed Summary |

### 4.3 Typed Evidence projection

`EvidenceSnapshotResponse.projection` 改为 `EvidencePublicProjectionResponse`，嵌套包含：

- `sources`: Riot/Data Dragon/official patch/OP.GG 四个固定 source models；
- `matches`: bounded match identity/champion/position/patch/win/timeline availability；
- `joins`: key/status/confidence/sources_present；
- `conflicts`、`gaps`: safe code/source/key；
- `claims`、disposition/confidence/bundle digest。

JSON 字段与当前 `to_public_projection()` 一致，所以是 schema hardening，不是 wire migration。Storage full
projection、Meta facts 和 raw body 仍不返回。

## 5. 前端模型分层

```text
unknown JSON/text/event
  → Api*Wire decoder (snake_case, exact schema)
  → identity assertion (expected profile/task/run)
  → Workbench adapter (camelCase, display-safe copy)
  → immutable WorkbenchView
  → React components
```

建议文件职责：

| 文件 | 职责 |
|---|---|
| `web/src/api/wire.ts` | 只放 wire interfaces/enums，不假装运行时已校验 |
| `web/src/api/decoders.ts` | `unknown`→exact wire；拒绝 extra/unknown enum/non-finite/坏时间 |
| `web/src/api/client.ts` | same-origin fetch、content-type、body/error bounds、AbortSignal |
| `web/src/api/taskEventStream.ts` | EventSource factory、task event decoder、close/terminal/error |
| `web/src/workbench/model.ts` | fixture/live 共用、无 fixture-only 标志的 UI view |
| `web/src/workbench/adapters.ts` | wire/fixture→view；role/evidence/training 确定性映射 |
| `web/src/workbench/liveController.ts` | generation、请求顺序、并行、SSE 和 state reducer |

不在 component 里直接 `fetch`，不让 component 认识 snake_case 或 HTTP status。

## 6. 加载与控制流

### 6.1 初次打开

```text
GET profiles
  ├─ 503/invalid → full client error
  ├─ []          → empty profiles
  └─ profiles    → select URL-valid profile else first profile
                    → GET latest locator
```

### 6.2 选择 profile

1. generation +1；abort 旧 fetch，关闭旧 EventSource，清空旧内容；
2. locator 为空：显示该 profile 的“暂无复盘”，不显示其他 profile 内容；
3. locator 有 task/run：并行读取 task、product-state、event page；
4. active：显示 not-ready 和真实 events，打开一个 SSE；
5. terminal：按 Product State 条件加载内容；
6. self profile 读取 Training plan/progress；observed 永不请求个人 Training。

### 6.3 内容加载规则

| Product State | Summary/report | Evidence | UI |
|---|---|---|---|
| published | 必须成功；任一 integrity failure 为 client error | revision 存在则必须成功 | 完整工作台 |
| degraded | report/summary 可用则显示 | snapshot 可有可无；缺失显示 reason | 报告可看但限制持续可见 |
| rejected | 不请求 report/summary | revision 存在时可展示 rejected Evidence | 明确 withheld |
| not_ready | 不请求内容 | 不请求 | lifecycle only |

任一 content response 的 run/task identity 不匹配 expected binding，整次 generation fail closed；不能只丢一张
卡继续显示混合数据。

## 7. SSE 状态机

```text
idle → connecting → live ──terminal──→ closed
                    ├─ transient error → reconnecting → live
                    └─ profile switch/unmount → closed
```

- `task.lifecycle` 必须通过 exact decoder，event_cursor 严格递增；duplicate/replay cursor 忽略；跳号允许，
  因为 server cursor 是全局序号而不是 task-local连续值；
- event task_id/run_id 必须匹配 binding；不匹配立即关闭并报 client integrity error；
- terminal `succeeded|failed|cancelled` 关闭 stream并触发一次 authoritative reload；
- 浏览器网络错误只显示 reconnecting，不改变 Product State；
- server `stream.error` 映射为 safe live-update error，保留最近 authoritative snapshot并提供显式重试；
- 不显示假百分比、倒计时或 ETA。

## 8. 真实性 UI 修正

### Recent Form

硬编码 “The lane is stable...” 删除。标题使用静态 `Recent form at a glance`，数据只来自 Summary；主位置、
英雄、胜负和聚合指标继续展示，仍不伪造逐局历史。

### Coach Brief

published/degraded 读取 verified Markdown。`react-markdown@10.1.0` 当前 npm metadata 为 MIT，实施时锁定
exact package tree；HTML、image、link 均禁用。组件保留 Coach Core 标头和 publication 标签，正文不猜字段。

### Training

self 显示 active plan 的 title/objective 和最多一个 primary metric：baseline、target、latest value、unit、
trend、sample count。没有 progress 就显示 insufficient data。observed 只显示 read-only public study 边界。
现有 fixture 的 session count/progress bar/next action 必须重塑或明确 fixture-only，live 页面不得显示。

### Evidence

Source card 的数字/版本/freshness/provenance 来自 typed projection；label 是固定产品字典。Gap 只显示 code、
source 和可确定的 claim impact。未知未来 code 使用通用限制文字，不把未知 code 当客户端崩溃。

## 9. 错误矩阵

| 层 | 示例 | UI 行为 |
|---|---|---|
| client resource | network、bad JSON、content-type、decoder failure | client error/retry；不写 rejected |
| identity integrity | late response、profile/task/run mismatch | abort generation、清空内容、fail closed |
| task lifecycle | queued/running/recovery/failed/cancelled | lifecycle + Product State authoritative copy |
| publication | published/degraded/rejected | 决定 report 是否可读 |
| evidence | absent/expired/degraded/rejected/integrity failed | Evidence 限制或 client integrity error |
| SSE transport | reconnect/stream.error | reconnecting 或 safe retry，不改 publication |
| training | no plan/no progress/observed | 合法空状态，不升级成页面错误 |

错误 body 只读取 allowlisted `code`/`run_id`，不渲染 response text、stack、URL、owner 或 raw exception。

## 10. 安全、性能与部署边界

- 所有请求使用 relative `/api`；开发 Vite proxy，同源生产形态留 Batch E reverse proxy；
- 不设置 wildcard CORS，不在 JS/localStorage 保存 Actor、RSO token、Riot Key 或 Cookie；
- response body、Markdown 和 SSE 都有大小/类型上限；React 不使用 `dangerouslySetInnerHTML`；
- profile 切换先清空旧内容，宁可短暂 skeleton 也不展示错误账号；
- 每 selection 最多一个 stream；所有 fetch 可 abort；页面隐藏/卸载关闭资源；
- 当前 JS gzip 109.89 kB；加入安全 Markdown 后总 JS gzip 上限 150 kB；
- 当前只测本地/Fake/fixture/真实 PostgreSQL，不调用 Riot/OP.GG/Provider/LLM，不声称公网 p95/SLA。

## 11. 验证矩阵

- pure Python：locator models/service、latest ordering、cross-owner/hidden/no-task、Summary error mapping；
- real PostgreSQL：owner+relationship identity、latest active/failed/succeeded、tie break、legacy/hidden exclusion；
- API/OpenAPI：latest/summary/typed Evidence JSON 和 404/409/500/503 body-free；
- TypeScript unit：每个 wire decoder 的合法/extra/unknown enum/bad time/non-finite/identity mismatch；
- controller unit：abort、generation race、parallel content、role boundary、partial failure；
- SSE unit：replay/duplicate、terminal close、switch/unmount、stream.error、mismatch；
- browser no-I/O：真实 HTTP fixture server + Vite proxy，验证 loading→active→published、degraded/rejected、
  profile switch 不串号、Training self/observed、Markdown HTML/link/image 不执行；
- visual/a11y：现有 1440/1024/390/320、keyboard、focus return、reduced-motion、axe 继续全绿；
- full gates：Python/full PostgreSQL、RAG、Harness、compile/pip/YAML、Secret/tracked-data、governance/diff、
  Linux package 与 exact-SHA 三 job。

## 12. 当前限制与面试表述

完成实施后可以说：

> 我用 owner-scoped latest-review locator 把玩家档案绑定到服务器 task/run，再用严格 HTTP/SSE decoder 和
> generation guard 组合 Product State、Summary、verified Markdown、Evidence 与 Training；profile 切换会
> abort 旧请求并关闭旧 stream，避免异步结果串号。

仍不能说：正式 Auth/RSO、Evidence 自动刷新、完整 Timeline/Training、生产长连接容量、HTTPS/备份/部署
或公网 SLA 已完成。

## 13. 后续已登记但不并入本批的 Core 验收

### 13.1 OP.GG useful-breadth gate

Stage 7 V1 不重开。lane-meta 之外，以真实产品消费者评估 `champion analysis` 与 `lane matchup guide` 两个
最低候选；`synergies` 只在阵容/双人路消费者成立时进入。每个工具仍需独立 schema/grammar/provenance、
费用、降级和 UI 用途，不按 18 个目录数量追求覆盖率。

### 13.2 完整真实融合 golden slice

当前真实 bundle 为 `degraded/unjoined`，不是完整纵向完成证据。8F 前必须至少一次使用可公开、可复现且
body-free 的样本完成：

```text
Riot 玩家比赛 + Data Dragon 静态定义 + Riot 官方 patch/update
  + OP.GG 对应 champion/meta/matchup
  → typed EvidenceBundle
  → 个性化训练建议
  → live UI 中可追溯 Evidence
```

允许真实结果诚实 degraded，但验收样本必须实际覆盖四类来源和建议/UI 消费；不能继续用缺来源的 replay
冒充该目标完成，也不能为追绿覆盖旧负面证据。

### 13.3 复盘节奏

每个 checkpoint 关闭时提供一次短复盘：做了什么、为什么、数据流、证据、限制、下一步；连续完成多个
checkpoint 时再给批次总复盘。聊天复盘不替代八维持久证据，八维材料也不替代实时进度感。

## 14. 设计门公共证据

design `4057c93f4ac1ac9ebd181528e559b084e3425e89` / Actions `32639561338` 的 exact-SHA
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。公共 pytest 1752、真实 PostgreSQL 194，
frontend unit 35/Playwright 12/typecheck/build 与 Linux package smoke 同 SHA 通过。该证据只关闭设计门；
本设计中的 backend/frontend implementation 仍未开始。
