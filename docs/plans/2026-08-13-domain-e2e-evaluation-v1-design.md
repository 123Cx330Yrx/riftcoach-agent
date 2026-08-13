# 5D-7 Domain E2E Evaluation V1 设计

## 1. 具体问题

5D-6b 已证明生产 `ZhipuProvider` 可以完成最小结构化输出和一次工具往返，但同一个
Provider 在真实 `recent-form-review` 中没有形成可交给 Agent 的统一响应。Harness 安全
降级了，公开结果却只能写成 `knowledge_round_trip_incomplete`。

如果现在直接改 Prompt 或换模型，我们无法回答三个基本问题：

1. 是 Provider 响应没有规范化，还是 Agent 没有选择工具？
2. 是工具没执行，还是执行后没有形成可归因证据？
3. 最终报告没发布，是事实审查失败，还是质量门禁按设计拒绝？

因此 5D-7 的第一步不是“把这一次调绿”，而是先建立稳定、可复现的评测合同。

## 2. 底层原理：评测的是控制系统，不只是一段文字

RiftCoach 的 Agent 路径是一个受约束控制系统：

```text
Provider / Agent
  -> Tool selection and execution
  -> attributable Evidence
  -> fact/citation Evaluation
  -> Harness terminal decision
```

最终文本相同，不代表控制路径相同。例如，模型可以猜出一条看似正确的建议，但如果
没有执行 `knowledge.search`，它就没有可审计的知识来源。反过来，依赖故障导致
`degraded` 并不一定是系统错误；如果场景预期安全降级，这个终态反而是正确行为。

所以每个评测案例必须同时声明：

- 应该出现的 Agent 终止方式；
- 必须调用和成功执行的工具；
- 最少需要多少可归因来源；
- 是否必须完成事实、引用和注入检查；
- 允许的最终终态；
- Provider 调用、延迟、Token 和成本上限。

评测结果必须把“任务能力是否成功”和“评测器是否正确识别失败”分开。离线开发基线
可以包含故意构造的失败观测；分类准确率高只证明评测器能识别这些已知失败，不能证明
真实模型质量高。

## 3. 方案比较

### 方案 A：复用 5D-6b 单一案例并调整 Prompt

优点是快。缺点是同一案例同时用于发现问题、调参和验收，结果必然被污染；一次成功
也无法证明工具、证据和质量门禁在其他表达下有效。拒绝。

### 方案 B：只让 Judge 给最终报告打分

实现简单，但无法区分 Provider、Agent、Tool、Evidence 和 Harness 失败。Judge 本身
还是模型，可能把流畅文本误判为可信事实。拒绝作为唯一评测。

### 方案 C：分层领域评测 + development/held-out 生命周期

每条案例冻结控制路径、事实/引用要求、终态和资源边界；候选运行只提交脱敏结构化
观测。开发集用于修正评测器，保留集在规则冻结后单次运行。采用。

## 4. V1 合同

### 4.1 Dataset

Dataset 保存案例的不可变期望：

```text
identity and lifecycle
  dataset_id / version / role / calibration_excluded / created_at

candidate contract snapshot
  Skill name/version
  Context Builder contract
  structured Evaluation contract

case expectations
  Agent -> Tool -> Evidence -> Evaluation -> Terminal -> Resources
```

`development` 允许用于开发评测器，必须记录污染来源。`held_out` 必须
`calibration_excluded=true`，且不能包含参与开发的来源；运行时还需要显式确认评测规则
已经冻结。当前入口批次只建立 development，不创建或运行 holdout。

### 4.2 Candidate Observation

候选观测只允许保存机器可检查的安全字段：

- Provider 调用数、规范化响应数和安全错误码；
- Agent status、stop reason；
- 提议工具名、成功工具名；
- 去重后的 evidence source IDs；
- fact/citation/injection check 的三态结果；
- Evaluation 是否验证、分数；
- terminal status 和安全 reason；
- latency、Token、cost 的可空数值。

不保存 Prompt、模型正文、思维链、工具 Observation 原文、原始 request ID、异常正文或
API Key。`null` 表示“没有可靠观测”，绝不能解释成 0、false 或免费。

### 4.3 Layer Result 与失败分类

每层输出四态 verdict：

- `pass`：所有该层要求都被观测满足；
- `fail`：已有观测明确违反要求；
- `unknown`：该层有要求，但前置失败或字段缺失，不能判断；
- `not_applicable`：案例明确不要求该层。

失败码是稳定白名单，例如：

```text
provider_response_unavailable
agent_not_completed
tool_selection_missing
tool_execution_incomplete
evidence_missing
fact_check_failed
citation_check_failed
injection_resistance_failed
evaluation_unavailable
quality_gate_failed
terminal_status_mismatch
resource_limit_exceeded
unsafe_publication
```

结果可以保留多个失败码，同时按数据流从前到后选一个 `primary_failure`。这样不会把
后果误当根因，也不会因为只显示一个原因而丢掉发布安全问题。

## 5. 数据流与控制流

```text
versioned Dataset JSON -----> strict loader -----+
                                                |
recorded Candidate JSON ----> strict loader -----+--> layered evaluator
                                                          |
                                                          +-> per-layer verdicts
                                                          +-> safe failure codes
                                                          +-> task success
                                                          +-> classification match
                                                          +-> aggregate baseline
```

Loader 先检查 dataset/candidate identity、案例数量、Skill/Context/Evaluation 快照以及
重复 ID。Evaluator 不调用 Provider、Tool、RAG 或 Judge，只比较冻结期望与结构化
观测。CLI 在加载 held-out 时必须显式声明规则冻结，并在合同错误时不写结果。

## 6. 本入口批次实现与不实现

实现：

- 严格 Pydantic Dataset、Candidate 和 Result 模型；
- development/held-out 生命周期门禁；
- 分层 verdict、稳定失败分类和资源 `null` 语义；
- 一组离线 development 案例和候选观测，覆盖资源 unknown 与明确超限；
- 把 5D-6b 真实脱敏失败作为 development Bad Case；
- 离线基线和 CLI 合同测试。

不实现：

- 不修改 Agent/Skill/Harness 生产控制流；
- 不修改 Prompt 或 Context Builder；
- 不调用真实 Provider，不接 DeepSeek/Qwen；
- 不让 Judge 生成新的标签；
- 不创建或运行 held-out；
- 不实现 5E 的统一 Trace；
- 不进入 5D exit review。

## 7. 测试如何证明行为

1. Schema 测试拒绝重复 case ID、角色错误、污染的 holdout 和快照漂移。
2. 分类测试分别制造 Provider 无响应、缺工具、工具失败、缺证据、坏引用、注入失败、
   质量门禁和不安全发布，检查稳定失败码和优先级。
3. 三态测试确认没有观测的 latency/token/cost 保持 `null`，不会被算作 0。
4. CLI 负例确认 development 模式不能读取 held-out，且失败前不写结果。
5. 保存基线复读测试确认结果与 Dataset/Candidate 身份和逐案例 oracle 对齐。

这些测试只能证明评测基础设施能处理已知离线观测。它们不能证明真实 Provider 能完成
领域任务，也不能证明 Prompt 已经抵御未知注入。

## 8. 5D-7 内部实施批次

以下只是现有 `5D-7` 内部批次标签，不是新增或改名用户已批准的子阶段：

1. Batch A：本设计、数据合同、失败分类和离线 development 基线；
2. Batch B：Prompt/Context 版本身份与可重复实验入口；
3. Batch C：多案例工具、事实、引用和模型级注入评测；
4. Batch D：冻结规则后的 holdout、有限真实运行及第二 Provider 决策输入；
5. 5D-7 review：核对证据后决定能否进入 5D exit review。

后续批次可以深化前一批合同，但不能用一份新 Prompt 或一个新模型推翻 Dataset
生命周期、确定性事实真相源和 ReviewHarness 唯一发布权。

## 9. 非功能要求与安全边界

- **可复现性**：相同 Dataset 和 Candidate 字节产生相同逐案例结论。
- **可维护性**：失败分类是稳定枚举，不依赖异常字符串匹配。
- **安全性**：公开结果只保存白名单字段；不可信文本不进入评测控制指令。
- **成本**：入口批次外部调用为 0；未知单价时 cost 保持 `null`。
- **性能**：离线评测是小型确定性批处理，不引入数据库或分布式基础设施。
- **故障隔离**：某一案例合同错误使整个候选评测 fail closed，不生成部分正式基线。

## 10. 面试安全表述

> 我没有只对最终文案做 LLM-as-Judge，而是把领域 Agent 的 Provider、工具执行、证据、
> 事实/引用审查和 Harness 终态拆成分层评测。开发集与保留集有独立生命周期，未知
> Token、延迟和成本保持 null；5D-6b 的真实失败作为开发 Bad Case 保留，用来验证安全
> 失败归因，而不是反向调 Prompt 追求一次通过。
