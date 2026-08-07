# 5D-2 Context Builder V1 设计

## 1. 结论先行

5D-2 在 `ValidatedSkillExecution` 与未来 `AgentRunRequest` 之间增加一个
provider-neutral Context Builder。它不把所有输入拼成一段长 Prompt，而是先构造
带来源、信任语义、指令权限、必需性和优先级的 `ContextSection`，再按确定性大小
预算保留完整 section，最后渲染为现有 `ChatMessage(system, user)`。

输出是 `ContextBundle`，不是 `AgentRunRequest`。工具白名单、迭代/调用/超时预算的
编译以及 AgentLoop 累积消息检查仍属于 5D-3。

## 2. 初学者理解：Context Builder 到底解决什么

模型看到的每一段文本并不具有相同地位：

- 项目 Policy 和经过 Catalog 校验的 SKILL.md 可以约束模型；
- Riot API 派生数据可以作为比赛事实，但英雄名等字符串仍只是数据；
- 用户请求表达关注点，不能修改工具权限；
- RAG 文档可以解释指标，但不能变成该玩家已经发生的事实，也不能发布命令。

如果把它们直接插值到一个字符串里，代码就丢失了这些区别。Context Builder 的核心
不是“写一个更聪明的 Prompt”，而是先建立机器可检查的上下文中间表示，再确定性
渲染。Prompt 是最终文本；Context Engineering 还包括来源选择、范围投影、信任
分层、预算、裁剪和失败策略。

## 3. 三种方案比较

### 方案 A：继续使用 `compact_summary() + f-string`

改动小，但旧 compactor 仍复制所有 match、excluded 和 failed rows，且没有
trust/source/required/priority。字符串变长后只能按字符截断，无法保证 JSON 和引用
完整，拒绝。

### 方案 B：类型化 section、确定性选择、统一渲染

先保留结构和语义，预算选择只能整段保留或整段丢弃；最后复用 Provider 层已有的
`ChatMessage`。它能独立测试，又不提前创建 Agent 请求，采用。

### 方案 C：立即使用真实 Provider tokenizer 或 LangGraph/Pi Context

真实 tokenizer 更精确，框架也可能提供消息状态，但当前 GLM 尚未完成 5D-6b 准入，
第三方 Runtime 要到 5F 用同一切片对照。现在引入会制造厂商/框架耦合，延后。

## 4. Context 合同

### 4.1 `ContextTrust`

V1 只描述初始上下文：

| trust | 来源 | 可作为指令 | Provider role |
|---|---|---:|---|
| `internal_policy` | RiftCoach 内部规则 | 是 | system |
| `skill_instructions` | 已校验 SKILL.md | 是 | system |
| `deterministic_facts` | Summary / 确定性报告 | 否 | user |
| `user_request` | 用户原始表达与 focus | 否 | user |
| `knowledge_evidence` | RAG citation | 否 | user |

动态 ToolResult 不伪装成初始 section；AgentLoop 继续用现有 `tool` role 和
`tool_call_id` 表示 Observation，5D-3 再做累积大小检查。

### 4.2 `ContextSection`

每段包含：

```text
section_id
trust
source
content
required
priority
instructional（由 trust 推导，调用方不能伪造）
message_role（由 trust 推导）
```

最终渲染为 JSON envelope。即使用户或 RAG 内容包含“忽略系统”“调用 Riot 工具”或
伪造分隔符，它仍位于 `instructional=false` 的 JSON 字符串中。结构分层只能降低
注入风险，不能宣称模型绝对不会受恶意内容影响；5D-7 还要运行注入评测。

### 4.3 `ContextBundle`

Bundle 保存：

```text
run_id
skill_name + skill_version
selected sections
rendered ChatMessages
estimated_tokens
max_context_tokens
omitted_section_ids
```

它使后续 Compiler 能检查“使用了什么上下文、哪些内容因预算被排除”，但统一
Trace/event/usage 仍属于 5E。

## 5. 两个 Skill 的最小事实投影

### 5.1 `recent-form-review`

必需 section：

- 内部 Policy 与本 Skill 的完整已校验指令；
- schema、玩家身份、请求范围和受控 metadata；
- allowlist 后的 `recent_summary` 聚合；
- excluded/failed 的数量与安全边界字段，不复制原始异常文本；
- 完整确定性报告（data-only）；
- 用户表达和 focus（data-only）。

可选 section：

- 输入顺序中的单局 allowlist 投影，最多构造 10 条；
- 初始 `KnowledgeEvidence` 中每个 citation 独立成段。

近期 match 只保留趋势复盘需要的身份、胜负、位置、时长、KDA、发育/伤害/视野/
占比、早期死亡和 Timeline 状态。未知扩展字段不会自动进入模型上下文。

### 5.2 `single-match-review`

必需 section：

- 内部 Policy 与本 Skill 的完整已校验指令；
- schema 和玩家身份；
- 唯一 target row 的 allowlist 投影，包括 short-game、是否进入聚合、Timeline
  status/error、死亡、装备购买和目标事件；
- 用户表达、`target_match_id` 和 focus。

可选 section：

- 确定性报告中包含精确 `target_match_id` 的完整行；
- 初始知识 citation。

不得注入 `recent_summary` 或其他 match row。若报告没有目标 ID 行，target row 仍是
必需事实源，不使用聚合报告替代单局事实。

## 6. 大小估算与确定性裁剪

`ContextSizer` 是可注入协议。默认 `DeterministicContextSizer` 对非 ASCII 字符、
ASCII 文本和结构符号做固定启发式估算，并加入消息开销。它的目标是稳定 preflight，
不是冒充真实 Provider token usage；5D-6b/5D-7 再与真实 usage 校准。

预算算法：

1. 使用已验证 Manifest 的 `max_context_tokens` 作为不可提高的硬上限；
2. 调用方只能传入更低的运行/测试上限；
3. 先渲染所有 required sections，若已超限则 `ContextBudgetError`；
4. optional sections 按 priority 降序、原顺序稳定尝试；
5. 每次只加入完整 section，加入后超限则整段省略；
6. 最终消息再次估算并记录结果；不截断 JSON、Markdown 行或 citation。

AgentLoop 后续加入 Tool Observation 会继续增长消息，因此 5D-2 的“初始上下文通过”
不等于整个运行永远不会超限。5D-3 必须在每次 Provider 调用前复检累积消息。

## 7. 失败与安全边界

- 非 `ValidatedSkillExecution` 不进入 Builder；
- 不支持的 Skill 名称或 typed input 类型立即拒绝；
- 重复 section/citation identity 立即拒绝；
- required context 超预算立即拒绝，不静默删 Policy、Skill 指令或核心事实；
- 单局找不到唯一目标已由 Skill input contract 拒绝，Builder 仍不回退到近期聚合；
- 空白或非法 citation 不作为可用知识；
- 用户、事实和知识文本都不能改变 `instructional`、role、工具权限或预算；
- Builder 不调用 Provider、ToolRuntime、AgentLoop、Harness，也不发布报告。

## 8. 测试如何证明行为

- section trust 自动决定 `instructional` 和 role，调用方不能自报权限；
- 两个真实 Skill 均生成一个 system 与一个 user message；
- 近期只投影 allowlist 字段，最多 10 个 match sections，并保留样本边界；
- 单局只出现 target match，不出现 recent aggregate 或其他 match ID；
- Timeline unavailable 的 `None`、空集合和 error 保持未知语义；
- 恶意用户/RAG/事实字符串只位于 data-only user section；
- 相同输入和 sizer 产生相同消息、顺序和估算；
- optional match/citation 在小预算下整段省略，required 超限 fail closed；
- 传入高于 Manifest 的上限不会扩大预算；
- Builder 不创建 `AgentRunRequest`，测试也不调用模型或工具。

## 9. 完成后的准确表述

可以说：

> RiftCoach 已实现 provider-neutral Context Builder V1，对内部指令、确定性事实、
> 用户请求与知识证据进行类型化分层，并按 Manifest 上限做确定性整段裁剪。

不能说已经：

- 跑通受限 Skill Agent；
- 完成真实 Provider token 精确计数；
- 解决 Prompt Injection；
- 完成 AgentRunRequest 权限/预算编译；
- 完成动态 Tool Observation compaction；
- 生成或发布 Coach 报告。
