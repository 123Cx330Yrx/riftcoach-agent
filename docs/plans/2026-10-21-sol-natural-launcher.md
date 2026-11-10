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

2026-10-21封存后接收修正（仅后续版本）：请求仍明确`reasoning.effort=high`。
响应reasoning字段省略/null、对象内effort省略/null统一视为未回显；不能据此认证实际档位或第三方上游。
显式high仅是渠道回显；显式其他字符串、错误类型仍返回reasoning_identity。
无正文观测新增固定reasoning_echo枚举：absent/null/effort_missing/effort_null/high/conflict/malformed，
未收到响应时为null。不保存任意effort、正文或私有推理；SDK序列化字段值警告关闭。
原六项与本轮冻结接收代码相同，旧响应无区分性观测，不能据修法推断旧实际值或恢复旧失败为成功。
仅更新独立候选清单，不改冻结执行树、封存原件及旧stream路径。后续恢复应复用现有报告与工具结果，
具体执行与费用须另有可审查方案；本修正不自动重买或重生成。

明确且已回收的传输超时依现有合同共用一次重试；身份、结构、语义及来源变化不重试。
重复运行未审阶段在读取Key前暂停；已关闭会话不重开。未完成intent保留证据待核。
如果派生输出已产生但进程未保存其摘要，也保留原件并阻止盲目继续，不删除后重试。

调用预算提案仍为6逻辑调用+1共享超时尝试、498688tokens、1200活动秒，
按既有价估算0.6170624元而非账单硬限。用户已对此任务明确授权；缺有效绑定授权时不执行`run`。
真正准备好还要求当前提交公共CI、干净冻结执行树、真实作者预检完成及发送前价格确认。

## 入口使用

### 从封存的首次审查接收失败继续

`prepare --parent-operator <原Operator> --parent-seal-sha <原stdout保留的seal SHA>`
生成独立的新Operator；原run_id和审查主体保持，原Operator只读。仅支持已完整封存、
两次生成和只读检索完成、首次facts-initial在reasoning_identity拒绝且用量已知的情形。
完整原库存、原guard/checkpoint、请求/结果绑定、失败用量及源码差异均核对；
原生成/来源/提示/依赖变化则拒绝。prepare实际回放到同一报告、同一审查请求的发送前边界。

新会话导入已完成的原操作；前缀最后一项是明确标记的派生记录，其报告/响应/请求保持原样，
累计账目包含旧失败。只重置新会话的停止状态和未完成审查的逻辑位置，
旧3次尝试、52067已知tokens、失败明细和190.094活动秒全部继承，不伪装为旧run恢复成功。
后续生成被禁止，只提示天机阁Key，不读取智谱配置。父证据验证贯穿发送、审查导入、应用与封存。

当前剩4次Sol尝试、最多新增321536tokens；总计仍最多7次、498688tokens、1200活动秒。
按输入0.4/输出2元每百万tokens估算新增最多0.233472元，非账单硬限。
明确超时仍可共享重试一次，但消耗上述4个位置；若因此不足以完成双fresh，按预算停止并保留结果。
补测不重置历史成本，不扩大上限，不把跨接收版本的拼接证据称同版本资格。
授权需明确绑定父seal、新plan/HEAD、新增上限及零生成，旧grant不能自动沿用；
新版本精确HEAD公共CI、干净执行树和真实原生预检仍是实际发送前条件。

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

继续交接：新control/start-authorized.ps1先执行同目录wait_public_ci.py（前台只读，不是automation），
固定CI39610700918/HEAD084c415c/原授权SHA。仅同HEAD全部8项success才进入原实际launcher，
后者再次核CI/授权/native/来源后加载显式智谱配置并只提示天机阁Key。
最多等1小时、每30秒查一次，授权过期/CI失败/连续三次查询失败均在执行前退出，查询故障不冒称CI失败。
等待可Ctrl+C，尚未产生execution时无模型发送；原首次stdout仍create-only。
六项判定分支和实际授权校验通过，入口语法通过；此入口未运行。

## 恢复入口实际准备（2026-10-21）

2026-10-21恢复准备实核：34项相关回归已通过，执行树D:/riftcoach-sol-natural-continuation-execution冻结51f31f60。
实际prepare完成；独立作者原件/check-answer/真实native final/导入及严格只读回查通过，原件前后不变。
新plan与预检原stdout根详见sol_natural_continuation_preparation_20261021.json。首次启动脚本已备好并通过语法检查。
CI39623758447在15:22 UTC仍in_progress：Web/Postgres/打包通过，四pytest分片运行。
下一动作仅核冻结HEAD公共CI；全绿后给绑定新plan/父seal的具体补充授权。无execution、无新请求、无Key读取。

新Operator为outputs/riftcoach-sol-natural-continuation-20261021，同级control/start-first.ps1
要求明确传入新授权文件及原SHA；不读取智谱配置，只隐藏提示天机阁Key。旧授权不自动重绑。
预检guard8080b1db、最新checkpoint8a58a383及完整根在result和control原stdout保留。
新增最多4次Sol/321536tokens/估价0.233472元，旧3次成本继承；生成禁止，超时重试占剩余位置。

## 2026-10-22 发送前技术准备完成

2026-10-22北京时间09:47实核：冻结51f31f60的公共CI39623758447全部8项success。
再次严格只读核源码、父证据及真实native预检，原件未变、execution不存在。技术准备完成，
下一动作是确认新plan/父seal绑定的恢复付费授权，再提供隐藏输入天机阁Key的命令；
最多新增4次Sol/321536tokens/估价0.233472元，零生成，旧成本与累计预算继承。新请求0、Key读取0。

## 2026-10-22 恢复授权已绑定

2026-10-22用户明确回复“授权”。新grant绑定恢复plan94c8fe57/冻结51f31f60/父seal，
最多新增4次Sol、321536tokens、零生成，继承旧成本和累计预算；SHA37676388，
有效至北京时间2026-10-23 09:48:43。CI/实际路径/源码/真实native再次核验通过。
同级control/start-authorized.ps1已备好且语法通过；下一动作由用户隐藏输入天机阁Key启动，
随后逐项审查真实输出。此刻execution不存在、新请求0、Key读取0。
