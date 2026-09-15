# ADR-0097：建立带查询指引的新候选领域资产

- 状态：Accepted for offline design
- 日期：2026-09-06
- 范围：RQ-239 / Stage 8 / 8E / 8-Advanced candidate-only

## 背景

RQ-238 已把 `coaching-query-guidance-v1` 绑定到候选 Context 接缝，并在三个代表场景完成离线链路；
唯一真实 guided_03 也取回了 3 个来源。但这还不是独立领域证据。旧 RQ-235、RQ-227、RQ-230、RQ-237
考卷都已消费或具有历史结论，不能把新指引注入后重跑。

## 决定

建立 RQ-239 全新、候选专用的领域资产包，包含新的 Dataset、case/run ID、用户问题、marker、
Input Plan、Prompt/Context Snapshot、预算证明、协议和 body-free 回执身份。案例覆盖最近状态复盘、
生存调整、经济/补刀调整，并另设一个不可信资料边界；它们与 RQ-238 代表场景使用不同文字和身份，
不能复用旧 fixture 摘要。

资产必须显式绑定 `coaching-query-guidance-v1`、候选 request policy、`quality_hardening=True`、
`retrieval_hardening=True`、一次修订、来源下限 1 和 85 分事实/引用/注入/评测硬门。预算沿现有
205000/613000 上界重新计算，不降低检索阈值或放宽安全规则。Context 快照必须由候选入口重建并核对，
不接受调用方单独传入的任意长文本作为“指引”。

## 顺序与边界

先完成 no-I/O 资产交叉校验、历史排重、最坏路径预算和聚焦回归；再取得同 SHA 公共 CI 与新鲜 G53-3-L；
最后才在单独授权下执行一次新的真实领域观察。真实失败首错停止，不自动重跑，不覆盖旧回执。
不注册候选、不切换产品默认模型、不改 GLM-5.2 回退、Portal、Account、Workbench、Auth、路由或生产媒体。

