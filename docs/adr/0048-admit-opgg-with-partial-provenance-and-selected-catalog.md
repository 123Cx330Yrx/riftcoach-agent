# ADR-0048：以 partial provenance 和获准目录子集接入 OP.GG MCP

## 状态

Accepted（2026-08-21）。本 ADR 修订 ADR-0047 的二元候选准入解释；它准许 7-3
真实接入受限 OP.GG 能力，但不关闭 7-3，也不准入 7-4 RiftCoach MCP Server 或
7-5 双向互操作退出门。

## 背景

官方 `opgginc/opgg-mcp` 仓库指向 `https://mcp-api.op.gg/mcp`。受限真实探针已证明
该 endpoint 可以完成标准 MCP `initialize`、initialized notification、`tools/list`
和只读 `lol_list_lane_meta_champions` 的 `tools/call`。因此它不是普通 HTTP 接口被
重新命名为 MCP。

同时，目标 LoL 工具没有 `outputSchema`，成功结果是自定义文本而非
`structuredContent`，也没有当前 patch、源数据生成时间或上游 TTL。官方代理仓库的
MIT 许可证不能自动证明底层数据的再利用条款，稳定限流合同也未发布。ADR-0047 原先
把这些缺口合并成“关键合同不完整则整体 deferred”，会把真实传输能力和有限
provenance 错误地当成同一问题。

真实产品 smoke 还发现第二个 Bad Case：当前目录有 30 个工具，其中 18 个为 LoL；
两个未获准的 Valorant 工具使用数组根 `outputSchema`。若 Client 在 allowlist 前先按
RiftCoach 的对象输出合同解析全目录，一个无关工具就会阻断已获准 LoL 工具。

## 决策

### 1. 分离“可连接”与“可声明什么”

OP.GG 被裁决为 `admitted_with_restrictions`。标准 MCP transport/session 和只读工具
调用可真实使用；Meta 证据等级固定为 `partial`，只允许
`current_snapshot_recommendation`。以下声明继续禁止：

- `exact_patch_attribution`；
- `historical_patch_comparison`；
- `upstream_freshness_claim`。

本地 `retrieved_at` 只表示 RiftCoach 何时取回结果，`expires_at` 只表示本地 15 分钟
使用期限；两者不能冒充 OP.GG 的生成时间或数据新鲜度。`upstream_patch` 和
`source_generated_at` 保持 `null`。

### 2. 只对获准目录子集建立严格快照

`tools/list` 整体仍先受 response byte 和 tool count 上限约束，避免未获准条目绕过
资源门。随后 Client 只解析业务 allowlist 中的 descriptor，建立不可变 catalog/tool
schema digest；未获准工具既不能注册、调用，也不能用其不兼容 schema 阻断获准工具。

获准工具自身仍必须完整通过名称、字段、JSON Schema、annotations、大小和 drift
检查。此决定不是“忽略整个目录错误”，而是把严格验证放在真正具有执行权限的最小
权限集合上。

### 3. 自定义文本只经白名单语法归一化

Lane Meta Adapter 固定 `lang=en_US`、位置、字段、最多 10 行、一次尝试、deadline 和
正文上限。结果必须匹配固定 class header 和以下 AST 形状：

```text
LolListLaneMetaChampions(
  "en_US", position,
  Data(Positions([LaneRow(八个固定 scalar), ...]))
)
```

解析器只接受指定 `Call`、`Name`、`List` 和 `Constant` 节点，不使用 `eval`、
`literal_eval`、动态 import 或属性访问。英雄名、rate、tier、rank、唯一性和数量再次
进入 typed model 校验；任何额外节点、代码表达式、指令文本、非法 rate、重复 rank、
schema drift 或超限都返回 body-free 安全错误。

### 4. Meta 只作为可过期外部数据进入 Context

规范化结果成为 immutable/digest-bound `MetaEvidence`。Context 新增
`external_meta_evidence` trust，只允许 optional、`meta:` 前缀、user-role、data-only
section。它不能成为 system instruction，不能写 Memory、Candidate、Plan 或 Progress，
也不能覆盖 Riot 官方玩家/对局/版本事实。

## 备选方案

### A. 因缺 patch/TTL/outputSchema 整体拒绝 OP.GG

拒绝：真实 MCP handshake/list/call 已成功，缺口限制的是可支持的声明，不是否存在
标准连接能力。

### B. 接收任意文本并直接送入 Prompt

拒绝：会把远端正文、schema drift 和 prompt injection 带入产品信任边界，也无法形成
稳定测试或来源摘要。

### C. 严格解析全目录后再做调用 allowlist

拒绝：真实 30-tool 目录证明未获准的异构游戏工具可以阻断获准 LoL 工具；这违背最小
权限边界，也没有增加获准工具的安全性。

### D. Partial provenance + selected-catalog strict parsing（采用）

采用：保留标准互操作价值，同时诚实限制 freshness/patch 声明，并让执行权限、schema
验证和业务领域保持一致。

## 后果

正面结果：OP.GG 进入真实产品链路；远端描述和正文不会成为产品指令；Riot 官方事实与
OP.GG 聚合 Meta 可以分层组合；未来英雄分析、协同和对线工具可复用同一 per-tool
Adapter 模式。

代价与限制：当前只有 lane-meta 完成产品化；每个新增工具仍需独立字段/语法/用途合同；
OP.GG 未发布的 patch/freshness/rate-limit/数据条款不能由本项目补写；外部 endpoint 漂移
仍可能让调用 fail closed。

## 证据

- `data/evaluation/results/mcp/opgg_meta_admission_v1.json`
- `data/evaluation/results/mcp/opgg_meta_product_smoke_v1.json`
- `tests/test_opgg_meta_admission.py`
- `tests/test_mcp_streamable_http.py`
- `tests/test_mcp_transport.py`
- `tests/test_opgg_meta_adapter.py`
- `tests/test_opgg_meta_smoke.py`

## 参考

- ADR-0005：只把标准 MCP 称为 MCP
- ADR-0047：Stage 7 Adapter-first 边界
- RQ-075 / RQ-076
- `docs/plans/2026-08-21-opgg-meta-adapter-design.md`
