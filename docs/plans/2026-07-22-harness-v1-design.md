# Harness v1 设计说明

## 1. 目标

把当前分散的“生成 → 评测 → 修订 → 再评测”脚本组织成一个由确定性代码控制的运行生命周期。模型负责生成、审查和提出修订文本；Harness 负责顺序、状态、预算、Artifact、发布条件与失败降级。

Harness v1 只服务“基于现有 Summary 生成 Coach 报告”这一条线性流程。它不实现通用 DAG、Multi-Agent、Session、Memory、标准 MCP 或完整 Tool Runtime。

## 2. 为什么现在建设

当前各脚本能够单独工作，但调用者仍需人工决定：使用哪个输入文件、按什么顺序运行、评测失败后是否修订、最多修订几次，以及最后哪个文件可以视为正式报告。继续增强 RAG 只会让输入更丰富，不能解决运行过程缺少控制的问题。

Harness 先建立稳定生命周期，后续 Provider、RAG、Skill、Memory 和 Multi-Agent 才能接入统一边界。

## 3. 核心原则

1. **模型建议，代码裁决**：LLM 的 verdict 只是证据之一，代码检查 Schema、阈值、修订预算和终态。
2. **Artifact 显式传递**：步骤之间通过带类型、版本和哈希的产物传递结果，不依赖隐式文件名猜测。
3. **有限自主性**：修订次数、模型调用次数和可修改范围均有上限。
4. **失败可解释**：每次失败记录阶段、错误类别和降级选择。
5. **默认安全发布**：未通过质量门控的模型报告不得成为最终发布物。
6. **可重放**：Run Manifest 保存输入、配置、状态变化和产物引用。

## 4. 状态机

```text
CREATED
  → FACTS_READY
  → KNOWLEDGE_READY
  → DRAFT_READY
  → EVALUATING
      ├── PASSED → PUBLISHED
      ├── NEEDS_REVISION → REVISING → RE_EVALUATING
      │                         ├── PASSED → PUBLISHED
      │                         └── 未通过且预算耗尽 → DEGRADED / REJECTED
      └── FAIL → DEGRADED / REJECTED
```

`DEGRADED` 表示只发布确定性 Markdown 报告，并明确说明 Coach 报告未通过；`REJECTED` 表示连安全降级产物也不可用。终态不可再次向前推进。

## 5. Artifact 模型

每个 Artifact 至少记录：

```json
{
  "artifact_id": "唯一标识",
  "run_id": "所属运行",
  "kind": "PLAYER_SUMMARY",
  "schema_version": "1.0",
  "path": "相对运行目录的路径",
  "sha256": "内容哈希",
  "created_at": "UTC 时间",
  "producer": "facts/generator/evaluator/reviser/publisher"
}
```

Harness v1 使用以下类型：

- `PLAYER_SUMMARY`
- `DETERMINISTIC_REPORT`
- `RETRIEVAL_EVIDENCE`
- `COACH_DRAFT`
- `EVALUATION_RESULT`
- `REVISED_REPORT`
- `FINAL_REPORT`
- `RUN_MANIFEST`

Artifact 内容仍存文件，Manifest 只保存元数据与引用。这样保持实现轻量，同时为未来数据库或对象存储留出接口。

## 6. 运行目录

```text
data/runs/<run_id>/
├── manifest.json
├── inputs/
│   ├── player_summary.json
│   └── deterministic_report.md
├── retrieval/
│   └── evidence.json
├── drafts/
│   ├── coach_draft.md
│   └── revision_1.md
├── evaluations/
│   ├── evaluation_0.json
│   └── evaluation_1.json
└── output/
    └── final_report.md
```

该目录包含本地运行数据，默认进入 `.gitignore`。公开仓库只提交经过匿名化的固定样例。

## 7. 发布策略

- `verdict=pass` 且分数达到阈值：发布对应 Coach 报告；
- `needs_revision`：在预算允许时执行一次受限修订并复评；
- `fail`、评测器不可用、输出 Schema 非法或预算耗尽：降级为确定性报告；
- Summary 或确定性报告本身无效：拒绝运行，不生成正式报告；
- v1 默认最大修订次数为 1，避免自我循环。

分数阈值、最大修订次数和降级策略属于运行配置，必须写入 Manifest。

## 8. 幂等与过期结果

`run_id` 标识一次不可变运行。每次状态推进都检查 Manifest 当前状态。对已经进入终态的运行再次执行，只返回既有结果。任何携带旧 `attempt_id` 的评测或修订结果都不能覆盖当前 Artifact。

v1 是单进程同步运行，不实现分布式租约；先通过 `attempt_id` 和原子文件替换避免明显的旧结果覆盖。真正租约和恢复留到阶段 8。

## 9. 故障与降级

| 故障 | 行为 |
|---|---|
| Summary Schema 无效 | `REJECTED` |
| 确定性报告缺失 | `REJECTED` |
| RAG 不可用 | 记录故障，以空知识证据继续 |
| 草稿生成失败 | 发布确定性报告，`DEGRADED` |
| 评测响应非法 | 发布确定性报告，`DEGRADED` |
| 修订失败或越权 | 丢弃修订，发布确定性报告 |
| 复评未通过 | 发布确定性报告 |

## 10. 测试与验收

测试不依赖真实 GLM 或 Riot API，而使用 Fake Steps 验证状态机：

- 首次评测通过；
- 评测失败、修订后通过；
- 修订预算耗尽；
- RAG 故障降级；
- 非法评测 JSON；
- 修订破坏标题或异常缩短；
- 重复执行的幂等行为；
- 旧 attempt 结果不可覆盖新产物；
- Manifest 和 Artifact 哈希可验证。

完成标准是一条命令能够运行完整闭环，每个状态变化和发布决定均可从 Manifest 解释，并且未通过的模型草稿不会被发布。

## 11. 面试表述边界

可以准确表述为：实现了质量门控型 Agent Harness、版本化 Artifact、有限自修订、再评测、确定性降级和运行 Trace。

在阶段 2 完成时不能声称已经实现通用工作流引擎、分布式调度、Multi-Agent、持久化任务队列或标准 MCP。
