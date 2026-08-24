# 8E 双语产品表面基础八维 walkthrough

> 本文在实现过程中持续补证；8E 父级 coverage 在整个阶段关闭前仍保持 `planned`。

## 1. 问题与原理

目标是让同一 canonical 产品状态在 `zh-CN/en` 下可读，同时不篡改报告、实体数据或 API code。UI locale、
Data Dragon locale 和 Coach content language 是三个合同，不是一个“翻译开关”。

## 2. 设计与取舍

采用 zero-dependency typed catalog + React context；拒绝整页机翻，当前不引入 i18next/react-intl。完整比较见
ADR-0066 与专用设计。

## 3. 代码地图

实施后补：locale contract/store/catalog/provider、LocaleSwitch、各产品组件、fixture/live tests。

## 4. 数据与控制流

实施后补：storage/navigator → locale state → catalog render；API/model/report bytes 保持不变。

## 5. 测试与证据

实施后补：red→green、unit/browser/build/bundle、Python/真库/Linux 与 exact-SHA CI。

## 6. 失败、安全与隐私

locale storage 不含身份或内容；corrupt/missing key 安全 fallback；server-authored content 不浏览器机翻。

## 7. 运维与回退

本批无 migration、外部服务或新依赖；可独立回退 locale provider/catalog，不改变 API 和 Artifact。

## 8. 面试表述与限制

可以表述为“把 UI copy、数据 locale 和生成内容语言分层，并用 typed catalog/持久化/a11y 回归实现双语产品
表面”。在实现和 exact-SHA 关闭前，不能说双语已完成；即使完成，也不能说旧报告已被可靠翻译或 LoL 双 locale
资产已接入。
