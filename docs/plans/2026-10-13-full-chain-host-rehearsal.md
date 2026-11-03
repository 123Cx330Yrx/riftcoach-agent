# 三阶段真实 Host 交接演练

## 工作卡

- 目标：补足新证据入口只有模拟 native 事件的缺口，验证原独立作者实际写文件、check-answer、唯一 native final、主审导入及严格封存。
- 路径：`scripts/full_chain_host_rehearsal.py` 私有复用 `FullChainEvidence` 与原状态机，选择提交内 `claim-scope:4` 单项，依次初评、必要编辑、完整终评。完整业务输入和政策不变，所有业务响应固定为离线夹具。
- 边界：Provider/HTTP/实际模型 tokens 均 0；内部三份 transport/usage/observation 是显式 synthetic 记录，仅用于驱动原状态机。网络连接在演练进程中禁止，完全不读取模型密钥。真实的部分是两主体判断、作者文件与 native 事件，不是模型能力或质量资格。
- 主体：原主审 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4`；复用 `/root/host_scope_calibration`、`01a12f0c-bb7c-74e3-ad92-775eefbe399a`。每阶段一次新任务，恢复同任务仅消息，不新建主体。
- 目录：新 run `data/runs/model_comparison/document-full-chain-host-offline-20261013`；run 外操作记录、作者和观测在 `C:/Users/33502/Documents/Agent/outputs/riftcoach-full-chain-host-offline-20261013`。未来原15准备目录不使用，旧 run 不重开。
- 验收：先完整离线预验，再冻结源码/plan 唯一启动；逐阶段实读全文、来源、实际 request/response/stage，主审与独立作者各自判断。初评只判断意见；后两阶段另逐项核四个 ReportAssessment 字段。全部已审阶段读取真实 native 事件，作者原件/checkpoint/观测保持，严格只读 replay 和 create-only seal。
- 失败决策：有效语义拒绝停止该case后续阶段；硬故障停止演练，保留原件，不补发或伪造。演练不授资格，不延展任何旧付费授权，automation 保持 PAUSED。

## 当前状态

首个案例已经关闭。初评真实作者文件、checkpoint重读、check-answer、唯一native、submit和严格seal均完成；主审接受，独立作者因第6段“四局中单”证据与“这5局”结论的范围冲突判漏检。双方原判断保存，case按语义拒绝终止，revision/final均未发送。28原件、53源码SHA不变；9条公开原生命令exit0，外部Provider/HTTP/tokens均0。内部1份响应/30tokens只是synthetic计数。真实三阶段成功仍为false。

证据：`data/evaluation/results/full_chain_host_rehearsal_20261013/initial-disagreement/`，seal SHA `63e009ffd6f03fe16aa033918a10b4e0bfbc9142b95c11d96b039f8f1ee8aa83`。这个结果证明分歧能阻止依赖阶段，不能冒充正例全链通过，也不修改或补签旧质量判断。

接续一个**不同的工程控制**：`scripts/full_chain_explicit_host_rehearsal.py`和提交内`full_chain_host_count_20261013.json`。保留同一五局来源、政策和状态机，另写短报告只植入“三胜两负/60%”与实际“两胜三负/40%”的明确计数冲突。它不是原15的替换材料、不是上一报告的重评，也不用于模型质量。单独冻结到`document-full-chain-count-host-offline-20261013`，仍由原两个主体真实独立判断，最多三份离线响应；先完整预验，再唯一启动。原失败的run、答案、脚本及封存不改。若该工程用例仍被拒绝，同样停止依赖阶段，不绕过判断求通过。


## 第二案例关闭结果

`host-io-count:1` 已关闭，执行 plan `297dd0e06031ea71d3e356c6469cc182e6c6b931daddf9b22c8f4a34e9c5ecb4`。initial 两主体接受；revision 两主体均拒绝 `unsupported_explanation`。原稿的“三胜两负/60%”确已改为“两胜三负/40%”，完整16段报告的四项 ReportAssessment 均 true；但实际编辑 reason 仍是 `OFFLINE fixture correcting the direction of the mixed-sample means.`，与真实计数/胜率修改不符。政策要求 reason 解释必要修改，正确成稿不能使错误编辑理由合格。这是本地离线夹具复用时遗漏字段的确定性缺陷，不是 GLM 的失败。

两次作者 create-only 写入、check-answer、唯一 native final、主审实读及 submit 均完成。初评7条、修订7条公开原生命令 exit0；修订中发生上下文压缩，恢复后和 final 前均重读同一路径/SHA。程序按 `revision_host_rejected` 结束，final 未发送，无重试/改答案/补签；runner exit0。严格只读 replay 与 create-only seal 通过，48原件、54源码、run外作者及观测保持。seal SHA `a0a3a6f9b0a4023aac2a38133b7bac6d829a818ca3a14b2a544307ae6d60f2d3`；公开 native、主审原件、材料检查和审计在 `data/evaluation/results/full_chain_host_rehearsal_20261013/explicit-count/`。

本案例外部 Provider/HTTP/真实业务模型 tokens 均0；内部2响应/60tokens及0.000484元只是 synthetic 账本输出，不是实际费用。两案例总计3个真实 Host 阶段/3次 submit，均真实封存，但**没有成功的真实三阶段正例**。首案例初评范围分歧继续保留；第二案例不能抹去该分歧。两者无新增资格。旧458原件与首案例28原件逐个复核不变。

## 验证与裁决

三个独立测试用例通过：original整链与禁网恢复2项（208.51秒），explicit整链1项（204.75秒）。native事件均为明确替身，测试证明IO/路由/状态机，不能证明夹具理由语义正确。explicit预验首次因transport身份默认值不符而失败，修正构造器使用明确REVIEW_MODEL_TRANSPORT_ID后通过；该次未启动真实run。真实审查又暴露reason错配，不能以先前测试通过掩盖。

首次偏离位于本地响应生产者：第二适配器只替换 BEFORE/AFTER/来源，复用父 offline_factory 时仍沿用固定的混合均值 reason。未来适配器应把完整编辑响应连同理由作为同一夹具绑定并在派发前检查，不能只替换正文。当前两个冻结脚本和已关闭run不改，也不新开第三次演练去冲通过。缺失的真实final正例如实保留。

版本边界检查见 `version-boundary.json`：原15有5份报告含“四局中单”证据后“这5局”结论的争议句；这里只是字符串定位，不给其他4份补判。当前time600的15个请求均被旧资格身份入口拒绝，不能拼旧资格。接续无付费准备应先厘清原15实际范围命题及前瞻标签/版本绑定，再决定工程正例修复与正式证据范围，避免继续用不同简化报告替代质量主阻断。旧报告、标签、审查和失败原件不回写；无新付费授权。

执行基线53abb5f4的公共CI38387480676已success；本次新提交仍须查询自己的CI。automation保持PAUSED；8E、自然消费和所有产品依赖未完成。
