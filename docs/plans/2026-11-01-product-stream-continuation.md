# 同任务流式接续准备

## 当前：追加额度已授权

2026-11-01 01:18北京时间，用户明确“确认”同任务追加预算，已写create-only授权authorization.json，SHA 3203ae789cb82ba88d0ab66bcd51a6037f681a3278061ce08a31435f3fb7136f。累计上限12实际请求/723456tokens含历史unknown预留/2100活动秒；每请求300秒/16384输出、截止北京时间11月1日15:50:40保持。只复用当前3次成功生成，从同一facts-initial继续，必要时走双初审→唯一application→同稿双fresh；不导入诊断意见、不清零历史失败/费用，不增加自动重试。

追加预算作为该任务session内单独原件固定，不改全局8请求/401920tokens/900秒。新请求实时检查该任务额度/期限；历史许可按原合同回放，新手动补测绑定最新pin。追加许可禁止新生成，HTTP恢复入口不能提交额度。直接回读历史高ordinal回执不派发网络请求；实际新发送仍受逐请求预算和任务版本绑定约束。

真实临时Postgres/API/Worker零发送预检通过。仍为8HTTP/29323known/366910unknown预留/4retry、3次成功生成和5次524；累计活动827.172秒。原目录和旧DB保持。当前runs_root D:/rc-stream-20261101/verified-runs，task941d238c-972b-4b5a-bedc-302af12d1504/run review_1a568160d5aa44b5a2acd2f72fb679f8；最新checkpoint fc0d48305548f26c2abbc47fb566fb9d95822b3de5e8ad2e1d6a24781153de06，最新DB outputs/riftcoach-product-stream-authorized-20261101/migrated-db.dump SHA f3a5f822fe3b6bb487f3e65e32bad28fb7031287d4c23f870bd1d975178130f7。后续不能退回上轮迁移DB或attempt-9 DB。

相称验证78项通过：追加额度/产品链/旧手动许可40，真实SQL续接1，CI相同前置检查10，既有角色预算失败27；11个Runtime清单、compile/governance/diff检查通过。新清单只随相关源码指纹更新，旧清单、业务请求、15例标签及原15完成不改。SQL与模型替身验证不冒充真实流式上游验收。本轮准备阶段新付费0。

下一行动：一次提交推送后，固定干净执行cwd D:/riftcoach-sol-product-stream-budget-execution-20261101及同HEAD CI，核外置run_stream_continuation.py和唯一wait_stream_ci.py发送前guard。只有CI八项全绿且授权有效时，启动一次原任务流式续接，每segment最多1新请求，总新增最多4；普通成功边界可续下一职责，524/格式/语义暂停不自动补测。外置Control outputs/riftcoach-product-stream-authorized-20261101，binding.json固定HEAD/CI/授权/最新DB与驱动；attempt-10是唯一执行输出，先核waiter/进程/claim，禁止重复首启。执行返回后核真实费用与原件，使用inspect_current_browser_v2.cjs attempt-10只读验收并完成快照/清理；监控无变化不通知，终局删除。Stage8E、默认发布准入不变。结果data/evaluation/results/sol_product_stream_budget_authorized_20261101.json。

以下为历史准备记录。

目标：保留原3次成功生成、5次524及全部费用，将同task/run从1.7.0迁到1.7.1；先在新目录和临时SQL中零发送验证，不改原目录/DB/冻结源码。

实现：Worker新绑定固定execution_contract，旧绑定不会隐式改用新版本。迁移器只接受未发布、未封闭、初审前的生成成功和有真实524回执的失败；核每次请求/回执/累计费用，逐字复制operations/transport/journal，另存父原件归档，新guard明确新版本。SQL通过锁定同owner/task/run和原checkpoint的一次行政更新采用证明；仍需普通resume，迁移本身不发请求。

验证：原件篡改/错误身份/缺失回执/旧pin/并发状态拒绝；合成SQL/Worker恢复与真实原任务临时SQL零发送回放。补测次数授权保留；旧8请求/401920tokens/900活动秒不自行扩大，当前不读模型凭据。

终点：形成可核的迁移证明、成功前缀复用/零发送结果和具体后续预算。新预算获授权前保持当前首审暂停，不能把旧诊断意见导入或另开新任务清零费用。

## 准备结果

2026-11-01 00:55北京时间，完成同一产品任务从1.7.0非流式到1.7.1流式的受控迁移准备。Worker绑定明确记录execution_contract；旧绑定不能隐式升级。迁移仅接受尚未取得初审意见的成功生成与真实524回执，SQL按同owner/task/run及旧checkpoint采用证明，仍保持当前首审暂停。迁移不是重开任务，不授予预算或自动补测权限。

实际旧数据库在临时Postgres恢复后，原3次成功生成、5次524、8HTTP/29323known/366910unknown预留/4retry完整继承；198份父运行原件及原DB均保持，39个父检查点归档。旧已提交补充许可只允许按归档原pin回放，新许可仍必须绑定最新pin。普通resume实走API/SQL/Worker但新模型请求0、来源请求0、真实模型凭据读取0；未审查报告409，assistant消息0，临时迁移容器已清理。累计活动时间由824.281增加至825.968秒（本地恢复耗时），没有清零。

当前可恢复副本runs_root D:/rc-stream-20261101/verified-runs；task941d238c-972b-4b5a-bedc-302af12d1504、run review_1a568160d5aa44b5a2acd2f72fb679f8不变。最新checkpoint e35377cdd14a02e1a48b8c07d8fc9055dd99358d6b323909af6eaeba86c91d3d；数据库outputs/riftcoach-product-stream-migration-20261101/migrated-db.dump，SHA e7dd1d529d880ea369eb52757fd5b1c1553eb51d1fb1c4bb05a1cb1a83cdf209。后续从此副本接续，旧目录/DB继续只读，不回退旧快照。

验证：迁移/旧本地故障恢复/补充许可22项通过，包含真实临时SQL/Worker与替身模型；CI相同前置检查10项通过，11个Runtime清单及compile/governance/diff检查通过。原CI41220508456的web-checks失败是上轮遗漏natural_duty当前清单维护，仅app.runtime.coach_contract指纹变化；新增当前快照并改测试引用，旧快照及其他20字段保留。原CI四个pytest分片仍在运行，不把未结束项写成通过。本轮不重跑无关整套测试，原15完成不撤销。

下一行动：就同一任务确认具体追加预算方案（尚未授权）：增加4个请求槽、321536tokens及1200活动秒，累计12请求/723456tokens/2100秒；每请求300秒和16384输出保持。覆盖双初审，以及必要修订后的双fresh；不重复生成，不导入诊断意见，不清零未知费用。手动重试次数授权保留，失败仍消耗实际槽与token预留，不自动循环；截止仍北京时间11月1日15:50:40，不自行延长。获准后实现仅该task的追加预算绑定，验证旧许可回放及新发送上限，固定执行版本并按同HEAD CI结果续流式首审。当前无付费执行者或waiter，Stage8E及默认准入保持。工作卡docs/plans/2026-11-01-product-stream-continuation.md；结果data/evaluation/results/sol_product_stream_migration_ready_20261101.json。
