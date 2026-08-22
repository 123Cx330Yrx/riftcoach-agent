# 8D Riot + OP.GG Evidence Fusion 设计

## 1. 给初学者的心智模型

证据融合不是“把两个接口返回的 JSON 拼成一个大字典”。可以把每个来源想成一张带
标签的证据卡：Riot 卡片说明玩家在某局做了什么，Data Dragon 卡片说明某个版本的
英雄/装备 ID 叫什么，patch 卡片说明官方版本事实，OP.GG 卡片说明当前环境下大家
常用什么。融合器做的工作是给卡片贴上 join key（地区、队列、位置、英雄、版本），
检查标签和时间，再把“能一起解释什么”和“不能一起解释什么”写清楚。

这里的 provenance（来源证明）回答“这条值是谁提供的”；freshness（新鲜度）回答“这条
值现在还能不能用”；conflict（冲突）回答“两个来源对同一个 join key 不一致时发生了
什么”；confidence 不是凭感觉给分，而是由来源等级、版本匹配和状态规则得到的有限
结论。OP.GG 的 partial provenance 不会因为 Riot 同日有 patch 就自动变成 complete。

## 2. 范围与不做什么

本检查点实现：

- `RiotMatchEvidence`、`DataDragonSnapshot`、`RiotPatchEvidence` 三个官方/静态 typed 输入；
- 复用 Stage 7 `MetaEvidence` 作为 OP.GG typed 输入；
- `EvidenceJoinKey`、`EvidenceJoin`、`EvidenceConflict`、`EvidenceGap`；
- 纯函数 `fuse_evidence()` 和 `EvidenceBundle` digest/public projection；
- 过期、缺失、patch/version mismatch、Meta partial、instruction-like label 和 schema
  drift 的 TDD；
- no-I/O 纵向 fixture，证明 bundle 能进入 data-only 投影。

本检查点不实现：

- Riot/OP.GG 真实网络调用、Key、刷新后台、付费 MCP；
- 8E React/SSE/Auth/HTTPS/部署；
- Multi-Agent、DAG、图数据库、第三方 Agent Runtime；
- 用 OP.GG 补齐 Riot 的 patch、source time 或历史事实。

## 3. 方案比较

| 方案 | 优点 | 风险 | 裁决 |
|---|---|---|---|
| 直接 JSON merge | 写得快 | 丢 provenance，冲突静默覆盖 | 拒绝 |
| 通用 claim graph | 关系表达强 | 新持久化/查询复杂度，超出当前规模 | 暂缓 |
| typed bundle + pure kernel | 可重算、可审计、易测试、复用现有接缝 | 模型数量增加 | 采用 |

## 4. 契约与数据流

```text
adapters / fixtures (no-I/O)
  ├─ RiotMatchEvidence[]
  ├─ DataDragonSnapshot?
  ├─ RiotPatchEvidence?
  └─ MetaEvidence[]
        │
        ▼
fuse_evidence(now)
  ├─ validate source digests and time windows
  ├─ derive explicit join keys
  ├─ compare Riot ↔ patch ↔ Data Dragon versions
  ├─ join OP.GG only by position + champion (+ patch when known)
  └─ derive claims, gaps, conflicts, confidence, disposition
        │
        ├─ EvidenceBundle (immutable, digest-bound)
        └─ allowlisted data-only projection for later Coach/UI
```

`EvidenceBundle` 的 `claims` 只允许以下语义：`riot_match_facts`、
`data_dragon_static`、`official_patch_facts`、`current_meta_recommendation`、
`exact_patch_meta_comparison`。后者只有 complete Meta provenance 且 patch 精确匹配时
才可出现；Stage 7 partial Meta 永远只有 `current_meta_recommendation`。

## 5. 失败、安全与降级

| 输入情况 | 结构化结果 | 是否可给建议 |
|---|---|---|
| Riot match 缺失 | `rejected` | 否 |
| OP.GG 缺失/过期 | `gap` + `degraded` | 可，仅基于 Riot |
| Riot patch 与 Data Dragon 不同 | `conflict` + `degraded` | 可，但禁止 exact-patch 结论 |
| OP.GG partial 无 patch | `joined_partial` | 可作 current snapshot |
| complete Meta patch 不匹配 | `conflict` + `degraded` | 可，保留两边来源 |
| 标签含 instruction-like 文本 | `schema_rejected` | 否，拒绝该来源 |
| digest/时间/字段漂移 | `schema_rejected` | 否，fail closed |

融合器不保存原始 upstream body、PUUID、Key、Prompt 或隐藏推理；conflict/gap 只保留
allowlisted code、source 和 digest。`confidence` 是 `high/medium/low/unknown` 的规则
投影，不是模型概率。

## 6. 验证计划

1. 先写 pure contract 红灯：严格字段、digest、join key、claim 限制和 projection。
2. 再写 fusion 红灯：完整匹配、partial Meta、missing/expired/conflict/schema drift。
3. 加 no-I/O fixture vertical：Riot/Data Dragon/patch/OP.GG → bundle → data-only payload。
4. 运行相邻 Meta/Context/Runtime 测试、完整回归和治理/安全门；公共 exact-SHA 三 job
   通过前 coverage 保持 `planned`。

## 7. 证据边界与面试表述

可以准确说：

> 我用不可变 typed EvidenceBundle 把 Riot 官方事实、Data Dragon 版本静态、官方 patch
> 和 OP.GG partial Meta 放进同一个可重算融合内核；每个 join 都带 key、来源、digest、
> freshness 和 conflict，冲突时降级而不覆盖。

不能说：

- 已经接入所有 OP.GG 工具或完成实时刷新；
- OP.GG 提供了 Riot patch 或 upstream freshness；
- 已完成公网部署、Auth、SSE 或 Multi-Agent 产品化。
