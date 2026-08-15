# DeepSeek Fresh-Gate 4 运行入口设计

## 1. 当前缺口

Fresh-Gate 3 已经公开冻结了新的匿名 fixture、三案例 held-out Dataset、V1.1 input
plan 和逐案例 Prompt/Context snapshot，但生产 CLI 仍绑定已经消费过的 V1.1.0 旧考卷。
只把 CLI 默认路径替换为新文件并不安全：旧 Adapter 协议结果携带旧 Context 身份，而
新领域采用门还必须显式保存旧失败、修复 CI、新资产 CI 和当前代码 CI 的连续证据。

Fresh-Gate 4 的入口批因此只解决“新考卷怎样安全到达现有生产执行链”，不运行真实
考卷。

## 2. 方案比较

### 方案 A：原地替换旧常量

实现最少，但会把旧实验入口改造成含义不同的新入口，也无法解释旧协议 Context 与新
领域 Context 的合法差异。拒绝。

### 方案 B：复制一套 V2 CLI 和协调器

文件隔离直观，但会复制 Key 顺序、预算、首错停止、Executor、Evaluator 和 Harness，
从而产生第二套需要重新证明的控制面。拒绝。

### 方案 C：版本化准入，复用一个生产执行器

保留旧结果和旧底层记录合同；增加 Fresh readmission evidence 和新结果 envelope，
把旧协议/失败、修复 CI、资产冻结 CI、当前代码/CI 与新输入身份串起来。现有 CLI 改为
面向当前 Fresh profile，并继续调用同一个预算 Provider、production Executor 与领域
协调器。采用。

## 3. 合同分层

```text
HistoricalDomainEvidence
├─ 旧 3-call 协议结果 bytes SHA
├─ 旧 1-call 领域拒绝结果 bytes SHA
└─ ADR-0022 修复 commit / public CI

FreshDomainAssetFreezeEvidence
├─ Fresh-Gate 3 asset commit / public CI
├─ Dataset / input plan / snapshot file bytes SHA
└─ summary / report fixture bytes SHA

ExperimentPreparationReport
├─ 当前 clean code SHA == public CI SHA
├─ 新 Dataset / Context identity
└─ 12-call / 12000-token / $0.10 等资源上限

FreshDomainHeldOutAdmission
├─ 上述三层证据
├─ 新逐案例 Context commitments
└─ 既有 DeepSeekDomainRunAdmission
```

最后一层中的既有 admission 继续供原领域协调器执行。Fresh admission 自身固定记录
`external_provider_calls=0`、`held_out_executed=false`，且单凭该对象不授权 Provider
构造；CLI 还必须看到显式真实调用确认。

## 4. CLI 控制流

```text
参数与输出冲突检查
        ↓
读取本地冻结资产并重建三个 Context 摘要
        ↓
核对历史 bytes、修复 CI、资产 CI、当前 clean SHA / public CI
        ↓
形成 FreshDomainHeldOutAdmission（仍为零调用）
        ├─ --prepare-only：在这里返回
        ↓
独占预留新结果路径
        ↓
加载 .env / Key
        ↓
构造 DeepSeekProvider
        ↓
现有 ProductionDomainCaseExecutor + bounded coordinator
        ↓
不可变 Fresh result envelope
```

`--prepare-only` 是本批公开 CI 可走的路径。它不能创建结果 sentinel、读取环境变量或
构造 Provider。未来真实运行会在同一入口中重复全部准入检查，然后才预留输出并加载
Key，避免“昨天预检通过、今天代码已变”的时间差。

## 5. 兼容与记录策略

- 旧 `ProviderDomainExperimentRecord@1.0` 和两个历史 JSON 保持原字节可读；
- 新增 Fresh result envelope，而不是改变旧结果字段语义；
- envelope 显式包含 Fresh admission 和原领域结果，因此同时保存证据链与原分层判决；
- 旧协议只证明 Provider/Adapter 协议能力，允许它的旧 Context 身份与新领域 Context
  不同；协议 result bytes SHA、模型、资源和准入状态仍必须完全匹配；
- production Executor 仍只接收 `case_id + provider`，Dataset oracle 不进入执行路径。

## 6. 失败与安全语义

- 任一历史文件、新资产、fixture、case order、Context、Skill、Evaluation、预算或 CI
  身份漂移：在环境/Provider 之前失败；
- 输出已存在：在预检和 Key 之前失败，禁止覆盖；
- `--prepare-only`：Provider/Key/结果文件三者都不可触达；
- 真实模式：结果路径先独占预留，再加载 Key；后续异常保留空 sentinel，阻止静默重跑；
- 领域协调器继续执行每例 4 calls、总计 12 calls、每例 4000 tokens、首错停止和
  unsafe-publication global stop；
- 公开模型只保存白名单状态、资源、摘要和 SHA，不保存 Prompt、用户/注入/RAG/模型
  正文、reasoning、request ID、原始异常或 Key。

## 7. 测试如何证明本批行为

1. 新资产及完整历史链形成稳定 no-I/O admission；函数签名不接 Provider/API Key。
2. asset CI、当前 CI、任一文件 bytes 或逐案例 Context 漂移均 fail closed。
3. `--prepare-only` 不调用 environment loader/provider factory，也不创建输出。
4. 输出冲突早于预检；真实模式的输出预留早于环境和 Provider。
5. Fake Provider 通过同一生产 Executor/RAG/Evaluation/Harness 生成新 envelope，证明装配
   可达，但明确不评价真实 DeepSeek 质量。
6. 首例失败跳过后两例、预算和 sanitizer 继续使用既有测试，并增加新 profile 回归。
7. 旧结果仍逐字节复读；新测试和公开 CI 的外部调用、held-out execution 均为 0。

## 8. 本批之后

公开 exact-SHA CI 成功后，Fresh-Gate 4 入口批才算完成。届时下一动作不是自动运行，
而是向用户重新展示 `deepseek-v4-pro`、最多 12 calls、12000 observed tokens、每请求
1024 output tokens、`$0.10` 停止线和首错停止，再取得一次明确真实调用确认。
