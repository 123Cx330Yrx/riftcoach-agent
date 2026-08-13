# ADR-0014：领域实验绑定 Prompt/Context 语义身份

## 状态

已接受

## 日期

2026-08-13

## 背景

ADR-0013 建立了分层领域评测，但 Batch A 的 `ContractSnapshot` 只包含人工版本字符串。
未升版本的 Skill 指令、Context Policy/渲染或 Evaluation Prompt/Schema 变化不会被机器
发现，因此不同输入规则可能被误当成同一模型或 Provider 候选。

5D-7 后续还要进行多案例 Prompt 实验和可能的第二 Provider 对照。评测前必须先冻结
控制变量，同时不能把完整 Prompt、事实或模型原文写入公开结果。

## 决策

采用“组件身份 + 案例 Context 身份”的双层 SHA-256 快照：

- 组件层分别指纹化 Skill Manifest/Instructions、Context Policy、`knowledge.search`
  工具合同、Evaluation Schema/事实投影，以及 Evaluation/repair/revision 的系统指令和
  行为探针；
- 案例层从真实 `SkillExecutionBoundary -> ContextBuilderV1` 构建输入 Artifact、section、
  system/user message 和预算摘要；
- 快照包含自校验 SHA-256，只保存安全标识、元数据和摘要；
- Domain E2E Schema 升至 1.1，Dataset/Candidate/Result 的 `ContractSnapshot` 必须绑定
  Prompt/Context 快照 ID 和摘要；
- 离线 admission 在外部调用前重建当前快照，并同时核对 Dataset 文件身份；漂移即失败。

## 备选方案

### 只依赖人工版本号

无法发现忘记升版本的正文变化。拒绝。

### 只哈希最终消息

不能定位 Skill、Policy、事实和 Evaluation 的变化来源，也会混淆组件与案例变量。
拒绝作为唯一方案。

### 哈希整个 Python 文件或 Git SHA

会把注释和无关重构误判成实验语义变化；Git SHA 也无法说明哪些输入合同实际生效。
拒绝作为语义身份，Git SHA 仍可在后续 Trace 中作为代码 provenance。

## 影响

### 正面

- 后续 Provider/Prompt 比较可以证明控制变量一致；
- 漂移能够定位到组件或 Context section；
- Dataset 与 Candidate 在评测器入口直接强绑定；
- 公开证据不需要保存完整 Prompt 或模型原文。

### 负面

- 有效 Prompt/Context 变化需要显式更新快照和 development Dataset 版本；
- 行为探针只能覆盖其固定调用路径，不能证明所有条件分支都未变化；
- Batch A 的当前 development Schema/版本需要升级并离线重建基线。

### 中性

- 不改变 Prompt 文案、Context Builder 选择逻辑或 Harness 发布权；
- 不调用真实 Provider，不创建 held-out，不接第二 Provider；
- 统一运行 Trace 仍属于 5E。

## 证据

- `docs/plans/2026-08-13-prompt-context-experiment-identity-design.md`
- `docs/plans/2026-08-13-domain-e2e-evaluation-v1-design.md`
- `docs/adr/0013-adopt-layered-domain-evaluation.md`
