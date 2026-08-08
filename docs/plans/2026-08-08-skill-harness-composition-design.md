# 5D-5 Harness Composition & Typed Terminal Output 设计

## 1. 结论先行

5D-5 用一个新的 `DraftPreparationStep` 把旧的顺序检索/生成路径与 5D-4 的 Skill
Agent 草稿准备路径统一接入现有 `ReviewHarness`。Harness 仍然是唯一拥有评测、受限
修订、发布、确定性降级和拒绝权的控制面。

新建薄的 `SkillReviewExecutor`，负责把已经验证的
`ValidatedSkillExecution + ContextBundle` 绑定到一次 Harness run，并在终态后从落盘
Manifest 与完整性校验通过的 Artifact 构造该 Skill 声明的 Pydantic Output。

本轮不改变 Provider 文本协议，不调用真实 Provider，不实现 5D-6a 结构化输出，不引入
LangGraph、Agent SDK、Multi-Agent 或新依赖。

## 2. 初学者理解：这一步到底在接什么

5D-4 已经能让受限 Agent 做两件事：

```text
根据上下文生成一个草稿
记录它实际调用 knowledge.search 得到的知识证据
```

但“模型写出了一篇草稿”不等于“产品可以把这篇报告交给用户”。草稿可能数字错误、
引用不存在、因果表达过度，或者根本没达到最低分。

5D-5 做的是 composition（组合）：

```text
Agent 准备草稿与证据
          │
          ▼
既有 ReviewHarness
评测 → 最多一次受限修订 → 再评测
          │
          ├── published：发布通过门禁的最终报告
          ├── degraded：只返回确定性报告
          └── rejected：不返回报告
```

“Agent 会调用工具”是执行能力；“Harness 决定什么可以对外发布”是治理能力。把两者
分开后，即使以后换模型、Prompt 或 Agent SDK，质量门禁仍然不被模型绕过。

## 3. 当前缺口

现有 `ReviewHarness` 构造器直接依赖：

```text
RetrieverStep + GeneratorStep + EvaluatorStep + ReviserStep
```

5D-4 的 `SkillAgentDraftPreparer` 已经一次返回：

```text
CoachDraft + KnowledgeEvidence + AgentRunResult
```

如果直接增加 `run_prepared()`，会出现两套 Harness 控制流；如果给构造器同时保留
`retriever/generator/draft_preparer` 三个可选参数，会形成大量非法组合。两种方式都会让
评测、状态迁移和 Artifact 逻辑逐渐漂移。

## 4. 方案比较

### 方案 A：ReviewHarness 构造器接受两组互斥依赖

改动小，但调用方可能同时传或都不传，Harness 内部长期保留新旧分支。拒绝。

### 方案 B：新增 `run_prepared()`

表面最省事，实际会复制输入落盘、评测循环、修订计数、降级与发布逻辑。拒绝。

### 方案 C：统一 `DraftPreparationStep`，旧路径由 Adapter 兼容

Harness 只认识一个草稿准备合同。旧 Retriever/Generator 由
`SequentialDraftPreparer` 顺序调用；新 Skill Agent 由外层绑定 Adapter 转成同一结果。
采用。

## 5. Harness 中立合同

在 `app.harness.steps` 增加：

```python
@dataclass(frozen=True)
class DraftPreparationRequest:
    player_summary: Mapping[str, Any]
    deterministic_report: str

@dataclass(frozen=True)
class DraftPreparationResult:
    draft: CoachDraft
    knowledge: KnowledgeEvidence

class DraftPreparationStep(Protocol):
    def prepare(
        self,
        request: DraftPreparationRequest,
    ) -> DraftPreparationResult: ...
```

合同刻意不包含 `AgentRunResult`。Harness 是领域无关的质量控制器，不应该反向依赖
Agent 模块。完整 Agent run 由外层 `SkillReviewExecutor` 保留，后续 Trace/可观测性再
决定如何持久化。

## 6. 旧路径兼容

`SequentialDraftPreparer` 包装现有 `RetrieverStep + GeneratorStep`：

```text
DraftPreparationRequest
  → retriever.retrieve(RetrievalRequest)
  → generator.generate(GenerationRequest + KnowledgeEvidence)
  → DraftPreparationResult
```

CLI、现有 Harness 测试与工具 Adapter 都改为显式组装这个顺序 Adapter。成功路径的
知识、草稿、评测、修订和发布语义不变；失败仍只能降级或拒绝，不能绕过 Harness。

## 7. 新 Agent 路径的组合边界

`SkillReviewExecutor.execute(execution, context)` 先检查：

- execution 必须是 5D-1 产生的 `ValidatedSkillExecution`；
- context 的 run ID、Skill name 和 version 必须完全一致；
- Skill Manifest 必须要求质量门禁；
- Harness 阈值与 fallback 只能来自该 Manifest；
- run store 必须使用同一个已规范化 run ID。

随后用一个单次绑定的 Adapter 调用：

```text
SkillAgentDraftPreparer.prepare(execution, context)
                    │
                    ├── DraftPreparationResult → ReviewHarness
                    └── AgentRunResult          → 外层结果保留
```

Agent preparation 失败会变成稳定的 `agent_draft_preparation_failed`，交给 Harness 按
Manifest 决定 deterministic fallback 或 rejected。外层不能把失败的 Agent 草稿直接
包装成 Skill Output。

## 8. 唯一控制流

```text
ValidatedSkillExecution + ContextBundle
                  │ identity check
                  ▼
       bound Agent DraftPreparationStep
                  │
                  ▼
            ReviewHarness.run
                  │
        write two input Artifacts
                  │
        prepare draft + knowledge
                  │
 write Evidence → validate citations → write Draft
                  │
      evaluate → revise? → re-evaluate
                  │
      publish / degrade / reject
                  │
                  ▼
 terminal Manifest + verified Artifacts
                  │
                  ▼
      SkillTerminalOutputBuilder
                  │
                  ▼
 LoadedSkill.output_model.model_validate(...)
```

无论旧路径还是 Agent 路径，`ReviewHarness.run()` 都只有这一份状态迁移和发布实现。

## 9. Typed terminal output 的事实来源

输出字段不能从模型最后一条消息拼装：

| 输出字段 | 唯一事实来源 |
|---|---|
| `run_id` | terminal Manifest，并与 execution/store 核对 |
| `status` | terminal Manifest status |
| `report` | 完整性校验后的 FINAL_REPORT Artifact |
| `evaluation_score` | 与 `manifest.attempt_id` 对应的最终 EVALUATION_RESULT Artifact |
| `evidence_source_ids` | 完整性校验后的 RETRIEVAL_EVIDENCE Artifact |
| `warnings` | terminal decision 与经过净化的 terminal reason |
| `target_match_id` | 已验证的 SingleMatchReviewInput |

最终 payload 必须交给 `LoadedSkill.output_model.model_validate()`。如果 Manifest、Artifact
或 Output Model 任一不一致，组合层 fail closed，不返回半成品 dict。

## 10. Artifact 完整性与输入承诺

5D-1 的 `SkillInputArtifactBinding` 已计算两份输入的 kind、schema version 和 SHA-256。
5D-5 在 Harness 完成后重新读取实际记录和字节，并逐项核验：

```text
run_id + kind + schema_version + sha256 + physical bytes
```

`FileRunStore.read_artifact()` 先检查物理文件的实际摘要，再与 5D-1 承诺比较。这样 typed
output 不只是相信“调用时传入了同一个 Python dict”，而是证明 Harness 真正落盘的
输入就是 ExecutionBoundary 承诺的内容。

## 11. 最终评测分数语义

Harness 修订时会存在 attempt 0 和 attempt 1 两份评测。输出只读取：

```text
evaluations/evaluation_attempt_{manifest.attempt_id}.json
```

因此：

- 首次通过：返回 attempt 0 分数；
- 修订后通过：返回 attempt 1 分数；
- 有合法失败评测后降级/拒绝：返回最后一次合法落盘分数；
- preparation 或 evaluator 在写出合法评测前失败：返回 `None`。

分数描述“最后一次已完成评测”，不代表 degraded 报告自身获得了该分数。状态字段仍是
最终发布结论。

## 12. 报告与 warning 语义

- `published`：FINAL_REPORT 是通过质量门禁的草稿或修订稿，warnings 为空；
- `degraded`：FINAL_REPORT 必须与确定性报告 Artifact 一致，warnings 包含
  `deterministic_fallback` 和稳定失败原因；
- `rejected`：不得存在或暴露 FINAL_REPORT，`report=None`，warnings 包含
  `report_rejected` 和稳定失败原因。

异常类名、Provider 原文、用户内容和知识正文不进入 warnings。失败原因只保留类似
`agent_draft_preparation_failed`、`evaluation_failed`、
`revision_budget_exhausted` 的代码。

## 13. 质量配置边界

映射规则固定为：

```text
publish_score_threshold     ← manifest.quality_gate.minimum_score
allow_deterministic_fallback ← manifest.quality_gate.allow_deterministic_fallback
max_revisions                ← 既有 Harness 有界默认值 1
```

Manifest 当前没有 `max_revisions`，本轮不凭空扩展 Schema。调用方也不提供阈值或
fallback 覆盖参数，避免低权限调用绕过 Skill 的发布规则。

## 14. 测试如何证明

1. 旧 Harness 全套通过顺序 Adapter 保持发布、修订、降级和拒绝语义；
2. Agent 草稿必须先进入 Evaluator，不能直接成为 FINAL_REPORT；
3. 修订后发布时 Output 报告来自 FINAL_REPORT，分数来自 attempt 1；
4. Agent preparation/evaluation 失败只能 deterministic degraded；
5. Manifest 禁止 fallback 时 rejected 且 `report=None`；
6. evidence source IDs 只来自实际落盘 Evidence；
7. 两份输入 Artifact 的 schema/SHA/字节与 5D-1 commitment 一致；
8. Manifest minimum score/fallback 映射不可由调用方覆盖；
9. run/Skill/version/context/target match 漂移在执行前失败；
10. Output Model 或 terminal Artifact 损坏时不返回 typed output；
11. 两个真实 Skill 都走 Catalog、Router、Boundary、ContextBuilder、Fake Provider、真实
    `knowledge.search`、AgentLoop 与同一 ReviewHarness；
12. 不发起真实 Provider 请求，不产生 5D-6a 结构化输出实现。

## 15. 当前限制与准确表述

完成后可以说：

> RiftCoach 已把受限 Skill Agent 生成的草稿及真实工具证据接入唯一质量门控
> ReviewHarness；terminal Skill Output 只由终态 Manifest 和完整性校验通过的最终
> Artifact 构造，并由 Skill 声明的 Pydantic Output Model 再验证。

不能说已经：

- 完成真实模型 Tool Calling；
- 让 Provider 原生返回结构化 Skill Output；
- 完成 Prompt E2E 质量评测；
- 完成 AgentRuntime、持久化 Trace、Session 恢复或 Web 部署；
- 采用 LangGraph、Pi/Claude Agent SDK 或 Multi-Agent。

## 16. 面试时怎么解释

可以先讲取舍：Agent 负责动态选择知识工具和提出草稿，确定性 Harness 负责状态、评测、
修订次数和发布权。再讲证据：最终 API 对象不是从模型文本直接反序列化，而是从带 SHA
的 Artifact 重建。最后讲兼容：旧 Retriever/Generator 通过 Adapter 使用同一草稿准备
协议，所以没有维护两套质量流水线。
