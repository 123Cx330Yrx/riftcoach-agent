# ADR-0055：采用 typed EvidenceBundle 的 Riot + OP.GG 证据融合内核

## Status

Accepted for `8d-riot-opgg-evidence-fusion-core`（2026-08-23）。

## Context

8D 需要把四类来源交给同一个 Coach/产品流程：Riot 官方账号与对局事实、Data
Dragon 版本化静态定义、Riot 官方 patch/update 事实，以及 Stage 7 已准入的 OP.GG
partial Meta。它们回答的问题不同，更新节奏不同，可信范围也不同：Riot 记录某个玩家
实际发生了什么，Data Dragon 解释一个版本中的英雄/装备 ID，patch 事实说明版本变化，
OP.GG 只提供允许范围内的当前聚合快照。

直接合并 JSON 会丢失来源、版本和时间边界，容易把 OP.GG 缺失的 patch 错误地继承成
Riot patch，也会在冲突时静默覆盖。8D 还必须拒绝过期、缺失、schema drift 和
instruction-like payload，并给后续 Coach/UI 一个可解释的降级结果。

## Decision

采用一个纯函数驱动的、不可变且可重算 digest 的 `EvidenceBundle`：

```text
RiotMatchFacts + DataDragonSnapshot + RiotPatchFact + MetaEvidence
        │ typed validation
        ▼
deterministic join keys (region, queue, position, champion, patch)
        │ provenance/freshness/conflict policy
        ▼
EvidenceBundle (claims, joins, conflicts, gaps, disposition, digest)
```

融合内核只接收已经由各自 adapter 取得的 typed snapshot，不读取 Key、不调用网络、
不执行 MCP/Provider/LLM。Stage 7 的 `MetaEvidence` 仍是唯一 OP.GG 输入，且它的
partial provenance 只能支持 `current_snapshot_recommendation`；它不能获得 Riot patch、
source-generated time 或 upstream freshness。

融合规则固定为：

1. Riot facts、official patch 和 Data Dragon 版本只由它们自己的来源声明；不跨来源补值。
2. join key 显式包含 routing region、queue、position、champion name 和 optional patch。
3. Data Dragon 与 Riot patch 的版本不一致、Riot match 与 official patch 不一致，都会
   进入 conflict 列表；任何冲突都让 bundle `degraded`，不静默覆盖。
4. OP.GG Meta 只有在 position/champion 可 join 且 evidence 未过期时才进入 joined
   projection。partial Meta 可以支持当前快照建议，但永远不能支持 exact-patch 或历史
   patch claim。
5. 缺失 patch、静态版本、Meta join 或过期 Meta 进入 typed gap；没有 Riot match fact
   的输入只能得到 `rejected` bundle。
6. `EvidenceBundle` 的 digest 覆盖所有 source digests、join/conflict/gap 和 claim
   projection；公共投影只暴露 allowlisted facts/provenance/status，不暴露 PUUID、Key、
   原始 MCP body、Prompt 或 Provider 错误。

## Alternatives Considered

### A. 无类型 JSON merge

拒绝：实现短，但无法证明 join key、来源优先级和不继承 patch，冲突会被最后写入者覆盖。

### B. 通用 claim graph / event-sourced evidence store

暂缓：可表达更多关系，但在当前单服务器作品集规模下引入新的持久化/查询复杂度；8D
只需要可重算、可审计的 bundle，后续若真实 Bad Case 证明需要图查询再另立 ADR。

### C. Typed EvidenceBundle + pure fusion kernel（采用）

保留现有 adapter、Context、Runtime Trace 和 PostgreSQL 资产，融合规则可单测、可复放，
失败时能清晰投影 `degraded/rejected`。代价是需要显式维护来源模型和 join/conflict 规则。

## Consequences

### Positive

- Coach 和 UI 可以区分官方事实、版本静态、patch 事实与当前 Meta，而不是看一份无来源 JSON。
- 缺失、过期、冲突和 partial provenance 都是可测试的结构化结果。
- 纯函数 no-I/O 设计适合 TDD、公共 CI 和后续 8E 接入。

### Negative

- 需要在 adapter 边界把已有 summary/Meta 数据严格投影到新模型。
- `degraded` 是正常产品状态，调用方不能把它当成完整 patch 结论。

### Deferred

- 真实 Riot/OP.GG 调用、缓存/刷新调度、SSE、前端和正式 Auth 留到 8E/8F。
- 自动 patch/update 抓取和历史 Meta 存储只有在 8D 的 typed seam 通过后另行设计。

## References

- `docs/adr/0048-admit-opgg-with-partial-provenance-and-selected-catalog.md`
- `docs/adr/0051-adopt-stage8-evidence-gated-runtime-fusion-and-productization.md`
- `docs/plans/2026-08-21-opgg-meta-adapter-design.md`
