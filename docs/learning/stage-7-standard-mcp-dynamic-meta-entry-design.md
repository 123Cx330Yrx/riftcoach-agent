# Stage 7：标准 MCP 与动态 Meta 入口设计学习材料

## 1. 问题与原理

RiftCoach 已有内部 Tool Runtime，但另一个程序无法仅凭 `ToolDefinition` 猜出如何
初始化会话、发现工具、调用工具和处理协议错误。MCP 是跨程序的互操作合同；Tool
Runtime 是本应用内的可靠执行合同。两者相连，但不是同一个东西。

动态 Meta 又是另一种问题：它会随 patch 和时间变化，来源可能不稳定，返回内容也不
可信。正确做法不是把外部 JSON 直接塞进 Prompt 或 Memory，而是由 Meta Adapter
转换成带 source、patch、digest、fetched_at 和 freshness 的 data-only `MetaEvidence`。

## 2. 本检查点做什么/不做什么

做：初学者教学、源码接缝审计、Adapter-first 方案比较、ADR、设计、实施顺序、OP.GG
准入清单和测试矩阵。

不做：安装 MCP SDK、实现 Client/Server、调用 OP.GG、读取 Key、把普通 HTTP 称为 MCP、
让外部 Meta 直接写 Memory/Plan/Progress 或改变 owner/player 身份。

## 3. 代码地图

- `app/tools/models.py`：工具名称、版本、input/output schema 和 policy；
- `app/tools/registry.py`：发现和 allowlist 的内部目录；
- `app/tools/runtime.py`：timeout、retry、cache、breaker、fallback、metrics；
- `app/api/composition.py`、`app/product/*`：对外 Application Service 接缝；
- `app/agent/context.py`、`app/agent/memory_context.py`：trust、data-only、ceiling 和 owner-scoped Context；
- `app/harness/*`、`app/runtime/*`：评测、发布、Trace 和安全终态；
- `docs/adr/0047-*`、Stage 7 design/implementation：冻结边界和后续任务。

## 4. 数据与控制流

```text
MCP initialize -> capability/version check -> tools/list -> schema snapshot
      -> allowlisted tools/call -> ToolDefinition -> ToolRuntime
      -> MetaEvidence -> Context data-only section -> Skill/Harness
```

失败在协议层、可靠性层或 Meta 规范化层就停止；不能绕过 Application Service 或
Memory gate。对外 Server 反向走 owner-scoped Application Facade，只暴露只读安全 DTO。

## 5. 测试如何证明行为

先测纯 envelope、版本/capability、工具 schema、错误映射和结果上限，再用本地 fixture
测 session/transport/disconnect/timeout。之后测 Meta stale/digest/schema/injection 和
data-only 边界，再测 Server owner scope 与 Application Service 接线。fixture 只能证明
实现符合合同，Stage 7 完成还需要真实外部 MCP Server 和真实外部 MCP Client 的一次可复现
互操作证据。

## 6. 运行与证据

入口设计阶段运行治理、完整 pytest、compileall、RAG 两套评测、Harness dry-run、secret/
tracked-data/YAML/diff 门；外部调用计数必须为 0。后续真实门必须 key-last、首错停止、
body-free immutable trace，并记录 exact SHA、协议版本、server/client identity、transport
和时间窗口。

## 7. 失败、安全与边界

版本不兼容、capability 缺失、未知工具、allowlist 越权、schema drift、malformed/oversized
result、断线、超时、限流、stale/digest mismatch 和 prompt injection 都 fail closed。
外部内容永远是不可信 data；不得覆盖 owner/player/conversation、system instruction、
Memory 或发布状态。OP.GG 尚未通过 endpoint、许可、schema、freshness 和互操作审计，当前
只能称为 candidate/deferred。

## 8. 面试准确表述

可以说： “我把标准 MCP 放在协议 Adapter 层，先转换到现有 Tool Runtime 的可靠执行合同；
动态 Meta 再经过有来源和 freshness 的 `MetaEvidence`，以 data-only 方式进入 Context。入口
设计已冻结错误、权限、OP.GG 准入和真实互操作门。”

不能说： “RiftCoach 已经接入 OP.GG MCP、支持任意 MCP Server，或已经完成外部互操作。”
这些都要等后续真实 Server/Client 证据。
