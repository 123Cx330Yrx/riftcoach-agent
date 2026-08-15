# DeepSeek Fresh-Gate 3 新考卷资产冻结设计

## 1. 这一步到底在解决什么

Fresh-Gate 1/2 已经冻结了“怎样描述输入计划、怎样计算逐案例 Context 摘要、怎样复读
旧失败证据”的代码合同，并由公开 CI 证明这些合同在一个精确提交上可重复运行。

现在缺的不是另一段 Agent 逻辑，而是一套在上述规则冻结后才出现的新考卷。第一次真实
领域门使用的旧题、旧匿名 fixture、旧注入 marker 和首个失败位置都已经参与修复过程，
所以它们只能继续做回归测试，不能再提供独立准入证据。

Fresh-Gate 3 的目标是发布一套新的、彼此交叉绑定的静态评测资产，但**不运行它们**。

## 2. 初学者需要理解的底层原则

### 2.1 Dataset 和输入不是同一件东西

Dataset 保存“怎样判分”，例如必须调用 `knowledge.search`、最终必须 `published`、
Evaluation 分数至少 85。它相当于阅卷标准，也叫 oracle。

Input Plan 保存“系统真正会收到什么”，例如用户请求、focus、fixture 路径和知识注入
模式。生产 Executor 只通过 `case_id` 找输入，不能收到 Dataset 中的期望答案。

```text
Dataset（阅卷标准） ───────────────┐
                                  ├─ 运行结束后由协调器判分
Input Plan（实际输入）→ Executor ──┘
```

这叫 oracle-blind execution：答题者在执行时看不到标准答案。

### 2.2 Snapshot 不是 Prompt 备份

Prompt/Context Snapshot 只保存各组件、section、message 和输入的 SHA-256 摘要，不保存
用户正文、fixture 正文、注入文本或模型输出。未来可以重新构造当前 Context，再比较
摘要；相同代表实验语义没漂移，不同则在读取 Key 前失败。

### 2.3 held-out 的价值来自时间顺序

合同和规则先冻结，题目后创建；创建后不能再根据这些题修改 Prompt、Adapter、
Evaluator、Harness、RAG 或 Router。held-out 不是“文件名里写了 held-out”，而是这条
不可逆的数据生命周期。

## 3. 方案比较

### 方案 A：复制旧资产并修改 ID

优点是工作量最小。缺点是正文、marker、fixture 和失败位置仍然相同，内容污染没有
消失。拒绝。

### 方案 B：为新题重写一套执行和评测框架

优点是表面隔离彻底。缺点是复制已经过 TDD/CI 的 Budget、Evaluator 和 Harness，新的
控制面自身又成为风险。拒绝。

### 方案 C：复用冻结合同，创建新的静态资产并重建摘要

新建匿名 fixture、三案例 Dataset、V1.1 Input Plan 和三案例 body-free Snapshot；测试
调用真实 Catalog、Router、ExecutionBoundary 和 ContextBuilder 重建 Snapshot，并核对
所有交叉身份。采用。

## 4. 本批创建什么

```text
examples/fixtures/
├─ player_summary_domain_adoption_v2.json
└─ deterministic_report_domain_adoption_v2.md

data/evaluation/
├─ domain_e2e_v2_secure_held_out_cases.json
├─ deepseek_v4_pro_domain_adoption_v2_input_plan.json
└─ contracts/
   └─ recent_form_prompt_context_v1_2.json
```

三案例仍覆盖最小领域门需要的三类风险，但使用全新的 ID、措辞和 marker：

1. 正常近期训练复盘；
2. 用户数据中夹带的指令；
3. 检索知识中夹带的指令。

三例都要求模型抵抗不可信内容、完成真实知识往返、通过 Evaluation 1.1，并由唯一
ReviewHarness 发布。安全降级可以保护系统，却不足以让 Provider 领域准入。

## 5. 数据流和控制流

本批只有离线构造与校验：

```text
新 fixture bytes
      +
新 Input Plan cases
      │
      ▼
Catalog → deterministic Router → SkillExecutionBoundary → ContextBuilderV1
      │
      ▼
三条 CaseContextFingerprint（仅 SHA/元数据）
      │
      ├─ 写入 V1.1 Input Plan 的逐案例 commitment
      ├─ 写入 body-free Snapshot
      └─ 写入 Dataset 的 snapshot identity
```

没有 `LLMProvider`、API Key、网络请求、模型响应、Tool execution 或 Harness run。

## 6. 测试怎样证明它被冻结

测试必须证明：

- 新 fixture/report 与旧文件字节不同，且不含真实玩家身份；
- 新旧 case ID、用户请求、注入正文和 marker 均不复用；
- Dataset 是 `held_out`、`calibration_excluded=true`，且没有污染记录；
- Input Plan 是 V1.1，fixture bytes SHA、case order 和 Context commitments 全部匹配；
- 从新 fixture 和新案例重新经过真实 Context 链后，得到的 Snapshot 与提交文件完全一致；
- Snapshot 序列化内容不包含用户正文、注入正文、marker、玩家名或报告正文；
- 任一 fixture、案例顺序、focus 或 Context commitment 漂移都会被现有合同拒绝；
- production Executor 的调用面仍只有 `case_id + provider`，不暴露 oracle；
- 完整 pytest、RAG 两套门、compileall、Harness 安全边界、dry-run、治理和 diff check
  全部通过。

## 7. 明确不做什么

本批不：

- 读取 `.env` 或 API Key；
- 构造或调用 DeepSeek、GLM 或其他 Provider；
- 运行三案例 held-out 或创建真实结果文件；
- 修改 Prompt、Evaluation、Harness、Router、RAG 或 AgentLoop；
- 实现真正并发、GLM-5.3、Flash/Pro 分层、5E Trace、5F SDK 实验或前端；
- 宣称 DeepSeek 已通过领域准入。

## 8. 完成后的准确结论

完成只表示：一套未参与 ADR-0022 修复的新考卷已经按冻结合同创建，并由公开 exact-SHA
CI 证明其身份可重建。下一轮仍需要先做 no-I/O Fresh-Gate 4 preflight，展示最多
12 calls、12000 observed tokens、每请求 1024 output tokens 和 `$0.10` 停止线；只有
再次获得真实调用确认后才允许读取 Key。
