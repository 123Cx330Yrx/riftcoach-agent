# ADR-0065：采用已验证的事件/阶段 Timeline 投影

- 状态：Accepted
- 日期：2026-08-24
- 检查点：`8e-productization / remaining-product-modules / timeline-dto-ui`

## 背景

`recent-form-review` 的 `PLAYER_SUMMARY` 已持久化对局时长、死亡时间、装备购买和全局目标事件，
但没有持久化 `analyze_match_timeline()` 曾计算的 Gold/CS/XP/level 连续序列。产品层若直接绘制
这些曲线，只能依赖 fixture 或重新调用上游，既破坏已发布 Artifact 的可追溯性，也会把不存在的
数据画成事实。

## 决策

1. 新增 owner-scoped `GET /runs/{run_id}/timeline`，复用既有 task terminal/publication gate 与
   `RunQueryService._read_verified_player_summary()` 的 receipt、Runtime Trace、manifest、Artifact、
   input commitment、byte budget 和 Summary schema 校验。
2. API 只投影真实事件：death、item purchase、elite objective，并按 `0–15`、`15–25`、`25+`
   计算阶段。连续 Gold/CS/XP 曲线不在本批出现。
3. 整体和单场分别表达 `available | partial | unavailable`；缺失不是零。原始 `timeline_error` 可能含
   本地异常正文，永不出现在公共 DTO，只映射为固定安全原因码。
4. 输出按 match/event 数量设置上限并显式报告 total/projected/truncated，不静默假装完整。
5. React 沿用 same-origin exact decoder、generation/AbortController 与单一 controller 状态；不建立第二套
   fetch/store。UI 使用小型 semantic SVG/CSS-free event rail（HTML 轨道与真实数据几何），并提供始终
   可见的时间顺序列表作为键盘、屏幕阅读器和窄屏 fallback。
6. 视觉读法为 `Esports coaching intelligence · tactical editorial + restrained Hextech`；机械纹理仅是
   低对比底层秩序。动效只解释 match/event 选择，`prefers-reduced-motion` 下直接到终态。

## 比较过的方案

- **绘制 Gold/CS/XP 曲线**：当前 Artifact 没有这些序列，拒绝；未来必须先演进 Summary schema 和
  producer，再单独评审。
- **请求时重新调用 Riot Timeline**：会让已发布报告与 UI 使用不同事实快照，也引入网络、Key、费用和
  失败语义，拒绝。
- **引入 ECharts**：当前只有少量离散事件，增加 bundle 和交互面没有相称收益，暂不采用。
- **只用 Evidence 的 `timeline_available`**：只能说明有无，不能呈现真实事件，信息不足。

## 后果与边界

该切片能回答“哪一局、哪个阶段、发生了什么”，不能回答连续经济差、补刀差、经验差或事件因果。
Timeline 仍是 Riot 官方比赛事实的受限投影，不是隐藏推理，也不是 OP.GG meta 结论。
