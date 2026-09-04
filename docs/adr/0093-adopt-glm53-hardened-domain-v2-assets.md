# ADR-0093：采用 GLM-5.3 Flash 加固领域 V2 新鲜资产

- 状态：Accepted
- 日期：2026-09-04
- 范围：Stage 8 / 8E / 8-Advanced / candidate-only evaluation

## 背景

RQ-227 已经消耗了低思考三案例考卷，并留下不可覆盖的失败回执。RQ-228 修复了两个独立边界：
报告至少需要一个可归因来源，用户或知识数据里的指令性文本不得被执行或原样回显。修复后不能用
同一考卷重考，否则模型、提示与测试之间的污染会让结果失去独立性。

## 方案比较

1. 复用 RQ-227 资产：成本最低，但旧问题和 marker 已暴露，拒绝。
2. 只更换 ID 和文件名：形式上是新版本，语义和数据仍被消耗，拒绝。
3. 新建 V2 协议计划、Dataset、Input Plan、Prompt/Context Snapshot 与合成 fixture，并以
   no-I/O 准入器交叉绑定 RQ-228 加固版本：采用。

## 决策

采用 `glm53-flash-hardened-domain-observation-v2`。离线准入必须同时验证：

- 全新的 case ID、run ID、问题正文、合成数据和 forbidden marker；
- held-out 角色、冻结规则、每案/全域调用与 token 上限、零 SDK retry、零 revision、首个不安全失败即停；
- `glm53-flash-domain-quality-v1`、候选 `low + 4096` 请求策略，以及每案至少一个来源的要求；
- 每个上下文都实际包含可信候选 policy 附录，且 Dataset、Plan、Snapshot 和 fixture 的身份一致；
- 准入阶段 `external_provider_calls=0`，不读取 Key、不构造 Provider、不创建真实结果回执。

## 边界

该决策不注册 GLM-5.3 Flash、不改变产品默认模型、不移除 GLM-5.2 手动兼容/应急路径，也不改
Portal、Account、Workbench、Auth 或路由。离线通过只说明新一轮材料可安全开考，不证明真实领域
质量、黄金切片、生产安全/部署/合规或 8F 完成。真实协议与领域观察仍需后续明确授权。

