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

## 2026-08-24 本地实施状态

- Steps 1–6 已完成；RQ-104 的独立中英文 copy 审计与 RQ-105/ADR-0067 的 Portal→Account→Workbench 纠偏
  作为同一 atomic implementation 合并验证，避免先把旧错误拓扑翻译两遍。
- RQ-106 又把旧 plate-only Portal 校准为母图分层 V1；运行时 bitmap 无 text/UI/core，semantic DOM 不变。
- Step 7 已完成：frontend unit `24 files / 136 passed`、Playwright `36 passed`、JS/CSS gzip
  `142.68/18.50 kB`；Player Link focused `26 passed, 1 warning`，完整 Python
  `1982 passed, 1 skipped, 1 warning, 127 subtests`；真 PostgreSQL/Alembic、两套 RAG、Harness、
  compile/pip/YAML、npm audit、SDK/Secret、governance/diff 与 Linux package 全绿。
- Step 8 尚未执行。公共 exact-SHA 三 job 前 foundation 保持 open，coverage 保持 planned。
- RQ-107 bounded Coach 是本批后序建议，不在该 implementation 内塞入 Conversation client/chat UI；插入顺序
  等用户裁决。
