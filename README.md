# RiftCoach Agent

RiftCoach 是一个基于 Riot 公开赛后数据的英雄联盟复盘与训练助手。项目坚持“程序计算事实、知识库提供解释依据、模型负责组织表达、独立评测决定是否发布”的设计原则。

## 当前定位

当前版本是 RiftCoach 的独立领域核心与 Agentic Workflow 原型，尚未直接接入 EchoMind 或 AGI-Saber，也尚未实现完整的会话式 Agent 平台。

当前数据分工：

- Riot API：账号、对局详情与时间线事实；
- MatchAnalyzer：补刀、经济、伤害、视野、参团率与死亡时间等确定性指标；
- Data Dragon：英雄、装备、符文和召唤师技能的官方静态中文映射；
- 本地 RAG v0.1：指标解释、复盘方法、训练原则与数据边界；
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

## 本地 RAG v0.1

知识文档位于 `data/rag_docs/`。当前实现按 Markdown 标题切块，使用适配中文的词元与双字组合进行本地相关性检索，不依赖向量数据库或外部 Embedding 服务。

```powershell
python scripts\query_rag.py "输局视野分和经济下降应该怎么复盘" --top-k 3
```

这是业务可行性验证版本，不代表正式 RAG 已完成。正式 RAG 将在 Harness 与 Tool Runtime 稳定后补充来源元数据、引用、混合检索、重排与检索评测。

## 测试

```powershell
python -m pytest -q
```

Pull Request 和推送到默认分支时，GitHub Actions 会在 Python 3.11 环境重复执行同一测试命令。

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
