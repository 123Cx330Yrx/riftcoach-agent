# RiftCoach Agent

RiftCoach 是一个基于 Riot 公开赛后数据的英雄联盟复盘与训练助手。项目坚持“程序计算事实、知识库提供解释依据、模型负责组织表达、独立评测决定是否发布”的设计原则。

## 当前定位

当前版本包含 RiftCoach 独立领域核心、质量门控 Harness、可靠 Tool Runtime、RAG v1、最小 Agent Loop 与 Skill Router 基础。项目没有直接合并 EchoMind 或 AGI-Saber，也尚未实现完整的会话式 Agent 平台。

当前数据分工：

- Riot API：账号、对局详情与时间线事实；
- MatchAnalyzer：补刀、经济、伤害、视野、参团率与死亡时间等确定性指标；
- Data Dragon：英雄、装备、符文和召唤师技能的官方静态中文映射；
- 本地 RAG v1：混合召回、来源过滤、引用证据、拒答和独立保留集门禁；
- 智谱 GLM：依据事实与检索证据生成教练式中文报告；
- 独立评测：检查数字忠实度、证据边界与过度推断，并支持受限修订和再评测。

领域输出使用版本化的 [Player Summary Schema v1.0](docs/summary_schema.md)。短局会保留明细但不计入聚合，Timeline 缺失会显式记录状态而不会被伪装成零事件。

## 当前链路

```text
Riot ID
→ 最近对局与时间线
→ 确定性指标汇总
→ Data Dragon 静态映射
→ Markdown 统计报告
→ 本地知识检索
→ GLM 教练式草稿
→ 独立事实评测
→ 受限修订与再评测
→ 通过后发布
```

## 项目边界

RiftCoach 只分析已经结束的公开赛后数据，不提供实时对局辅助，不读取客户端内存，不追踪隐藏敌方信息，也不自动操作游戏。

动态版本 Meta（英雄胜率、登场率、禁用率、主流出装和符文等）尚未接入。后续计划通过标准 MCP 客户端获取，并与 Riot API 的玩家事实严格分层。

## 本地开发

要求 Python 3.11 或更高版本。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

复制 `.env.example` 为 `.env`，填写本地 Riot API 与智谱 GLM 配置。不要提交 `.env`。

### 当前异步 HTTP / Task 基座（阶段 6A）

仓库现在包含一个显式依赖注入的 FastAPI Adapter：`app.api.main:create_app(...)`，以及
PostgreSQL durable task、owner-scoped 查询、POST 202 入队、独立 polling Worker 的控制面合同。
HTTP 层不直接选择 Skill、拼 Prompt 或调用 Provider。6A-6 已为这个基座补齐默认关闭 CORS、
日志/Secret 脱敏、有限容量、terminal delete 的隐藏与补偿、retention 和安全指标。6A-7 现已在本地
建立 API+Worker+PostgreSQL packaging、真实 Worker composition 和 no-I/O Linux smoke 合同；exact-SHA
公共验证成功前仍不把 6A 标为完成。

这些能力仍不等于正式公网鉴权/HTTPS、Session/Memory、SSE 或自动 lease/reclaim。真实外部 Worker
组合已在 6A-7 本地实现，但 Docker/Compose 公共 CI 成功前不能称为已验证部署；PostgreSQL job 继续是
task 并发与生命周期语义的阻塞证据。

### 本地 Linux package 与进程职责

`Dockerfile` 只包含运行所需的 Python 应用、migration、Skill、Prompt Program、RAG 文档和两个启动脚本，
使用非 root 用户运行；`.env`、本地 cache/run、测试、报告和实验资产不会进入镜像。Compose 的启动依赖是：

```text
PostgreSQL healthy
→ migrate 一次性升级到 Alembic head
→ FastAPI ready
→ production Worker 或 no-I/O smoke
```

先运行不需要 Riot/模型 Key 的 Linux 控制面 smoke：

```powershell
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke up --build --detach --wait --wait-timeout 120 api
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke run --rm --no-deps smoke
docker compose --project-name riftcoach-packaging-smoke `
  --profile smoke down -v --remove-orphans
```

这个 smoke 会通过 HTTP 创建一条合成 task，由独立诊断 Worker 真实 claim，并故意在不访问 Riot/Provider
的前提下写入安全的 `failed/worker_execution_failed`，再通过 HTTP 查询确认。它证明 package、migration、
API、PostgreSQL、claim 和终态回写；不证明 Coach 报告质量。成功的 Application/Runtime/Harness/Artifact
链由离线产品纵向测试单独证明。固定的 Compose project name 会把 smoke 的网络和数据卷与普通本地运行
隔离；脚本本身也只接受 Compose/本机 API 与 PostgreSQL host。不要省略 project name，否则诊断 Worker
可能接触同一 Compose project 中已有的 queued task。

运行真实本地 Worker 前，先在 `.env` 填入 Riot 与当前 Zhipu 产品基线配置，再执行完整预检：

```powershell
python scripts\run_review_worker.py --worker-id worker-1 --check
docker compose --profile runtime up --build
```

`--check` 会验证数据库连接与 Alembic head、Data Dragon、本地 RAG、Skill/Prompt drift、Riot/Provider
配置与构造合同、Artifact 目录，然后在 claim 前退出；它不会额外付费调用模型，也不把“构造成功”冒充
Riot/Provider 凭据或领域质量已经在线验证。缺任一配置只返回 allowlisted 安全码，不会把 queued task
提前变成 running。
当前 Compose 使用显式 local fixed owner，仅供本机演示；它不是公网 Auth。不要把端口 8000 直接暴露到公网。

构建近期对局汇总：

```powershell
python scripts\build_player_summary.py --riot-id "<GAME_NAME>#<TAG_LINE>" --count 10 --queue 420
```

生成确定性报告和 Coach 草稿：

```powershell
python scripts\generate_markdown_report.py --input data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json
python scripts\generate_llm_coach_report.py --summary data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json --rag-top-k 5
```

执行评测与受限修订：

```powershell
python scripts\evaluate_coach_report.py --summary data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json
python scripts\revise_coach_report.py --report reports\riftcoach_coach_report_<GAME_NAME>_<TAG_LINE>.md
```

## Harness v1 单入口

阶段 2 将原先需要人工串联的“检索、生成、评测、受限修订、再评测、发布”组织为确定性状态机。Harness 负责执行顺序、修订预算、Artifact 留存和发布门控；模型只能产生候选内容，不能自行决定报告是否发布。

先使用 `--dry-run` 验证本地闭环。该模式会执行真实的 Summary 校验、本地 RAG、状态机、文件型 Run Store、哈希登记和发布过程，但使用确定性 Fake 替代收费的模型生成、评测和修订调用：

```powershell
python scripts\run_review_harness.py `
  --summary data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json `
  --deterministic-report reports\riftcoach_report_<GAME_NAME>_<TAG_LINE>.md `
  --run-id local_dry_run `
  --dry-run
```

确认 dry-run 后，移除 `--dry-run` 执行真实 GLM 质量闭环：

```powershell
python scripts\run_review_harness.py `
  --summary data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json `
  --deterministic-report reports\riftcoach_report_<GAME_NAME>_<TAG_LINE>.md `
  --publish-score-threshold 85 `
  --max-revisions 1
```

每次运行默认写入 `data/runs/<run_id>/`，其中保存输入、RAG 证据、草稿、每轮评测、修订稿、最终报告和带 SHA-256 的 `manifest.json`。未通过质量门控的 Coach 草稿不会成为最终报告；失败时默认发布确定性报告并标记为 `degraded`，也可以通过 `--no-deterministic-fallback` 改为拒绝发布。

阶段 3 已为模型、RAG、Riot API 和 Data Dragon 建立统一的 Provider / Tool 契约与适配器。Harness 的生成、评测和修订不再访问具体 SDK 的 `choices` 结构，而是统一调用 `llm.chat`；检索统一调用 `knowledge.search`。Runtime 负责 Schema、有限重试、缓存、三态熔断、fallback 和运行指标，Harness 继续只负责任务级状态与发布门控。现有数据构建脚本暂时保持兼容，后续入口可以逐步改用已经注册的 Riot API 与 Data Dragon 工具。

不需要真实玩家数据或模型密钥的完整合成示例：

```powershell
python scripts\run_review_harness.py `
  --summary examples\fixtures\player_summary_demo.json `
  --deterministic-report examples\fixtures\deterministic_report_demo.md `
  --run-id harness_v1_demo `
  --dry-run
```

状态机、Artifact 目录、故障降级和表述边界详见 [Harness v1 使用与原理](docs/harness_v1_usage.md)。Provider、Tool Runtime、EchoMind 迁移边界和 MCP 区别详见 [Provider 与 Tool Runtime 使用说明](docs/provider_tool_runtime_usage.md)。

## 本地 RAG v1

知识文档位于 `data/rag_docs/`。当前实现按 Markdown 标题切块，使用适配中文的词元与双字组合进行本地相关性检索，不依赖向量数据库或外部 Embedding 服务。

```powershell
python scripts\query_rag.py "输局视野分和经济下降应该怎么复盘" --top-k 3
```

阶段 4 RAG v1 已完成并进入维护：包括结构化 Markdown 元数据、父子块索引、BM25、可替换 Embedding 接口、确定性 hashing embedding 基线、RRF 混合召回、证据门控、来源多样性、版本/位置/有效期过滤、冲突处理和 chunk 级 Harness 引用。当前八题开发集结果为 Recall@K 1.0、MRR 1.0、nDCG@K 1.0、无答案误召回率 0.0；阶段 4M 另有独立保留集门禁。

这组问题也参与了初始阈值校准，因此结果只证明当前开发基线可复现，不是独立泛化证明；hashing embedding 也不等同于语义语言模型。独立保留集、abstain 与引用支持门禁详见 [RAG 4M 独立评测门禁](docs/plans/2026-08-04-rag-4m-independent-gate.md)以及 [RAG v1 现状审计与检索基线](docs/rag_v1_baseline.md)。

## Agent Loop 与 Skill Router

阶段 5A 建立了 Provider-neutral 的最小受限 Agent Loop：模型只能通过结构化
`ToolCall` 请求白名单工具，Runtime 返回 `ToolObservation`，循环受迭代次数、
工具次数和停止原因约束。它已用 Fake Provider 和真实 `knowledge.search` 工具验证，
生产 Zhipu Adapter 的最小结构化输出与 Tool Calling 协议已经真实准入；但 GLM-5.2
在一次 recent-form 领域切片中没有形成可交付给 Agent 的统一响应，因此真实领域能力
仍未准入，不能把低层协议通过写成 Coach Agent 已上线。

阶段 5B 建立 `manifest.yaml + SKILL.md + Pydantic I/O` Skill Contract；Catalog
现在包含 `recent-form-review` 与 `single-match-review` 两个真实用户 Skill。单局
合同复用 Player Summary v1.0，并要求目标 match ID 唯一；短局可以审查，Timeline
缺失保持显式未知。阶段 5C-1 至 5C-4 已完成 Router 请求与决策合同、严格 Catalog、
声明式确定性匹配，以及拒绝/排除否决/多候选歧义验收。5C-5 已建立双 Skill
development 与独立 holdout；5C-6 依据唯一设备语义 Bad Case 决定 V1 暂缓 LLM
Router fallback：

```text
用户表达 + 可用 Skill 路由元数据
→ 检查每个候选的必需信号组与排除信号
→ selected / rejected / ambiguous
→ 稳定原因码与可解释证据
```

Router 只选择工作流，不执行 Skill、Tool、Harness 或模型。两个真实候选已有近期、
单局、混合范围歧义、裸 ID 拒绝和域外边界单测。当前开发集为 23/23；规则冻结后的
独立 holdout 为 11/12，唯一失败已原样保留且没有反向调规则。

5D 已把 Skill/Context、AgentLoop、ToolRuntime、本地 RAG 和唯一 ReviewHarness 组合为
受限执行链。5D-7 Batch A/B 建立分层领域评测和 Prompt/Context 语义身份；Batch C 又用
Scripted Provider 在零外部调用下执行 7 个 development 场景，真实验证工具、事实、
引用、用户/RAG 注入与发布门禁。其中一个“评测器漏判注入”场景被实际发布，再由分层
评测标为 `unsafe_publication`。这证明离线实验接线和故障识别，不证明任何真实模型的
领域质量或通用抗注入能力。原理与边界见
[Agent Loop v1](docs/agent_loop_v1.md)、[Skill Contract v1](docs/plans/2026-08-05-skill-contract-v1-design.md)
、[单局 Skill Contract](docs/plans/2026-08-06-single-match-review-skill-design.md)
、[Router 拒绝与歧义验收](docs/plans/2026-08-06-router-rejection-ambiguity-review.md)
和 [5D-7 Batch C 可执行评测设计](docs/plans/2026-08-13-domain-e2e-offline-executable-design.md)。

Batch D 入口审计进一步确认：当前事实 Evaluator 没有看到用户原话、实际 RAG 证据和
信任标签，不能靠增加一个枚举或硬编码 canary 就声称解决 Prompt Injection。项目已用
[ADR-0016](docs/adr/0016-version-injection-evaluation-before-real-provider-comparison.md)
冻结兼容迁移：保留 `coach_evaluation@1.0.0` 历史复现，下一步离线实现 1.1.0 安全
评测合同与不可修订的发布阻断；独立 held-out 和有限真实 Provider 比较必须等新合同与
实验身份冻结后才能进入。该设计尚不是已完成的注入防护或真实模型准入。

## 测试

```powershell
python -m pytest -q
```

Pull Request 和推送到默认分支时，GitHub Actions 会在 Python 3.11 环境重复执行同一测试命令。
CI 还会检查项目治理状态连续性、阶段 4M 独立 RAG 保留集、真实 PostgreSQL 事务/并发，以及不读取
Riot/Provider Key 的 Linux Docker/Compose package smoke。

## 架构路线

- 代码主体：独立 RiftCoach 仓库；
- 应用架构参考：EchoMind 的 Tool、Session、Memory、Monitor 与 Evaluation 思想；
- 高级运行时参考：AGI-Saber 的 Context Builder、父子块检索、DAG、取消、快照与恢复；
- 可靠执行参考：Sea-Mult-Agent 的 Artifact 契约、确定性控制面、预算、租约与事件历史；
- 三个参考项目均按能力迁移，不直接换皮、切换技术栈或整体合并。

完整阶段路线见 [docs/roadmap.md](docs/roadmap.md)，重要决策见 [docs/adr](docs/adr)。

## 版本产物

- `reports/`：本地生成报告和评测中间产物，默认不提交；
- `examples/sample_coach_report.md`：使用合成数据编写的公开展示样例；
- `data/cache/`：Riot API 本地缓存，默认不提交。

## 开源与数据说明

- 仓库不包含 Riot API Key、LLM API Key、`.env` 或本地缓存；
- 公开示例使用合成标识和简化数据，不对应真实玩家；
- 用户自行查询的数据只保存在本地运行目录，除非用户主动选择其他存储方式；
- Riot、League of Legends 及相关商标归 Riot Games 所有。本项目与 Riot Games 没有隶属或背书关系；
- 安全问题请按照 [SECURITY.md](SECURITY.md) 说明私下报告。

本项目采用 [MIT License](LICENSE) 开源。
