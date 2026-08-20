# 6B-5 Memory Candidate & Write Gate 设计

## 1. 这一步到底解决什么

聊天、比赛复盘和模型回答里经常出现“以后还值得记住”的信息，例如用户偏好中文报告、某段时间想训练
补刀，或最近复盘观察到前 15 分钟死亡偏多。直接把这些句子写进长期画像很危险：模型可能理解错、用户
可能只是举例、公开观察对象也不等于当前 owner 本人。

因此 6B-5 不直接建设“记忆内容库”，而是建设长期写入的控制面：

```text
来源事实/用户输入/模型提案
→ Memory Candidate（待审核提案）
→ deterministic gate（机器可解释规则）
→ 用户或系统决策
→ typed materializer（同事务写具体业务表）
```

Candidate 类似数据库变更申请单。它记录“谁在什么会话里提出、想改哪一类长期状态、为什么允许或拒绝”，
但 pending Candidate 本身不是 Memory。只有 typed materializer 真正写入目标表并和 accepted 一起 commit，
才算物化完成。

## 2. 本批实现与排除项

### 实现

- strict Candidate/domain contracts；
- deterministic gate policy V1；
- PostgreSQL `memory_candidates` 与 0005 migration；
- owner-scoped create/get/reject/expire/accept Repository；
- 事务内 typed materializer registry；
- 用户结构化 Candidate 的薄 HTTP create/get/accept/reject；
- body/provenance-safe public DTO；
- Fake/pure、真实 PostgreSQL、API/composition/package/CI 证据；
- 八维学习 walkthrough。

### 不实现

- 具体 Preference/Profile/Review Memory 表（6B-6）；
- Training Plan/Progress 表（6B-7）；
- assistant terminal、模型抽取 producer、Memory-aware Context（6B-8）；
- Redis、向量库、LangGraph、Multi-Agent、新 SDK；
- 正式 Auth/RSO、SSE、前端；
- 真实 Riot、Provider 或 Key 调用。

## 3. 核心模型

### 3.1 枚举

```text
TargetScope       owner_global | owner_player
CandidateKind     owner_preference | player_profile | review_memory
                  | training_plan | training_progress
Operation         set | append
ProvenanceKind    user_structured_input | user_message_extraction
                  | model_inference | deterministic_run_fact
                  | published_review_observation
Status            pending | accepted | rejected | expired
DecisionActor     user | system
```

6B-5 知道候选的业务“类型”，但不建立这些类型的目标表。

### 3.2 Pending command 与服务器身份

受信任 command 可以携带：

- owner_id、conversation_id、idempotency_key；
- 可选 source message/task/run/artifact SHA；
- target scope、candidate kind、memory key、operation、payload；
- provenance kind、producer ID/version、confidence。

它不能携带 relationship_id、player_subject_id、relationship_role。Repository 锁定 owner 可见的 active
Conversation 和 active relationship 后复制 tuple。即使客户端、模型或正文声称另一个玩家，也没有字段可
覆盖数据库身份。

### 3.3 payload 与 fingerprint

payload 必须是 JSON object，canonical JSON UTF-8 最大 8 KiB，禁止非有限数字和不能稳定序列化的对象。
fingerprint 覆盖 schema、conversation/source refs、proposal、payload canonical bytes 与 provenance producer，
但不包含服务器生成 candidate ID/时间。相同 owner + Idempotency-Key + fingerprint 返回 replay；同 key 不同
fingerprint 返回 conflict。

## 4. Gate policy V1

Gate 是纯函数，输入 proposal/provenance/relationship role，输出：

```text
allowed
requires_confirmation
reason_code
policy_version=memory-gate-v1
```

主要规则：

1. scope/type 一致：owner preference 只能 owner_global；其他类型 owner_player；
2. observed 只能 `review_memory + append + observation_note|public_trend`；
3. model/natural-language 一律 requires confirmation，confidence=1 也不例外；
4. structured UI 只对 allowlisted owner preference/self profile 具备 system-accept eligibility；
5. deterministic run fact 只允许 review/progress；published review 只允许 review observation；
6. Training Plan 无论来源都要求用户确认；
7. Gate 拒绝的 proposal 不创建 Candidate，返回安全 reason code。

Gate 只决定“是否允许进入候选队列、是否必须人工确认”，不决定目标表冲突、Plan metric 或版本 supersede。
这些属于以后 typed materializer 的业务规则。

## 5. PostgreSQL schema

`memory_candidates` 采用普通关系列保存身份/状态，JSONB 只保存严格有界 proposal payload：

```text
candidate_id UUID PK
schema_version 1.0
owner_id + conversation_id + relationship_id + player_subject_id + relationship_role
idempotency_key + request_fingerprint
source_message_id? + source_task_id? + source_run_id? + source_artifact_sha256?
target_scope + candidate_kind + memory_key + operation
proposal_payload JSONB + proposal_payload_sha256
provenance_kind + producer_id + producer_version + confidence?
gate_policy_version + requires_confirmation
status + decision_actor_kind? + decision_actor_id? + decision_reason_code? + decided_at?
materialized_target_kind? + materialized_target_id? + materializer_version?
created_at + updated_at + expires_at
```

数据库 CHECK 保证：

- pending 没有 decision/materialization 字段；
- accepted 必须同时有 decision 和 materialization reference；
- rejected/expired 有 decision 但没有 materialization；
- confidence 为 0..1；payload/fingerprint/digest/ID 有界；
- status/role/scope/kind/operation/provenance 使用允许列表；
- accepted/rejected/expired 不能通过 UPDATE 回到 pending，identity/proposal/provenance 不可变；
- Conversation 复合 FK 防止 Candidate 换 owner/subject；
- source message/task/run 引用必须属于同一 Conversation identity；
- `(owner_id,idempotency_key)` 唯一。

索引优先服务 owner pending list/decision、Conversation history 和 expiry；6B-5 暂不做向量索引。

## 6. Repository 与事务控制流

### 6.1 create

```text
lock active relationship
→ lock active Conversation
→ validate optional source belongs to same identity
→ run deterministic gate before insert
→ owner/key advisory lock
→ replay/conflict check
→ insert pending Candidate using server tuple
→ commit
```

Gate 判定不合法时 Repository 不插入任何 row。公共 API 只能创建 `user_structured_input`，其他来源留给以后
内部 producer。

### 6.2 reject / expire

锁定 owner-scoped Candidate。pending 才能进入对应终态；同一终态重试返回 replay；其他终态返回 conflict。
这两条路径不调用 materializer。

### 6.3 accept

```text
lock Candidate
→ pending/owner/source/relationship/gate actor validation
→ lookup registry[candidate_kind]
→ missing: target_unavailable, no mutation
→ materializer.materialize(session, candidate)
→ validate returned kind/id/version
→ Candidate accepted + target reference
→ commit
```

同一 Candidate 再次接受时只返回 accepted replay，不再次调用 materializer。并发请求由 row lock 串行。
materializer 与 Repository 共享 Session，禁止自己 commit/rollback；异常导致整个 transaction rollback。

## 7. API

```text
POST /conversations/{conversation_id}/memory-candidates
GET  /memory-candidates/{candidate_id}
POST /memory-candidates/{candidate_id}/accept
POST /memory-candidates/{candidate_id}/reject
```

create 使用 `Idempotency-Key`。owner 来自 ActorContext。accept/reject body 为空，防止客户端提交
decision_actor、target identity 或 materialization reference。公开 response 不含 payload、provenance producer、
confidence、subject/PUUID/source body；错误只用 allowlisted code。

生产 composition 注册空 materializer registry。因此 6B-5 期间 accept 会安全返回 409
`memory_target_unavailable`，Candidate 仍 pending。测试可以注入 Fake Service 验证 HTTP accepted projection，
真实 PostgreSQL 测试用测试专用 typed target 证明事务，而不把它安装到产品。

## 8. 测试为什么能证明行为

| 层 | 证明内容 | 不能证明 |
|---|---|---|
| pure model/gate | payload、来源、role、confidence、状态 shape | 数据库并发 |
| Fake Service | 错误映射、ID/clock/fingerprint、防御性投影 | PostgreSQL FK/锁 |
| migration | 可逆 schema、CHECK/FK/trigger、metadata head | API 组合 |
| Repository PostgreSQL | server tuple、owner 隔离、幂等、终态、并发 | 正式 Auth |
| materializer PostgreSQL | 同事务 target+accepted、回滚、exact replay | 6B-6 真实 Memory 业务规则 |
| API/composition | trusted owner、strict DTO、fail-closed registry、no-I/O | 模型质量/真实 Riot |
| package/CI | Linux 安装、真库 migration、外部 calls=0 | 公网部署/SLA |

## 9. 面试安全表述

可以说：

> 我把模型提案和长期状态分开，设计了 PostgreSQL-backed Memory Candidate write gate。Candidate 从服务器
> Conversation 派生 owner/player identity；模型置信度不提供写权限；确认时通过同事务 typed materializer
> 写目标记录并更新 Candidate，失败整体回滚，重复确认幂等重放。

不能说：

- “6B-5 已经实现完整长期记忆”；
- “用了向量数据库自动召回用户画像”；
- “exactly once 在任何分布式故障下都绝对成立”；
- “公开 observed 账号等于已验证本人”；
- “测试专用 target 就是生产 Preference/Profile 表”。
