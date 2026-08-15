# 阶段 5D：Python 受限 Agent Loop 退出审查

## 1. 结论先行

阶段 5D 通过退出审查，可以进入阶段 5 的下一检查点 **5E AgentRuntime V1**。
阶段 5 本身仍在进行中，5E、5P、5F 均未完成。

这次通过代表 RiftCoach 已经能够把一个确定性选中的 Skill 安全地编译为一次受限
Agent 执行：上下文按任务最小化，工具权限和预算来自 Manifest，模型只能在白名单内
请求工具，实际工具结果才会形成知识证据，草稿必须经过唯一 ReviewHarness 后才能发布。
非法结构化输出、越权、预算耗尽、上下文漂移、Provider 失败和安全评测失败都有明确的
拒绝或确定性降级路径。

这次通过**不代表**：

- 已有真实模型通过完整领域质量门；
- GLM-5.2、DeepSeek V4 Pro 或其他模型已经成为生产默认模型；
- 已实现统一 `run/stream/event/trace/usage` AgentRuntime；
- 已实现 LangGraph、Pi、Claude Agent SDK、Multi-Agent、Memory、MCP 或前端；
- 已证明对未知 Prompt Injection、生产延迟或开放世界请求充分可靠。

当前 GLM-5.2 与 DeepSeek V4 Pro 的领域能力仍是 **unknown / 未准入**。这项限制会被
带入 5E，而不会被改写成模型通过或模型很差。

## 2. 初学者先理解：Agent Loop 和 AgentRuntime 不是一回事

### 2.1 Agent Loop 解决什么

模型一次回答不一定能直接完成任务。它可能先提出：

```text
“我需要查询知识库”
```

系统执行工具后，把观察结果交回模型，模型再继续。这种“模型决定回答或调用工具，
系统执行后再把结果送回模型”的有限循环，就是 Agent Loop。

5D 解决的是：这个循环怎样被 RiftCoach 的 Skill、Context、Tool 和 Harness 约束，不能
因为模型输出看起来合理就绕过权限、预算或发布门。

### 2.2 AgentRuntime 还要解决什么

AgentRuntime 是 Loop 外面更完整的运行壳。5E 将统一回答：

```text
这次运行的唯一身份是什么？
现在进行到哪个事件？
调用了哪些模型和工具？
各用了多少时间、Token 和成本？
为什么停止、降级或发布？
同步 run 与流式 stream 是否遵守同一语义？
```

所以 5D 的产物是“安全可组合的受限执行链”，5E 才把这条链组织成统一、可观察的运行时。
5D 没有提前造一个通用工作流框架，也没有因为 5E 尚未实现而缺少基本的安全终态。

## 3. 5D 完成后的真实数据流和控制流

```text
RouterDecision(selected name + version)
                    │
                    ▼
SkillExecutionBoundary
  校验 Skill 身份、输入合同、run_id、Artifact 内容承诺
                    │
                    ▼
ContextBuilderV1
  只投影当前 Skill 必需事实
  标记 policy / trusted facts / untrusted user & RAG
  必需段超预算即拒绝，可选段只能整段保留或省略
                    │
                    ▼
AgentRunCompiler
  从 Manifest 编译 allowlisted tools、迭代/调用/超时/Context 预算
                    │
                    ▼
AgentLoop
  Provider response ── answer ───────────────┐
       │                                      │
       └─ ToolCall → ToolRuntime → ToolResult │
                            │                 │
                            └─ Tool observation 回到下一轮
                                             │
                    ▼                        │
SkillAgentDraftPreparer ◄────────────────────┘
  只有实际成功的 ToolExecutionRecord 才转换为 KnowledgeEvidence
                    │
                    ▼
ReviewHarness（唯一发布权）
  Evaluator → 允许时有限修订 → 再评测
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      published   degraded   rejected
                    │
                    ▼
SkillTerminalOutputBuilder
  只从 terminal Artifact 真相重建 typed Skill output
```

这里的数据流是 Skill、事实、工具记录、证据、草稿和终态 Artifact 的流动；控制流是
权限、预算、失败和质量门决定下一步能否继续。模型只参与其中有限的决策与文本生成，
不拥有工具执行权和发布权。

## 4. 原始十项功能要求逐项验收

| # | 入口设计要求 | 实现与证据 | 判定 |
|---:|---|---|---|
| 1 | 接受有效 Router + Skill 输入 | `SkillExecutionBoundary` 校验 selected identity、输入模型和内容承诺；两个真实 Skill 有组合测试 | 通过 |
| 2 | 拒绝身份、版本、输入和 Artifact 漂移 | Catalog-backed name/version、run ID、共享 Artifact 编码与哈希校验；篡改测试 fail closed | 通过 |
| 3 | 权限、预算、质量阈值来自声明式合同 | `AgentRunCompiler` 从 Manifest 编译工具与 Loop 预算；`SkillReviewExecutor` 从 quality gate 取得分数和 fallback 策略 | 通过 |
| 4 | 两个 Skill 使用不同最小上下文 | `ContextBuilderV1` 为近期复盘和单局复盘采用不同 allowlist 投影 | 通过 |
| 5 | AgentLoop 可以请求 `knowledge.search` | Fake Provider 与实际 `ToolRuntime` / 本地混合 RAG 的工具往返测试 | 通过 |
| 6 | 实际 ToolResult 才能形成证据 | 共享 evidence converter 只接受成功的 `ToolExecutionRecord`，并检查来源、去重和冲突 | 通过 |
| 7 | Agent 草稿必须进入 Harness | `DraftPreparationStep` 是唯一接缝；Agent 没有直接发布 API | 通过 |
| 8 | typed output 只来自 terminal Artifact | `SkillTerminalOutputBuilder` 读取最终 Manifest 和已验证 Artifact，不信任中间草稿 | 通过 |
| 9 | 非法输出、越权、预算和上下文问题 fail closed | 结构化 Schema、工具白名单、批次原子预检、累积 Context、deadline 和 Provider 错误测试 | 通过 |
| 10 | 评测 Prompt/Context、工具、事实、引用和发布安全 | 版本化 Dataset/Candidate/Result、Evaluation 1.1、development/held-out 生命周期和真实负面实验 | 通过，保留真实模型局限 |

## 5. 非功能要求审查

| 维度 | 5D V1 证据 | 当前边界 | 判定 |
|---|---|---|---|
| 可靠性 | Provider/Tool/Evaluation 失败可降级或拒绝；终态由 Harness 决定 | 不是跨进程恢复或高可用系统 | 通过 V1 |
| 安全性 | 最小上下文、信任标签、工具白名单、严格 Schema、注入 blocking policy、秘密与结果边界 | 未证明未知真实攻击全部可阻断 | 通过 V1 |
| 成本可控 | Skill 的迭代、工具、Context、timeout 预算；实验另有调用/Token/金额停止线 | 没有生产 p50/p95 和稳定真实 Usage | 通过 V1 |
| 可测试性 | Fake Provider、真实本地知识工具、严格结果模型和无网络回归 | Fake 结果不能替代模型质量 | 通过 |
| 框架中立 | 领域合同不依赖 LangGraph/Pi/Claude Agent SDK | 5F 才做 Runtime 候选实验 | 通过 |
| 可观察性 | 已有 run_id、Agent stop、Tool records、Harness Artifact、Usage 和安全错误码 | 信号分散，尚无统一 Trace/Event | 满足 5D，明确交给 5E |
| 性能 | 同步、有限轮数、有限工具调用和 cooperative deadline | 没有生产 SLA，也不能硬抢占同步 SDK 调用 | 有界但未产品化 |

## 6. 为什么“没有领域模型通过”不阻塞 5D

这里必须分清三层：

1. **Adapter 协议能力**：能否把统一消息、结构化输出和 ToolCall 与厂商 SDK 双向转换；
2. **领域模型质量**：模型能否在 RiftCoach 的真实任务里正确选择工具、引用事实并生成
   合格报告；
3. **系统安全终态**：模型失败时，系统是否会阻止不可信内容发布并安全降级。

目前真实证据是：

- Zhipu 和 DeepSeek 都留下了部分低层协议证据；
- 两者都没有获得完整 RiftCoach 领域质量准入；
- 失败路径没有绕过 Harness，安全降级生效；
- 评测系统能够诚实产生 admitted、rejected 或 unknown，而不是为了过关反复调题。

5D 的结构性验收要求第 3 层必须成立，并要求第 1、2 层有可复现实验门；它没有要求
某一家随时间变化的商业模型必须在今天通过。否则内部架构进度会被厂商发布时间、配额、
SDK 响应差异或一次真实调用永久绑住。

因此，领域模型未准入是一个明确的产品限制和未来采用门输入，不是 5D 控制架构缺失。
5E 仍可使用 Fake/确定性路径建立厂商无关 Runtime，同时保持真实 Provider 默认关闭。

## 7. `max_revisions` 的边界裁决

审查发现 `SkillReviewExecutor(max_revisions=...)` 仍是 Harness 运行政策参数，而不是
Skill Manifest 的 Loop budget。这里不在 5D-exit-review 临时改合同，原因是：

- Manifest 已控制 Agent 迭代、工具调用、timeout 和 Context；
- Manifest 的 quality gate 已控制最低分与 deterministic fallback；
- 修订次数属于 Harness 自己的质量闭环政策，既有阶段 2 合同允许调用方显式配置；
- 当前生产入口没有把它暴露为用户可注入参数，实验中使用 `0` 是为了隔离首稿能力。

它不是当前越权漏洞，但 5E 必须把最终采用的 runtime/Harness policy provenance 写入统一
Trace，使“为什么本次允许几次修订”可观察。若以后要让 Skill 单独声明修订预算，需要
新的合同、迁移和 ADR，不能在退出审查里静默扩张 Manifest。

## 8. 跨层验证证据

本次退出审查使用两组相互补充的离线回归：

- 核心执行、Context、Compiler、AgentLoop、真实本地 RAG、Harness、Artifact 和 typed
  output：`173 passed, 34 subtests passed`；
- Provider Adapter、协议门、领域实验、资源/采用控制和生命周期：
  `176 passed, 22 subtests passed`。

其中两个真实 Skill 的组合测试会真实运行本地 `knowledge.search`，但模型由可控 Fake
Provider 代替，所以它证明控制链与数据链，不证明商业模型质量。退出提交还必须通过完整
pytest、两套 RAG 门、compileall、安全边界、Harness dry-run、治理和 exact-SHA 公共 CI。

## 9. 仍然存在且必须诚实保留的限制

- 没有真实 Provider 完成并通过完整的近期复盘领域链路；
- 单局复盘没有真实 Provider 领域质量证据；
- 两个真实模型注入 held-out 因先前首错停止而未执行；
- 当前 development 注入回归只证明已知案例，不代表普遍抗注入；
- DeepSeek 资源 calibration 只有 1 个已发送但未规范化的响应，真实 Usage/费用 unknown；
- 没有生产延迟分布、p50/p95、吞吐、SLA 或稳定成本基线；
- GLM-5.3 普通 API 可用性审计 deferred，Flash 未测试；
- 没有统一事件流、Trace、Usage 汇总和同步/流式 Runtime 表面；
- cooperative timeout 不能硬抢占阻塞中的同步 SDK；
- Session、Memory、MCP、部署和 Multi-Agent 仍属于后续阶段。

## 10. 5E 的精确交接条件

5E 不是重写 5D，而是在现有合同外增加统一运行时。首批设计必须复用：

- 同一个安全 `run_id`；
- `SkillExecutionRequest` 与编译后的 `AgentRunRequest`；
- `AgentRunResult`、Tool execution records、Harness terminal manifest；
- 已有 Provider/Tool/Harness 的停止原因和 Usage；
- 只有 ReviewHarness 能发布的硬约束。

5E 应设计并随后验证：

```text
run(request) -> terminal result
stream(request) -> ordered runtime events -> same terminal result

RuntimeEvent:
  run_started
  context_compiled
  provider_call_started / completed / failed
  tool_call_started / completed / failed
  evaluation_completed
  publication_decided
  run_completed

RuntimeTrace:
  identity + versions + policy provenance
  timing + usage + safe failure taxonomy
  evidence/artifact references, not raw secret bodies
```

进入 5E 后仍然不得自动调用真实 Provider、切换默认模型、加入 LangGraph/SDK 或实现前端。
第一步必须先做初学者设计、审计现有分散信号、比较最小组合方案，再决定实现切片。

## 11. 面试时可以和不可以怎样说

可以说：

> 我把选中的 Skill 编译为 Manifest 约束的 AgentRunRequest，使用 trust-typed Context
> 隔离系统策略、确定性事实与不可信用户/RAG 内容。Agent 只能调用白名单工具，只有实际
> ToolExecutionRecord 能形成引用证据；草稿必须经过 ReviewHarness 的结构化评测和发布门。
> Fake Provider + 真实本地 RAG 的双 Skill 组合回归验证了控制链，真实 GLM/DeepSeek
> 实验则保留了未准入结论，没有把安全 fallback 冒充为模型质量通过。

不可以说：

- 已经实现生产级通用 Agent Runtime；
- 已完成真实模型选型或自动多模型路由；
- GLM 或 DeepSeek 已生成并通过完整教练报告；
- 已证明系统能抵抗所有 Prompt Injection；
- 已接入 LangGraph、Pi、Claude Agent SDK、MCP、Memory 或 Multi-Agent；
- 完整阶段 5 已结束。

## 12. 最终退出判定

5D-entry-design、5D-1 至 5D-7 的原始功能要求、失败边界、测试证据、真实负面实验和
限制均已有可追溯记录。本次审查没有发现必须在 5D 修复的结构性代码缺口；分散的运行
信号已经足以成为 5E 的输入，但尚未被误写为统一 Runtime/Trace。

因此：

- **5D 状态改为已完成**；
- **阶段 5 继续进行中**；
- **唯一下一检查点改为 5E AgentRuntime V1**；
- **当前仍无领域 Provider 准入**；
- **5P Prompt Program V1、5F Runtime/SDK 采用实验和阶段 6 以后能力仍不得提前开始**。
