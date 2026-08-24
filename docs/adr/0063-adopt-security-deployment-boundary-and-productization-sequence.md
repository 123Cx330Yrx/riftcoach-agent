# ADR-0063：冻结 8E 安全、部署边界与产品化施工顺序

- 状态：Accepted for `8e-batch-e-security-deployment-entry-design`（2026-08-23）
- 范围：8E Batch E 的威胁模型、身份/信任边界、部署拓扑、安全响应合同、Secret 与备份生命周期、隐私/观测门，以及剩余 Web 模块顺序
- 不包含：本 ADR 不实现 Auth/RSO、HTTPS、限流、备份、生产部署或新的前端页面；这些能力必须在后续原子实施批次中逐项 TDD 和 exact-SHA 验证

## 背景

8E 已有 owner-scoped player profile、Evidence snapshot、cursor SSE 和 Live Workbench，
但当前 production profile 没有可信登录，`ActorContext` 仍由外部适配器提供；Compose
只证明单机 API/Worker/PostgreSQL 能启动，尚没有 HTTPS termination、安全响应头、限流、
备份 restore/erase 或公开隐私说明。继续堆前端会把“能展示”误当成“能安全交付”。

本项目还必须保持几个容易混淆的事实：RiftCoach 登录证明的是 RiftCoach owner，不证明
用户拥有某个 Riot 账号；RSO 未来只能通过安全 callback 和 `/accounts/me` 的 PUUID 精确
匹配升级 `claimed_self`；`public_observed` 只允许公开观察语义；OP.GG 是不可信的
partial Meta 来源，不能覆盖 Riot 官方事实或继承 patch/freshness。

## 威胁模型与信任边界

```text
browser (untrusted) ──HTTPS──> edge/static web
                                   │ same-origin /api
                                   ▼
                              API (Actor/Auth boundary)
                              │         │
                    short-lived jobs │         ├── Riot / OP.GG / LLM (untrusted upstream)
                              ▼         │         └── typed adapters + Evidence/Harness gates
                           Worker       ▼
                              └────> PostgreSQL (control/data lifecycle)
                                      └── Artifact/Trace volume
                                      └── encrypted backup (restore must replay erase tombstones)
```

- 浏览器、URL、请求 body、SSE、Riot/OP.GG/MCP 返回值均是不可信输入；不能携带 owner、PUUID、
  Key、lease token、Prompt 或内部 operation identity 来改变服务器事实。
- Edge 负责 TLS、基础 IP 防护和静态 Web；API 是唯一产生 `ActorContext` 的产品边界。
- PostgreSQL 是 task、profile、conversation、Memory、Evidence 和生命周期控制面的真源；
  Artifact/Trace 保持各自事实源，不把正文复制进新的“万能产品表”。
- Worker 只消费已验证 task，拥有最小的 Riot/LLM Secret；外部来源先过 typed adapter、
  provenance/freshness、Harness 和 publication gate。

## 身份决策

采用 provider-neutral `AuthPort` + server-side opaque session 的边界，具体身份供应商留给
实现批次用许可、费用和运维证据选择。浏览器只持 `Secure; HttpOnly; SameSite=Lax` 的短期
session cookie，不持 JWT、Riot API Key 或 RSO access token；API 从 session 解析 owner，
再把 owner 传给现有 owner-scoped service。

RiftCoach Auth 与 Riot RSO 分成两条链：

| 身份 | 证明什么 | 当前/未来能力 |
|---|---|---|
| `owner_authenticated` | 用户登录了 RiftCoach | 访问自己的 owner-scoped 数据 |
| `claimed_self` = `self + unverified_claim` | 用户声明某个外服 Riot ID 是自己的 | 可保存自己的目标/Plan/Progress，但显式未验证 |
| `public_observed` = `observed + public_observed` | 只观察公开账号 | 公开比赛分析和 owner-local 备注，不写被观察者私人 Memory |
| `verified_self` = `self + rso_verified` | 未来 Auth + RSO callback + `/accounts/me` PUUID 精确匹配 | 才能显示已验证本人；不能绕过 Riot 权限 |

RSO 不是登录替代品，也不是“输入 Riot ID 就认证”。RSO callback 必须一次性 state/nonce、
严格 redirect allowlist、token server-side、短生命周期和撤销/解绑记录；失败时保持
`unverified_claim`，不自动跨区、不支持 CN fallback、不把 ShowMaker 设为默认。

## 部署方案比较

| 方案 | 裁决 | 取舍 |
|---|---|---|
| 单机 Compose：edge/static Web、API、Worker、Player-Link Worker、PostgreSQL | 采用为首个公开交付 | 与现有 package/CI 最接近，适合作品集；需要明确 TLS、备份和单节点故障边界 |
| 托管 PostgreSQL + 两个容器服务 + 静态站点 | 保留为迁移路径 | 运维更稳，但增加供应商、网络和费用；在单机门通过前不提前绑定 |
| Kubernetes/Redis/Celery/Kafka 全家桶 | 拒绝当前采用 | 没有新的容量/恢复 Bad Case，不能用基础设施名词替代可靠性证据 |

Web 生产构建作为独立静态 artifact/container 由 edge 提供；API 只在同源 `/api` 下服务，
避免公网 wildcard CORS。API、Worker、PostgreSQL 置于私有网络，只有 edge 暴露 443。第一
个部署不承诺跨区 HA；必须测量并诚实发布 RPO/RTO，而不是写成 99.9% SLA。

## 安全合同

1. **CORS/CSP/响应头**：生产默认同源、CORS 空 allowlist；开发 origin 必须显式列出。CSP
   至少固定 `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
   font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none';
   form-action 'self'`，并启用 `X-Content-Type-Options: nosniff`、严格 Referrer-Policy、
   Permissions-Policy；HTTPS edge 成功后再启用 HSTS。
2. **限流与容量**：edge 对登录、RSO callback、player link、review create 和 SSE 建立 IP
   粗限流；API 对 owner 建立任务/Link/并发 SSE 上限。请求体、header、连接空闲时间、SSE
   事件数/字节数和单次响应均有硬上限；超限返回 allowlisted body-free code。单进程内存
   limiter 不是多副本一致性方案，若扩容成为真实需求必须再引入共享限流存储和 ADR。
3. **Secret**：开发可用 `.env`，生产只允许 secret-manager adapter 或受限环境注入；
   读取时不打印、不进入 traceback/Artifact/Trace/DB/backup；按 `secret_version` 记录
   脱敏审计，支持双 Key overlap、轮换、撤销和 restart/readiness 失败关闭。Riot/LLM/RSO
   Secret 绝不进入浏览器。
4. **错误与观测**：公开错误只有稳定 code、request id 和必要状态；结构化日志只允许
   route/status/latency/owner hash、task/run digest 和 failure code，不记录 Riot ID tag、
   PUUID、Cookie、Prompt、原始 upstream body 或 Token。健康检查分 live/readiness；指标
   至少覆盖请求 RED、队列/lease、SSE、Evidence freshness、backup/restore 和 auth failures。

## 数据生命周期、备份与隐私

PostgreSQL、Artifact/Trace volume 和 backup 是同一 owner 生命周期的三个落点。导出/删除
必须先写不可覆盖 deletion marker，再清理在线数据；backup restore 后必须先重放 marker，
否则恢复出的已删除数据不能重新对外提供。restore drill 必须验证 owner、conversation、
Evidence、Memory、Plan/Progress 和 Artifact 的 FK/隐藏语义；失败时保持服务 not-ready。

首个部署采用“可测量目标、不可夸大”的运维合同：先以 RPO ≤24h、RTO ≤2h 作为 restore
drill 目标，只有演练得到的 p50/p95 和成功率才写入 8E/8F 证据；没有跨区域灾备承诺。
公开隐私说明必须写清：收集哪些 Riot ID/公开比赛/Meta/训练数据，Riot ID 不等于所有权，
observed 与 self 的差异，OP.GG partial provenance，LLM 发送边界，保留期限，导出/删除
语义，backup erase 延迟和支持联系方式。

## 剩余前端与产品化顺序

安全/部署 core 先行，之后保持 `Cinematic Portal → Account Access → Broadcast Workbench`。以下编号首先记录
施工顺序；用户可见拓扑已由 ADR-0067/RQ-105 澄清，不能再把 AuthGate 或 Riot ID 表单叫作 Portal：

1. **Production shell/Auth gate**：同源静态 Web、登录态、未登录/加载/拒绝状态；不把 RSO 当登录捷径。
2. **Rift Awakening + Account Access**：Portal 是核心激活前零 API/SSE 的电影开屏；激活后才进入独立 Account 层启动 provider-neutral session、已有档案与 Player Link。Image2/Photoshop 只提供无文字/无 UI 的可替换氛围层，所有身份、信息与状态仍由真实 DOM/typed contract 驱动。
3. **Rift Timeline**：先冻结 owner-scoped Timeline DTO，再用 SVG/ECharts；没有 DTO 不画假曲线。
4. **Evidence/Agent Trace**：深化现有 Drawer，展示 allowlisted event/claim/freshness/decision；不暴露 raw trace 或隐藏推理。
5. **Training Plan/Progress**：把当前薄摘要扩成真实计划、metric history、纠错和趋势；observed 继续只读。
6. **OP.GG useful-breadth + golden slice**：至少评估 champion analysis、lane matchup；synergies 只有真实阵容消费者需要时才加入。完成 Riot match + Data Dragon + official patch + OP.GG → training advice → UI evidence 的一次 body-free golden slice。
7. **8E exit / 8F handoff**：补充评测、截图、部署/备份证据和广泛 README/作品集研究。

RQ-107 又指出静态 Coach report 不是最终 Agent 产品交互。是否在 RQ-103 前插入 review-grounded bounded Coach
原子项仍待用户裁决；裁决前本 ADR 不静默改写上述后序顺序，也不把现有 Report 锚点冒充可追问 Agent。

这不是把五模块缩成普通 Dashboard：Batch D/Live Workbench 是工作台纵切，Rift Awakening 与
受限 Void Holographic Lab 仍保留各自职责；任何新动画仍须通过许可、键盘、reduced-motion、
移动和性能双层采用门。

## 非目标与进入条件

- 本 checkpoint 不实现 JWT/OIDC/RSO、Web server TLS、Redis/Kubernetes、备份脚本、限流 middleware、
  电影感入口、Timeline DTO 或真实外部刷新。
- 只有 ADR/design/plan、八维教学证据、治理、本地比例门、独立提交和 exact-SHA 三 job 公共 CI
  全绿后，才把 Batch E 实施交为下一 `prepared` 检查点。
- 8E coverage 继续 `planned`；Batch E 完成后仍不能直接关闭 8E，必须逐批完成 implementation、
  restore drill、生产/浏览器门和完整 golden slice。
