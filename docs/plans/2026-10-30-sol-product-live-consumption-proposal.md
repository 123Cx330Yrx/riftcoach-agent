# Flash/Sol 最小真实产品消费检查草案

2026-10-30。状态：单项任务和待发输入已准备，等待具体付费授权。承接已批准并实现的ADR0119；不继承10月29日已封存批次或延长其授权。

零付费预检已补普通HTTP入口：API显式配置`RIFTCOACH_TASK_PUBLICATION_MODE=evidence_bound_v1`，Worker显式选择`RIFTCOACH_WORKER_EXECUTION_PROFILE=sol-dual-product-v1`。前者使两条Review创建入口固定Evidence模式，不由客户端请求体选择；默认仍legacy。实际浏览器已能发起观摩会话，经过真实临时Postgres、Memory、Worker暂停续接，读取Evidence/报告/累计用量与唯一会话回复；普通恢复、524手动补测、取消三例通过，外部IO为替身。首次Evidence投影连同原时间随任务保存，恢复不重新计算bundle摘要。真实账号/近期来源预检和干净2715ae40执行目录已准备，普通任务输入绑定与新CI结果仍待完成/确认，见`2026-10-30-sol-product-preflight.md`，此文仍不是冻结付费清单。

## 具体目标

只检验一项Recent Review从普通任务入口、真实Flash/Sol、持久Worker到数据库、报告/Evidence和工作台累计用量能否连续消费。原15和自然正式修订证据继续有效，不再跑另一套15，不预设必须发生修订才算合格。直接双pass与可靠修订后双fresh均按已采用合同处理。

## 拟定输入与隔离

- 单项公开观摩：`DK ShowMaker#KR1`、`asia`、最近5场、queue420、overall；身份用途固定为observed，不能作为用户本人Training结果。账号与近期5场/5时间线已于2026-10-30实际查询成功，来源摘要见sol_product_real_source_preparation_20261030.json；普通任务/Memory完整输入绑定仍待完成，不用来源预检冒充最终模型输入冻结。
- 使用本次实现提交的干净执行版本；授权清单必须列出实际HEAD、独立profile `sol-dual-product-v1`、Python与cwd、来源摘要、输入摘要、输出路径及截止。此草案不是已冻结清单。
- 在独立临时数据库/本地端口执行与观察，保存实测原件后清理临时服务；不迁移或写入现有产品库，不切默认路由，不公网部署。
- 先Host-only核普通入口实际可用、观摩身份与Evidence绑定、浏览器登录、租约/取消和已有凭据名称，不打印凭据；若产品入口需要补接，先完成零付费修复再冻结清单。

## 请求、费用与停止边界

最多8次实际模型请求、401920累计tokens、900累计活动秒；每次至多300秒。正常4次直接通过或6次修订，附加位置供检索或明确恢复共享。Flash/high生成，Sol/high独立facts/completion，程序唯一应用，双fresh读同一实际新稿。当前产品渠道没有随Codex开发环境切回official而自动更换。

SDK自动重试0。524/可恢复格式故障暂停当前项并保留未知费用；手动补测仍须用户明确触发，最多2次且计入总限。互斥修法、来源/身份真实错误或fresh拒绝保留原稿与意见，不重买成功前缀，不为了pass偷偷换任务。预算耗尽也只暂停该任务。token限制不宣称为金额账单硬限；若需要金额边界，先核当前渠道报价再明确写入授权。

## 结束时应交付的证据

实际调用账、已知/未知/未发区分；生成和审查的原始请求回执；真实应用前后稿与两fresh摘要（若发生修订）；普通任务事件、数据库与API owner读取/非owner拒绝；浏览器可读报告/Evidence及累计用量截图。核实原件和停止点后提交结果，遇阻也保留成功前缀并给出局部恢复办法。不得把本次一条成功改写为稳定性、Stage8E整体或全部产品完成。

当前只完成实施包的离线/真库验证。本草案还需在零付费预检后形成可审核的冻结执行清单，之后再取得具体付费授权；不直接执行本文件。

## 玩家呈现检查（用户提前补充）

真实成稿回到工作台后，同时记录口吻与可读性：关键判断是否直白、建议是否具体、观摩对象是否明确、依据能否回查；检视整块纯文本显示对手机阅读的影响。此项用于决定后续最小呈现调整，不新增付费请求、不预设当前稿失败。措辞须在最终审查之前调整；排版不改已核验含义，禁止通过后再自由改写。具体要求见requirements_change_log的2026-10-30玩家表达条目。


## 首次发送前的实际任务准备

2026-10-30续：冻结2715ae40的CI41011784904已8项全部通过。普通cookie/CSRF API已创建一项真实观摩身份绑定任务，经临时Postgres、Memory和实际产品Worker，在session_model_boundary首次模型发送前暂停。采用已实取的5场/5时间线来源，source读取1次；请求/known/unknown/retry均0。首次实际待发模型输入、完整来源、检查点和数据库快照已固定；另一新临时库恢复校验通过，任务1/暂停1/assistant0/Training0，临时容器均已删除。

准备脚本前两次未启动API lifespan，服务未绑定而返回503；没有创建复盘任务或模型发送。修正准备脚本后通过，没有修改冻结产品源码。首次请求文件是待发输入，不冒称真实HTTP发送回执。

下一动作：按task-preparation-v3/execution-plan.json取得一项具体付费授权后，恢复同一任务并执行。范围为DK ShowMaker#KR1最近5场queue420观摩，Flash/high生成＋现有企业渠道Sol/high双审；最多8实际请求/401920tokens/900累计活动秒，每请求300秒，最多2次需用户明确触发的同项恢复。拟截止2026-10-31 07:45 UTC（北京时间15:45），尚未授权或发送。清单和证据见data/evaluation/results/sol_product_task_prepared_20261030.json；不沿用旧授权。默认/产品库/原15/Stage8E/automation保持；玩家口吻与排版在实际成稿消费中检查，审后不额外自由改写。


## 已授权执行的实际结果

2026-10-30实测：授权清单下完成3次Flash生成侧真实请求，累计29323 known/0 unknown/0retry；6次knowledge.search，生成最终正文返回，尚未进入Sol双审。任务终态failed/harness_execution_failed，没有发布报告。浏览器真实页面已核实累计用量29323、失败正文不可读，原响应/来源/检查点/数据库与失败均保留，执行者已退出、临时容器已删除。

定位为本机长路径原子写入：knowledge/retrieval_evidence.json目标247字符可用，但NamedTemporaryFile复制完整文件名作prefix后增至261字符，FileNotFoundError。相同247字符路径复现原失败，缩短prefix写入成功；原生成稿标题合同亦通过。开发树仅将临时文件prefix限为4字符；新回归先失败后通过，9项存储测试/12子检查、11入口及10项库存/API检查通过。冻结2715ae40未改，没有把这次执行层故障记成Sol语义失败。

下一动作：离线准备failed任务的受控恢复，保留原失败事件、三次成功模型响应、费用和检查点。现resume只接受recovery_required，直接改SQL或覆盖已提升的失败原件都不可接受；不重买生成前缀，不自动补测或另开付费试验。原授权截止2026-10-31 07:45 UTC不延长，剩余调用先不发送。证据data/evaluation/results/sol_product_live_storage_failure_20261030.json。玩家口吻要求保留，实际可见生成正文已存在但尚未完成审查，不作为已验收玩家成稿。原15、默认、产品库、Stage8E与automation PAUSED保持。


## 本地失败受控恢复

2026-10-30续：受控本地失败恢复已实现并通过实际原件零发送重放。同一task/run在新隔离目录逐字继承13个已提交操作、3次生成响应与29323 known/0 unknown/0retry；原143份封存证据保持，原SQL failed/worker_execution_failed事件和Runtime harness_execution_failed回执均保留。新目录另有完整失败原件压缩归档，不覆盖旧失败查询文件，不修改原冻结2715ae40。

实际browser-db恢复后，经受检恢复服务转入recovery_required，再由普通owner API和Worker重放，已到首次Sol审查发送前session_model_boundary。checkpoint a80096ba…、首审输入bd8fe407…与恢复数据库已固定；累计151.859活动秒，新增请求/真实凭据读取均0。6项新真库检查通过，覆盖原失败保留、双审完成、原件变化拒绝、旧pin/错误owner拒绝和取消。另17项既有真库链路与30项相关本地检查/12子检查通过，11个Runtime入口库存通过。

下一动作：绑定新干净修复提交及其CI，沿已固定首审输入继续同一任务。旧2715ae40/原授权plan不改，修复差异单列绑定；原8次/401920tokens/900活动秒与2026-10-31 07:45 UTC截止保持，已用3次、最多余5次，不重发生成、不自动补测。默认/产品库/原15/Stage8E与automation PAUSED不变。证据sol_product_local_failure_recovered_20261030.json；玩家最终稿和浏览器消费仍待审查完成。

恢复入口为app.product.local_failure_recovery.prepare_local_failure_recovery与PostgresTaskContinuations.recover_local_failure，属于显式行政操作，不开放通用failed重试API。只接受完整成功生成前缀、无待确认请求、无审查/terminal/seal且有真实失败回执的原任务；源/输入/预算逐字保持，失败原件以ZIP归入新run私有删除边界，避免Windows路径再嵌套超限。之后沿普通resume继续，原失败事件不删除，恢复操作以proof SHA幂等。
