# 自然Coach消费路径免费核验

2026-10-09；代码基线e0d3437432324f2a10a85a1cc85057a513e8f9b5。
本包查已有产品路径和真实资格依赖，避免为未选语义方案再造管线。
Provider0；未启动服务、读取密钥、访问真实Riot/DB或修改产品代码。

## 已有路径与当前组合缺口

| 数据/控制路径 | 已有实现 | 本次证据及限制 |
|---|---|---|
| 自然请求→有身份的近期数据→Runtime请求 | app/product/recent_review.py、recent_review_service.py | 应用服务typed入口、错误安全投影与回执验证已覆盖；上游使用替身 |
| 本地知识/Memory→Agent→review共享预算 | app/product/native_coach_composition.py、app/runtime/runtime.py、review_sender.py | 原native/角色/范围/边界显式构造器已有，不改变默认Worker；不是当前1.5.6消费 |
| 必要编辑→新稿fresh→发布拒绝/允许 | app/evaluation/review_bound_editor.py、tests/test_review_bound_coach_application.py | 实际Agent/tools调用路径配脚本化响应；坏锚点、真错/fresh拒绝不发布，恢复消耗槽后不发第六次；不证明模型检错 |
| 同一Evidence快照→成稿/manifest/receipt→读取 | app/product/native_coach_composition.py、recent_review_service.py、run_receipts.py | 原native覆盖摘要绑定、过期外源保留缺口、发布/拒绝及读取一致；不当新组合外源质量证据 |
| task→executor→Worker→终态/journal | app/tasks/recent_review_executor.py、app/workers/review_worker.py、composition.py | 原native应用测试含任务身份/终态读取；可靠Worker测试覆盖恢复路径，仓库/运行依赖替身，不是本次真实Postgres事务 |
| 默认生产构造与候选资格 | app/workers/composition.py、scripts/run_native_coach_product.py | 默认构造使用既有RuntimeCompositionRoot/单ProviderRegistry，不调用上述新组合构造器；真实native消费入口仍在prepare/密钥前拒绝缺语义资格 |
| 文档1.5.6组合 | app/runtime/coach_contract.py、document_review_provider_factory.py、app/evaluation/document_review_qualification.py | 有显式unadmitted_opt_in合同/诊断factory/资格入口。全app引用核未见产品应用构造器接入它；这是未完成接线范围，不是已运行路径的故障 |

不因已有opt-in构造器或替身发布就授予产品准入。当前1.5.6的资格、自然生成/知识工具、
当前review/editor/fresh与出版同对象绑定、真实Worker/DB/API/UI/journal尚未由本包证明。
正式质量资格通过后才能安排真实消费；届时复用现有请求/compiler/共享预算/Evidence/事务
路径，逐项核当前身份，不能套用原native测试结论或直接改默认Worker。

## 相称验证与决定

实际运行以下已有离线测试，未新建镜像测试或合成业务意见：

- test_native_coach_application、test_review_bound_coach_application、
  test_recent_review_application_service、test_worker_composition：58 passed，14.04秒。
- test_reliable_review_worker：11 passed，2.56秒；用于补先前四文件未覆盖的lease/恢复终态疑点。

测试默认使用tmp目录/替身，不读取本机历史run。本次没有发现需要修复的接线缺陷，
没有必要提前添加另一个未准入应用构造器，更不能把它称为共同语义修复。
结果选择是保留已有管线；独立工程覆盖继续复用，当前组合接线与真实质量仍分开验收。
本包不改变模型/预算/阶段、生产注册或旧资格；旧2/15与3/15各自保留、新资格0。

## 后续工作卡

工程路径核验已完成，下一产品工作按活动计划的独立部分准备本人Training采用/反馈与
四块消费同对象的验收，先从现有实现追踪身份/版本及失败恢复，明确本地缺陷直接修。
正式15和当前组合自然消费继续依赖共同语义修复及原资格门；不拿训练工程准备抵消此阻断。
前端主树工作、两树整合、Memory、身份运维及八维学习保留，未改变阶段顺序。
