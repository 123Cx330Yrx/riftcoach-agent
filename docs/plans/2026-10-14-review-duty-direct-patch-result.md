# 初审逐字补丁固定报告：真实执行与关闭结果

2026-10-14。本例完成了初审给出精确补丁、程序原样应用、完整新稿验收及双职责 fresh。
结果为 `development_chain_pass`，只支持继续考虑该开发方向，不代表稳定改善或产品采用。
方案见[冻结启动提案](2026-10-14-review-duty-direct-patch-launch.md)，
机制见[设计与反证](2026-10-14-reviewer-authored-patches-design.md)。

## 实际行为与语义

| 阶段 | 实际结果 | 主审与独立审查 |
|---|---|---|
| facts-initial | 72 / needs_revision；两个真实问题、同一 repair 组的两个替换 | 完整意见、解释、来源和全部补丁均接受 |
| completion-initial | 95 / pass；无问题和补丁 | 接受，未虚构额外任务要求 |
| compatibility | 两职责意见兼容；无模型调用 | 完整来源与全部补丁核对后 clear |
| edit | 程序预览完整新稿；无 Flash 或模型重写 | 两方四项 ReportAssessment 均 true |
| application | 唯一原样应用两个替换 | 只绑定四项前置 Host submission，不倒灌 fresh |
| facts-fresh | 96 / pass；issues 空，block 4 可读性标记 | 对同一完整实际稿重新核对后接受 |
| completion-fresh | 96 / pass；issues 空，block 4、19 可读性标记 | 对同一实际任务和资料消费重新核对后接受 |

原稿第 14 段明确用中单口径却写败局早死 2.67，并称差异很小；第 4 段在中单比较语境沿用
早死几乎相同。真实来源是中单胜局 3、2 次，均值 2.5；中单败局 0、1 次，均值 0.5；
混合败局加辅助 7 次，三局均值才是 2.67。新稿两处均写明中单胜 2.5、败 0.5、胜局更多，
并把 2.67 明确放回混合口径，保留仅四局中单及不能据此推断一般关系/因果的限制。
完整上下文保留了描述性差异，没有断言少死无效或导致失败，未将措辞优化升级成事实错误。

两条补丁使用严格 `block_14`、`block_4` 和唯一锚点，互不重叠，原文坐标逆序重建与实际稿
逐字相同；其余 23 段和两段剩余内容原样保留。分位置表格、伤害构成解释、事件时间、知识
引用、未知训练目标的条件选项及观摩身份均经全稿核对。没有修字段后重买或遗漏 fresh。
第 4 段的泛指混合均值拉低未被扩成所有指标全称；第 6 段稳定按本样本中单补刀语境审查。
正文 K3/K4/K5 等实际支持行动；未提供 OP.GG，正文已说明缺口，不强制编造消费。

- 原稿 SHA256：`a3889a655782132f269f1a4cda7b0506e242dbd783df17d03740f01b1d1b3ba4`。
- 实际新稿 SHA256：`0da0c6299711cb8feff3c135b86768c3d94c82e159110c709b5fef7a3ac3d2c3`。
- 两项 fresh 的 report 与唯一 application 的 report 完全相同。

## 执行、用量与证据

用户明确“授权继续”后签发新授权；冻结 HEAD `505aff8fbd5919fe352e5c2a99e100d9358db224`，
公共 CI `38564530018` 全绿。实际 cwd/Python、即时 native、有效授权、clean HEAD、854 源码
配置和三文件包检查通过后，唯一 waiter 启动原 runner；未重启、重试或补发。授权有效期保持
2026-10-14 12:43:55 至 2026-10-15 12:43:55 UTC。原准备和授权前行政快照没有改成业务证据。

主审 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4`，独立复用
`01a12f0c-bb7c-74e3-ad92-775eefbe399a`。六个 stage 各唯一派单；独立自行写 run 外作者文件、
check-answer、唯一完整 native final；主审实读真实事件后提交自己的 notes。原生记录在
submit、后续发送、应用与关闭回放中核验。行政 input 直读 false 的限制未被改写为保证可读。

| 调用 | 输入 tokens | 输出 tokens |
|---|---:|---:|
| facts-initial | 14426 | 6384 |
| completion-initial | 13078 | 1329 |
| facts-fresh | 13081 | 4902 |
| completion-fresh | 11733 | 906 |
| 合计 | 52318 | 13521 |

实际调用及 HTTP 各 4，均 GLM-5.3/high、HTTP 200，Flash 0。known 共 65839 tokens；
unknown_reserved、receiptless、发送未知均 0，未发 slot 为空。按合同输入 8 / 输出 28 元每百万
token 估价 **0.797132 元**，实际账单未核实，不能当账单硬上限。
活动 318.515 秒、Host 3959.876 秒、墙钟 4278.391 秒，均在各自限制内。
runner 退出 0，stderr 空；末阶段 `host:completion-fresh`，没有执行失败点。

严格只读 replay 与唯一 create-only `Operator/seal.json` 均通过。使用最初 stdout 实读的
guard SHA `29ed902d944454a39ffcfc81ffa56b9187d06b36c98bc4ad8e2167a366e5cdfa` 和关闭时 stdout
实读的 exit SHA `bf03a830b9eafacabc9503e0a3adf0cb24d995bdb85b776129e1a0e43ee23016`，没有从
现盘重新计算一个信任根替代原记录。seal SHA 为
`0d17d2b9e027ad45891a52c67c5becd3f4836768bbf5c4a91b08591f53428656`。

关闭核 103 份本批原件的精确库存与 SHA、六份真实 native/作者、四份 run 外无正文观测、
控制库存、唯一应用和全部来源绑定。854 源码/三文件包保持。旧 847 源码/3 包/64 原件、
旧五次批 131/11/77、旧职责 43 原件和其余八批 760 原件逐件 SHA 保持，不回写旧结论。
机器记录：`data/evaluation/results/review_duty_direct_patch_close_audit_20261014.json`。
原件：`data/runs/model_comparison/review-duty-direct-patch-20261014`；Operator：
`C:/Users/33502/Documents/Agent/outputs/riftcoach-review-duty-direct-patch-20261014`。

## 方案去留与未完成事项

本例表明初审可以同时给出正确意见和精确修法，省去第二模型改写后，真实新稿通过完整验收
及双 fresh；这是较旧失败链新增的实际编辑消费证据。不能据两次运行断言隔离变量的因果
改善或稳定率：新请求/合同不同，且材料熟悉，非 holdout。错误补丁仍可能通过结构预览，
开发 Host 验收不能代替产品自动语义保证。原 15 的旧失败、分歧与未认证项保持，不授新资格。

自然任务仍为两次生成加四次审查，共 6 次，超过产品 5 调用合同；不能因本例固定报告只有
4 次就宣称预算问题解决，也不删职责或跳 fresh。下一动作是零付费核对自然任务路径与预算
的方案取舍，形成具体可审查结果；本批已关闭，automation 已暂停，没有下一付费批授权。
正式同版本 15、自然 Coach/Training、四块联动、完整 journal、前端头像审美、Memory、身份
运维、两树整合、独立评估及学习保持。8E 未完成，代码、Owner 理解、来源资格与公开成熟度
分别验收。仅更新结果文档与审计记录；治理和差异检查通过，不重复已通过的无关离线测试。
