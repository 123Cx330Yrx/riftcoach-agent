# 既有完整重评的两项有界诊断

> 本准备记录已执行并关闭：首例双审拒绝，第二例未发送。当前结果及下一动作见
> [真实结果](2026-10-08-scope-resolution-result.md)。以下“尚未授权”等文字记录冻结时状态。

## 问题、选择和适用范围

原15新批严格2/15，claim-scope:3在检出补刀真错时增加早死口径误报，已经封存停批。
报告全文和对应规则确实到达模型，再追加相同提醒没有有区分力的依据。
本次复用已有完整重评和问题映射，检验带旧意见时能否同时撤回误报、保留真错。
不重建编辑器、不增加产品结构、不修改原15或已关闭回执。

这是发展诊断，模型看到历史初评，会受到旧意见锚定；不是新鲜初评、盲测或稳定率评估。
现有接口仍检查完整报告，不能叫做仅针对单项的窄裁决。

| 顺序 | 完整输入 | 应核验的行为 |
|---|---|---|
| 1 actual-mixed | 封存的claim-scope:3完整报告、来源及真实初评 | 撤回旧block4误报，保留block6补刀真错；不新增无据问题/解释/修法 |
| 2 explicit-middle-counterfactual | 仅把早死描述显式改成中单口径，其余完整上下文及历史意见保留 | 两个问题都保留；后文全样本限定不能替明确中单错误免责 |

第二例是明确标注的合成机制对照，不修改原始输入。期望只在host评测侧，不送入请求。
两项都要真实主审/独立审查；source IDs存在、schema可解析或score较高都不能替代来源核验。
host评价重评是否正确，原报告仍有真错，`report_assessment`必须显式为null。

## 已完成的执行接线

- `scripts/run_scope_resolution_diagnostic.py`：复用现有CI/身份/凭据前置检查、create-only目录、
  角色路由、共享预算和回执、host时钟；仅两次GLM-5.3/high重评，不调用Flash或编辑器。
- `scripts/scope_resolution_handoff.py`：从真实transport回执重新核对来源、请求、公开回包和
  stage；输出独立任务，导入明确event ID的真实native final，主审笔记必须另行明确给出。
  双审不一致或拒绝均停止，不能代写独立作者。
- 原子发布完整审查文件；提交与关闭共用短OS锁，事件读取在锁外。迟到审查不得写入已关闭批，
  进程退出会释放OS锁，单字节锁文件作为运行证据保留。
- 一例通过后才进入下一例；任何语义、协议、来源、身份、预算或传输失败停止。无自动重试、
  无新变体、无旧批剩余额度转授；中断调用保留未知用量，不冒充免费或成功。

## 冻结、成本与当前状态

冻结：`data/evaluation/results/golden_scope_resolution_preparation_20261008.json`。
方案SHA：`36dcf2f4db83c19e6af08f8a8ff6356b698f89627a5e8f6d28d7e654ab5f0e95`。

- 最多2次GLM-5.3/high调用、193536tokens、600活动秒；每次最多32768输出、300秒。
- host等待另计，最多86400秒。保守未缓存估价2.859008元，不是账单硬封顶。
- 主线程 `01a0c6c5-01d1-78d0-82fb-e567e0ab7150`；独立线程 `01a0ebaf-790b-70b2-9f02-9e354d9ea50b`。
- 真实只读preflight通过，派发正文仍不可读，当前路由及终态可用；沿既有
  `native-final-attestation-v1`，不保证未来服务可用。
- **尚未获本冻结方案的付费授权，Provider新增0，尚未创建执行目录。**
  最终提交公共CI全绿及明确授权后才执行，不能把历史提交CI套到新代码。

## 验证与审查

新runner15项测试通过，末次临时文件清理调整后2项交接测试再次通过；此前3项输入隔离测试通过。
涵盖真实回执写入器→阶段重建→事件导入→create-only提交→两阶段完成的离线路径，
以及错映射、漏真错、缺映射、拒绝、身份错误、host不可用、未知用量、预算耗尽与关闭竞争。
合成模型/host仅验证实现，不能宣称GLM通过语义测试。

独立代码审查发现显式null字段可遗漏、关闭与迟到提交可竞争，修复后复核无阻断。
独立作者误用未装pytest的解释器，未独立重跑测试；上述通过来自主执行器的项目`.venv`。

## 对完整Agent路径的决策影响

当前自然任务为选工具→根据工具结果生成报告→初评→编辑→fresh，共5次调用。
加入重评变为6次，超过现有产品5次限制；现有真实composition的离线测试已经证明第6次会被拒绝：
`tests/test_review_boundary_examples.py::test_actual_application_initial_edit_fresh_and_shared_budget`。
因此本诊断成功**不允许自动插入产品**，也不改变5次/401920tokens/900秒的产品合同。

成功只说明这两个有旧意见条件的重评能够区分边界；再以实际入口、触发条件和全链预算
决定是否采用及如何验证。若需要变更产品预算/采用标准，另行明确决定，不能在接线时暗改。
失败则否定“现有完整重评足以修复本对照”的假设，保留首次偏离，不继续追加提示后付费重试。
无论哪条分支，原15仍2/15，默认产品、自然Coach、Worker/DB/API/Workbench及8E都不获得资格。

## 操作与恢复

在后端checkout根目录用`.venv/Scripts/python.exe -m scripts.run_scope_resolution_diagnostic`
预览或执行；必须用模块方式启动，直接运行脚本路径不能解析`scripts`包。
执行参数为已冻结root/independent ID、`--execute --preparation <冻结文件> --plan-sha <上述SHA>`，
加上最终`--ci-run`、既有本地`--env-file`和`--codex-executable`。不将凭据写入文档/日志。

执行目录固定为`data/runs/model_comparison/scope-resolution-diagnostic-20261008`；存在即拒绝重开。
每项出现`review-required.json`后，用`python -m scripts.scope_resolution_handoff task --key <key>`
生成任务交给真实独立作者。其合法final完成后，主审笔记文件仅含accepted、defects、source_review；
用`submit --key <key> --notes <路径> --event-id <实际事件ID> --codex-executable <路径>`导入。
接收阶段评价而非成稿认证，不把可读性建议升级为问题。封存只导出公开回包，保留原件摘要。

恢复先查目录、PID/日志、原始回执和result，不因用户中断或额度切换重发未知请求。
四块联动、个人Training、前端审美/必要重做/头像、Memory及其他后续仍沿活动计划保留。
