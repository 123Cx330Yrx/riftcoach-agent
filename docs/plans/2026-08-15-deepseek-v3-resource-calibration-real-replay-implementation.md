# DeepSeek V4 Pro development Usage 真实回放实施计划

> **阶段边界：** 本文仍属于 5D-7，不新增或改名子阶段。用户已经明确确认本轮最多
> 8 次真实 DeepSeek V4 Pro development 校准调用；这里的 V3 是第三次领域采用尝试，
> 不是 DeepSeek 模型版本。

## 1. 具体问题

离线批已经用生产组装冻结了 baseline/ceiling 两个 profile 的四阶段请求，也证明了
Fake Provider 下的预算和停止控制。但是 `simulate_resource_calibration()` 故意只接受
带显式标记的 Fake Provider，因此当前没有任何入口能够安全地执行已确认的真实回放。

本批要增加一条很薄的真实执行接缝：它不重新拼 Prompt、不运行 held-out、不评价回答
质量，只把已经冻结的 8 个 `ChatRequest` 逐个交给真实 `DeepSeekProvider`，保存规范化
Usage、延迟、费用和安全停止码。

## 2. 原理

控制面与数据面继续分开：

```text
冻结 development profile
  -> 生产组装重建 8 个请求
  -> 与公开 body-free snapshot 逐项核对
  -> code SHA == exact public CI SHA
  -> 结果路径独占预留
  -> 最后才读取 .env / 构造 Provider
  -> 逐请求真实回放（max_tokens=64）
  -> 首错停止并提交不可变脱敏结果
```

前半段是控制面，负责证明“准备调用的就是公开冻结的那 8 个请求”；后半段是数据面，
负责产生真实 Usage。`provider_construction_authorized=false` 的 no-I/O admission 不会被
偷偷改义，而是由新的 run admission 在用户确认、输出预留和 exact-SHA CI 都满足后
显式升级。

## 3. 本批实现

### Task 1：真实运行合同与不可变结果

**输出：**

- `ResourceCalibrationRunAdmission`：绑定用户确认、8-call 固定边界、no-I/O admission
  和输出身份；
- `RealResourceCalibrationResult`：只保存白名单观测，明确真实外部调用次数和质量排除；
- 不可变输出 reservation：运行前用独占创建预留，成功或失败都不能覆盖重跑。

**测试：**

- 未确认、调用数不是 8、code/CI/请求身份漂移时，在环境和 Provider 前拒绝；
- 结果文件存在或路径越界时，在环境和 Provider 前拒绝；
- 结果 JSON 不包含 API Key、Prompt、response、reasoning、工具/RAG 正文、原始 request ID
  或异常正文。

### Task 2：薄真实回放协调器

**输出：**

- 与 Fake simulation 共用同一个受预算 replay 核心，但用不同结果类型保留证据语义；
- 每请求由共享 ledger 强制替换为 `max_tokens=64`；
- 第 N 次失败只计 N 次外部调用，后续请求不发送；
- Provider 返回的正文只在调用栈内完成规范化，绝不进入公开结果或预算推导。

**测试：**

- 注入一个没有 `is_offline_calibration_fake` 标记的测试 Provider，验证真实协调器 8/8；
- 第 3 次受控失败时只调用 3 次、完成 2 条观察；
- output Usage 超过 64、Usage 缺失、模型身份漂移和调用/Token/金额越界均首错停止；
- Fake simulation 仍拒绝真实 Provider surface，不能削弱原隔离门。

### Task 3：Key-last CLI

**输出：**

- `scripts/run_deepseek_resource_calibration.py`；
- 默认只接受冻结 profile、公开 request snapshot 和受控结果目录；
- `--prepare-only` 可在零 Key、零 Provider 情况下证明身份；
- 真实运行必须同时提供 `--confirm-real-call`、`--confirm-public-ci-success`、精确
  `--public-ci-sha` 和 `--max-calls 8`。

**测试：**

- 事件顺序固定为 output check -> profile/request preflight -> reservation -> environment
  -> Provider -> replay -> immutable commit；
- prepare-only 在 preflight 后直接返回，不预留结果、不读环境、不构造 Provider；
- 任一 preflight/reservation 错误都保持 Key-last；
- 受控 Provider 结果成功和失败都只写安全字段。

### Task 4：本地门禁与公开代码冻结

先运行聚焦测试、相邻回归、完整 pytest、两套 RAG、compileall、Harness dry-run、
tracked-data/SDK boundary、治理与 `git diff --check`。全部通过后提交并推送，再确认
GitHub Actions 对该精确 SHA 成功。

此时只能声称“真实回放入口已公开验证”，不能声称 Usage 已采集。

### Task 5：一次真实 8-call development 回放

只有在 Task 4 的干净精确 SHA 上：

1. 再跑一次 `--prepare-only`；
2. 确认正式结果文件不存在；
3. 最后加载 `DEEPSEEK_API_KEY`；
4. 最多发送 8 个请求，SDK/application retry 均为 0；
5. 任一错误或预算越界立即停止，不补跑；
6. 首次写入真实结果，保留失败结果并禁止覆盖。

### Task 6：预算裁决与公开结果冻结

- 只有 8/8 完整结果才运行 ADR-0026 的纯预算公式；
- 将真实结果和预算裁决分开保存，避免把“采集完成”与“允许建 V3”混为一谈；
- 若总成本超过 `$0.10` 或前两次 Agent 带 25% 余量后超过 30 秒，停止并回到人工决策；
- 更新 canonical state、活动计划、findings/progress、路线历史、能力矩阵和项目决策；
- 再运行完整门禁，提交推送并验证 exact-SHA public CI。

## 4. 本批不实现

- 不创建或运行 V3 held-out；
- 不修改 V2 或重跑任何旧结果；
- 不调 Prompt、Context、Skill、Evaluation、Harness 或 RAG；
- 不接入 Flash、GLM-5.3、Qwen 或模型自动路由；
- 不进入 5D exit review、5E、5F、5P 或阶段 6；
- 不引入 LangGraph、Pi/Claude Agent SDK、Multi-Agent、前端或新依赖；
- 不把 development Usage 当作模型质量、抗注入或产品默认模型证据。

## 5. 验收口径

真实结果只有两种合法终态：

- `completed`：8/8 规范化响应与 Usage 齐全，可以进入纯预算推导；
- `stopped`：保存已经发生的调用与安全失败码，后续请求跳过，不在同一结果身份下重跑。

无论哪种终态，都不能直接准入领域质量。只有完整 Usage、预算裁决、持久化状态和结果
提交的 exact-SHA CI 全部公开冻结后，下一检查点才可能是 V3 held-out 的创建设计。
