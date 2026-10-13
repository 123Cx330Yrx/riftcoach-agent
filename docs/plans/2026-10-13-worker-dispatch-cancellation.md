# Worker取消必须阻止下一次模型发送

本工作处理已在`2026-10-13-post-joint-consumption.md`记录的运行缺口。三处旧语义问题仍未
修复，新15提议仍撤回，没有新模型调用或资格。本轮未找到足以替代语义判断的确定性合同
缺陷：完整请求已有全文和范围规则；原文/来源绑定只验证出处，不能证明解释成立。因此
未新增引用字段、同义教学或付费诊断，独立修复可复现的执行问题，不将其算作语义进展。

## 故障、机制与改动

原`ReviewWorker`持续续租，但仅在同步executor返回后检查取消/所有权。真实应用中的
两次生成、初评、编辑、终评可能全部发送，最后才取消发布。用修改前的观察函数代入
新回归，第一次生成后请求取消，实际仍记录5个delegate发送；回归按预期失败。

新控制流为：Worker绑定当前执行的检查函数 → Provider启动观察前检查当前租约 →
ACTIVE才继续原观察/发送 → 完整返回照常保存 → 下次发送再次检查 → Worker按原CAS收尾。
发送前直接调用既有heartbeat，能发现两次快速阶段之间的取消，不必等周期续租。
检查与周期续租共用串行锁，丢失/取消结果不能被后来的ACTIVE覆盖；数据库异常同样阻断。
Worker仍用原cancel_running、ownership_lost或安全错误收尾，没有生成伪造业务终态。

- `app/runtime/dispatch_control.py`：用ContextVar把检查限制在当前同步执行，退出及异常时
  恢复上下文，拒绝嵌套覆盖。`DispatchStopped`走既有终止性观察异常路径，避免被当作
  模型格式问题触发重评、回退或编辑。
- `app/runtime/observer.py`：在ProviderCallStartedSignal交付前做检查，未获准发送不记录
  实际Provider-start。Provider包装层在这个边界之前已清掉旧receipt，不会借用上次回执。
- `app/workers/review_worker.py`：将本租约检查绑定到executor执行期，串行heartbeat并保留
  终止状态，之后沿原终态逻辑处理。无租约的旧执行模式不声称获得这一能力。

最初把检查放入ObservedLLMProvider会改变已登记组件指纹，完整应用测试明确拒绝。
最终保留该模型包装代码原样，将租约前置条件接在任务控制/观察入口；没有放宽resolver、
更新旧manifest或借旧模型质量证据认证本改动。模型政策/schema、角色、采样、预算与冻结
workflow源码保持。任务控制改动需以下新的运行回归，不以旧语义通过抵扣。

## 验证与真实边界

回归覆盖：发送前取消，初评/编辑后的取消，实际后台续租线程在进行中的调用期间观察到
取消/丢失/异常，后来ACTIVE不能撤销取消，不同执行上下文隔离、错误后无旧receipt，
完整Coach应用的生成→工具→生成→初评→编辑→终评及共享预算接线。模型和DB均为替身，
真实的是应用调用链、文件IO、观察事件和后台线程；未调用外部Provider。

完整应用分别在第1/3/4个请求完成后设置取消，后续请求不发送；正常路径仍走5个请求。
修改前观察函数在相同第1个请求后的取消测试中继续走满5次，是明确的旧行为反例。

局限与运行说明：

- 不强行终止已在进行的HTTP；已发送请求仍按实际响应和用量保留。取消在最后一次检查
  之后才到达时，该请求可能已开始，终态CAS继续防止发布。
- 未改冻结的外层预算器。它在进入观察入口前预留调用/token，所以被拦截的后续尝试
  仍占保守预留并将budget停止；这不等于实际Provider/HTTP发送，也不是实际使用量。
  测试分别核对预算尝试2与delegate/Provider-start各1，未释放或伪造用量。
- 此处覆盖现有同步Worker→Runtime链路。ContextVar不会自动跨任意新线程传播；未来
  自建线程/进程的模型执行需显式传递执行控制，不能凭当前测试宣称已覆盖。
- 取消/API/DB/UI的完整真实部署验证和未采用的time600默认接线仍是后续依赖；本补丁
  不开放候选、不改变产品资格、阶段顺序或原15语义标准。

运行验证：`python -m pytest tests/test_worker_dispatch_control.py tests/test_runtime_observer.py tests/test_runtime_observed_provider.py tests/test_reliable_review_worker.py tests/test_review_worker.py tests/test_worker_polling.py tests/test_worker_composition.py tests/test_timed_document_worker.py tests/test_correction_scope_runtime.py --tb=short -q`。

该组125项通过（44.69秒）。后续补上“没有观察器也不能绕过取消”及更精确的取消粘性检查，
新增文件23项定向复验通过（8.95秒）；再核取消路径无final_report的4项通过（4.80秒）。治理及diff检查通过。旧修复就绪审计逐字段不变，执行准备中的54份去重源码绑定SHA及
700历史原件SHA实核不变；无需修改旧准备、冻结workflow、标签或历史审查结论。

Owner理解、真实模型质量与部署成熟度未由本次代码回归认证，8E及全部下游保持未完成。

## 公共CI失败与应用回归修正

`4be52567`的[CI38413626331](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/38413626331)
四个pytest分片均在`test_coach_application_composition`的同一参数化测试失败：旧断言要求
整个任务只有一次heartbeat，实际五次发送前检查加终态检查为六次。前端、打包、Postgres
迁移检查成功。上一轮定向验证遗漏了这两套更早的应用/Worker组合测试，不能称公共CI已通过。

本地原断言复现`6 != 1`。查全部heartbeat计数断言后，同时修正
`test_coach_application_composition.py`与`test_offline_coach_runtime.py`：正常/质量拒绝
路径要求每次实际发送及终态至少各有一次检查，允许后台周期续租；失去所有权的夹具改为
完成五次模型响应后才返回LOST，继续验证结束时不能提交或投影对话终态。旧夹具首次
heartbeat即LOST在新语义下会阻断首次发送，不能再用它测试结束时的失去所有权。
发送前取消/丢失/数据库异常的零发送断言由`test_worker_dispatch_control.py`保留覆盖。
没有改生产guard、放宽租约门、跳过测试或调整CI配置。

两套应用测试、Worker控制及可靠Worker共113项通过（22.38秒），全部使用替身Provider/DB，
应用测试禁止网络。检查没有模型调用、新Host任务或历史证据修改；新提交的公共CI须单独
核验。这是上一运行修复的收尾，三处语义问题仍未修复。

## 后继CI与真实数据库/API验证

`4eb471fe`/CI38416151132又暴露两处遗漏：历史时间裁决重建使用了变更后的Worker摘要；
native应用测试也在第一次heartbeat注入LOST，却仍要求完整三次调用。前者从Git取回
与原裁决SHA完全一致的Worker源码，仅增加可核归档；后者在第三次响应后才注入LOST，
仍禁止原子Evidence提交和对话投影。原裁决/业务回执、生产代码、租约门和模型规则未改。
时间审计及native应用25项通过，历史时间审计逐字重建成功。

新增`tests/test_worker_dispatch_postgres.py`并接入公共Postgres测试任务。实际使用
FastAPI TestClient → ReviewTaskService → PostgresTaskRepository → ReviewWorker →
RecentReviewTaskExecutor → 现有correction-scope应用；数据库为独立临时Postgres17容器，
模型及比赛来源为既有替身。不是time600自然消费、真实模型质量、浏览器操作或8E资格。

六项数据库场景通过：正常五次；第1/3/4次响应期间经API取消后只发1/3/4次；第5次期间
取消仍禁止对外报告；另一owner取消返回404且正常五次不受影响。SQL状态、生命周期事件、
owner隔离、取消幂等和报告HTTP门均核实。关闭发送前guard的内存反例在第一次取消后仍发
满五次，测试如预期失败；不是仅验证最终状态。没有改生产函数做这项对照。

**新发现、未修复：提前取消的用量Trace缺口。** 第1/3/4次取消时API/SQL正确cancelled，
本地receipt为failed/observation_failed且trace_reference为空。DispatchStopped继承
RuntimeObservationError，旧Runtime以观察器损坏路径返回，未持久化已观察调用的汇总Trace。
因此先前“在途响应保留”仅能支持发送边界和原Provider回执，不足以声称产品用量日志完整。
上述六项只验发送/可见性；正常及最后一次取消另验完整Trace计数。没有为使测试通过而伪造
Trace/用量或把缺失当0。取消控制还不能作为完整journal验收，后续需将可信取消与真实观察
失败区分，保存已发生事件，同时保留观察故障拒绝、旧冻结源码与原件的隔离。

本机Docker启动另遇`sailor-ingest.sock`无法重命名。官方stop后无后台进程，两个运行socket
目录同级备份，重建后Docker29.7.2正常，原Postgres卷/15432映射保留且healthy；没有恢复出厂
或读取模型凭据。测试仅对独立临时数据库迁移，未对产品库downgrade。恢复证据位于
`C:/Users/33502/Documents/Agent/outputs/riftcoach-local-runtime-20261013/recovery.json`。
