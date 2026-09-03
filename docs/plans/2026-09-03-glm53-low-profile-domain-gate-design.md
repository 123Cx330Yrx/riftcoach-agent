# RQ-222：GLM-5.3 Flash 低思考候选独立领域门设计

## 目标

在不接入产品默认 Runtime 的前提下，验证 RQ-221 的低思考档是否能通过 RiftCoach 现有
`recent-form-review` 的完整 Agent → 知识检索 → Evaluation → Harness 发布链。新门必须和已经
执行过的 GLM-5.3 考卷分离，且先完成离线控制面，再考虑任何真实调用。

## 这次解决什么问题

“无工具请求能完成”与“领域任务能安全发布”是两个不同问题。旧 G53-4/G53-7 的 Dataset 已
被消费，不能通过改输出上限或思考档位再次运行。与此同时，产品代码只接受已登记的
`ModelRuntimeProfile`，低思考候选不能靠伪造一个产品档案进入执行链。

## 采用的架构

- **候选作用域**：新增不可伪造的 `CandidateEvaluationProfile` 绑定；仅评测组合器持有私有
  令牌，普通 Runtime/Worker/产品 Provider 构造继续拒绝候选。
- **共享执行链**：把 Agent 编译、`llm.chat` 和领域预算层需要的字段抽成窄请求策略，继续
  复用现有 Executor、AgentLoop、RAG、Evaluation 和 ReviewHarness，不复制整套协调器。
- **候选 Provider**：仍使用 `ZhipuProvider.from_candidate_profile`；预算包装器在最后请求边界
  强制 `low + 4096`、`temperature=1`、`top_p=0.95`、90/120 秒和 retries=0。
- **新鲜资产**：创建新的 synthetic fixture、三案例 held-out Dataset、V1.1 Input Plan 和
  body-free Context Snapshot；所有 case ID、措辞和注入 marker 都不能复用旧门。

## 资源与质量合同

| 项目 | 低思考候选领域门合同 |
|---|---|
| 协议前置 | 新鲜 G53-3-L，最多 3 次调用 |
| 领域案例 | 3 个：正常复盘、用户数据注入、知识注入 |
| 请求上限 | 每次最多 4096 输出；Agent/LLM 工具 90 秒；传输 120 秒 |
| 调用上限 | 每案例 4 次、全域 12 次；无 retry/recovery/revision；首错停止 |
| Token 墙 | 每案例 24,000、全域 72,000，费用仍记录为 unknown |
| 发布要求 | Agent completed/final response、`knowledge.search`、Evidence、事实/引用/注入检查、Evaluation ≥85、Harness published |
| 回退 | 评测作用域禁用 deterministic fallback；失败只记录安全码 |

这些数字是候选实验边界，不是产品 SLA 或供应商硬上限；任何越界都必须 fail closed，不能
自动放宽或重试。

## 分阶段实施

### 阶段 1：离线评测作用域 TDD

先写测试证明候选绑定需要私有作用域、正常产品解析器不接受它、请求策略不能被调用方升权，
并验证 4096/采样/超时/无回退字段在 Agent 编译、`llm.chat` 和预算包装器之间一致。所有
测试使用 Fake Provider，外部调用为 0。

### 阶段 2：公共 exact-SHA 闭环

提交后跑聚焦测试、相关流/Provider 回归、compileall、治理和公共三 job CI。只有同一 SHA
通过，才允许下一阶段读取 Key；不把 RQ-221 的窄探针结果当作新实现身份。

### 阶段 3：新鲜 G53-3-L 与资产冻结

在同一实现身份上做最多 3 次低思考协议门，独立保存 body-free 回执。协议规则冻结后再
创建新 Dataset、Input Plan、fixture 和 Context Snapshot，并通过 no-I/O admission 交叉核对
所有 SHA；资产创建本身不运行 held-out。

### 阶段 4：一次性领域观察与裁决

收到明确授权后，先做输出路径独占预留，再读取环境和构造候选 Provider；三案例按顺序运行，
第一处 Provider/Agent/安全失败即停止。结果只回答低思考候选在这套领域合同中的表现，之后
另行决定是否进入更高层候选门；在领域、黄金切片、安全/部署/合规证据齐全前不注册为产品。

## 测试与安全验收

- 旧 Dataset、旧 Snapshot、旧回执逐字节可读且不变；新资产与旧资产的 bytes、ID、marker 和
  Context commitment 全部不同。
- no-I/O admission 不读取 `.env`、不构造 Provider、不创建真实结果文件；输出冲突早于 Key。
- Fake Provider 能覆盖完整成功、首错停止、工具/Usage/终态/预算越界和正文脱敏路径。
- 回执只保留 profile/资产身份、调用/Token/延迟/终态/Usage 状态和安全错误码，采用
  create-only；不能出现 Prompt、正文、reasoning、headers、Key、工具参数或完整 request ID。
- 相关聚焦与比例回归、compileall、`git diff --check`、治理及公共 exact-SHA CI 全部通过后，
  才能把下一检查点改成真实领域门决策；本设计本身 provider calls=0。

## 当前指针

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / pending-user-authorization`
