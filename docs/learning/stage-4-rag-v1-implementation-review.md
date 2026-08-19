# 阶段 4 学习复盘：RAG v1 的真实实现与证据边界

> 本文从实现完成后的视角解释 RiftCoach RAG v1。它补充已有的设计文档，重点回答“代码
> 最终在哪里、一次检索怎样流动、评测数字能证明什么”。当前项目进度仍以
> [`project_execution_state.md`](../project_execution_state.md) 为准。

## 1. RAG 真正解决什么问题

Player Summary 只记录这个玩家已经发生的比赛事实，例如补刀、经济、伤害和死亡时间。它
不会自然包含这些知识：

- 小样本胜率应该怎样解释；
- 视野分能说明什么、不能说明什么；
- 怎样把一个统计差异变成可执行训练观察；
- 哪些结论超出了 Riot 赛后数据边界。

把所有知识硬写进 Prompt 会带来版本漂移、无法引用和难以评测的问题。RAG 的职责是：在
生成前，从一个可维护知识库中找出**与当前问题相关、有来源、适用版本明确**的证据。

```text
用户/报告问题
→ 检索候选
→ 过滤不适用或证据不足的内容
→ 返回结构化 KnowledgeHit
→ 分配不可由模型伪造的引用 ID
→ 交给 Agent 解释
→ Harness 检查引用和发布边界
```

RAG 不等于向量数据库。数据库只是可能的存储手段；RAG 的核心是检索合同、证据策略、引用
和评测。当前知识库只有少量 Markdown，先用本地可重复实现比提前部署 Milvus、Elasticsearch
和 Neo4j 更容易验证。

## 2. 从 v0.1 到 v1：设计和采用裁决

### 2.1 v0.1 的真实起点

早期 `LocalKnowledgeRetriever` 按 Markdown 标题切块，用中文单字/二元词和简化 TF-IDF
排序。它验证了“外部复盘知识能否改善 Coach 上下文”，但缺少正式元数据、稳定 chunk ID、
父子块、语义通道、融合、拒答、冲突处理和检索评测。

### 2.2 v1 采用的方案

阶段 4 参考 AGI-Saber 的父子块、混合检索和 RRF 思想，但重写为本地、可替换实现：

1. Markdown front matter 保存来源、知识类型、版本、更新时间、位置和有效期；
2. H2 章节成为父块，较小子块负责匹配，命中后回填父块上下文；
3. BM25 提供精确词法召回；
4. `EmbeddingProvider` 提供稠密检索接口，默认 `HashingEmbeddingProvider` 只做确定性基线；
5. RRF 根据两个通道的排名融合，不直接相加不同量纲的分数；
6. Evidence Policy 检查版本、位置、有效期、词法支持、查询覆盖、冲突和来源多样性；
7. 没有足够证据时正常 `abstained=true`，与系统故障分开；
8. `knowledge.search` 把检索器接入阶段 3 Tool Runtime；
9. Harness 分配 `[K1]` 等 citation ID，保存 chunk/parent/source/version 映射并拒绝未知 ID；
10. development 与 independent holdout 分开评测。

### 2.3 明确拒绝或延后的方案

- 没有直接复制 Saber 的 PostgreSQL + Elasticsearch + Milvus + Neo4j 全家桶；
- 没有把 hashing vector 宣称为真实语义模型；
- 没有实现 LLM 查询改写、多查询 Agentic Retrieval 或 cross-encoder 精排；
- 没有根据 8 条开发题或 7 条 holdout 题声称大规模泛化；
- 没有把 citation 支持词检查说成完整 Claim-to-Evidence 语义正确率；
- 没有完整的知识库自动构建、原子版本切换和回滚流程；该维护能力仍在
  [`architecture_capability_matrix.md`](../architecture_capability_matrix.md) 的 Q06 中明确待补。

相关设计分别见：

- [`rag_v1_baseline.md`](../rag_v1_baseline.md)：起点、指标与当前基线；
- [`RAG 索引与混合召回设计`](../plans/2026-07-23-rag-v1-index-retrieval-design.md)；
- [`证据策略与 Harness 接入设计`](../plans/2026-07-24-rag-v1-policy-harness-design.md)；
- [`4M 独立评测门`](../plans/2026-08-04-rag-4m-independent-gate.md)；
- [`ADR-0004`](../adr/0004-lightweight-rag-before-heavy-infrastructure.md)：轻量优先。

## 3. 真实代码地图

### 3.1 类型和可替换边界

| 文件 | 真实职责 |
|---|---|
| `app/rag/models.py` | `KnowledgeMetadata`、`KnowledgeQuery`、`KnowledgeHit`、`KnowledgeSearchResult` 的不可变合同 |
| `app/rag/provider.py` | `KnowledgeProvider.search()` Protocol；让业务不绑定具体索引 |
| `app/rag/legacy_provider.py` | 将 v0.1 旧检索器适配到新合同，用于兼容和对照 |

关键对象的关系：

```text
KnowledgeQuery(text, top_k, filters)
→ KnowledgeProvider.search()
→ KnowledgeSearchResult(hits, abstained, diagnostics)
→ KnowledgeHit(chunk_id, parent_id, content, matched_content, score, metadata)
```

### 3.2 文档、索引与召回

| 文件 | 真实职责 |
|---|---|
| `app/rag/documents.py` | 解析受限 front matter 和 Markdown；形成父/子块；生成内容稳定 ID |
| `app/rag/bm25.py` | 本地 BM25 词法索引和排序 |
| `app/rag/embedding.py` | `EmbeddingProvider`、确定性 Hashing Embedding 与 DenseIndex |
| `app/rag/hybrid.py` | 依次取得 BM25/dense 候选、RRF 融合、父块去重、调用 Evidence Policy |
| `app/rag/retriever.py` | v0.1 tokenizer/legacy 检索能力，也被 Evidence Policy 复用做词元覆盖 |

### 3.3 证据、工具和发布接缝

| 文件 | 真实职责 |
|---|---|
| `app/rag/policy.py` | 适用性过滤、支持阈值、版本冲突、确定性重排、来源多样性、abstain diagnostics |
| `app/tools/adapters/knowledge.py` | 把 `KnowledgeProvider` 包成 Schema 严格的 `knowledge.search@2.0.0` 工具 |
| `app/harness/knowledge.py` | 去重真实 Tool payload，生成 `K1...Kn` 和 `KnowledgeEvidence` |
| `app/harness/adapters.py::LocalRagAdapter` | 通过 Tool Runtime 调 `knowledge.search`，不直接绕过工具边界 |
| `app/harness/runtime.py` | 保存 `retrieval_evidence.json`；发布前拒绝报告中不存在的 citation ID |

### 3.4 评测和运行入口

| 文件 | 真实职责 |
|---|---|
| `app/rag/evaluation.py` | Dataset/Case/Result 合同及 Recall@K、MRR、nDCG、FPR、abstention、citation support 计算 |
| `scripts/query_rag.py` | 本地查询、显示父/子块数量、diagnostics 和命中证据 |
| `scripts/evaluate_rag_retrieval.py` | 选择 legacy/hybrid、加载数据集、写结果，并按阈值返回非零退出码 |
| `data/evaluation/rag_retrieval_cases.json` | 参与阈值开发的 development 数据集 |
| `data/evaluation/rag_v1_holdout_cases.json` | `role=held_out`、`calibration_excluded=true` 的 4M 数据集 |
| `data/evaluation/results/rag_v1_*_baseline.json` | 已归档的结构化结果，不是不可变生产模型成绩 |

主要测试职责：

- `test_rag_documents.py`：元数据、父子块、稳定 ID 和坏文档；
- `test_rag_bm25.py`：BM25 排序；
- `test_rag_embedding_hybrid.py`：Hashing/Dense/RRF 和 embedding fallback；
- `test_rag_evidence_policy.py`：支持阈值、适用性、冲突、多样性和 abstain；
- `test_rag_contracts_and_evaluation.py`：类型、指标和数据集角色；
- `test_riftcoach_tool_adapters.py`：`knowledge.search` Schema 投影；
- `test_harness_adapters.py`、Harness runtime tests：`K1` 引用和非法引用发布阻断。

## 4. 一次检索的实际数据和控制流

```text
data/rag_docs/*.md
      │ load_markdown_corpus()
      ├─ front matter → KnowledgeMetadata
      ├─ H2 section → ParentChunk（完整上下文）
      └─ paragraph/length split → ChildChunk（匹配单元）
      │
      ├───────────────┐
      ▼               ▼
 BM25Index         DenseIndex
 精确词法          HashingEmbeddingProvider
      │               │
      └──── rank lists┘
              │
              ▼
       Reciprocal Rank Fusion
       score += 1 / (rrf_k + rank)
              │
              ▼
       child 命中 → parent 内容回填
              │
              ▼
 EvidencePolicy.apply(query, candidates)
      1. version/position/as_of 适用性
      2. BM25 score + query coverage 支持门
      3. knowledge_key 版本优先/冲突拒绝
      4. 确定性 rerank
      5. 每来源数量限制
              │
              ├─ 无证据 → abstained=true + diagnostics
              └─ 有证据 → ordered KnowledgeHit[]
              │
              ▼
 knowledge.search ToolResult
              │
              ▼
 Harness knowledge_evidence_from_search_payloads()
       → [K1], [K2]... + source/chunk/parent/version
              │
              ▼
 Agent/Generator 看到 data-only evidence context
              │
              ▼
 Harness 校验报告中引用 ID 并决定发布/降级
```

### 为什么“小块召回、父块回填”

整章直接检索，上下文完整但主题太多；极小片段检索，命中精确但解释可能残缺。当前实现让
ChildChunk 参与 BM25/Dense 排名，返回时读取对应 ParentChunk 的完整章节，同时把命中的
`matched_content` 保留给 Evidence Policy 和审计。

### 为什么 RRF 不直接相加分数

BM25 分数和余弦相似度不在同一量纲。RRF 只使用“各通道排第几”，因此不需要假设两个分数
可以直接比较。它提高了融合的可解释性，但仍不保证语义正确，所以后面还有 Evidence Policy。

### Hashing Embedding 到底是什么

它把 token 确定性映射到固定维度并归一化，用于验证 DenseIndex、余弦检索和可替换接口。它
没有经过语言语义训练，不能稳定理解同义词。当前“hybrid”表示词法通道 + 稠密向量通道的
工程链路，不表示已经接入高质量语义 Embedding 模型。

## 5. 评测指标如何理解

- **Recall@K**：标注相关来源中有多少出现在前 K；
- **MRR**：第一个相关来源出现得多靠前；
- **nDCG@K**：多个相关来源的排序质量；
- **no-answer false-positive rate**：无答案题是否仍错误返回证据；
- **abstention accuracy**：标注应拒答的案例是否 `abstained=true`；
- **citation support rate**：命中内容是否包含预先标注的支持词。

当前归档结果：

| 数据集 | 数量/角色 | Recall/MRR/nDCG | 拒答/引用 | 能证明什么 |
|---|---|---|---|---|
| `rag_retrieval_cases.json` | 8 条 development，参与阈值校准 | 均为 `1.0` | no-answer FPR `0.0` | 当前规则能复现开发基线；不能作为独立泛化成绩 |
| `rag_v1_holdout_cases.json` | 7 条 held-out，声明 calibration excluded | 均为 `1.0` | FPR `0.0`，abstention/citation support `1.0` | 独立门禁机制可运行，当前小集合通过；不能外推大规模、多版本或完整语义引用 |

“citation support=1.0”只是确定性支持词包含检查，不等于逐条自然语言 Claim 都被证据完整蕴含。

## 6. 需求到源码、测试、CI 和限制

| 要求 | 源码 | 测试/评测 | 公共证据 | 当前限制 |
|---|---|---|---|---|
| 来源与版本元数据 | `models.py`、`documents.py`、`data/rag_docs` front matter | `test_rag_documents.py` | RAG v1 历史提交 `d55f137` 至 `27f1fe5`；当前 CI持续回归 | 只有少量手工知识文档；更新/回滚流程未自动化 |
| 父子块 | `documents.py`、`hybrid.py` | 文档和 hybrid tests | 当前 pytest job | H2/段落规则适合当前 Markdown，不是通用文档解析器 |
| BM25 + 可替换 Dense | `bm25.py`、`embedding.py` | BM25/embedding tests | 当前 pytest job | 默认 Hashing 不是语义模型 |
| RRF 与 embedding 降级 | `hybrid.py` | `test_rag_embedding_hybrid.py` | 当前 pytest job | 单进程内存索引；没有大规模延迟/内存基线 |
| 证据支持、版本和冲突 | `policy.py` | `test_rag_evidence_policy.py` | 当前 pytest job | 阈值由小开发集校准；没有模型语义重排 |
| 正常拒答与系统故障分离 | `KnowledgeSearchResult`、policy、Tool adapter | 合同/政策/工具 tests | CI development + holdout gate | 拒答只针对当前库和规则，不保证所有域外问题 |
| chunk 级引用进入 Harness | `app/harness/knowledge.py`、runtime | Harness adapter/runtime tests | Harness dry-run + pytest | 当前只确定性验证 ID 是否存在；完整语义忠实度仍需更强 Eval |
| 独立 4M 数据生命周期 | holdout JSON、`evaluation.py`、CLI | `--require-independent` 和数据集测试 | `33f4bcd` 建立门禁；当前 CI每次执行 | `calibration_excluded` 是维护声明，不是系统自动证明 |
| RAG 故障安全降级 | Tool Runtime + ReviewHarness | Tool/Harness fault tests | 当前 CI | 降级报告没有外部知识增强，不应伪装成完整 Coach 质量 |

最新已知完整公共基线 `0c13a58` / Actions `32301852042` 的 pytest job 仍执行两套 RAG
门禁并通过。这个 run 主要关闭 6B-2，但全量门确保阶段 4 没有回归；它不是一项新的大规模
RAG 实验。

## 7. 可重复运行

### 7.1 查询本地知识库

```powershell
.\.venv\Scripts\python.exe scripts\query_rag.py `
  "输局视野分和经济下降应该怎样复盘" `
  --top-k 3
```

这会读取本地 Markdown 并使用默认 Hashing Embedding，不调用真实 LLM 或外部向量服务。输出中的
`diagnostics` 能解释候选、过滤、支持和拒答原因。

### 7.2 复现 development 门

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py `
  --provider hybrid `
  --output tmp\rag-v1-development.json `
  --min-recall 1.0 `
  --min-mrr 1.0 `
  --min-ndcg 1.0 `
  --max-no-answer-fpr 0.0
```

### 7.3 复现 independent holdout 门

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag_retrieval.py `
  --provider hybrid `
  --cases data\evaluation\rag_v1_holdout_cases.json `
  --require-independent `
  --output tmp\rag-v1-holdout.json `
  --min-recall 1.0 `
  --min-mrr 1.0 `
  --min-ndcg 1.0 `
  --max-no-answer-fpr 0.0 `
  --min-abstention-accuracy 1.0 `
  --min-citation-support 1.0
```

### 7.4 聚焦代码测试

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_rag_documents.py `
  tests/test_rag_bm25.py `
  tests/test_rag_embedding_hybrid.py `
  tests/test_rag_evidence_policy.py `
  tests/test_rag_contracts_and_evaluation.py `
  tests/test_riftcoach_tool_adapters.py `
  tests/test_harness_adapters.py `
  -q
```

上述命令均可无 API Key 运行。评测输出写到 `tmp/`，避免覆盖仓库已归档基线。

## 8. 失败、安全和范围边界

- front matter 非法、知识目录不存在或语料无有效子块时，索引构建应显式失败，不静默使用坏知识；
- Dense 检索异常时可配置退回 BM25，并在 hit attributes 中标记 `embedding_fallback`；若禁止
  fallback，则异常向上交给 Tool/Harness 故障路径；
- “正常没证据”返回成功的 `abstained=true`；基础设施/Schema 错误返回工具失败，二者不能混淆；
- 同一 `knowledge_key` 中优先适用版本和更新时间；最高优先级正文冲突时该 key 不进入上下文；
- 用户文本、知识正文和检索结果都是 data-only，不因包含指令文字而获得工具权限；完整 Prompt
  Injection 防护还依赖阶段 5 Context/Evaluation，RAG v1 本身不能单独解决；
- Harness 分配 citation ID 并拒绝未知 ID，但“存在这个 ID”不自动证明模型句子被该证据完整支持；
- 本地知识文件是项目维护内容；未来外部 MCP/网页内容必须经过来源、版本、Schema 和不可信内容边界；
- 当前无知识库热更新、原子索引发布、版本回滚和污染恢复流程，不能称为生产知识平台；
- 当前无真实语义 Embedding、多租户向量隔离、大规模并发、在线重排或 Agentic Retrieval；
- RAG 保存外部可复用知识，不保存玩家私人 Memory，也不替代 Riot 比赛事实数据库。

## 9. 面试时可以和不可以怎样说

可以准确表述：

> 我实现了轻量、Provider-neutral 的本地 RAG：Markdown 元数据和父子块负责来源与上下文，
> BM25 与可替换 Dense 通道通过 RRF 融合，确定性 Evidence Policy 处理版本、位置、有效期、
> 冲突、支持阈值和来源多样性。检索结果经 Tool Runtime 进入 Harness，系统分配 chunk 级
> citation ID 并在发布前阻止未知引用。评测区分参与校准的 development 和独立 holdout，
> 同时记录拒答与引用支持信号。

如果被问为什么没有直接上向量数据库：

> 当时只有少量知识文档，没有规模、并发或持久向量检索 Bad Case。先用统一
> `KnowledgeProvider` 和可重复门禁验证检索语义，未来替换 Embedding 或存储时不需要改
> Agent/Harness；这比先承担 Milvus/Elasticsearch/Neo4j 运维更符合证据驱动。

不可以说：

- “Hashing Embedding 是语义大模型”；
- “RAG 在所有问题上准确率 100%”；当前只有 8 条 development 和 7 条 holdout；
- “citation support 1.0 等于所有生成 Claim 都有严格语义蕴含”；
- “已经实现 LLM 查询改写、cross-encoder 重排或 Agentic Retrieval”；
- “已经有生产级向量数据库、热更新和回滚”；
- “RAG 可以替代玩家 Memory 或 Riot 事实层”；
- “RAG 通过就说明最终 Coach 报告质量通过”；报告仍需 Agent/Provider 和独立 Harness 评测。

一句话总结阶段 4：**RAG v1 的价值不是堆向量数据库，而是把知识变成有来源、有适用性、
可拒答、可引用、可评测的证据接口。**
