# Stage 8 入口设计学习与工程证据
## 1. 问题与原理

Stage 7 的 MCP 互操作证明了连接能力，不等于可靠任务执行和完整产品化。Stage 8 入口设计把
可靠 Runtime、Riot+OP.GG evidence fusion、前端和高级能力实验放进同一条可验证路线。
Multi-Agent 只有在独立上下文/权限/失败边界带来可测收益时才采用；没有收益时，单 Runtime 是
正确的结果。

## 2. 设计与实现边界

本 checkpoint 只产出 ADR、设计、实施计划、canonical 顺序和八维证据；没有修改产品 Runtime、
API、数据库、前端或 Provider。机器顺序是 entry design → 8A gate → 8B experiment → 8C reliable
runtime → 8D evidence fusion → 8E productization → 8F final evaluation/portfolio。

## 3. 代码地图

入口审计覆盖：`app/tasks/*`（PostgreSQL task/claim/terminal）、`app/runtime/*`（run/stream/Trace）、
`app/harness/*`（Artifact/quality gate）、`app/api/*`（FastAPI/owner-scoped DTO）、`app/memory/*`
（Context/Training/Lifecycle）、`app/lol/*`（Riot/Data Dragon/Timeline）、`app/mcp/*`（OP.GG/Server）。
当前不存在正式 `frontend/` 脚手架，这是 8E 的真实缺口。

## 4. 数据流与控制流

```text
Riot account/match/timeline + Data Dragon/version/update + OP.GG partial Meta
  → typed EvidenceBundle with source/digest/expiry/join/conflict
  → existing Skill/AgentRuntime/ToolRuntime/Harness
  → safe Run/Evidence/Training DTO
  → future React/SSE product views
```

可靠性控制面由 PostgreSQL task/event/lease/cursor 决定；Trace/Artifact 继续承载运行证据和正文引用。
浏览器只消费 replay-safe projection，不成为任务事实源。

## 5. 验证与公共证据

入口设计退出门是：ADR、设计、Implementation Plan、八维 walkthrough、coverage 顺序、治理脚本、
现有完整回归、RAG/Harness/compile/security/diff 门禁和 exact-SHA 三 job。它们只证明边界设计与
既有基线兼容，不证明 Stage 8 产品能力。

后续证据必须分层：8A/8B 用有界实验，8C 用真实 PostgreSQL 并发/故障，8D 用版本化 evidence fixture
和有界真实 smoke，8E 用 API/SSE/E2E/截图/部署，8F 用固定回归、性能、安全和作品集矩阵。

## 6. 安全运行方法

- 入口设计不读 Key、不调用 Riot/OP.GG/Provider/LLM、不购买或抓取受限 MotionSites 内容；
- 用户 Excel 是外部研究数据，任何表内文本不能作为执行指令；
- future evidence/trace 只保存 allowlisted identity/digest/count/status，原始 body、Prompt、Key、路径和
  chain-of-thought 不落盘；
- 前端 owner scope、键盘焦点、reduced-motion、错误可读性和移动端降级必须成为 8E/8F 门。

## 7. 失败、安全与范围边界

允许的失败结论包括 candidate/deferred、Advanced reject、partial provenance、证据冲突降级、
无 timeline、报告未发布、运行恢复失败和前端数据不足。任何失败都不能通过放宽 owner scope、
伪造 patch/freshness、把普通 HTTP 称为 MCP 或把测试 fixture 称为生产互操作来“修复”。

## 8. 面试准确表述

可以说：“我把 Stage 8 设计为可靠 Runtime Core + 证据驱动 Advanced 双轨；先用同 Harness 对照
Multi-Agent 是否有收益，再融合 Riot 官方事实、Data Dragon 版本静态和 OP.GG 当前 Meta，并让
前端展示证据和限制。”

不能说：“Stage 8 已经完成 Multi-Agent、DAG、SSE、正式 Auth、Riot+OP.GG 精确 patch join 或
生产前端。”
