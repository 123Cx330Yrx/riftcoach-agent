# 互补职责与编辑消费：离线实现及下一验证范围

2026-10-14。当前完成的是离线合同原型，设计见
[ADR0117](../adr/0117-proposed-complementary-review-duties.md)。
上批关闭提交8a69e4ec的公共CI38507399305成功；本轮无模型发送。

## 已解决的工程问题

事实专责排除了“是否引用/使用知识”的任务完成度义务，但旧完整校验器仍会以
`native_missing_knowledge_citation_unreported`拒绝缺引用的pass。离线反例已复现。
新隔离校验器明确区分职责，同时保留未知引用、来源、段号、协议和注入检查。
原完整校验器及冻结源码保持，旧五次初评结果没有重判。

`scripts/review_duty_composition.py`把同一完整报告/来源交给facts与completion；
用input/report/request SHA及stage绑定两份原样意见，不平均分数、不合并问题。
准备编辑要求明确的兼容状态；调用者填clear并不构成真实语义认证。
两份意见进入原block editor，沿实际锚点/重叠/回执校验组装新稿，再为新稿构建两份fresh。
fresh不带旧意见；结构双pass始终不能打开产品发布门。

这使“评价→意见传递→改文组装→新稿复查”能在软件层表达。completion政策仍未实测，
真实兼容裁决、Host绑定、观测、共享预算与取消接线、实际模型编辑均未完成。
原三处语义问题仍未证明稳定解决；真实full分歧不改签，熟悉材料不充当holdout。

## 验证与复现

- 19项新离线测试覆盖完整来源、职责边界、污染/协议拒绝、原样双意见、实际组装和fresh绑定。
- 47项既有预算/editor相关回归通过；均为软件验证，不是模型调用或Host审查。
- `scripts/audit_review_duty_composition.py`从15份完整固定输入构建30份请求，核正文/来源/schema
  保持，并核旧live身份全部拒绝。结果为
  `data/evaluation/results/review_duty_composition_offline_20261014.json`。
- 审计保存五份相关源码SHA。已有131本批原件、11件包、77源码及历史证据按旧清单复核；
  canonical历史字节保持。本轮不创建或改写任何业务run。

复现测试：

```powershell
./.venv/Scripts/python.exe -m pytest tests/test_review_duty_composition.py tests/test_document_review_timed_budget.py tests/test_report_block_keyed_editor.py -q --tb=short --show-capture=no
./.venv/Scripts/python.exe -m scripts.audit_review_duty_composition --output <new-path-outside-data/runs.json>
```

审计输出create-only，应使用新的临时输出路径并在比对后清理；不要覆盖已封存证据。

## 最小真实消费验证提案与执行缺口

只复用上批duty-3的完整输入快照，重新取得facts/completion初评；若两份均经真实审查接受、
有实际可修问题且修法兼容，则一次Flash编辑，再对实际新稿分别fresh。最多4 GLM-5.3/high
加1 Flash/high，共5请求、483840tokens、2700活动秒、86400Host秒，单次600/300秒与32768输出。
未缓存合同上界估价5.8609664元，实际账单不以此为硬封顶。没有生成、重试、补发或资格授予。
双方initial都pass则结束，不能硬造一次编辑来声称消费成功。

下一工作包须先完成隔离开发入口：

1. 新请求/回执身份绑定完整政策、来源、职责、阶段、编辑协议及预算，旧入口继续拒绝。
2. 将主审/独立真实native接受与两份修法的兼容裁决绑定到同一稿和原样意见；clear不能自签代替。
3. 每次发送前核run库存、run外观测/作者、完整请求和共享账本；取消/硬故障停止后不得恢复发送。
4. 用离线整链验证双pass跳过、拒绝/冲突停止、实际改文、两fresh、预算耗尽与未知用量，
   再形成执行包、preflight、同提交CI、具体新授权。当前尚未达到执行准备完成。

任何facts实错、completion无依据要求、错误修法、fresh失败或冲突均否定该链在此例的充分性；
协议/native/transport/预算故障停止，不将缺失当成功。正向结果仅支持开发方向，不能重启原15。

自然产品含两次生成时最坏7调用，当前5调用/401920tokens/900秒不自动扩容。
以后必须复用`CoachBudgetedProvider`的同一账本/时钟和真实Worker取消/租约门。
仅提高调用数而保留token/时间上限也可能走不完；当前不能承诺自然任务完成。
automation保持暂停；本提案未请求也未取得新付费授权。8E和下游产品依赖保持未完成。
