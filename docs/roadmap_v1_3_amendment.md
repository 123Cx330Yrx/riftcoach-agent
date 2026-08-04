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
3G Provider Tool Calling 契约与第二 Provider 验证
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

## 3. 3G 多模型边界

第一轮真实验收为：

- GLM；
- 一家协议行为差异明显的第二 Provider；
- Qwen、Kimi 等保留 Capability、配置和 Adapter 扩展点。

第二家必须与 GLM 通过同一套 Tool Calling、结构化输出、错误和领域契约测试。第三家作为扩展性复验，不以 Provider 数量代替架构证据。

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
