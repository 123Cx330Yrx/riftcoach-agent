# 6B-6 Preferences / Profile / Review Memory 设计稿

## 1. 初学者问题定义

6B-5 的 Candidate 是“有人提出了一条可能值得长期保存的信息”，不是信息本身。
如果只把 Candidate 标成 accepted，数据库里仍没有真正的偏好、画像或复盘记忆。
6B-6 要建立三个真实、可查询、可更正的 typed target，并把它们接到 6B-5 的
事务 materializer 接缝。

这一步解决的是**长期状态落库**，不是 RAG 检索，也不是聊天上下文拼装：

- RAG 文档回答“外部知识是什么”；
- Match/Artifact 保存“这局比赛发生了什么”；
- Memory 保存“这个 owner/玩家关系上，经过允许的规则长期成立什么”；
- Candidate 保存“这条长期状态是从哪里提出、是否被接受”。

## 2. 数据和控制流

```text
用户结构化输入 / 已发布确定性观察
        │
        ▼
6B-5 Candidate（服务器派生 owner + Conversation identity）
        │ accept
        ▼
锁 Candidate → 解析 typed envelope → advisory lock(scope,key)
        │
        ├─ 校验 relationship role / key / payload
        ├─ 锁 current active，校验 expected_version
        ├─ supersede 旧记录（如有）
        ├─ 插入 typed target 新版本
        └─ 同一事务把 Candidate 改为 accepted
        │
        ▼
Preference / Profile / Review Memory 查询投影
```

任何一步失败都回滚；模型、Riot API、文件和 Provider 不在这条事务内。

## 3. 目标表合同

### 3.1 `memory_preferences`

业务主键是 `(owner_id, memory_key, active)`。典型记录：

```text
owner_id=alice
memory_key=report_language
version=1
status=active
payload={"value":"zh-CN"}
```

Candidate 的 Conversation/relationship 只作为 provenance 和权限检查来源；同一 owner
从不同 Conversation 设置同一偏好时，仍修改 owner-global 的版本链。

### 3.2 `player_profiles`

业务主键是 `(owner_id, relationship_id, player_subject_id, self, memory_key, active)`。
V1 只允许 `self + unverified_claim` 或未来已存在的 `self + rso_verified`；当前没有
正式 RSO 创建入口。Profile 示例：

```text
main_role     → {"value":"TOP"}
champion_pool → {"value":["Renekton","Ornn"]}
```

### 3.3 `review_memories`

业务主键是 `(owner_id, relationship_id, player_subject_id, role, memory_key, active)`。
V1 的 `append` 是版本化追加：旧记录进入 history，新记录成为 active。`observed` 只能
使用 `observation_note` / `public_trend`，例如：

```text
public_trend     → {"metric":"deaths_before_15","direction":"down","value":1}
observation_note → {"text":"公开对局中前 15 分钟死亡次数出现下降趋势"}
```

这类记录描述公开观察，不写“用户的私人训练目标”或未经证明的心理/因果结论。

## 4. 版本和冲突

`version` 从 1 开始。第一次写入允许 `expected_version` 缺省或为 `null`；已有 active
时必须显式提供当前版本。两个请求同时更新时：

```text
请求 A 读取 v1，先锁 key，写 v2
请求 B 仍带 expected_version=1，拿到锁后发现当前为 v2
→ B 返回 memory_version_conflict，Candidate 仍 pending
```

旧记录只允许 `active → superseded|retired`；payload、owner、subject、key、version 和
source candidate 都不可原地修改。每个 active key 通过 PostgreSQL partial unique index
保证最多一行；每个 source candidate 通过 UNIQUE 保证最多物化一次。

## 5. 严格 payload envelope

Candidate 的通用 JSONB 保持 6B-5 合同不变。6B-6 materializer 只接受：

```json
{"value": <该 key 的严格值>, "expected_version": <整数或 null>}
```

`extra=forbid`、严格类型、长度/深度上限、allowlist key 和 digest 校验全部在纯 Python
先完成；数据库再限制 payload 大小、状态、角色、scope、FK 和唯一性。target 只保存
规范化后的 value，而不保存控制字段 envelope。

## 6. 查询 API 投影

三个查询服务只接受可信 `owner_id`，并先验证 relationship 是否属于该 owner：

- owner preference 列表：默认 active，history 由 bounded `include_history` 开关控制；
- player profile：只返回该 owner relationship 的 active self profile；
- review memory：返回 self/observed 的 active review records，history 可限量读取。

响应不包含 PUUID、原始 Candidate payload、Prompt、Provider 原始响应或内部异常；查询
跨 owner、跨 relationship、hidden conversation/relationship 一律返回安全 not-found。

## 7. 实施原子批次

1. **Pure contracts**：typed payload、scope/role/key policy、version envelope、错误模型；
2. **Materializer seam**：Fake target 先写红灯，证明同一 Session、rollback 和 conflict；
3. **ORM/migration**：三张表、复合 FK、partial unique、版本/状态 CHECK、immutable trigger；
4. **Repository**：advisory lock、active lock、supersede/insert、source candidate exactly-once；
5. **Composition**：注册三个真实 materializer，生产不再使用空 registry；
6. **Query API**：owner-scoped active/history 读取，不提供绕过 Candidate 的 PATCH；
7. **Verification**：聚焦/完整回归、migration upgrade/downgrade、真实 PostgreSQL 并发、package no-I/O、
   walkthrough/coverage、提交和 exact-SHA 三 job。

## 8. 本批明确不做

- Training Plan / Training Progress（6B-7）；
- Memory-aware Context、typed assistant terminal（6B-8）；
- 生命周期/导出/删除总线（6B-9）；
- 正式 Auth/RSO、RLS、SSE、前端、公网部署；
- Redis、Chroma、向量数据库；
- LangGraph、Multi-Agent、Pi/Claude SDK、新 Provider 或真实 Riot/Provider 调用。
