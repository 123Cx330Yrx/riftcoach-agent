# 完整15关闭后的未发送8例接续

用户明确纠正当前动作：“不是啊，我是说后面8例”。接续目标是执行这8例的初评、
必要编辑和fresh，沿原效率策略收齐独立案例证据；当前不换教学或转去其他产品环节。

原批因为旧root429后恢复分支不能派冻结独立主体而按硬故障规则关闭。
这不说明后8例语义失败，也不意味着停止整个项目。原批不重启，前7例不重发；
第7例未审的96/pass保留缺口。旧剩余预算不迁移，本次执行依据是用户当前的8例接续要求。

## 接续实现

新增`scripts/document_remaining8_adapter.py`，复用原runner、workflow、transport和native
evidence的隔离module实例，不修改原源码或sys.modules中的旧模块，不复制业务工作流。
从固定SHA的公开旧seal核`unexecuted_keys`恰好为后8例，再逐项核原冻结源码、cells和
time600初评请求SHA。prepare、observe及task/submit/replay/seal都绑定相同新计划。
两个含函数内旧evidence导入的Host入口在隔离实例内显式接线；旧calls_for只读取实际新目录
回执，未调用旧prepare/load_plan，独立工程复核未发现错误旧计划加载。

| 项目 | 本次范围 |
|---|---|
| 顺序 | claim-scope:5、claim-scope:6、claim-scope:7、observed:1..5 |
| 来源/政策 | 与关闭批后8例完整原稿、source、实际初评请求逐项一致；不复用历史Host判断 |
| 最大调用 | GLM13 + Flash5 = 18；3个应接受控制不做无必要编辑，5个真错控制最多初评/编辑/fresh |
| 最大tokens | 1741824（每调用保守96768） |
| 时间 | 每案900秒/5calls/401920tokens；整批活动7200秒/Host86400秒 |
| 单次 | GLM600/Flash300，受案内剩余和整批剩余截短；输出32768 |
| 保守未缓存估价 | 19.298304元，非硬计费封顶，实际回执另行结算 |
| run | data/runs/model_comparison/document-remaining8-time600-20261010 |
| 新主审root | 01a1261f-94b1-7510-8d72-fd5514789015 |
| 新独立Sol | 01a1263f-db97-7e02-bd7e-70b3a11b59ce，/root/remaining8_independent |

Provider仍为既有GLM-5.3/high与GLM-5.3-flash/high，不因Codex开发模型改变。
语义拒绝停该案依赖阶段，继续下一独立案；身份、来源、native、checkpoint、协议、
transport、预算和主体不可用等硬故障停全批。无重试、重评、重开、补签或资格。

## 实际准备证据

新独立主体已实际读取预检文件并核SHA，再次读取后返回唯一多行JSON原生final。
主审通过安装的codex.exe只读实核lineage、completed/error=null、final_answer、
实际5个工具items及原样JSON。current_input_readable=false由现行FINAL_POLICY支持；
opaque dispatch并不冒充正文可读，精确终答与原生membership仍强制核验。
该预检证明当前路由与终答可用，不保证未来容量，也不是业务审查。

独立主体实际读取适配器、测试与原runner/evidence相关代码，工程复核无blocking findings；
没有读取旧Host意见或主审notes，没有Provider调用。其提出revision/final尚缺接缝覆盖，
主审已增加真实回执factory与合成Provider/Host的三阶段路径检查；这些不计真实质量。

最终7项接缝检查实际通过（126.68秒），覆盖8库存/隔离、请求与旧seal篡改拒绝、
初评语义拒绝继续独立案、编辑/fresh完整接缝、checkpoint篡改与硬abort停批、
严格回放和create-only封存。模型与Host均为合成，不冒认真实8质量。
create-only准备方案SHA：`fcc5adf8af0e37cc38add2cc4dbc9ae947deb5a0e676ad96eaa2b9d2a02cf556`；
文件为operator的`preparation-plan.json`，首次发送前再核源码、文件及原生身份。

首个公共CI38061326419在Linux的controls夹具触发旧原SHA漂移：21份冻结源码在Git
检出时仅换行与Windows原字节不同。生产adapter及旧源码不改；仅测试使用固定46文件
原SHA/LF SHA映射，逐项绑定旧seal并核当前Git对象；内容变化不能通过映射。
独立工程复核无阻断，另实际检查46份追加内容均不匹配映射。新增反例恢复生产原SHA
函数后，LF副本仍被prior拒绝；此夹具不进入真实执行，不放宽生产冻结门。
该失败发生于付费前，新run不存在。原operator授权快照保留，修正提交另绑定实际CI。
修正后最终8项本机检查实际通过（124.13秒）；公共Linux结果仍需同提交CI验证。

Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-remaining8-20261010`。
首次发送前核最终准备/源码/clean exact HEAD/同提交全绿CI，并即时重读真实native主体。
运行期源码/HEAD冻结，create-only启动记录，只有一份runner；等待无变化不重复通知。
每个完成stage的主审全文核验和独立全文审查仍须精确checkpoint/SHA与真实native终答。

## 后续与边界

8例执行结束后严格只读重放、公开白名单封存，核实际调用/known/unknown/receiptless/
未执行及最早偏离，更新canonical/活动计划/progress/findings并检查提交推送。
后8例即使全部通过也不补第7例认证，不能拼成同期完整15或正式准入；历史2/15、3/15、
remaining11各自保留。完成或不能继续后自动任务保持暂停。

收齐本次后再结合全部正反证据选共同语义改良；正式同版本15、自然消费、8E、
Coach/Training/四块联动、Worker-DB-API-UI-journal、前端审美头像、Memory、身份运维、
两树整合与八维学习仍保持原依赖。本次不转移到其他环节来替代8例覆盖。
