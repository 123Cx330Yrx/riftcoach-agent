# ADR-0066：采用 typed 双语产品表面并分离内容语言

- 状态：Accepted
- 日期：2026-08-24
- 检查点：`8e-productization / remaining-product-modules / bilingual-product-surface-foundation`

## 背景

当前 Rift Awakening、Auth gate、Workbench、Timeline、Evidence 与 Training 的 UI copy 主要硬编码为英文。
与此同时，项目已有三种不同的语言事实：浏览器界面语言、Data Dragon 实体 locale，以及 Memory 中的
`report_language=zh-CN|en-US`。如果只在浏览器中机翻整页，会把已发布 Coach 报告和证据正文改写成没有
provenance 的新内容；如果把 API enum 翻译掉，又会复制后端状态机并破坏 exact decoder。

## 决策

1. UI locale 只允许 `zh-CN | en`。React 使用仓库内 typed catalog 和 locale context，不新增 i18n runtime
   dependency；英文 catalog 是安全 fallback，中文 catalog 必须在 TypeScript 编译时覆盖同一 key 集。
2. 初始 UI locale 按“合法版本化 localStorage → `navigator.languages` → `en`”解析；切换后只保存
   `{"schema_version":"1.0","locale":...}`，并同步 `document.documentElement.lang`。该存储不包含 owner、
   Riot ID、Token、Cookie、报告或其它隐私数据。
3. `published/degraded/rejected`、reason code、source kind、event kind 等 API/内部 code 保持 canonical 英文；
   组件只把 code 映射为当前 locale 的展示 copy，不修改 wire/model 真值。
4. Coach report、Training title/objective 和其它 server-authored content 保持生成时原文，不做浏览器机翻；UI
   必须明确其为 original generated content。现有 owner `report_language` 仍是未来生成偏好真源：UI `en`
   对应 report preference `en-US`，UI `zh-CN` 对应 `zh-CN`，但切换 UI 不静默写 Memory，也不冒充旧 Artifact
   已绑定 run-scoped language provenance。
5. 英雄、装备、符文等 LoL 实体名称/资产 locale 属 RQ-103 下一原子批：`zh-CN→zh_CN`、`en→en_US`。
   本批只冻结映射和 fallback，不拼未锁版本的 Data Dragon URL，也不把英文实体名做词典机翻。
6. 同一可访问 locale control 覆盖 Portal、Auth 和 Workbench；键盘、focus-visible、320px、reduced-motion、
   text expansion、missing/corrupt storage、missing-key fallback 和 bundle <150 kB 均为阻塞门。
7. `zh-CN` 与 `en` 分别按各自产品语境编辑。catalog 不是逐字翻译表，也不是给用户看的系统说明书；
   `裂谷指挥中心`、`runtime environment`、`fixture`、`projection`、内部 reason/error/gap code 和解释设计意图的
   旁白不得出现在普通产品主表面。地区与状态由 canonical code 映射成自然展示名，wire/model 真值保持不变。

## 比较过的方案

- **浏览器/第三方整页机翻**：实现快，但会改写报告和证据语义，无法给翻译结果 provenance，拒绝。
- **引入 i18next/react-intl**：生态成熟，但当前只有两个静态 locale，新增 runtime/bundle/配置成本没有对应
  收益；未来出现 ICU plural、远程 catalog 或多团队翻译流程时再评估。
- **typed 本地 catalog + React context**：零新依赖、编译时 key 完整、容易测试和回退，采用。

## 后果与边界

本批完成后，当前 UI chrome、状态、导航、帮助与可访问名称可以正式切换中英；canonical data 和原始 Coach
内容不被篡改。它不证明旧报告的实际语言、Data Dragon 双 locale 资产、专业术语翻译审核或全站最终视觉签收；
这些分别需要 run-scoped report provenance、RQ-103 asset/detail enrichment 和 8E final visual QA。
