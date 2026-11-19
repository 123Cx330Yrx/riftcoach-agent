# 最后一项超时的追查

2026-10-12。用户要求继续查明 `T9-relation-contrast:initial` 超时原因。

**结论：已确认触发的是父进程整次请求的 600 秒截止；造成流未完成的上游根因仍无法追溯定责。**
本次原件没有逐次收字节时间、阻塞时线程栈或服务端请求追踪记录。
本地真实 SDK/HTTP 复现证明，连接静默与持续心跳可以留下同样的事件级记录，不能据此选择其一。
这不是模型语义拒绝，也没有证据证明增加时限、换网络或改教学就能修好。

## 已确认的执行链

- 冻结运行源码 `1039fb50184aebdcbc9401da3b33b594b92919b7` 与本轮读取的传输、路由及 SDK 适配源码无差异。
- 最后保存的进度：30,672 ms、768 个已归一化事件、2,190 个 reasoning 字符计数，正文/工具参数/usage/terminal 均未观测到。没有读取私有 reasoning 正文。
- `result.json` 的 `state=deadline`、`elapsed_ms=600079` 来自 `run_child` 捕获 `subprocess.TimeoutExpired`；随后终止并回收子进程。它不是供应商返回的“600 秒超时”错误。
- `collect` 只在 `next(iterator)` 前后检查全局截止；同步读取不返回时，子进程无法走到下一次检查。SDK 的标量 timeout 是打开请求时的剩余时长，HTTPX/httpcore 将其用于每次 socket read，并不随整个请求的剩余时间递减。后续某次读取的超时可能晚于父进程截止。
- 父进程终止子进程后，不保证子进程执行 `finally` 或写 `failure.json`。没有该文件、没有 `close_ms` 并不证明它正常关闭或从未发生底层问题。子进程 stderr 定向至 DEVNULL，runner stderr 为空也不是底层无错证据。

## 对之前描述的更正

“30.7 秒后没有新事件”应改为“30.7 秒是最后一次保存的事件进度”。
普通事件每 64 个才保存一次，里程碑及允许的 HTTP 阶段事件另行触发保存；进度不是逐事件日志。
子进程被终止可能丢失最后一组未保存事件，最后保存的时间不是精确断流时刻。
`advance_duration_ms` 只累计已经返回的迭代，不能用 20.765 秒推断剩余 569 秒花在什么位置。
`last_http_event=receive_response_body.started` 是整个响应体读取阶段，不是最近一包网络数据。
SSE 注释心跳和尚未完成的 SSE 帧也不会变成已归一化模型事件。

## 路由与同期日志

实际入口沿 `document_relation_diagnostic -> document_full_report_diagnostic -> document_sampling_screening.run`
执行 `route_environment('direct')`：暂时清除进程代理并设置 `NO_PROXY=open.bigmodel.cn`。
因此 GitHub waiter 的 12000 代理不能据此认定用于模型 HTTP 请求；Windows HTTPX 的系统代理回退也受该 NO_PROXY 排除。
这不证明网络路径中不存在操作系统/网络侧干预，也不证明公网链路稳定。

只读检查 UTC 14:45—14:59 的 Windows 日志：WLAN 有 3 组安全功能停止/启动/成功事件，
在 14:45:58、14:47:22、14:48:42；该窗口未返回断开/重连事件，不能把这些安全功能事件当成断网证据。
14:48:42 晚于最后保存的进度，且之前已有相似事件，缺少该请求连接的关联证据。
System 警告/错误 340 条均为 ROG Live Service 的 7031 终止记录，没有证明它影响此请求。
找到同期 VPN 应用日志，12 条中 9 条是受保护载荷，未解码；其余为应用自有 HTTP 200，不能代表模型请求。
没有可用的该请求抓包、代理逐连接记录或服务端请求状态，不能由当前网络探测倒推历史根因。

## 无外网复现

`scripts/diagnose_stream_stall_offline.py` 使用实际关系 worker、当前 OpenAI SDK/HTTPX/httpcore、真实本地 HTTP/1.1 SSE 与现有父进程收尾函数。
SDK 地址固定替换为 loopback、凭据替换为 OFFLINE，并在 socket connect 前拒绝任何非 127.0.0.1 目的地。
输入在本地从开发材料重建，响应全部合成；无模型 API、无业务 run、无资格。
父进程使用同一实现的原始 time600 transport 标识，子进程使用关系标识；测试将截止缩至 15 秒，不冒充生产 600 秒或远端 TLS 复现。

| 合成情况 | 实际本地发送 | 保存进度 | 收尾 |
|---|---|---|---|
| 前缀后完全静默 | 65 个事件 | 64 个事件、reading | 15.032 秒 deadline，无 worker failure |
| 前缀后持续注释心跳 | 65 个事件、80 次心跳 | 64 个事件、reading | 15.015 秒 deadline，无 worker failure |
| 前缀后明确 EOF | 65 个事件 | 65 个事件、failed | 6.797 秒，missing_terminal |

两个超时案例在截止前取得无正文、无局部变量的线程栈，均停在 httpcore `sync.py:read -> socket.recv`；
这是本地案例的观测，不是历史失败进程的栈。SDK 逐读超时实测约 13.14/13.219 秒，而父进程从启动起共 15 秒。
初版 8 秒本地夹具的采样时刻撞上 SDK 懒加载，断言失败；增至 15 秒后 3 项全部通过。该失败留在 operator 外部目录，未混入真实批次。

复现命令（输出目录必须不存在且在 data/runs 外）：

```powershell
& D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe -B -m scripts.diagnose_stream_stall_offline --output <new-offline-output-directory>
```

工作目录为 `D:/riftcoach-agent-rq192-pr`。版本：openai 2.54.0、httpx 0.28.1、httpcore 1.0.9、h11 0.16.0。
机器可读证据见 `data/evaluation/results/document_relation_timeout_diagnosis_20261012.json`。

## 技术决定与边界

本次历史根因标为 **undetermined**，不再通过重复读取相同进度文件或重新付费来“确认”猜测。
不延长 600 秒、不改网络、不采用候选、不补发；原批 73 原件、旧批原件及所有缺口保持，automation PAUSED。
本次新增离线诊断、独立的可选观测组件与记录，没有修改线上/冻结 worker。

用户要求诊断后继续推进，已直接补充 `scripts/stream_observation.py`：HTTPX 响应流外包一层只计数的观察者，
独立采样线程每 0.5 秒保存读取阶段、原始字节/块计数、最近字节时间、有效 SDK timeout 和无局部变量的调用栈；
仅允许格式受限的 x-request-id，不保存正文、reasoning、请求头、URL或异常消息。
目录 create-only 且拒绝 data/runs，后续快照原子替换；观察者不改返回字节、异常对象、关闭操作、重试或截止时间。
采样失败可见，不会掩盖原流结果。强制终止可能丢失最后一个采样周期，必须先核 observed_ms 的新鲜度；它仍不是逐包抓包。

启用 `--observe` 后，真实本地 SDK/HTTP/子进程四路径全部通过：静默记录最后字节距采样 8,313 ms，
持续心跳记录 62 ms；原来的模型事件级进度均为 64。EOF 仍失败，完整正常响应仍成功，证明观测不会将部分结果变为成功。
另 6 项测试覆盖正文/凭据/异常消息不落盘、原异常和关闭透传、目录边界及可见写入失败。
该组件目前只在离线诊断入口显式使用，尚未绑定任何新付费计划或生产默认；有效公网路由及服务端关联还须未来入口一并核验。

若未来再批准真实传输验证，应先把这项观测绑定到该次 worker 和 run 外目录，再记录有效路由；保留既有硬截止与未知用量规则。
这些可以区分本地卡住、无新字节、仍有字节但无模型事件；服务端与中间链路的最终归因仍可能需要供应商或网络证据。
## 接着推进的语义方案裁决

进一步只读对照旧 H5 与 T9 基线的公开 `suggested_correction`：H5 在正确指出均值不接近后，新增“因此……并未把胜局与负局分开”；
T9 的初评输入正文已经包含“不等于数值未区分这四个观测”，并且错误是“均值相同”而非原 H5 的“均值接近”。
这些差异使 T9 成功不能充分代表旧 H5 修法故障已复现或已改善；这只是设计上的差异，未证明它导致了两次不同输出。
因此不选“只补买 T9 候选就证明修好了”，也不把加来源编号或去掉初评的已否定方案恢复为下一步。

已完成两篇新作者开发材料 U1/U2，保留原完整来源、身份和26实际段号，全文只差第14段的一句“均值并不接近/均值接近”。
两篇都去掉报告正文中预先写出的逐对分离结论与“不等于未区分”的提示，但完整来源中的逐局数字和确定性 all_pairs 证据保留。
第6段在两篇新材料中同样明确“这4局中单内”，隔离已知范围措辞争议；这不是修改或翻案旧 R4。
第15段保留正确的补刀区间重叠，避免同时引入第二个事实错误。
现有真实输入构造器核得每篇26段、证据项/玩家事实/知识/用户问题不变；报告变化产生的source_digest和block ID按新全文重建，不能沿用旧绑定。
初次准备误把整个含source_index的data_json要求不变，构造器正确拒绝该断言；改为逐项核真实来源不变、每篇索引重新生成后通过，未写出错配材料。

材料位于 `data/evaluation/fixtures/relation_repair_material_preparation_20261012.json`，可用
`python -m scripts.prepare_relation_repair_material --output <new-file>` 重建；明确 `execution_package=false`、
`execution_authorized=false`、`independent_calibration=false`。这是派审前的作者准备快照，后续校准不改写这份历史声明。
没有新业务run、Provider请求或自动任务；开发材料校准另行记录如下。

## 独立全文开发校准与下一方案

复用原`host_scope_calibration`完成一次新开发材料任务，没有新建Agent。主审先保存全文意见，再读取独立结果：
U1无实质错误，U2仅第14段均值接近错误；双方一致。完整修法保留逐局3/2与0/1、均值2.50/.50及因果证据限制，
不新增“未区分胜负”或因果零效应。正文其他正确事实、范围和K1—K5引用保持。

材料SHA为`77f22cafa8f28ba3149b786f9bec6113a8a2ee857e85c0110cb9b85b0e82bac8`；
task SHA为`dd31cff2b1f04d99a315a773815e54c7919dc31ed12339f69858ffbe73f918de`。
真实native turn `01a130cc-90c2-73b3-b1c1-b39609a4e323`已完成且只有一个final；作者JSON与final除结尾换行外逐字一致。
20条公开命令exit0，全文输入/来源分段输出与材料一致（只规范控制台换行），完整报告、policy、确定性来源和final前重核均有公开证据。
派发正文加密，只核真实NEW_TASK路由和终答归属，不宣称解密或OS沙箱。结果在
`data/evaluation/results/host_relation_repair_calibration_20261012/`，不改旧业务批原件。

这组材料可用于进一步隔离H5同类“接近”修法与正确保留，但仍使用熟悉来源；不是holdout或GLM语义改善证明。
下一项选择在新材料上准备完整初评对照，先离线接入run外观测、核有效路由与实际输入，然后才形成具体有界执行包。
两臂皆过或基线未复现时，不称机制改善；候选仍错则否定，硬传输故障停止该批。
任何新成本另行授权；旧批不重开，600秒不延长，不把材料校准当产品质量通过。
