# 初审逐字补丁：固定报告开发验证准备

2026-10-14。目标是验证初审直接给出的精确补丁，能否在完整验收后原样应用，并使实际新稿
通过事实与完成度两种 fresh。机制与反证见[候选设计](2026-10-14-reviewer-authored-patches-design.md)。
本文件是具体待授权提案；当前没有新授权、业务 run、执行 claim、waiter 或 Host 派单。

## 范围、费用与去留

只用已熟悉的 duty-3 固定报告完整输入，不新增生成，不导入旧意见、评分或 Host 标签。
顺序为 facts-initial → completion-initial → compatibility → edit（完整程序预览验收）→
唯一 application → facts-fresh → completion-fresh。compatibility、edit 和 application 不调用模型。
初审同时保留完整 issues/解释/修法及 issue_ids、before/after/reason，不转换旧模型响应。

| 限制 | 本批范围 |
|---|---|
| 模型 | 最多 4 次 GLM-5.3/high；Flash 0 次 |
| token | 总计 387072；每次输入上限 64000、输出 32768 |
| 时间 | 模型活动总计 2400 秒、每次 600 秒；Host 独立 86400 秒 |
| 费用 | 合同未缓存包络估价 5.718016 元；不是账单硬封顶 |
| 重试 | 0；不补发、不重开、不沿用旧授权 |

两 initial 均 pass 则提前结束，只证明本例无需修改，不能记编辑成功。否则两份完整意见及
全部补丁均须双审接受，非重叠不能代替兼容性判断。实际预览整稿经四项 ReportAssessment
验收后才唯一应用；两 fresh 实读同一实际新稿，不携带旧意见或标签。
任一意见拒绝、语义冲突、坏补丁、整稿拒绝、fresh 非 pass 或身份/来源/协议/native/观测/
transport/预算硬故障均停止全批，无重试。严格 block_N、唯一锚点、无重叠、问题库存保持；
相同补丁重叠也拒绝，不自动选择一份。完整响应缺有效观测硬停，未知用量不记成功或零消耗。

新初审若仍有实质错误，否定此例上的充分性，不按错误字段打补丁后继续购买。
正向单例最多支持开发方向，不证明稳定改善、holdout、原 15 资格或产品采用。自然任务仍
为两次生成加四次审查，共 6 次，超过产品 5 调用上限；不删职责、跳 fresh 或静默扩容。

## 已冻结准备

- 入口：`python -m scripts.review_duty_patch_launch`。
- 绝对 cwd：`D:/riftcoach-agent-rq192-pr`。
- Python：`D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`。
- 包：`data/evaluation/fixtures/review_duty_direct_patch_20261014`，仅 inputs.json、facts-initial.json、completion-initial.json。
- 准备：`data/evaluation/results/review_duty_patch_launch_preparation_20261014.json`。
- 准备 SHA256：`a27cdfb32f305fba8221359cab436a8857d9866f648c02158420cd1877e3b9fb`。
- plan SHA256：`fdfc041c2889b199681f533e3dbd033ad35aa48c47e9a1d062615210f0afc5e7`。
- Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-review-duty-direct-patch-20261014`。
- 唯一未来 run：`data/runs/model_comparison/review-duty-direct-patch-20261014`。
- 新授权身份：`review-duty-direct-patch-launch-v1-authorization`，尚未签发。

准备固定 854 份源码配置和三文件包 SHA。完整输入/原稿/plan 与先前只读 readiness 相同，
两 initial 字节与新 builder 完全相同。旧 847 源码配置、3 件包、64 本批原件逐件核 SHA 保持。
prepare 的 execution_ready=true 仅指入口准备就绪；execution_authorized=false。
准备不包含执行 HEAD；新授权才绑定最终 clean HEAD、同 HEAD 公共 CI 和上述准备 SHA。
文档/准备资料提交不改变源码指纹，但任何源码或包变化都要求重新审查冻结关系，不能覆盖旧准备。

Operator 下 create-only 保存 preparation-native-paths.json 和 preparation-complete.json。
实际绝对 Python/cwd 子进程启动通过；既有主体血缘、route/final 可用，current_input_readable=false、
future_input_guaranteed=false。这只是授权前行政预检，不是业务审查；正式启动必须即时重核。
实现基线 f046e04f / CI38562682178 查询时仍运行中，不记全绿；准备资料提交的公共 CI 另核。
此前 87 个不同相关检查通过；本轮只创建资料，核包/输入/源码/旧库存、真实路径与 native、治理及差异，
没有重跑无关通过项，没有真实 GLM 请求或业务 Host 任务。automation 保持 PAUSED。

## 获得新授权后的唯一执行路径

1. 用户明确批准上述新批范围后，按最终 HEAD/CI/准备 SHA 记录一次不超过 24 小时的新授权。
   旧批授权不适用，不延展原期限。同 HEAD 公共 CI 全绿、clean exact HEAD、854 源码和三文件包
   不变、授权有效、即时 native 与实际绝对 cwd/Python 启动预检全部通过后才首次 execute。
   已有任何 run/execution/claim 时不另起；若唯一等待进程存在也不重复启动。
2. 用新入口 execute，显式提供 preparation/preparation-sha、authorization/authorization-sha、
   env-file 和 codex-executable。Codex 固定 `C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`。
   独占 claim 后才读取配置。GitHub 仅进程代理 http://127.0.0.1:12000；模型子进程清代理，
   NO_PROXY=open.bigmodel.cn，不改用户网络。CI 查询故障不当 CI 失败。
3. 保存首次 stdout guard SHA。每个 host_pending 使用 task 命令和原 guard SHA 读取完整 dispatch。
   原样交给既有 `/root/host_scope_calibration`（01a12f0c-bb7c-74e3-ad92-775eefbe399a），不新建 Agent。
   每 stage 唯一 NEW_TASK，同 task 恢复仅 MESSAGE；精确 checkpoint 路径/SHA、绝对 cwd/Python、
   run 外 author-answer 路径必须齐全，不追加 backend，不泄主审/旧标签/批代码。
4. 主审 01a1248f-e18c-7282-92bf-7ceb2eb5dce4 实读完整 material/report/source/policy/request/response；
   facts 排除完成度但不免解释和修法依据，completion 不造要求；泛指不补全称，措辞不升级事实门。
   独立恢复和 final 前重读同 checkpoint，自写 JSON、check-answer 通过后唯一完整多行 native final。
   主审实读真实事件后用自己的 notes、event-id、guard/checkpoint SHA submit；不代写、裁剪或伪造。
   实际新稿审全部修改和正确保留，fresh 仍审全文。需 abort 时同绑定终止，不恢复发送。
5. 原件/作者/控制库存/已审 native/run 外观测贯穿 submit、下一发送、唯一应用和关闭回放。
   日志不记录正文、reasoning 或秘密。关闭时保存 stdout 最初 exit SHA 和 guard SHA，不从现盘
   重算冒充原信任根。phase-result.json 进入 closure，按真实阶段重建最早停止点。
6. 新入口 replay 严格只读，seal 仅 Operator/seal.json create-only；核全部 native/作者/原件/
   观测/实际调用/HTTP/known/unknown/receiptless/未发、停止阶段与语义差异。缺证据明确失败或未知。
   结果、canonical、活动计划、progress/findings 同步后相称检查、提交推送，automation 暂停。

全部旧封存与历史分歧保留，不补签、重判或拼资格。正式同版本 15、自然 Coach/Training、
四块联动、journal、前端头像审美、Memory、身份运维、两树整合、独立评估与学习依赖均保持。
