# 5P-4 File-backed Run Receipt & Query Projection 实施计划

## 1. 状态与范围

- 日期：2026-08-17
- canonical checkpoint：`5P-4-file-backed-run-receipt-query`
- 用户授权：RQ-044
- 依据：ADR-0033 与 5P entry design
- 当前性质：TDD 实施计划；尚未安装 FastAPI 或实现 HTTP

本检查点只建立本地文件查询证据链：body-free receipt、不可覆盖的原子 Store、严格
`RunQueryService`，以及 Application Service 在取得类型化 Runtime 终态后写 receipt 的接缝。

## 2. 要解决的问题

现有 `runtime_trace.json`、Harness `manifest.json` 和 `output/final_report.md` 分别保存运行事实、
Artifact 账本和最终正文，但缺少供产品查询使用的安全入口。只根据 `run_id` 拼文件路径会绕过
Runtime/Publication 终态、Schema 和 SHA-256 校验，也无法保证 rejected run 不泄露报告。

新增 `api_run_receipt.json` 只保存查询所需的安全索引，不复制报告、Prompt、Context、Tool 数据、
异常或绝对路径。查询必须重新核对 receipt、Trace、manifest 和最终 Artifact 的一致性。

## 3. 冻结合同

### 3.1 Receipt

严格 frozen/extra-forbid 模型至少包含：

- `schema_version=1.0`；
- `run_id`；
- Runtime status；
- publication status，可为 null；
- terminal reason；
- Runtime Trace reference，可为 null；
- `created_at_utc`；
- `report_available`。

completed Runtime 必须有 publication 与 Trace reference；rejected 或无可验证 Trace 时不得声明
报告可用。Store 固定写入 `runs/<run_id>/api_run_receipt.json`，使用同目录临时文件、flush/fsync 与
不覆盖提交；任何第二次写入都失败并保留原字节。

### 3.2 Query view

`RunView` 只允许返回：

- Runtime/Publication/terminal；
- Skill name/version 与 Prompt Program id/version；
- started/completed/elapsed；
- completeness-aware Runtime Usage；
- `report_available`。

不得返回 Provider identity、Artifact 路径、Prompt/Context、Tool data、原始异常或报告正文。
Trace 缺失的失败 Runtime 可以返回 receipt 中可证明的最小字段，其 identity/time/Usage 为 null；
completed Runtime 不允许缺 Trace。

### 3.3 查询错误

- receipt 不存在或 run_id 非法：`run_not_found`；
- rejected、无可验证 final report：`report_not_available`；
- receipt/Trace/manifest/Artifact 任一损坏或互相矛盾：`run_integrity_failed`。

错误对象只保留固定 code，不保留底层异常、损坏正文或本地路径。

## 4. 严格读取流程

```text
normalize run_id
→ strict receipt
→ optional RuntimeTraceStore.read_trace(reference)
→ receipt 与 Trace 的 runtime/publication/terminal 交叉校验
→ FileRunStore.read_manifest()
→ manifest status/final decision/terminal transition 与 Trace publication 交叉校验
→ 唯一 final_report record 与 Trace Artifact reference 逐字段匹配
→ FileRunStore.read_artifact() 重验真实字节与 SHA-256
→ UTF-8、非空 Markdown 校验
→ allowlisted RunView 或 Markdown
```

早期 Runtime failure 可能在 Harness manifest 创建前就形成失败 Trace；只有 failed、无 publication、
无报告的组合允许 manifest 缺失。Trace 缺失时一律不开放报告。Trace 后、receipt 前的进程崩溃会
留下孤立 run，V1 不扫描目录、不推断恢复。

## 5. Application Service 接缝

新增窄协议 `RunReceiptWriter.write_result()`。Application Service 在验证 Runtime result 的 run_id
属于服务器生成 request 后、投影 completed/failed 结果前写 receipt：

- completed 与类型化 failed `RuntimeRunResult` 都写；
- Prompt Program 启动漂移、Runtime 抛出未类型化异常或返回错误 run_id 时不伪造 receipt；
- receipt 写入失败映射为现有 body-free `review_runtime_failed`；
- 单元测试使用显式 Fake writer；5P-5 composition root 才注入真实 file store。

## 6. TDD 批次

### Batch A：Receipt/Store 红灯与实现

- 严格字段、状态不变量、UTC、run_id 与 Trace reference 绑定；
- 固定文件名、UTF-8 JSON + trailing newline、round trip；
- unsafe run_id、重复写、提交失败清理和原字节不变；
- receipt 不含报告、Prompt、Tool、异常、路径字段。

### Batch B：Query 红灯与实现

- published/degraded 正常 RunView 与 Markdown；
- rejected/无报告、run not found；
- receipt、Trace digest/schema、manifest publication/final decision/terminal、Artifact record/digest、
  重复 final report、非法 UTF-8/空报告篡改；
- failed + nullable Trace 的最小安全视图；
- 错误脱敏和 allowlisted RunView 字段。

### Batch C：Application Service 接线

- receipt 在 Runtime completed 结果返回前写入；
- failed Runtime 在安全异常抛出前写入；
- wrong run_id、未类型化 Runtime 异常和前置上游失败不写；
- writer failure 不泄漏底层错误。

## 7. 验证门

1. 新增 receipt/query 聚焦测试；
2. Application Service、Runtime Store、Harness Store 相邻回归；
3. 5P/Runtime/Harness 比例回归；
4. 完整 pytest 与两套 RAG 门禁；
5. compileall、Harness SDK boundary、tracked secret/run-data、dry-run；
6. governance、`git diff --check`、stale phrase 搜索；
7. 提交、推送与 exact-SHA GitHub Actions。

所有测试使用临时目录、fixture 和 Fake Runtime；Key/Riot/Provider/held-out I/O 必须为 0。

## 8. 明确不实现

- FastAPI、OpenAPI、TestClient 或任意 HTTP endpoint；
- SQL、Session、Memory、鉴权、幂等和多 worker 事务；
- SSE、后台任务、cancel/resume、目录扫描或孤立 run 恢复；
- 真实 Riot/Provider 调用、模型切换、held-out；
- LangGraph、Pi/Claude Agent SDK、MCP、Multi-Agent 或 5F。

5P-4 完成后只交接到 `5P-5-thin-fastapi-adapter-no-io-vertical-slice`，不自动实施。

## 9. 本地执行证据

- Batch A/B 首轮 collection red：缺少 `app.product.run_receipts` / `run_query`；实现后 26 passed；
- Batch C 首轮 red：Application Service 不接受 `receipt_writer`，23 failed；实现后转绿；
- 最终 receipt/query/Application 聚焦：50 passed；
- 5P/Runtime/Harness 相邻：179 passed, 12 subtests passed；
- 完整回归：860 passed, 110 subtests passed；
- 两套 RAG、compileall、Harness SDK boundary、tracked secret/run-data、Harness dry-run、
  governance 与 diff check 通过；
- Key/Riot/Provider/held-out I/O：0。

当前仍待实现提交、推送和 exact-SHA 公共 CI，5P-4 尚未正式关闭。
