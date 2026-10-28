# 双初审重叠补丁：诊断与恢复方案

目标：两位审查者正确指出同一处错误时，保留两份原意见，生成一份能覆盖两项意见的新稿；不靠重复购买初审碰运气。

## 已确认的事实

原15已完成12例。第13例observed:3两项初审及各自完整来源双审均已接受：facts为92/needs_revision，completion为90/needs_revision。两者都只纠正block_21把ShowMaker比赛误归阅读者的错误，保留8.805和1.5；before逐字相同，after措辞不同。原程序在preview拒绝任何区间重叠，实际执行停于compatibility/edit任务生成之前，没有application或fresh。冻结源码原函数零发送重现精确异常direct_patch_overlap_requires_new_joint_design；原件与作者库存未变。

这否定了“两个独立补丁总可直接无重叠拼接”的设计假设；本例不构成模型审查语义失败。两项新调用均正常返回，无超时、未知用量或重试。前12成功、本例原稿及两份意见、旧失败与费用全部保留。原版本结果不可改写成通过。

证据：Control/observed-3-exact-overlap-diagnosis.json；data/evaluation/results/sol_original15_observed3_initials_accepted_20261028.json；observed-3/session/terminal.json及0033 checkpoint。外层原始记录的只读核验/封存与恢复设计分开。

## 路线选择

| 方案 | 判断 |
|---|---|
| 重买初审，期望措辞或范围变得不重叠 | 拒绝：已有两份正确意见，新请求不修复组装机制。 |
| 固定事实优先、忽略另一份补丁，或按字符串相似度自动合并 | 拒绝：可能漏掉另一职责的实质要求，文本相近不等于语义兼容。 |
| 显式冲突协调，选择已有替换并验证两份问题覆盖 | 首选的离线修复方向：不新增模型请求，保留来源与原始补丁，不能靠选择顺序冒充语义判断。 |
| 合成任意联合新措辞 | 本包暂不采用：扩大作者责任和改文范围。没有现成候选能完整覆盖时如实保持未解决，再独立设计。 |

## 拟实现的数据与控制流

1. 将每个原始edit按职责、repair组、issue_ids、原文区间和原稿SHA建立不可变引用；issue身份必须带职责，不能把两个issue 1混为同一项。
2. 构建重叠连通分量，保留全部原操作。非重叠路径逐字沿用；重叠不再直接丢弃，也不直接应用。
3. 在原preview之前增加显式的Host冲突协调记录。每个分量只能选择完整的一条或多条已有原edit，所选操作必须互不重叠；记录选择、舍弃和两职责全部问题的覆盖理由。初始实现不生成新after。
4. 主审和独立作者完整读取同一原稿、来源、两份公开意见及全部候选，验证所选替换确实覆盖该分量两职责的要求，并保留正确内容。仅编号覆盖或两份文字意思相近均不够。不能达成一致则保留未解决状态，不重买初审。
5. 按批准的具体原edit只组装一次；其余正确内容、来源、章节与知识引用照原校验。既有compatibility和四项ReportAssessment整稿双审仍执行，不能用协调意见代替。
6. 唯一application后，两项fresh必须核实际同一新稿。仍按已有超时恢复规则保留已完成项；新增真实调用仅在准备和有效费用范围核实后安排。

新增记录必须绑定原稿/输入、两份原意见、候选、选择、作者和native原件SHA；replay重新验证选择及所有原校验，不能修改旧两份意见或补写已不存在的兼容任务。具体接线涉及review_duty_direct_patch、NaturalDutyWorkflow、SessionWorkflow/Host gate及回放消费方，不能只改preview的一个if。

## 零付费验收与恢复边界

先验证本次真实反例及通用边界：两条完全相同操作、相同before而after不同、部分区间重叠、三个操作形成的连通冲突、跨职责重复issue编号、遗漏问题、选中操作仍重叠、候选/原件/选择被改动、无重叠正常路径。确认错误选择不能仅凭结构检查通过，完整整稿审查和同稿fresh始终必需。

冻结执行树和原15计划保持；开发树中的新设计不能冒充原版本结果。若进入真实恢复，必须先形成明确版本与原证据继承记录：复用本例正确初审，不重发前12，不清零累计费用；旧失败不删除。不能把旧12、新组装恢复13、剩余2直接拼成原版本全15资格。后两例当前未执行，产品仍未准入。

## 2026-10-28 本地实现与实际预览

开发树已实现完整的显式协调消费路径：direct patch保留全部原操作及重叠连通分量，使用稳定清单SHA绑定选择；SessionWorkflow先持久化选择，再发布独立patch-coordination任务，随后仍经过原compatibility、edit、唯一application与双fresh。没有选择时仅暂停，没有悬空intent或关闭记录；恢复从原选择继续。意见原文仍按原字节保留，JSON对象字段排序不改变同一清单的SHA。非重叠路径与原journal保持兼容。

正式开发启动器支持run的--patch-coordination-file/--patch-coordination-sha。必须对应既有patch-conflicts记录，在CI、Key和发送前验证；未开始的例子不能预塞选择再购买初审。其余action不接受这两个参数。启动器仍拒绝有seal的原Operator，没有开放重开旧批。

真实第13例的零付费准备位于C:/Users/33502/Documents/Agent/outputs/riftcoach-original15-overlap-preparation-20261028。已核原seal和2184件库存、两份material/submission/checkpoint及作者原件SHA，用实际journal中的原始response和原始request生成完整材料。显式提案选择completion的完整原after（op_2），因其明确写出“观摩对象ShowMaker”且完整保留四中单与8.805/1.5；facts的op_1及其完整意见保留为弃选候选，不否定该意见。预览SHA eae9605e45cb6b1f02ee37ae76f255232a528ec414ac8c1b012af9b7688fb21d，仅第21段的一句变化，其余27段逐字保持。preparation SHA 80eef3751b5c5cd7f21bfd5a10f6058b3590164be1d7ef59f72e54846addfe29。

这是未批准预览，不是实际application、当前native接受或fresh结果。准备辅助脚本两次零发送断言/文本哈希错误保留说明；修后逐件核对已有四份预览文件，没有覆盖原执行或重新调用模型。当前没有建立真实恢复session，没有读取Key。

## 接续接口与下一工作包

本地协调路径与封存记录继承是两个独立接口。真实observed:3的前8个操作依次是model/journal/host-task/host-decision各两组；第9个才是失败outcome。后续恢复必须使用新版本与独立目录，精确继承前8步和两份已接受原件，而不是删除第9步或修改原terminal/seal。两份初审累计43742known/0unknown/0retry、原批43HTTP/773045known/195578unknown预留/3retry，以及旧活动时间2727.218秒均须保留。新请求只能是实际新稿的双fresh或已有规则允许的手动传输补测；不重新购买初审或前12例。

继承器、真实native协调/整稿双审及实际双fresh仍待完成；开发启动器的参数接通不能代替该继承器。下一步复用已有sealed-parent导入模式，先在新目录做零发送的原件→实际native回放→协调任务边界核验，再冻结版本/CI并核对有效授权与剩余费用。当前原独立作者线程仍能读取，协作工具未列出可恢复的live agent；尚未向其发送新任务，也未更换作者。

未来资格判断需区分原冻结版本结果与修复版的整体证据；不把开发预览拼为原版本全15通过，也不由此要求重买已成功模型输出。先验证证据在修复版中的等价消费与必要剩余项，再据既有合同判断能支持的结论。本工作不授权新付费批或改变产品准入。


## 2026-10-28 第十三例封存前缀继承与真实零发送核验完成

新继承器精确保留第13例前8步、两项attempt、全部原transport及两份journal共38件原字节；原第9步失败outcome/terminal/seal留在原目录。两项原生事件与作者原件经当前真实读取重新校验，两次成功回执重新消费，新工作流准确回放至协调选择边界，未读取Key、未产生新Provider或新native任务。准备目录临时session已清理，尚未建立真实恢复session。

保留本例2HTTP/43742known/0unknown/0retry和2727.218活动秒，原批43HTTP/773045known/195578unknown预留/3retry及前12例成功不变。原3600秒尚余约872.782秒；后续不可清零时间或借新目录扩预算。继承器没有授权能力，缺发送guard在模型intent之前拒绝。原件库存/作者变化、伪造历史账目/时间/句柄/路径均拒绝；已接受旧句柄不能补签重交。

模拟整链成功/拒绝两项99.58秒通过；增加实际准备入口、缺send guard与父库存变化断言后成功分支87.24秒通过。真实预检preparation SHA a79630b1030424ddb8b2b76811e5ceaa04052bd47d67e9522dcf744f26a16f8f，parent proof SHA693137059c51344dad6ed37350946b38f490a22bc2e19a4f7a25f2bde1d709e4；最初guard及退出checkpoint取原stdout记录，非事后重算。第一次模拟读取terminal层级错误已修正并保留说明。证据data/evaluation/results/sol_original15_patch_inheritance_local_20261028.json。

下一动作：将该继承器接入独立版本的恢复启动器，固定来源/HEAD/CI与原有效授权/余量，再发布协调及整稿双审，最后才发送实际同稿双fresh。当前paid_launcher_ready=false；原15仍12/15，observed:4/5未测，automation PAUSED、Stage8E和产品未准入保持。

## 2026-10-28 恢复启动器实现中

scripts/original15_patch_recovery_launch.py将原seal/proof、原授权及有效续接、原余量和明确协调文件绑定到独立版本。准备与Host-only不读取Key；本地已接受前缀先回放到真正新发送边界，才验证精确HEAD公共CI与当前授权并从Windows Credential Manager惰性读取企业分组Key。每个片段最多新增一次模型调用，下一片段继续原检查点，不自动循环或重发成功项。

原grant及续接字节均不改写，绑定本例原guard的authorization SHA，不为新目录新发费用或延长时间。原case3600活动秒与全批请求/token余量照旧扣除，旧43次与未知用量预留始终保留。缺原续接、过期、预算不足、未决历史intent、源码变化均在新IO前拒绝；Host-only仍可完成已经返回意见的审查。

运行、task、submit、status、reconcile、只读replay及唯一seal接同一新session；旧两份native不能重交，正式新任务沿用原独立作者。正常成功和语义拒绝均需严格外层回放；明确524超时沿用原手动补测机制暂停同项，未手动触发不读取Key或发送。reconcile仅消费已完成原回执，不重发未知请求。

当前先跑实际启动器与mock HTTP/native整链，覆盖正常、协调拒绝、过期、Host-only、超时及手动恢复。首轮模拟发现发送guard把正在持有的model intent误当成遗留未决请求，已按operation→capture_attempt的真实顺序修正；遗留未决请求在打开片段时仍拒绝。测试helper的递归路由替身也已改正。尚未部署真实恢复启动器或读取Key。

## 2026-10-28 恢复启动器本地验证完成

恢复启动器已接通原授权/续接、原账目和活动时间、精确新HEAD及真实发送边界CI。Host-only与native等待不读Key、不查CI；每片段最多一个新fresh请求。正常成功、协调拒绝、524后普通resume零发送及手动同项恢复三条模拟整链通过（3 passed / 543.03秒）；最后作者run外路径及严格回放修正后成功分支另行复核通过（1 passed / 177.58秒）。测试HTTP/native均为替身，不是模型质量证据。

原真实授权续接文件已核验，截止北京时间10月29日00:25:43，未延长或清零。开发期路由替身递归与当前owned intent误拒绝已修复并留痕。当前新增Provider/Key均0、尚无真实恢复session；下一动作：提交并冻结独立执行副本，先完成零发送patch-coordination、compatibility、edit双审，再于同HEAD公共CI全绿且原授权/余量有效时发送同稿双fresh。原15仍12/15，旧失败、费用、seal、automation PAUSED和产品未准入保持。

证据：data/evaluation/results/sol_original15_patch_launcher_local_20261028.json。


## 2026-10-28 唯一应用及测试维护CI续接

第13例两份初审复用；patch-coordination、compatibility和edit四项双审已接受导入，唯一application完成，新稿eae9605e。0035 paused checkpoint SHA7a04d08b66cda6078749b387c2a5c610e9ae1931eb9fbbd566f147b8c471e57e停在facts-fresh发送边界。原15仍12/15，新增Provider/Key均0。冻结58a947ca公共CI40646310462两项失败，原因分别为旧当前库存快照未更新、application回放测试替身缺verify_assembly。修复8c05a3c4只改两测试和新增当前库存，不覆盖历史库存；28项测试与治理通过，新CI40653270119运行中。Control行政续接SHA069e37f8逐件核唯一三文件提交、冻结执行源码/业务输入不变，保留原plan/guard/0035/作者及所有原账目；10项本地边界检查通过。明确此为测试维护提交CI与冻结执行源码等价的同HEAD条件例外，不宣称原失败CI变绿。下一动作：修复提交CI全绿后续同稿双fresh及完整来源双审，再严格只读回放封存；不重新prepare或重买初审。原授权截止、763.111活动秒余量、旧费用/失败、Stage8E和产品未准入保持。
