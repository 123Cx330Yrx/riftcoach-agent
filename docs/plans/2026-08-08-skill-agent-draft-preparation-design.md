# 5D-4 Evidence-Aware Agent Draft Preparation 设计

## 1. 结论先行

5D-4 新增 `SkillAgentDraftPreparer`，把已经通过 5D-1/2/3 的
`ValidatedSkillExecution + ContextBundle` 交给现有 `AgentRunCompiler` 与
`AgentLoop`，并将成功的最终文本降格为 `CoachDraft`、将实际
`knowledge.search` 工具结果转换为现有 `KnowledgeEvidence`。

知识证据转换不在 Agent 模块复制。旧 `LocalRagAdapter` 已有单次知识 payload 到
Harness 证据的映射，本轮将其抽成一个纯、可复用、fail-closed 的转换器，旧顺序
Harness 路径和新 Agent 路径共同使用。

本检查点不修改 `ReviewHarness` 控制流，不产生 published/degraded/rejected，不构造
terminal Skill Output，不调用真实 Provider，也不进入 5D-5。

## 2. 初学者理解：草稿和证据为什么必须分开

模型最终回答是一段自由文本。它可以写“我参考了某篇文档”，但这句话本身不能证明
工具真的被调用，也不能证明文档内容就是模型看到的内容。

RiftCoach 因此把一次 Agent 运行拆成两条产物：

```text
Agent final response  → CoachDraft       模型提出的解释
ToolExecutionRecord   → KnowledgeEvidence 代码确认的知识来源
```

只有 `AgentLoop.tool_executions` 中真实存在、工具名正确、执行成功、输出结构合法的
`knowledge.search` 结果才进入证据。模型在 Markdown 中凭空写出的 source ID 不会被
收进证据。

这叫 provenance：结论和它的来源具有独立、可核对的数据链。下一阶段 Harness 会把
两者一起保存和评测，但本阶段只负责可靠地准备它们。

## 3. 三种方案比较

### 方案 A：在 Agent 模块复制 LocalRagAdapter 映射

实现最快，但旧 Harness 与新 Agent 会有两套 citation ID、去重和字段校验规则。任何
一边修复，另一边都可能漂移。拒绝。

### 方案 B：相信模型 final response 中声明的来源

无需解析 ToolResult，但模型可以遗漏、写错或伪造来源，无法形成可审计证据。拒绝。

### 方案 C：共享纯转换器，只消费真实 ToolExecutionRecord

把知识 payload 到 `KnowledgeEvidence` 的映射提取为一个纯函数；旧 Adapter 传一个
payload，新 Agent 传本次运行的一个或多个成功 payload。采用。

## 4. 目标合同

```text
SkillAgentDraftPreparer.prepare(
    execution: ValidatedSkillExecution,
    context: ContextBundle,
) -> AgentDraftPreparationResult
```

结果包含：

```text
draft: CoachDraft
knowledge: KnowledgeEvidence
agent_run: AgentRunResult
```

保留完整 `AgentRunResult` 是为了让 5D-5/5E 以后读取停止原因、Usage 与真实工具执行，
但本轮不创建统一 Trace 或 Artifact。

## 5. 控制流

```text
ValidatedSkillExecution + ContextBundle
                  │
                  ▼
          AgentRunCompiler
 identity / Manifest / budget / tool checks
                  │
                  ▼
             AgentRunRequest
                  │
                  ▼
              AgentLoop
       Fake Provider + real ToolRuntime
                  │
                  ▼
             AgentRunResult
      ┌───────────┴────────────┐
      ▼                        ▼
final response         knowledge ToolResults
      │                        │
      ▼                        ▼
 CoachDraft      shared evidence converter
      └───────────┬────────────┘
                  ▼
     AgentDraftPreparationResult
```

## 6. 共享知识证据转换

新纯转换器接收一个或多个 `knowledge.search` 成功 payload：

1. 验证 provider、abstained、diagnostics、count 与 chunks；
2. 验证每个 chunk 的归因字段；
3. 按工具执行顺序、chunk rank 顺序保留首见顺序；
4. 相同 `chunk_id` 且内容一致时去重；
5. 相同 `chunk_id` 但来源/内容冲突时 fail closed；
6. 去重 source ID；
7. 为最终唯一 chunks 分配稳定 `K1..Kn`；
8. 复用同一格式生成 `KnowledgeEvidence.context`。

没有知识调用时返回 `KnowledgeEvidence.empty()`。有调用但全部拒答时，保留
`abstained=True` 和调用诊断，不把“无答案”伪装成“没有检索”。

## 7. Preparer 成功与失败语义

成功必须同时满足：

- Compiler 成功；
- AgentRunStatus 为 `COMPLETED`；
- stop reason 为 `FINAL_RESPONSE`；
- final response 存在且 content 非空；
- 每个实际知识工具执行成功且 payload 合法；
- 没有当前 V1 不支持的非知识工具执行。

否则抛出 `AgentDraftPreparationError`，错误只包含安全的 stop reason 或工具错误码，
不复制用户内容、知识正文或 Provider 原始异常。

直接最终回答、不调用知识工具是合法路径。它适用于仅需解释确定性事实的情况；其
`KnowledgeEvidence` 为空，不能伪装成使用了 RAG。

## 8. 引用边界

最终 K1..Kn 由真实执行结果在运行后统一分配。当前 Tool Observation 尚未携带这组
运行级 citation ID，因此 5D-4 不修改或猜测模型 Markdown 中的引用。

5D-5 会继续使用 Harness 的 unknown-citation 校验，5D-7 再评测引用覆盖率、支持度和
Prompt 设计。本轮只能声称证据已可审计，不能声称草稿引用质量已经通过。

## 9. 测试如何证明

- 旧 `LocalRagAdapter` 在抽取转换器后保持 K1/source/context 行为；
- 单 payload、多 payload、相同 chunk 去重和冲突 chunk 拒绝；
- 两个真实 Skill 都经过真实 Catalog、Router、ExecutionBoundary、ContextBuilder、
  Compiler 与 AgentLoop；
- Fake Provider 调用真实本地 `knowledge.search`，最终 draft 与 evidence 均来自同一
  AgentRunResult；
- 模型文本声称的虚假来源不会进入 evidence；
- 无工具直接回答得到空 evidence；
- 工具失败、坏 payload、Stopped/Failed、缺少 final response 全部 fail closed；
- 原 AgentLoop、Harness Adapter、RAG 与 ToolRuntime 回归继续通过。

## 10. 当前边界与准确表述

完成后可以说：

> RiftCoach 已实现受限 Skill Agent 的证据化草稿准备：Fake Provider 可以通过真实
> knowledge.search 动态检索，代码只从实际 ToolExecutionRecord 构造
> KnowledgeEvidence，并把最终模型文本作为尚未发布的 CoachDraft。

不能说已经：

- 调用真实 Provider 完成 Tool Calling；
- 把草稿接入 Harness 或发布报告；
- 生成 terminal Skill Output；
- 完成结构化 Provider 输出；
- 证明草稿引用覆盖率或 Prompt Injection 防护充分；
- 完成 AgentRuntime、Trace、Session、LangGraph 或 Multi-Agent。
