# 8E Portal → Account → Workbench 纠偏设计与实施计划

## 1. 问题与原则

现有实现让默认入口直接申请 session，并把账号表单与电影开屏混在一起；预览还会跳进 fixture。
本批应用“互斥产品层 + 最晚启动 I/O”原则：品牌层只负责进入仪式，账号层负责会话与 owner-scoped 玩家档案，
工作台层才负责 live review controller/SSE。任何视觉状态都不能制造认证、绑定或发布事实。

## 2. 控制流

```text
/?                       Portal（零 API/SSE）
  └─ 激活中央核心        pushState(?stage=account)
       └─ issue session  Account Auth states
            └─ GET profiles
                 ├─ 选择已有 profile
                 └─ POST player-links + bounded GET poll + refresh profiles
                       └─ 明确继续
                            pushState(?stage=workbench&player_profile_id=...)
                                 └─ create/start LiveWorkbenchController once
```

`popstate` 重新解析 URL；每次只挂载一层。离开 Workbench 会 dispose controller，离开 Account 会 abort profile/link
请求。刷新 Account 重新校验 session；刷新 Workbench 重新校验 session，并拒绝不属于当前 owner 的 profile ID。

## 3. 组件与合同

- `AwakeningScene`：只呈现全屏品牌开场和一个语义 core button；视觉预览可显示明确的 Demo handoff，但不含表单。
- `ProductJourney`：解析/写入 `portal|account|workbench`，处理 history 与焦点交接；fixture/preview 在它之外。
- `AccountAccess`：承载 `AuthGate`、locale control、已有 profile 选择和新增玩家表单；不声称 Riot RSO 登录。
- `PlayerLinkHttpApi`：strict request/response、同源 URL、16 KiB error body、2 MiB JSON body、内存 CSRF、每次提交
  新 idempotency key。
- `AccountAccessController` 或等价 hook：generation/AbortController、有界轮询、terminal state、profiles refresh；
  不重试不可重试失败，不把原始 response/error body带入 UI。
- `LiveWorkbenchController`：接受明确 initial profile ID；若 owner-scoped profiles 中不存在则 fail closed，不回退第一项。

## 4. TDD 顺序

1. journey parser/history 与默认零 I/O 红灯；Portal core click/Enter/Space/focus 红灯；
2. Player Link wire/decoder/HTTP 的 exact schema、CSRF/idempotency/error/abort 红灯；
3. Account profiles/选择/新增、pending→succeeded/failed/timeout 与 profile refresh 红灯；
4. 实现 journey、Portal、Account 和 controller profile fail-closed；
5. 更新既有 Auth/live/locale/awakening E2E，并新增完整 production journey、reload/back/forward 与 fixture 隔离；
6. 独立编辑 `zh-CN`/`en`，加入地区映射，删除用户表面的内部 code 与 AI 说明腔；
7. 运行 unit/typecheck/build/完整 Playwright、1440/1024/390/320 截图、axe、键盘/focus/reduced-motion、
   bundle 与仓库比例门；同步八维证据后再提交和等待 exact-SHA 三 job。

## 5. 明确不做

不在本批引入 React Router、Three/GSAP/第二动画栈、真实 OIDC/RSO provider、CN routing、自动跨区重试、
Data Dragon 资产、Evidence/Trace 深页、Training full、OP.GG breadth/golden slice 或 8F。Portal 与账号页仍需在
RQ-103 和 8E final visual QA 中继续细节/资产签收。

## 6. 本地实施结果

- Steps 1–6 已完成：strict journey URL、semantic core、Account/Auth、Player Link exact client/controller、
  live profile fail-closed、history/reload、session cleanup、双语 copy 与 fixture/preview 隔离均有 TDD。
- fake server 和 `product-journey.spec.ts` 证明 core 前 API=0、真实 Link queued→running→succeeded→profile
  refresh、Portal→Account→live Workbench、back/forward/reload 和 unlisted profile 拒绝；完整 Playwright 36 绿。
- 后端 `test_player_link_api.py` 增加 session owner→CSRF Link→terminal→profiles 纵向，文件 26 绿。
- RQ-106 的 background/keyframe 和 bounded handoff 只增强 presentation，不改变本计划的身份/网络控制流；
  现有 Portal/Account 继续属于 V1 而非 final visual sign-off。
- 当前只待完整比例门、八维数字、独立 commit/push 和 exact-SHA 三 job；正式 OIDC/RSO 与 RQ-107 Coach
  interaction 仍未实现。
