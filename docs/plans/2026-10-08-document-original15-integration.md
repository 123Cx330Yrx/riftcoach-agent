# 文档呈现完整链路：离线适配工作卡

## 目标和决定

三例真实完整初评支持进入同版本整链验证，尚未验证必要编辑和fresh。当前工作把同一份
完整Markdown文档请求接入现有review/edit/fresh和原十五例资格路径，不添加新审查环节。
沿用GLM审查/Flash编辑、完整上下文标准、五调用401920 tokens/900秒产品预算。
原15历史严格2/15；三例初评不转授新候选资格；8E未完成。

## 原理与数据流

模型现在看到正文文档和段号标签，来源仍是完整原数据。发送、预算及回执读取必须认同
同一份四消息请求，否则只更换工作流会在发送或读回时被旧三消息合同拒绝。

实际入口 `scripts/run_document_review_qualification.py` 复用既有v2执行器、CI及真实主体预检。
新显式 `document-review` backend逐例重建请求字节、SHA、大小、目录与schema；绑定
`DocumentReviewWorkflow`、四字段review-bound编辑器、版本1.5.6的未准入预算合同和
`DocumentRoleProviderFactory`。初评/必要编辑/fresh各阶段仍做真实全文双审；fresh从实际
新成稿构建，journal同时保存baseline与实际请求摘要。最终严格consumer读取原始回执、
重放工作流及每阶段native事件，检查关闭封存；不能用旧profile或三例初评替代。

角色分类器只验证文档协议、标签、政策和schema，并临时还原三消息给既有角色分类器。
这份临时对象不会发给模型，也不认证来源含义或尝试恢复原始JSON字节。事实表按列分组，
保留所有值却不保证恢复原对象跨组插入顺序；重新序列化不能伪称获得原source/catalog SHA。
完整来源及重评previous raw的字节绑定由既有issued/prepared比对和严格工作流回放负责。
默认生产resolver未注册1.5.6，也没有新增产品composition/Skill采用；这是新资格入口。

## 验收与失败分支

- 所有原15原始input/report SHA不变；新请求重新冻结，schema/catalog值维持原来源。
- 使用真实router/factory/预算/receipt writer，替换网络端点验证初评→编辑→fresh和双审导入。
- 从关闭封存反向重建全部15例，拒绝错误身份、篡改正文/段号/schema/旧fresh及旧资格。
- 五槽与第六次拒绝、超量发送前拒绝、未知用量保留占位；无自动retry或预算绕过。
- 运行中源码冻结，不在测试/实测过程中修改它所绑定的文件；源码变更后重新建立验证身份。
- 后续真模型同批首实质失败即停止，不重开关闭批、不把不同版本成功拼成通过。

上述替身证明工程接线，不证明新版本15例真实质量、900秒可达性或自然Agent消费。
真实付费方案必须完成冻结及相同提交CI全绿后取得其新增授权，本工作包Provider0。

## 后续产品依赖

同版本真实质量合格后，再检查自然生成/工具消费、Coach/Review/Training/Evidence联动、
本人Training、journal/Worker/DB/API/UI消费；前端审美/必要重做/英雄头像、Memory、身份运维、
两树整合及八维学习沿原活动计划保持，不把此评审专项当整个Agent项目。

## 验证记录

新预算/身份/请求/冻结篡改及执行接线18项通过；初次整15例替身执行、双审及strict seal回放
通过。清单补齐后的整15例执行、双审及strict封存回放复验通过（503.92秒墙钟）。相关既有130项回归通过
（807.34秒墙钟），compile及governance/diff检查通过。独立代码复核发现六个实际未覆盖的
解析/段落/报告校验依赖，现已纳入身份与外层源码冻结；末次复核未发现剩余阻断。

本轮发现并纠正两处执行问题：初稿错误地从表格投影读取原facts，第一例发送前失败；改为
明确的角色协议校验，来源认证由精确workflow/replay负责。一次测试过程中编辑冻结源码，
导致candidate_identity_mismatch；保留该失败，固定源码后重新完整验证。这些都不是模型
语义失败，也没有产生真实模型用量；不得把未验证初稿或测试失败记成产品进展。

冻结准备：`data/evaluation/results/golden_document_review_qualification_preparation_20261008.json`，
SHA `6c9d36bb3540b17fd88d636db71ac682f41ea53754f11a36d600062b81d0d304`（canonical plan）。
39项外层源码及22项新身份源码冻结，另由旧业务manifest绑定政策/传输组件。逐例原输入
保持，15个实际四消息request SHA重新生成；首次输入上界43738—48066。
准确计划重建通过；真实principal预检当前可核route/final，保持native-final-attestation-v1，
不保证未来原生输入可读性或替代后续每阶段真实final。首次预检因独立审查尚在运行未有
完整final拒绝，作者完成后真实预检通过，没有放宽合同。

待授权完整原15方案最多35次（Flash编辑10、GLM审查25）、3386880 tokens、10500活动秒，
Host等待86400秒，未缓存保守估价37.167104元；这是估价而非硬账单金额。无重试/重评、
无旧资格转授、首阶段拒绝即停。当前Provider0，等待器未创建，接续自动任务保持暂停。
最终提交公共CI全部成功并获对应新授权后才可首次执行。


提交前统一本次五份manifest为仓库要求的LF；Windows默认CRLF会令CI的原始manifest SHA
不同。仅格式改变，15份请求、来源、schema、源码文本摘要及预算逐项相等；重建最终冻结
计划为上述6c9d36bb，针对最终格式复核身份/执行接线/预算回归，不借旧实测资格。五份manifest
同步确定性共享实现指纹，模型/业务政策与产品版本不变。完整15的结构fixture使用空编辑，
只证明执行/Host/receipt/回放协议，绝不证明实际错误修好或真实15质量。
