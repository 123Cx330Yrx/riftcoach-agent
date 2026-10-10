# 时间600候选的发送链与业务workflow离线接入

## 已交付及限制

本轮接通GLM600/Flash300新时间请求→角色router→共享任务ordinal→create-only回执
factory→父/子进程→实际worker→SDK编码/stream/close/usage→Exchange→业务初评/编辑/fresh。
复用原CoachBudgetedProvider、RoleRoutedProvider、GoldenProcessStreamProvider和编辑业务
校验，不复制发送生命周期、不绕指纹。任务900/5调用/401920tokens/完整来源/high保持。
本轮付费Provider0，无新业务run/资格；execution_ready=false，不能启动新付费批。
模型输出及450秒为明确模拟；没有证明真实GLM完成耗时、语义充分性或自然产品消费。

上一提交b00a9eaf/CI38039283424已确认success。本轮需自身提交CI，不能借用上轮全绿。

## 实现路径与边界

- golden_stream_bridge新增两种显式transport，GLM单次600与schema1.4观测，Flash仍300；
  新旧transport双向校验时间标记，包括GLM被任务剩余截到300以下的情况。旧transport
  不再接受新标记生成请求，旧请求也不能选新transport。标记仅在Host原请求，不发Provider。
- GLM专用能力scope SDK政策630/630/660：仅精确新policy/model可签发，复制对象/其他
  policy不能获得600能力。父进程以actual request.timeout作为更紧的硬截止，含启动、
  读取和清理；worker核started/deadline不超actual请求，stream结束后关闭仍计时，迟到不交付。
- TimedDocumentRouter通过既有dispatch hooks复用角色计数/真实response/新鲜receipt
  校验。factory复用RoleReceiptedStreamProvider的任务共享ordinal/请求/回包/create-only
  reservation与result；直接generation伪称revision在建目录前拒绝。重复run/ordinal不重发。
- TimedDocumentWorkflow继承contrast整链；原Document/BlockKeyed增加默认不变的
  请求摘要/检验/编辑检查接缝。原完整来源、政策、issue解释、source/block、编辑reason、
  保留正确内容及完整fresh校验不改。fresh计划/实际issued/receipt摘要绑定新时间身份，
  通过和有效拒绝都实际走业务状态机，不把工程pass当业务认证。
- _TimedLimits明确记录各role的新transport/单次上限/真实SDK政策，保留base_contract_version，
  不把旧uniform330政策写成新候选发送身份。默认Agent/product注册没有切换。

## 指纹与历史证据

共享源码变化要求旧当前manifest同步：5个runtime profile的component SHA及program SHA
已显式更新。native/role/coarse/correction/boundary旧入口必须自身重算并验证，未禁用
resolver或删除任何指纹字段。旧版本成功不升级为本轮业务资格；新组合仍未准入。

原时间裁决及旧seal不改。两个变化的历史源码按LF归档到
docs/archive/2026-10-10-timing-decision，摘要与旧裁决逐项核同；archive不执行。
audit现场运行既有预算反例与旧300拒绝，只对过去源码身份读取固定归档；原裁决JSON
固定原字节SHA，归档/历史内容篡改拒绝。其余未变源码仍现场重算，未静默绕指纹漂移。

## 验证及发现

新时间transport12项检查：真实子进程worker/SDK编码/五调用初评-编辑-fresh通过与拒绝、
450秒模拟complete、close触600单次截止、父进程kill/reap、实际factory未知/坏回执/
错模型、重复ordinal、角色错配与旧Flashtransport拒新标记。子进程禁止网络连接，
使用公开夹具，凭据仅OFFLINE_FIXTURE，所有目录由pytest临时路径创建。

12项发送链加先前25项完整请求/预算与4标量共41项通过；104项公开时间裁决/document/editor/
contrast/旧stream-capacity回归通过；113项旧factory/预算/自然native-role应用与文档
diagnostic/Flash配对检查通过。后续factory角色门补丁重跑相关51项通过，不叠加计数。
旧full15候选/runner/evidence与coarse/correction/boundary合同63项通过（544.13秒）；
最后factory构造默认值调整后4项实际factory相关检查通过，不重复累计。

真实执行发现IPC解码会把整数timeout规范为浮点600.0；回执应绑定原发送字节而非
子进程重新序列化，实际代码用前者。测试修正比较方式，没有改原回执或将不匹配放过。
先前manifest漂移及总摘要遗漏在显式当前manifest更新后消除，未重复回退候选机制。
编译/公开旧裁决原字节重建/治理/diff核验，原seal SHA保持一致。

## 下一动作

当前存在完整离线发送链，但新时间身份还没有进入具体冻结诊断方案、checkpoint/
native导入、严格只读回放与公开seal白名单；不能拿旧认证签新请求，旧批不重开。
下一沿现有runner/handoff/replay接入时间身份和每案900/整批账本，核失败闭锁、
Host等待与恢复不重置Provider活动时间；Worker续租/取消/失去所有权与发布边界另需
当前组合消费检查。准备可审查新方案后才取得具体成本授权，不借旧28/45调用余量。
正式同版本15、新资格、自然消费、8E及原产品下游仍未完成。
