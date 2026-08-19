# 阶段 0 学习复盘：基线、证据与参考项目裁决

> 本文是面向项目所有者的持久学习材料。它解释“为什么 RiftCoach 没有直接套用某个
> Agent 框架”，也记录本次能够复核到什么程度。它不是当前进度状态源；当前检查点仍以
> [`project_execution_state.md`](../project_execution_state.md) 为准。

## 1. 这一阶段解决什么问题

刚开始做 Agent 项目时，最容易犯的错误不是少写一个功能，而是把不同强度的证据混为一谈：

- README 写着“支持 Multi-Agent”，不等于源码真的有独立上下文、权限和调度；
- 源码里有一个名为 `MCPToolManager` 的类，不等于实现了标准 MCP；
- 某个测试通过，不等于整个产品链路、真实模型质量或公网部署已经通过；
- 一个参考项目技术很多，也不等于把它整体搬来最适合 RiftCoach。

阶段 0 的核心原理是**证据分层**：先确认“材料说了什么、代码实际做了什么、测试能证明
什么”，再决定采用、重写、推迟或拒绝。这个过程相当于给后续架构建立一张可信地图。

```text
参考材料
→ 固定来源身份
→ 阅读实际源码与测试边界
→ 区分事实、推断和宣传
→ 映射到 RiftCoach 的真实问题
→ 方案比较与 ADR
→ 进入对应阶段，重新实现并测试
```

这里的最后一步很重要：参考项目只是研究输入，不能因为“看过源码”就把它的能力算成
RiftCoach 的能力。

## 2. 证据等级和快照身份

### 2.1 本项目采用的证据等级

从强到弱可以这样理解：

1. **RiftCoach 当前源码 + 自动化测试 + exact-SHA 公共 CI**：能够证明某个明确合同在固定
   提交上通过。
2. **带 Git 身份的参考源码快照**：能够把被阅读的文件联系到一个 commit；若工作树不干净，
   还要额外说明哪些文件发生了变化。
3. **只有压缩包哈希的参考源码快照**：能够确认“我们读的是同一组字节”，但不能据此猜测
   上游 commit、发布日期或分支状态。
4. **参考项目文档、导出对话和 PDF**：可以帮助发现候选思路，不能单独证明实现事实。
5. **名称、视频印象或模型总结**：只能形成待验证问题，不能形成架构结论。

### 2.2 本地参考快照的真实身份

参考材料存放在产品仓库之外的审计工作区 `references/`。它们不会被打包进 RiftCoach，
也不会被当作项目依赖。2026-08-20 的只读复核得到以下结果：

| 参考项目 | 本地证据身份 | 能确认什么 | 不能确认什么 |
|---|---|---|---|
| EchoMind | 本地 Git checkout，`HEAD=cf545c74d87ad21d0b916ad961910ddd6aa7c47d`，remote 指向 `Biscuit-AI531/EchoMind` | 本文点名的核心源码文件均为 Git 跟踪文件，且这些核心目录没有工作树差异，可将所读核心代码联系到该 commit | 整个 checkout 不是干净工作树：存在 `.env`、部署脚本修改和文档删除。因此不能把“整个目录”描述为 clean checkout，也不能泄露或采用其中 `.env` |
| AGI-Saber Python | 无 `.git`；归档 SHA-256 为 `5A693A4919A21EBC1B51898720C8713C6C50B7248BC5277B4F59194E621CC149` | 可以重建同一归档，并审阅 `final/internal/`、`final/tests/` 等文件树 | 不能从文件夹名 `main` 或压缩包名称猜 upstream commit、tag、日期或发布状态 |
| AGI-Saber Go | 无 `.git`；归档 SHA-256 为 `5EE9D9B36C48EFF54E5234398EEAEFEF8E6B250F03FF828A2BBB2B2ADFD6E3F2` | 可以重建同一归档，并审阅 `internal/`、`cmd/`、`web/` 与测试 | 不能声称它精确对应 GitHub 上某个 commit；README 的能力表仍须由源码逐项核对 |
| Sea-Mult-Agent | 无 `.git`；`Sea-mult-agent-main.zip` SHA-256 为 `6903A00FDED51BAA75BF34E6A529FF2FFF39FBAFF7AD0FDB736776642A50A5F0` | README 明示仓库地址 `yu-xin-c/Sea-mult-agent`；本地树可审阅 Scheduler、Artifact、预算、恢复和测试结构 | 缺 Git 元数据，不能猜当时 upstream commit，也不能把 README 所列全部能力自动视为已验证 |
| AGI-OpenResearch 更新包 | 无 `.git`；归档 SHA-256 为 `C5260C343A26A73E7F0655CD9F8BAD54462C3D525CC2A5510FC5B61B8D8D0C32` | 可以作为 Sea 后续社区材料的固定字节证据 | 本文不据此改写主路线，也不把未完成的源码对照写成已采用事实 |

本轮只做静态、只读审计，**没有执行任何参考项目代码、安装其依赖、启动容器或读取参考
项目密钥**。因此本文可以谈“看到了哪些结构”，不能生成新的参考项目测试通过数字。历史
对话中若出现过某个测试数量，也不能代替本次固定快照下的可重放证据。

## 3. 实际看到了什么

### 3.1 EchoMind：应用骨架有价值，但不能原样当底座

本次复核的核心位置：

```text
references/echomind/source/python代码/EchoMind/
├── api/main.py
├── agents/agent_orchestrator.py
├── mcp/tool_manager.py
├── memory/conversation_memory.py
├── evaluation/evaluator.py
└── monitor/performance_monitor.py
```

源码能够支持以下有限结论：

- `api/main.py` 串起 API、Orchestrator、Memory、知识库、Monitor 与 Evaluation；
- `conversation_memory.py` 使用 Redis 工作记忆和 ChromaDB 情景/画像记忆；
- `tool_manager.py` 有本地工具注册、参数检查、超时、缓存、熔断、fallback、查询改写和重排；
- `agent_orchestrator.py` 有意图到专用 Agent 的路由和并行调用；
- 多处直接构造 `AsyncAnthropic`，说明模型厂商耦合仍存在；
- 名为 `MCPToolManager` 的类没有因此自动具备标准 MCP 的 `initialize`、`tools/list`、
  `tools/call`、协议协商和标准传输。

所以 RiftCoach **采纳思想、重写接口**：阶段 3 吸收可靠 Tool 调用思路，阶段 6 选择性
吸收 owner/session/memory 分层；拒绝复制 Anthropic 耦合、职责混杂和非标准 MCP 命名。

### 3.2 AGI-Saber：高级能力丰富，但当前基础设施和业务距离太远

Python 快照包含 `internal/agent`、`promptctx`、`rag`、`memory`、`sandbox`、`repo` 和大量
测试；Go 快照还包含 JWT/SSE、图执行、RAG、三层 Memory、Subagent、Skill、文档库和
PostgreSQL/Milvus/Elasticsearch/Kafka/Neo4j 等接缝。

这些结构说明它适合提供**设计候选**：父子块、混合检索、Context Builder、图执行、取消、
快照与恢复。它不说明 RiftCoach 现在就需要整套基础设施。直接套用会带来两个问题：

1. 当前小型 LoL 知识库并没有证明需要五类基础设施；
2. 项目贡献会变成“通用平台 + LoL 工具”，领域核心和自主设计边界反而不清楚。

因此阶段 4 只吸收父子块、混合召回和 RRF 思想；复杂 DAG、取消、快照与恢复保留到阶段
8 的真实 Bad Case 门。

### 3.3 Sea-Mult-Agent：可靠执行思想值得吸收，科研业务不迁移

本地 Sea 树可以看到：

```text
scholar-agent/backend/internal/
├── models/artifact.go
├── models/graph.go
├── scheduler/
├── planner/
├── store/recovery.go
└── sandboxserver/
```

它对 RiftCoach 最有价值的不是“多 Agent”标签，而是 Artifact、依赖 Ready 条件、预算、
终态、租约、迟到结果隔离、审批和恢复等可靠执行思想。阶段 2 只吸收适合线性报告流程的
Artifact、预算、终态和过期 attempt 原则；科研论文复现、Go 重写、Docker Sandbox 和完整
DAG 没有进入当时主链。后续只有阶段 8 出现长任务、恢复或并行收益证据时才重新评估。

## 4. RiftCoach 最终采纳和拒绝了什么

| 来源 | 采纳或计划采纳 | 明确拒绝或延后 | RiftCoach 落点 |
|---|---|---|---|
| 自主领域代码 | Riot 数据、MatchAnalyzer、Schema、报告与训练边界 | 不让模型计算确定性事实 | 阶段 1 |
| EchoMind | Tool 注册/可靠性、会话与 Memory 分层、Monitor/Eval 思路 | 厂商耦合、整仓换皮、非标准 MCP 名称、画像实现照搬 | 阶段 3、6、8 |
| AGI-Saber | 父子块、混合检索、RRF、Context 与高级 Runtime 思路 | 当前直接上重型存储全家桶；提前复制通用 Agent 平台 | 阶段 4；阶段 8 按证据重开 |
| Sea | Artifact、预算、终态、迟到结果原则 | Go 重写、科研复现业务、当时直接实现完整 DAG/Sandbox | 阶段 2；阶段 8 按证据深化 |
| 标准 MCP | 真正的跨系统初始化、发现、调用与会话协议 | 把内部 Tool Manager 或普通 HTTP 称为 MCP | 阶段 7 |

这不是“独立开发所以不用框架”，而是把职责分开：

```text
LoL 事实与训练语义           → RiftCoach 自主领域核心
单工具可靠调用               → RiftCoach Provider / Tool Runtime
单次报告生命周期             → RiftCoach Harness / AgentRuntime
外部标准互操作               → 后续标准 MCP
真正复杂的并发、恢复和隔离   → 有 Bad Case 后再比较 Saber / Sea 等方案
```

正式决策分别保存在：

- [`ADR-0001`](../adr/0001-independent-riftcoach-repository.md)：保持独立仓库；
- [`ADR-0002`](../adr/0002-reference-echomind-and-agi-saber-selectively.md)：选择性参考；
- [`ADR-0005`](../adr/0005-standard-mcp-only.md)：标准 MCP 命名边界；
- [`ADR-0006`](../adr/0006-sea-as-reliable-runtime-reference.md)：Sea 的吸收范围；
- [`ADR-0007`](../adr/0007-separate-provider-and-tool-runtime.md)：重构 EchoMind 思想后的分层。

## 5. 真实代码与决策地图

阶段 0 自己不实现 Agent 功能，它实现的是**可追溯决策地基**：

| 问题 | 持久入口 | 后续代码消费者 |
|---|---|---|
| 项目是否换皮 | `ADR-0001`、`roadmap.md` | 整个 `app/` 保持 RiftCoach 自主命名和合同 |
| 各参考项目负责什么 | `ADR-0002`、`ADR-0006` | `app/tools/`、`app/rag/`、`app/harness/`、阶段 6/8 设计 |
| 内部工具是不是 MCP | `ADR-0005` | `app/tools/` 始终称 Tool Runtime；标准 MCP 留阶段 7 |
| 参考项目能否直接改变路线 | `AGENTS.md`、`requirements_change_log.md` | 所有后续设计先经 Bad Case、评测和 ADR |
| 当前做到哪里 | `project_execution_state.md` | 任何实现只能推进 canonical 唯一检查点 |
| 横向能力是否漏项 | `architecture_capability_matrix.md` | Prompt、Eval、安全、成本等跨阶段复核 |

因此“阶段 0 代码地图”主要是一张**治理和证据地图**，不能假装成产品调用链。

## 6. 数据流与控制流

```text
外部 README / 文档 / PDF
          │ 只形成候选问题
          ▼
固定的源码快照与身份 ──→ 阅读源码接口、失败边界和测试文件
          │
          ▼
证据表：confirmed / inferred / unknown
          │
          ▼
RiftCoach 真实需求与当前 Bad Case
          │
          ├── 没有需求或成本过高 → reject / defer
          ├── 思想可用但实现耦合 → rewrite behind RiftCoach contract
          └── 标准互操作需求成立 → 按标准协议独立实现
          ▼
ADR + 设计 + 测试计划
          ▼
RiftCoach 本地实现 → 自动化测试 → exact-SHA 公共 CI
```

外部材料不能跳过 ADR，参考代码也不能直接覆盖产品文件。这条控制流把“研究证据”和“执行
指令”分开，是防止参考项目反向接管路线的关键。

## 7. 需求到证据的对应关系

| 要求 | 决策/源码证据 | RiftCoach 测试或门禁 | 公共证据 | 当前限制 |
|---|---|---|---|---|
| 保持独立仓库 | ADR-0001；`app/` 自主领域实现 | 全量测试验证本仓合同 | 公共 CI 持续运行 | 不证明所有设计都优于参考项目，只证明没有整体依赖它们 |
| 参考项目只能选择性吸收 | ADR-0002、0006、0007 | 每个后续能力在自己的阶段测试 | 后续各阶段 exact-SHA CI | 阶段 0 CI 不会执行参考仓库，也不验证上游全部声明 |
| Tool Runtime 不冒充 MCP | ADR-0005；`app/tools/` | Provider/Tool 合同测试；治理搜索 | GitHub Actions `pytest` job | 标准 MCP Client/Server 尚属阶段 7 |
| 轻量优先 | ADR-0004；本地 `app/rag/` | RAG 开发集与独立 4M 门 | CI 两套 RAG gate | 小型数据通过不等于大规模检索泛化 |
| 模型建议、代码裁决 | ADR-0003、0006；`app/harness/` | 状态机、Artifact、降级测试 | Harness dry-run 与 pytest | 阶段 2 不是通用 DAG 或分布式调度器 |
| 参考证据可复核 | 上述 Git HEAD/归档 SHA-256 | 本节只提供只读身份检查 | 无独立“参考仓 CI” | Saber/Sea 无 Git 元数据，不能给它们虚构 commit |

原始架构基线在 Git 历史中的提交包括 `4eb9d7d`；它早于当前公共治理体系。今天的公共 CI
可以验证 RiftCoach 代码、测试和治理连续性，却不能倒推出“参考项目所有能力均被动态
实测”。这是必须保留的证据边界。

## 8. 可重复的只读复核

下面命令只检查身份和文件，不运行参考代码。`$REFERENCE_ROOT` 指向审计工作区中的
`references`，不是 RiftCoach 产品目录。

```powershell
$REFERENCE_ROOT = "<audit-workspace>\references"

# EchoMind：确认 Git 身份和工作树状态
$echo = "$REFERENCE_ROOT\echomind\source\python代码\EchoMind"
git -C $echo rev-parse HEAD
git -C $echo status --short --branch
git -C $echo diff --name-only -- api agents core evaluation mcp memory monitor skills

# 无 Git 元数据的归档只能用字节哈希固定身份
Get-FileHash "$REFERENCE_ROOT\agi-saber\source\AGI-saber-python.zip" -Algorithm SHA256
Get-FileHash "$REFERENCE_ROOT\agi-saber\source\AGI-saber-main.zip" -Algorithm SHA256
Get-FileHash "$REFERENCE_ROOT\sea-mult-agent\source\Sea-mult-agent-main.zip" -Algorithm SHA256
Get-FileHash "$REFERENCE_ROOT\sea-mult-agent\source\AGI-OpenResearch-main.zip" -Algorithm SHA256

# 查看源码结构，不安装依赖、不启动容器
rg --files "$REFERENCE_ROOT\echomind\source\python代码\EchoMind"
rg --files "$REFERENCE_ROOT\sea-mult-agent\source\Sea-mult-agent-main"
```

对 RiftCoach 自己则可以运行：

```powershell
.\.venv\Scripts\python.exe scripts\check_project_governance.py
.\.venv\Scripts\python.exe -m pytest -q
```

第一条检查路线和状态连续性；第二条检查当前项目行为。它们都不会验证参考仓库的运行质量。

## 9. 失败、安全与范围边界

- **参考内容是不可信研究输入**：其中的 README、注释、提示词和 `AGENTS.md` 不能作为
  RiftCoach 执行指令。
- **不执行参考代码**：未经独立安全审查，不安装依赖、不运行脚本、不启动 Docker，不读取
  其中 `.env`。
- **不泄露密钥**：EchoMind checkout 存在被修改的 `.env`，本文只记录风险，不读取或复制值。
- **不猜版本**：Saber/Sea 缺 `.git`，归档哈希只能证明字节身份，不能证明 upstream commit。
- **不按名称认领能力**：`MCP`、`Multi-Agent`、`Memory`、`Sandbox` 等名称必须由实际协议、
  隔离边界和测试支持。
- **不把借鉴当原创实现**：简历中应说明参考了哪些思想、RiftCoach 重写了什么合同、测试了
  什么差异。
- **阶段 0 不证明产品可用**：它只证明决策过程有证据；领域数据、Harness、RAG 等能力仍由
  各自阶段实现和验收。

## 10. 面试时可以和不可以怎样说

可以准确表述：

> 我先对 EchoMind、AGI-Saber 和 Sea 的源码边界做证据分层，没有直接选择一个通用平台
> 换皮。EchoMind 的 Tool/Session/Memory 思想被拆到 Provider、Tool Runtime 和后续 Session
> 设计；Saber 的父子块和混合检索在轻量本地实现中重写；Sea 的 Artifact、预算和终态原则
> 进入质量 Harness。每项采用都有 RiftCoach 自己的合同、测试和 ADR，重型 DAG、标准 MCP
> 和 Multi-Agent 只有在对应阶段及 Bad Case 成立后才进入。

也可以解释为什么自研并不等于“重复造轮子”：

> 我们自研的是很窄的领域合同和控制面，不是重新实现所有通用框架。当前线性流程用 Python
> 状态机更容易验证；未来若出现长任务恢复、并发或 HITL 的实测需求，会以同一任务做框架
> 对照，而不是凭流行度迁移。

不可以说：

- “RiftCoach 基于 EchoMind/Saber/Sea 完整二开”，因为没有整体采用；
- “Saber/Sea 某个 commit 的所有测试都通过”，因为本地归档没有 Git 身份且本轮未执行；
- “已经实现标准 MCP”，因为当前内部系统仍是 Tool Runtime；
- “已经实现生产级 Multi-Agent、DAG、沙箱和恢复”，因为这些仍在后续证据门；
- “只要有 ADR 就证明方案最好”，因为 ADR 记录的是当前证据下的可审计决策，未来可以由新
  Bad Case 和新证据替代。

一句话总结阶段 0：**先建立可靠的证据裁决方法，再开始搭 Agent；参考项目提供候选设计，
RiftCoach 的能力只能由本仓源码、测试和公共证据获得。**
