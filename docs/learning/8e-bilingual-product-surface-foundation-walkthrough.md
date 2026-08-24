# 8E 双语产品表面基础八维 walkthrough

> 本文在实现过程中持续补证；8E 父级 coverage 在整个阶段关闭前仍保持 `planned`。

## 1. 问题与原理

目标是让同一 canonical 产品状态在 `zh-CN/en` 下可读，同时不篡改报告、实体数据或 API code。UI locale、
Data Dragon locale 和 Coach content language 是三个合同，不是一个“翻译开关”。

## 2. 设计与取舍

采用 zero-dependency typed catalog + React context；拒绝整页机翻，当前不引入 i18next/react-intl。完整比较见
ADR-0066 与专用设计。

## 3. 代码地图

- `web/src/i18n/locale.ts`：`zh-CN|en`、typed English catalog、complete Chinese catalog、strict V1 storage、fallback；
- `web/src/i18n/ProductLocaleProvider.tsx`：locale state、`document.lang`、`Intl` number/time 和 `t()`；
- `web/src/components/LocaleSwitch.tsx`：Portal、Auth、Account、Workbench 共用的键盘可访问控制；
- `web/src/i18n/productCopy.ts`：canonical status/event/region code 到 catalog key；
- Workbench components：只 render structured model，不把 adapter 拼出的英文句子或 wire code 当 copy；
- `web/src/test/renderWithLocale.tsx`、locale/component/App tests 与 `web/tests/e2e/locale.spec.ts`：两种语言证据。

## 4. 数据与控制流

```text
strict localStorage envelope
  → 若缺失/损坏：navigator.languages
  → 若仍不匹配：English
  → ProductLocaleProvider
      ├─ catalog UI copy
      ├─ Intl number / UTC time
      └─ html[lang]

API/SSE canonical model ────────────────┐
Coach report / Training plan raw bytes ─┴→ 不随 locale 变化
```

切换 locale 只更新 React context 和 versioned storage；不会重取 API、重连 EventSource、改 profile、写 Memory，
也不会机翻已通过 Harness 的 Report/Plan。地区下拉使用带平台范围的长名称，工作台卡片使用短名称；
`MIDDLE`、Training metric key、Evidence gap/error code 等 canonical 值由 allowlisted mapping 投影，未知值使用
bounded generic copy，不回退裸 code。

## 5. 测试与证据

- locale core 覆盖 exact storage、多余字段/版本/异常、navigator、English/key fallback、placeholder 和 document lang；
- component/App 覆盖中英文 status/copy、original Report/Plan bytes、role/metric/gap code 不外泄；
- Playwright 36 场覆盖 Portal/Account/Workbench、reload persistence、键盘/focus、1440/1024/390/320、axe、
  reduced-motion、语言切换不产生 API/SSE 差异；
- production build JS/CSS gzip `142.68/18.50 kB`，JS 低于 150 kB 硬门；CSS/SVG/已有 Motion 外没有第二动画 runtime；
- frontend unit `24 files / 136 passed`、完整 Python `1982 passed, 1 skipped, 1 warning, 127 subtests passed`，
  真 PostgreSQL/Alembic、RAG/Harness、compile/pip/YAML、npm audit、SDK/Secret、governance/diff 与 Linux package
  smoke 全绿。独立 commit/public exact-SHA 仍是关闭门，不能用本地全绿提前关闭。

## 6. 失败、安全与隐私

locale storage 不含身份或内容；corrupt/missing key 安全 fallback；server-authored content 不浏览器机翻。普通产品
表面不显示 fixture/runtime/projection/reason/gap/error code；Evidence 专业视图只保留必要 digest，并用自然语言
说明其作用。未知 role/metric/gap 不泄露原始 identifier。Riot ID 与英雄名保持 source bytes，不做词典猜译。

## 7. 运维与回退

本批无 migration、npm 依赖、API/Memory schema 或产品数据外部调用。可独立回退 locale provider/catalog，
不改变 API、Artifact、Task 或 EventSource；丢失 storage 只回到 navigator/English。运行 `npm run typecheck`、
`npm run test:unit`、`npm run build`、`npm run test:e2e` 可复现浏览器侧门禁。

## 8. 面试表述与限制

可以表述为“把 UI copy、数据 locale 和生成内容语言分层，并用 typed catalog、strict persistence、canonical
code projection 和 a11y/browser 回归实现双语产品表面”。在 exact-SHA 关闭前只能说本地实现通过；即使关闭，
也不能说旧报告已被可靠翻译、LoL 双 locale 资产已接入，或 bounded Coach 对话已经产品化。
