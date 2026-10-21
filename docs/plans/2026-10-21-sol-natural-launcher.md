# 自然任务实际入口与零付费预检

## 目标与范围

把已经实现的持久会话接到自然观摩应用的实际命令入口。一次任务在各审查点暂停，
恢复时沿用原报告、工具结果、预算、失败与未知预留，避免重复生成或重复购买审查。
本工作包不启动付费请求，不沿用原六次批或补测授权，不改变产品GLM采用及五调用合同。

`scripts/sol_natural_launch.py` 复用 CandidateSession、SessionReviewGate、真实应用准备函数、
两角色传输和原生事件读取。旧固定批启动脚本不改为新的执行队列。
原准备函数没有将 execution_session 传给应用，本次增加显式传递；默认旧路径保持。

## 数据与控制流

1. `prepare` 在实际 cwd/Python 内捕获首请求，绑定完整源码、依赖版本、Skill/Profile、
   RAG和固定来源，写外部Operator的唯一plan。要求干净checkout，作者目录在Operator外。
   首请求摘要使用SessionBudget的相同超时归一化，并去掉仅在预算下游添加的标记。
2. `native-task` 只发布一份明确的行政夹具，实查原生主审/独立审查者身份。
   `task` 输出原存完整dispatch；作者写自己的文件并check-answer，再返回唯一原生final。
   `submit` 使用主审自己的决策和真实event-id导入；不代写独立意见。
   该预检证明交接可用，不是对业务报告的审查，不保证未来原生读取一直可用。
3. `run` 先查原plan SHA、干净精确HEAD、同HEAD公共全绿CI、未过期新授权及实际原生预检。
   获取会话进程锁并检查未完成intent/关闭/未审任务后，才加载凭据。
   用户已配置智谱时，通过与授权同路径的`--zhipu-env-file`复用原`load_role_settings`，
   只隐藏输入天机阁Key；未指定文件时保留两家手动输入。不搜索其他环境/文件，不落盘Key，
   拒绝getpass回退到明文输入。配置缺失或非智谱官方地址直接报错，不悄悄另找Key。
4. 每个新请求及重试再次核授权、来源与既有审查；实际应用遇到Host检查会暂停。
   恢复必须带最初guard和最新checkpoint，原授权字节、CI及预检根保留在session内。
   每段派生应用输出也保留摘要，下一段拒绝变化或未提交的输出。
5. `status`不发送请求；`replay`在临时派生目录重演完整应用，原Operator逐项只读核对，
   `seal`在成功回放后create-only写唯一Operator/seal.json。保留拒绝与未知预留，不授资格。
   进程丢失留下pending时沿用inspect_sol_session的显式原回执reconcile，不自动重发。

## 失败处理与交付边界

明确且已回收的传输超时依现有合同共用一次重试；身份、结构、语义及来源变化不重试。
重复运行未审阶段在读取Key前暂停；已关闭会话不重开。未完成intent保留证据待核。
如果派生输出已产生但进程未保存其摘要，也保留原件并阻止盲目继续，不删除后重试。

调用预算提案仍为6逻辑调用+1共享超时尝试、498688tokens、1200活动秒，
按既有价估算0.6170624元而非账单硬限。用户已对此任务明确授权；缺有效绑定授权时不执行`run`。
真正准备好还要求当前提交公共CI、干净冻结执行树、真实作者预检完成及发送前价格确认。

## 入口使用

所有命令都使用冻结执行树的绝对cwd和已经实核的Python，从`-m scripts.sol_natural_launch`进入。
`prepare --operator <外部新目录> --run-id <新任务> --primary <实际主审ID> --independent <实际独立ID>`。
后续命令都加`--operator`及原`--plan-sha`。`native-task`只能首次执行；
`task/submit/status`加原`--guard-sha`、最新`--checkpoint-sha`，行政预检加`--preflight`。
`submit`另需`--key`、`--primary-file`、`--event-id`；主审文件也置于证据目录外。
实际执行的恢复另外保留原`--authorization-sha`；不得事后重算并冒充最初保留的根。

`run`另需原授权文件/SHA、CI run及行政预检guard/checkpoint；首次没有执行guard，
恢复则必须带执行guard/checkpoint。命令缺必要参数会拒绝，默认没有付费动作。
`replay/seal`只消费已有执行guard/checkpoint/authorization SHA，不读取Key。
当前这份说明不是可复制的付费启动授权；具体路径、身份和冻结SHA以最终准备包为准。

测试使用合成响应与合成原生事件；验证完整应用暂停、作者导入、恢复、不重复发送、唯一应用、
完整回放、唯一封存，以及CI/身份/过期授权/首请求变化的前置拒绝。真实作者预检另行记录，
不把测试替身计入真实业务审查、模型可靠率或8E退出条件。

## 当前交接（2026-10-21）

实现冻结e1de08913606267db0c97f2ead95ffa723f9ed17，CI39534539078全部8项success。
执行树D:/riftcoach-sol-natural-launch-execution保持clean，真实作者行政预检及只读回查通过。
Operator为C:/Users/33502/Documents/Agent/outputs/riftcoach-sol-natural-launch-20261021，
plan SHA为76c1e683590542f5443a85abeeeb67101e40e7385a1fc73c668862e36033f84d。
同级riftcoach-sol-natural-launch-20261021-control/start-first.ps1为首次启动入口；
必须提供授权后生成的AuthorizationFile/AuthorizationSha，原stdout追加到create-only日志，
execution已存在则拒绝再次首次启动，恢复另用真实执行guard/最新checkpoint。
公开报价确认记录见Operator/pricing-confirmation-20261021.json及同日integration result。
用户随后明确授权，本次预算与截止已保存；未创建execution或发送模型请求。
用户指出智谱早已配置，原两家重输入口已在执行前撤下，原脚本/授权保持存档。
修正仅显式复用D:/riftcoach-agent/.env的智谱配置，天机阁仍隐藏输入；实际本地加载核实可用且为官方地址，
未输出密钥；这次读取属于配置核验，不记成“从未读取凭据”。15项入口回归通过（103.76秒），
预算、来源、模型角色及用户原授权截止不扩展。后续需冻结修正版和核该HEAD CI/实际预检。

修正后实际交接：HEAD084c415cbcfac173f1a075983260aa9d694b430c，执行树
D:/riftcoach-sol-natural-stored-key-execution；Operator为outputs/riftcoach-sol-natural-stored-key-20261021。
新plan SHA641f4cac2a98be481e08752866eddc6814f53c066eeb7323f3d67a27edc785a3。
真实行政预检与原件严格只读回查通过，原stdout根及当前0006 checkpoint、event-id均在同级control保存。
授权SHA2ef562edb1ca15fcad8646063307bcb441b02faf0a877edc76903d209155decd，
原issued/expires/预算保持；显式配置路径绑定。替换脚本为同级control/start-authorized.ps1，
语法通过、未运行；公共CI39610700918尚在运行，未通知用户填Key。
