# 文档呈现三例完整初评：执行接缝

## 目标、输入与判断

玩家任务仍是Coach结合实际来源给出可靠分析。当前主阻断是完整初评误报正确范围，不能由后续
人工删问题或编辑成功抵消。本包只把已裁决的三例筛查接入现有真实请求/回执/双审链路，判定
此呈现是否值得后续同版本验证。三例及所有事实、历史比较和结构风险见
`2026-10-08-document-review-probe.md`，不增加案例、提示规则或输出字段。

顺序：原混合报告 → 仅明确中单范围的反例 → 完整正确稿。模型看到完整报告和来源；Host预期/
旧结果不进请求。任一实质误报/漏检或其他失败立即关闭；全过也仅是已知同源的窄范围信号。

## 路径与边界

`scripts/run_document_review_diagnostic.py` 复用既有 `execute_plan` 的同提交CI、clean checkout、
真实原生主体预检、凭据读取、create-only批目录以及原流式RoleReceiptedStreamProvider。
新诊断selector只允许三个冻结四消息请求；仅允许执行预算metadata和缩短timeout，恢复到旧
请求做来源/schema/角色核验。实际发送和回执绑定的是新四消息原字节，不发送旧baseline。
生产默认router和contract没有注册该视图，实例诊断路径只用GLM-5.3/high，Flash零调用。

预算构造先核旧合同的端点身份，随后在该单次实例安装更窄限制：最多3次、290304tokens、
900活动秒；Host等待独立最多86400秒。请求仍有64000输入/32768输出/300秒上限；未知调用的
预留保留。沿用原预算/转发/Host clock逻辑，不建立第二套传输或取消行为。

现有 `read_role_calls` 增加显式可选的可信诊断角色resolver，默认仍用采用的生产分类器。
诊断resolver逐个精确还原冻结请求，其他字节/ordinal/role/model/profile/reservation/terminal/
usage检查仍全部执行。原15资格入口没有传此resolver，仍拒绝四消息。该读回能力不授产品资格。

`scripts/document_review_handoff.py` 从真实transport重建source、journal和stage，核准全部摘要，
逐例输出完整全文审查任务。主审和独立审查继续用native-final-attestation-v1；都必须核查所有
评审事实、解释、修法、引用、正确内容保持和标签引发的新错误，不机械匹配目标block集合。
report_assessment必须null：接受的是本次初评质量，不把带真错的原报告认证为修复。
导入在原OS关闭锁下原子/create-only发布；关闭或重复提交拒绝，不能用迟到决定重开批次。

## 冻结、授权与失败决策

冻结覆盖三份请求/来源/policy/schema、历史封存摘要、代码依赖、主体、实际budget及proof策略。
准备命令只读源码/原件，不用凭据，不发模型请求；输出plan采用create-only。
未来执行必须绑定最终提交、同提交公共CI全绿、当前真实主体预检、用户新增批预算授权。
不会重开已关闭批或借旧余额。预算保守未缓存估价4.288512元，不是账单硬封顶。

首语义失败否定此呈现对该例的充分性；不追加近义提示重跑。传输不完整记语义未知，保留调用/
已知usage/未知预留和原件。三例全过后才能选择同版本完整质量验证和正式身份接入；不能增加
历史原15的2/15、宣布8E完成或证明JSON因果。具体决策沿前包表格。

## 本地证据

新入口14项检查通过，包括真实传输回执写入/读回/原生导入（响应仍为脚本替身）、预算与身份
错误拒绝、首失败停和关闭拒绝。与旧scope入口/准备器联合37项通过；另关闭期间晚提交1项
通过，旧默认回执/孤儿/未知用量16项回归通过。不同组覆盖有交叉，不相加当独立业务样本。
治理、编译及diff检查通过。独立复核指出两项冻结依赖遗漏：role_task_outcome与严格JSON解析器
所在的golden_inference_scope_v5，已补齐；连同实际传输/Provider等直接实现共57项源码冻结。
预算、角色、回执/Host绑定和关闭竞态未见其他阻断；真实原生主体预检通过，执行前还须再次预检。
当前native-final证明可读route与完成final，原生输入当前不可读且不保证未来可读；沿用已采用的
native-final-attestation-v1，不把该预检宣称为未来审查可用保证。

冻结SHA：`bdb678d80a8568443ce92d01ec3a636542a4ebe6f5c6ea0b5ecf6d63a1f376a6`。
公开计划：`data/evaluation/results/golden_document_review_diagnostic_plan_20261008.json`；
本地create-only计划及真实预检：
`C:/Users/33502/Documents/Agent/outputs/riftcoach-document-review-diagnostic-20261008/`。
精确计划重建核验通过。代码已具备执行入口，但新增预算尚未授权，未启动执行或等待器。
这些只证明工程路径，当前未发新Provider请求；核心误报未获修复证明，原15仍2/15、8E未完成。

复现入口（后端根目录）：

```powershell
.venv/Scripts/python.exe -m scripts.run_document_review_diagnostic --root-thread-id <root> --independent-thread-id <independent> --output <new-plan.json>
.venv/Scripts/python.exe -m scripts.document_review_handoff task --key actual-mixed
```

执行命令还须指定 --execute、--preparation、--plan-sha、--ci-run、--env-file、--codex-executable；
本文件不是费用授权。关闭后的结果按白名单公开封存，完整原件保持本地，不发布凭据或私有推理。
