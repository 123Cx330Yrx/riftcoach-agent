# 8E Batch E 安全与部署实施计划

> **For Codex:** REQUIRED SUB-SKILL: Use the executing-plans workflow to implement this plan task-by-task.

**Goal:** 在不破坏现有 owner-scoped、Evidence/Harness 和 8C 控制面边界的前提下，分批实现可审计 Auth、部署安全、Secret、备份擦除和剩余 Web 产品模块。

**Architecture:** 采用 provider-neutral AuthPort + server-side opaque session；RiftCoach Auth 与 Riot RSO 独立。首个部署是 edge/static Web + API + Worker + PostgreSQL 的单机 Compose，数据库/Artifact/backup 共用 deletion marker 语义。当前实现保持模块化单体，所有外部来源继续经过 typed adapter 和 Harness。

**Tech Stack:** FastAPI/SQLAlchemy/Alembic/PostgreSQL、现有 8C Worker、反向代理/HTTPS edge、React/Vite/TypeScript、Playwright/axe、现有 body-free observability；不预先引入 Kubernetes、Redis、Celery、Kafka 或第二套前端动画栈。

## Current execution note (2026-08-24)

视觉 Task 3 已先完成本地门，随后 E1/E2/E3 的最小实现已落地并通过 focused TDD：HTTP opaque session/CSRF、
request body/header budgets 与单机 rate policy、versioned SecretSource/key-last Worker composition。当前仍是
local implementation，尚未取得本批独立 exact-SHA 公共闭环；OIDC/RSO、PostgreSQL session repository、真实
Secret Manager、HTTPS edge 和 deployment 继续按原顺序保留；E4 backup/restore/erase 已进入本地 TDD，
但仍未有对象存储/KMS/加密 backup bytes 或生产 restore drill。

E4 implementation/evidence `27b9256` / Actions `32660145945` 已完成 exact-SHA 三 job 公共闭环。下一项
是 E5 packaging/observability，继续复用单机 Compose、现有 health/readiness 与 body-free observability
接缝；E5 不自动引入 Redis/Kubernetes/第二套 metrics runtime。E5 implementation/evidence `ca6da44` /
Actions `32661425379` 也已完成 exact-SHA 三 job 公共闭环；下一项转入 production shell/Auth gate，仍不
把 local/test session 说成 OIDC/RSO production login。

当前 production shell/Auth gate 已完成本地 TDD：`AuthGate` 在同源 opaque session 成功前不 mount live
controller；`auth_unavailable` 与 `auth_session_expired/revoked/required` 分别投影为配置缺失与可恢复
session boundary。视觉 Task 3 同步完成低机械感 polish。实现仍等待独立提交与 exact-SHA 公共 CI；真实
OIDC/RSO、PostgreSQL session repository、HTTPS edge 和 provider adoption 不在本批声称完成。

---

## Task 1: Auth and owner session

**Files:**
- Create: `app/auth/` contracts, server session model/port and provider adapter
- Modify: `app/api/actor.py`, `app/api/composition.py`, `app/api/main.py`
- Test: auth contract, CSRF/state/nonce, owner isolation, session expiry/revocation, browser login states

Write red tests for unauthenticated/expired/revoked sessions, cross-owner lookup, and `claimed_self` versus `rso_verified`; implement only the smallest provider-neutral port and opaque HttpOnly cookie boundary. Keep external OIDC/RSO calls behind an explicitly selected adapter and never store access tokens in browser or artifacts. Verify with unit/API/PostgreSQL/browser tests before the next task.

## Task 2: Edge security and request budgets

**Files:**
- Create/Modify: deployment edge config, API security middleware/settings and security-header tests
- Test: CORS/CSP/HSTS/nosniff/referrer/permissions headers, body/connection/SSE limits, rate-policy fixtures

Start with failing tests for wildcard CORS, missing CSP, oversized/chunked bodies, idle SSE and per-owner/IP rate limits. Implement explicit production settings and a documented single-node limiter; do not claim multi-replica consistency without a shared-store ADR.

## Task 3: Secret lifecycle

**Files:**
- Modify: `app/workers/composition.py`, `app/providers/config.py`, deployment config
- Create: provider-neutral secret source/rotation/revocation contracts
- Test: key-last construction, missing/expired version, dual-key overlap, revoke, log/trace/artifact/backup redaction

Implement secret-manager injection behind a port; development environment injection remains an explicit local profile. Every failure is an allowlisted readiness/configuration result.

## Task 4: Backup, restore and erase

**Files:**
- Modify: `app/lifecycle/`, persistence lifecycle repositories, packaging/backup scripts
- Create: encrypted backup manifest and restore/erase drill harness
- Test: owner export/delete, DB/artifact purge, marker idempotency, restore replay, erase-before-ready, partial-failure compensation

Extend the existing lifecycle service so an erased owner cannot reappear after restore. Measure the provisional RPO≤24h/RTO≤2h targets; record observed results and limitations rather than declaring an SLA.

## Task 5: Production packaging and observability

**Files:**
- Modify: `Dockerfile`, `compose.yaml`, CI workflow, web static artifact packaging
- Create: edge deployment/readiness/metrics runbook
- Test: non-root image, migration order, API/worker readiness, rollback, structured logs/metrics, bounded load and restore smoke

Serve web static assets through the edge and keep API/Worker/PostgreSQL private. Preserve no-I/O package smoke and exact-SHA PostgreSQL/Linux jobs.

## Task 6: Remaining product modules

Implement in order: secure production shell/Auth gate → `Rift Awakening` → Timeline DTO/UI → Evidence/Trace drawer depth → Training full page → OP.GG breadth and the Riot/Data Dragon/official patch/OP.GG → Training → UI golden slice. Each task gets its own design review, focused TDD, screenshot/axe/performance checks and body-free evidence; use MotionSites only as one candidate source.

## Task 7: 8E exit and 8F handoff

Build a matrix covering identity, security headers, limits, Secret lifecycle, backup restore/erase, deployment, browser accessibility/performance, useful-breadth and golden slice. Mark 8E complete only after all hard gates, eight learning dimensions, local gates, independent commit and exact-SHA public CI are green.
