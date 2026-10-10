# 接续从未发送的后四例

当前目标仍是完成用户要求的后8例覆盖。前3例通过，第4例observed:1初评完成但恢复操作产生
重复NEW_TASK，使native导入失败，本批已按硬故障规则关闭。后四例没有发送，不是语义失败。
本计划只准备observed:2..5；旧批、observed:1与旧完整15第7例都不重启、重买、补签或复用旧Host意见。

## 方案取舍

不能放宽唯一NEW_TASK门来追认失败事件，也不需要改变Provider教学、业务修法或时间预算。
明确问题在root恢复操作：协作running和native interrupted并存时，仍是同一审查turn，
followup_task会加入第二个NEW_TASK。今后恢复只发普通MESSAGE，等待当前turn完成；即使
普通消息没有立即回复也不能升级成NEW_TASK重派。真正不可恢复按硬故障停止，如实保留。
新stage只在先前turn实读completed且无error、唯一final并导入完成后投递。冻结校验器继续拒绝
重复dispatch，任何人不得改原件让它通过。

新增`scripts/document_remaining4_adapter.py`加载隔离的原remaining8 module实例，复用已有
runner/evidence的完整生命周期、checkpoint、native导入、语义继续、硬停和严格replay。
不修改原remaining8 adapter或其源指纹，避免破坏旧封存重放。prepare同时核两份公开旧seal，
确认后四恰好从未发送、observed:1为未认证终态，逐项核47源码和原始完整input/request/cell SHA。
测试专用固定原SHA/LF映射不进入生产，源码内容漂移仍拒绝。没有新架构、Provider合同或默认产品入口。

| 项目 | 准备范围 |
|---|---|
| 顺序 | observed:2、observed:3、observed:4、observed:5 |
| 最大调用 | GLM8 + Flash4 = 12；四个真错控制每个最多初评/编辑/fresh |
| 最大tokens | 1,161,216，保守每调用96,768 |
| 时间 | 整批活动3600秒/Host86400秒；每案900秒/5calls/401920tokens |
| 单次 | GLM600/Flash300，受剩余截短；输出32768 |
| 未缓存保守估价 | 12.0078336元，非硬计费封顶，实际回执另算 |
| 新run | data/runs/model_comparison/document-remaining4-time600-20261011 |
| 主审/独立 | 01a1261f-94b1-7510-8d72-fd5514789015 / 01a1263f-db97-7e02-bd7e-70b3a11b59ce |

真实Provider仍为GLM-5.3/high与GLM-5.3-flash/high；Codex开发模型不改变产品模型。
当前只做prepare、断网接缝检查、独立工程审查和提交/CI，没有新的Provider调用或run。
旧批不能续跑，不能把旧余量移给本计划；执行需要用户确认这份具体新预算及同HEAD全绿CI/
clean exact checkout、即时真实native预检后首次启动，唯一runner并冻结源码/HEAD。

本机7项离线检查通过（71.27秒），覆盖精确未发送库存、旧module隔离、固定请求拒篡改、
初评语义拒绝后继续四独立案、编辑/fresh三阶段接缝、硬abort、checkpoint错误、严格回放及
create-only封存、生产拒绝LF副本。Provider与Host为合成，仅证明工程接线，不证明四例质量。
编译、治理及diff检查通过。公共同提交CI与即时native仍是实际首次发送前检查，不能用旧CI代替。

真实独立工程审查无blocking findings，独立离线7项再次通过（70.65秒）；逐项实核47原源码、
旧138原件和5认证stage的真实native，observed:1原事件仍被双dispatch门拒绝。原生工程终答与
工具条目证据见[`document_remaining4_engineering_review_20261011.json`](../../data/evaluation/results/document_remaining4_engineering_review_20261011.json)，
工程复核不替代业务全文审查。主审实读该真实completed/唯一final及当前lineage/单dispatch可用，
不保证未来容量。方案已create-only准备，SHA
`b44521f21789195e3b9a5ccd5b9108d7ad6a6f725111aead79b5331d47f0de1b`；
原字节文件SHA`cb8d2104896c07df371e338943175229e607a27f056517e2cc16462b6e2c5086`，
公开原件[`document_remaining4_preparation_20261011.json`](../../data/evaluation/results/document_remaining4_preparation_20261011.json)。
Operator `C:/Users/33502/Documents/Agent/outputs/riftcoach-remaining4-20261011`；尚未授权execute，
没有创建新run、读取Provider密钥或发送模型请求。

## 执行与失败分支

统一入口`python -m scripts.document_remaining4_adapter {run|handoff}`，handoff一律绝对run路径。
每stage先material严格复建及完整source、history journal、实际请求/响应/编辑操作和全部policy。
精确checkpoint/path SHA投递；主审和独立各自全文核事实、解释、修法、editor reason、引用及保留内容，
不读对方意见。作者恢复及final前重读同checkpoint、自己的JSON check-answer、唯一多行JSON原生final。
主审实读真实事件后submit，不代写、裁剪或伪造。接受的revision/final四项ReportAssessment全真；
fresh pass>=85且无实质误报漏检。泛指不补全称，措辞不升级真错，Host标签不发Provider。

语义拒绝停该案依赖阶段并继续独立案；身份/来源/native/checkpoint/协议/transport/预算/主体不可用
硬故障helper abort停全批。无重试、重评、重开或资格；不得通过新候选绕预算或失败裁决。
关闭后只读replay、create-only公开白名单、真实native核验、原件SHA与实际账目，更新当前状态及计划。
自动任务保持PAUSED；等待无变化保持安静。

四例即使全过也不弥补未认证两例，不拼正式完整15，新增资格0。收齐独立案例后再综合全部正反证据
裁决共同语义机制，正式同版本15、自然消费、8E与全部产品/学习依赖仍保留。
