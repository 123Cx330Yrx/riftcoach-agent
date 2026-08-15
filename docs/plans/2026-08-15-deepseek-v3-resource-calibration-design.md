# 5D-7 DeepSeek V3 资源合同 development 校准设计

## 1. 这一步具体解决什么问题

这里的 `V3` 指第三次独立的领域采用尝试，不是 DeepSeek 的模型版本。

V2 已经真实证明旧资源合同不可达：第一条规范化响应消耗 3241 input + 199 output，
下一次调用在预留 1024 output 后至少需要 4464 的单例上限，而旧上限只有 4000。
但 V2 没有走到最终草稿和独立 Evaluation，因此不能据此判断模型报告质量。

当前真正缺少的是一份在看见新 held-out 答案前完成的资源合同。它必须回答：

1. 正常的工具往返和 Evaluation 到底需要哪四种请求形状；
2. DeepSeek 对这些真实请求形状报告多少 input tokens；
3. 单案例、三案例、金额和延迟上限怎样从证据推导，而不是拍脑袋填写；
4. 资源仍然不足时，系统怎样在 Provider I/O 前或首个越界响应后失败关闭。

## 2. 初学者需要先理解的三个概念

### 2.1 控制流预算

近期复盘的正常路径不是“调用一次模型”：

```text
第 1 次 Agent 请求
  -> 模型选择 knowledge.search
  -> 本地工具执行
第 2 次 Agent 请求
  -> 模型根据工具结果生成草稿
第 3 次 Evaluation 请求
  -> 独立评测草稿
第 4 次 Evaluation repair（仅当第 3 次 JSON 格式非法）
  -> 使用相同 Schema 最多修复一次
```

前三次是正常必经路径，第四次是合法但可选的恢复路径。报告内容修订在本采用门中仍被
禁用，因此不存在第 5 次调用。

### 2.2 Usage 校准不是质量评测

Usage 校准只问“这份请求实际占多少 Token、耗时多久”，不问“模型回答得好不好”。
校准请求可以使用公开的合成 development 数据；它的回答不能成为领域准入证据。

### 2.3 安全上限不是统计保证

本设计使用两个 development 轮廓和 25% 工程余量。25% 是预先冻结的保守政策，不是
“95% 置信区间”，也不代表两条样本足以估计线上分布。任何真实请求超过校准 envelope
或真实 Usage 超过预算时仍然失败关闭，不会自动加预算追绿。

## 3. 入口审计证据

当前生产链和测试已经证明：

- 成功路径为 2 次 Agent + 1 次 Evaluation；
- `decode_structured_response()` 最多允许一次同合同 Evaluation repair；
- repair 成功路径精确使用第 4 次、也是最后一次领域调用；
- `max_revisions=0` 只禁止报告内容修订，不会删除 Evaluation 的一次格式修复；
- 账本在每次 I/O 前预留当前请求的最大输出，但只把 Provider 返回的实际 Usage 永久结算。

本设计入口又用公开 development fixture、本地受控 Provider 和真实 production Executor
走通了四阶段请求形状。只观察消息角色、数量和 tokenizer-free 本地长度，不打印或保存
正文：

| 阶段 | 消息角色 | 本地长度单位 |
|---|---|---:|
| `agent_initial` | system, user | 5956 |
| `agent_after_tool` | system, user, assistant, tool | 7064 |
| `evaluation` | system, user | 5749 |
| `evaluation_repair` | system, user | 2510 |

这些数只证明第四种请求形状真实存在；它们不是 DeepSeek tokenizer 的官方 Token 数，也
不是即将写入 V3 的预算。

## 4. 方案比较

### 方案 A：直接把 V2 单例上限提高到一个大数

实现最少，但新数字没有完整 Usage 证据，还会把已经看过的 V2 考卷用于调预算。拒绝。

### 方案 B：直接运行一条 development 端到端模型链路

它能得到一次真实消耗，但请求是否进入工具、Evaluation repair 等阶段取决于模型当次
行为。资源校准和模型行为混在一起，未到达的阶段仍然是 unknown。拒绝作为资源合同的
唯一依据；以后可以保留为语义 development 测试。

### 方案 C：冻结生产形状的 development 请求，再做独立 Usage replay

先用受控本地响应让真实 production Executor 确定性地生成四个 `ChatRequest`，再把这些
请求逐个交给候选 Provider，仅收集规范化 Usage/延迟。这样所有阶段都可观测，且不需要
held-out 答案。采用。

### 方案 D：现在关闭 DeepSeek 候选

它能停止继续花费，但 V2 暴露的是实验预算错误，不是模型质量失败。一次最多 8 calls、
有严格金额停止线的 development 校准仍具有信息价值，因此暂不关闭；若推导预算超过
既有 `$0.10` 门，则自动回到关闭/重新授权决策，不静默抬价。

## 5. 被采用的校准架构

### 5.1 两个 development profile

#### `baseline`

- 使用新的公开合成近期复盘输入，不复用 V2 fixture、case ID、注入 marker 或正文；
- 一次合法 `knowledge.search`；
- 短而完整的 Coach 草稿；
- 一次受控非法 Evaluation 后形成 repair 请求。

它代表当前常规请求形状，不代表平均线上用户。

#### `ceiling`

- 所有内容仍然是公开合成 development 数据；
- 近期 match 投影达到现有合同允许的 10 条；
- Agent Context 接近但不超过 Skill 的 16000 本地 context ceiling；
- 工具批次、知识结果、Coach 草稿和非法 Evaluation 内容均使用现有合同内的有界大值；
- 仍只构造 4 次 Provider 请求，不增加 Agent 迭代或修订能力。

它用于形成可审计的请求 envelope 上界，不是用无意义字符把 Prompt 人工填满。

### 5.2 四个固定阶段

两个 profile 都必须按同一顺序生成：

```text
agent_initial
agent_after_tool
evaluation
evaluation_repair
```

离线构造器必须使用现有 Catalog、Router、ExecutionBoundary、ContextBuilder、AgentLoop、
本地 `knowledge.search`、Secure Evaluation Adapter 和 ReviewHarness。只替换 Provider 的
受控返回，不另写一套“长得像生产”的 Prompt 拼接器。

### 5.3 独立 Usage replay

真实校准时，8 个冻结请求逐个发送，顺序为 baseline 四阶段、ceiling 四阶段：

- 请求正文、tools 和 response contract 与冻结请求相同；
- 校准专用 `max_tokens=64`，只降低无用途的校准输出费用；
- 每个响应只要求被 Provider Adapter 规范化，不解析为 Coach/Evaluation 质量结果；
- SDK retry、Tool retry 和应用 retry 都为 0；
- 任一请求失败、Usage 缺失或身份漂移后立即停止，不补跑；
- 最多 8 次真实调用，必须另行得到用户明确确认。

这里测得的 `input_tokens` 是资源校准证据；校准模型生成的内容不得进入 RAG、Memory、
Prompt 调节、领域分数或简历能力结论。

## 6. 数据与控制流

```text
新的 development fixture/profile
        |
        v
真实生产组装 + 本地受控 Provider
        |
        +--> 4 个 ChatRequest/profile
        |    只冻结 digest、角色、数量、本地长度和合同身份
        |
        v
离线 admission + exact-SHA public CI
        |
        v
再次展示 8-call / 64-output / 64000-token / $0.10 上限
        |
   用户明确确认后才 Key-last
        |
        v
DeepSeek Usage replay（首错停止）
        |
        +--> 每阶段 input/output/latency/cost 安全记录
        |
        v
确定性预算推导器
        |
        +--> 可达且 <= $0.10：允许设计全新 V3 held-out
        |
        +--> 不可达或 > $0.10：停止并回到候选关闭/重新授权决策
```

## 7. 预算推导规则

下面的公式在看到任何 V3 held-out 正文前冻结。令阶段集合：

```text
S = {agent_initial, agent_after_tool, evaluation, evaluation_repair}
```

对每个阶段 `s`，取两个 development profile 中较大的真实 Provider input Usage：

```text
observed_input_s = max(baseline_input_s, ceiling_input_s)
stage_input_ceiling_s = round_up_256(observed_input_s * 1.25)
```

然后：

```text
case_input_ceiling  = sum(stage_input_ceiling_s for s in S)
case_output_ceiling = 4 * 1024
case_token_limit    = round_up_1024(case_input_ceiling + case_output_ceiling)

domain_token_limit  = 3 * case_token_limit
global_token_limit  = 1428 historical protocol tokens + domain_token_limit
```

即使多数案例不触发 repair，也按四阶段计算单例上限；未使用的第四次只是剩余上限，不会
被记作实际消耗。

金额使用 ADR-0018 已冻结的 DeepSeek V4 Pro 实验单价，并分别计算 input/output，不能把
所有 Token 当成同一种价格：

```text
case_cost_ceiling =
  case_input_ceiling  * 1.32 / 1_000_000
  + case_output_ceiling * 3.96 / 1_000_000

global_cost_ceiling = round_up_cent(
  0.00221496 historical protocol cost
  + 3 * case_cost_ceiling
)
```

若 `global_cost_ceiling > $0.10`，不得通过减少科学上需要的 Token 上限来硬塞进停止线；
本门停止并要求新的候选关闭/金额授权决策。若单价证据在真实运行前过期，也必须先更新
价格快照和 ADR，不能沿用旧数字。

延迟不使用平均值掩盖慢调用：

```text
stage_latency_s = max(baseline_latency_s, ceiling_latency_s)
case_latency_limit = round_up_5000(sum(stage_latency_s) * 1.25)
```

前两次 Agent 调用的校准延迟还必须与现有 Skill `timeout_s=30` 单独比较；如果这两次的
带余量总和不可达，V3 不得只改 Dataset 延迟字段来绕过 Skill 超时。

## 8. 25% 安全余量与运行时门禁

25% 只应用于实际测得的 input Usage 和延迟。output 已由每请求 1024 的硬上限覆盖，不再
重复乘系数。为了防止“总 Token 足够、单个请求形状却变大”，V3 运行前还必须检查：

- 当前阶段的本地 `DeterministicContextSizer` 长度不超过 `ceiling` profile 同阶段长度；
- message roles、tools、response contract 和阶段顺序与冻结合同一致；
- 每例仍为 4 calls、三例为 12 calls，repair 最多一次；
- 实际 Usage 在每个响应后结算，超限立即停止；
- 任何 held-out 越界都成为不可变失败结果，不反向修改本轮预算。

这是一套“校准 envelope + 工程余量 + fail-closed”的组合，不宣称能够统计覆盖所有未来
Prompt。若后续 Prompt/Context/Skill/Evaluation 版本变化，必须重新做 development 校准。

## 9. 校准自身的安全预算

下一次真实 development 校准仍是独立实验，而不是无限试跑：

| 项目 | 上限 |
|---|---:|
| Provider/model | `deepseek/deepseek-v4-pro` |
| development profiles | 2 |
| requests/profile | 4 |
| 真实调用总数 | 8 |
| 校准单请求 output cap | 64 |
| 校准 observed token 总上限 | 64000 |
| 校准金额停止线 | `$0.10` |
| SDK/application retry | 0 |
| 失败处理 | 首错停止，不补跑 |

这些数字只是未来校准运行的上限。本设计批不读取 Key、不构造 Provider、不调用模型。

## 10. 数据生命周期与污染边界

- 校准 Dataset/Profile 必须显式标记 `role=development` 和
  `quality_admission_excluded=true`；
- V2 Dataset、fixture、input plan、Context snapshot 和结果全部只读；
- 校准资产测试必须拒绝任何 V2 case ID、marker、fixture digest 或正文复用；
- 真实校准结果首次写入后不可覆盖，只保存白名单元数据；
- 校准失败也要保留，不能修改 profile 后在同一实验 ID 下重跑；
- 只有校准结果、预算裁决、代码和 exact-SHA CI 都公开冻结后，才允许创建新 V3
  held-out；
- V3 held-out 一旦创建，不得用于重新计算上述公式或调整 Prompt/Context。

## 11. 公开记录允许和禁止保存什么

允许保存：

- profile/stage ID、provider、requested/resolved model；
- code/CI/asset/request SHA-256；
- message count/roles、本地长度、tools/contract 是否存在；
- input/output tokens、latency、finish reason；
- request ID 的 SHA-256；
- Decimal 费用、停止码和是否完整。

禁止保存：

- API Key、环境变量值；
- Prompt、response、reasoning、工具或 RAG 正文；
- 原始 request ID、SDK 异常、URL/header；
- V2 或未来 V3 held-out 答案；
- 校准输出的领域评分或“模型质量通过”字段。

## 12. 失败分类

| 失败 | 发生位置 | 处理 |
|---|---|---|
| development 资产/身份漂移 | Provider 前 | `calibration_identity_mismatch`，零调用 |
| 四阶段或角色顺序不完整 | Provider 前 | `calibration_path_incomplete`，零调用 |
| output/result 路径已存在 | Key 前 | 拒绝覆盖，零调用 |
| 当前 SHA 未通过公开 CI | Key 前 | `public_ci_not_verified`，零调用 |
| 调用/Token/金额预留越界 | I/O 前 | 对应 budget stop，停止 |
| Provider/Usage 无法规范化 | 响应处 | 保存安全错误码，首错停止 |
| 8 calls 未全部完成 | 裁决处 | calibration incomplete，不推导 V3 |
| 推导成本超过 `$0.10` | 裁决处 | 不建 V3，回到人工决策 |
| V3 请求超过 ceiling envelope | 未来 V3 I/O 前 | `calibration_envelope_exceeded` |

## 13. 非功能要求

- **安全**：Key-last、输出预留、正文不落库、首错停止；
- **可重复**：所有公式为纯 Decimal/整数运算，舍入方向固定向上；
- **可追溯**：profile、请求、代码、CI、结果和预算裁决均有独立摘要；
- **可维护**：复用现有 Provider/Executor/ledger，不引入第二套 Agent Runtime；
- **诚实性**：本地长度、Provider Usage、推导 ceiling、实际 held-out Usage 分字段表达；
- **成本**：development 校准与未来 held-out 分别授权、分别记账；
- **性能**：记录每阶段延迟，但不从两个样本声称 p95/SLO。

## 14. 后续实现批怎样证明本设计

下一批仍为零外部调用，并可以在一个连贯批次完成离线 TDD、完整门禁、提交、推送和
exact-SHA CI。至少验证：

1. 两个 development profile 都能经真实生产组装形成精确四阶段请求；
2. `ceiling` 的每个扩大字段都来自现有合同边界；
3. 请求捕获和持久化不包含正文或敏感字段；
4. V2 ID/marker/digest/正文复用会失败；
5. 校准 prepare 函数不接收 Provider、Key 或网络客户端；
6. Fake Provider 的 8-call 路径、首错停止、Token/金额越界均受控；
7. 预算推导公式、25% 余量和所有向上舍入有边界测试；
8. 不完整的 7/8 Usage 不能产生 V3 推荐预算；
9. 推导金额超过 `$0.10` 时拒绝继续；
10. 旧 V1/V2 资产和结果仍逐字节可复读；
11. 完整 pytest、两套 RAG、compileall、Harness/secret/tracked-data、dry-run、治理和
    `git diff --check` 全部通过。

公开 CI 成功后，才向用户展示 8-call 校准上限并单独请求真实 development I/O 确认。

## 15. 本批明确不实现

- 不创建校准 Dataset、Provider runner、CLI 或真实结果；
- 不创建或运行 V3 held-out；
- 不修改 V2、Prompt、Context、Skill、Evaluation、Harness 或默认模型；
- 不测 Flash、GLM-5.3、Qwen 或自动模型路由；
- 不进入 5D exit review、5E、5F、5P 或阶段 6；
- 不引入 LangGraph、Pi/Claude Agent SDK、Multi-Agent、前端或新依赖。

## 16. 本设计的验收结论

资源校准采用方案 C：两个公开 development profile 通过真实生产组装形成四阶段请求，
再以最多 8 次、`max_tokens=64` 的独立 Provider replay 收集 Usage。V3 预算使用逐阶段
最大 input、25% 工程余量、四次 1024 output 硬上限和固定向上舍入推导；推导成本超过
`$0.10` 或任一阶段不可达时停止，不创建 held-out。当前 Provider 调用数为 0。
