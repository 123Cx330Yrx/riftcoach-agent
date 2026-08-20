# 6B-9 Lifecycle / Export / Exit Review 设计稿

## 1. 初学者问题定义

Memory 真正可信的最后一关不是“能记住”，而是用户能知道系统记了什么、能导出、能按明确范围删除，并且
清理失败时数据不会重新出现。数据库之间存在 FK 和历史链，直接 `DELETE` 一张表可能失败或误删；因此控制面
先改变 owner 可见性，再异步/重试物理清理。这个原则叫 hidden-before-cleanup。

## 2. 本批做与不做

本批实现 owner-scoped export、三种删除范围、统一 hidden state、deletion marker、retention/purge、补偿重试、
性能/安全/两 owner 隔离纵向、package 1.6 和 Session/Memory V1 exit matrix。它不实现正式 Auth/RSO/HTTPS、
RLS、SSE/前端、备份恢复、Task cancel/lease、MCP、Multi-Agent、新基础设施或真实 Riot/Provider 调用。

## 3. 方案比较

| 方案 | 优点 | 风险 | 裁决 |
|---|---|---|---|
| 分散到各 Repository | 局部代码少 | 跨表部分删除、补偿和范围不一致 | 拒绝 |
| 中央 service + 各表 hidden_at + marker | 可见性原子、查询简单、可补偿 | migration/query 改动较多 | 采用 |
| FK cascade hard delete | 代码最短 | 破坏审计/Task 独立生命周期，失败前可能部分清理 | 拒绝 |

## 4. 合同与数据模型

`OwnerDataExport` schema 1.0 带 generated_at、owner_id、policy version 与 typed sections。它只包含当前 visible
私有数据；每类上限 500，任何一类超限返回 `export_too_large`，不静默截断。Artifact 只返回 kind/schema/path
identity/SHA，PUUID、Riot ID、Prompt、Provider/Tool body 和内部错误不导出。

`OwnerDataDeleteCommand` 的 scope 为 `conversation_only|conversation_and_derived_memory|relationship_private_data`。
前两类必须且只能带 conversation_id；第三类必须且只能带 relationship_id。Repository 服务器派生其余 tuple，
不存在和越权统一 not-found。

migration 0009 给 Candidate、Preference、Profile、Review Memory、Plan、Progress 增加 `hidden_at`；active partial
unique 条件同步为 `status='active' AND hidden_at IS NULL`。新增 `owner_data_deletions`：marker_id、owner_id、scope、
conversation_id/relationship_id、status(`cleanup_pending|complete`)、safe reason、affected counts、created/
updated/completed timestamps。marker 不保存正文。

## 5. 控制流

```text
ActorContext.owner_id + typed scope
→ Service 校验 shape
→ Repository 锁 target 并服务器派生 identity
→ 同一短事务：selected rows hidden_at=now + marker cleanup_pending
→ commit 后 owner query/Context/export 立即不可见
→ CleanupPort 清理 run/context files（如有）
→ success: marker complete
→ failure: marker 保持 pending，body-free reason，可幂等 retry
```

Retention 使用同一 Repository visibility primitive。Purge 只针对 hidden_at 早于 cutoff 的 row，并以 bounded batch
按依赖顺序删除；Conversation/Relationship/Player Subject 可因 Task/FK 独立生命周期继续保留 body-free hidden row。

## 6. 三种删除的精确效果

- `conversation_only`：Conversation 变 hidden、Message 隐藏；既有 Candidate 与长期 target 继续可查，证明对话删除
  不等于忘记已确认 Memory。
- `conversation_and_derived_memory`：再隐藏 `source_conversation_id/conversation_id` 匹配的 Candidate、typed Memory、
  Plan/Progress；其他 Conversation 和 owner-global 非来源记录不受影响。
- `relationship_private_data`：隐藏该 owner/relationship 的所有 Conversation/Message 与 player-scoped Candidate/
  Profile/Review/Plan/Progress，并隐藏 relationship；owner-global Preference 与另一个 owner 同 PUUID 数据保留。

Task/Run/Artifact 不随上述命令删除，仍由 6A endpoint/retention 管理。

## 7. 读取路径与写入门

所有 Candidate/typed Memory/training query、Memory Context selector、accept/materializer source lookup 增加
`hidden_at IS NULL`。隐藏 active record 后 partial unique 允许用户从新 Candidate 创建新 active 版本；新版本
不得把隐藏记录当 supersedes predecessor。terminal writer 遇到 hidden Conversation 继续 fail closed。

## 8. 测试与验收

1. pure export/delete/retention/marker shape、上限与时间边界；
2. Repository 真库：三 scope、active unique 重建、FK/rollback/replay/concurrency；
3. 两 owner、两 Conversation、同 PUUID 隔离；claimed-self 与 observed 数据分离且无 verified-self 创建路径；
4. export 有历史链而无 PUUID/secret/internal body；
5. cleanup 失败后不可见、pending marker、幂等 retry、purge FK 顺序；
6. API 404/409/202/200、owner 从 ActorContext 派生；
7. Context/terminal publication 回归、package schema 1.6、完整本地门禁和 exact-SHA 三 job；
8. exit matrix 逐项绑定源码、测试、CI、限制和面试表述。

## 9. 当前限制

V1 的 export 是同步有界 snapshot，不是大规模异步归档；purge 是单实例 bounded batch，不声称法务级擦除时限；
Player Subject/alias 不因单 owner 删除而物理清理；正式 Auth/RLS、备份副本清理、跨区域灾备和隐私政策审计仍未完成。
