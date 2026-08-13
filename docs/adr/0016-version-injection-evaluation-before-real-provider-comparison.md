# ADR-0016：先版本化注入评测，再进行真实 Provider 比较

## 状态

已接受

## 日期

2026-08-13

## 背景

Batch C 的 executable development 基线证明：当 Agent 草稿服从 RAG 中的不可信指令，
而 Evaluator 错误返回 pass 时，ReviewHarness 会按合同发布该草稿；Domain E2E 的独立
canary oracle 才在运行后标记 `unsafe_publication`。

当前 `coach_evaluation@1.0.0` 没有专用注入类别，评测 Prompt 也没有接收用户原话、
实际 KnowledgeEvidence 或信任标签。直接添加关键词扫描只能通过已知测试；原地修改
1.0.0 又会破坏 Batch A-C 已冻结的 Prompt/Context 身份和历史复现。

## 决策

采用版本化的安全评测迁移：

- 保留 `coach_evaluation@1.0.0`，仅用于复现已有证据；
- 后续实现 `coach_evaluation@1.1.0`，输入最小化的确定性事实、待审报告、data-only
  用户请求和实际 bounded KnowledgeEvidence；
- 1.1.0 新增 `prompt_injection` issue，并由确定性 Harness policy 视为不可修订的
  blocking issue，直接降级或拒绝；
- 合成 canary 只作为 development/held-out oracle，不进入生产关键词黑名单；
- 新合同必须产生新的 Prompt/Context snapshot 和 development Dataset，旧的 1/7
  unsafe-publication 基线原样保留；
- development 通过并冻结后才创建独立 held-out；创建不等于运行，首次结果不得用于
  反向调当前规则；
- 只有新评测合同、snapshot 和 held-out 生命周期就绪后，才用新 ADR 选择最多一个第二
  Provider 候选；
- 首次真实比较固定 3 个 held-out 场景，每 Provider 每场最多 4 calls、领域总计最多
  12 calls、SDK retry 为 0、`max_revisions=0`。第二 Provider 另有最多 3 calls 的
  Adapter 协议准入预算。

## 备选方案

### 发布前扫描已知 canary 或关键词

只会硬编码测试答案，无法覆盖语义变体并可能误伤正常文本。拒绝作为生产方案。

### 原地修改 `coach_evaluation@1.0.0`

会让同一版本名代表不同语义，并且仍缺少判断注入所需的来源上下文。拒绝。

### 立即用 GLM 和一个新 Provider 跑 Batch C 案例

当前安全评测合同存在已知漏判，且 Batch C 是已污染的 development 集；真实比较会把
评测缺陷、案例泄漏和模型差异混在一起。推迟。

## 影响

### 正面

- 历史证据继续可复现，新安全语义有明确版本；
- Evaluator 获得判断注入所需的最小来源上下文；
- 安全问题不能被高分、普通 revision 或错误 verdict 绕过；
- Provider 比较使用同一冻结合同、数据集和硬预算。

### 负面

- 需要同时维护 1.0.0 兼容路径和 1.1.0 新路径；
- 新 snapshot、development 与 held-out 增加评测资产维护成本；
- 即使 1.1.0 通过已知 canary，也不能证明对未知注入普遍安全。

### 中性

- ReviewHarness 继续是唯一发布控制面；
- 不新增主阶段、Skill、Agent、Provider 或运行框架；
- 统一 Trace、Session、Memory、MCP 和 Multi-Agent 仍在各自既定阶段。

## 证据与后续门

- `docs/plans/2026-08-13-injection-evaluation-and-provider-gates-design.md`
- `docs/plans/2026-08-13-domain-e2e-offline-executable-design.md`
- `data/evaluation/results/domain_e2e_v1_offline_executable.json`
- 下一步只实现 D1：Evaluation 1.1 与 blocking policy 的离线 TDD；不创建 held-out、
  不调用真实 Provider、不接第二 Provider。
