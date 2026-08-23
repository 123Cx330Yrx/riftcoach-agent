# 8E Batch E 安全与部署入口设计 walkthrough

> 状态：entry design；本文件不表示 Auth/RSO、HTTPS、备份、部署或剩余 Web 模块已实现。

## 1. 问题与原理

Live Workbench 已能从 owner-scoped API/SSE 读取真实产品投影，但“能读取”不等于“能公开运行”。
当前 production API 没有正式登录，`ActorContext` 仍依赖外部适配器；Compose 也没有 HTTPS、CSP、
备份恢复和限流合同。Batch E 先把安全边界冻结，避免把前端动画或一次 live smoke 当成生产能力。

最容易混淆的三个概念是：

- RiftCoach Auth：证明谁在使用本产品，并产生 owner；
- Riot RSO：未来证明 owner 是否控制某个 Riot 账号；
- Riot/OP.GG：提供事实或 Meta，不提供 RiftCoach 登录，也不自动证明所有权。

因此 `claimed_self` 必须继续显示未验证，`public_observed` 只能生成公开观察语义，只有
Auth + RSO callback + `/accounts/me` PUUID 精确匹配后才允许 `verified_self`。

## 2. 设计与代码地图

本检查点冻结 provider-neutral `AuthPort` + server-side opaque session；浏览器只持
HttpOnly cookie，API 通过 Actor adapter 恢复 owner。首个部署采用 edge/static Web + API +
Worker + PostgreSQL 的单机 Compose，托管数据库保留为迁移路径，Kubernetes/Redis/Celery/Kafka
没有当前 Bad Case，不提前采用。

现有接缝与未来消费者如下：

| 现有位置 | 已有职责 | Batch E 后续消费者 |
|---|---|---|
| `app/api/actor.py` | trusted ActorContext、local/test 静态 provider | Auth session adapter |
| `app/api/composition.py` | profile、CORS、readiness、PostgreSQL lifespan | security settings、session binding |
| `app/workers/composition.py` | Key-last、四地区 Riot client、lease/fencing | Secret source/rotation |
| `app/lifecycle/service.py` | owner export/delete/marker | Artifact/backup erase replay |
| `compose.yaml`/`Dockerfile` | API/Worker/PostgreSQL package | edge、TLS、web artifact、backup drill |
| `web/src/api`/`web/src/workbench` | exact decoder、SSE、identity guard | authenticated production shell |

## 3. 数据与控制流

```text
browser --HTTPS--> edge/static web --same-origin /api--> API
       HttpOnly session                         │
                                                ▼
                                     AuthPort -> ActorContext(owner)
                                                │
                      owner-scoped profile/task/Memory/Evidence APIs
                                                │ queued task + 8C lease
                                                ▼
                          Worker -> typed Riot/OP.GG/LLM adapters
                                                │
                                Evidence + Harness publication gate
                                                ▼
                PostgreSQL snapshots + Artifact/Trace + body-free SSE/UI
```

删除/恢复是另一条必须一致的链：`owner delete → immutable marker → online DB/artifact purge →
encrypted backup restore → marker replay → readiness`。恢复后若删除标记没有重新生效，服务必须
保持 not-ready，不能把被删除数据重新公开。

## 4. 硬门、失败与边界

- 生产 CORS 默认同源，不能使用 wildcard；CSP、HSTS（TLS 成功后）、nosniff、Referrer-Policy、
  Permissions-Policy 必须能在代理/浏览器测试中看到。
- body、header、connection、SSE event/bytes、登录/RSO callback 和单次响应都有上限；超限只返回
  allowlisted error code。
- Secret 不得进入浏览器、DB、Artifact、Trace、日志或 backup；轮换/撤销失败时 readiness fail closed。
- 公共错误不能泄露 PUUID、Riot ID tag、Cookie、Prompt、upstream body、DSN 或异常正文。
- RPO≤24h、RTO≤2h 是待 restore drill 验证的初始目标，不是当前 SLA；没有跨区域 HA 承诺。
- 现有 OP.GG partial provenance、8B Multi-Agent reject、`degraded/unjoined` live replay 和真实
  golden slice 的缺口均保留，不能由本设计追绿。

## 5. 原子施工顺序

E1 Auth/session → E2 edge security/limits → E3 Secret lifecycle → E4 backup/restore/erase →
E5 packaging/observability；随后 W1 secure shell/Rift Awakening、W2 Timeline、W3 Evidence/Trace、
W4 Training、W5 OP.GG breadth + golden slice，最后 8E exit/8F handoff。每项都要独立设计、TDD、
八维证据、本地门、独立提交和 exact-SHA 三 job。

## 6. 验证与运行

本轮只运行治理门，不启动生产服务、不读取 Secret、不调用 Riot/OP.GG/Provider。后续实现批次必须
分别验证 unit/API/PostgreSQL/browser/package/restore/负载，而不是用本地静态配置替代安全证据。

## 7. 面试安全表述

可以说：

> 我先冻结了 Auth 与 Riot RSO 的职责分离、owner 信任边界、单机 Compose + edge 部署拓扑，
> 并把删除 marker 延伸到 Artifact/backup restore；后续按 E1–E5/W1–W5 逐项实现和验收。

不能说：已经实现正式登录/RSO、HTTPS/CSP/限流、备份恢复、公开部署、完整 Timeline/Training、
全量 OP.GG 或 8E/8F 完成。

