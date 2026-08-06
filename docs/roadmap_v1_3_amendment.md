# RiftCoach 路线 v1.3 局部校准

本文件只记录对既有阶段 0-8 路线的增量修正，不增加、删除或重排九个主阶段。

## 1. 决策原则

每项能力以后同时记录：

- 最终目标；
- 当前闭环；
- 下一层深化；
- 高级候选；
- 升级触发条件；
- 最终验收证据。

`V1` 表示首个真实、可测试的闭环，不表示能力上限。高级组件仍必须通过 Bad Case、Eval、成本和运维证据后才能进入生产主链。

## 2. 近期顺序

```text
3G-1 至 3G-3 Tool Calling 契约、能力协商与 Provider Registry
→ 4M RAG 独立评测门禁
→ 5A Agent Loop 教学
→ 5B Skill Contract
→ 5C Skill Router
→ 5D Python 受限 Agent Loop
→ 5E AgentRuntime V1
→ 5P 早期产品纵向切片
→ 5F 第三方 Runtime 采用实验
→ 6A 完整 FastAPI 与 SQL 任务模型
```

原 v1.3 曾把第二 Provider 验证放在 4M 之前。2026-08-04 的后续讨论已调整为：
先冻结 3G-1 至 3G-3，进入 4M 和真实 Skill/Agent 场景；3G-4 至 3G-6 在该场景
形成后再按同一领域评测触发。它们是延后，不是取消。

## 3. 3G 多模型边界

当前唯一真实基线是 GLM。DeepSeek、Qwen、Kimi 等均为候选，尚未锁定第二家。
选择第二 Provider 的触发条件是：出现真实 Skill/Agent 任务后，候选与 GLM 通过
同一套 Tool Calling、结构化输出、错误、质量、延迟和成本评测。第三家只用于验证
扩展性，不以 Provider 数量代替架构证据。

模型能力需要分成三层：启动配置更换默认 Provider、调用方显式选择 Provider、
系统按任务自动路由。Registry 目前只提供前两者所需的内部解析骨架，产品级选择
和自动路由尚未实现；多模型也不等于 Multi-Agent。

3G 声明 Streaming 能力，但完整流式实现可以随阶段 5 产品切片和阶段 6 SSE 消费者逐步补齐。

## 4. RAG 4M 质量门禁

进入依赖 RAG 决策的 Agent Loop 前，补齐：

- 开发集；
- CI 回归集；
- 独立保留集；
- 无答案集；
- 版本冲突集；
- 引用语义支持集；
- 数据集版本和污染记录。

本任务提高评测可信度，不在此时引入 Milvus、Elasticsearch、Neo4j 等重型基础设施。

## 5. Skill Contract 去重

Skill V1 使用：

```text
skills/<skill_name>/manifest.yaml
skills/<skill_name>/SKILL.md
app/skills/models.py
data/evaluation/skills/
```

- `manifest.yaml` 是机器可读的版本、权限、预算和停止契约；
- `SKILL.md` 是任务方法、边界、步骤和示例；
- Pydantic 模型是输入输出 Schema 的唯一代码权威；
- 评测集集中管理，避免每个 Skill 复制一套格式。

## 6. AgentRuntime 演进

V1（阶段 5）：

- `run()`；
- `stream()`；
- 统一输入输出、事件、终止原因、Usage 和 Trace。

V2（阶段 6）：

- `continue_session()`；
- `cancel()`；
- `resume()`；
- 持久状态与 Context Compaction。

V3（按证据进入阶段 8）：

- Fork；
- Steering；
- Background Task；
- Subagent；
- 跨进程事件和 Checkpoint 分支。

## 7. 产品切片

阶段 5 在本地 AgentRuntime 可运行后，增加不依赖临时数据库的早期 API 切片：

```text
POST /reviews/recent
GET /runs/{run_id}
GET /runs/{run_id}/status
GET /runs/{run_id}/report
POST /runs/{run_id}/follow-ups
```

该切片复用现有 Harness Artifact。阶段 6 再加入 SQL、用户隔离、Session、Memory、幂等、恢复、SSE 和完整前端。

## 8. OP.GG 与 Meta

阶段 7 的明确目标包括标准 MCP Client 和 OP.GG MCP 主线接入，但业务层不得依赖 OP.GG 原始字段：

```text
OP.GG MCP
→ OPGGMetaAdapter
→ MetaProvider / MetaEvidence
→ ToolRuntime
→ Skill / Agent
→ Quality Harness
```

实施时仍需验证端点、协议版本、许可和公开部署边界。第一批其他来源只考虑官方补丁和 Data Dragon，不为了形式上的多源同时接入大量网站。

## 9. 阶段 8 双轨

`8-Core` 是必须完成的产品、部署、合规、Eval 和作品集交付线。

`8-Advanced` 至少完成一个高级能力采用实验，包含 Bad Case、实现、对照、消融、成本和 ADR。实验可以得出采用、局部采用或拒绝采用；不预先强制 Multi-Agent、DAG、Agentic Retrieval 或微调上线。

## 10. 当前执行状态

当前仓库已经完成：

```text
3G-1 Tool Calling 内部消息契约
3G-2 Provider 能力协商
3G-3 Provider Registry
4M 独立 RAG 保留集首个门禁
5A 最小 Agent Loop 与真实 knowledge.search 领域切片
5B Skill Contract 与 recent-form-review 样板
5C-1 Skill Router 输入输出契约与三态决策约束
5C-2 Skill Catalog 严格发现、稳定快照与候选投影
5C-3 声明式确定性路由
5C-4 拒绝、排除否决与多候选歧义验收
5C-5-prep-2 single-match-review 第二个真实 Skill Contract
```

4M 当前使用 7 个小型保留案例，结果用于证明门禁机制可运行，不代表检索已经具备充分泛化能力。后续应扩充按知识类型、版本和位置分层的保留集，但不因此引入重型向量基础设施。

5C 的完整原始检查点和当前状态为：

```text
5C-1 Router Contract          已完成
5C-2 Skill Catalog            已完成
5C-3 Deterministic Router     已完成
5C-4 Rejection / Ambiguity    已完成
5C-5 Router Evaluation        进行中；旧单 Skill 开发评测待重建
5C-6 Model Fallback Decision  未正式开始
```

5C 路由旧开发集有 15 个参与校准的小型单 Skill 案例，历史精确匹配率为 `1.0`、
错误选择率为 `0.0`。现在 Catalog 已有两个真实 Skill，旧结果因候选集合变化而
有意过时；它不是独立保留集，也不代表当前双 Skill 自然语言路由已经充分泛化。

源码审计已修正首批 Skill 分类：`recent-form-review` 与 `single-match-review` 是
两个真实用户任务；报告事实审查继续由已经实现的 `EvaluatorStep` 和
`ReviewHarness` 强制执行，不重复包装为内部 Skill。未实现的调用模式合同已取消。
`single-match-review` 已完成，下一步冻结旧单 Skill 开发基线并重做双 Skill
开发集与独立保留集。原 `prep-1` 与 `prep-3` 均在写代码前取消；动态状态以
`docs/project_execution_state.md` 为准。
`3G-4` 真实第二 Provider、`3G-5` 多 Provider Tool Calling 和 `3G-6` 任务级自动
路由暂不作为连续任务；它们要等 Skill 和 Agent Loop 形成真实调用场景后，按同一
套契约和领域评测重新触发。
