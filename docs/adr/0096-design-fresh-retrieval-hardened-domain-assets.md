# ADR-0096：为检索加固候选建立全新领域协议与资产

- 状态：Accepted for offline design
- 日期：2026-09-05
- 范围：RQ-237 / Stage 8 / 8E / 8-Advanced candidate-only

## 背景

RQ-235 的 V3 真实领域首案在检索成功但零片段后以 `evidence_required` 停止。RQ-236 已在候选
执行器中加入 `coaching-query-recovery-v1`，并取得本地与公共 CI 证据。旧 RQ-235 的考卷、Context、
协议和回执必须保持不可变，不能把新行为注入旧身份后重跑。

## 决定

建立全新、离线准入的领域验证资产，显式绑定：

1. 新 Dataset、case/run ID、Input Plan、marker、Prompt/Context Snapshot、预算报告、协议 ID 和回执路径；
2. 候选请求策略与 `retrieval_hardening=True`，验证“原查询优先、单一安全主题最多一次补查”；
3. 至少一个短而明确的教练查询和一个仍应拒绝的混合/注入查询，确保修复提高检索支持而不扩大语义猜测；
4. body-free 诊断只保存主题、尝试/计数、过滤键名、原因枚举及评测计数，不保存查询正文、答案、
   reasoning、工具参数、凭据或自由文本；
5. 与既有 V3 相同的事实、引用、注入、来源和 85 分质量门，以及完整请求预算证明。

新资产先通过 no-I/O 身份交叉校验、聚焦测试、公共 CI 和新鲜 G53-3-L，之后才可在单独授权下进行
真实领域观察。RQ-235、RQ-227、RQ-230 的旧考卷和回执不重跑、不覆盖。

## 边界

这只是候选评测资产设计，不改变默认 Runtime、GLM-5.2 兼容/应急路径、Portal、Account、Workbench、
Auth、路由、生产媒体或 8-Core；候选仍未注册，production_admitted=false。

