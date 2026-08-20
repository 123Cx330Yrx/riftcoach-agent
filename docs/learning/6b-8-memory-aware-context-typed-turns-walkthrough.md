# 6B-8 Memory-aware Context / Typed Conversation Turns 实现复盘

## 1. 问题与原理

数据库里“有聊天和 Memory”不等于模型应该看到全部数据。Working Context 是单次运行的有界投影：它必须
先证明 owner/Conversation/relationship/subject/role，再选择 active、可见、与当前 typed Skill 合法的数据。
Message、Memory 和 Progress 即使正文像命令，也仍是 data；只有内部 policy 与 Skill instructions 是指令。

另一条原则是 terminal truth。Agent draft 可能被 Harness 拒绝，文件也可能损坏；Assistant Message 只有在
SQL Task succeeded、publication published/degraded、final Artifact digest 和冻结 identity 全部一致后才能
落库。否则下一次运行会把未发布草稿当成可信历史。

## 2. 设计与实际实现

ADR-0045 采用 run-scoped decorator，而不是第二套 Agent 或在 Runtime 外拼 Prompt：

- schema 2.0 Task binding 转为严格 `MemoryContextBinding`，legacy 1.0 保持 null；
- PostgreSQL selector 用一个短事务选择最多 12 Message、16 Preference、16 Profile、12 Review Memory、
  1 active Plan 和 12 latest Progress；
- observed 只允许 Message、owner Preference 和 observed Review Memory，永不读取 Profile/Plan/Progress；
- `MemoryAwareContextBuilder` 把每条记录变成 optional `DETERMINISTIC_FACTS` section，仍由原 Builder/Sizer 和
  `min(Skill ceiling, caller ceiling)` 做整记录选择；
- `memory_context_manifest.json` 只保存 ID/version/digest/count/disposition/reason；
- migration 0008 给 `(conversation_id, source_run_id)` assistant row 加 partial unique；
- terminal writer 重验 Task/Artifact/identity，追加 assistant，并可把显式 typed proposal 交给既有 Candidate
  Gate。当前 Recent Review output 没有 proposal 字段，生产 projector 因而传空 tuple，不解析报告文本。

## 3. 代码地图

| 责任 | 文件 |
|---|---|
| binding/record/snapshot/body-free manifest | `app/memory/context_models.py` |
| Context manifest 原子文件 store | `app/memory/context_manifest_store.py` |
| existing Builder 的 internal data-section seam | `app/agent/context.py` |
| run-scoped decorator | `app/agent/memory_context.py` |
| owner/role-scoped PostgreSQL selector | `app/persistence/memory_context_repository.py` |
| Runtime request binding 与 Context 调用 | `app/runtime/models.py`, `app/runtime/runtime.py` |
| Compiler/Application/Executor binding 传递 | `app/product/recent_review.py`, `recent_review_service.py`, `app/tasks/recent_review_executor.py` |
| typed terminal turn/proposal | `app/conversations/turns.py` |
| 0008 与 SQL terminal writer | `migrations/versions/0008_terminal_assistant_source_unique.py`, `app/persistence/terminal_turn_writer.py` |
| Worker/production composition | `app/workers/review_worker.py`, `app/workers/composition.py` |

## 4. 数据与控制流

```text
schema 2.0 Review Task frozen identity
→ Executor creates MemoryContextBinding
→ Application compiler includes binding in RuntimeRunRequest
→ Runtime validates Skill/policy/run ID
→ PostgreSQL selector reads legal snapshot, then transaction ends
→ decorator creates data-only optional sections
→ existing ContextBuilder selects whole sections under the same ceiling
→ body-free manifest atomically persists before Provider execution
→ existing AgentLoop/ToolRuntime/ReviewHarness publishes or rejects
→ evidence verifier returns TaskTerminal
→ SQL Task succeed CAS
→ terminal writer re-reads succeeded Task/final Artifact/binding
→ append one idempotent assistant Message
→ explicit typed proposals, if any, become pending Candidates through 6B-5 Gate
```

外部 Riot/Provider 调用期间没有数据库锁。manifest 在 Harness `manifest.json` 之前写入同 run 目录不会创建
第二个 Harness；`FileRunStore.create_run()` 允许已有目录但仍要求自己的 manifest 不存在。

## 5. 验证证据

- pure：strict binding、digest/body-free manifest、stable order、self/observed shape、count partition；
- Context：data-only trust、user role、注入正文不升级、whole-record omission、无 binding 默认 parity；
- file：canonical replay、tamper conflict、safe run path、atomic temporary cleanup；
- Runtime：private binding 只交给 Context builder，run drift 拒绝；legacy request 无 I/O；
- PostgreSQL selector：两 owner/role、14→12 Message、active typed records、observed self-only 排除；
- migration/writer：0008 partial unique、Task/Artifact mismatch 零写入、assistant replay、typed Candidate pending；
- Worker：只有 succeed CAS 后调用 projector；ownership loss 不写；
- package schema 1.5：真实 PostgreSQL 中选择 Message+Preference+Plan 三条 legal Context，故意 failed Review
  的 terminal assistant count 为 0，`external_riot_provider_calls=0`。

本机没有 PostgreSQL/Docker，所以 selector、0008 与 terminal writer 真库测试明确 skip；只有实现 SHA 的公共
`postgres-migrations`/`packaging-smoke` 能补齐。公共闭环前 coverage 保持 planned。

## 6. Runbook

聚焦：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_memory_context_models.py `
  tests\test_memory_aware_context_builder.py `
  tests\test_memory_context_manifest_store.py `
  tests\test_memory_context_repository_postgres.py `
  tests\test_terminal_conversation_turns.py `
  tests\test_terminal_turn_migrations_postgres.py `
  tests\test_terminal_turn_writer_postgres.py -q
```

完整：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
.\.venv\Scripts\python.exe scripts\check_project_governance.py
git diff --check
```

私有 manifest 位于 `runs_root/<run_id>/memory_context_manifest.json`；它只能用于内部审计，不能作为公开
Message/Memory 正文 API。对话消息仍从既有 owner-scoped GET 查看，Candidate 仍从既有 API 确认/拒绝。

## 7. 失败、安全与边界

- binding 不存在/隐藏/跨 owner/role 漂移：Context 阶段安全失败，Provider 调用为 0；
- required current facts 超 ceiling：原 ContextBuilder fail closed；Memory 不会挤掉 required facts；
- manifest 已存在但 bytes 不同、路径是 symlink 或写盘失败：不执行模型；
- failed/rejected Task、report unavailable、Artifact/binding/digest mismatch：不写 assistant；
- 同 source run 同 digest：replay；同 source run 不同 digest：integrity failure；
- terminal proposal 不是显式 typed、provenance 不在 allowlist 或 Gate 拒绝：不创建 Candidate；
- 当前 Worker 的 Task success 与随后 SQL terminal projection 是两个短事务；projection 幂等但不是跨步骤原子。
  失败会产生 body-free worker error，6B-9 的 lifecycle/compensation 审查必须覆盖重试/修复边界；
- 没有开放域 follow-up Skill、向量检索、正式 Auth/RLS、SSE/前端、MCP、Multi-Agent 或真实外部调用。

## 8. 面试准确表述

可以说：

> 我把 Conversation-bound Task 的服务器身份传进现有 Runtime，用 PostgreSQL selector 选择 active、owner/
> role 合法的 Message 和 typed Memory，再作为 data-only whole sections 交给同一个 ContextBuilder ceiling。
> 每次选择都有不含正文的 manifest；Assistant 只有在 Task、publication 和 final Artifact 全部验证后才写，
> 并用 source-run unique 保证幂等。

不可以说：

- “实现了通用聊天 Agent”——V1 只增强 typed Recent Review；
- “Memory 能自动可靠提取”——当前 output 没有 proposal，系统拒绝从报告正文猜测；
- “Context 是 tokenizer 精确最优”——Sizer 仍是确定性 preflight；
- “已经生产级隔离/Auth”——当前依赖 trusted ActorContext 和 owner-scoped SQL，没有正式 Auth/RLS；
- “package 证明成功模型回复”——package 的 Review 故意失败，只证明 legal selection 和零 Assistant；成功
  terminal writer 由真实 PostgreSQL 测试证明，模型质量仍不由此推出。
