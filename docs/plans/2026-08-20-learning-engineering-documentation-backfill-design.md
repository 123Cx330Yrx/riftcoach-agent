# RiftCoach 持久教学与工程说明补齐设计

## 1. 结论

RQ-067 不是一个新的产品阶段，也不改变阶段 0—8 或 6B-1 至 6B-9 的顺序。它是进入
`6B-3-conversation-message-foundation` 前的横向交付修补：把过去已经实现、测试并公开验证，
但尚未形成可独立复习材料的能力补成持久教学与工程说明。

重新从阶段 0 审计后的结论是：缺口并非从 6B 才开始。最早缺口位于阶段 0 的参考证据建档；
阶段 1、阶段 4、5A、5B、6B-1 和 6B-2 也有不同程度缺口。阶段 2、5C、5D、5E、5P、5F、6A
已经可以由少量明确的设计、实施计划与退出审查组合覆盖，不重复重写。

## 2. 什么才算“补齐”

每个被标记为完整的阶段或覆盖组，必须能从仓库中的少量明确材料回答以下八类问题：

1. **问题与原理**：为什么需要这一层，它解决什么真实问题；
2. **设计与实现**：采用了什么方案，拒绝了什么方案，实际实现与原计划有何差异；
3. **代码地图**：入口、合同、核心实现、存储/Adapter 和输出分别在哪；
4. **数据流与控制流**：数据如何变化，谁决定下一步、终态和发布；
5. **验证证据**：要求怎样映射到源码、测试、公共 CI 和仍未知的边界；
6. **运行方法**：如何用安全、可重复的命令观察当前能力；
7. **失败、安全与范围边界**：失败时怎样收敛，哪些能力尚未实现；
8. **面试安全表述**：可以怎样准确描述，哪些说法属于夸大。

聊天记录、canonical、progress 中的一句“已经讲过”、测试总数或代码存在，均不能单独满足上述合同。
同一份成熟退出审查可以覆盖多个原子子阶段，但必须在学习覆盖账本中显式列出覆盖关系。

## 3. 三种补齐方案

### 方案 A：为每个历史原子子阶段新建一篇文档

优点是颗粒度最细。缺点是会产生几十篇重复文档，设计、实现与退出事实容易再次漂移，维护成本高。
不采用。

### 方案 B：只写一篇全项目总览

优点是文件最少。缺点是无法承载具体代码、测试、事故和边界，也不能证明每个子阶段已被教学覆盖。
不采用。

### 方案 C：覆盖矩阵驱动的混合方案

采用。成熟材料直接复用并进入统一索引；部分缺口原位补强；明显缺口新增实现后 walkthrough/review。
用机器可检查的覆盖清单绑定当前 checkpoint 和持久材料，避免以后再次只靠聊天记忆。

## 4. 审计裁决

| 覆盖组 | 裁决 | 本批动作 |
|---|---|---|
| 阶段 0 | 最早真实缺口 | 新增参考证据审计：source snapshot、真实模块、验证强度、采纳/拒绝和面试边界 |
| 阶段 1 | 明显缺口 | 新增领域核心 walkthrough、真实代码图、错误流、测试矩阵、运行和面试表述 |
| 阶段 2 | 完整 | 在学习索引中复用 Harness 设计、实施计划和使用说明 |
| 阶段 3 Core | 小幅缺口 | 在现有 Provider/Tool Runtime 使用说明补最终证据矩阵和面试表述；3G-1/2/3 直接复用 |
| 阶段 4 | 实施后复盘缺口 | 新增 RAG V1 implementation review、代码图、证据矩阵、维护/回滚边界和面试表述 |
| 5A | 小幅缺口 | 原位补真实代码地图、原始测试矩阵及后来深化关系 |
| 5B | 明显缺口 | 新增 Skill Contract V1 实现后复盘 |
| 5C | 完整 | 复用总退出审查，并从较短早期设计链接到它 |
| 5D/5E/5P/5F | 完整 | 在学习索引中显式列出入口设计、实施和退出材料 |
| 6A | 组合覆盖完整 | 复用总设计、总实施计划、exit matrix/review 与 README 运行说明，不制造七份重复材料 |
| Session/Memory entry | 完整 | 复用 ADR-0039、总设计和总实施计划 |
| 6B-1 | 实现后复盘缺口 | 新增身份/关系/Link 持久化 walkthrough，包含两次真实 migration 事故 |
| 6B-2 | 实现后复盘缺口 | 新增 API→Worker→事务外 Resolver→短事务终态 walkthrough |
| 6B-3 | 尚未实现 | 先登记 planned；进入后必须在关闭前形成完整持久成品 |

## 5. 本批产物

### 新增

- `docs/learning/README.md`：面向项目所有者的学习入口与覆盖状态；
- `docs/learning/coverage.yaml`：机器可检查的覆盖关系；
- `docs/learning/stage-0-baseline-and-reference-evidence.md`；
- `docs/learning/stage-1-domain-core-v1-walkthrough.md`；
- `docs/learning/stage-4-rag-v1-implementation-review.md`；
- `docs/learning/stage-5b-skill-contract-v1-implementation-review.md`；
- `docs/learning/6b-1-player-identity-link-persistence-walkthrough.md`；
- `docs/learning/6b-2-async-player-link-worker-api-walkthrough.md`。

### 原位补强

- `docs/provider_tool_runtime_usage.md`：最终证据矩阵与面试边界；
- `docs/agent_loop_v1.md`：代码地图、测试矩阵与后续深化；
- 5C 的短入口设计：链接完整 5C exit review；
- `README.md`：学习入口和已完成 Player Link 能力/运行边界；
- `AGENTS.md`：把持久学习成品加入子阶段关闭合同；
- `scripts/check_project_governance.py` 与测试：检查覆盖文件、当前 checkpoint 和证据路径。

## 6. 治理合同

`docs/learning/coverage.yaml` 为覆盖账本，不取代 canonical。每个 coverage group 声明：

- `id` 与 `covers`；
- 严格递增的 `sequence`，防止通过移动 YAML 列表项绕过前序覆盖门；
- `status: complete | planned`；
- 八个维度分别由哪些仓库内 Markdown 文件承担。

治理脚本要求：

1. 覆盖文件是合法 YAML 且 schema 受支持；
2. 当前 canonical checkpoint 必须出现在某个 coverage group；
3. sequence 必须是唯一、严格递增的非负整数，当前组之前的组必须全部 complete；
4. `complete` group 的八个维度都非空；
5. 所有证据路径必须是仓库内、存在、非空的 Markdown 文件；
6. `planned` group 可以暂缺部分证据，但不能被写成已完成。

未来从 6B-3 切换到 6B-4 前，6B-3 group 必须改为 complete 并补全八维证据，否则治理门失败。

## 7. 验证与退出

本批不改变产品代码和数据库 schema，不读取 Key，不调用 Riot/Provider，不执行外部参考项目代码。
验证分为：

1. 新增治理单测的红灯/绿灯；
2. 文档内部链接、coverage path、UTF-8 与 YAML 检查；
3. `tests/test_project_governance.py` 聚焦回归；
4. 完整 pytest、两套 RAG、Harness dry-run、compileall、安全与 `git diff --check`；
5. 独立提交、推送，并等待 exact-SHA 公共 CI。

只有公共闭环后才能称“缺口已补齐”。随后按 RQ-067 无需再次确认，直接进入 6B-3；进入不等于完成，
6B-3 仍须按初学者说明、设计复核、TDD、最小实现、实现后复盘和公共验证逐步完成。
