# 取消与失败任务的用量消费

2026-10-14，承接[取消Trace修复](2026-10-13-worker-dispatch-cancellation.md)。
本包目标：用户能看到停止前已经发生的消耗，且不因查询用量获得未发布报告。
不是模型语义修复、time600自然消费、完整journal或8E退出证据。

## 机制与实现

旧磁盘Trace已保留，但`GET /runs/{run_id}`对失败/取消任务固定409，前端也只在可发布时
取run并丢弃usage。新增独立只读`GET /runs/{run_id}/usage`，先用既有`owned_run_task`
确认当前owner及终态，再经`RunQueryService.get_run`复用receipt、Trace和Artifact完整性核验。
只返回schema_version、run_id、task_status、usage，不返回报告、正文、路径、身份秘密。
旧run/report/summary/timeline/证据发布权限不放宽。

- API：`app/api/main.py`、`app/api/run_usage_models.py`；不构造模型/Worker，不读密钥。
- 解码与消费：`web/src/api/{wire,decoders,liveWorkbenchApi}.ts`、`web/src/workbench/liveController.ts`。
  取消/失败/拒绝终态只取用量，不取受限正文；发布任务复用既有run中的usage，避免多一次请求。
  保留选择generation/run绑定，返回状态与任务不匹配则拒绝。
- 展示：`RunUsagePanel.tsx`在工作台侧栏显示调用、总tokens、估价；中英文文案齐全。
  取消/运行失败的Banner和CoachBrief不再误称为证据不足或质量审查失败。

数据流：发送观察 → 原Runtime Trace/receipt → SQL任务终态/owner → 校验后的只读投影 →
HTTP解码及run绑定 → 用量面板。SQL取消与磁盘Runtime状态可以不同，各自含义不混用。

## 失败与安全边界

| 情况 | 行为 |
|---|---|
| 非owner或不存在任务 | 404，查磁盘之前拒绝 |
| queued/running/recovery_required | 409，不读尚在写入的Trace |
| cancelled/failed且根本没有receipt，或有receipt但没有可信Trace | usage=null，显示暂无可信记录；不补0 |
| succeeded却缺receipt、损坏的receipt/Trace、错run返回 | 500/run_integrity_failed，不伪装为正常未知 |
| partial/unknown tokens或费用 | 总量/总费用未知；已观测tokens单列，不拿部分值充总量 |
| 可信零调用not_applicable | 显示实际零tokens，与缺失记录区分 |
| 最后一次响应后取消 | 可以有本地报告和用量，但SQL仍拦报告；只暴露用量白名单 |

复用既有完整性与权限服务，没有新增存储、依赖或自动模型调用。前端估算费用按原
pricing profile记录显示，明确不是供应商账单。没有部署，另一主树前端未改/未合并。

## 验证与复现

52项API/边界/整链测试通过（17.46秒），其中6项用独立临时Postgres17真实迁移/SQL、
FastAPI、Worker和显式包装的correction-scope应用；第1/3/4/5次取消、正常及外人取消
均核用量与报告权限。模型、Riot来源为替身，不是外部模型验证。
新增用量API的12项覆盖未知、损坏、错run、进行中及owner前置拒绝。

32项前端单测通过，TypeScript类型检查通过；6项真实Chromium live-workbench浏览器
检查通过（11.7秒），包括取消状态的1440/320px截图、未知总量、无报告请求与无横向溢出，
以及原SSE/切换身份/拒绝/降级/响应式/键盘/可访问性路径。浏览器使用本地HTTP替身服务，
与Postgres整链分段验证，**没有声称浏览器直接连该真实Postgres或外部模型**。
主审已实看320px截图，使用既有布局；不作为全站审美完成证明。

最初测试失败分别为新夹具未满足RuntimeUsage字段/价格身份、OpenAPI路径清单未更新，
以及浏览器语言存储夹具误用裸字符串（应为带schema_version的JSON）；已修正后通过。
没有修改生产用量完整性校验来迁就夹具。

本地复现：

```text
python -m pytest tests/test_run_usage_api.py tests/test_live_workbench_api.py tests/test_reliable_task_api.py tests/test_fastapi_adapter.py -q --tb=short --show-capture=no
# 以下只允许独立、可丢弃测试数据库；该fixture会downgrade/upgrade，绝不可指向产品库。
python -m pytest tests/test_worker_dispatch_postgres.py -q --tb=short --show-capture=no
cd web
npm run test:unit -- src/components/RunUsagePanel.test.tsx src/workbench/liveController.test.ts src/components/WorkbenchState.test.tsx src/api/decoders.test.ts
npm run typecheck
npm run test:e2e -- tests/e2e/live-workbench.spec.ts
```

临时数据库容器`riftcoach-usage-20261014`经专属label核验后已停止自动删除；
产品数据库原卷和127.0.0.1:15432保持。浏览器/测试服务由Playwright退出清理。
54份冻结准备源码及700历史原件SHA复核不变，旧readiness审计逐字段一致；旧失败和缺口不回写。
响应模型收紧终态枚举后，21项API/工厂定向复验通过（3.45秒）。治理、compile和diff检查通过。
两张浏览器截图保留在`C:/Users/33502/Documents/Agent/outputs/riftcoach-terminal-usage-20261014/`。

## 理解与后续

取消是停止未来工作，不会抹掉过去消耗；公开用量也不代表允许公开结果。这里用两个
独立查询权限表达这两件事，缺失数据保持未知。面试可表述为：“先核owner及数据库生命周期，
再读取哈希验证的执行凭证；使用白名单投影展示已发生用量，发布门独立决定正文可见性。”

本包代码、离线/分段集成证据完成；Owner理解未实测、未部署、当前组合自然任务消费未完成。
模型语义修法仍走[职责对照方案](2026-10-14-review-duty-design.md)，不能把本包算作三处语义失败改善。
