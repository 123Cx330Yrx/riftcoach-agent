# DeepSeek V4 Pro 三案例领域 held-out 执行接缝设计

## 1. 具体问题

DeepSeek V4 Pro 已经用一次真实、最多三调用的协议门证明：生产 Adapter 能完成严格
结构化输出和一次工具往返。但这仍然没有回答模型能否在 RiftCoach 的真实
`recent-form-review` Skill、RAG、AgentLoop、Evaluation 1.1 和 ReviewHarness 组合链中
正确工作。

下一门是三场冻结的领域 held-out。它最多产生 12 次新的计费请求，而且首次结果无论
好坏都不能删除、覆盖、调 Prompt 后重跑。因此在运行前必须补齐一个可离线证明的执行
接缝。当前已有 Provider 总预算、停止控制器、分层领域评测器和安全 Agent failure
observation，但还没有一个组件同时保证：

- 真实 I/O 前完成代码、公开 CI、Dataset、Prompt/Context 和协议证据核对；
- 继承已经消耗的 3-call/Token/金额协议账本，而不是重新从零计数；
- 三场依次运行，每场最多 4 calls / 4000 observed tokens，领域总计最多 12 calls /
  12000 observed tokens；
- 任一 Provider、案例结果或 unsafe publication 失败后，不再执行剩余案例；
- 公开结果不包含 Prompt、用户/攻击原文、RAG 文本、模型正文、Tool Observation、原始
  request ID、异常或 Key；
- 同一实验身份的结果不能被静默覆盖或当作一次“新实验”重跑。

本批只建造并离线验证这把“考试执行锁”。不读取 `.env`，不创建 DeepSeek 客户端，不
运行真实 held-out，不调整 Prompt，不比较 Flash/Qwen/GLM，也不进入 5D exit review、
5E、5F 或 Multi-Agent。

## 2. 初学者需要理解的底层原理

### 2.1 控制面和数据面必须分离

控制面回答“这次实验可不可以开始”，包括 SHA、CI、冻结身份、旧协议证据和预算。
数据面才真正把请求交给模型。若先加载 Key 或创建客户端，再做校验，就无法证明失败
发生在出网之前。

所以真实入口必须保持顺序：

```text
显式确认
  -> 输出位置和非重复检查
  -> exact SHA / public CI / Dataset / Snapshot no-I/O preflight
  -> 已准入协议结果及摘要校验
  -> 冻结案例执行计划摘要校验
  -> 才允许加载 Key 和创建 Provider
```

### 2.2 held-out 评测不能让执行器偷看答案

Dataset 保存判分合同，案例执行计划保存输入的身份摘要，生产执行器只负责运行相同的
Skill/Harness 链并返回安全观测。协调器不能按“预期通过/失败”伪造行为，也不能复用
development runner 中已经为已知 canary 写好的脚本化模型答案。

### 2.3 预算是 pre-I/O reservation，不是事后统计

如果第 13 个领域请求先发出，再发现超过上限，预算已经失效。账本必须先预留调用和本次
最大输出 Token，Provider 返回后再按规范化 usage 结算真实 Token、金额和延迟。SDK
报错也不退还已发出的调用；usage 缺失则停止，不能按 0 计算。

协议门已经消耗 3 calls、Token 和金额。领域门必须从该脱敏账本继续，而不是创建一份
“0/15”的新账本。否则累计 15-call / 16000-token / $0.10 停止线只是文档口号。

### 2.4 fail-closed 和 stop-on-first-failure

三案例按冻结顺序串行运行。每个案例结束后先形成 `DomainCandidateCase`，再由现有分层
Evaluator 检查 Provider/Agent、Tool、Evidence、Evaluation、Terminal 和 Resources。
出现下列任一情况立即停止：

- Provider/usage/预算错误；
- 案例安全观测不符合类型合同；
- task outcome 或 primary failure 与冻结 oracle 不符；
- 任何 unsafe publication。

最后一项触发全局停止；其他硬失败停止 DeepSeek 候选。已经发生的安全观测保留，剩余
案例明确标记 skipped，不以空值冒充已执行。

## 3. 方案比较

### 方案 A：直接复用 `OfflineDomainExecutionRunner`

该 runner 很适合 development，因为它用 `_Scenario`、脚本 Provider 和已知 canary
验证生产控制流。但这些脚本答案正是开发期 oracle。把它接到 held-out 会让执行器知道
考题答案，并且它不负责真实 Provider 累计预算。拒绝。

### 方案 B：写一个包含所有逻辑的真实 API CLI

单文件可以很快发请求，但会把预检、Key 加载、Provider 构造、Skill 运行、判分、预算
和持久化耦合在一起。测试很难证明失败发生在 Key/网络之前，也很难在不接真实 API 的
情况下覆盖首错停止和部分结果。拒绝。

### 方案 C：薄实验协调器 + 案例执行 Protocol + 现有评测/账本

协调器只拥有顺序、预算、停止、判分和脱敏记录；案例执行器拥有一次生产 Skill/Harness
运行；Provider 仍走统一 `LLMProvider`；判分继续复用 `evaluate_domain_candidate()`。
测试可注入 Fake Provider 和合成案例执行器，真实入口以后只负责按严格顺序装配依赖。
采用。

## 4. 合同和控制流

### 4.1 冻结身份

一次领域实验由下列信息共同标识：

- 当前干净代码 SHA 和相同的成功 public CI SHA；
- `domain-e2e-v1-1-secure-held-out@1.0.0` 及 SHA-256；
- `recent-form-prompt-context-v1-1` 及 SHA-256；
- `recent-form-review@0.2.0`、`context-builder-v1`、
  `coach_evaluation@1.1.0`；
- 已准入 DeepSeek 协议结果 SHA-256 和当时的代码 SHA；
- 案例执行计划 ID、版本、SHA-256 和固定 case ID 顺序；
- Provider `deepseek`、Model `deepseek-v4-pro`、thinking off、SDK retry 0。

执行计划公开结果只保存摘要和 case ID，不保存用户攻击原文、RAG 注入正文或 canary。
本批定义身份合同但不创建/读取真实 held-out 执行正文；后续真实门必须先冻结该计划，
且不得用真实输出反向修改当前规则。

### 4.2 数据流

```text
ExperimentPreparationReport
  + admitted protocol evidence
  + held-out Dataset
  + execution-plan identity
  + LLMProvider
  + DomainCaseExecutor
        |
        v
seed cumulative ResourceLedger from protocol evidence
        |
        v
for each frozen case in order
  -> register 4-call / 4000-token case boundary
  -> wrap Provider with cumulative + scope + case pre-I/O gates
  -> executor runs one production case
  -> coordinator derives calls/tokens/cost/latency from ledger deltas
  -> build safe DomainCandidateCase
  -> existing layered evaluator judges that case
  -> mismatch/unsafe => stop and mark remaining skipped
        |
        v
complete candidate/result only when all three observations exist
        |
        v
immutable sanitized ProviderDomainExperimentRecord
```

资源字段由协调器从账本差值生成，不能信任案例执行器自行上报。案例执行器只允许返回
状态、工具名、证据 ID、布尔检查、Evaluation 分数、终态和 provenance digest 等安全
语义观测。

### 4.3 累计资源

DeepSeek 固定边界：

| 范围 | Calls | Observed tokens |
|---|---:|---:|
| 已执行 Adapter protocol | 3 | 最多 4000 |
| 每个领域案例 | 4 | 最多 4000 |
| 三场领域累计 | 12 | 最多 12000 |
| Protocol + domain 累计 | 15 | 最多 16000 |

每请求最大 output tokens 为 1024；累计估算金额不得超过 `$0.10`。金额使用协议与领域
真实 usage 按冻结峰值单价累计，不把未知 usage 或未知价格写成 0。

## 5. 安全记录

公开记录白名单包括：

- Provider/model、代码/CI/Dataset/Snapshot/plan/protocol 摘要；
- calls、Token、估算金额、延迟、停止码；
- Agent status/stop reason 和安全 Provider error code；
- 工具名称、证据 ID、布尔 fact/citation/injection 结论；
- Evaluation 是否有效及分数、Harness 终态/安全原因码；
- 每案例分层失败码和聚合准确率；
- provenance SHA-256。

禁止字段包括 Prompt、原始用户/攻击文本、模型正文、RAG/Tool Observation 正文、原始
request/tool-call ID、SDK 对象、异常字符串、Key 和玩家个人数据。输出使用独占创建；
固定实验结果已存在时在 preflight 前拒绝，避免借新文件名绕过首次结果。

## 6. 离线 TDD 如何证明行为

1. 从已准入协议账本继承 3 calls/Token/金额，领域请求从累计第 4 次开始计数。
2. 每案例第 5 次和领域第 13 次调用都在 Fake Provider 收到请求前被拒绝。
3. 每案例 4000、领域 12000、累计 16000 Token 以及 `$0.10` 在 I/O 前/结算后按规则停止。
4. 第一个案例失败后，后续案例为 skipped 且 Fake Provider 不再收到请求。
5. unsafe publication 触发 global stop；其他 mismatch 只停止候选。
6. 资源数由 ledger 差值产生，案例执行器不能伪报 calls、Token、金额或延迟。
7. 序列化结果不出现 Fake Prompt、攻击串、模型正文、request ID、异常或 Key。
8. 同一固定输出只能创建一次，第二次在任何环境加载或 Provider 构造前失败。
9. 身份、协议准入、Dataset role/case order、plan digest 任一不匹配都在 Provider I/O 前
   fail closed。

这些测试证明执行控制，不证明 DeepSeek 的领域质量或真实抗注入能力。真实答案只能由
后续单次 held-out 运行产生。

## 7. 当前限制与下一门

本批完成后，仍缺少一次单独授权的真实领域门：冻结并摘要化真实案例执行计划、在新的
干净提交上通过 exact-SHA public CI、运行 no-I/O preflight，然后才加载 Key，最多执行
12 次真实调用并归档首次脱敏结果。

即使三场全部符合冻结期望，也只表示 DeepSeek V4 Pro 获得当前 recent-form 最小领域
准入；它不自动成为产品默认模型，不证明统计显著优于 GLM/Flash/Qwen，也不触发未来
Flash/Pro 任务分层。

采用决策见 `docs/adr/0020-use-no-io-admission-and-thin-coordinator-for-domain-heldout.md`。
