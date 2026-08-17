# ADR-0033：采用薄 FastAPI 与 Application Service 构建近期复盘切片

## 状态

Accepted

## 日期

2026-08-17

## 背景

现有 `AgentRuntimeV1` 接收已选 Skill、Summary、确定性报告、Artifact binding 和 Runtime policy，
而产品用户只能提供 Riot ID 和少量选项。仓库没有 API 模块或生产 Runtime composition root；
确定性报告还位于 CLI 脚本。v1.3 的早期文件型 API 清单又包含 follow-up/status，但阶段 6 才负责
Session、Memory、SQL、SSE、用户隔离和完整前端。

## 决策

1. 使用 FastAPI 作为薄 HTTP Adapter，并新增同步 `RecentReviewApplicationService`；
2. Application Service 调用 app-level Summary Builder/Report Renderer、typed compiler 和唯一
   `AgentRuntimeV1.run()`；handler 不导入 scripts、不拼 Agent/Harness；
3. typed `/reviews/recent` 通过 Catalog 可信选择 recent Skill，不重新调用自由文本 Router；
4. 增加 body-free immutable run receipt 与 Query Service，复读 Trace/manifest/final Artifact；
5. V1 端点固定为 POST recent、GET run、GET report、GET health；不单列 status，不做 follow-up；
6. 默认本地绑定，同步阻塞、单进程文件存储；无鉴权前不得宣称公网部署就绪；
7. FastAPI/ASGI/TestClient 依赖在 5P-5 独立加入并验证，不在 entry design 偷跑；
8. 所有 API 测试使用 Fake Provider/本地 fixture，模块 import 和 CI 不读取 Key或网络 I/O。

## 后果

### 正面

- 形成真实“Riot ID → Runtime → 质量门 → 报告”的产品接缝；
- HTTP、应用用例和 AgentRuntime 职责清楚；
- 未来 CLI/MCP/网页可复用 Application Service；
- 文件型 run/report 可展示而不提前引入 SQL。

### 负面

- 新增 FastAPI/ASGI 依赖和一个应用层；
- 同步长请求延迟高，文件投影不支持多 worker 事务；
- Trace 与 receipt 之间存在进程崩溃窗口；
- 无鉴权/限流，首版只能本地使用。

### 中性

- 真实模型领域质量仍未准入；Fake Provider 纵向测试只证明接线；
- SSE、Session、Memory、SQL、幂等、恢复和完整前端仍在阶段 6/8；
- 5F 的 Pi/Claude Agent SDK 对照不受影响。

## 备选方案

### Handler 直接串 CLI

拒绝。会依赖脚本、复制旧 Harness 装配并绕过 Runtime。

### 原样暴露 RuntimeRunRequest

拒绝。泄漏内部 Skill/Artifact/policy 合同，且不是 Riot ID 产品入口。

### 立即做异步任务、SQL 与 SSE

拒绝。当前没有并发、恢复或多用户 Bad Case，且会越过阶段 6。

## 参考

- `docs/plans/2026-08-17-prompt-program-and-early-product-slice-design.md`
- `docs/roadmap_v1_3_amendment.md`
- `app/runtime/runtime.py`
- `app/harness/store.py`
- ADR-0029、ADR-0031、ADR-0032
