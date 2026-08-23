# 8D Riot + OP.GG Evidence Fusion：从多份 JSON 到可解释证据包

这份材料记录 `8d-riot-opgg-evidence-fusion-core` 的当前本地实现和边界。设计依据是
[ADR-0055](../adr/0055-adopt-typed-evidence-bundle-fusion.md)、[8D 设计](../plans/2026-08-23-8d-riot-opgg-evidence-fusion-design.md)
和[实施计划](../plans/2026-08-23-8d-riot-opgg-evidence-fusion-implementation.md)。implementation/evidence
`a274b7f` 已由 Actions `32598480400` 完成 exact-SHA 三 job；这仍不等于实时外部刷新或 8E 产品化。

## 1. 问题与原理

Riot、Data Dragon、官方 patch 和 OP.GG 不是同一种数据：Riot 说明玩家实际对局，Data Dragon
解释版本化静态 ID，patch 说明官方版本事实，OP.GG 只给当前 Meta 快照。直接 `dict.update()`
会丢掉来源和时间边界，最危险的错误是把 OP.GG 缺失的 patch 静默补成 Riot patch。

8D 采用 `EvidenceBundle`：每条来源先变成严格 typed snapshot，再用显式 join key（region、queue、
position、champion、optional patch）做确定性融合。`provenance` 是“谁提供了它”，`freshness` 是“此时
能否使用”，`conflict` 是“来源互相不一致”，`gap` 是“应该有但缺失/过期”。`confidence` 只是这些规则
的有限投影，不是模型拍脑袋的概率。

## 2. 设计与实现

`app/evidence/fusion.py` 提供：

- `RiotMatchEvidence`：只保留 allowlisted match facts，不保留 PUUID 或原始响应；支持 Data Dragon 中文 label；
- `DataDragonSnapshot` 与 `OfficialPatchEvidence`：版本、时间和 source digest；
- `EvidenceJoinKey`、`EvidenceJoin`、`EvidenceConflict`、`EvidenceGap`：把比较维度和失败状态结构化；
- `EvidenceBundle`：不可变 sources/joins/conflicts/gaps/claims/disposition/confidence，digest 覆盖 canonical projection；
- `fuse_evidence()`：纯函数，不读取环境、不创建 Client、不调用网络/MCP/Provider/LLM；
- `to_public_projection()`：给 8E Coach/UI 的 allowlisted、body-free 投影。

`app/evidence/adapters.py` 把既有 Summary row 和 Data Dragon identity 投影到新契约。它只接收已经
物化的输入，role 会把 `TOP/MIDDLE/BOTTOM/UTILITY` 归一到 `top/mid/adc/support`，patch 只提取明确
的 major.minor，错误统一为 body-free `EvidenceAdapterError`。

Stage 7 的 `MetaEvidence` 直接复用。partial Meta 可以生成 `current_meta_recommendation`，但不能生成
`exact_patch_meta_comparison`；只有 complete provenance 且 patch 精确匹配时才允许后者。

## 3. 代码地图

| 层 | 文件 | 职责 |
|---|---|---|
| evidence package | `app/evidence/__init__.py` | 导出稳定 typed seam |
| source adapter | `app/evidence/adapters.py` | Summary/Data Dragon no-I/O 投影 |
| fusion kernel | `app/evidence/fusion.py` | 版本核对、Meta join、digest、降级和 public projection |
| upstream Meta contract | `app/meta/models.py`, `app/meta/opgg.py` | Stage 7 partial provenance 与 selected catalog |
| existing Riot/static | `app/lol/summary_schema.py`, `app/lol/match_analyzer.py`, `app/lol/data_dragon.py` | 原始领域事实和静态服务 |
| focused tests | `tests/test_evidence_fusion_contracts.py`, `tests/test_evidence_fusion_vertical.py` | 纯合同、冲突、过期、no-I/O 纵向 |

## 4. 数据流与控制流

```text
materialized Summary/Data Dragon/official patch/Meta
  → strict source contracts + digest
  → explicit join key
  → version/freshness/provenance checks
  → EvidenceBundle
  → allowlisted data-only projection
```

典型 partial Meta 路径：Riot match `15.16` + Data Dragon `15.16.1` + official patch `15.16` + OP.GG
partial snapshot，会得到 `complete` 的结构化包和 `medium` confidence；它可以支持 current snapshot，
但不产生 exact-patch Meta claim。缺少 Meta 会是 `degraded`，而 Riot facts 仍可用。版本冲突会保留双方
digest，join 变成 `conflict`，不会让后写入的来源覆盖先写入的来源。没有任何 Riot match 时只返回
`rejected`，不暴露 claims。

## 5. 验证证据

TDD 首先以 `ModuleNotFoundError: app.evidence` 红灯，随后最小 contracts/kernel/adapters 变绿。
当前 focused 集合为 `18 passed`（contracts + vertical），相邻 OP.GG Meta/Context 集合为 `48 passed`。
覆盖的 Bad Case 包括：

- partial Meta 不继承 Riot patch；
- complete Meta patch mismatch；
- Data Dragon/Riot patch mismatch；
- missing/expired Meta、missing Riot；
- instruction-like label、malformed patch、duplicate match identity；
- public projection 中不得出现 PUUID、Key、raw MCP body、Prompt 或异常正文；
- monkeypatch `requests`/`os.getenv` 后仍完成 no-I/O vertical。

本地完整 pytest 为 `1691 passed, 134 skipped, 1 warning, 127 subtests passed`；RAG development/holdout、
Harness dry-run、compileall、pip、YAML、governance 和 diff 均通过。134 个 skip 主要是本机无 PostgreSQL/
Docker/Linux 条件；它们不能替代 exact-SHA 公共 PostgreSQL/Linux 证据。

公共 run `32598480400` 精确绑定 implementation/evidence SHA `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48`：

- `pytest`：`1692 passed, 133 skipped, 1 warning, 127 subtests passed`；RAG/Harness/安全门全绿；
- `postgres-migrations`：PostgreSQL 17 上 `186 passed, 1 warning`，migration 可逆且 metadata=head；
- `packaging-smoke`：Linux no-I/O 产品纵向 schema 1.6，外部 Riot/Provider 调用 0，非 root/image boundary 全绿。

## 6. Runbook

```powershell
C:\Users\33502\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_evidence_fusion_contracts.py tests/test_evidence_fusion_vertical.py -q
C:\Users\33502\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_opgg_meta_adapter.py tests/test_opgg_meta_smoke.py tests/test_context_builder.py -q
python scripts/check_project_governance.py
git diff --check
```

真实 Riot/OP.GG 调用不属于这组 runbook；它们需要后续检查点明确批准和独立的费用/隐私/公开证据。

## 7. 失败、安全与范围边界

- 只接受 Pydantic strict source contracts；schema drift、无版本值、控制字符或 instruction-like label fail closed；
- OP.GG partial provenance 不会被 Riot patch、同日时间或 Data Dragon 版本“补全”；
- digest 是完整性身份，不是上游真实性证明；freshness 由时间窗口和版本比较显式给出；
- `degraded` 是产品可解释状态，不应被调用方当成完整 patch 结论；
- 不保存 PUUID、Key、原始 MCP/Provider body、Prompt 或 chain-of-thought；
- 8D 当前不实现刷新调度、React/SSE/Auth/HTTPS/备份、Multi-Agent/DAG/图数据库或第三方 Runtime；
- `EvidenceBundle` 仍是进程内 pure seam，尚无 PostgreSQL 持久化和实时上游刷新证据。

## 8. 面试准确表述

可以说：

> 我没有把 Riot 和 OP.GG JSON 直接拼接，而是把官方事实、版本静态、patch 和 partial Meta 变成带来源
> digest 的 typed EvidenceBundle。融合按 region/queue/position/champion/patch 显式 join；缺失、过期和
> 冲突会保留来源并降级，OP.GG 缺 patch 时不会继承 Riot patch。

不能说：

- 已实时接入所有 OP.GG 工具或完成公网刷新；
- OP.GG 提供了 Riot 官方 patch 或 upstream freshness；
- 已完成 8E Web/Auth/SSE/部署或 Multi-Agent 产品采用；
- 本地 18 项测试等于公共 PostgreSQL/Linux exact-SHA 证据。
