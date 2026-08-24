# 8E 双语产品表面基础实施计划

1. 先为 `UiLocale`、strict `LocaleStore`、browser/default resolver、catalog completeness、missing-key fallback 和
   placeholder 写红灯。
2. 实现零依赖 typed catalogs、`ProductLocaleProvider`、`useI18n()` 和可访问 `LocaleSwitch`；先让 Portal、
   Auth 和 App shell 红→绿。
3. 把 client loading/empty/error 从英文 message truth 收敛为有限 code；UI 用 catalog 展示，controller 行为、
   generation/abort/SSE 不变。
4. 逐组件迁移 Workbench 静态 copy：Profile/Event/Product State/Recent Form/Timeline/Coach/Training/Evidence；
   Evidence adapter 改保留 canonical structured values，不在 adapter 拼英文展示句。
5. 对 report/training/source content 加 original-content disclosure；切 UI locale 的测试必须证明 report body bytes、
   run identity、Product State 和 API 调用次数不变。
6. 增加 browser 红灯：中文/英文切换、reload persistence、Portal/Workbench、keyboard、390/320 overflow、
   reduced-motion、axe critical/serious 0 和 remote request 0；再实现布局/text expansion 修补。
7. 运行 frontend 全套、Python 比例回归、RAG/Harness/Alembic/真库/Linux package、security/governance/diff，
   更新八维 walkthrough 和最新 bundle。
8. 创建独立 implementation/evidence commit，push，并等待同一 SHA 的 `pytest`、`postgres-migrations`、
   `packaging-smoke` 全绿；之后才交接 RQ-103 Data Dragon asset/detail enrichment。
