# 自然观摩单任务：模型双初审漏检，结束本批

2026-10-15。本次真实运行完成，业务验收拒绝。主审和独立作者分别指出同一观摩/训练边界错误；
作者原件与真实 native final 另有一个末尾换行差异，严格字节验收失败。原件均保留，未裁剪、
重签或要求第二份 final。8E 未完成，候选保持拒发布，automation 保持 PAUSED。

## 实际执行与业务结论

用户确认本包费用后曾要求暂停，重启后明确恢复。沿首次确认后观测时钟记录授权，未因重启延长；
其时间不是伪造的原生消息时间。执行绑定干净 `f606ecb42cc1a26d06f99b411b57c9013e46c2e6`，
CI `38704482702` 全部 8 项成功；771 份准备绑定文件逐项一致，即时 native 路由及绝对路径启动通过。

真实 typed OBSERVED 任务进入现有 Runtime/AgentLoop：第一次 Flash 自主发出四次 knowledge.search，
返回 5 个知识片段；第二次 Flash 生成七节初稿；GLM 事实初审 96/pass，完成度初审 95/pass，
后者仅给表格可读性 advisory。两初审均无 issues/repairs，按合同直接结束，未强制凑足六次。

| 检查对象 | 结果 |
|---|---|
| 实际调用与预算 | Flash/high 2 次 + GLM-5.3/high 2 次；4 HTTP；59574 tokens；229.531 秒 |
| 账本 | 0 未知用量、0 HTTP 未知、0 缺回执；2 个未预留调用槽 |
| 成本 | 原报价下未缓存估算 0.4182756 元，不是账单 |
| 发布 | Runtime completed，candidate_initial_pass_unqualified；API rejected、report_available=false |
| 编辑与复审 | compatibility、preview、application、双 fresh 均未执行；没有编辑成功证据 |
| 原件 | 46 份 run 文件、run 外观测、原 stdout guard/closure 的只读 replay 通过 |

初稿第 6 节 HOST_BLOCK 24 要求“5 局观察周期内输局补刀/分钟不低于 8”，并“记录训练后的指标变化”。
用户任务只允许观摩练习：阅读者无法通过观摩改变被观摩比赛的结果；若指标属于阅读者本人，
又没有本人数据或目标支持。前段“以下均为观摩练习”的声明不能消除动作对象与目标的冲突。
K3 支持记录、周期与复盘方法，不支持把这些他人比赛转换为本人训练成效。两初审都漏检。

主审先独立保存意见，随后读取独立结果；双方对最早偏离和两次漏检一致。数值、分组、引用及
外部来源大部分正确，混合样本描述未被补成“全部指标/某位置必然如此”的错误；条件位置选项
本身不是缺陷，OP.GG 已满足至少一项事实联系条件建议的义务。否定集中在真实行动，不按篇幅、
建议数量或可选措辞增设门槛。最早偏离是第 2 次调用的生成，后续 pass 不抵消它。

## 原生审查与封存缺口

固定 checkpoint：`98ed52bac2f6502b98cc28eeb096a61e74392cddabdb9963bce19efbf99f6904`。
复用独立线程的真实事件：
`01a12f0c-bb7c-74e3-ad92-775eefbe399a/01a13f97-35e3-7222-bd1c-2a95c816d90f/msg_0789f6f5c6269665016ad0cbe2b5c0819191cbb5a78865de19`。
父子路由、唯一完整 final、六字段绑定及语义 JSON 均核验；当前派发 input 仍不可直读，不冒称可见。

- 主审原件 SHA：`e8fdbc990111ac238dbfdd967edd2302eb07a912bdc6978f42e9caeb3d583c23`。
- 独立作者 11150 字节，SHA：`74d36bf5d8ca24c7bf2444089611cccde647a8330c5f1035c4626870adc0f75a`。
- 原生 final 11149 字节，SHA：`db73e35e513f46ce1952d0d26582f246345d9212596401fa03489a3205a7f69a`。
- 唯一差异是作者末尾多一个 LF，JSON 值完全相同；严格字节验收为 false，未归一化冒充一致。

Operator 唯一 create-only seal 状态为 `closed_with_author_byte_mismatch`，决定为 `reject_candidate`；
这记录失败关闭，不声称完整审查链验收成功。seal SHA：
`3a49ec71bdc038b73a7def5e84ee0d5183ed0deee23973bb6abfbcf26ef6d70a`。
原 stdout guard 为 `ec86ef5cec7119c21140fdadb5fe5931e72cb4858a32b0562e5bf3b5a63fe452`，
closure 为 `2dc72b778f4971a19492d6e74bb8fbf61ffac56e3f31637abe9e238f78f01ac5`，未事后换根。

27 份作者/原生/控制文件及明确移除私有 reasoning 的公开阅读投影，按原字节归档到
`data/evaluation/fixtures/natural_duty_observed_review_20261015/`。全部库存和判定在
`data/evaluation/results/natural_duty_observed_result_20261015.json`。
46 份完整运行原件留在 `data/runs/model_comparison/natural-duty-observed-20261015`；
Operator 为 `C:/Users/33502/Documents/Agent/outputs/riftcoach-natural-duty-observed-20261015`。
公开阅读投影不冒充含私有字段的原始传输文件；原始字节受 closure 绑定。

## 下一工作与机器恢复

本批结束，不改这份报告后补发、不重买或重开。下一步是零付费核对“观摩者能执行什么动作”的
身份与证据约束如何贯穿 typed 请求、生成和两职责判断，用完整正反例区分任务表示缺口与模型
漏判，再选择机制修复；不把数字 8 或单句提示当根因。原有政策已写明观摩边界，遗漏不是由
缺少这句规则直接证明的。工程接线有效部分保留，当前语义候选不准入。

重启后 Docker 同类 AF_UNIX 残留再次阻断。确认进程停止后，备份并重建 Docker/run 与
docker-secrets-engine 两运行目录；原容器、数据卷不变，Docker29.7.2、healthy、15432、SQL1、
迁移0014_message_projection_status 已核。记录位于本机 docker-recovery-20261015/recovery-restart-203601.json；
未证明上游永久修复，不改用户网络或重置卷。

本例是熟悉公开历史来源，不是 holdout 或实时抓取。正式同版本15、自然 Coach/Training、
四块联动/journal、前端审美头像、Memory、身份运维、两树整合、独立评估和学习仍保留。
旧固定报告成功、失败、原稿保留未决与所有原件/裁决不重判；原产品五次上限不变。
