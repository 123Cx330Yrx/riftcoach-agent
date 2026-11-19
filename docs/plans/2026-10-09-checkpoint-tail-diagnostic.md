# 固定Host任务入口的六例尾链诊断准备

本方案为新的独立批目录`document-checkpoint-tails-20261009`，不重开已关闭六尾链。
仍检验六份真实accepted历史初评之后的必要编辑/fresh；只修Host任务交付/停止/封存
入口，不改六个Provider输入、模型、政策、预算或采用质量标准。
准备阶段没有Provider发送、批目录或等待器；付费执行需要此具体方案的新明确授权。

## 选择与不变内容

顺序`scope:4`、`claim-scope:6`、`observed:2`、`:3`、`:4`、`:5`，每案Flash必要编辑，
整稿真实双审接受后才发GLM-5.3/high fresh。历史初评来自已封存十一初评扫描，只取
六份真正双审接受needs_revision的原件；不重买初评、不重签历史初评。
两处原分歧`attribution:1`、`scope:3`仍不下传，不用本批重新评级它们。

旧首案编辑虽完整返回且主审暂接受，但独立错绑、没有有效双审或fresh，不能当已完成
尾链。新方案对六案统一观察新编辑→fresh，旧一次失败和用量继续保留，不迁移原件或
冒称继续旧批。正式15不与这些分批结果拼接；同批15及产品资格标准不变。

## 新入口的数据与控制流

`scripts/run_document_checkpoint_tails.py`复用冻结旧`controls/observe`：所有历史原件
摘要、完整初评输入、六份editor request和fresh构造、共享budget/clock、SDK零重试
及单例语义失败分流保持。新preparation显式增加run_id、checkpoint/abort合同及四项
新源码摘要。旧observer结果里的experiment是原workload标签，plan和seal另含新run_id，
不会把它误当旧目录重开。

新handoff/seal沿旧严格来源/transport重建逻辑建立前瞻版本，保留旧文件供历史封存
精确回放。新变更只在新入口生效，不能修改旧SOURCE_FILES使旧封存失去可重建性。

每个待审stage：

1. 主审先独立核完整来源、原稿、实际stage/response/reason、全部改动和保留内容。
2. 新handoff的`checkpoint`先按实际回执重建精确task，附完整初评/编辑或fresh政策，
   在operator目录create-only发布task/checkpoint/dispatch。恢复后及final前必须重读同一
   绝对路径和SHA；独立作者不得搜索旧task或读取primary/其他Host意见。
3. 作者独立全文成稿并用checkpoint helper检查自己的JSON，原样native final输出。
4. `submit`必须提供原checkpoint路径/SHA，核对原task与当前完整材料重建完全一致，
   从实际Codex native event获取独立意见；现有四项ReportAssessment及全文native质量
   校验保持。任务/checkpoint原字节与其摘要随stage留存，关闭后可独立回放。
5. 只有真实双审通过才进入fresh或下一阶段。路由一致、离线测试、CI或高分均不能替代
   内容正确；fresh须pass且>=85、无实质误报漏检。

运行时也在旧observer核native/全文质量之前强制核完整task与checkpoint快照，不能
绕过handoff提交或拖到末次seal才发现漏pin；缺少checkpoint在下一次发送前硬停止。

Host标签不发Provider。泛指不补全称，样本描述/否定证据充分性与明确因果断言区分；
措辞建议不升级事实门。ADR0116否决的全段解释账本不复活。

## 故障、成本和关闭

有效整稿语义拒绝停该案依赖阶段，继续其他独立案；身份/来源/native/checkpoint/
协议/transport/预算/主体不可用等硬故障停全批。不重试、重评、重开关闭批或自动授资格。
新`operator-abort.json`是明确的操作员停止记录，不是独立意见或native attestation：
绑定当前待审stage和有限reason码，OS关闭锁/原子发布，原runner finally自行记真实
calls/known/unknown、Host/活动时长和未执行案。无效marker或与submission冲突仍失败。
新seal核marker与实际硬关闭一致，不能造receipt、意见或成功stage。
停止信号只核保存计划和当前pending binding，不依赖已损坏的来源重建；来源损坏仍可
关闭账目，但严格seal必须拒绝source_changed，不能宣称原件完整或补造成功封存。
已有review-submission落盘后，live material/checkpoint拒绝重新交付该stage。

预算保持最多12次新调用（Flash编辑6、GLM-5.3/high fresh6），1,161,216 tokens、
3,600活动秒、86,400 Host等待秒。每次上限32,768输出tokens和300秒，SDK零重试。
按64000输入/32768输出的保守未缓存估价9.4347264元，非硬计费封顶；unknown用量
保守预留，不因无回执当免费。单次执行前要求clean exact HEAD、同提交公共CI全绿、
真实主/独立谱系和native路由预检；已存在批目录在CI/凭证访问前直接拒绝。

## 证据与限制

实际新任务入口及故障关闭的离线检查使用已提交公开seal构建synthetic IO，禁止读取
本机data/runs。工程替身不能证明真实编辑/fresh质量。已有两次真实alpha→beta路由
探针和89项检查支持精确任务切换，仍未复现自动compaction或证明長全文跨压缩稳定。
新业务stage继续逐项核实际材料及native final，不能把探针当业务认证。

本次11项离线检查全部通过（114.58秒）：完整六例12调用替身往返、语义拒绝继续
其他案、显式abort、来源损坏可停但不可封存、漏pin发送前停止、摘要篡改、提交后
关闭窗口、重复提交和既有目录付费前拒绝。测试禁止读取本机data/runs。

六尾链通过也只是accepted-history-conditioned覆盖。两处分歧、同版本正式15、自然
产品消费及8E仍有依赖；旧文档3/15与历史严格2/15分别保留，新增资格0。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/重做/头像、
Memory、身份运维、两树整合和八维学习继续保留在活动计划。

冻结方案SHA：`231338b6b8ef970600e322311b82f2d68489cb5c3b527c3659d4d267cff93aeb`。
公开preparation/readiness为`data/evaluation/results/golden_document_checkpoint_tails_*_20261009.json`；operator资料在
`C:/Users/33502/Documents/Agent/outputs/riftcoach-document-checkpoint-tails-20261009`。
实际六份历史原件、全部请求/身份/预算精确核对通过，旧SOURCE_FILES与闭批21原件摘要不变。
最终独立代码复核无剩余缺陷；实际native final事件
`01a0ebaf-790b-70b2-9f02-9e354d9ea50b/01a11ee7-23b7-7803-956d-61b0019dfe28/msg_0f1ffc23fbabd630016ac86c781e7c8191a9196128afb5dc63`
已按当前checkpoint严格读回，真实谱系/当前native路由预检通过。
三次代码复核原生输出多余括号严格拒绝、原样保存；最后由作者用多行JSON重新输出，
没有主审裁剪或代写，不是闭批业务重评。作者本地JSON通过不能保证native原样输出，
后续业务stage继续严格读取真正final；不能把本次格式修正声称为长期稳定。
公共CI必须对应最终提交，执行前主体/路由重新预检，不能拿上个提交CI或缓存预检代替。
本文件不构成用户付费授权：execution_authorized=false、Provider0、无run/等待器，接续PAUSED。
