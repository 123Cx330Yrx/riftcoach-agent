# ADR-0076：冻结 GLM-5.3 候选边界观察与隔离接线合同

- 日期：2026-09-01
- 状态：`implementation-public / candidate-only / harness-design-complete`
- 范围：Stage 8 / 8E；GLM-5.3-Flash 候选 runtime wiring design（RQ-196）
- 依据：RQ-194 实现提交 `a7580e861cd986c026040c7fcfcc3fa577737961`、
  Actions `33496237588`；RQ-195 评审与其三 job 公共证据

## 背景与问题

RQ-194 的 `ZhipuStreamAdapter.assemble()` 是“完整回答”接口：只有真实 EOF、合法
终止原因和有效 Usage 同时成立，才会交付 `ChatResponse`。这对产品同步合同是正确的，
但候选恢复策略还需要识别一个很窄的形状：`finish_reason=length`、正文为空、reasoning
非空、Usage 有效、且处于初始 Agent 回合。若直接把 `StreamAdapterError` 当成这个形状，
网络中断、半截流、模型错配和真正的截断会被混为一谈。

另一个接缝是预算身份：已登记的 `glm-5.3-flash-runtime-v1` 会把请求上限收紧到
2048；候选 v2 需要 8192 和一次 fresh-recovery。把候选上限塞进普通
`ZhipuProvider` 或只相信请求 metadata，都会让 v1/v2 身份和预算发生隐式泄漏。

## 决策

### 1. 冻结四元身份和尝试身份

下一批实现的模块名暂定为 `app/evaluation/candidate_stream_contract.py`，其中的
`CandidateRuntimeBinding` 必须同时携带并精确校验：

| 字段 | 唯一允许值 |
| --- | --- |
| `provider_id` | `zhipu` |
| `model` | `glm-5.3-flash` |
| `runtime_profile_id/version` | `glm-5.3-flash-runtime-v2-candidate` / `2.0.0` |
| `policy_id/version` | `glm-5.3-flash-fresh-recovery-candidate-v1` / `1.0.0` |

绑定还要带 `attempt_ordinal` 和 `attempt_kind`（`primary` 或
`fresh_recovery`）。实现必须比较受信常量本身，而不是只比较可由调用方构造的同值
字段；错配、伪造对象、非 candidate 状态和不连续 ordinal 都在 Provider I/O 前拒绝。

### 2. 采用只输出状态的 `BoundaryObservation`

`BoundaryObservation` 是不可变、body-free 的单次流观察。它可以记录以下白名单字段：

- schema 版本、四元身份、尝试序号/类型；
- 生命周期：`opened`、`eof_observed`、`terminal_observed`、`close_state`；
- 安全终止码、`content_state`、`reasoning_content_state`、有界
  `tool_call_count`；
- `usage_state`，以及仅在 `valid` 时出现的 input/output/cached token 数字；
- 有界单调 `elapsed_ms`、已解析 model、安全错误码/错误阶段；
- request identity 的 SHA-256 摘要（不保存原值）；
- 由内部状态机推导的 `observation_state` 和 `next_action`。

它绝不接受或保存部分正文、reasoning、工具参数、Prompt、SDK 对象、Key、原始请求
ID 或异常原文。`candidate_eligible` 不是可由调用方填写的字段；只有在
`eof_observed + terminal_observed + close_state=closed + valid Usage` 成立后，才可把
快照映射成现有 `ResponseBoundarySnapshot`，再由版本化 policy 重新计算资格。

字段状态的聚合规则也固定：非字符串/冲突优先级高于非空，非空高于空字符串，空高于
显式 null；从未观察到字段才是 `not_observed`。因此“正文为空”不能被缺失字段或
异常伪装。Usage 缺失/非法时 token 总额保持 `None`，不能写成数字 0。

### 3. 共享校验核心，分流完整与不完整结果

下一实现要把 RQ-194 的 model、sequence、tool、Usage 和 request-id 校验抽成同一份
纯函数/内部验证核心，供两条路径使用：

```text
供应商 chunk
  → 共享验证/翻译核心
      ├─ 完整 stop/tool_calls + EOF + Usage
      │    → 现有 ProviderStreamAssembler → 临时 StreamAssemblyResult
      └─ length/缺终态/缺 Usage/中断
           → BoundaryObservation（只保留状态）
```

完整分支继续使用 `assemble()` 的回答合同；不完整分支永远不能构造
`ChatResponse`。观察器本身不重新实现一套宽松的 vendor parser，也不通过读取 assembler
私有正文来推导资格。任何 read、translate、model、sequence、tool、Usage、EOF 或 close
错误都使本次观察 `fail_closed`，并消耗已预留的尝试槽位。

### 4. 用独立候选传输承载 v2 预算

未来的 `CandidateZhipuStreamTransport`（名称可在实现时确认）放在 `app/evaluation/`，
只接受上述精确 candidate profile/policy 和普通智谱 API 的标准基址。它使用候选 profile
的 8192 单次上限、90 秒 Agent/工具窗口、120 秒传输上限、`temperature=1`、`top_p=0.95`
和 SDK `max_retries=0`，并把每次请求 cap 收紧到剩余账本。

它不是 `LLMProvider`，不注册到 `ProviderRegistry`，不改变 `ModelRuntimeProfile` 注册表、
`create_zhipu_provider()`、默认 composition root 或 `capabilities.streaming`。原因是：
绑定 v1 的产品 `ZhipuProvider` 会合法地收紧到 2048；完全不绑定 profile 的普通 Provider
又无法证明 v2 身份。独立 transport 将这两个风险隔开，并必须与 RQ-194 共用验证核心或
通过逐字段 conformance 测试证明两者一致。

### 5. `CandidateStreamEvaluationHarness` 的控制流

候选调用方只允许显式持有 adapter/transport、candidate policy、candidate profile 和
`ResponseRecoveryLedger`，不被默认发现。每次尝试的固定顺序是：

1. 在 I/O 前校验四元身份、attempt ordinal、请求形状和剩余预算；
2. 先 `ledger.reserve_next()`，再打开一次流；open 失败也算该槽位的终态；
3. 通过共享核心消费到真实 EOF，或在异常/取消时安全关闭并产生观察；
4. 完整流只交付临时 `StreamAssemblyResult`，边界流只交付 `BoundaryObservation`；
5. 对满足完整 EOF/终态/Usage 的观察映射 `ResponseBoundarySnapshot`，由 policy 重新分类；
6. 无论成功、超时、Usage 缺失、close 失败还是取消，都对该 reservation 恰好一次
   `settle()`；
7. 从 allow-list 观察和 ledger 生成候选 Trace。任何第三次 reservation、重复 settle、
   失败后继续调用都拒绝。

当前 `execution_allowed=false` 保持不变：即使 primary 形状被 policy 判为
`candidate_eligible`，也只能产生 `awaiting_recovery` 记录，不能发送 fresh-recovery。

### 6. 独立的候选 Trace 投影

下一实现新增 `CandidateStreamTrace`（schema `1.0`）或等价显式 envelope，而不是把
`StreamAssemblyTrace` 直接写入 `RuntimeTraceStore`。顶层保留四元身份、attempt rows、
调用数、可确定的 token 总额（任一未知时总额为 `None`）、耗时、未知 Usage 次数、预算
超限和终态；每行保留 ordinal/kind、状态、finish/error code、字段状态、tool count、
Usage 状态/数字和耗时。构造器必须重新校验身份稳定、ordinal 连续、调用数等于行数及
总额一致，不能相信调用方传入的资格布尔值。

Trace、`repr`、JSON 和异常文本均不得出现正文、reasoning、工具参数、Prompt、Key、
SDK 对象或原始 request ID。这个 Trace 只服务候选评测，不是统一 Runtime Trace，也
不改变现有同步 Runtime 的 Usage/预算语义。

## 状态机与失败矩阵

```text
not_started
  → awaiting_primary
  → observing_primary
      ├─ complete_text / tool_calls_ready
      ├─ candidate_shape → awaiting_recovery（当前不得执行）
      └─ fail_closed
```

| 事件 | 观察结果 | 是否允许下一次调用 |
| --- | --- | --- |
| 正常 EOF + `stop`/`tool_calls` + 合法 Usage | 完整分支，交付临时 assembled result | 否 |
| `length` + 空正文 + 非空 reasoning + 合法 Usage + EOF/close | `candidate_shape`，再由 policy 判定 | 当前否（execution disabled） |
| 缺 EOF、缺 terminal、缺 Usage、`length` 形状不符 | `fail_closed`/unknown | 否 |
| open/read/translate/model/sequence/tool/close 异常 | 脱敏 `fail_closed`，结算当前槽位 | 否 |
| 四元身份或 attempt ordinal 错配 | I/O 前拒绝 | 不产生调用 |
| 第三次 reservation、重复 settle、未知 reservation | ledger 状态错误 | 否 |

## 备选方案与取舍

- **把 adapter 包成 `LLMProvider`：拒绝。** 会让默认注册表看到候选，并掩盖完整流与
  边界流的差异。
- **在 `AgentLoop` 增加隐式 streaming 分支：拒绝。** 会同时改变工具回放、截止时间、
  Runtime Trace 和产品预算，且不能解决 v1/v2 profile 冲突。
- **直接复用现有一次性诊断脚本：拒绝。** 旧脚本会以可变 recorder 观察同步响应，
  没有流 EOF/close 生命周期，也不能成为可复用的候选端口。
- **独立 evaluation transport + shared validation core：采用。** 代价是要先实现
  body-free observer 和较完整的故障矩阵，但能保持生产主线不变、让身份和预算可审计。

## 非功能与安全约束

- 观察路径只保留 O(1) 的字段状态/计数，不累积正文、reasoning 或工具参数；
- 所有计数、token、时间和集合大小有硬上限，时钟使用单调时间；
- 任何 unknown Usage 都显式标记，不得当作零继续恢复；
- 供应商错误统一为安全码，异常原文只作为被丢弃的 cause；
- 传输工厂固定 `max_retries=0`，预算由 ledger 累计而非单次 cap 覆盖；
- 代码、fake 测试、Trace 和证据不得读取或落盘 Key；真实调用仍需单独授权和新鲜
  exact-SHA 身份。

## 本门退出条件与下一步

RQ-196 的设计退出条件已经完成；其原定的 implementation checkpoint 由 RQ-197 推进为本地实现。
该历史设计门不代表候选已注册、不打开 `capabilities.streaming`、不改默认模型、不改 AgentLoop/Workbench/
Portal/Account/Auth，也不发真实 API 请求。

### RQ-197 实现附录（2026-09-01）

已在隔离分支落地纯 fake/local `BoundaryObservation`、共享事件验证核心、候选 v2 注入式 transport port 和
独立 Trace allow-list。`ProviderStreamEvent` 保留显式 null/缺失 presence；完整 assembler、智谱翻译与观察器
共享 model/sequence/tool/Usage/大小校验。实现只保存生命周期、字段状态、终止码、工具计数、有效 Usage 数字、
单调耗时和 SHA-256，不保存正文、reasoning、Prompt、工具参数、Key、SDK 对象或异常原文；不完整/异常流
fail-closed，不构造 `ChatResponse`，unknown Usage 不当零。

候选仍 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 2048/零额外调用、
`capabilities.streaming=False`、GLM-5.2 显式回退、产品 Runtime、统一 Trace、Workbench、Portal、Account、
Auth、默认模型和 `production_media=0` 均保持原状。聚焦与相邻回归为 `163 passed`，compileall、diff check、
governance 已通过；全量本地首错是缺少 `RIFTCOACH_TEST_DATABASE_URL` 的 PostgreSQL fixture。

RQ-198 已完成该公共 CI 门：实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run
`33507627615` 三 job 全绿，公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。

当前唯一下一精确 checkpoint 为：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`

下一轮只设计隔离 harness/ledger/Trace 接缝；候选仍不注册、不打开 `capabilities.streaming`，不执行真实 API、
fresh-recovery、G53-7、黄金切片或生产准入。严格 Flash v1 和现有产品边界继续不变，本轮暂停。

### RQ-199 设计附录（2026-09-02）

上段“下一轮只设计”的状态已由 RQ-199 推进。ADR-0077 进一步发现：现有
`ResponseRecoveryLedger` 需要已知的首回合快照，而真实 harness 又必须在 primary I/O
前 reserve，因此不能直接用 sentinel snapshot 或结束后才记账。后续实现采用
candidate-only staged ledger：先预留未知 primary，真实 `BoundaryObservation` 完成后才
冻结 policy/plan 并结算；一条 normalized stream 只经一次事件泵，同时服务 observer 和
仅内存 assembler，最后生成独立 body-free receipt。

当前唯一下一精确 checkpoint 已更新为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。
候选仍未注册、activation disabled、`execution_allowed=false`；严格 Flash v1、产品 Runtime、
`capabilities.streaming=False`、Workbench、Portal、Account、Auth 和 `production_media=0` 不变，
没有真实 API、fresh-recovery、G53-7 或黄金切片。
