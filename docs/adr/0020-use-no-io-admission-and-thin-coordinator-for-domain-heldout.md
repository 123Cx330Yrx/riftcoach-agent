# ADR-0020：领域 held-out 采用 no-I/O admission 与薄协调器

## 状态

已接受；实现 ADR-0016/0018 已冻结的三案例真实领域门，不改变 Provider、模型、案例或
阶段范围

## 日期

2026-08-14

## 背景

DeepSeek V4 Pro 已通过最小 structured/tool Adapter 协议门，但三场领域 held-out 最多
还会产生 12 次真实调用。仓库已有分层 Domain Evaluator、development 脚本 runner、
实验预算和停止控制器，却没有一个组件同时保证：协议资源继续累计、每案例预算、逐例
首错停止、结果脱敏、Provider 前身份校验和不可重复输出。

直接复用 development runner 会把已知 `_Scenario`/canary 和脚本化模型答案带入
held-out；把所有逻辑写入一个真实 API CLI，则难以在不读取 Key/创建 Provider 的前提下
测试身份、预算和失败分支。

## 决策

采用三部分组合：

1. `prepare_deepseek_domain_heldout_run()` 作为 no-I/O 控制面。它不接收 Provider，先
   绑定代码/public CI、Dataset/Snapshot、已准入协议字节摘要和案例执行计划摘要；
2. `DomainCaseExecutor` 只运行一个案例并返回白名单语义观测，不上报 calls、Token、
   金额或延迟；真实 Executor 必须声明与 admission 相同的 execution-plan identity；
3. 薄协调器从协议 snapshot 继续累计账本，把受控 Provider 逐例交给 Executor，以账本
   差值构造 `DomainCandidateCase`，复用现有分层 Evaluator，并执行首错停止。

DeepSeek 预算维持 ADR-0018：protocol 3 calls/4000 tokens，domain 12 calls/12000
tokens，每案例 4 calls/4000 tokens，累计 15 calls/16000 tokens、每请求最多 1024
output tokens、金额停止线 `$0.10`。Provider/案例 mismatch 停止候选，unsafe
publication 触发全局停止。输出在 Provider 构造前独占创建；失败或崩溃留下哨兵，不能
静默重跑。公开记录不保存 Prompt、攻击/用户正文、模型/RAG/工具正文、request ID、异常、
Key 或玩家身份。

当前批次只用合成 Provider/Executor 验证控制面，不创建或运行真实 held-out 执行正文。
真实领域门必须在该接缝的 exact-SHA public CI 成功后单独进行。

## 影响

### 正面

- “先 preflight 后 Key”由类型和调用结构保证，不只靠脚本注释；
- 真实协议消耗不会在领域门中被重置，累计预算可审计；
- 开发 canary 与真实 held-out Executor 分离，减少 oracle 泄漏；
- 部分失败仍能保存安全记录，并明确哪些案例 skipped；
- 不增加框架、数据库、LangGraph、SDK Runtime 或第二套 Evaluator/Harness。

### 负面

- 资源账本和领域记录合同增加了 scope/case 维度；
- 真实领域门仍需冻结执行计划并实现生产案例 Executor/CLI；
- 进程级崩溃只能留下不可重复哨兵，不能提供阶段 8 才规划的快照恢复；
- 三案例结果仍是准入证据，不具有统计显著性。

## 备选方案

### 直接复用 `OfflineDomainExecutionRunner`

拒绝。它故意知道 development scenario/canary，并使用脚本 Provider；不能评价真实模型，
也没有继承协议资源的职责。

### 单个真实 API CLI 完成全部逻辑

拒绝。会把 Key/Provider 构造、执行、判分和存储耦合，使 pre-I/O 失败与部分结果难以离线
证明。

### 给 `ReviewHarness` 加实验预算和 held-out 逻辑

拒绝。Harness 是产品质量发布边界，不应依赖某个 Provider、评测 Dataset 或一次性实验
生命周期；实验协调留在 evaluation 层。

## 参考

- `docs/plans/2026-08-14-deepseek-domain-heldout-execution-seam-design.md`
- `docs/adr/0016-version-injection-evaluation-before-real-provider-comparison.md`
- `docs/adr/0018-select-deepseek-v4-pro-for-domain-admission.md`
- `app/evaluation/provider_domain_experiment.py`
