# ADR-0011：将 Skill AgentLoop 作为 Harness 的证据化草稿准备步骤

## 状态

已接受

## 日期

2026-08-07

## 背景

阶段 5A 已有受限 `AgentLoop`，阶段 5B/5C 已有两个 Skill Contract 与确定性 Router，
阶段 2 已有负责 Artifact、评测、修订和发布的 `ReviewHarness`。这些组件尚未形成
一条 Skill 执行链。

当前 Harness 使用固定顺序：Retriever 预先检索，Generator 通过 `llm.chat` 单次
生成。AgentLoop 则允许模型动态调用工具。如果直接保留两种检索，Agent 使用的
ToolResult 不能自动进入 `KnowledgeEvidence` 和评测；如果让 AgentLoop 接管质量
流程，又会复制 Harness 的状态和发布门禁。

## 决策

采用单一外层 `SkillReviewExecutor`，并把 AgentLoop 接入为 Harness 的证据化草稿
准备能力：

```text
selected RouterDecision
→ validate LoadedSkill + typed input
→ Context Builder + Skill budgets/permissions
→ AgentLoop + ToolRuntime
→ DraftPreparationResult(CoachDraft + KnowledgeEvidence)
→ existing Harness evaluation/revision/publication
→ typed Skill Output
```

Harness 增加 `DraftPreparationStep` 接缝。现有 Retriever + Generator 由顺序 Adapter
实现该接口；新的 Skill Agent Adapter 使用 AgentLoop，并把真实知识工具结果规范化
为现有 `KnowledgeEvidence`。

Harness 继续是唯一有权产生 `published/degraded/rejected` 终态的组件。AgentLoop
只能产生草稿和执行证据，不能直接发布报告。

本决策不恢复 ADR-0008 中已取消的 Manifest invocation mode，也不创建内部事实
审查 Skill。`EvaluatorStep` 继续按照 ADR-0009 留在 Harness。

## 备选方案

### 给旧 Harness 入口包装 Skill

改动最小，但不会使用 AgentLoop，也没有模型驱动的受限工具选择，不能完成 5D。

### 让 AgentLoop 接管全部 Harness 生命周期

表面更 Agentic，但会复制 Artifact、评测、修订预算和发布门禁，让模型靠近发布
控制面，拒绝。

### 立即采用 LangGraph 或 Agent SDK

当前主要问题是应用合同组合，不是缺少通用图执行器。第三方 Runtime 仍在 5F 用
同一真实切片和评测进行采用实验，当前不采用。

## 影响

### 正面

- 复用现有 AgentLoop、Tool Runtime、KnowledgeEvidence 与 Harness；
- Agent 可以按需调用 Skill 白名单内的知识工具；
- 工具证据能进入引用、评测和 Artifact 链路；
- 发布权仍由确定性代码控制；
- Runtime 框架保持可替换。

### 负面

- Harness 需要一个新的草稿准备接口和兼容 Adapter；
- 必须把 Agent ToolResult 严格转换为 KnowledgeEvidence；
- 需要处理 Agent 无草稿、越权、预算耗尽和证据缺失等新失败路径。

### 中性

- 旧 Retriever/Generator 协议仍可作为顺序 Adapter 的内部依赖；
- 统一 Trace、stream、Session、取消和恢复不在本决策中；
- 真实 Provider Tool Calling 与结构化输出必须通过后续独立准入检查点。

## 安全与失败边界

- Router 非 selected 时不得进入 Executor；
- 权限和预算只来自 Catalog 中已验证的同名同版本 Manifest；
- 用户、RAG 和 Tool 内容不能修改工具白名单或质量阈值；
- Context 或执行预算超限时 fail closed；
- Agent 草稿必须经过 Harness Evaluator；
- Agent、工具、Provider 或结构化解析失败时只能确定性降级或拒绝；
- 不得用新 Agent 路径绕过 citation 校验和事实审查。

## 验证要求

- Fake Provider + 真实 `knowledge.search` 的 evidence-aware draft 测试；
- 越权、重复 ToolCall、预算和 Context 溢出测试；
- Agent ToolResult 到 KnowledgeEvidence 的来源/引用测试；
- 旧顺序 Harness Adapter 的兼容回归；
- 所有 Agent 草稿均经过 Harness 才能形成 terminal Skill Output；
- 真实 Provider 准入前完成结构化输出和 Prompt/Context 领域评测。
