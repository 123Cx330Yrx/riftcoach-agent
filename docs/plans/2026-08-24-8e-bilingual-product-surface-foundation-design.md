# 8E 双语产品表面基础设计

## 1. 初学者先理解

“网页支持中文和英文”不只是把按钮文字换掉。RiftCoach 同时有三层语言：

1. **UI copy**：导航、按钮、状态说明、aria-label，由前端 catalog 控制；
2. **实体数据**：英雄、装备、符文和版本静态定义，由 Data Dragon version + locale 控制；
3. **Coach 内容**：报告和训练建议，是某次 Agent/Harness 运行产生的 Artifact，语言必须绑定用户偏好并保留
   provenance，不能由浏览器事后机翻。

API code 仍像数据库主键一样保持唯一。例如服务器永远返回 `degraded`，中文 UI 显示“受限”，英文 UI 显示
“Degraded”。这样后端状态机只有一份，展示语言可以有多份。

## 2. 方案与取舍

### 方案 A：整页机翻

最省代码，但会把报告正文改成新的、未评测文本，并可能误翻英雄/装备名。拒绝。

### 方案 B：i18next/react-intl

适合多 locale、ICU plural 和翻译平台；当前两个 locale 会增加依赖、bundle 和第二套运行配置。暂不采用。

### 方案 C：typed catalog + locale context（采用）

英文 catalog 定义 key 类型，中文 catalog 用 `satisfies` 保证完整；Provider 只提供 locale、`t()`、数值/时间
格式化和 `setLocale()`。组件直接 import hook，不通过 barrel，避免扩大 bundle。

## 3. 合同

```text
UiLocale = "zh-CN" | "en"

LocaleStore.read(): UiLocale | undefined
LocaleStore.write(locale): void

ProductLocaleProvider
  ├─ lazy initial state: store → navigator → en
  ├─ document.documentElement.lang
  ├─ versioned localStorage persistence
  └─ t(key, params) + number/time formatting
```

localStorage key 为 `riftcoach.ui-locale.v1`，value 只接受 exact JSON：

```json
{"schema_version":"1.0","locale":"zh-CN"}
```

字段缺失、多余、版本错误、非法 locale、非 JSON 或 storage exception 全部安全回退，不阻塞产品加载。

## 4. Copy 分类

| 类型 | 处理方式 | 例子 |
|---|---|---|
| UI 静态 copy | catalog | “Open evidence” / “打开证据” |
| canonical code | code→catalog key | `published` → “已发布” |
| 数值/时间 | `Intl` + locale | 场数、百分比、UTC 时间 |
| 玩家/Riot ID | 原样 | `Riverline#EUW` |
| 英雄/装备/目标 label | 保留 source locale | 下个 RQ-103 批处理 |
| Coach report/Training content | 原文 + disclosure | 不浏览器机翻 |
| Prompt、Trace body、Secret | 永不进入 UI | 安全边界不变 |

## 5. 组件与数据流

`App` 在任何 surface 选择前建立 Provider，因此 Portal、AuthGate、fixture 和 live 共用同一 locale。`LocaleSwitch`
在 Portal 与 AppFrame 使用同一 state；切换只触发 React copy 重渲染，不重新请求 API、不重连 SSE、不切 profile，
也不改变 Product State。

Workbench adapter 保留 canonical model。现有 adapter 中为 Evidence 拼出的英文展示句将改为结构化数量、版本、
source kind 和 gap code，由 `EvidenceDrawer` 在 render 时翻译；这样切 locale 不需要重取数据。客户端 loading/
empty/error 也改为有限 message code，避免把英文句子当状态真值。

## 6. 错误、安全与边界

- missing key：开发时 TypeScript 阻塞；运行时 English fallback，最终回退为可审计 key，不白屏；
- localStorage unavailable/corrupt：忽略并按 navigator/default 解析；
- report language unknown：显示“保留生成时原文”，不猜中文/英文；
- locale switch：不写 Cookie、URL、Memory、owner、Riot ID 或 server；
- source content：不通过 `innerHTML`，SafeMarkdown 现有转义边界不变。

## 7. 验证

- core unit：locale 解析、strict storage、missing-key、placeholder、document lang、persist；
- component unit：状态/code/copy 中英映射，切换不改变 canonical data/report body；
- browser：Portal 与 Workbench 两 locale、reload persistence、keyboard/focus、390/320 text expansion、axe 0、
  reduced-motion、remote request 0；
- engineering：typecheck、unit、build、Playwright、JS gzip <150 kB、Python/OpenAPI regression、governance/diff；
- exact-SHA：独立提交的 pytest、postgres-migrations、packaging-smoke 三 job 全绿后才关闭 foundation。

## 8. 本批不做

不新增后端 locale enum，不改变 API status/reason code，不写 Memory preference mutation，不给旧 report 猜语言，
不接 Data Dragon 资产、不做 Evidence/Trace 深页、Training full、OP.GG breadth/golden slice 或最终视觉签收。
