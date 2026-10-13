# 前瞻三阶段证据入口

2026-10-13。接续post-joint-consumption的工程范围，保留现有初评→必要编辑→完整终评及共享预算；不采用关系教学、不开放生产、不启动新付费批次。

## 问题与实现

旧full15已有三阶段业务状态机和严格回放，但缺少后来用于单次初评的run外作者文件与观测检查。新入口把这些检查放到实际交接位置：核对全部证据后才接受审查或允许下一请求。它保护的是证据完整性，不能把错误模型判断变成正确判断。

`scripts/full_chain_evidence.py`提供`FullChainEvidence`与prepare/task/submit/abort/replay/seal命令；没有付费execute命令。程序化observe复用原15控制、TimedDocumentWorkflow、TimedDocumentBudget和原状态机；每case仍5调用、401920 tokens、900活动秒，GLM600/Flash300受剩余时间截短。Host等待时间独立计时。固定原15仍不包含自然生成。

`scripts/full_chain_modules.py`仅在私有模块的builtins表中路由明确依赖，使旧runner函数内部导入的evidence也指向同一个私有实例。没有覆盖公共模块、全局import或旧源码，也没有复制业务状态机。私有模块以独立名字注册供类型解析使用。新身份、精确路径和新增源码SHA加入plan，旧plan不能进入新入口；历史回放仍用原模块。

### 数据与控制流

1. prepare核验绝对cwd/Python路径并实际启动解释器，检查导入的是当前后端模块。输出create-only准备文件，不创建run、授权或Provider请求。新plan的execution_authorized/execution_ready均false。
2. 三阶段使用`case/{initial,revision,final}`路径。publish_task生成唯一完整任务、checkpoint和完整dispatch；独立作者只收到该任务及其绝对路径/SHA、解释器和run外作者路径，不接收主审或预期标签。
3. submit前检查白名单、链接、作者文件和已完成请求的观测。读取native后，在原提交锁内再次检查；作者JSON必须与native判断一致。写入`evidence-guard.json`，固定作者原字节SHA、checkpoint SHA及当时全部观测文件SHA，再由原原子发布过程写submission。
4. 等待、stage接受、下一发送以及已创建transport预留后的子进程交接前再次检查。已提交作者即便只改空白也会被SHA检查拒绝；未知run文件/目录、run外孤立观测、链接、观测漂移均阻断后续发送。错误目录或旧plan在创建锁文件前拒绝。
5. `scripts/full_chain_observed_transport.py`为GLM审查及Flash编辑分别记录run外无正文观测，绑定实际请求SHA、原transport、worker目录和direct路由。沿用SDK/子进程，模型、policy、schema、重试和时间上限不变。完整响应缺有效观测硬停止；失败尾项可保留unavailable/incomplete，不能当成功。
6. replay复用原源码的请求重建、预算、Host原生事件和阶段检查，再核新库存/作者/观测。对run及run外原件做前后快照；关闭后不触碰锁。seal只能create-only写到run、作者和观测目录之外，不能用移动/删除异常文件使旧证据通过。

有效语义拒绝结束当前case依赖并继续下一独立case；身份、来源、checkpoint、协议、transport、预算、主体或证据硬故障停全批。污染或篡改的证据不能严格封存；保留原件与失败，不把拒绝封存当作待清理文件问题。

## 可复现验证

```powershell
& D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe -B -m pytest tests/test_full_chain_evidence.py tests/test_full_chain_observed_transport.py -q --tb=short
```

工作目录为`D:/riftcoach-agent-rq192-pr`。测试使用提交内原15来源的明确两case子集，网络被禁止或严格限于127.0.0.1；没有把这个子集改为实际资格样本。

- 完整三阶段及下一正确case：真实作者文件写入→实际check-answer CLI→模拟native原始事件→真实导入/submit→只读replay/create-only seal。验证原件不变、同一共享账本、Host等待不占模型活动秒、final剩余350秒及下一case重新分配600秒。
- 三个stage分别覆盖额外文件、native读取期间污染、作者判断不一致、提交后作者原字节漂移、checkpoint错配、观测缺失/漂移及900秒任务截止；确认没有下一请求。
- 三个stage的有效语义拒绝继续下一独立case。原模块对象保持、旧plan无写入拒绝、错误task路径和seal位置拒绝、孤立观测拒绝、绝对路径实际启动另有检查。
- 两模型各做完整返回/提前EOF，使用真实子进程、SDK和本机HTTP。观测绑定/无正文记录/读后不变/篡改拒绝均核；HTTP仅本机回环，项目模型服务调用为0。

以上native响应是明确替身，作者与check-answer/导入/锁/文件IO是真实代码；不能称真实独立Host已完成演练。测试终答不授语义或产品资格。

## 准备结果与运行边界

`data/evaluation/results/full_chain_evidence_preparation_20261013.json`保存当前原15输入及源码绑定，路径指向新的prospective run和独立operator目录。它继承原15构造器的最坏包络，**不是新45次成本提案或授权**；未创建该run，未读取密钥，未派新Agent或真实Host任务。公共CI按本次提交核验，不能沿用旧绿。

下一项为该新入口的真实无付费三阶段Host演练与具体版本/资格接缝准备：复用既有独立主体，明确模拟业务响应，完整原样dispatch、作者自己的答案和真实native事件。真实演练后才可形成需模型调用的具体范围并核对应成本授权、冻结版本、公共CI、即时主体与启动预检。旧已关闭授权、结果和缺口不迁移。

默认产品仍未接time600；同版本完整15质量、自然生成/工具消费、Worker阶段间取消、真实DB/API/UI/journal仍未完成。阶段8E、Coach/Training、四块联动、前端审美头像、Memory、身份运维、两树整合及独立评估/学习保留。这里提供代码、流程及可复现验证，不表示Owner理解已验收或子阶段已退出。
