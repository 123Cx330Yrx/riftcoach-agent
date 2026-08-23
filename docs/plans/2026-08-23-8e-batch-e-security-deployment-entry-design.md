# 8E Batch E 安全与部署入口设计

## 目标

为 RiftCoach 从“可审计的 Web 纵向切片”走向“可安全公开运行”冻结身份、威胁模型、部署、
Secret、限流、备份/恢复/擦除、隐私、观测和剩余前端模块的原子施工边界。本文件只冻结设计，
不实现产品代码或读取 Secret。

## 初学者心智模型

登录解决“谁在使用 RiftCoach”；RSO 解决“未来能否证明这个 owner 控制某个 Riot 账号”；
Riot/OP.GG 解决“有哪些事实/Meta 证据”。三者不是一回事。API 先把请求绑定到可信 owner，
再让现有 owner-scoped Repository 读写；Worker 才在后台使用最小 Secret 调外部服务；结果先
经过 Evidence/Harness，再由 Web 展示。浏览器永远不是事实源。

## 现状接缝审计

| 接缝 | 已有证据 | Batch E 要补的设计 |
|---|---|---|
| Actor | local/test 静态 provider，production 无 actor 时 readiness fail-closed | AuthPort、session cookie、OIDC/RSO 分离、owner 映射 |
| Web/API | Vite `/api`、显式 CORS、live/ready、body/SSE 上限 | same-origin production shell、CSP/HTTPS、rate/connection budgets |
| Worker | 预建四地区 Riot clients、Key-last composition、lease/fencing | secret-manager/rotation/revocation、最小权限和审计 |
| Data | PostgreSQL migrations、Evidence snapshots、6B-9 lifecycle | backup/restore/erase marker 一致性与 RPO/RTO drill |
| Observability | body-free task observability、8C events、cursor SSE | request/queue/auth/evidence/backup metrics 和脱敏告警 |
| Frontend | Workbench live integration、reduced-motion、axe、122.01 kB JS gzip | secure production shell 后按五模块顺序继续 |

## 方案裁决

### 身份

比较了浏览器 JWT、第三方 BaaS 直接暴露 token、以及 provider-neutral server session。
采用最后一种：客户端只持 HttpOnly cookie，API 通过 AuthPort 得到 owner；OIDC 是
RiftCoach 登录的外部协议适配，RSO 是独立的 Riot relationship verification 流程。
这样保留同源/CSP、撤销和 owner-scoped 现有服务的控制权，又不在本批锁定供应商。

### 部署

比较了单机 Compose、托管 PostgreSQL + 容器和 Kubernetes。采用单机 Compose + edge/static
artifact 作为第一个作品集部署，托管数据库作为迁移路径，拒绝没有规模 Bad Case 的编排平台。
TLS 由 edge termination 负责；API/Worker/PostgreSQL 不直接公网暴露。

### 生命周期

采用现有 centralized owner lifecycle + append-only deletion marker 扩展到 Artifact/backup。
不建立第二套清理队列或“恢复后人工猜测”流程；restore 必须在 ready 前重放 erase marker。

## 数据/控制流

```text
browser --HTTPS--> edge/static web --same-origin /api--> API
       session cookie                         │
                                              ▼
                                    AuthPort -> ActorContext(owner)
                                              │
                       owner-scoped profile/task/Memory/Evidence APIs
                                              │ queued task
                                              ▼
                                  PostgreSQL control plane
                                              │ claim + lease/fencing
                                              ▼
                         Worker -> Riot/OP.GG/LLM (typed adapters)
                                              │
                             Evidence + Harness publication gate
                                              ▼
                PostgreSQL snapshot + Artifact/Trace + body-free SSE/UI
```

删除/恢复旁路：`owner delete → deletion marker → online DB/artifact purge → encrypted backup
restore → marker replay → readiness`。任何一步失败都记录 allowlisted failure 并保持不可公开。

## 后续原子实施批次（设计冻结，不在本轮执行）

| 批次 | 内容 | 主要红灯/绿灯 | 退出证据 |
|---|---|---|---|
| E1 | AuthPort、session、OIDC/RSO callback、ActorContext | 未登录/过期/CSRF/state/nonce/owner mismatch | auth unit/API/DB/浏览器 session |
| E2 | HTTPS edge、CORS/CSP/安全头、body/connection/SSE 限制与 rate policy | wildcard、CSP violation、超限、SSE 泄漏 | proxy/package/browser/security headers |
| E3 | Secret manager adapter、rotation/revocation、日志脱敏与 readiness | 缺 Secret、旧版本、trace 泄漏 | config/rotation/failure-injection/secret scan |
| E4 | backup/restore/erase 与公开隐私说明 | restore resurrects erased row、partial purge、marker conflict | PostgreSQL/artifact/backup drill + privacy review |
| E5 | edge + web artifact + API/Worker deployment、readiness/observability/capacity | wrong startup order、non-root、no metrics、rollback | Linux package/Compose/restore/metrics/load smoke |
| W1 | secure production shell + `Rift Awakening` | auth state/RSO claim/reduced-motion/mobile | Playwright/axe/screenshots |
| W2 | Timeline DTO + visualisation | missing/partial timeline, fake series | DTO/evidence/e2e/perf |
| W3 | Evidence/Trace drawer deepening | raw trace/hidden reasoning leakage | decoder/a11y/security tests |
| W4 | Training full page + progress history | observed writes/private fields/unsupported trend | typed API/Postgres/e2e |
| W5 | OP.GG breadth + Riot→Data Dragon→patch→Meta→Training→UI golden slice | provenance/freshness/join gap | one bounded external replay + body-free evidence |
| EXIT | 8E review and 8F handoff | any unresolved hard gate | complete coverage, deployment/restore/portfolio evidence |

## 硬门与边界

- 生产浏览器不得保存 owner/PUUID/Key/RSO token/Prompt；所有 API 与 SSE 仍 owner-scoped。
- 生产 CORS 不允许 wildcard；CSP、HSTS（仅 HTTPS 后）、nosniff、Referrer-Policy 和 Permissions-Policy
  必须可在浏览器/代理测试中观察。
- 请求 body、header、响应、SSE、登录/RSO callback 和 rate bucket 都有有限容量；错误只投影 allowlist。
- Secret 不落 DB、Artifact、Trace、日志或 backup；轮换和撤销失败必须 fail closed。
- 备份恢复必须先应用删除 marker；未证明 erase 一致性前不声称完成隐私删除。
- 公开部署不承诺 99.9% SLA；RPO≤24h/RTO≤2h 只是待演练目标。
- 视觉仍遵循 RQ-091/RQ-092：硬门过后主动追求 beautiful/fashion/cool；MotionSites 只是候选池，
  Image2/Photoshop 只在入口素材批次按许可使用，不能改变安全/事实合同。

## 不能说与可以说

可以说：

> 我为 8E 冻结了 provider-neutral AuthPort、RiftCoach owner 与 Riot RSO 的职责分离，
> 以及单机 Compose + edge 的可审计部署边界；删除 marker 会贯穿在线数据、Artifact 和备份恢复，
> 后续按 E1–E5/W1–W5 逐项 TDD 和 exact-SHA 验证。

不能说：已实现正式登录/RSO、HTTPS/CSP/限流、生产备份恢复、公开部署、完整 Timeline、全量 OP.GG
或 8E/8F 已完成。

