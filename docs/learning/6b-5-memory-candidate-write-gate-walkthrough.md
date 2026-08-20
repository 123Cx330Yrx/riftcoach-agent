# 6B-5 Memory Candidate & Write Gate：初学者 walkthrough

状态：实现进行中；本文解释当前设计和已落地代码，不把本地 skip 或测试专用 target 写成生产长期记忆。

## 1. 问题与底层原理

一个 Agent 会从三类地方得到“可能值得长期记住”的信息：用户明确设置、用户自然语言、模型/确定性分析
推断。它们的可信度和权限不同。最危险的错误是让模型直接调用 `UPDATE player_profile`：模型的输出是
不可信数据，不是服务器权限。

RiftCoach 把这件事拆成两个对象：

```text
Candidate = 一张“请求长期改变状态”的提案单
Typed Memory = 以后由具体业务表保存的真实长期状态
```

因此当前链路是：

```text
来源 → Candidate(pending) → Gate/用户决策 → typed materializer → 同事务 accepted
```

Candidate 被拒绝也可以安全记录决策；被接受但没有 typed target 时不能假装成功。这个原则和 Agent 的
工具调用很像：模型可以提出 ToolCall，但真正执行仍需 Tool Runtime 的权限、schema 和事务边界。

## 2. 本批范围

### 已实现/本批目标

- strict/frozen Candidate command、identity、payload、fingerprint、状态合同；
- deterministic `memory-gate-v1`；
- PostgreSQL `memory_candidates` 0005 migration/ORM/Repository；
- owner-scoped create/get/reject/expire/accept；
- same-Session typed materializer protocol；
- public structured create、safe query/accept/reject API；
- no-I/O package smoke 和阻塞 PostgreSQL 测试入口。

### 明确没有实现

- `owner_preferences`、`player_profiles`、`review_memories` 等具体 target 表；
- Training Plan/Progress；
- 模型自动抽取、assistant Message、Memory-aware Context；
- Redis、Chroma、向量检索、LangGraph、Multi-Agent、Pi/Claude SDK；
- 正式 Auth/RSO、SSE、前端；
- Riot/Provider/Key 调用。

## 3. 代码地图

| 层 | 文件 | 责任 |
|---|---|---|
| Domain | `app/memory/models.py` | 枚举、strict command、Candidate 状态、payload SHA、body-safe view |
| Gate | `app/memory/gate.py` | 纯函数来源/role/scope/kind 决策，不读数据库 |
| Port | `app/memory/ports.py` | Repository、Service、typed materializer、restricted Session 合同 |
| Service | `app/memory/service.py` | 取得服务器 identity、调用 Gate、生成 ID/TTL/fingerprint、错误映射 |
| ORM | `app/persistence/memory_records.py` | PostgreSQL 表、CHECK/FK/index metadata |
| Repository | `app/persistence/memory_repository.py` | 短事务、锁、server-derived identity、状态转换、materializer 接缝 |
| Migration | `migrations/versions/0005_create_memory_candidates.py` | 可逆 schema、source identity unique、trigger |
| HTTP | `app/api/memory_models.py`, `app/api/main.py` | strict JSON、trusted ActorContext、body-safe DTO、allowlist error |
| Composition | `app/api/composition.py` | 生产空 materializer registry；资源只在 lifespan 构造 |
| Smoke | `scripts/run_packaging_smoke.py` | 安装后 Candidate pending→reject，外部 calls=0 |

## 4. 数据流与控制流

### 4.1 创建

1. HTTP 从 `ActorContext` 得到 owner；body 不能提交 owner、relationship、subject、PUUID 或 provenance。
2. Service 先向 Repository 查询 owner-scoped active Conversation identity。
3. Gate 根据 server role 判断：例如 model inference 即使 confidence=1 也 `requires_confirmation=true`。
4. Service 创建带 TTL 的 Pending command；Repository 再按 relationship→Conversation 锁顺序复核 identity、
   Gate 和 source message/task/run 归属。
5. `(owner_id, idempotency_key)` advisory lock 串行重试；同 fingerprint replay，不同 fingerprint conflict。
6. 插入 `pending` Candidate，commit。

### 4.2 拒绝/过期

Repository 锁定 Candidate 及其 Conversation identity。只有 pending 能进入 rejected/expired；同终态重试
返回 replay，其他终态返回 conflict。拒绝/过期不调用 materializer。

### 4.3 接受

```text
锁 Candidate
→ hidden/relationship/Conversation/expiry/actor 校验
→ registry[candidate_kind]
→ 缺少 target：TARGET_UNAVAILABLE，零写入
→ materializer(session_view, candidate)
→ target reference 合同校验
→ Candidate accepted + reference
→ 同一短事务 commit
```

`MaterializationSession` 只暴露 `add/execute/scalar/flush`，没有 `commit/rollback`；materializer 必须把目标
记录写在 Repository 已拥有的事务里。若它插入目标后抛错，事务整体 rollback，Candidate 仍 pending。

## 5. 为什么使用 typed materializer 而不是万能表

Preference、Profile、Review、Plan、Progress 的 owner scope、关系角色、冲突和生命周期不同。一张 JSONB
`memories` 表会把这些规则藏进运行时 if/else，数据库无法直接证明 `observed` 不能拥有私人画像。
6B-5 又不允许提前造出具体 target，所以采用协议接缝：测试 target 证明事务；6B-6/6B-7 注册真实 typed
materializer 并让每张 target 表拥有 `source_candidate_id UNIQUE`。

这是一种“先稳定写入协议、后插入业务类型”的分阶段设计，不是把 Candidate reference 当成目标记录。

## 6. 测试证据

- `tests/test_memory_candidate_models.py`：payload canonical、SHA、终态 shape、public projection；
- `tests/test_memory_candidate_gate.py`：model confidence、observed 限制、scope/kind/source；
- `tests/test_memory_candidate_service.py`：trusted identity、错误映射、empty registry fail closed；
- `tests/test_memory_candidate_records.py`：metadata、离线 migration、constraint name；
- `tests/test_memory_candidate_migrations_postgres.py`：真实表/FK/CHECK/trigger/direct SQL；
- `tests/test_memory_candidate_repository_postgres.py`：owner、幂等、锁、reject/expire、pending；
- `tests/test_memory_candidate_materialization_postgres.py`：测试 target 同事务 commit/rollback/replay/并发；
- `tests/test_memory_candidate_api.py`：strict HTTP、trusted owner、safe DTO、empty decision、409 mapping；
- `tests/test_packaging_smoke.py`：Linux no-I/O 测试纵向 Candidate pending→reject。

本机没有 PostgreSQL/Docker 时，真库相关测试会明确 skip；公共 `postgres-migrations` job 才是 FK/trigger/
事务/并发证据。测试专用 `test_memory_targets` 不是生产 Memory 表。

## 7. Runbook

```powershell
cd D:\riftcoach-agent
.venv\Scripts\python.exe -m pytest tests\test_memory_candidate_models.py tests\test_memory_candidate_gate.py tests\test_memory_candidate_service.py -q
.venv\Scripts\python.exe -m pytest tests\test_memory_candidate_records.py tests\test_memory_candidate_api.py -q
python scripts\check_project_governance.py
```

真库/CI：

```text
DATABASE_URL=postgresql+psycopg://...
RIFTCOACH_TEST_DATABASE_URL=postgresql+psycopg://...
python -m alembic upgrade head
python -m alembic downgrade base
python -m alembic upgrade head
```

生产 composition 当前空 registry 是有意行为；调用 accept 得到 `memory_target_unavailable`，不是故障重试
信号，也不应该盲目安装一个 receipt。

## 8. 失败、安全与未实现边界

- owner 来自可信 ActorContext；没有正式 Auth 时公网 composition 仍 fail closed；
- Conversation identity 不由客户端、模型、alias 或正文覆盖；
- 跨 owner/source mismatch 不创建 Candidate；
- `model_inference`、自然语言抽取永远 pending；confidence 只展示/排序；
- observed 只能 observation_note/public_trend，不能 profile、preference、plan、progress；
- terminal Candidate immutable；accepted reference 不能替代真实 target；
- materializer 不可做网络、模型、文件 I/O；
- 这批不证明正式 Auth、真实 Provider 质量、生产 SLA 或所有分布式故障下的 exactly-once。

## 9. 面试表述

可以说：

> 我没有让 LLM 直接写长期画像，而是设计了 owner-scoped Memory Candidate write gate。Candidate 的身份从
> Conversation 在服务器端派生，模型置信度不提供写权限；确认时用同一 PostgreSQL 事务调用 typed
> materializer，目标写入和 Candidate accepted 同时提交，失败整体回滚，重复请求通过 row lock replay。

必须补充：

> 当前 6B-5 只完成 Candidate 控制面和 materializer seam，生产 registry 在具体 Preference/Profile/
> Review Memory 表实现前 fail closed；那些业务表属于后续 6B-6/6B-7。

不要说“已经有完整长期记忆”或“receipt 就是 Memory”。

## 10. exact-SHA 公共闭环

实现提交 `7156cb5` 的首个公共 run 暴露了一个测试生命周期缺口：测试专用 target 表仍引用 Candidate 表，
fixture 却先执行 migration downgrade。生产断言已经通过，失败发生在 teardown。最小修复 `dd7c9c8` 让
fixture 先删除测试表，再回滚 migration；没有使用 `CASCADE` 掩盖依赖，也没有放宽生产 FK。

Actions run `32376405150` 对修复 SHA 的三项结果为：完整 pytest
`1358 passed, 88 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
`126 passed, 1 warning`；Linux package smoke 的 Candidate 为 `rejected` 且
`external_riot_provider_calls=0`。因此 6B-5 的八维证据可以关闭，但结论仍严格止于 Candidate write gate；
Preference/Profile/Review Memory 属于等待授权的 6B-6。
