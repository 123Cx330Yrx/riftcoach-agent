# 知识工具声明与实际执行对齐

## 已定位的问题与本次裁决

恢复402中断后，先核对工作树、无活动Provider及三父封存，再推送7d52fd64。
同提交公共CI为36306595419；原九例计划尚未启动。等待检查时沿自然Coach下游
追踪，发现1.5.4的manifest声明knowledge.search@2.1.0，输出必含retrieved_at，
实际RuntimeExecutionFactory却只为native、role、coarse三个实例启用该能力，
漏掉继承同一合同的新correction-scope，实际构造2.0.0。

这是可复现的接线错误，不是模型推断、Provider网络或本次402造成的错误。
实际本地工厂探针及回归：四个当前合同和无合同旧入口中，只有correction-scope
在修前失败。旧资料解析允许缺少时间是历史兼容，不能替代当前声明的工具合同。

原九例不经过自然工具入口，但修复会刷新组合manifest身份。只改源码不刷新
manifest会报component fingerprint drift；刷新后旧续接报
role_continuation_candidate_changed，旧资格前缀报plan_identity_mismatch。
原十五份审查请求字节不变，并不等于现有规则允许跨manifest迁资格。
因此停止尚未启动的九例，先修对齐；不先付费跑一份已知不能进入修后资格的组合。
旧计划、旧三例及全部失败原件不改，也不通过变更验收标准转移资格。

## 修复及证据

- RuntimeExecutionFactory按NativeCoachExecutionContract继承家族启用检索时间，
  替换容易漏项的逐实例枚举。require_coach_contract仍只接受已注册合同；
  无合同旧入口保持2.0.0。
- 四份当前manifest仅更新实际runtime组件指纹和整体摘要；模型、high、审查/
  编辑提示、来源表示、合同snapshot、共享产品预算和默认产品开关均不变。
  correction-scope manifest补齐LF规则，确保Windows和公共检查读取同一原始摘要。
- 新回归核实际注册工具的完整schema/策略摘要与manifest一致，再真正执行本地
  检索，验证host UTC时间进入knowledge projection及各引用，文档updated_at独立。
  修前1 failed/4 passed；修后完整检索时间文件17 passed，2.01秒。
- 独立审查验证四份manifest可通过真实RuntimeCompositionRoot；原15请求逐字不变。
  三父239份原件再次核验摘要不变。未发送新Provider请求。
- 主任务实际应用生成/工具/审查/编辑/fresh、严格资格及组合工厂相关回归
  66 passed，166.65秒；与知识时间文件17项合计83项。新提交公共检查结果记录在
  当前执行状态，不把替身检查算真实质量通过。

新增prepare_fresh是现有完整十五例准备逻辑的纯函数入口：只产生当前计划和请求，
不创建run、不发请求、不读取密钥；原run入口仍拒绝已关闭批。它避免为本次变化
再造一个硬编码after-*执行器。原始计划和修后提案均使用同一执行/交接/严格审计底座。

## 身份、费用及下一动作

旧manifest：24a876ae985244f552a663147720fa0435bc49b53e1c41b857ff2f2aad6c4201。
新manifest：6be60527f7a8f015737d5afb5a4d67c6151f844affa2be387e283373b93fdebf。
旧身份严格3/15保留为历史；新身份真实资格为0/15，8E未完成。
旧九例准备443c220a…2d28及campaign-v1保持原样、未启动，不能再作为当前动作执行。

修后完整十五例已生成具体准备和预算提案：

- `data/evaluation/results/golden_correction_scope_runtime_alignment_preparation_v1.json`
  canonical SHA 7a797831d4e029846bbe2773b85705237e16e293c5e4c5dbc443fe2adc9f322e。
- `data/evaluation/results/golden_correction_scope_runtime_alignment_proposal_v1.json`
  明确execution_authorized=false；同HEAD公共检查与新增预算确认前不得启动。
- 采用已修工作稿/显式最终提交，原300/900秒时钟、首错停批、无重试/重评及
  完整双审不变。旧意见或旧成功均不注入新请求或迁为新资格。

历史已用12 calls/169342 tokens/2799.094秒，unknown=0；未缓存估价1.6393516元，
不是账单。新完整批最坏35 calls/3386880 tokens/10500秒，保守全GLM未缓存预留
50.03264元，非硬账单上限。合计最坏47/3556222/13299.094，相对原35/3386880/10500
需新增12 calls/169342 tokens/2799.094秒授权；不得用换身份重置累计费用。

## 后续产品依赖

自然开发入口`run_role_coach_development --profile correction-scope`已经存在，
复用生成、知识工具、一次修订、fresh审查、共享预算、Trace及文件发布；已有证据主要
为网络替身。其代码本身只验冻结计划与同HEAD公共CI；先原15再自然实测的顺序来自
ADR0113，不能称为代码自动解锁。正式`run_native_coach_product`仍禁止execute，
Worker尚未选择correction-scope组合。通用Evidence事务、Worker、API与UI可复用，
公共PostgreSQLfixture通过不证明本机Docker或当前新组合实际消费。

完整原15之后仍需自然请求/工具/真实纠错、当前组合存储/Worker/API/界面证据。
四块联动、个人Training、前端审美及头像、Memory、身份运维、两树整合和学习继续
按原路线；这些工作不因固定报告验证通过而自动完成。
