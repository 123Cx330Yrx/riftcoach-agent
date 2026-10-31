# 原15固定报告逐项执行

本入口评估同一候选合同1.6.6，使用原15完整报告、来源与5accept/10reject标签。
不生成新报告，不继承旧版本成功，不作为新holdout或产品准入。费用授权以当前Control中
绑定最终plan SHA的有效grant为准；旧自然任务grant不能使用，不自动延长期限。

## 执行约定

每例依次为facts-initial、completion-initial；需要修改时，再经Host compatibility与edit、
程序唯一应用、实际同稿facts-fresh及completion-fresh。每个业务门均须主审全文判断与
独立作者原件→check-answer→真实native final→唯一导入。两初审均pass时结束该例，
不声称编辑成功。原标签只在执行结束后比较，不进入模型或独立作者材料。

原15顺序由prepare生成的coverage固定。每个case独立session、transport、journal；
前例完整只读回放（含真实native、作者原件、成功/失败transport收据及用量）匹配后，
才能启动下一例。错标签或真实语义拒绝保留成功前缀与最早停止证据，不能用格式恢复
将其改成通过。该候选不满足本轮评估不意味着历史成功证据消失。

顺利时按标签预计50职责审查；结构上每例最多4职责+4手动补测，15例最多120实际
请求、9646080 tokens、每例3600活动秒。报价输入0.5/输出2.5元每百万tokens，
全部最大未缓存包络估价8.7552元，不能当作账单硬限。超时的未知预留另列，不当已知账单。

## 准备与原根

在最终clean执行checkout、指定Python实际启动；下列命令中的变量由最终控制器固定，
不是让用户猜路径、thread ID或SHA。源码、原输入、候选、cwd/Python/Codex与plan绑定。

```powershell
& $Python -X utf8 -m scripts.sol_original15_launch prepare --operator $Operator --primary $Primary --independent $Independent
& $Python -X utf8 -m scripts.sol_original15_launch native-task --operator $Operator --plan-sha $PlanSha
```

native-task只做行政作者/check-answer/native导入预检，0模型请求；它不证明业务审查质量。
独立作者必须使用生成的完整dispatch，实读精确checkpoint及其SHA，写指定run外原件，
check-answer通过后只给一次完整多行native final。主审读取真实事件后提交自己的判断。

**每次可变操作都保存原始stdout和退出记录，立即固定stdout SHA。** 从stdout中保留
最初guard和每次最新checkpoint根，不能事后从checkpoint文件重算冒充原输出。
`--roots-file`是case→`{guard_sha256, checkpoint_sha256}`，其文件另用`--roots-sha`绑定。
native预检的最新两根另存为`--preflight-proof`。锁是内核互斥设施，仅协议规定的
session.lock不纳入证据字节库存；其他.lock文件仍核验，重定向/硬链接仍拒绝。

## 逐项发送及Host导入

新费用grant应绑定grant_binding返回的具体plan、HEAD、合同、分组和包络，最多24小时，
不自动延期。执行前验证同HEAD公共CI全绿、clean源码与完整输入、真实native预检。

```powershell
& $Python -X utf8 -m scripts.sol_original15_launch run --operator $Operator --plan-sha $PlanSha --case $Case --roots-file $Roots --roots-sha $RootsSha --preflight-proof $Preflight --authorization-file $Authorization --authorization-sha $AuthorizationSha --ci-run $Ci
```

发送器先不读Key回放到实际新请求边界。Host审查等待、查看、导入、关闭和只读回放均
不读Key。只有新请求前才隐藏提示天机阁企业Key，用户等待输入不消耗活动秒；输入后
仍按真实UTC重查授权期限及文件绑定。普通run不会自动补测、循环15例或跨越Host门。

本机Control/start-authorized.ps1在交互运行时先显示记录核验提示。成功记录重放完成后才
出现隐藏Key输入；输入后还有发送前核验，因此回车不表示已发送请求。等待期间沿用现有
进程，核对其stdout和退出记录；不要重复启动。此提示只改善等待说明，不改变核验或发送。

```powershell
& $Python -X utf8 -m scripts.sol_original15_launch task --operator $Operator --plan-sha $PlanSha --case $Case --authorization-sha $AuthorizationSha --guard-sha $Guard --checkpoint-sha $Checkpoint
& $Python -X utf8 -m scripts.sol_original15_launch submit --operator $Operator --plan-sha $PlanSha --case $Case --authorization-sha $AuthorizationSha --guard-sha $Guard --checkpoint-sha $Checkpoint --key $Stage --primary-file $PrimaryFile --event-id $EventId
```

task只显示尚未导入任务的原始dispatch，同任务恢复只用MESSAGE，不再NEW_TASK。
这里指工具层消息类型：首次派发用`collaboration.followup_task`；同任务在现有运行者上只用`collaboration.send_message`。`followup_task`即使正文以MESSAGE开头，也会生成新的NEW_TASK。不要仅凭原生API的interrupted快照再次followup；先核协作运行状态。若已出现重复派发，保留全部真实消息及唯一作者/final，记录本地交接故障，不裁剪记录、不覆写final、不重发Provider、不将其判作模型语义失败。原reader继续拒绝重复派发。
submit后从本次原stdout更新根。仅推进Host/关闭时给run加`--host-only`；遇真实发送边界
会暂停，不提示Key。新一例也须显式指定当前case。

### 本批单事件交接恢复

2026-10-26用户明确要求“处理”后，仅对claim-scope:4/facts-initial的既有事件启用
`scripts/codex_dispatch_recovery.py`的固定SHA外部适配器。它先复现原reader拒绝，再从真实
native读取并核对四条完整派发、父/作者/唯一final及membership、checkpoint、material和
作者原件；全部绑定精确事件和原始SHA，逐次回放重新验证。其他事件走原reader；legacy
dispatch政策不允许该恢复。保留两次NEW_TASK事故，不声称加密输入等价已验证，也不重写意见。

当前批次后续submit/run/replay/seal必须经Control/operator.py的`host_events`，由
settings中的原plan SHA及恢复manifest/module SHA固定启用；恢复前operator/settings快照保留。
直接调用冻结CLI仍会因该事故拒绝，这是预期，不能改冻结reader使其通过。原费用grant及期限
不变，恢复本身0请求/0Key，不关闭整批。原失败和新恢复证据分别保留，不能把原失败改成通过。

## 暂停、恢复与封存

- HTTP524/已验证timeout或明确格式错误：只暂停当前项。上游恢复后，在同一run命令
  显式加`--manual-retry`，每次仅授权一次同请求恢复；成功前缀、失败收据与已知/未知
  用量保持。普通run只返回等待，不提示Key、不补发。
- 身份、来源、补丁、真实语义或观测硬错：保留最早停止，不能借手动补测越过。
- 进程中断留下unresolved intent：普通run禁止重发。只有已有完整原始响应可以通过
  `reconcile`只读验证transport并导入原响应；缺响应/未知状态先诊断，不能当未发送。
- 包络不足：先暂停，提出具体扩展，不把预算错误伪装成模型质量失败。

```powershell
& $Python -X utf8 -m scripts.sol_original15_launch reconcile --operator $Operator --plan-sha $PlanSha --case $Case --authorization-sha $AuthorizationSha --guard-sha $Guard --checkpoint-sha $Checkpoint
& $Python -X utf8 -m scripts.sol_original15_launch replay --operator $Operator --plan-sha $PlanSha --roots-file $Roots --roots-sha $RootsSha --authorization-sha $AuthorizationSha
& $Python -X utf8 -m scripts.sol_original15_launch seal --operator $Operator --plan-sha $PlanSha --roots-file $Roots --roots-sha $RootsSha --authorization-sha $AuthorizationSha
```

replay严格不改Operator或作者原件；独立核原响应与请求、HTTP状态、观测、known/unknown
tokens及手动恢复分类。seal只在15例匹配完成或确认最早失败后create-only写Operator/seal.json。
永不自动授qualified/发布。真实DB/API/UI消费与自然Coach/Training仍需单独验收。
