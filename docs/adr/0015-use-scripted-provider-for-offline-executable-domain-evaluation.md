# ADR-0015：用脚本 Provider 建立离线可执行领域评测

## 状态

已接受

## 日期

2026-08-13

## 背景

ADR-0013 建立了分层领域评测，ADR-0014 冻结了领域实验的 Prompt/Context 身份。但
Batch A Candidate 仍是人工记录的离线观测，只能证明分类器，不能证明 Skill、Agent、
Tool、RAG 与 Harness 的实际控制流。

直接运行真实 Provider 会在本地接线尚未被可执行基线证明前引入费用、随机性和调参污染。

## 决策

Batch C 采用确定性的脚本 Provider 驱动真实本地控制流：

- 所有案例必须先通过 ADR-0014 admission；
- Provider 响应由场景脚本固定，外部调用严格为 0；
- Skill、ContextBuilder、AgentLoop、ToolRuntime、本地混合 RAG、证据构建、
  ReviewHarness 与分层评测器均使用生产实现；
- 新增 `offline_executable` Candidate kind，要求每案例提供安全 provenance SHA-256；
- 注入案例覆盖用户输入和 RAG evidence，两者只持久化布尔检查与摘要，不保存原始运行
  文本；
- 允许 development 基线暴露 unsafe publication，不用修改 Prompt 或伪造终态追绿。

## 备选方案

### 继续人工记录 Candidate

不能证明实际控制流。拒绝作为 Batch C。

### 立即调用真实 Provider

当前无法先排除本地控制流缺陷，也会污染后续比较。推迟到规则冻结后的有限实验。

### Mock 每一个内部组件

会绕过 ToolRuntime、RAG 和 Harness，得到的只是单元测试拼接。拒绝。

## 影响

### 正面

- 零费用、可复现地验证完整本地 Agent 控制流；
- 工具、证据、引用、事实、注入和发布错误可以分层归因；
- 后续真实 Provider 运行有可信的本地基线；
- 可诚实暴露质量门漏判，而不把“生成文本”当作安全成功。

### 负面

- 脚本 Provider 不能代表真实模型能力；
- 合成 canary 不能覆盖未知注入；
- 当前 Evaluation Schema 没有专用注入 issue category，需要独立离线 probe。

### 中性

- 不改变 0-8 阶段、Prompt、两个 Skill、RAG 生产策略或 ReviewHarness 发布权；
- 不创建 held-out，不新增 Provider，不进入 5E；
- 5D-6b 的真实 Provider Bad Case 继续保留在 Batch A development evidence 中。

## 证据

- `docs/plans/2026-08-13-domain-e2e-offline-executable-design.md`
- `docs/adr/0013-adopt-layered-domain-evaluation.md`
- `docs/adr/0014-bind-domain-experiments-to-prompt-context-identity.md`
