# 5C-5 前置复核：事实审查属于 Skill 还是 Harness

## 1. 本轮解决的问题

本轮不实现 Skill，也不运行模型。它只回答：`report-fact-check` 是否真的应该成为
第三个 Skill，还是已经由 Harness 的事实评测组件完整承担。

这个问题必须在写调用模式合同前解决。否则项目会先为了一个假设中的内部 Skill
扩展 Manifest，再发现它与已有 Evaluator 重复。

## 2. 四个概念的区别

### Skill

Skill 是一个用户或系统可以复用的完整任务合同，通常需要独立目标、输入输出、
工具权限、预算、步骤和成功标准。

### Skill Router

Router 只根据用户表达选择要执行哪个用户任务。它不生成报告，也不负责内部质量
控制。

### EvaluatorStep

EvaluatorStep 接收已经生成的报告和证据，返回结构化评分、结论和问题。它是
Harness 可替换、可测试的质量端口。

### ReviewHarness

Harness 掌握控制流：什么时候评测、是否修订、最多修订几次，以及最终发布、
降级还是拒绝。模型不能自行决定发布。

## 3. 真实代码数据流

```text
player_summary + deterministic_report
                │
                ▼
          ReviewHarness
                │
        RAG → 生成 CoachDraft
                │
                ▼
     EvaluatorStep.evaluate(request)
                │
                ▼
        EvaluationResult
         ├─ pass 且达到阈值 → publish
         ├─ needs_revision → revise → re-evaluate
         └─ fail / 异常 / 超预算 → degrade 或 reject
```

代码映射：

| 职责 | 当前权威实现 |
|---|---|
| 评测输入输出与端口 | `app/harness/steps.py` |
| 模型调用适配 | `app/harness/adapters.py` |
| 事实包、Prompt、Parser | `app/evaluation/coach_report.py` |
| 调用时机、修订和发布 | `app/harness/runtime.py` |
| 独立复用入口 | `scripts/evaluate_coach_report.py` |
| 控制流和失败证据 | `tests/test_harness_runtime.py` |

## 4. 三个方案比较

| 方案 | 能否工作 | 主要代价 | 裁决 |
|---|---|---|---|
| 三个能力都进入用户 Router | 不能正确表达强制后置评测 | 把质量步骤伪装成用户意图 | 拒绝 |
| 事实审查作为内部 Skill | 可以实现 | 与现有 Evaluator 重复，扩展 Manifest 但没有新增能力 | 暂不采用 |
| 两个用户 Skill + Harness Evaluator | 已经有真实实现和测试 | 未来有真实内部 Skill 时再设计调用模式 | 采用 |

## 5. 为什么这不是削弱项目

分类改变不等于删掉能力。事实审查仍然是所有 Coach 报告的强制发布门禁，而且其
地位比一个可选 Skill 更强：用户 Router 无法绕过它，模型也不能自行跳过它。

项目的技术亮点来自职责清晰和可验证控制，不来自 Skill 数量。准确表述是：

> 两个领域 Skill 负责近期复盘和单局复盘；独立 Evaluator 负责事实忠实度与推断
> 边界；确定性 Harness 负责修订预算和发布裁决。

## 6. 已发现但本轮不修的缺口

`EvaluationRequest` 已携带 `KnowledgeEvidence`，但当前 `ChatEvaluationAdapter`
构造 Prompt 时只使用事实包与报告。Runtime 会拒绝未知引用 ID，但尚未逐条判断
RAG 引用是否真正支持对应结论。

这是真实的 Evaluation 深化项，应在 5D/5E 的 Context、结构化输出、Prompt 版本
和 Trace 工作中补齐。它应增强现有 Evaluator，而不是复制一个事实审查 Skill。

## 7. 后续顺序

```text
5C-5-prep-1  Skill Invocation Contract（写代码前取消）

5C-5-prep-2  single-match-review
→ 第二个真实用户可路由 Skill

5C-5-prep-3  report-fact-check Skill（写代码前取消）

5C-5  Router Evaluation
→ 冻结旧单 Skill 开发基线
→ 建立两个真实 Skill 的新开发集与独立保留集

5C-6  Model Fallback Decision
→ 只依据真实 Bad Case 决定是否需要模型兜底
```

阶段 5D 才执行选中的 Skill，并继续复用现有 `EvaluatorStep`。本轮没有进入 5D。
