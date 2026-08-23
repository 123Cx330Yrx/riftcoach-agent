# ADR-0062：采用最新档案复盘定位器与客户端组合式 Live Workbench

- 状态：Accepted for `8e-productization` live-data integration design gate（2026-08-23，RQ-095）
- 范围：把 Batch D fixture 工作台安全接到 Batch B/C 已有 owner-scoped API 与 cursor SSE；补齐最新复盘
  定位、Recent Summary HTTP、typed Evidence HTTP 与安全 Markdown 消费合同。
- 不包含：Riot ID/RSO 电影感入口、正式 Auth/RSO、自动 Evidence refresh、完整 Timeline/Training、HTTPS、
  backup/restore、部署、公网发布或 8F。

## 背景

Batch D 已证明工作台的视觉、四态、Evidence Drawer、Training 摘要、响应式和无障碍，但它只消费严格
fixture。后端虽然已经公开 `/player-profiles`、task/event/SSE、run/report、Evidence/Product State 和
Training query，仍有四个真实接线缺口：

1. profile 没有到最新 conversation-bound recent-review task/run 的 owner-scoped 定位器；页面刷新后无法
   知道该加载哪次复盘；
2. `RecentSummaryView` 已有严格查询服务，但没有 HTTP endpoint；
3. `EvidenceSnapshotResponse.projection` 在 OpenAPI 中仍是自由 `object`，浏览器缺少稳定嵌套 schema；
4. fixture 的编辑式标题、结构化 Coach 摘要和 session completion 不是现有后端事实，live 模式不能继续
   把它们显示成真实数据。

## 历史视觉连续性与未结范围

RQ-094 对“Stage 8 裁决到正式开工”区间做了定向 session-log 复核。最终视觉三方向不是 Batch D 的施工
三案，也不是 `Hextech Tactical Editorial` 的另一个名字：

| 方向 | 长期职责 | 当前裁决 |
|---|---|---|
| `Rift Awakening` | 电影感入口、战争迷雾、Rift 路径、Coach Core 与 Riot ID/RSO 叙事 | 后续 8E 高视觉预算模块 |
| `Esports Intelligence` | 长期使用的电竞分析工作台、Timeline、Evidence 与 Training | 主产品；Batch D 是首个静态纵切 |
| `Void Holographic Lab` | 3D/全息 Hero 视觉实验 | 只有在性能、移动、reduced-motion 与维护门通过后局部采用 |

最终组合固定为 `Cinematic Portal → Broadcast Workbench`。当前 live integration 只让第二层消费真实后端；
它不得删除第一层或把完整产品缩成普通 Dashboard，也不得借接线批提前实现第三层 WebGL 工作台。
`Hextech Tactical Editorial` 是 A/B 两层共享的 tokens、字体、材质与状态语言；`Rift Command Center` 是
方向 B 的首个施工切片，二者都不取代三方向裁决。

同一复核还发现两项未完成目标：OP.GG 当前只产品化 lane-meta；真实融合 replay 仍是
`degraded/unjoined`，缺 Data Dragon/official patch、个性化训练建议和前端追溯。本 ADR 不假装顺手解决
它们。后续必须分别通过 OP.GG useful-breadth gate，以及一次
`Riot match + Data Dragon + official patch + OP.GG → training advice → UI evidence` 的真实 golden slice；
两者均须在 8F 最终退出前关闭，但不能扩大当前 locator/API/SSE 批次。

## 方案比较

| 方案 | 裁决 | 主要权衡 |
|---|---|---|
| A. `GET /runs/{run_id}/workbench` 单一 BFF 大 DTO | 拒绝当前采用 | 首屏调用少，但把 task、publication、Evidence、Training 和 UI 版式耦合到一个新聚合真源；部分失败和 SSE 更新更难保持诚实 |
| B. 浏览器只依赖 URL/localStorage 中的 task/run ID | 拒绝 | 后端变化最小，但刷新、跨设备和档案切换没有服务器真源；容易把旧 run 绑定到新 profile |
| C. 薄 latest-review locator + 现有 API 客户端组合 | 采用 | 只补缺失 identity seam；各 API 保持原职责，浏览器用严格 decoder 和 profile/task/run generation 防竞态；调用数略多但作品集规模可控 |

## 决策

### 1. 新增 owner-scoped latest-review locator

新增 `GET /player-profiles/{player_profile_id}/reviews/recent/latest`。它只定位该 active profile 最新一条可见、
conversation-bound recent review；不扫描 legacy 无 identity task，不返回 owner、PUUID、Conversation 私有字段、
worker/lease/checkpoint 或 Artifact 路径。

- profile 不存在、hidden、cross-owner：404，统一 `player_profile_not_found`；
- profile 存在但没有复盘：200，`latest_review=null`；
- 有复盘：返回 task/run/status/timestamps/publication/report availability 与现有 endpoint links；
- “最新”按 `created_at DESC, task_id DESC` 确定，包含 active、failed、cancelled 和 succeeded，不能跳过失败
  去找更好看的历史成功结果；
- 复用现有 relationship/task 索引，当前不加 migration；只有查询计划或规模 Bad Case 才增加复合索引。

定位器使用独立 product port/service/repository，不把新方法强塞给所有现有 `TaskRepository` Fake。

### 2. 补 Recent Summary，复用 verified Markdown report

新增 `GET /runs/{run_id}/recent-summary`，调用现有 `RunQueryService.get_recent_summary()`；owner/task 终态和
错误语义与 `/runs/{run_id}`、`/report` 一致。只允许 published/degraded recent-form run 返回聚合 Summary；
active、failed/cancelled、rejected、wrong-skill 和 integrity failure 均 fail closed。

现有 `/runs/{run_id}/report` 继续返回 Harness 验证后的 `text/markdown`，不再从 Markdown 猜造
`verdict/strengths/priorities/nextSession`。前端采用 `react-markdown` 的受限路径：固定版本/lockfile、
`skipHtml`、不启用 `rehype-raw`，只渲染 allowlisted heading/paragraph/list/emphasis/code/blockquote/hr，拒绝
image 和外部 link。实施时总 JS gzip 必须不高于 150 kB；超出则停止采用并回到 escaped plain-text 方案。

### 3. Evidence wire schema 与浏览器 decoder

不改变 `/runs/{run_id}/evidence` 的 JSON shape，但把 `projection: dict[str, object]` 收紧为嵌套 Pydantic HTTP
models，使 OpenAPI 明确 sources、matches、joins、conflicts、gaps 和 claims。前端仍把所有 `fetch().json()`
视为 `unknown`，用手写 exact decoder 校验 schema/version/enums/finite numbers/timestamps/identity binding；
当前端消费集合很小，不引入 Zod 或 OpenAPI codegen。

API wire DTO 与 UI view model 分开：decoder 先得到严格 wire model，adapter 再映射为 camelCase 工作台视图。
`observed` 只在 adapter 映射为 UI 的 `public_observed`。未知字段、枚举或 identity mismatch 不做 best effort，
进入安全 client error。

### 4. 前端组合与身份隔离

默认 live 页面使用同源 `/api`；Vite development proxy 去掉 `/api` 前缀，产品 API 不开放 wildcard CORS，
前端不保存 token、owner 或 Key。fixture 只在显式 `?scenario=` preview/test 路径加载。

每次 profile 选择创建新的 load generation 和 `AbortController`，先关闭旧 EventSource，再读取：

```text
profiles
  → latest-review locator
    → task + product-state
      ├─ active: event page + one EventSource
      └─ terminal: run + recent-summary/report + optional evidence
  → self only: training plan + progress
```

任何晚到 response/event 必须同时匹配 generation、player profile、task 和 run，才能进入 UI。切换 observed
profile 立即清空旧 self Summary/report/training，不保留“先显示旧内容再刷新”的 stale-while-revalidate。

### 5. SSE 与产品状态分层

使用浏览器原生 `EventSource`，同源 cookie-compatible，不引入第二个 SSE parser。每次选中 task 最多一个
stream；profile switch、terminal event、component unmount 必须关闭。浏览器按标准携带 Last-Event-ID；
服务端现有 cursor replay 继续防重复。

短暂 SSE 断线只显示 `live updates reconnecting` 客户端提示，不把 Product State 改成 rejected。terminal
event 到达后关闭 stream，重新读取 task/product-state，再按 Product State 决定是否加载 report/summary/
evidence。没有 Evidence snapshot 时必须诚实显示 `degraded/evidence_not_available`；本批不临时调用 Riot 或
OP.GG 追绿。

### 6. Live UI 只显示真实可推导字段

- Recent panel 不再使用硬编码战术 headline；标题改为静态产品标签，全部数字来自 Recent Summary；
- Coach Brief 显示 verified Markdown，不从文本猜结构；rejected/not-ready 继续不读报告；
- self Training 显示 plan title/objective、metric baseline/target/current、trend/sample count；删除 fixture-only
  `2/5 sessions`、completion percent 和 next action；
- observed profile 不调用 Training endpoint，只显示静态 read-only 学习边界，不推断私人训练状态；
- Evidence label/detail 只由 typed source/provenance/freshness/join/gap code 确定性映射，不生成隐藏推理。

## 非功能门

- 每次 profile selection：最多 1 个 active EventSource；请求全部可 abort；不发 Riot/OP.GG/Provider/LLM；
- 同源 `/api`，无浏览器 secret/localStorage token，不放宽当前 CORS；
- 客户端错误、Product State、SSE reconnect 三类状态保持独立；
- desktop/tablet/mobile、keyboard/focus/reduced-motion/axe 现有门全部保留；
- production JS gzip ≤ 150 kB；没有第二套动画栈、query/cache 框架或 runtime schema dependency；
- PostgreSQL locator、HTTP DTO/OpenAPI、browser live flow、SSE cleanup/reconnect、identity race 和无远程 I/O
  必须由分层测试证明；本批不宣称外部 SLA。

## 后果

正面影响：live 页面能从服务器事实恢复当前 profile/run，保持后端职责清晰，并把静态稿中不存在的数字
及时移除。代价是客户端需要维护少量 endpoint decoder 和显式组合状态；作品集规模下这是可测试的合理
复杂度。若以后实测网络 waterfall 成为首屏 Bad Case，再用相同 view model 评估 BFF，不预先建立第二真源。
