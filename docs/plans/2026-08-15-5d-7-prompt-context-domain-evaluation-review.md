# 5D-7 Prompt/Context 与领域端到端评测收尾审查

## 1. 结论先行

5D-7 可以完成，下一检查点可以进入 `5D-exit-review`。

这里的“完成”指 RiftCoach 已经建立并验证一套可复现、可拒绝、可安全归因的
Prompt/Context 与领域 Agent 评测系统。它不代表 GLM-5.2、DeepSeek V4 Pro 或任何其他
真实模型已经获得领域质量准入，也不代表模型生成报告已经达到生产可用水平。

当前真实模型采用结论仍然是：

- Zhipu/GLM-5.2 与 DeepSeek V4 Pro 都有最小协议层证据；
- 两者都没有完成并通过 `recent-form-review` 的真实领域全链路；
- DeepSeek 当前实验已由 ADR-0027 关闭，领域质量保持 `unknown`；
- GLM-5.3 普通 API 尚未正式可用，G53 迁移门保持 deferred；
- Flash/Pro 分层没有准入，也不属于 5D-7 的补考。

负面模型结果没有被改写成成功。5D-7 通过的是“考试制度、考场控制和安全判卷能力”，
不是“某个考生已经考过”。

## 2. 初学者应怎样理解这一层

一个领域 Agent 不是只有模型回答。RiftCoach 当前链路是：

```text
版本化 Skill 与 Context
        |
        v
Provider 产生回答或 ToolCall
        |
        v
AgentLoop 校验权限和预算
        |
        v
ToolRuntime 执行 knowledge.search
        |
        v
只有成功工具记录才能形成 Evidence
        |
        v
Evaluator 检查事实、引用和注入风险
        |
        v
ReviewHarness 决定发布、降级或拒绝
```

5D-7 的任务是为这条链建立同一把尺子。最终文字看起来流畅，不能代替工具调用、证据、
事实检查和发布门禁；反过来，真实模型调用失败但 Harness 正确降级，也不等于整个系统
失效。评测必须指出失败发生在哪一层，并保留 `unknown`，不能把没观测到的 Token、费用、
事实检查或注入检查当成零或通过。

## 3. 原始范围与逐项验收

| 原始目标 | 当前证据 | 判定 | 边界 |
|---|---|---|---|
| 分层 Dataset/Candidate/Result 合同 | `domain_e2e.py`、Schema 1.1/1.2、10 案例离线基线 | 完成 | 小型开发集不能代表生产分布 |
| development/held-out 生命周期 | 角色、污染记录、规则冻结、显式运行确认和不可覆盖结果 | 完成 | 已消费 held-out 不得再次用于调节当前规则 |
| Prompt/Context 实验身份 | Skill、Context、Evaluation、逐案例输入摘要与 SHA-256 绑定 | 完成 | 保存的是 body-free 身份，不是 5E 统一 Trace |
| 真实本地控制流评测 | Scripted/Fake Provider 经过 Skill、AgentLoop、真实本地 RAG、Evaluator、Harness | 完成 | Fake Provider 只证明控制流，不证明模型能力 |
| Tool 选择与执行 | 缺工具、工具失败、批次预算/白名单/重复预检与真实 `knowledge.search` | 完成 | 真实 Provider 的领域工具往返尚未完整通过 |
| Evidence 与引用 | 证据只来自成功 `ToolExecutionRecord`，缺证据/坏引用可分层拒绝 | 完成 | 不宣称所有自然语言引用都能正确识别 |
| 事实质量门 | 合成错误事实、评分、结构化失败和 fail-closed 路径 | 完成 | 真实模型完整报告质量未准入 |
| 用户/RAG Prompt Injection | Evaluation 1.1 data-only 安全上下文、`prompt_injection` blocking issue、不可修订阻断 | 完成（已知攻击集） | 两个真实注入 held-out 因首例停止未执行；未知攻击无普遍保证 |
| 安全发布 | 旧 1.0 开发基线保留 1/7 unsafe publication；1.1 新基线为 0/7 | 完成 | 这是已知 development 场景的回归，不是安全认证 |
| Provider 协议能力 | Zhipu 与 DeepSeek 最小 structured/tool 协议有真实证据 | 部分完成 | 协议通过不等于领域质量通过 |
| 领域模型采用 | GLM-5.2 不准入；DeepSeek 领域门/资源校准停止并关闭 | 不准入，结论完整 | 质量保持 unknown，不作为 5D-7 通过项伪装 |
| 资源、成本与延迟 | pre-I/O ledger、真实 V2 Usage、不可达性裁决、V3 不完整 Usage 的 null 语义 | 完成评测合同 | 没有完整成功链路的 p50/p95 或生产成本 |
| 失败归因与脱敏 | 稳定 `failure_code` + allowlisted nullable `provider_error_code` | 完成 | 旧 V3 细分原因已丢失，永久保持 unknown |

## 4. 关键评测证据怎样解读

### 4.1 离线记录基线

`domain_e2e_v1_offline_baseline.json` 有 10 个受控案例，任务结果与失败分类均为 10/10。
它覆盖 Provider 无响应、工具、证据、引用、注入、质量门、资源和 unsafe publication。
其中故意保留的 unsafe-publication 负例证明评测器能发现已知错误，不证明生产 Harness
当时已经阻断了它。

### 4.2 可执行开发基线

旧 Evaluation 1.0 的 7 个场景真实经过本地 Agent 控制流，保留了 1/7 unsafe
publication Bad Case。Evaluation 1.1 增加最小 data-only 用户/RAG 上下文和不可修订安全
类别后，同一类安全开发场景变为 0/7 unsafe publication，同时任务结果与失败分类保持
1.0。这证明已知缺口被版本化修复，没有覆盖旧证据。

### 4.3 真实 Provider 结果

真实结果只支持以下结论：

- 最小 structured/tool 协议可以工作；
- GLM-5.2 的一次领域链没有形成可交给 Agent 的统一响应；
- DeepSeek 旧 held-out 在并行 ToolCall 合同处被安全拒绝；
- 修复多 ToolCall development 合同后，V2 仍因真实 Prompt 下资源门不可达而停止；
- V3 development Usage calibration 的首请求没有形成规范化响应，Usage 与费用 unknown；
- 所有失败都没有绕过 Harness 发布不受信任报告。

这些证据不能推出“DeepSeek 模型差”“GLM 更好”“Flash 会更合适”或“模型成本为零”。

## 5. 为什么没有真实模型准入仍能完成 5D-7

评测门是 decision gate，不是 pass-only gate。一个合格的采用门必须允许三种结果：

```text
admit     证据满足合同，可以进入下一层
reject    已有观测明确违反合同
unknown   前置失败或观测缺失，不能判断质量
```

如果只有模型通过时阶段才能结束，那么失败后只能不停改 Prompt、调预算、换模型或重复看过
的考题，评测就会退化成追绿工具。当前系统正确保存了拒绝和 unknown，并定义重新采用门，
因此领域模型未准入是有效实验结论，不是要求无限重试的流程漏洞。

## 6. 方案比较

### 方案 A：等待 GLM-5.3，再让 5D-7 完成

优点是可能获得新的真实模型结果。缺点是把项目进度绑定到外部发布时间，也混淆“评测系统
是否完成”和“候选模型是否上市”。拒绝。

### 方案 B：立即测试 Flash 或继续追 DeepSeek Pro

可能更快得到一次成功，但没有新的成本/延迟需求或全新采用身份，容易在已经看过的问题上
追绿，也违反 ADR-0019/0027 的重开条件。拒绝。

### 方案 C：完成 5D-7，模型采用保持未准入并条件化重开

保留全部负面证据，把 G53 和未来 Pro/Flash 对照作为独立 Provider 采用门；先对阶段 5D
整体做退出审查。采用。

## 7. 带入下一检查点的限制

`5D-exit-review` 必须继续核对而不能掩盖：

1. 没有真实 Provider 完成并通过近期复盘领域全链路；
2. 单局 Skill 只有 Fake Provider + 真实本地 RAG/Harness 组合证据，没有真实模型领域证据；
3. 真实注入 held-out 后两例因为首错停止没有执行；
4. 没有完整成功链路的 p50/p95、稳定 Token 和成本基线；
5. GLM-5.2 只是开发基线，不是产品质量默认选择；
6. 统一 run/event/trace/usage 仍属于 5E，当前实验记录不能冒充它；
7. G53 与未来 Pro/Flash 比较必须使用新实验身份、安全错误 provenance、资源可达性和新 ADR。

这些限制可能影响未来是否上线模型生成报告，但不要求推翻已完成的 Context、Evaluation、
Harness 和实验控制面。

## 8. 测试与审查证据

本次收尾审查先运行 5D-7 相关的 Domain E2E、Prompt/Context、Coach Evaluation、
Provider Domain、Adoption 和 Resource Calibration 测试：`130 passed, 4 subtests passed`。

完整本地回归为 `616 passed, 103 subtests passed`；RAG development 与 independent
holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/citation support 也为 1.0；
compileall、Harness SDK/tracked-data 边界、dry-run、治理和差异检查通过。

审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已通过 GitHub Actions run
`31876536179` 的 exact-SHA 公共 CI；公共环境再次通过治理、完整 pytest、两套 RAG、
compileall、Harness SDK/tracked-data 边界和 dry-run，且没有 Key 或 Provider I/O。

## 9. 退出判定

5D-7 的合同、版本身份、离线控制流、已知注入阻断、资源门、失败归因、真实负面结果和
重新采用边界均有可追溯证据。没有 Provider 获得领域质量准入，这一限制已明确保存，且
不会通过修改旧考题或重复调用来掩盖。

因此 5D-7 状态改为 **已完成（模型领域采用未准入，已公开验证）**；阶段 5 和 5D 仍为 **进行中**；
唯一下一检查点改为 **`5D-exit-review`**。该变更不授权读取 Key、调用 Provider、迁移
GLM-5.3、测试 Flash、修改默认模型或进入 5E。
