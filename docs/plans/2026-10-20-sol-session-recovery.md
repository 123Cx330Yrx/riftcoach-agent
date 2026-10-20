# 自然任务候选的持久恢复与审查接线

## 本轮结果与边界

起点 `7444cd887d91e82fc1f91c3bee0694695a0ca646` 的公共 CI 39401813306 已结束为 failure，
不是等待中。四分片首错均关联共享预算对旧候选合同的兼容：失败路径直接读取不存在的
`version`，遮蔽原异常并阻止已知用量结算。改为精确合同对象判断，保留旧合同行为。
Windows 旧 original15 结果仅有 CRLF 转换，恢复 Git LF 原字节并锁定属性；原 SHA 不改。

本轮工作包是在同一个自然任务里保存生成、检索、审查和修订进度。用户重启或审查等待后，
应继续未完成环节，而不是再生成旧报告、重复买审查或重置未知用量。
这仍是开发候选的工程实现；没有新付费请求、真实业务审查结论或模型采用决定。
最终测试与新提交 CI 状态以 `sol_session_recovery_20261020.json` 和实际公共运行记录为准。

## 设计与实际路径

复用应用服务、AgentLoop、Harness、共享预算、Flash/Sol 原传输和逐字补丁程序。
`build_natural_duty_candidate(execution_session=...)` 仅为精确 Sol 候选开启持久模式。
普通产品和旧自然候选继续使用原路径。

1. `CandidateSession` 在 Operator 独立目录保存 create-only guard、操作意图、结果和检查点链。
   恢复必须提供原 guard SHA 和最新已保留 checkpoint SHA，不能重新算根来冒充已有信任。
   内核文件锁阻止第二执行者；进程退出释放锁，但未完成发送仍需核实，锁释放不证明子进程结束。
2. `SessionBudget` 位于 `ObservedLLMProvider` 上方。新请求才进入原共享预算及真实观察器；
   历史结果本地读取，不产生第二个 Provider Completed 事件。Router 保留全任务 ordinal，
   每段派生 Runtime Trace 只统计该段新 IO；累计调用/known/unknown/retry 以持久 session 为准。
3. `SessionTools` 保存完整 `knowledge.search` 结果，包含原 retrieved_at、引用、顺序和工具返回。
   恢复不重新检索。只缓存模型回答而重新检索会改变请求和来源时间，因此不能采用。
4. `SessionWorkflow` 重演业务状态到最新边界，但原 journal/application 只读核对。
   补丁应用记录只写一次，历史业务输出与每段派生 Harness/Trace 存储分开。
5. `SessionReviewGate` 复用 `ExactNativeGate`：两初审、兼容性、实际预览四项 ReportAssessment、
   两 fresh 分别停顿。作者原件必须在证据目录外；原生 final 逐字节导入，不代写或规范化答案。
   提交、下一发送、应用前和回放重核既有 native/作者/材料。拒绝后持久关闭，不继续购买。

业务材料包含完整原稿/新稿、source pack、data、原请求政策、完整意见和全部实际补丁。
Host 的兼容性与编辑检查不增加第三方模型调用。初审双 pass 仍直接结束，不能声称验证编辑/fresh。

## 中断恢复与失败决策

| 现有证据 | 行为 |
|---|---|
| 完整已提交的操作 | 精确请求核对后读取原结果，恢复预算和已使用重试；不发送 IO |
| 主进程消失，但完整原传输响应和关闭观测齐全 | 显式 `reconcile` 只读验证原传输，补记派生 session 结果；原传输不改，不发请求 |
| 只有发送意图、没有可信完整回执 | 保留 pending 和所有原件；不推断未发送，不自动重试，不释放未知预留 |
| 明确超时且同一受控进程已回收 | 沿用已实现的全任务共享一次重试，预算不足或第二次超时停止 |
| 已使用重试后重启 | 恢复 retry-used，不能再获得一次重试 |
| 已封 terminal/seal、身份/请求/SHA 改变、审查拒绝 | 不重新打开、不覆盖；旧已完成结果仍保留 |

Sol 复用同一完整回执验证器读取；Flash 核原 request/response/reservation/terminal/progress。
允许新增文件仅限当前完整调用的已知回执路径，先前库存不能变。
原件不完整、文件半写、缺退出/关闭证明等情况不会冒称恢复成功。
保留失败回执与原未知费用；`reconcile` 不是供应商账单核销或上游身份认证。

每段活动时间累积，进程关闭期间等待不计入活动秒。重演和核验耗时保守计入新段活动时间；
失去主进程后的完整调用使用原监督回执耗时恢复，不使用新进程的 monotonic 值代替旧时钟。

## 本地操作入口

零密钥、零发送入口：

```powershell
& 'D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe' -m scripts.inspect_sol_session status --session '<绝对session目录>' --guard-sha '<最初保留的guard SHA>' --checkpoint-sha '<最新保留的checkpoint SHA>'
```

仅当完整原响应已落盘但操作结果未提交，使用相同参数将 `status` 换为 `reconcile`。
它只验证原件并追加恢复记录。参数不是新授权，不能借此重开旧批。
`checkpoint_sink` 输出每次新根；调用者必须原样保留。每段应用输出使用新的派生目录，
transport、journal 和 session 是三个互不包含的目录。未知原件不得删除后重试。

## 验证范围与交接

工程回归覆盖实际应用暂停/续跑、完整工具结果、全任务预算、共享重试、唯一应用、
原回执恢复、真实进程退出、篡改、并发所有权、native 原件导入、拒绝停止及本地回放。
所有模型和原生审查事件均为明确的测试替身；没有以替身意见授业务资格。

下一交付边界是付费 launcher 的最终集成：绑定干净冻结目录、精确 HEAD 公共全绿 CI、
完整 source/config 准备包、真实原生审查上下文及实际 cwd/Python 启动预检，之后才提交具体费用授权。
当前这些准备未全部完成，`paid_launcher_ready=false`。本轮不让用户填 Key 试启动。
现有的 status/reconcile 命令不能发起模型请求。

原六次批、第六项独立补测及其错误和资格边界保持。6逻辑调用+1共享超时尝试、498688tokens、
1200活动秒仍为尚未授权的新提案；产品GLM采用与五调用合同、8E、同版本15、Coach/Training、
四块联动、前端头像审美、Memory、身份运维、两树整合、独立评估和学习要求不变。

解释本实现时应强调：这是带原始回执的断点续跑，而不是重试所有异常；本地重演不等于真实模型
再次成功，工程测试不等于业务质量。可以说明具体停顿点和防重复机制，不能说已经完成产品化。

## 2026-10-21 历史回放夹具修复

469da8ec / 公共CI39451570923已完成failure，四分片均在remaining4夹具初始化停止：
历史来源清单要求旧runtime.py，测试归档未保存该文件，因而误用当前已修改源码。
从归档原指定提交51923f4b95e0e17f6bec9aea8d622fd65e2fbce4提取原文件，
LF SHA 30d18b7499da443dca0b10e8515d9510b778bfb8eb1a8a22076eaa65ba04ffbe与原清单完全一致。
仅追加测试快照；旧九份源码、预期SHA、封存回执与真实prior拒绝门均保持。
两清单47/46文件逐项匹配，remaining4/remaining8完整17项回归通过（195.09秒），
包含当前源码不可冒充历史源码的反例；governance及diff-check通过。模型0、密钥0。
下一步推送修复并核该精确HEAD公共CI，未证明全套通过，付费launcher仍未ready。
