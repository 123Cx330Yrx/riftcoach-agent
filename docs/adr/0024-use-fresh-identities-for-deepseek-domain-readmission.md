# ADR-0024：用新鲜身份重新评估 DeepSeek 领域准入

## 状态

已接受；只授权后续离线合同 TDD，不授权创建正式新 held-out、读取 Key 或真实调用

## 日期

2026-08-15

## 背景

DeepSeek V4 Pro 第一次真实领域 held-out 在首个正常案例暴露多 ToolCall Adapter 边界，
旧 Dataset 1.1.0 随即按首错停止并以 `admitted=false` 不可变归档。ADR-0022 已通过
development TDD 和 exact-SHA CI 证明 Adapter/AgentLoop 可以严格解析、整批预检并顺序
消费多个 ToolCall，但该证据不能让已被开发过程看见的旧考卷恢复新鲜。

项目仍需要回答一个独立问题：修复后的当前代码能否在真实 `recent-form-review`、RAG、
Evaluation 1.1 和 ReviewHarness 中完成正常复盘、抵抗用户注入和知识注入，并安全发布。

## 决策

采用“复用现有控制面、重新冻结全部实验身份”的方案：

1. 旧 Dataset、输入计划、真实协议结果和真实拒绝结果保持只读，不覆盖、不复制改名、
   不重跑；
2. 继续复用 no-I/O admission、薄协调器、预算 Provider、oracle-blind production
   Executor、分层 Evaluator 和唯一 ReviewHarness；
3. 先用 development 合成数据为向后兼容的 input-plan、Prompt/Context 和实验记录合同
   做离线 TDD；该批不创建正式新 held-out；
4. 离线实现和 exact-SHA CI 冻结后，单独创建不同的匿名 fixture、新 Dataset、新输入
   计划和三个实际案例的 Prompt/Context 摘要；创建后不得用于调 Prompt、Adapter、
   Evaluator、Harness 或路由；
5. 新 admission 必须绑定旧协议 bytes SHA、旧拒绝结果 bytes SHA、ADR-0022 修复
   commit/CI、当前 code/public-CI SHA、新 Dataset/fixture/plan/Context SHA 和
   Evaluation/Skill identity；任一漂移都在 Provider I/O 前失败；
6. 新鲜领域门保持每例最多 4 calls、领域最多 12 calls、每例 4000 tokens、领域
   12000 tokens、每请求 1024 output tokens、金额停止线 `$0.10`、SDK/Tool retry 为 0、
   `max_revisions=0` 和首错停止；这些只是未来上限，真实运行仍需单独确认；
7. 历史 3 次协议调用和 1 次失败领域调用必须单独展示；新鲜门不能把历史消耗重置为
   “从未调用”，历史失败调用的 Token/费用继续保持 unknown；
8. 只有三例全部执行并发布、task/failure accuracy 均为 `1.0`、unsafe publication 为
   `0.0`、事实/引用/注入/Evaluation 和资源边界全部通过，才允许领域 `admitted=true`。

## 备选方案

### 重写完整领域门

拒绝。会复制已经验证的 Harness、Evaluator、预算和停止控制，增加新的实验基础设施
风险。

### 直接重跑 Dataset 1.1.0

拒绝。旧案例、输入、marker 和失败位置已经参与开发；重复运行只能作为修复回归，不能
提供新鲜准入证据。

### 复制旧文件并只修改 ID/version

拒绝。标识变化不能消除内容污染，会制造“看似新鲜”的错误证据。

### 立即同时评估 Pro、Flash 和 GLM-5.3

拒绝。当前门只回答 Pro 的领域准入；Flash 分层仍在 5P 后/阶段 6，GLM-5.3 仍按
ADR-0023 的独立可用性/profile/协议/领域门推进。

## 影响

### 正面

- 真实 Bad Case、修复证据和新鲜验收形成连续且不可改写的证据链；
- 不复制第二套 Agent、RAG、Evaluator 或 Harness；
- 新 held-out 不会在合同 TDD 期间参与校准；
- Key-last、预算、首错停止、脱敏和不可覆盖结果继续生效；
- 后续面试可以清楚区分回归测试、held-out、协议准入和领域准入。

### 负面

- 需要兼容旧合同并维护一套新的 Dataset/fixture/plan/Context 身份；
- 在真实调用前至少需要两次公开 CI 冻结：合同实现一次，新考卷资产一次；
- 新鲜三案例仍是小样本，不能证明普遍生产质量；
- 最多再产生 12 次真实领域调用，但当前 ADR 不授权这些调用。

### 中性

- 当前仍处于 5D-7，不进入 5D exit review、5E、5P、5F 或阶段 6；
- 不修改 Prompt、Evaluation 1.1、Skill、RAG、默认模型或 `.env`；
- 不实现真正并发、自动模型路由、Multi-Agent 或第三方 Agent SDK；
- GLM-5.2、GLM-5.3 和 DeepSeek Flash 的既有规划边界不变。

## 参考

- `docs/plans/2026-08-15-deepseek-fresh-domain-adoption-gate-design.md`
- `docs/adr/0013-adopt-layered-domain-evaluation.md`
- `docs/adr/0014-bind-domain-experiments-to-prompt-context-identity.md`
- `docs/adr/0020-use-no-io-admission-and-thin-coordinator-for-domain-heldout.md`
- `docs/adr/0021-correct-heldout-injection-admission-before-execution.md`
- `docs/adr/0022-sequentially-consume-multi-tool-call-batches.md`
- `data/evaluation/results/provider_capabilities/deepseek_v4_pro_adapter_protocol.json`
- `data/evaluation/results/provider_capabilities/deepseek_v4_pro_domain_heldout.json`
