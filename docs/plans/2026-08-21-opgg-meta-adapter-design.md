# 7-3 OP.GG Meta Adapter 设计与准入审计

## 1. 要解决的问题

RiftCoach 已有可靠的内部 Tool Runtime，但在 7-3 前还不能通过官方 OP.GG MCP 获取动态
Meta，也没有一种能同时表达“事实内容、来源、取回时间、上游未知项和允许用途”的稳定
数据形状。直接把远端文本交给 Agent 会混淆协议、可靠性、业务事实与 prompt 信任。

本检查点建立第一条真实外部 Meta 纵向链：官方 Streamable HTTP MCP → 既有 ToolRuntime
→ 严格 lane-meta Adapter → partial `MetaEvidence` → optional data-only Context。

## 2. 官方候选审计

审计身份固定为：

- repository：`https://github.com/opgginc/opgg-mcp`；
- audited repository HEAD：`039904bf655927402c28717c12bb51fe949e2d61`；
- repository license：MIT；
- endpoint：`https://mcp-api.op.gg/mcp`；
- negotiated protocol：`2025-06-18`；
- server：`OP.GG MCP Server / 1.0.0`。

通过项：官方身份、HTTPS Streamable HTTP、标准 initialize、tools capability、session
header、initialized notification、tools/list，以及只读/幂等 lane-meta tools/call。

限制项：LoL 工具无 outputSchema；lane-meta 无 structuredContent、current patch、source
generated time 或 upstream TTL；稳定 quota、底层数据条款和 server-side session expiry
未公开；DELETE 返回 405。裁决是 `admitted_with_restrictions`，而不是 fully trusted 或
deferred。

## 3. 方案比较

1. 业务代码直接 POST OP.GG：代码少，但不是可复用 MCP Client，绕过已有 Runtime；拒绝。
2. 动态任意 JSON/text 进入 Context：接得快，但 schema drift 与注入无法控制；拒绝。
3. MCP Adapter + ToolRuntime + per-tool anti-corruption Adapter：职责分离、可测试、可扩展；采用。

真实目录 Bad Case 进一步决定：全响应先受 byte/tool-count 总门约束，然后只对业务
allowlist 建立严格 schema snapshot。未获准工具永远不注册/调用，也不能以异构 schema
阻断获准工具。

## 4. 组件与代码地图

- `app/mcp/transport.py`：HTTPS-only、no redirect、session header、JSON/SSE、deadline、
  request/response 上限和安全 close。
- `app/mcp/client.py`：initialize 后 notification、获准 catalog snapshot、远端 underscore
  名到本地 dotted alias、固定本地 description、调用仍交给 ToolRuntime。
- `app/meta/models.py`：typed lane fact、provenance/use-case enum、immutable/digest-bound
  `MetaEvidence` 和 expiry gate。
- `app/meta/opgg.py`：OP.GG catalog contract、固定参数、Runtime 调用、安全 AST grammar 和
  partial evidence 构建。
- `app/meta/context.py`：只把规范化 evidence 投影为 optional `meta:` Context section。
- `app/agent/context.py`：新增 `external_meta_evidence` data-only trust；既有 Memory 规则保留。
- `scripts/run_opgg_meta_smoke.py`：显式 `--execute` 的一次真实、body-free 产品 smoke。

## 5. 数据与控制流

```text
McpClientSession.initialize
  -> StreamableHttpMcpTransport POST initialize
  -> POST notifications/initialized
  -> tools/list（总量上限，再选 admitted subset）
  -> ToolDefinition(opgg.lane_meta_champions)
  -> ToolRuntime.execute（一次尝试、deadline、metrics）
  -> tools/call(lol_list_lane_meta_champions)
  -> bounded text
  -> allowlisted AST grammar
  -> LaneMetaChampionFact tuple
  -> MetaEvidence(partial, retrieved/expires, patch=null)
  -> ContextSection(meta:, user, optional, data-only)
```

Riot API/Data Dragon/官方 patch 数据属于独立官方事实层。本批不调用 Riot，也不实现两源
join；后续组合只能按 champion/position/region/queue/patch 等明确键对齐。OP.GG 缺 patch
时不得借用同日 Riot patch 冒充精确绑定。

## 6. 合同与限制

- source 固定 `opgg`，位置只允许 top/mid/jungle/adc/support；
- 最多返回 10 行；rates 必须在 `[0,1]`，tier/rank 类型和唯一性严格；
- 远端 schema/output 发生任何未准入漂移都 fail closed；
- `retrieved_at`/`expires_at` 是本地生命周期，不是上游 freshness；
- partial evidence 只允许 current snapshot recommendation；
- 原始 content、session、描述、错误正文不进入持久结果；
- Meta 不写长期 Memory/Candidate/Plan/Progress，不覆盖 Riot 玩家事实；
- 7-3 的 Meta section 是显式 Context extension，不自动进入已冻结 Prompt Program V1；基础 Context
  descriptor/fingerprint 保持不变，未来生产组合必须单独版本化 Meta-enabled Program，不能重写历史实验；
- 本批不实现英雄分析/协同/对线等其他 17 个 LoL 工具 Adapter，不进入 7-4/7-5。

## 7. 错误与安全

HTTP 非 200、非法 content type、redirect、坏 session、超时、过大 frame、目录/工具 schema
漂移、远端 tool error、非单一 text、AST 额外节点、代码调用、指令式伪英雄名、非法 rate、
重复 rank 和过期 evidence 均有固定错误或使用拒绝。异常不携带 endpoint response body、
session、玩家标识或 secret。

## 8. 验证矩阵

- pure/fixture：Meta model、digest、expiry、allowed use、AST shape、注入和数值边界；
- transport：initialize/notification/list/call/DELETE、JSON/SSE、HTTPS/no redirect、session、大小；
- adjacent：7-1 contracts、7-2 transport、ToolRuntime、Context/Memory Context；
- real smoke：一条产品代码 lane-meta 调用，只持久化 body-free identities/digests/counts；
- full regression：全部 pytest、RAG 两门、Harness dry-run、compileall、governance、Secret/
  tracked-data、YAML、pip 与 diff；
- public gate：同一实现 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke`。

## 9. 外部调用账本

初始 admission window 记录 initialize 1、notification 1、tools/list 3、tools/call 1、DELETE 1。
产品实现期间又执行：一次失败前置 smoke（initialize/list，无 tool call）、一次脱敏目录诊断
（只投影名称/schema 顶层形状）和一次成功产品 smoke（一个 lane-meta tool call）。截至本地
成功 smoke，合计 initialize 4、notification 4、tools/list 6、tools/call 2、DELETE attempt 4；
Riot calls、LLM Provider calls 和 Key reads 均为 0。不得把这些单向调用冒充 7-5 双向互操作。

## 10. 退出条件

7-3 只有在代码/测试/真实 body-free smoke、八维学习证据、完整本地门和实现 SHA 的三项公共
CI 全部成立后才能关闭。关闭后只交接 7-4 prepared/waiting authorization；不自动实现 Server。
