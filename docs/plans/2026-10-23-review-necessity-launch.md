# 三项必要修订边界诊断：受控入口

本工作包只检验已有事实审查政策候选在三份全文开发对照上的误报/漏报。
用户已要求继续准备，尚未授权此新范围付费；旧授权及旧六项均不挪用、不重开。
材料/标签及失败决策沿用 `data/evaluation/fixtures/review_necessity_20261023/README.md`。

## 实现及证据边界

`scripts/review_necessity_launch.py`调用现有 `reviewer_responses_process.run_once`，
沿用同一SDK、300秒监督、Key stdin、原HTTP观测和费用回执；不另建模型传输层。
每次完整结果使用既有 `ExactNativeGate` / `HostReviewWorkspace`：完整报告与可见请求/来源/
全部意见 → 原生独立作者原件/check-answer/final → 主审自己的判断/event-id → submit。
评测标签和旧意见不进入模型请求；主审材料标签不是独立接受，也不是模型改善证明。

每次命令明确携带原stdout的 plan/checkpoint SHA，append-only checkpoint记录库存及前序根。
claim在worker启动前落盘并输出；中断后不能换目录、重置账目或不查回执就重发。
新命令仅增加受控三项启动/恢复层，未修改产品Runtime、旧接收器、模型或发布标准。
调用前核实际cwd/Python、clean exact HEAD、tracked源码/材料重建、精确公共CI、授权UTC期限、
当前原生身份及所有已接受作者/原生记录。源码库存仅读Git tracked，不打开无关untracked probe。
旧诊断seal及完整库存贯穿准备/发送前核查，旧7HTTP/111392known/145824unknown/retry1单独保留。

## 范围、费用与取消

- 固定a、b、c顺序，每项一次facts-initial；无生成、completion、修订应用、fresh或15项批。
- 最多增加一次**显式**超时补测，三逻辑项总计最多4尝试，321536 tokens预留；无自动重试。
- 每尝试64000输入预留+16384输出、300秒。等待CI/Key/Host时没有活动worker计时。
- GPT-pro / gpt-6.1-sol / 请求high / Responses nonstream / 进程代理127.0.0.1:12000。
- 按用户已确认0.4/2元每百万输入/输出估算，三次0.175104元，含一次补测最多0.233472元。
  是预留估算，不是上游账单硬上限或新报价；known/unknown/not_sent分记，不重置旧费用。
- 新授权显式绑定plan SHA、profile、固定limits、人类授权证据、价格和至多24小时UTC区间。
  准备代码不自动批准或生成已批准grant。只有实际新授权后才能制作授权文件/固定SHA。
- Key仅终端隐藏输入，不落盘、不放argv/env，不在日志记录错误正文或私有reasoning。
  输入前取消没有claim；输入后重新核UTC/来源/原生，过期或漂移不发送。

## 结果决策与恢复

| 实际结果 | 入口行为 |
|---|---|
| 完整接收、尚未审查 | awaiting_review；不发送下一项 |
| 完整意见及修法语义正确，双审接受 | 继续下一份；三份完成也仍不授产品资格 |
| 任一误报/漏报/解释或修法实错 | 停本候选，不加一句提示后继续购买；有效观察与旧接受保持 |
| high/max回显冲突但完整有效公开意见 | 正式接收仍失败；仅作原生语义诊断，审完停止，不为档位补测 |
| 明确524/read timeout/监督deadline且已回收、已观测一次HTTP，无完整可用结果 | retry_available，保留其他已审项；须显式retry且剩余补测额度足够 |
| worker退出后已有完整receipt，主进程在导入前中断 | reconcile只读取现有回执并建立审查任务，绝不再发送 |
| claim存在而receipt缺失，或身份/协议/观测/库存不一致 | 禁止发送；保留unknown和原件，人工核查；不冒充not_sent |
| Key提示处取消 | 保留此前checkpoint，可恢复同一未claim项 |

`seal`为Operator内唯一create-only `seal.json`；它可封存部分结果，不把未做项当通过。
prepare后先停在needs_native_preflight；native-task只建立行政审查夹具，真实原生提交接受后才进入ready。
这份proof会在每次发送前重新读取作者/原生，不能靠计划里的自报布尔值直接绕过。
尚有不确定活动claim时拒绝封存，需先核进程及真实回执。`replay`严格只读，要求原seal SHA，
重核原生/作者及全部库存，不事后重算trust root充当启动时根。临时锁在Operator外，用OS锁，
进程退出释放，不用PID猜重启状态。锁文件保留给后续恢复，不进入封存库存。

## 命令与实际准备

干净执行树准备后，保留prepare完整stdout；所有后续命令使用其中的原SHA。
`check`不读Key、不发请求；业务原生预检仍须真实作者file→check-answer→唯一final→导入，
历史身份/final可读取不能替代这一过程，也不保证旧Agent仍能被当前协作工具调度。

模块CLI有prepare/check/native-task/send/retry/reconcile/submit/seal/replay。send一次只发送当前项，
返回完整dispatch文件路径；操作者原样派发，不从摘要重写。submit须主审自己写decision，
独立JSON只能来自作者及真实event；禁止操作者代写独立判断。
submit完成后保存其原stdout checkpoint再用同一入口继续，不根据目录mtime挑根。
每次调用前的CI绑定沿用已有合同；本地准备和复核历史材料不等CI，也不因一行文档重跑整站。

## 本地验收

新测试使用真实worker子进程/SDK、mock HTTP和明确标识的FakeGate，检查三项顺序、审后继续、
单项超时保留前项、显式有限补测、high/max诊断后停、语义拒绝、取消/UTC/路径/来源漂移拒发、
OS互斥、完整回执中断恢复、缺观测停发和只读seal。它们只证明工程控制流，不证明真实语义或原生交接。
不因fixture里模拟接受就给三份预期标签盖独立审查章。实际预检与准确执行树/根另存准备结果。
