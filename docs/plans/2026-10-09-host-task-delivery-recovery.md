# 独立审查任务恢复：定位与前瞻修法

已确认首案新任务到达独立作者，实际偏离发生在上下文压缩后的恢复阶段。
新增一份显式、不可覆盖的任务checkpoint，恢复后及final前重读；同一作者的两次真实
路由切换探针通过。没有重评已关闭报告，也没有新增RiftCoach Provider调用。
这是任务恢复补救及路由证据，不证明自动压缩故障绝不会再现或业务评审质量通过。

## 新证据怎样收窄原因

通过安装Codex只读API读取同一独立turn的公开commandExecution，并只取背后记录的
命令完成时间和compacted类型/时间。没有读取私有推理、压缩summary或replacement_history。
在此前错误final的同一turn `01a11eaf-fb13-7910-82e2-29ee7ab7f47b`，顺序为：

| UTC时间 / 北京时间 | 公开行为 |
|---|---|
| 03:23起 / 11:23起 | 读取scope-4-revision.task.json，查看当前run，读取当前来源/原稿/成稿/编辑与policy |
| 03:24:06.619 / 11:24:06.619 | 当前run完整材料读取命令完成 |
| 03:24:22.889 / 11:24:22.889 | 原生compacted记录 |
| 03:24:29.885 / 11:24:29.885 | 恢复后重新查看工作目录 |
| 03:24:45.230 / 11:24:45.230 | 转而读取旧review-bound-original15/claim-scope:4任务 |
| 随后 | 读取旧材料及旧primary notes，最终返回旧绑定 |

这排除了“新任务完全没到作者”的解释，也定位了可观察的任务恢复偏离。
仍不能据此断言内部压缩算法如何生成了旧summary，或encrypted transport本身导致故障。
旧primary意见的读取发生在已经偏离后的旧任务路径，不视作当前任务的有效独立审查；
后续任务明确禁止读取任何primary/其他Host意见。
历史已关闭批及原错误意见不修改，不借此次证据重新评级旧业务结果。

## 选择的最小改动

复用原全文task builder及`native-final-attestation-v1`，不改旧冻结helper、Provider政策、
模型、解析、预算或资格门。新增`scripts/host_review_task_checkpoint.py`：

1. `publish`只接收由既有真实material/helper产生的精确task文件，将绝对路径、任务文件
   SHA、六字段binding、reviewer及用途绑定到create-only checkpoint。
2. `dispatch`生成一段短的交付指令和精确读取命令，避免人工转录摘要。任务身份不从
   文件搜索、旧summary或相似案例名称推断。
3. 独立作者开始、恢复后及final前用`read`读取同一显式checkpoint和expected SHA；
   task或checkpoint变化/丢失时失败，不回退旧任务。
4. 作者自己的`check-answer`检查内外binding，不填字段、改意见或创建事件。
   之后仍须作者实际native final，原submit逐项全文质量/schema/身份/native校验照常。

`AGENTS.md`只补这种前瞻任务的恢复规则。独立作者不可读主审notes；拿不回当前路径/
摘要时报告路由不可用。checkpoint不会自行认证task来源、审查事实或接受报告。
原publish不是Provider发送或业务stage签名，helper拒绝携带伪造event/attestation。
每项实际stage需要各自的新checkpoint，不能替代真实source、response、policy全文。

后续实际待审时，先由既有handoff校验并导出任务，再使用：

```text
python -m scripts.host_review_task_checkpoint publish --checkpoint TASK_CHECKPOINT --task-file VERIFIED_TASK --reviewer-id INDEPENDENT_ID
python -m scripts.host_review_task_checkpoint dispatch --checkpoint TASK_CHECKPOINT --checkpoint-sha PUBLISHED_SHA
```

将dispatch原文交给既有独立作者；作者按其中要求读材料、独立成稿、预检答案并输出真实
native final。主审仍先自行留全文意见，再用既有native submit导入。没有新付费授权前
不得创建可发送的新Provider批。闭批原件和历史封存不走新checkpoint，也不重新签署。

## 验证与实际探针

9项新聚焦检查覆盖任务切换、旧答复拒绝、task/checkpoint改动、缺失/create-only、内外
绑定错配、duplicate JSON、伪造事件、probe与review用途隔离，以及原意见字节不被修复。
连同80项既有native事件检查，共89项通过。它们验证工程路径，不替代模型质量。

既有独立主体`01a0ebaf-790b-70b2-9f02-9e354d9ea50b`实际执行两个短路由探针：

- alpha：新的initial绑定；原生final从最新completed turn读取并核checkpoint一致。
- beta：切换到不同计划/请求/响应/报告及final阶段；原生final一致，alpha原答复用于beta
  被`host_checkpoint_answer_binding`拒绝。

alpha第一次把正确摘要转录错，实际`host_checkpoint_digest`在本地拦截；明确给出原摘要
后，作者仅修正自己的路由探针答复并验证。文件没改，业务报告没重评。随后dispatch直接
生成命令减少转录。此插曲保留，不能将首次失败删成无故障探针。
两个探针仅输出`probe_only=true, review_performed=false`，未读业务报告或闭批Provider
原件，没有StageAssessment、verdict、native review attestation或资格贡献。

alpha原生引用：
`01a0ebaf-790b-70b2-9f02-9e354d9ea50b/01a11ec8-dabe-7860-9956-08a1885f8047/msg_0f1ffc23fbabd630016ac8650a6ae8819180489e94d4422396`。
beta原生引用：
`01a0ebaf-790b-70b2-9f02-9e354d9ea50b/01a11ecb-4472-7fc3-be3c-5c94a3ede7b9/msg_0f1ffc23fbabd630016ac8655e7340819191731b2fafac5882`。

公开证据为`data/evaluation/results/golden_host_task_delivery_recovery_20261009.json`，
SHA256 `c4571f7b62c84680cf694e29e0b5d60469c2449338f5699ad5b9f7c2bae046ce`。
本地checkpoint/task/作者答案/native读回位于
`C:/Users/33502/Documents/Agent/outputs/riftcoach-host-task-delivery-20261009`。

## 限制与下一决定

没有主动触发或复现自动compaction；路由探针短小，不证明长全文审查跨压缩稳定。
保护仍依赖作者执行恢复读取，最终原native绑定校验继续拒绝漂移；不能保证绝对不再错批。
任何真实业务硬故障仍按具体授权停批，不能靠重写binding、换作者或追加重评求通过。

当前不需要修改Flash/GLM政策来修Host恢复问题。先将该交付方式纳入下一具体尾链方案
的操作要求和源码冻结，准备其CI/预算/真实主体资料后再申请新Provider范围；不是重开
已关闭的六尾链。正式完整15仍依赖实际尾链质量与两处分歧的有效处理，不能自动触发。
旧3/15、历史2/15分别保留，新增资格0；自然产品消费和8E等全局依赖不变。
