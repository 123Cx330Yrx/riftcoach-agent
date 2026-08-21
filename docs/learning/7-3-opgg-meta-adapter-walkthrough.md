# 7-3 OP.GG Meta Adapter 实现后讲解

## 1. 问题与原理

OP.GG MCP“能返回数据”不等于这些数据已经可以安全进入 RiftCoach。远端工具描述、schema
和正文都不可信；动态 Meta 还必须回答来源、取回时间、可使用范围和未知项。7-3 用反腐层
（anti-corruption layer）把外部协议形状翻译成本项目稳定领域模型：协议变化留在 Adapter，
Agent 只看到有界、类型化、带 provenance 的数据。

Riot 与 OP.GG 不是二选一。Riot API/Data Dragon/官方 patch 是玩家、比赛、版本和静态定义的
官方事实层；OP.GG 是聚合 Meta 参照层。后续可把“玩家实际发生了什么”和“大盘当前通常怎样”
并列分析，但不能让 OP.GG 覆盖 Riot 事实，也不能把缺 patch 的 OP.GG 快照强行标成 Riot 当前
patch。

## 2. 设计与实现

传输层使用官方 HTTPS Streamable HTTP endpoint，完成 initialize、initialized notification、
tools/list、tools/call 和本地 close；HTTP 只负责 delivery/session，MCP Client 仍负责协议和目录，
ToolRuntime 仍负责 deadline/retry/cache/breaker/metrics。

OP.GG 目标工具没有 outputSchema，返回自定义 class-like text。Adapter 固定请求字段并只遍历
白名单 AST：指定函数名、参数个数、List 和 scalar Constant。没有 `eval`，任何 Attribute、Import、
嵌套代码或未知节点都拒绝。规范化后的 facts 再检查英雄名、rate、tier、rank、唯一性和数量。

## 3. 代码地图

- `app/mcp/transport.py`：真实 Streamable HTTP transport。
- `app/mcp/client.py`：session/discovery、admitted subset、远端名到本地 ToolDefinition。
- `app/meta/models.py`：`LaneMetaChampionFact`、`MetaEvidence`、provenance/use-case。
- `app/meta/opgg.py`：OP.GG lane-meta 合同与 parser。
- `app/meta/context.py`：Meta evidence 到 ContextSection。
- `app/agent/context.py`：`EXTERNAL_META_EVIDENCE` data-only trust。
- `scripts/run_opgg_meta_smoke.py`：显式真实 smoke 和 body-free result。

## 4. 数据与控制流

```text
OP.GG MCP text
→ MCP envelope/size/session checks
→ allowed ToolDefinition
→ ToolRuntime
→ strict OP.GG grammar
→ typed facts
→ partial MetaEvidence + digest + local expiry
→ optional user-role Context data
→ Skill/Agent/Harness（后续组合使用）
```

远端 raw text 在 parser 后消失；Context 只保存规范化 JSON。`upstream_patch=null` 和
`source_generated_at=null` 是明确未知，不是漏填。`retrieved_at` 是本地取回时间，15 分钟
`expires_at` 是 RiftCoach 使用门。

这条 section 当前是显式扩展，不会自动注入已冻结的 Prompt Program V1。基础 Context descriptor
和历史实验 fingerprint 保持原样；未来把 Meta 接进生产 Runtime 时必须发布新的 Program identity，
不能为追求当前绿灯重写已经使用过的 held-out/资源校准证据。

## 5. 验证证据

- `tests/test_opgg_meta_admission.py`：官方身份和 restricted admission。
- `tests/test_mcp_streamable_http.py`：HTTP/session/notification/JSON/SSE/大小/安全错误。
- `tests/test_mcp_transport.py`：只有 admitted tool subset 进入严格目录快照。
- `tests/test_opgg_meta_adapter.py`：Runtime alias、facts、digest、Context、注入、非法 rate、重复
  rank、schema drift、超限、过期和用途拒绝。
- `tests/test_opgg_meta_smoke.py`：真实 smoke 必须显式执行且结果 body-free。
- `data/evaluation/results/mcp/opgg_meta_product_smoke_v1.json`：真实产品链成功摘要。

小集合测试证明合同，不证明 OP.GG 永久稳定、所有工具均已产品化或建议质量已经通过领域评测。
提交 `64311a1` 的 exact-SHA `pytest`、真实 PostgreSQL 与 Linux package 三 job 已全绿；公共
pytest `1546 passed, 116 skipped`、真库 `164 passed`，7-3 coverage 已置 `complete`。这些证据仍
不外推为全工具、精确 patch/freshness、Riot+OP.GG join、RiftCoach Server 或双向互操作。

## 6. 运行手册

离线聚焦测试：

```powershell
.venv\Scripts\python.exe -m pytest tests\test_mcp_streamable_http.py tests\test_opgg_meta_adapter.py tests\test_opgg_meta_admission.py tests\test_opgg_meta_smoke.py -q
```

真实 smoke 具有外部 I/O，只能在结果文件不存在且明确需要重建证据时执行：

```powershell
.venv\Scripts\python.exe -m scripts.run_opgg_meta_smoke --execute --position top --top-n 3 --output data/evaluation/results/mcp/opgg_meta_product_smoke_v1.json
```

脚本无 `--execute` 会拒绝运行；已有结果拒绝覆盖。正常开发和 CI 不重复调用外部 endpoint。

## 7. 失败、安全与边界

- 不接受 HTTP、redirect、未知 content type、非法/变化 session 或过大 frame；
- 未获准工具受总目录资源门约束，但不注册、不调用，也不阻断获准工具；
- 远端 description 不成为本地 Tool description，raw result 不进入错误或持久文件；
- Meta section 永远 optional、user-role、non-instructional；
- stale evidence、patch 历史用途和 freshness 声明被拒绝；
- 不读取 Key，不调用 Riot/LLM Provider，不写 Memory/Candidate/Plan/Progress；
- 7-3 只产品化 lane-meta；英雄分析、协同、对线和召唤师工具仍需各自 Adapter；
- 7-4 Server 和 7-5 双向互操作尚未实现。

## 8. 面试表述

准确说法：

> 我为 RiftCoach 实现了标准 MCP Streamable HTTP Client 接缝，并真实接入 OP.GG 的只读
> lane-meta 工具。由于上游没有 outputSchema、patch 和生成时间，我没有伪造完整 provenance，
> 而是用安全 AST grammar 归一化为可过期的 partial MetaEvidence，只允许当前快照建议；
> ToolRuntime、Context data-only 和 body-free smoke 都有分层测试。

不能说：

- “已经接入 OP.GG 全部工具”；
- “OP.GG 数据属于当前精确 patch”；
- “已经完成 Riot + OP.GG 两源融合”；
- “已经完成 RiftCoach MCP Server 或双向生产互操作”；
- “一次真实 smoke 证明长期稳定、建议质量或商业再分发合规”。
