# 8D Riot + OP.GG Evidence Fusion 实施计划

## Goal

在现有 Riot/Data Dragon/OP.GG typed 接缝之上实现 no-I/O、可重算、可审计的
`EvidenceBundle` 融合内核，并用 focused TDD 固定版本、来源、freshness、join、conflict、
partial provenance 和安全投影语义。

## Task 1 — Pure contracts（先红后绿）

- 新增 `app/evidence/fusion.py` 与 `app/evidence/__init__.py`。
- 新增 `tests/test_evidence_fusion_contracts.py`。
- 冻结 strict Pydantic models：Riot match, Data Dragon snapshot, official patch, join key,
  join/conflict/gap, claim 和 bundle。
- 固定 canonical digest、safe labels、时间/版本格式、不得携带 PUUID/Key/raw body。

## Task 2 — Deterministic fusion kernel

- 新增 `fuse_evidence()`；不调用网络、MCP、Provider 或读取环境变量。
- 处理 Riot↔patch↔Data Dragon 版本核对、OP.GG position/champion join、partial Meta 限制、
  expired/missing/conflict/schema gap。
- 返回 `complete/degraded/rejected` disposition、claims、confidence 和显式 reasons。

## Task 3 — Public data-only projection

- 增加 bundle `to_public_projection()` 与安全 data-only Context helper（如不扩展现有
  ContextTrust，则只返回 allowlisted payload，8E 再接正式 Context/UI）。
- 验证 projection 不包含 PUUID、Key、MCP body、Prompt、异常文本或 instruction-like 内容。

## Task 4 — No-I/O vertical/evidence

- 使用固定 Riot/Data Dragon/patch/OP.GG fixtures，证明完整匹配和降级分支。
- 更新 `docs/learning/8d-riot-opgg-evidence-fusion-core-walkthrough.md`、coverage、
  canonical state、active plan、roadmap/amendment/capability/project decisions。

## Task 5 — Exit gates

- focused + adjacent + full pytest；RAG、Harness dry-run、compileall、pip/YAML、SDK boundary、
  Secret/tracked-data/body-free、governance、diff check。
- 独立实现提交/推送，等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`。
- 公共全绿后才把 8D coverage 置 `complete`，并只交接 8E prepared/waiting authorization。

## Explicit boundaries

不读取 Key、不调用 Riot/OP.GG/Provider/LLM，不实现真实刷新、SSE、React、Auth/HTTPS、备份、
Multi-Agent、DAG、图数据库或第三方 Runtime。
