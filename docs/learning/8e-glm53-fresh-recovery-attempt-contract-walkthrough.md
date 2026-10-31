# 8E 学习材料：GLM-5.3-Flash fresh-recovery 尝试合同

日期：2026-08-31
对应需求：RQ-183 / ADR-0072

## 1. 问题与原理

一次 Provider 调用可能只产出 reasoning，最终没有可交付正文。RQ-181 的具体
形状是 `length + 空正文 + 非空 reasoning + 0 ToolCall`。如果为了“继续生成”在
适配器内部悄悄再发请求，系统会把两次网络消耗记成一次，并且把新的完整请求误说成
API 原生续写。

这里采用两个基本原则：每一个真正发出的底层请求都是独立 attempt；任何恢复都必须
由精确版本合同计划，并在失败时停止。reasoning 只能作为脱敏状态参与判定，不能变成
用户答案或公共证据。

## 2. 本批实现什么

`app/providers/response_recovery_contract.py` 提供四层无网络合同：

- `ResponseRecoveryRuntimeProfile`：候选身份、8192 单次上限、90/120 秒边界和
  candidate 激活状态；它不是现有 `ModelRuntimeProfile` 注册项。
- `ResponseAttemptSpec` / `ResponseAttemptOutcome`：把 `primary` 与
  `fresh_recovery` 以及结束原因、字段状态、Usage 数字分开记录，不保存原文。
- `ResponseRecoveryLedger`：预留一次、结算一次，统计每个底层调用和累计资源；最多
  两次，不产生第三次。
- `ResponseRecoveryTrace`：独立 schema 1.0 的脱敏尝试轨迹，记录身份、判定和资源，
  不改既有 `RuntimeTrace`。

`build_response_recovery_plan()` 会重新运行 RQ-182 候选策略。只有精确白名单形状
才会在离线计划中出现第二个槽位；返回的计划始终 `execution_allowed=false`。

## 3. 代码地图

```text
app/providers/response_completion_policy.py
  └─ 脱敏首回合判定
app/providers/response_recovery_contract.py
  ├─ ResponseRecoveryRuntimeProfile
  ├─ ResponseAttemptSpec / Outcome / Record
  ├─ ResponseRecoveryBudget / Ledger
  └─ ResponseRecoveryTrace
tests/test_response_recovery_contract.py
  └─ 30 项纯离线合同测试
```

## 4. 数据与控制流

```text
首回合 Provider 结果（适配器先脱敏）
  → ResponseBoundarySnapshot + ResponseRequestContext
  → 候选策略重新判定
  → offline-only RecoveryPlan
  → Ledger.reserve_next(primary) / settle(primary outcome) 记录已发生回合
  → 若白名单命中，再 reserve_next(fresh_recovery)
  → 外部执行层（本批不存在）
  → Ledger.settle(sanitized recovery outcome)
  → immutable attempt record / RecoveryTrace
```

首回合不是候选形状时，账本直接终止；是候选形状时，账本先把已观察到的 primary
作为一次已发生调用记账，然后也只能描述一次未来 `fresh_recovery`。账本会重新计算每个 Outcome 的策略判定，因此不能靠调用方传入一个
伪造的 `candidate_eligible=true` 打开恢复。

## 5. 预算合同

候选默认最多两次底层调用、一次额外调用，单次输出上限 8192，累计 input 32,000、
累计 output 16,384、累计观察时间 180,000ms。预留阶段检查剩余 attempt/output/
时间空间；结算阶段再检查实际 token、单次输出和单次时间。Provider 错误、Usage 缺失
和超预算都保留已消耗的调用槽位，不能通过重试抹掉。

这些数字只属于未注册候选，用于离线讨论“是否值得一次新诊断”；它们没有提升当前
产品严格 Flash v1 的 2048/零额外调用，也不是供应商硬上限或生产承诺。

## 6. 验证证据

聚焦命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_response_recovery_contract.py -q
```

结果：`30 passed`。相邻响应策略、Flash runtime、Runtime model、Observed Provider
和领域门回归合计 `128 passed`。测试覆盖身份错配、候选未注册、顺序、并发/重复结算、
预算不足、单次/累计超限、失败消耗、判定重算和 Trace 脱敏。

## 7. 运行方法与安全边界

这是纯 Python 对象合同，不需要 Key、服务器、SDK 或网络。模块没有 Provider 参数、
请求构造或可调用的 retry 入口；任何未来执行都必须在另一个明确授权的运行时层完成，
并保留 A/B exact-SHA、同 SHA G53-3、真实诊断和成本/延迟证据。不要把 Prompt、正文、
reasoning、工具参数、请求 ID 或 Key 写入 Outcome、Ledger 或 Trace。

## 8. 当前限制与后续闸门

- 仍没有 API 原生 resume；`fresh_recovery` 只是一次新的完整请求身份。
- 候选没有注册到产品组合根，不能被 metadata、模型输出或默认配置隐式启用。
- 本地合同测试不证明模型一般能力、领域采用、生产安全/部署合规，也不关闭 G53-7、
  黄金切片、OP.GG breadth 或 8F 作品集闸门。
- 真正接 Provider 前，必须取得新的 exact-SHA 公共 CI、在同一新 SHA 重取协议证据、
  再由用户单独授权一次有界真实诊断；结果不能覆盖 RQ-180/RQ-181。

## 9. 面试准确表述

可以说：

> 我把一次可能被 reasoning 耗尽的 Flash 响应拆成版本化的脱敏判定和有界尝试合同；
> 每个底层请求都进入预算账本和独立 Trace，最多只描述一次 fresh recovery，而且
> 候选未注册、不会偷偷重试。

不能说：

> GLM 已经支持自动续写、8192 已成为产品默认、或这组离线测试等于 G53-7/生产准入。

## 10. RQ-184 公共证据补充

RQ-184 把本合同从“本地离线实现”推进到可复核的公共证据接缝，但没有改变候选的注册状态。实现提交
A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的 Actions run `33405110692` 三 job 全部成功；同一 A checkout
的 G53-3 严格 `3/3` 调用通过（A1 `1/1`、A2 `2/2`，`admitted=true`，SDK retries `0`）。脱敏协议结果只由 A
的直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 新增，B 的 Actions run `33405881172` 三 job
也全部成功；A/B 无 I/O identity preflight 通过，结果 canonical-LF 摘要为
`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。

学习时要把三层证据分开：本地合同测试证明状态机边界，公共 CI 证明提交可复现，同 SHA G53-3 证明协议接缝；
它们都不证明 fresh-recovery 已实际执行、G53-7 已准入或产品已经具备生产成熟度。候选仍是
`activation_state=candidate` / `execution_allowed=false`，下一次真实诊断需要单独授权，并要记录成本、延迟、
失败和脱敏 Trace；严格 Flash v1 的 2048/零额外调用不变。

## 11. RQ-185 真实诊断为什么没有形成结果

RQ-185 中两次独立诊断启动都只进入 `primary` 首回合。第一次沿用候选合同的 120 秒传输边界，
调用方在约 60 秒无返回时停止；第二次把客户端传输上限临时收窄为 20 秒，但进程仍没有在约
60 秒内退出。两次都没有收到可观察响应，因此没有 Usage、finish reason、候选判定、Trace 或结果 JSON，
也不能确定请求是否已经抵达供应商或产生费用。

这揭示了一个和模型输出不同的工程边界：SDK 数值 timeout、代理连接、读取等待与外层进程截止并不一定是同一个
可观察状态。下一版若获授权，应先把这些层次分别计时和强制终止，再讨论模型恢复；不能把“进程未返回”直接写成
“模型超时”，也不能在没有首回合脱敏快照时打开 `fresh_recovery`。因此当前准确表述是：候选合同和公共协议证据
存在，但真实恢复诊断因传输/代理边界中断，尚无可用结果；严格 Flash v1 仍为 2048/零额外调用。

## 12. RQ-186/187：完整窗口仍无响应时如何表述

RQ-186 先证明请求级 deadline 确实进入 SDK；RQ-187 再用候选完整 90 秒窗口复核，唯一 primary 在 90.188 秒以
transport timeout 结束，仍没有响应、Usage、finish reason 或 request ID，也没有发送 fresh recovery。这样可以排除
“只是 30 秒太短”，但不能进一步判断是代理/连接/读取、首字节等待还是服务端生成延迟。

准确表述应是“候选长请求在受控窗口内未形成可观察供应商响应，费用未知”，而不是“模型能力失败”或“模型一定没收到
请求”。下一步若继续，必须设计传输/生成路径拆分诊断；候选仍未注册，严格 Flash v1 的 2048/零额外调用不变。

## 13. RQ-188：如何把传输可达与生成开始分开

用户扩大授权后，先在隔离工作树执行固定三路、最多三次调用的无正文诊断：合法 Flash `thinking=enabled`/`reasoning_effort=low` 最小控制、冻结上下文 256 token max 同步请求、冻结上下文 8192 token max 流式首块请求。首次 disabled-thinking 控制结果被保留为审计，但不作为 Flash 能力结论，因为该模型的 thinking 合同要求开启。

三路均收到可观察响应。两次同步请求有有效 Usage，却以 `finish_reason=length`、空正文、非空 reasoning 结束；流式请求约 687ms 先给出 `delta_reasoning` 首块，探针随后主动关闭，因此没有宣称终止 Usage 或完整流装配。正式结果 SHA-256 为 `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，诊断/source identity 为 `b67b4500ebdbff934e470fd92c1461184aa7c49b`。

学习上的关键区分是：这批证据确认 endpoint/model 路径可达且生成已开始，但没有裁决 90 秒长同步请求的代理/读取/服务端延迟，也没有证明 provider-neutral streaming、模型一般质量或生产准入。严格 Flash v1 仍是 2048 输出/零额外调用，候选仍未注册；下一步是输出额度与推理档位校准。
