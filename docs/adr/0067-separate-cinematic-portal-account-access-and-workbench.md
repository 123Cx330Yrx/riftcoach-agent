# ADR-0067：分离电影开屏、账号访问与复盘工作台

- 状态：Accepted
- 日期：2026-08-24
- 检查点：`8e-productization / remaining-product-modules / bilingual-product-surface-foundation`

## 背景

ADR-0064 把 Riot ID 校准表单放进了 `Rift Awakening`，后续实现又让默认 `/` 直接进入
`AuthGate → Workbench`，只有 `?surface=awakening` 才能看到视觉预览。预览成功还会跳到
`?scenario=published`，等于绕过认证并把 fixture 当作真实 handoff。中央海克斯核心本身只是
`aria-hidden` 装饰。这与用户确认的产品叙事相反：母图应是可进入的全屏动态开场，账号页是第二幕，
工作台是第三幕。

## 决策

1. 产品采用三个互斥视觉层级：`portal → account → workbench`。Auth 检查和 Player Link 是 account 层的
   内部状态，不再成为 Portal，也不与 Portal 同屏。
2. 默认 `/` 只渲染 Portal，不构造 Auth client、Player Link client、Live controller 或 EventSource。
   点击或用 Enter/Space 激活中央核心后，才通过 history 进入 `?stage=account` 并启动 session。
3. `?stage=account` 在 session 成功后读取 owner-scoped `GET /player-profiles`。用户可选择已有档案，也可用
   Riot ID、routing region 和 `self|observed` 调用现有 `POST /player-links`；写请求携带内存 CSRF 与新的
   `Idempotency-Key`，随后只对返回的 owner-scoped link URL 做有界、可取消轮询。
4. link 成功后刷新 profiles，以返回的 `relationship_id` 作为 `player_profile_id`。只有用户明确选择档案并
   继续，才进入 `?stage=workbench&player_profile_id=...` 并构造 live controller。
5. history、刷新和深链保持同一合法层级。非法 stage 安全回到 Portal；workbench 深链仍须重新通过 session，
   且 profile ID 必须出现在 owner-scoped profile 列表中，不能静默换成第一项。
6. `?surface=awakening` 是零 I/O 的视觉预览，handoff 只能明确进入 Demo；`?scenario=...` 是显式 fixture。
   两者不共享 production journey 状态，也不能证明真实 Auth、Player Link 或 live Workbench。
7. 当前 `/api/auth/session` 是 provider-neutral session bootstrap，不等于 Riot 登录。`self` 只产生
   `unverified_claim`；只有未来安全 RSO callback 与 `/accounts/me` PUUID 精确匹配才能升级为
   `rso_verified`。

## 方案比较

- **保持默认 AuthGate、把 Portal 当宣传预览**：代码改动最少，但违背已确认叙事并继续绕过入口，拒绝。
- **Portal 内展开账号表单**：交互简单，却继续混淆品牌开场和账号任务，移动端与焦点管理也更差，拒绝。
- **三个互斥层级 + query/history 编排（采用）**：无需引入路由依赖或服务器 rewrite，刷新/前进后退可测，
  同时让每层 I/O 生命周期清晰。

## 后果与边界

正向结果是默认入口、账号选择和真实工作台拥有清晰控制流；Portal 可以承担高视觉预算，账号页专注表单与
错误恢复，工作台保持高信息密度。代价是新增 journey/history、Player Link decoder/client、账号状态组件和
跨层 E2E。RQ-103 的 Data Dragon 英雄/装备/目标资产和 8E final visual QA 仍是后序原子批，本 ADR 不把当前
Portal 或账号页宣称为最终作品集签收。

## 验收

- 默认 Portal 在核心激活前 API/SSE 调用为 0；核心有可见 focus 并支持鼠标、Enter、Space；
- Account 层覆盖 session checking/signed-out/expired/unavailable，以及 profiles loading/empty/error/ready；
- Player Link 覆盖 exact decoder、CSRF、幂等、queued/running/succeeded/failed、超时/abort 和刷新 profiles；
- 选定档案后才启动一次 live controller，离开/认证失效时销毁，不残留旧数据或 EventSource；
- Portal、Account、Workbench 三层的 reload/back/forward、双语、320/390/1024/1440、axe、键盘、focus、
  reduced-motion 和无横向溢出均有证据。
