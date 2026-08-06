# ADR-0009：事实审查保留为 Harness Evaluator，而不是新增 Skill

## 状态

已接受

## 背景

阶段 5 最初把近期状态复盘、单局复盘和报告事实审查都列为首批 Skill 候选。
前两个能力对应用户主动提出的任务；事实审查则发生在报告草稿产生以后，其合法
调用依赖确定性事实、草稿和当前 Harness 运行状态。

在决定是否为事实审查增加内部 Skill 前，必须先回答一个更基础的问题：项目是否
已经存在同一能力，以及新的 Skill 合同能否增加独立价值。

源码审计确认现有链路已经完整承担事实审查职责：

- `EvaluatorStep` 定义 `EvaluationRequest -> EvaluationResult` 类型化端口；
- `ChatEvaluationAdapter` 复用事实包、评测 Prompt、一次 `llm.chat` 和响应解析；
- `ReviewHarness` 在每份草稿和修订稿后强制调用 Evaluator，保存评测 Artifact，
  并根据阈值、修订预算和失败策略发布、降级或拒绝；
- `scripts/evaluate_coach_report.py` 也复用同一 Adapter，证明它已经可以脱离完整
  Harness 单独运行；
- Harness 测试覆盖首次评测、修订后复评、非法结果、异常降级和禁止发布。

因此，新增 `report-fact-check` Skill 不会产生第二种业务工作流。它只会把现有
Evaluator 再包装一层，并引出重复输入输出模型、重复 Prompt/Parser，以及“事实
审查 Skill 的输出是否还要再经过质量门禁”的递归语义。

## 决策

首批真正的 Skill 只保留两个：

| Skill | 调用方式 | 业务职责 |
|---|---|---|
| `recent-form-review` | 用户文本 Router | 复盘多场近期对局 |
| `single-match-review` | 用户文本 Router | 深度复盘一场指定对局 |

报告事实审查继续作为版本化 Harness Evaluation Policy / `EvaluatorStep`，不是
Skill，也不进入用户 Router。

这四层职责保持分离：

```text
Skill                 定义用户任务、输入、工具、预算和产出
Skill Router          只选择用户想执行哪个 Skill
EvaluatorStep         检查草稿并返回结构化评测结果
ReviewHarness         决定评测、修订、复评、发布、降级或拒绝的控制流
```

阶段 5C 不增加 `user_routable/internal` 调用模式合同，因为当前没有真实内部 Skill
消费者。下一步直接建立第二个真实用户 Skill `single-match-review`，随后用两个
真实候选完成 5C-5 Router Evaluation。

若以后出现真实独立需求，例如审查用户上传的任意外部报告、需要多工具交叉核验
引用、或需要独立循环和专属权限预算，再以 Bad Case、I/O、权限、复用消费者和
评测证据重新裁决是否增加内部审查 Skill。

## 影响

### 正面

- 不为维持“三个 Skill”这个数字复制已有能力；
- Harness 仍然强制事实审查，质量门禁没有被删除或弱化；
- Router 只包含真实用户任务，路由评测不会混入内部控制步骤；
- 保留清晰的 Skill、Evaluator 和 Harness 边界，面试时可以准确解释；
- 避免在没有消费者时扩展 Manifest Schema 和 Catalog 语义。

### 负面

- 首批 Skill 数量从历史提案的三个修正为两个；
- 未来若出现真实内部 Skill，届时仍需单独设计调用来源和 Manifest 演进；
- 现有事实审查目前主要核对确定性事实和推断边界，尚不能声称已完整验证每条
  RAG 引用的语义支持关系。

### 中性

- 事实审查仍然使用模型，但“使用模型的内部步骤”不自动等于 Skill 或 Agent；
- 这不是 Multi-Agent，Evaluator 只是由同一 Harness 调用的独立质量端口；
- 独立评测 CLI 继续保留，它是 Evaluator 的另一个调用入口，不是另一个实现。

## 失败与安全边界

- 任何 Coach 草稿仍必须经过 `EvaluatorStep` 和代码阈值才能发布；
- Evaluator 异常、非法输出或复评不通过时，继续按现有策略降级或拒绝；
- Router 不负责也不能绕过事实审查；
- 未来不得复制第二套事实包、评测 Prompt、Parser 或发布门禁来伪装新 Skill；
- 当前 `EvaluationRequest` 虽携带 `KnowledgeEvidence`，但评测 Prompt 尚未消费该
  证据；在补充引用支持评测前，不得声称已完成 RAG 忠实度全量审查。

## 备选方案

### 三个能力全部作为用户可路由 Skill

事实审查缺少由用户文本提供的合法前置状态，并会制造无业务意义的第三种意图，
因此拒绝。

### 把事实审查包装成 `internal` Skill

调用边界比全部用户路由正确，但现阶段仍与 `EvaluatorStep` 重复。它没有独立
循环、分支、工具集合或运行预算，复用也已由注入式 Evaluator 端口提供，因此
暂不采用。

### 保留现有 Harness Evaluator

直接复用已实现和已测试的端口、Adapter、Prompt/Parser 与发布控制，改动最小且
职责清晰，因此采用。

## 参考

- `app/harness/steps.py`
- `app/harness/adapters.py`
- `app/harness/runtime.py`
- `app/evaluation/coach_report.py`
- `scripts/evaluate_coach_report.py`
- `tests/test_harness_runtime.py`
- `tests/test_harness_adapters.py`
- `docs/adr/0003-quality-gated-agent-harness.md`
