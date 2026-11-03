# 互补职责固定报告：执行准备与操作合同

本提案只回答一个尚未实测的问题：事实与完成度各自给出正确意见后，原样意见是否能兼容地
进入一次实际编辑，并使实际新稿同时通过两种复查。来源沿已熟悉的 duty-3 完整输入；不带
旧 Provider 意见、主审判断、独立标签或旧评分。不是原 15 例资格批，也不重判旧分歧。

## 具体范围与失败决策

固定顺序为 `facts-initial → completion-initial → compatibility → edit → facts-fresh → completion-fresh`。
compatibility 是完整原意见与来源的独立 Host 任务，不调用 GLM。每份实际输出均须主审实读，
并由既有独立主体完成唯一原生 final；不得用结构校验代替语义核验。

最多 **4 次 GLM-5.3/high + 1 次 GLM-5.3-flash/high**，483840 tokens、2700 活动秒、86400 Host 秒；
审查每次 600 秒、编辑 300 秒、输出每次 32768。合同未缓存上界估价 **5.8609664 元**，不是
实际账单硬封顶。初评双方均 pass 则直接结束，没有编辑消费证明；任何语义拒绝、兼容冲突、
错误改文或 fresh 非 pass 均停止本链；身份/授权/源码/协议/观测/预算/transport 故障也停止。
没有生成、重试、补发、关闭后续跑、另开同报告批次或资格授予。

正向单次只支持这个开发方向；任一实质错误否定本链在此例上的充分性。completion 也须有事实
与用户任务依据，不能借职责分离放过错误解释/修法。产品现有 5 调用预算不扩成 7 调用。
8E、正式同版本 15、自然 Coach/Training 消费及现有后续依赖均未因此完成。

## 实际入口与信任链

`scripts/review_duty_launch.py` 的 `prepare` 零网络、零密钥、零业务 run。三文件执行包固定完整
ReviewInput 和两 initial 请求；重新构建 SourceIndex、报告投影和请求字节必须相同。外层准备
保守冻结全部 app/scripts Python、Skill/运行配置及依赖声明，核心计划的旧准备保留历史。
新准备记录的 execution_ready 只表示入口实现准备；execution_authorized 始终为 false。

`execute` 先核准备/授权 SHA、24 小时以内的未过期授权、同 HEAD 公共 CI、clean exact HEAD，
实际启动绝对 Python/cwd，再读真实原生父子身份与 final 可读性。全部通过后，create-only 写
Operator/execution.json，占位成功才读取密钥；任何已有 run、作者/观测目录或执行占位均拒绝，
包括空目录。没有自动重启或生成授权的命令。

父进程启动 worker 前、子进程读配置前和创建 SDK client 前均重核授权/完整源码/包/checkout。
子进程环境副本清 HTTP/HTTPS/ALL 代理，NO_PROXY=open.bigmodel.cn；不修改用户网络。
GitHub 查询仅使用执行进程的代理。CI 查询故障不是 CI 失败，更不是重试模型的依据。

Host 等待期间反复核原件、观测、已审原生事件和控制文件；只准当前 checkpoint 指定的 run 外
作者文件新增。外部 submit 文件只提供主审自己的 Decision 与独立 event locator，核心从真实
native 导入独立全文并比对作者原文。控制文件有意外写入、篡改或错误 event 均停止后续发送。

关闭时将核心 closure SHA 和 Host 控制文件库存另存在 Operator/execution-exit.json，stdout
给出 guard/exit 两个 SHA，应作为当时的可信摘要留存，不能事后重算当原件证明。外层 replay/seal
须同时核这些摘要、完整源码/包、作者/native/观测、预算与停止顺序。只读审计在原 claim 时间
核授权，可在原授权过期或文档提交后进行；不得因此恢复发送。seal 只有 Operator/seal.json
一个 create-only 目标。缺少可信关闭摘要、不完整库存或控制文件污染都不能封成成功结果。

## 操作步骤

工作目录固定 `D:/riftcoach-agent-rq192-pr`，Python 固定该目录 `.venv/Scripts/python.exe`。
Operator 为 `C:/Users/33502/Documents/Agent/outputs/riftcoach-review-duty-chain-20261014`。
run 为 `data/runs/model_comparison/review-duty-chain-20261014`。
包为 `data/evaluation/fixtures/review_duty_chain_20261014`。
准备为 `data/evaluation/results/review_duty_launch_preparation_20261014.json`。

1. 完成离线验证、冻结准备、提交及公共 CI。收到针对本提案的明确新授权后，才能按该准备摘要、
   exact HEAD/CI 留存一次新的 24 小时授权；不沿用或延展旧五次初评授权。
2. 用 `python -m scripts.review_duty_launch execute`，显式传 `--preparation/--preparation-sha`、
   `--authorization/--authorization-sha`、`--env-file`、`--codex-executable`。
   Codex 固定 `C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`。
   唯一前台/后台进程持续运行，禁止第二份；按 stdout 留存 guard SHA。
3. 每项出现 host_pending 时，`task --operator … --key … --guard-sha …` 取得完整原样 dispatch。
   只交给既有 `/root/host_scope_calibration`（01a12f0c-bb7c-74e3-ad92-775eefbe399a）：
   每业务 stage 唯一 NEW_TASK，同 task 恢复只用 MESSAGE。不另建 Agent，不追加目录或泄露判断。
4. 独立作者在精确 run 外路径自行写 JSON、重读同 checkpoint、check-answer，通过后只给唯一
   多行 native final。主审 01a1248f-e18c-7282-92bf-7ceb2eb5dce4 实读真实事件、核路径/SHA，
   用自己的 notes 和 `submit --operator … --key … --guard-sha … --checkpoint-sha … --notes … --event-id …`。
   不代写、裁剪、重签独立答案。`abort` 使用同样绑定并永久停止后续发送；不重启。
5. 进程关闭后保留 stdout 的 exit SHA。`replay --operator … --guard-sha … --exit-sha … --codex-executable …`
   严格只读；`seal` 再加 `--output <Operator>/seal.json`。核 actual/HTTP/已知/未知/receiptless/未发、
   最早停止点及语义差异，再更新结果、canonical/活动计划/progress/findings并提交推送。

主审读取完整 material、report、source、policy、request、response；初评/fresh 各按实际稿件核全文
命题、范围、来源、解释、修法与正确保留。编辑另核实际新稿及四项 ReportAssessment。
行政唤醒、测试事件和校准不算本批审查；不存在的 native final/观测不能补造。

## 验证记录

相关整组 92 项通过（439.59 秒）；收尾拦截后 24 项受影响检查通过（111.01 秒），共 94 个不同场景。
实际绝对 Python/cwd 启动及既有独立主体原生路由/final 可读性预检已通过，原件在 Operator 的
`preparation-native-paths.json`。当前 input 直接可读性为 false；既有 final 路由可用，不能保证
未来任务可读，正式 execute 仍须即时复核。没有借此发送新的 Host 业务任务。

执行准备 SHA256：`6d583ac31d8c2861c7193200d47141bf817120ec3feb7214ad0b18e258079a24`；
内部 plan SHA256：`1769413b8c4b7d4ba073c88f0f785765ae03aa8a46d8d2be5af4e909f0008f72`。
准备绑定 847 份项目源码/配置与三文件输入包。旧 `44c79817…`、`7703a203…` 准备只留历史，
不能用于本次新入口。具体新授权及同 HEAD 公共 CI 全绿是 execute 前仍须满足的条件。
所有离线模型/native 内容均显式 SCRIPTED；本机 HTTP 只证明传输与停止行为，不证明语义改善。
