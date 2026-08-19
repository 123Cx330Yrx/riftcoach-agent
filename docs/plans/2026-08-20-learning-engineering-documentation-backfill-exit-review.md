# RQ-067 持久教学与工程说明补齐退出复核

## 1. 退出结论

本轮复核确认：缺口不是从 6B 才开始，最早真实缺口在阶段 0。阶段 0 以前已经有 ADR、路线和部分
高层吸收矩阵，但没有把“参考材料身份 → 实际源码模块 → 可复核测试事实 → RiftCoach 采纳/拒绝理由
→ 面试边界”串成独立证据链。阶段 1、4、5A、5B、6B-1、6B-2 又分别缺少不同程度的实现后复盘。

本轮采用覆盖矩阵驱动的混合补齐：成熟材料直接复用，真实缺口才新增 walkthrough 或 implementation
review。这样既避免数十篇重复文件再次漂移，也不把一篇总览当成所有阶段的证据。产品代码范围保持关闭：
本轮没有创建 Conversation、Message 或 Memory schema、migration、Repository、API 或测试，没有读取
Riot/Provider Key，也没有执行参考项目代码。

本地退出判定：`pass-local-pending-public-ci`。只有本批独立提交对应的 exact-SHA GitHub Actions
`pytest`、`postgres-migrations` 和 `packaging-smoke` 全部成功，才能升级为公共完成；在此之前 canonical
仍停在 `6B-3-conversation-message-foundation`，产品代码门关闭。

## 2. 审计方法

对每个历史覆盖组检查八个问题：

1. 它解决的真实问题和底层原理是什么？
2. 设计选择与实际实现是否一致，拒绝了什么？
3. 入口、合同、核心实现、适配器和输出分别在哪？
4. 数据怎样流动，控制流在哪里决定下一步、终态和发布？
5. 哪个源码、测试、公共 CI 和限制证据支持结论？
6. 项目所有者怎样用安全、可重复的命令观察它？
7. 失败、安全和范围边界是什么？
8. 面试时怎样准确说，哪些说法会夸大？

“聊天中曾经讲过”、代码目录存在、测试总数或某个参考项目 README 都不能单独满足这八项。

## 3. 覆盖裁决与实际动作

| 覆盖组 | 审计结论 | 本轮交付 |
|---|---|---|
| 阶段 0 基线与参考证据 | 最早真实缺口 | 新增参考快照身份、源码/测试边界、采纳/拒绝和面试证据审计 |
| 阶段 1 领域核心 | 明显缺口 | 新增 Riot→Analyzer→Summary→Report walkthrough、公式、未知值和短局边界 |
| 阶段 2 Harness | 已充分 | 索引复用已有使用说明、设计、实施和退出材料 |
| 阶段 3 Provider/Tool Runtime | 小幅缺口 | 原位补实现证据矩阵、当前运行观察、演进关系和面试边界 |
| 阶段 4 RAG/4M | 实施后缺口 | 新增代码地图、RRF/证据门、评测解释、维护/回滚限制复盘 |
| 5A Agent Loop | 小幅缺口 | 原位补四个核心对象、原始验收矩阵和后续深化关系 |
| 5B Skill Contract | 明显缺口 | 新增三种事实源、Loader 流、权限边界、合同测试和面试复盘 |
| 5C Router | 已充分 | 早期短设计链接统一退出复核，不重复写六篇教材 |
| 5D/5E/5P/5F、6A、Session/Memory entry | 已有组合覆盖 | 在学习索引中显式登记设计、实施计划、矩阵和退出复核 |
| 6B-1 Player Identity | 实现后缺口 | 新增四表、Repository、CAS、迁移事故和外服认领边界复盘 |
| 6B-2 Player Link | 实现后缺口 | 新增 API→Worker→事务外 Resolver→终态、Fake smoke、隐私与 hard-crash 边界复盘 |
| 6B-3 Conversation/Message | 尚未实现 | 仅登记为 `planned`，复用总设计作为入口；不得冒充完成 |

详细覆盖关系由 [`docs/learning/coverage.yaml`](../learning/coverage.yaml) 机器检查；学习入口由
[`docs/learning/README.md`](../learning/README.md) 提供。

## 4. 本轮新增和补强材料

### 新增

- `docs/learning/README.md`：项目所有者学习入口、八维合同、证据强度和防复发说明；
- `docs/learning/coverage.yaml`：17 个覆盖组，严格递增 sequence，当前 6B-3 为 planned；
- `docs/learning/stage-0-baseline-and-reference-evidence.md`；
- `docs/learning/stage-1-domain-core-v1-walkthrough.md`；
- `docs/learning/stage-4-rag-v1-implementation-review.md`；
- `docs/learning/stage-5b-skill-contract-v1-implementation-review.md`；
- `docs/learning/6b-1-player-identity-link-persistence-walkthrough.md`；
- `docs/learning/6b-2-async-player-link-worker-api-walkthrough.md`。

### 原位补强

- `docs/provider_tool_runtime_usage.md`、`docs/agent_loop_v1.md`：实现后代码图、证据矩阵、运行观察、
  演进和面试边界；
- 5C-1/2/3 短设计：指向统一 5C 退出复核；
- `README.md`：当前 Player Link 能力、只启动 Link Worker 的安全运行方式和外服认领边界；
- `AGENTS.md`：完成子阶段必须留下八维持久证据；
- `scripts/check_project_governance.py` 与 `tests/test_project_governance.py`：覆盖文件、当前 checkpoint、
  sequence、前序完整性、证据路径和 complete 维度防线；
- 路线、修订、能力矩阵、项目决策、执行状态和活动计划：记录 RQ-067 及条件授权，不改主阶段顺序。

## 5. 本地验证证据

### 聚焦回归

```text
Agent Loop + Skill Contract             34 passed
Provider/Tool Runtime                   101 passed, 68 subtests passed
领域核心 + RAG 代表性集合               37 passed
治理覆盖门                              12 passed
```

### 完整回归

```text
1224 passed, 42 skipped, 1 warning, 110 subtests passed
```

42 个 skip 是本机没有 PostgreSQL/Docker 的既有边界，不能被写成真库证据；6B-1/6B-2 的真实 PostgreSQL
和 package 证据仍由此前 exact-SHA 提交提供。

### 横向门

```text
RAG development:  Recall/MRR/nDCG 1.0, no-answer FPR 0.0
RAG holdout:     Recall/MRR/nDCG 1.0, FPR 0.0, abstention 1.0, citation 1.0
Harness dry-run: published, 0 revisions
compileall:      pass
SDK boundary:    pass
tracked secret/run data: pass
Markdown links/UTF-8/YAML/diff: pass
governance:      pass
```

RAG 数字只说明当前 8 条 development 和 7 条独立 holdout 门可复现；Harness dry-run 只说明 Fake/fixture
组合链可运行。它们都不证明真实 Provider 质量、生产部署或项目所有者已经掌握全部代码。

## 6. 防复发治理不变量

`coverage.yaml` 每个 group 必须声明：

- `sequence`：唯一、非负且严格递增；
- canonical group ID order：由治理脚本固定，不能靠重排并同步重编号绕过前序门；
- `covers`：一个 checkpoint 只能由一个 group 负责；
- `status`：`complete` 或 `planned`；当前在做的工作可以 planned，但不能被当成完成；
- `evidence`：complete group 的八个维度都必须有仓库内存在、非空 Markdown 证据。

治理脚本还要求 canonical 当前 checkpoint 出现在覆盖账本，并检查当前组之前的所有组均为 complete。未来
当 canonical 要从 6B-3 切到 6B-4 时，如果 6B-3 没有实现后复盘和八维证据，治理会拒绝该状态。

## 7. 仍然保留的限制

- 文档完整不等于模型质量、线上可用性或生产部署完成；
- 参考项目审计仍是研究证据，不是 RiftCoach 的依赖或实现贡献；
- 6B-3 之前没有 Conversation/Message/Memory 产品代码；
- 学习材料能让复习路径可恢复，但不能证明项目所有者已经读完，后续还需要逐篇读码、运行和问答；
- 本轮公共 CI 尚未运行，不能把本地 `pass-local-pending-public-ci` 写成公开完成。

## 8. 面试安全表述

可以说：

> 我发现项目早期缺的不是更多框架，而是把已实现能力变成可复核的学习与工程证据。因此从阶段 0
> 重新审计，使用覆盖矩阵把源码、测试、CI、运行方法和边界绑定到每个 checkpoint；成熟退出复核复用，
> 真缺口才新增实现后 walkthrough。这样代码进度和我能否解释它被分开管理。

不能说：

- “写了学习文档就代表产品功能增加”；
- “参考项目的源码/文档证明 RiftCoach 已拥有它们的能力”；
- “本地测试总数或 RAG 满分证明真实模型质量”；
- “6B-3 已经实现，因为它已经出现在路线和 coverage.yaml 中”。

## 9. 下一检查点

本批独立提交并通过 exact-SHA 三 job 后，按 RQ-067 自动进入：

```text
6B-3 初学者问题与原理教学
→ 现有 Session/Memory 设计复核
→ Conversation/Message 红灯合同
→ 最小 PostgreSQL schema/migration/Repository/API 实现
→ 实现后 walkthrough 与 coverage 更新
→ 本地门禁、提交/推送、exact-SHA 公共 CI
```

6B-3 仍不接 Agent、Review Task、Memory 写入、Auth/RSO、SSE、前端或新的 LangGraph/SDK；这些边界继承
ADR-0039、总设计和阶段 6 实施计划。

## 10. 公共闭环更新

本复核初版的 `pass-local-pending-public-ci` 已由提交
`63435d90f5153309fce98b92a2ff58425d54a684` 的 GitHub Actions run `32308631289` 兑现为公共完成；
`pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 均成功。RQ-067 前置门关闭，下一检查点
正式是 6B-3 初学者设计复核与 TDD。这里的公共成功仍只覆盖文档/治理和既有工程边界，不把 6B-3
产品功能或真实模型质量写成已完成。

### 10.1 后续治理加固

6B-3 设计前的只读复核发现，仅检查 YAML 列表位置和递增 sequence 仍允许“重排并重新编号”的
理论绕过。已增加 `LEARNING_COVERAGE_CANONICAL_ORDER`、coverage YAML 的人类可读镜像和负例测试；
治理聚焦由 10 项增为 12 项，主文档门的公共结果不变，且该加固不把 6B-3 代码误标为完成。
