# ADR-0079：设计版本化 GLM-5.3 候选 recovery 诊断协议

- 日期：2026-09-02
- 状态：`design-complete-local / candidate-only / implementation-pending`
- 范围：Stage 8 / 8E；`candidate-recovery-diagnostic-version-design`（RQ-203）
- 依据：ADR-0071、0072、0074、0077、0078；RQ-181–RQ-202；
  `app/evaluation/candidate_evaluation_harness.py`、
  `app/evaluation/candidate_stream_contract.py`

## 背景

RQ-201 已证明隔离候选评估台可以在同一提交上通过公共 CI。RQ-202 又修补了回执
字段可伪造、单次截止复用累计窗口等边界，并确认旧的
`glm53_flash_response_recovery_diagnostic.py` 不能直接承载下一次 recovery：它带有
真实 SDK/I/O、旧同步账本以及把未知 Usage 当作零的历史投影。

因此下一步不能“复制旧脚本再加一个开关”，而要先冻结一个独立、可版本化、可审计的
诊断协议。本 ADR 只完成协议设计，不实现协议、不读取 Key、不发送请求、不打开
fresh-recovery，也不把候选提升为产品运行时。

## 决策

### 1. 使用独立的协议身份和不可变记录

新协议的逻辑身份定为
`glm-5.3-flash-candidate-recovery-diagnostic-v2`，记录 schema 版本为 `2.0.0`。
版本号与既有旧诊断 `1.0` 不兼容；旧 JSON 只作历史证据，不能被原地迁移或覆盖。
每份记录必须同时携带以下精确身份：

- `provider_id=zhipu`、`model=glm-5.3-flash`；
- 候选 runtime profile 的 ID/版本和 completion policy 的 ID/版本；
- 实现提交 SHA、诊断代码 SHA、输入计划 SHA，以及不含正文的上下文形状 SHA；
- 本次 run 的随机 nonce SHA（nonce 只在内存中存在）；
- 协议 ID/版本和生成时间。

这些字段只用于重现“用的是什么合同”，不证明供应商质量或账号权限。所有 Git SHA
必须是完整的小写 40 位值；任何同值但类型/版本不完全匹配的对象都拒绝。

### 2. 输入是显式的、不可扩展的请求摘要

协议实现只接受已经通过候选 binding/profile/policy 检查的 `ChatRequest`、受信的
`ResponseRequestContext`、注入式 transport 和显式 activation permit。请求正文只在
单次内存生命周期存在，摘要允许记录：

- attempt 序号和 `primary`/`fresh_recovery` 身份；
- 消息数量、角色序列、每条消息的字段存在性/长度/工具数量和整体形状 SHA；
- 工具数量与选择模式、响应合同标志；
- 实际请求输出上限、单次 agent/transport 截止、采样参数和 retries 设置；
- 上述字段对应的 profile/policy 身份。

摘要禁止 Prompt、正文、reasoning、工具参数/结果、Key、原始 request ID、SDK 对象和
异常文本。调用方不能靠 metadata 选择 profile、policy、attempt kind、activation 或
预算；未知字段直接拒绝，而不是静默忽略。

### 3. recovery 是新的完整请求，不是续写或隐式重试

状态机固定为：

```text
CREATED
  -> PRIMARY_RESERVED -> PRIMARY_OBSERVING -> PRIMARY_SETTLED
       -> COMPLETE / TOOL_CALLS_READY / FAIL_CLOSED
       -> CANDIDATE_ELIGIBLE
              -> (activation permit 通过才可) RECOVERY_RESERVED
              -> RECOVERY_OBSERVING -> RECOVERY_SETTLED
              -> COMPLETE / TOOL_CALLS_READY / FAIL_CLOSED
```

primary 必须在 I/O 前 reserve；open、读取、取消、超时和 close 失败都消耗已预留槽位。
只有 BoundaryObservation 完整、policy 精确返回候选形状且独立 permit 有效时，才可以
reserve 第二槽位。第二槽位再次提交同一消息语义的完整请求，明确标记
`fresh_recovery`，不使用 resume token、不调用 SDK retry、不执行 ToolRuntime。当前
实现中的 activation 仍是 sealed `disabled`，所以本门不会真正打开第二条请求。

### 4. 每个 attempt 使用 body-free observation 和可推导决定

每行 `AttemptDiagnostic` 必须由同一条 normalized event pump 的观察结果生成，至少
包括：

- 生命周期：opened、EOF、terminal、close 状态；
- finish reason、可见正文/reasoning/tool 的字段状态和 ToolCall 数量；
- resolved model 与 request ID 的 SHA-256（不保存原值）；
- `usage_state=valid|missing|invalid`，以及仅在 valid 时出现的 input/output/cache
  token 数；
- 单调时钟推导的时间点和总耗时；
- `failure_class`、安全 `error_code`/`error_stage`、settled 标记；
- policy disposition、reason 和装配状态，全部由 observation 重算。

`disposition`、`candidate_eligible`、`assembled_complete`、错误和预算状态都不是
调用方可自由填写的资格字段。回执构造器必须再次推导并拒绝 `replace()` 或等价方式
造成的矛盾。完整 `ChatResponse` 只可瞬时交给显式 evaluation consumer，永不进入
diagnostic record、ledger、日志或产品 Trace。

### 5. 分开记录单次预算、累计预算和未知资源

候选 profile 的硬上限仍为：单次输出 8192、agent 90 秒、transport 120 秒；累计
input 32,000、output 16,384、elapsed 180,000ms，最多 2 attempts、最多 1 次额外
调用，SDK retries=0。实现还必须把真正传给供应商的 request-level output cap 写入
摘要，明确区分“请求 cap 被触发”和“候选 profile 累计预算被触发”。

预算投影使用三态：

```text
within   = 所需资源全部已知且没有任何维度超限
exceeded = 至少一个已知维度超过可信上限
unknown  = 仍有资源未知，不能证明 within，也不能把未知当作零
```

若 Usage 缺失/无效，input/output 总量为 `null`，费用和剩余额度不能由 `or 0` 推导。
已知的 elapsed、调用数和已知 token 仍可单独记录；未知不被假装成实际消耗为零。

### 6. 延迟采用分段、单调、可缺省的度量

每个 attempt 只记录整数毫秒，来源必须是单调时钟；没有观察到的阶段保持 `null`：

- `open_elapsed_ms`：调用方打开 transport 到成功返回流；
- `first_event_ms`：首个合法 normalized event；
- `first_visible_content_ms`：首个可见正文字段；
- `terminal_ms`：观察到合法终止原因；
- `close_elapsed_ms`：关闭资源耗时；
- `total_elapsed_ms`：从 reserve/open 监督起点到结算。

这些数字只描述本次客户端观察路径。没有 terminal 或 Usage 时不能据此宣称完整生成、
模型质量或供应商内部延迟；单次超时和 transport/服务端原因必须保持可区分的未知状态。
时钟反向、NaN、溢出或超过单次窗口立即 fail closed，并仍结算已发出的槽位。

### 7. 费用只在有可验证单价时计算

记录增加独立的 `CostObservation`，状态为 `unknown|estimated|actual`：

- `unknown`：Usage 不完整、单价未验证、计费口径不明或请求是否抵达未知；金额必须为
  `null`；
- `estimated`：Usage 完整且使用了在运行开始前冻结的公开单价快照，记录快照 ID/SHA、
  币种和四舍五入规则，但不把估算写成账单事实；
- `actual`：只有供应商提供了可核验的本次账单/用量凭证才允许使用，当前协议不要求也
  不会主动获取该凭证。

价格快照不能来自用户可控文本，不能保存账户标识、Key 或完整账单。没有可靠价格时
宁可保持 `unknown`，不以历史单价、零值或模型名称猜费用。

### 8. 失败聚合必须保留第一现场

每次 attempt 的 `failure_class` 只允许以下安全枚举：
`transport`、`protocol`、`identity`、`usage`、`budget`、`completion`、`consumer`、
`control`。同时保存规范化的 code/stage，不保存异常消息。顶层记录由已结算行推导：

- `run_state`：`complete_text`、`tool_calls_ready`、`candidate_eligible`、
  `recovery_complete`、`fail_closed` 或 `interrupted`；
- `first_failure`：第一条非空安全失败（若有）；
- `terminal_reason`：最后一条已结算决定或不可恢复的控制失败；
- `recovery_skip_reason`：未满足候选形状、预算未知、permit 无效或 activation disabled
  等明确原因。

后续错误不能覆盖已经观察到的第一现场；“请求没有响应”不能被改写成模型拒绝，
“Usage 缺失”也不能被改写成零成本。控制异常清理后继续传播，但回执仍留下安全的
`interrupted` 结算事实。

### 9. 记录落盘与 Trace 保持隔离

记录是可选的、原子 create-only 的 JSON 文件，使用 canonical UTF-8/LF；写入前后都要
执行 body-free allow-list 检查和完整文件 SHA-256。建议路径仍在
`data/evaluation/results/provider_capabilities/`，不建立数据库表、不写用户 API、不
迁移统一 `RuntimeTrace`。日志、`repr`、测试失败输出和异常包装同样不得泄露正文、
reasoning、工具参数、Prompt、Key、request ID 或供应商原始响应。

### 10. 启用门与证据门分离

本设计不生成 activation permit，也不改变当前 sealed disabled gate。未来要运行一次
真实候选诊断，至少需要：

1. 新协议实现的 exact-SHA 公共 CI（含完整 fake/local 失败矩阵）；
2. 同一 SHA 的协议 dry-run 和 body-free 序列化证据；
3. 明确的一次性真实调用授权、密钥只读存在性预检和费用/延迟停止线；
4. 运行后人工审查失败聚合、成本状态、Trace 脱敏和是否允许第二请求；
5. 在任何 G53-7、黄金切片或产品 Runtime 接线前，另立注册/准入决定。

## 失败矩阵

| 场景 | v2 记录 | 是否继续 |
| --- | --- | --- |
| 完整 `stop` + EOF + valid Usage | `complete_text`，可选 consumer 结果不落盘 | 否 |
| 完整 `tool_calls` + EOF + valid Usage | `tool_calls_ready`，只作评估观察 | 否，不执行工具 |
| 精确 `length`/空正文/非空 reasoning/valid Usage | `candidate_eligible`，记录 recovery plan | 当前 disabled，不继续 |
| 正文非空、带工具、非初始阶段或预算不足 | `fail_closed` + completion/budget code | 否 |
| 缺 EOF、terminal、model、request identity 或 Usage | `fail_closed`，资源/费用为 unknown | 否 |
| open/read/translate/close/clock/控制异常 | 结算已预留槽位，保留第一安全错误 | 否 |
| permit 过期、身份不符或重复使用 | activation/identity fail closed | 否 |
| 第二请求再次失败、再次 length 或累计超限 | `fail_closed`，保留两次实际尝试 | 禁止第三次 |
| consumer 抛错或试图写产品存储 | 独立 `consumer` 错误 | 不改变策略/账本 |

## 明确拒绝的替代方案

- **复制旧同步诊断器并改几个字段**：会带入 SDK/I/O、旧 `or 0` Usage 和含糊 activation，
  不能形成可验证的新版本边界。
- **把 v2 直接包装成 `LLMProvider` 或修改 AgentLoop**：会静默改变默认模型、调用
  计数、ToolRuntime 副作用、统一 Trace 和生产预算。
- **用“成功响应时间”代替分段延迟**：会把首块、首正文、terminal 和 close 混成一个
  数字，无法解释超时现场。
- **单价缺失时估算费用或把未知设为零**：会把成本不确定性伪装成可比较的生产证据。
- **把旧 `1.0` 结果原地升级到 `2.0`**：会破坏不可变历史和 exact-SHA 追溯。

## 设计退出条件与下一步

本门完成的设计证据是：协议身份、输入摘要、reserve/settle 时序、activation、
预算/Usage、分段延迟、费用三态、失败聚合、脱敏落盘、替代方案和实施测试矩阵均已
冻结在本 ADR、实现计划和学习 walkthrough 中。没有新增代码、结果 JSON、真实 API 或
生产能力。

下一精确 checkpoint 为：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`

只有再次授权后，才实现 v2 的 fake/local 协议和聚焦测试；实现后仍要取得 exact-SHA
公共 CI、协议证据与独立真实调用授权。Stage 8/8E 继续 `in_progress`，8F 未开始，
`production_media=0`。
