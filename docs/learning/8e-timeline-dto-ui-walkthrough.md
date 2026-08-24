# 8E Timeline DTO/UI 八维 walkthrough

> 本文在实现过程中持续补证；8E 父级 coverage 在整个阶段关闭前仍保持 `planned`。

## 1. 问题与用户价值

聚合胜率只能说明“最近整体怎样”，Timeline 用真实时间戳回答“问题集中在哪个阶段、哪一局发生了什么”。

## 2. 原理与方案比较

采用已发布 Summary 中的离散事件和 phase rail；拒绝伪造连续曲线、请求时重拉 Riot、以及为三类离散
事件引入图表库。完整取舍见 ADR-0065。

## 3. 代码地图

- `app/product/run_query.py`：strict Timeline models、event clock/phase normalization、bounded projection，
  并复用 verified `PLAYER_SUMMARY` 读取链；
- `app/api/live_workbench_models.py`、`app/api/main.py`、`app/api/composition.py`：typed response、latest link、
  owner/terminal/publication gate 与 composition proxy；
- `web/src/api/{wire,decoders,liveWorkbenchApi}.ts`：snake_case wire truth、exact nested decoder 和 same-origin
  client；
- `web/src/workbench/{model,adapters,liveController}.ts`：camelCase view、generation/abort 保护与 terminal content
  原子加载；
- `web/src/components/TimelinePanel.tsx`、`web/src/styles/workbench.css`、`web/src/app/App.tsx`：match selector、
  真实几何 phase rail、事件列表、缺失状态和工作台接线；
- `web/src/fixtures/workbenchFixtures.ts`、`web/tests/support/liveApiServer.mjs`：显式 synthetic fixture 与
  local fake-live 浏览器纵向，不冒充真实 Riot 调用。

## 4. 数据与控制流

owner task → terminal/publication gate → verified run stores → bounded Timeline DTO → exact browser decoder →
generation-guarded controller → match selector/phase rail/event list。

后端先检查 owner 对应 task 是否 terminal、是否有报告和合法 publication；query 再交叉验证 receipt、Trace、
manifest、Artifact identity/hash、input commitment、2 MiB 上限与 Summary schema。只有这条链通过后才读取
match events。浏览器 exact decoder 再次检查 run binding、字段全集、count/truncation、phase/time 和事件排序；
任一漂移都会让整个 terminal content fail closed，而不是显示一半未验证数据。

## 5. 测试与证据

- Backend 首红：API test collection 因不存在 `RunTimelineMatchView` 失败；实现后 query/API focused
  `45 passed`，相邻 API/composition/package `123 passed`；提交前又固定 event≤match-duration 与重复
  match identity 两类 cross-field fail-closed 回归；
- Frontend 首红：latest exact link、缺 `decodeRunTimeline()`、controller 未加载 Timeline 共 3 项失败；
  component 又先因缺 `TimelinePanel` 红灯；提交前又以红灯补足 event≤match-duration decoder；实现后 unit
  `92 passed`；
- Browser：完整 Playwright `25 passed`；1440/1024/390/320 无横向溢出，
  keyboard、reduced-motion、no-remote-I/O 与 axe critical/serious 0；
- Build：typecheck/build 通过，JS gzip `128.51 kB`、CSS gzip `15.27 kB`，仍低于 150 kB JS 硬门；
- Python：完整 `1981 passed, 1 skipped, 1 warning, 127 subtests passed`；唯一 skip 为 Windows symlink；
- 真 PostgreSQL：workflow 同清单 `201 passed`，Alembic head→base→head 与 `alembic check` 无 drift；
- Linux package：isolated Compose schema `1.6`、Memory Context 3、terminal assistant 0、外部调用 0、non-root/
  image exclusion 与资源清理通过；
- 人工查看的 durable 视觉证据：`docs/assets/8e-timeline/timeline-desktop.jpg`、
  `timeline-mobile.jpg`、`timeline-partial.jpg`。partial 图选中缺失比赛，证明缺失没有被画成零事件。

截至本段记录时，以上均是本地证据；独立 implementation/evidence commit 与 exact-SHA 三 job 仍是正式
关闭门。

## 6. 失败、安全与隐私

原始 `timeline_error`、PUUID、玩家私有 identity、Artifact path/body、Prompt、Key 均不进入响应；缺失以
固定 reason code 表达，篡改统一 body-free fail closed。

## 7. 运维与回退

新增 route 是只读投影，无 migration、外部调用或新 runtime dependency；回退可独立移除 route/client/panel，
不影响 Summary、Report、Evidence 和 task lifecycle。

本机真库运行必须同时把用户级 `RIFTCOACH_TEST_DATABASE_URL` 映射给 Alembic 使用的 `DATABASE_URL`：

```powershell
$env:DATABASE_URL = $env:RIFTCOACH_TEST_DATABASE_URL
python -m pytest -q
```

第一次完整回归没有做这层进程环境映射，得到 `1975 passed` 与 4 个 Alembic setup error；映射后当时的
4 项真库 focused 与完整 1979 项均通过。提交前再加入两项 cross-field integrity regression，最终完整计数为
1981。该失败没有被计作产品回归，也没有改测试来绕过真库。

## 8. 面试表述与限制

可表述为“我把可审计的 Riot Timeline 离散事实做成严格、owner-scoped、partial-aware 的产品 DTO，并用
真实几何事件轨和可访问列表呈现”。不能表述为已实现经济/补刀曲线、实时 Riot 查询或因果分析。

本批 Riot、OP.GG、Provider、LLM 调用均为 0；fixture 账号、match 和事件均明确 synthetic。真实持续曲线
仍需先演进 producer/Summary schema 并另设数据、隐私和可视化评审门。
