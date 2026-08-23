# 8E Batch C Evidence / Product API 设计

## 1. 初学者教学

### 真实问题

`EvidenceBundle` 已经会判断“证据是否能拼在一起”，但没有一个产品级仓库保存它；task event 已经
能从 PostgreSQL 重放，但浏览器还不能订阅；任务状态、Harness 发布状态和证据新鲜度又是三套不同
概念。前端若直接接这些底层值，就会把 `running`、质量拒绝、证据过期和系统失败混成一个“报错”。

### Agent / 软件原理

- **不可变快照**：保存当时真实得到的 typed 证据，不覆盖历史；刷新产生新 revision。
- **控制面与数据面分层**：PostgreSQL 保存 owner/run/revision/expiry 和 body-free typed snapshot；
  Runtime Trace、报告 Artifact 继续各自负责内部运行与正文。
- **事件重放**：SSE 只是一种送达方式；cursor 让消费者断线后从数据库事实继续。
- **状态投影**：产品状态是多个底层事实的确定性映射，不由前端临时 if/else 猜测。

### 本批做与不做

做：snapshot contract/serializer、PostgreSQL 0011/Repository、refresh revision、expiry view、四态 projector、
owner-scoped evidence/product endpoints、cursor SSE、composition/package/tests/八维证据。

不做：真实 Riot/OP.GG/LLM 调用、自动 refresh scheduler、React、Auth/RSO、HTTPS、备份、Multi-Agent、
DAG、第三方 Runtime 或新的队列基础设施。

## 2. 组件设计

| 层 | 组件 | 职责 |
|---|---|---|
| domain | `app/evidence/storage.py` | strict storage projection、snapshot identity、freshness、usable claims、四态 projector |
| port | `EvidenceSnapshotRepository` | append/replay 与 owner-scoped latest query |
| SQL | `evidence_snapshot_record.py` + migration 0011 | append-only JSONB snapshot、复合 FK、revision/refresh/digest/size constraints |
| service | `EvidenceProductService` | 将 task view 与 latest snapshot 组合成 Evidence view 和 ProductRunState |
| stream | `app/tasks/sse.py` | cursor resolution、SSE frame allowlist、bounded polling/keepalive/error close |
| HTTP | `evidence_models.py` / `main.py` | `/runs/{run_id}/evidence`、`/product-state`、`/tasks/{id}/events/stream` |
| composition | `api/composition.py` | lifespan 内绑定 SQL repository/service；构造阶段保持 no-I/O |

## 3. Snapshot 合同

```text
EvidenceBundleSnapshot
  snapshot_id: UUID
  task_id: UUID
  run_id: bounded server run id
  owner_id: private owner scope
  revision: 1..N
  refresh_id: bounded idempotency identity
  bundle: strict reconstructed EvidenceBundle
  stored_at: UTC
  expires_at: UTC | null
  snapshot_digest: SHA-256(identity + bundle digest + time)
```

storage JSON 只使用 8D 已 allowlist 的 Riot/Data Dragon/patch/OP.GG facts、joins/conflicts/gaps/claims。
`MetaEvidence` 必须从 dict 重建 dataclass 并重算自身 digest；不能用 `Any` dict 跳过验证。JSONB 正文设置
硬大小上限，禁止 raw response、PUUID、Key、Prompt、request payload 或任意异常文本。

### Refresh 语义

1. internal writer 提交 owner/task/run、`refresh_id`、typed bundle 和时间；
2. Repository 锁 task，校验身份与状态，查询同 refresh identity；
3. 相同 digest replay；不同 digest conflict；新 refresh 分配 `max(revision)+1` 并 insert；
4. latest 始终是最高 revision，绝不回退旧 snapshot；
5. Batch C 只建立这条持久接缝，不主动发起网络 refresh。

## 4. Expiry 与 public evidence view

`expires_at` 是所有明确易过期来源的最早 expiry。查询时：

- `now < expires_at` 或无 expiry：`current`；
- `now >= expires_at`：`expired`，保留 snapshot/bundle digest 用于审计，但移除
  `current_meta_recommendation` / `exact_patch_meta_comparison` 的 usable claim；
- public view 返回 revision、bundle digest、stored/expires/freshness、disposition/confidence、usable claims、
  source/join/conflict/gap allowlist；不返回 owner、refresh_id、storage body 或内部路径。

## 5. 四态 projector

状态优先级：

1. active task → `not_ready`；`recovery_required` 使用独立 reason；
2. failed/cancelled → `rejected`，但 reason 分别是 execution failure/cancel；
3. succeeded + Harness rejected → `rejected`；
4. succeeded + report available，若 publication degraded 或 evidence missing/expired/non-complete → `degraded`；
5. succeeded + published + complete/current evidence → `published`。

这套合同只说明“当前产品结果是否可展示以及限制”，不覆盖 `TaskStatus`、Harness publication 或
Evidence disposition；响应会同时保留这些原始安全枚举，方便调试和前端解释。

## 6. SSE 合同

路径：`GET /tasks/{task_id}/events/stream`。

- query `after_cursor` 与 header `Last-Event-ID` 二选一；同时存在且不一致返回 422；
- response `text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`；
- lifecycle frame：`id: <cursor>`、`event: task.lifecycle`、`data: <TaskEventResponse JSON>`；
- idle 只发送 `: keep-alive` comment；连接到达有限窗口后自然关闭，客户端按 cursor 重连；
- terminal event 发出后关闭；Repository 错误只发 allowlisted `stream.error` 并关闭；
- 连接前 owner lookup，cross-owner 与不存在都 404。

## 7. 测试矩阵

- pure contract：storage round-trip/digest/tamper/size/expiry/claims/product-state matrix；
- migration/metadata：0011 upgrade/downgrade/reupgrade、约束、索引、复合 FK/cascade；
- PostgreSQL：append/replay/conflict、并发 revision、cross-owner、latest、tamper、task cascade delete；
- API：owner 404、current/expired evidence、四态全矩阵、body-free OpenAPI/errors；
- SSE：cursor/header、reconnect/no duplicate、terminal close、keepalive、safe failure、forbidden fields；
- composition/package：构造 no-I/O，lifespan bind，Fake/fixture evidence + event stream；
- exit：focused、真实 PostgreSQL collection、完整 pytest、RAG/Harness、compile/pip/YAML、security scans、
  governance/diff 与 exact-SHA 三 job。

## 8. 当前限制与面试边界

可以说：

> 我把 typed EvidenceBundle 作为 PostgreSQL 追加式不可变快照保存，用 revision 和 refresh identity 做
> 幂等刷新，用查询时 expiry 投影避免改写历史；SSE 复用 durable cursor event，断线可重放，并把 task、
> Harness 和 evidence 映射成四个产品状态。

不能说：已完成实时自动刷新、正式公网 Auth、生产级长连接容量、备份恢复、React 前端或生产 SLA。
