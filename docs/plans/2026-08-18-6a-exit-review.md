# 6A Packaging & Exit Review

## 结论先行

当前本地裁决是 `ready-for-public-verification`，不是 6A 已关闭。6A-1 至 6A-6 的公共证据仍然
有效；6A-7 已补齐真实 Worker executable composition、非 root 镜像、Compose 依赖和 no-I/O Linux smoke，
本轮完整本地门已经成功；只有 exact-SHA Actions 也成功后，才允许将 exit matrix 的待定项改为通过。

## 这一步实际解决了什么

此前 API 能可靠写入 queued task，Worker 控制循环也能 claim，但 `run_review_worker.py` 固定安全退出，
仓库没有一套能把数据库、Riot/Data Dragon、RAG、Prompt Program、Provider、Application、Runtime、
Harness 和 Artifact 组装起来的进程入口。现在的数据/控制流是：

```text
配置完整解析（无 I/O，含 worker_id/Riot/Provider 配置合同）
→ PostgreSQL + Alembic readiness
→ Data Dragon / RAG / Skill / Prompt drift / Provider 构造合同 preflight
→ 返回可 polling Worker
→ claim 之后才处理真实玩家任务
```

构造阶段任何异常都会销毁 Engine，并只返回 allowlisted code；不会先 claim 再发现缺 Key。
该预检不会额外付费调用模型，也不冒充 Riot/Provider 凭据或领域质量已经在线验证。

## Linux smoke 为什么故意得到 failed task

smoke 的目标是证明镜像和控制面能在干净 Linux 中协作，而不是重新伪造一套 Coach。它使用：

```text
HTTP POST 202
→ PostgreSQL queued
→ 独立 no-I/O Worker claim
→ 受控 executor failure
→ failed/worker_execution_failed
→ HTTP task query 200
```

这样真实覆盖 package、migration、API、DB、claim 和终态写回，Riot/Provider 调用严格为 0。成功的
Application/Runtime/Harness/Artifact 链已经由 6A-4 的 PostgreSQL 离线纵向测试证明；两项证据组合后
才覆盖完整架构，任何一项都不能单独冒充真实模型报告质量。

## 当前本地证据

- packaging/Worker/API 聚焦：`46 passed, 1 warning`；
- 完整回归：`1100 passed, 27 skipped, 1 warning, 110 subtests passed`；本机无 PostgreSQL 的 27 个
  skip 必须由阻塞真库 CI 补齐；
- RAG development/independent holdout 均为 Recall/MRR/nDCG 1.0，holdout abstention/citation 1.0；
- Harness dry-run 为 `published`、0 revisions；compileall、Compose/workflow YAML 解析与
  `git diff --check` 已通过；
- Docker/Compose 运行：本机没有 Docker CLI，未本地执行，必须由 GitHub Actions Linux job 补齐；
- 真实 Riot/Provider/Key 调用：0。

人工收尾审查还修正了两个 package-only 风险：无效 `worker_id` 现在会在 Engine/网络构造前拒绝；
smoke 改用独立 Compose project/data volumes，并把 API stack 的 `up --wait` 与 one-off smoke 分开，
避免一次性 migration 的正常退出触发整组提前中止，也避免诊断 Worker 接触普通本地 queued task；
API 与数据库目标还被限制为 Compose/本机 host，test profile 不能伪装成远端诊断授权。

## 当前限制

- Session/Memory 尚未实现，当前不是长期个性化 Coach；
- 正式 Auth/HTTPS、限流、安全响应头、备份和公网运维尚未实现；fixed local owner 不能用于公网；
- SSE/前端尚未实现；
- lease/heartbeat/reclaim、自动 retry、cancel/resume 与 fencing 尚未实现；
- 真实 Provider 的领域质量仍未准入，smoke 和 Fake/no-I/O 证据不能改变该结论；
- 不包含 MCP、Multi-Agent、LangGraph 或新 Agent SDK。

## 面试时可以怎样准确描述

可以说：RiftCoach 用 PostgreSQL 同时承担 durable task queue 和生命周期事实源，API/Worker 分进程但共享
模块化单体代码；Worker 用 `SKIP LOCKED` 原子 claim，Agent 在事务外运行，终态用 ownership CAS，并在
启动时先完成配置与依赖预检。不能说：已经实现公网多用户服务、自动容灾、生产 SLA，或者 Linux smoke
证明了模型报告质量。

## 下一动作与退出裁决

提交推送后等待同一 SHA 的 pytest、真实 PostgreSQL 与 packaging-smoke 三个 Actions job。全部成功前
退出裁决保持 `keep-6a-open`。
