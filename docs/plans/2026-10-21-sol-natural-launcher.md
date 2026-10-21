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
   获取会话进程锁并检查未完成intent/关闭/未审任务后，才在交互终端分别隐藏输入两家Key。
   不读环境或文件寻找Key，不落盘Key，拒绝getpass回退到明文输入。
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
按既有价估算0.6170624元而非账单硬限。没有新的费用授权，不执行`run`，不让用户先填Key。
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
