# RQ-237：检索加固候选全新领域资产设计计划

## 目标

为 `coaching-query-recovery-v1` 建立一套与 RQ-235 完全隔离的 V3 领域协议和三案例资产，先完成
离线身份准入与预算证明，再等待后续新鲜协议和真实观察授权。

## 设计任务

1. 新建 Dataset、Input Plan、Prompt/Context Snapshot、匿名 fixture、marker、协议 ID 和 body-free 回执身份。
2. 在请求计划中显式绑定候选 request policy、`quality_hardening=True` 与 `retrieval_hardening=True`。
3. 证明每案/全域调用与 token 上界，保留 V3 最多一次修订及 85 分事实/引用/注入/来源门。
4. 加入可复现的短查询恢复样例、已有命中样例和安全拒绝样例；诊断只使用固定枚举和计数。
5. 通过 no-I/O 资产交叉校验、聚焦回归、compileall、diff check、governance 和同 SHA 公共 CI。

## 后续顺序

资产设计完成后，另立实现批并取得公共 CI；再在新资产身份上取得一次新鲜 G53-3-L。只有协议证据
通过且用户明确授权，才执行一次新的 V3 真实领域观察。任何阶段都不重跑 RQ-235 或覆盖旧回执。

## 限制

本计划不注册候选、不切换产品默认模型、不修改 Portal、Account、Workbench、Auth 或生产准入，
也不发送真实 Provider 请求。

