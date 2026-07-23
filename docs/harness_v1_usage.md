# Harness v1 使用与原理

## 1. Harness 解决什么问题

RiftCoach 的领域层已经能够生成结构化比赛事实、确定性报告、RAG 增强 Coach 草稿、事实评测与受限修订。问题在于：如果这些能力只是几个独立脚本，调用者仍需人工决定执行顺序、修订次数和最终发布文件，模型失败时也缺少统一降级策略。

Harness v1 是确定性控制层。它不负责计算比赛数据，也不是另一个大模型；它负责：

- 固定一次报告运行的步骤顺序；
- 为运行分配 `run_id`；
- 保存输入、证据、草稿、评测与最终报告；
- 限制模型修订次数；
- 根据结构化评测结果和代码阈值决定是否发布；
- 在模型或评测失败时降级为确定性报告，或明确拒绝；
- 通过 Manifest 和 SHA-256 解释最终结果来自哪里。

## 2. 数据流

```text
Player Summary + 确定性报告
        ↓
本地 RAG Adapter
        ↓
KnowledgeEvidence
        ↓
Coach Generator Adapter
        ↓
CoachDraft
        ↓
Evaluation Adapter
        ↓
EvaluationResult
        ├── 通过阈值 → 发布 Coach 报告
        ├── 需要修订且预算充足 → 受限修订 → 再评测
        └── 失败或预算耗尽 → 确定性降级 / 拒绝
```

Adapter 负责把现有业务函数转换成 Harness Step Protocol。状态机只依赖 `KnowledgeEvidence`、`CoachDraft` 和 `EvaluationResult` 等领域对象，不依赖智谱 SDK 或具体 RAG 存储。

## 3. 状态机

正常通过路径：

```text
CREATED
→ FACTS_READY
→ KNOWLEDGE_READY
→ DRAFT_READY
→ EVALUATING
→ PASSED
→ PUBLISHED
```

一次修订路径：

```text
EVALUATING
→ NEEDS_REVISION
→ REVISING
→ RE_EVALUATING
→ PASSED
→ PUBLISHED
```

安全终态：

- `DEGRADED`：Coach 草稿没有通过，只发布确定性报告；
- `REJECTED`：输入无效或运行配置禁止确定性降级，没有可发布产物。

终态不可继续推进。`attempt_id` 用来拒绝过期评测或修订结果，防止旧结果覆盖当前尝试。

## 4. 运行目录与 Artifact

```text
data/runs/<run_id>/
├── manifest.json
├── inputs/
│   ├── player_summary.json
│   └── deterministic_report.md
├── knowledge/
│   └── retrieval_evidence.json
├── drafts/
│   ├── coach_draft_attempt_0.md
│   └── revised_report_attempt_1.md
├── evaluations/
│   ├── evaluation_attempt_0.json
│   └── evaluation_attempt_1.json
└── output/
    └── final_report.md
```

Manifest 记录配置、状态变化、最终决策和每个 Artifact 的：

- 类型与 Schema 版本；
- 相对路径；
- 生产步骤；
- UTC 创建时间；
- SHA-256。

Artifact 文件一旦写入便不可覆盖。读取时重新计算哈希，内容被修改会触发完整性错误。

## 5. 不消耗模型额度的 dry-run

仓库提供完全合成的公开 fixture：

```powershell
python scripts\run_review_harness.py `
  --summary examples\fixtures\player_summary_demo.json `
  --deterministic-report examples\fixtures\deterministic_report_demo.md `
  --runs-root data\runs `
  --run-id harness_v1_demo `
  --dry-run
```

dry-run 真实执行：

- Summary Schema 校验；
- 本地 RAG 检索；
- 状态机；
- Artifact Store 与原子写入；
- Manifest 和哈希登记；
- 发布门控。

它只用确定性 Fake 代替 GLM 生成、评测与修订，因此不会读取 `LLM_API_KEY`，也不会消耗模型额度。dry-run 通过只能证明控制流与存储闭环有效，不能证明真实 Coach 内容质量。

相同 `run_id` 不可重复创建。再次测试时应更换 `--run-id`，或者删除本地 `data/runs/<run_id>/`；运行目录默认被 Git 忽略。

## 6. 真实 GLM 运行

配置 `.env` 后运行：

```powershell
python scripts\run_review_harness.py `
  --summary data\cache\player_summary_<GAME_NAME>_<TAG_LINE>.json `
  --deterministic-report reports\riftcoach_report_<GAME_NAME>_<TAG_LINE>.md `
  --publish-score-threshold 85 `
  --max-revisions 1
```

主要参数：

- `--publish-score-threshold`：发布 Coach 报告所需最低分，范围 0—100；
- `--max-revisions`：最大受限修订次数，v1 支持 0—3，默认 1；
- `--rag-top-k`：本地检索返回的最大知识块数；
- `--no-deterministic-fallback`：故障时拒绝，而不是发布确定性报告；
- `--run-id`：外部指定可追踪运行标识；省略时自动生成。

## 7. 故障与安全边界

| 故障 | v1 行为 |
|---|---|
| Summary Schema 无效 | CLI 在创建运行前拒绝 |
| 确定性报告缺失或为空 | CLI 在创建运行前拒绝 |
| RAG、生成或评测异常 | 默认进入确定性降级 |
| 评测 JSON 非法 | 不相信模型输出，进入降级 |
| `pass` 但分数低于阈值 | 不发布 Coach 草稿 |
| 修订越权或结构损坏 | 丢弃修订，进入降级 |
| 修订预算耗尽 | 进入降级 |
| 禁止 fallback | 进入 `REJECTED`，不生成最终文件 |

无论哪条失败路径，未通过质量门控的 Coach 草稿都不能复制到 `output/final_report.md`。

## 8. 测试证明什么

自动化测试覆盖：

- 合法与非法状态迁移；
- Artifact 路径逃逸、不可覆盖和哈希完整性；
- 首轮评测通过；
- 修订后通过与复评失败；
- 修订预算为零；
- RAG、生成、评测和修订异常；
- 评测输出 Schema 非法；
- Adapter 对现有 Prompt、Parser 和 Validator 的复用；
- CLI dry-run 的真实检索、存储与发布。

运行：

```powershell
py -3.11 -m pytest -q
```

GitHub Actions 还会在 Ubuntu/Python 3.11 上执行同一测试集和合成 fixture dry-run，用来捕获 Windows 本地环境没有暴露的路径或编码问题。

## 9. 当前没有实现什么

Harness v1 是单进程、同步、线性的报告工作流。当前不能声称已经实现：

- 通用 DAG 工作流引擎；
- 分布式任务队列、租约或断点恢复；
- Multi-Agent 协作；
- Session 或长期 Memory；
- 标准 MCP；
- 完整 Provider/Tool Runtime。

阶段 3 会把 CLI 中暂时直接创建的 OpenAI-compatible GLM Client 替换为 Provider 抽象，并增加超时、有限重试、缓存、熔断、fallback 与运行指标。阶段 8 才在有测量收益时引入 Saber/Sea 的复杂任务图、取消、快照和恢复思想。

## 10. 面试表述

准确表述：

> 设计并实现质量门控型 Agent Harness，用确定性状态机组织 RAG 检索、Coach 生成、独立事实评测、受限修订和再评测；通过版本化 Artifact、SHA-256、修订预算和安全降级保证未通过评测的模型草稿不会被发布，并提供无模型调用的 dry-run 验证运行闭环。

不应表述为：

- 实现了通用 Agent 操作系统；
- 实现了分布式多 Agent 调度；
- 已经具备完整任务恢复；
- 已经接入标准 MCP。
