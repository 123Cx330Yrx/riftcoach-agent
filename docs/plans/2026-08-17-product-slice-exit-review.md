# 5P Prompt Program 与早期产品纵向切片退出审查

## 1. 本地结论

5P 的本地退出裁决是 **`close-with-deferred-boundaries`**：原设计的十项功能要求已形成一条
真实可运行、可测试、可复读的本地同步产品切片，没有发现必须留在 5P 修补的结构性代码缺口。

这里的“可运行”有非常具体的含义：一个严格 HTTP 请求可以经过真实的产品编译、Prompt Program
校验、Application Service、AgentRuntime、ReviewHarness、本地 RAG、receipt/Trace/Artifact，
最后再由 Query Service 读回。纵向测试中只有外部 Riot 与 LLM Provider 被 Fake/fixture 替代，
内部产品控制链不是手填结果，也不是 mock 掉所有层。

这里的“关闭”不表示真实模型质量、生产 API、数据库、Session/Memory、鉴权、SSE、前端或公网
部署已经完成。5P-6 的 exact-SHA 公共 CI 成功前，本结论仍是本地结论，canonical 保持 in progress。

逐项证据见 `docs/plans/2026-08-17-product-slice-exit-matrix.md`。

## 2. 5P 实际搭建了什么

在 5P 之前，我们已经有 LoL 数据分析、两个 Skill、受限 Agent Loop、RAG、ReviewHarness 和统一
AgentRuntime，但它们更像一套“内部发动机”。用户不能只提交 Riot ID 就安全地驱动这台发动机，
Runtime Trace 中的 Prompt identity 也还只是标签，没有绑定真实 Prompt/Context/Evaluation 资产。

5P 补上的不是一个页面，而是发动机外面的第一套产品传动系统：

```text
严格 HTTP 请求
→ 产品请求编译器
→ 已验证 Prompt Program
→ 近期复盘 Application Service
→ 唯一 AgentRuntime + ReviewHarness
→ immutable receipt + Trace + manifest + final Artifact
→ 严格 Query Service
→ HTTP run/report 响应
```

它同时解决两件不同的事：

1. **Prompt Program V1**：把 Skill 指令、Context 合同、知识工具、Evaluation 1.1、修订 Prompt
   和校验器视为一个可版本化程序；任何组件漂移但未升级身份都会 fail closed。
2. **早期产品纵切面**：把用户级 Riot ID 请求编译成 Runtime 内部所需的 Skill、输入 Artifact、
   policy 和 run identity，并通过最小 FastAPI 接口消费结果。

## 3. 为什么要分这些层

### HTTP Adapter：翻译网络协议

FastAPI 只应该理解 JSON、路径、状态码、header 和 Markdown media type。它不应该知道该选哪个
Skill、Prompt 怎样组装、Harness 如何评测。否则未来 CLI、网页和 MCP 会各复制一套 Agent 流程。

### Application Service：执行一次产品用例

`RecentReviewApplicationService` 决定顺序：先拿 Summary、验证是否有可分析比赛、生成确定性报告、
编译 Runtime request、调用 Runtime、最后写 receipt。它不决定一份 Agent 草稿能否发布；发布权仍
属于 ReviewHarness。

### Domain Service：只负责英雄联盟事实

`app.lol` 负责 Summary 和确定性报告。它不知道 HTTP、Prompt 或模型。这样同一套 LoL 业务逻辑
可以被 CLI、API 和未来 MCP 重用，并用“CLI 与 app 输出逐字节一致”证明提升模块时没有改语义。

### Product Compiler：把外部意图变成内部可信合同

`POST /reviews/recent` 本身已经说明任务是近期复盘，因此 compiler 不再让自然语言 Router 猜一次。
它从 Catalog 读取精确 Skill，从 Manifest 投影预算/权限，为 Summary 与确定性报告计算真实字节摘要，
再让既有 ExecutionBoundary 做第二次校验。客户端不能伪造 run_id、Skill、Provider、Prompt、policy
或 Artifact digest。

### Prompt Program：保证 Trace 中的 Prompt 身份名副其实

一次 LLM 行为不只由一段 system prompt 决定。Context 信任分层、Skill 指令、工具合同、Evaluation
Schema、repair/revision prompt 都会改变行为。Prompt Program 把这些组件的身份和摘要绑定起来，
Runtime 只有在当前组件与 manifest 完全一致时才记录该 program identity。

### AgentRuntime 与 ReviewHarness：执行与发布控制

Runtime 负责一次受限 Agent run、Tool 调用、Usage、状态和 Trace；ReviewHarness 仍是唯一可以决定
published/degraded/rejected 的地方。5P 没有为了 API 再写一套 Agent 或质量门。

### Receipt 与 Query：查询时重新验事实

receipt 只是 body-free 安全索引，不是报告数据库。Query Service 不会只相信 receipt 的
`report_available=true`，而会重新核对 Trace、Harness manifest、唯一 final-report 记录和真实文件
SHA-256。任何矛盾都返回 `run_integrity_failed`，不会把损坏正文发给客户端。

## 4. 数据流与控制流有什么区别

初学 Agent 时很容易把“数据经过哪些对象”和“谁有权做决定”混在一起。

### 数据流

```text
Riot ID/options
→ Player Summary
→ deterministic report
→ Agent context/tool evidence
→ evaluated final report
→ Artifact/Trace/receipt
→ HTTP response
```

数据流描述内容怎样变形、保存和被复读。

### 控制流

```text
FastAPI validates HTTP
→ Application Service orders the use case
→ Compiler/Program gates identities and policy
→ Runtime controls execution/resources
→ Harness controls publication
→ Query Service controls disclosure
```

控制流描述每个关键决定由谁做。RiftCoach 的安全性主要来自控制权不重复：HTTP 不能跳过
Application，Application 不能绕过 Runtime，Runtime 不能绕过 Harness，Query 不能绕过完整性验证。

## 5. 这为什么已经是 Agent 产品切片，而不只是 RAG 或普通 API

RAG 只负责从本地知识库检索有来源的知识证据；它不是整个 Agent。当前切片还包含：

- Skill/Manifest 决定允许的任务、工具、预算和质量阈值；
- AgentLoop 可以让模型在白名单内调用 `knowledge.search`，并根据 observation 继续生成；
- Context Builder 把政策、用户事实和不可信知识按信任等级装配；
- ReviewHarness 独立评测、受限修订并决定发布或降级；
- AgentRuntime 统一状态、Usage、Artifact 和 Trace；
- Product/API 层把内部 Agent 合同变成用户可调用的用例。

因此“RAG 是 Agent 的一个工具/知识来源”是准确说法；“前面只是在搭 RAG”已经不符合当前仓库事实。

## 6. 测试分别证明了什么

### 单元与合同测试

证明每一层自己的不变量，例如请求不能携带服务器字段、Manifest 漂移必须拒绝、receipt 不能覆盖、
rejected run 不能读取报告。它们擅长定位具体错误，但单独不能证明全链已接通。

### 相邻/组合测试

证明两到数层使用同一个真实合同，例如 Application 调真实 compiler、Prompt composition 构造 secure
Evaluation 1.1、Query 交叉核对真实 Store。它们用于发现“各模块单测都绿，但接缝对不上”。

### no-I/O HTTP 纵向测试

从 TestClient 进入，经过真实 Application、Catalog、Prompt Program、Runtime、Harness、本地 RAG、
receipt/query 后返回。只有外部 Riot/Provider 用 Fake/fixture，因而它证明产品接线、失败门和状态投影，
不证明网络或模型质量。

### 完整回归与横向门禁

- 5P 聚焦：`121 passed, 1 warning`；
- Runtime/Harness 相邻：`166 passed`；
- 完整回归：`884 passed, 1 warning, 110 subtests passed`；
- RAG development 与 independent holdout 的 Recall/MRR/nDCG/abstention/citation 指标均通过，
  no-answer false-positive rate 为 `0.0`；
- compileall、Harness SDK boundary、tracked secret/run-data、dry-run、governance 均通过。

唯一 warning 是 FastAPI TestClient 当前经 Starlette 使用 httpx 的上游迁移提示。它不是业务失败；
当前没有通过屏蔽 warning 或随意降级依赖来制造“全绿”。

## 7. 为什么还不是生产就绪

5P 最重要的诚实边界是：**本地产品切片通过，不等于线上产品通过。**

| 尚未证明 | 为什么重要 | 后续归属 |
|---|---|---|
| 真实 Riot 产品调用 | 网络、区域、限流、Key、上游数据都可能失败 | 阶段 6 产品基础设施 |
| 真实模型 Coach 质量 | Fake Provider 不会暴露真实事实/引用/建议质量、成本和延迟 | 新鲜 Provider 采用门 |
| SQL/事务/崩溃恢复 | file receipt 在 Trace 与 receipt 之间存在 crash gap | 阶段 6/8 |
| Session/Memory/follow-up | 当前一次请求只产生一次复盘 | 阶段 6 |
| 鉴权/限流/CORS/多租户 | 没有这些就不能安全公网开放 | 阶段 6 与部署门 |
| SSE/后台任务/cancel | 当前 POST 同步阻塞 | 阶段 6/8 |
| 正式前端/公网部署 | TestClient 不是部署证据 | 后续横向交付 |
| 生产 p50/p95/成本/SLO | no-I/O 运行时间不能代表生产 | 真实流量后观测 |

## 8. 为什么没有整套接入 EchoMind、Saber、LangGraph 或 SDK

这不是忘记使用框架，而是按技术采用门做出的选择。

- **EchoMind** 给了薄 API、会话边界和可靠工具的参考，但其 Memory、工具管理器和应用骨架不能
  自动证明适合 RiftCoach。5P 只吸收与当前需求对应的分层思想，没有搬入客服代码或伪 MCP。
- **AGI-Saber** 的 DAG、快照、恢复适合复杂长任务；5P 是同步单用例，没有 DAG/恢复 Bad Case。
  提前引入会让我们花成本维护一套当前不消费的 Runtime。
- **Sea/OpenResearch** 主要提供研究流程和多 Agent 职责参考；当前质量门与用例没有需要多个独立
  Agent 互相协作的证据。
- **LangGraph** 适合显式状态图、分支、循环和持久恢复。当前自建 Runtime 已有严格执行/发布/Trace
  合同，5P 只需要产品消费层；迁移框架不能自动提升模型质量。
- **Pi / Claude Agent SDK** 确实可能减少 loop/runtime 维护量，但是否会保留我们现有 Skill、Tool、
  Harness、Trace 和安全错误语义还未知，所以它们在 5F 用同一切片做有界对照，而不是直接替换。

原则不是“永远自研”，也不是“必须用主流框架”，而是：真实 Bad Case → 备选方案 → 同任务评测
→ ADR。只有证据显示外部 Runtime 明显更好，才采用或局部采用。

## 9. 面试时怎样准确表述

可以这样说：

> 我把已有 LoL 数据分析、受限 Agent Loop、RAG 和质量门封装成了一个本地同步产品纵切面。
> HTTP 层只处理协议，Application Service 编排 Summary、确定性报告、typed Skill compiler 和
> AgentRuntime；Prompt Program 用组件 fingerprint 绑定 Skill、Context、知识工具、Evaluation
> 与 Revision 身份。运行后以 immutable receipt、Trace、manifest 和 final Artifact 做交叉完整性
> 校验。测试使用 Fake Provider 但保留真实 Runtime/Harness/RAG 控制链，所以能证明接线与安全
> 降级，不能声称真实模型质量或生产部署已经通过。

如果被追问为什么没用 LangGraph：

> 当前流程的真实复杂度是一个受限 loop 加一个确定发布状态机，并没有持久 DAG、长任务恢复或
> 多 Agent 调度需求。我先把边界和评测做成框架中立合同；5F 再用同一产品切片比较第三方 Agent
> Runtime，只有收益能覆盖迁移和语义损失时才采用。

不要说：

- “已经上线完整 AI 教练”；
- “真实模型报告质量已通过”；
- “实现了生产级分布式 Agent”；
- “使用了 EchoMind/Saber/LangGraph/MCP/Multi-Agent”，因为当前没有这些采用事实。

## 10. 退出与唯一后续

本地审查没有发现 5P 结构性缺口，因此不新增产品代码。正确的关闭顺序是：

```text
5P-6 local exit review
→ commit / push
→ exact-SHA GitHub Actions success
→ final state reconciliation
→ 5P complete
→ 5F-entry-design（只交接，不自动实施）
```

5F 将比较当前自建 Runtime 与 Pi / Claude Agent SDK 对同一受限产品切片的适配价值；它不是多模型
路由、Memory、MCP、Multi-Agent 或阶段 6 的实现阶段。只有用户再次明确继续后才开始。
