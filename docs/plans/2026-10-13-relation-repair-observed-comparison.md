# U1/U2完整初评修法对照的准备

目标是核验旧H5同类错误被检出后的修法是否仍错误否定样本区分，并同时检查正确稿保留。
这组材料的报告正文没有预写目标修法，只保留完整事实来源；U1/U2全文各26段，仅第14段
“均值并不接近/均值接近”一句不同。源事实、身份、知识、schema和完整初评要求保留。
材料的独立全文开发校准已完成，真实native/作者原件及主审意见见
`data/evaluation/results/host_relation_repair_calibration_20261012/close-audit.json`。

## 方案与选择理由

新入口`python -m scripts.document_relation_repair_diagnostic`复用当前完整报告runner、真实Host导入、
run外作者文件与工作区库存门。每篇顺序发送baseline和relation-contrast，只有system的虚构关系教学不同。
U1检查误报/正确保留，U2检查实际均值错误、解释、来源、最小修法及新增断言。
材料使用熟悉的历史来源，只提供开发诊断；即使四项全部通过也不授予产品资格。

不选择仅补买旧T9缺失一臂：其正文预写“不等于数值未区分”，且错误为“相同”而非H5“接近”，
无法充分代表旧故障。也不选择加引用编号或删初评：既有合同对照已反驳其作为修法方案的充分性。
当前选择仍是待验证候选，并没有因材料校准或离线测试而采用它。

## 真实请求前的观测与路由

新私有worker`scripts.document_relation_observed_request`保持原high/32768/600秒/SDK重试0合同，
在现有DefaultHttpxClient上追加字节观测hook；SDK请求、原字节、异常和close仍沿既有实现。
观测在operator的`observations`中create-only，每次以实际worker路径摘要独立定位，绑定原始请求SHA与新transport。
父进程在子进程终止后保存观测文件SHA、采样新鲜度和结果；完整响应缺少有效观测会硬停止。

有效路由在父进程和子进程分别检查：进程代理清空，NO_PROXY精确覆盖open.bigmodel.cn，
endpoint保持原GLM公网地址。只存路由契约，不存凭据、代理地址、正文、reasoning、URL或异常消息。
它不证明操作系统/网络侧路径，也不替供应商或抓包证据作上游归因。

提交、下一请求前和严格replay/seal均只读核验观测绑定及SHA。观测不写入run原件目录；
完整响应缺观测或原件变动不得通过Host提交。硬失败尾项可保留观测不可用，仍是失败/未知用量，不能补发。

## 有界范围与执行前条件

固定顺序：`U1-baseline:initial`、`U1-relation-contrast:initial`、`U2-baseline:initial`、`U2-relation-contrast:initial`。
全部initial，report_assessment=null，无生成、编辑、fresh、重评、重试或补发。

| 边界 | 值 |
|---|---|
| GLM-5.3/high | 最多4次，Flash0 |
| tokens | 387072（每请求输入64000、输出32768上限） |
| 活动时间 | 2400秒；每请求600秒 |
| Host时间 | 本范围授权内最多86400秒，不因等待延展 |
| 估价 | 未缓存上限口径5.718016元，非硬账单封顶；无usage尾项费用未知 |
| run | `data/runs/model_comparison/document-relation-repair-20261013` |
| operator | `C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-repair-20261013` |

包位于`data/evaluation/fixtures/document_relation_repair_20261013`，准备不会读取模型凭据、调用Provider、
创建业务run或派新native任务。未来必须先有本范围的新明确成本授权、同HEAD全绿公共CI、clean exact HEAD、
包/全部绑定源码不变，以及即时真实native和绝对cwd/Python启动预检。旧已关闭范围的authorization不能复用。
cwd为`D:/riftcoach-agent-rq192-pr`，Python为该树`.venv/Scripts/python.exe`，禁止追加backend。

独立复用原主体，每stage唯一NEW_TASK，只传完整原样dispatch与精确checkpoint/SHA、绝对路径和run外作者路径；
同task恢复仅MESSAGE，不泄漏主审/校准标签/批次代码。独立final前重读相同checkpoint，自写JSON check-answer后
唯一native final；主审读真实事件再submit，指定安装的codex.exe。主审核实际全文而非只看预期段号。

## 结果对应的去留

候选仍错则否定；两臂皆过或基线未复现时不称机制改善。完整语义拒绝/分歧继续下一独立项；
身份/来源/native/checkpoint/协议/transport/预算/主体硬失败停止全批。关闭后只读严格回放与create-only seal，
实核所有已审native，原件SHA不变，核actual/HTTP/known/unknown/receiptless/未发及最早偏离。
旧批原件与缺口独立保留，正式同版本15、自然消费、8E及全部既有下游依赖保留。

## 验证与当前状态

本轮无付费准备已完成，执行授权与实际模型结果均未建立。固定9文件包验证通过，plan SHA为
`2bd63a11ff50005803a746c8ecf7cc9e55d73b4c44be96cd9f04808cdc38ad2f`。
新旧关系入口与观测联合50项通过（157.74秒），包含实际loopback SDK/HTTP/worker的四条路径、
提交/下一发送/只读封存、缺失/篡改/transport硬停止、旧授权拒绝及原入口隔离。
实际模型请求0、新业务run0、新native作者任务0；原批73原件清单及SHA不变。
本机绝对cwd/Python实际启动和当前真实native预检通过，codex为0.153.4，未来执行前仍即时重核。
Windows大小写环境变量判断、Pydantic私有模块注册、Host marker导出和工作区重复安装问题已在准备期修复。
结果见`data/evaluation/results/document_relation_repair_preparation_20261013.json`。
原39c798b6公共CI38274465147已核completed/success；本次变更必须查询自己的CI。
