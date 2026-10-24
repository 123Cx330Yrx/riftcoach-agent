# J1/J2 全文联合检查：执行准备

> 本文保留授权前准备快照。随后用户已明确确认，四次初评已执行并关闭；实际结果、授权与成本以[关闭结果](2026-10-13-relation-joint-result.md)为准。下文“未授权/未执行”均指准备时点。

新范围的目标是同时观察真实错误检出、修法正确性和正确全文保留。它继续
[联合提案](2026-10-13-relation-joint-review-proposal.md)，不更换模型审查 schema，
不添加提示词，不删除初评、来源或既有编辑/终评链。这里只准备四次独立初评，
不把准备、校准或离线测试当成 Provider 语义通过。

## 两分支接续与材料校准

`说明知识截止时间 (13)` 已将旧批收尾、失败裁决、新材料提案提交到同一后端分支，
依次为 `266e5df9`、`05470874`、`8f271698`。`说明知识截止时间 (12)` 新建后的
回合因模型容量不足失败；其继承的早期主会话记录不是额外执行。两个分支均已空闲，
原主会话 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4` 是唯一执行入口。
恢复时已核 `8f271698` 的公共 CI `38355387193` 全绿；新实现仍须自己的同 HEAD CI。

用户换位置导致的正常暂停已解除。原独立主体
`01a12f0c-bb7c-74e3-ad92-775eefbe399a` 的同一 J1/J2 材料任务已完成。
工具只能用 `followup_task` 唤醒空闲主体；经用户同意的行政唤醒会产生原生
NEW_TASK 信封，随后用 MESSAGE 接续原固定材料。行政可响应确认不计审查终答，
不声称原生记录只有一个回合，也不改变业务 stage 的一次派发协议。

校准材料与 task 原件保持 SHA：

- 材料：`7997f6d571f72b2e47bb49803e57f11cca02b00205d299ca568a57f2bb17c927`
- task：`738ecd4647a8b83711a257d923eeebb669091d1e06d1b55ee5499e615eced077`
- 校准审计：`data/evaluation/results/host_relation_joint_calibration_20261013/close-audit.json`

原生完成回合 `01a13462-fba7-7821-860c-03b51332bbd2` 的唯一 JSON final 与作者原件
一致。原任务及恢复后的 10 条公开命令均 exit 0；全文、全部输入/来源、policy 可见，
恢复与 final 前固定文件重读/SHA、作者 create-only 和 json.load 实核。
派发正文加密，仅证明真实路由与 final，不声称已解密正文或建立 OS 沙箱。

双方结论一致：J1 无需事实修正；J2 第14段四局中单早死均值2.50/0.50不接近，
第15段补刀均值略低不等于每个胜场都低于每个负场。两条独立修法逐项核对：
8.95/8.66均低于9.64又高于8.38，保留全部五局比较、正确相邻断言与因果限制。
第7段仅有可选 advisory。熟悉来源不是 holdout，校准不能授予产品资格。

## 独立执行入口与数据流

统一入口：`python -B -m scripts.document_relation_joint_diagnostic`。

1. `prepare` 从固定全文校准重建两篇各26段报告、全部来源与四请求，仅 system
   教学及其 variant 标记区分双臂；create-only 保存包。`verify` 逐字重建并核库存。
2. `run` 仅接受本范围 `document-relation-joint-authorization-v1`，先核新授权、
   clean exact HEAD、同 HEAD 公共 CI、完整包/源码 SHA、当前真实 native 主体，
   以及绝对 cwd/Python 实际启动。已有 run 或 transport 不重开。
3. 私有 `document_relation_joint_request` worker 保留600秒总截止、SDK重试0，
   将无正文的字节观测绑定实际请求 SHA、worker 路径与 direct 路由。
4. 每项 `material` 供主审实读；原独立主体只收完整原样 dispatch 和精确检查点。
   自己写 run 外答案、check-answer 后唯一 native final；主审实读事件后才 `submit`。
   提交及下一发送核 Host 库存、作者/终答和观测绑定。语义拒绝/分歧继续下一独立项；
   身份、来源、native、checkpoint、协议、transport、预算或主体硬故障停全批，无重试。
5. 关闭后只读严格 `replay`、create-only 白名单 `seal`；实际已审项逐个核 native，
   保留所有原件和未知用量。完整响应缺有效观测是硬故障；硬失败尾项可如实缺观测，
   不能算成功。无自动语义判定或生产默认变更。

隔离路径：

- 包：`data/evaluation/fixtures/document_relation_joint_20261013`
- run：`data/runs/model_comparison/document-relation-joint-20261013`
- operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-joint-20261013`
- observations、author-answers 均在 operator 内、run 外。
- cwd：`D:/riftcoach-agent-rq192-pr`
- Python：`D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`
- Codex：`C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`

旧入口及冻结源码不改。新私有 worker 明确保留与旧观测实现相同的处理方式，
使用独立版本、marker、transport 和进程入口，不在运行时重绑旧模块或借旧 run。

## 具体成本范围与执行边界

顺序：J1-baseline、J1-relation-contrast、J2-baseline、J2-relation-contrast，均 initial。
最多4次 GLM-5.3/high，Flash 0；最多387072 tokens、2400活动秒、86400 Host秒，
每请求600秒和32768输出。按全部未缓存上界估价 **5.718016元**，不是实际账单硬封顶。
不含生成、真实编辑、fresh、重评、重试或补发；不得沿用旧授权或剩余次数。
同一范围授权最长24小时，issued_at/截止不延展；授权还需绑定完成准备后的精确 HEAD、CI及包摘要。

候选任一实质错误则不采用；两臂都通过或基线不复现不能宣称改善。
同版本完整15、自然消费、8E以及全部产品下游依赖继续保留。
旧 U1/U2、R4/T9及其前批均关闭，缺失项不补签；旧自动任务保持 PAUSED。

新范围尚无成本授权、无业务 run、无 Provider 请求。完成离线准备并冻结提交后，
将该具体四次范围交用户决定；用户此前的“继续”覆盖普通接续与准备，不转移旧批成本授权。

## 准备验证结果

新旧入口及材料联合 **69项测试通过**（218.71秒）；真实本地SDK/worker覆盖完整响应、
静默、心跳和EOF，未接外部模型。验证旧两批授权拒绝、请求漂移拒绝、旧模块/路径隔离、
观测缺失/篡改停批、下一发送门、只读replay和create-only seal；模拟Host不是业务审查证据。
CLI prepare/verify生成并核对9文件包，plan SHA：
`e890e28f41a35586fb589fac62bf2fb05b1cf01833613a5d858012d07b2a7d6c`。

当前绝对Python/cwd真实启动及原native主体谱系/路由预检通过；派发正文仍加密，
按既有native-final-attestation协议处理，执行前仍须重新预检。
旧六批66/73/47/26/14/146原件库存及SHA逐项未变，原两批69/73个冻结source SHA未变。
机器记录：`data/evaluation/results/document_relation_joint_preparation_20261013.json`。
