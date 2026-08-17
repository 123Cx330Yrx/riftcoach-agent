# 5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice 实施计划

## 目标

把已经完成的 `RecentReviewApplicationService` 与 `RunQueryService` 暴露为一个
严格、薄、同步的本地 HTTP 适配层。FastAPI 只负责 HTTP 合同、请求校验、状态码和
安全错误投影；它不选择 Skill、不构造 Prompt/Policy、不调用 CLI、不编排 Harness。

## 教学边界

本轮解释并实现：HTTP Adapter、应用服务边界、查询投影、错误映射和 TestClient。
本轮不实现：真实 Riot/Provider、Key、SQL、Session/Memory、后台任务、SSE、鉴权、
公网绑定、完整前端、LangGraph、Pi/Claude SDK、MCP、Multi-Agent 或 5P-6。

## 数据流

```text
HTTP JSON
  -> FastAPI 请求模型/422
  -> RecentReviewApplicationService
  -> Fake Summary + typed compiler + Fake Runtime/Harness
  -> body-free receipt
  -> 安全 POST 响应

GET run/report
  -> RunQueryService
  -> receipt + Trace + manifest + final Artifact 交叉校验
  -> 安全 DTO 或 Markdown
```

## 实施步骤

### Step 1 - 红灯合同

- 新增 API 聚焦测试，冻结四个端点、请求/响应模型、错误码/HTTP 映射、受限 headers、
  不存在的 status/follow-up/SSE 路径，以及模块 import 不读取环境 Key/网络。
- 输出：`tests/test_fastapi_adapter.py` 红灯证据。

### Step 2 - 依赖与薄 Adapter

- 增加 FastAPI runtime 依赖和 dev `httpx`；实现 `app/api/main.py`。
- `create_app(review_service, query_service)` 只接受显式依赖，避免 import 时组装真实外部
  Provider；使用 allowlisted response/error models。
- 输出：四端点可由 TestClient 调用，handler 不导入 `scripts` 或内部 Runtime 合同。

### Step 3 - 本地纵向切片与错误门

- 使用 fixture/Fake Service 验证 POST 成功、应用层上游/配置/runtime 失败、GET 查询和报告
  完整路径；使用真实 `RunQueryService` 的本地查询 fixture 验证报告媒体类型与完整性错误。
- 证明没有 Key/网络/真实 Provider I/O，且原始异常、URL、路径、Prompt 和正文不会进入错误响应。

### Step 4 - 比例验证与状态收尾

- 聚焦 API、5P、Runtime/Harness 相邻回归；完整 pytest、两套 RAG、compileall、治理、
  SDK/tracked-data/secret/run-data 边界、Harness dry-run、diff check。
- 更新 canonical、active plan、findings、progress、roadmap/matrix/decision 状态；提交、
  推送并用 exact-SHA CI 验证。

## 完成标准

- 四个固定端点与 OpenAPI 路径严格符合 ADR-0033；POST/GET/report/health 正常与错误路径
  均有测试。
- API 层不拥有业务编排；所有业务顺序继续由 Application Service/Runtime/Query Service
  负责。
- 所有测试外部 Provider calls、Key reads、Riot calls、held-out executions 均为 0。
- 5P-5 本地与 exact-SHA 公共验证成功后，canonical 只交接到 5P-6，不自动实现 5P-6。

## 风险与限制

- 同步 HTTP 请求会阻塞；文件 receipt/query 不是多 worker/崩溃恢复事务。
- API 没有鉴权、限流、CORS 或公网部署保证，只能作为本地展示切片。
- Fake Runtime/Provider 只证明接线与安全合同，不证明真实模型 Coach 质量。
