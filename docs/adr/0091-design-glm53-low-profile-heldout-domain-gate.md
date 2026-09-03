# ADR-0091：设计 GLM-5.3 Flash 低思考候选独立领域门

- 日期：2026-09-03
- 状态：`protocol-assets-implemented-local / candidate-only / pending-public-ci`
- 范围：Stage 8 / 8E；RQ-222

## 背景

RQ-221 已在冻结、无工具上下文中用 `thinking=enabled`、`reasoning_effort=low`、
`clear_thinking=false` 和 4096 输出完成一次真实响应观察。它只回答了“这一类短请求能否
完成”，没有回答模型能否在 RiftCoach 的 Skill、知识检索、评测和发布链里稳定完成领域任务。
旧 GLM-5.3 G53-4/G53-7 考卷已经被看过，旧失败位置也参与过修复，因此不能换一个 profile
后原地重跑来冒充独立证据。

现有 `ProductionDomainCaseExecutor` 和多个运行时构造器还把 `ModelRuntimeProfile` 限定为
已登记的产品档案。直接登记低思考档会提前改变产品接线；直接复制整套执行器又会产生第二套
未经证明的控制面。

## 决策

采用一个版本化、仅评测可用的低思考领域门：

1. 新建独立的 `CandidateEvaluationProfile`/绑定作用域。它携带 RQ-221 的 provider、模型、
   thinking、采样、4096 输出和 90 秒 Agent/LLM 工具窗、120 秒传输窗，但只能由评测入口
   通过私有能力令牌构造。正常 `resolve_model_runtime_profile()`、产品 Runtime、Worker 和
   默认模型解析器继续拒绝它。
2. 把共享执行链抽象成“请求策略”接缝：Agent 编译、`llm.chat`、候选预算包装器和现有
   `ProductionDomainCaseExecutor` 共同消费该显式评测策略；不削弱全局的已登记档案校验。
   评测策略在最后一层强制覆盖 profile、4096、采样、超时和无重试，模型输出不能升权。
3. 为低思考领域门创建全新的匿名三案例 Dataset/Input Plan/Prompt-Context Snapshot，使用
   新 fixture、case ID 和注入 marker。Dataset 为 `held_out` 且 `calibration_excluded=true`；
   执行器只通过 `case_id + provider` 看到输入，阅卷 oracle 仍留在协调器外。
4. 先在同一新实现上取得独立的低思考 G53-3 协议回执（最多 3 次：结构化、工具往返、终态/
   Usage），再冻结新考卷并做 no-I/O admission，最后才在另一次明确授权下运行领域门。
5. 领域门固定每案例最多 4 次、总计最多 12 次、无 retry/recovery/revision、首个不安全失败
   停止；每次请求最多 4096 输出、Agent/LLM 工具 90 秒、传输 120 秒。候选实验的总 token
   上限暂定为每案例 24,000、全域 72,000；这是 fail-closed 的实验资源墙，不是产品承诺，
   必须在离线实现中由冻结 Context 重新计算并写入身份。
6. 领域质量仍要求真实 Agent 完成、`knowledge.search`、Evidence、事实/引用/注入检查、
   独立 Evaluation 达到 85 且由 Harness 发布；评测作用域关闭确定性回退，避免用 fallback
   掩盖低思考档的失败。所有正文、reasoning、Prompt、Key、工具参数和完整 request ID 均不
   进入公共回执。

## 方案比较

### 方案 A：旧考卷换档重跑

拒绝。题目、fixture、注入 marker 和首个失败位置已经被消费，无法再提供 held-out 泛化证据。

### 方案 B：把低思考档注册为产品档案

拒绝。一次窄探针不能授权全局 Runtime；这会让候选实验和生产默认值混在一起。

### 方案 C：显式评测作用域 + 新鲜考卷（采用）

复用已经验证的 Agent/RAG/Evaluation/Harness 控制面，只增加最小的请求策略接缝；候选可以
使用更合适的预算，产品注册表仍保持封闭，证据身份也能独立追踪。

## 数据与控制流

```text
新 fixture / 新 Input Plan / 新 held-out Dataset
                 │
                 ▼
      ContextBuilder → case commitments（只保存 SHA）
                 │
                 ▼
      low-profile evaluation admission（仍为 0 次调用）
                 │
                 ├─ 低思考 G53-3-L 协议回执
                 └─ 一次明确授权的 3 案例领域运行
                              │
                              ▼
          现有 AgentLoop + knowledge.search + Evaluation + Harness
                              │
                              ▼
                 body-free、create-only 领域回执
```

## 非目标与停止线

本 ADR 不修改 Portal、Account、Workbench、Auth、路由、生产默认模型或 `production_media`，
不打开 `capabilities.streaming`，不重写任何旧 GLM-5.2/GLM-5.3 回执，也不把领域门结果直接
当作黄金切片、公共生产成熟度或 8F 完成。任一身份、预算、终态、Usage、工具或安全检查失败，
都保留不可变失败回执并停止；没有新的明确决定前不自动发真实请求。

## RQ-225 实现更新

RQ-225 已按本 ADR 完成显式 `request_policy` 协议接缝、最多 3 次的低思考 G53-3-L
离线组合器，以及全新三案例 held-out 资产的 no-I/O 准入。新增 Dataset、V1.1 Input Plan、
Prompt/Context Snapshot 和合成 fixture 均通过身份、case/marker 隔离与上下文 commitment
交叉校验；聚焦协议/资产回归 `20 passed`，provider calls=0。实现细节见
[RQ-225 实施计划](../plans/2026-09-04-glm53-low-profile-protocol-and-assets-offline-implementation.md)
和[学习 walkthrough](../learning/8e-glm53-low-profile-protocol-and-assets-offline-implementation-walkthrough.md)。

本批仍不读取 Key、不发真实请求、不注册候选、不改变产品 Runtime、默认模型、Portal、
Account、Workbench、Auth、路由或 `production_media=0`。当前精确检查点为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-local / pending-public-ci`；
同一实现 SHA 的公共 exact-SHA CI 是下一闸门，绿灯后仍需另一次明确授权才可执行真实协议门。
