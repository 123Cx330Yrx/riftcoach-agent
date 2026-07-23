# RAG v1：现状审计与检索基线

## 1. 为什么先评测再升级

RAG 的目标不是部署向量数据库，而是为 Coach 提供相关、可追踪、适用于当前问题的知识证据。没有固定评测集时，更换切片、Embedding 或存储后只能凭主观感受判断效果。

阶段 4 因此先固定：

```text
知识库版本
→ 测试问题
→ 标准相关来源
→ 检索结果
→ Recall@K / MRR / nDCG / 无答案误召回率
```

## 2. RAG v0.1 的真实实现

当前 `LocalKnowledgeRetriever`：

1. 读取 `data/rag_docs/*.md`；
2. 遇到 Markdown 标题时切成一个块；
3. 中文生成单字和连续二元词，英文保留 token；
4. 使用简化 TF-IDF 词法分数排序；
5. 返回来源文件、章节标题、正文和分数。

它不是向量检索，也没有调用大模型。优点是本地、确定、零额外服务；缺点是同义表达召回弱，并且缺少正式元数据和拒答阈值。

## 3. 当前调用链

```text
Harness LocalRagAdapter
→ Tool Runtime: knowledge.search
→ knowledge tool adapter
→ LocalKnowledgeRetriever
→ KnowledgeChunk
→ 格式化为 Coach 上下文
```

阶段 3 已经把 Tool Runtime 边界固定，因此 RAG v1 可以替换内部 Provider，而不需要重写 Harness 生命周期。

## 4. 当前缺口

- 来源只有文件名和标题，没有知识类型、版本、更新时间或适用位置；
- chunk 没有稳定 ID 和父块；
- Markdown 标题切分不控制块长度；
- 只有词法召回，没有语义召回；
- 没有去重、融合或重排；
- 分数没有可解释阈值，库外问题仍可能误召回；
- Harness 只保留来源文件名，不能引用具体 chunk；
- 原测试只证明一个示例能命中，不衡量整体检索质量。

## 5. 新增 KnowledgeProvider 契约

RAG v1 使用：

```text
KnowledgeQuery
→ KnowledgeProvider.search()
→ KnowledgeSearchResult
→ KnowledgeHit[]
```

每个 `KnowledgeHit` 必须包含：

- `chunk_id`；
- 可选 `parent_id`；
- 正文、分数与排名；
- `source_id` 和标题；
- 知识类型、版本、更新时间、适用位置等元数据。

`LegacyLocalKnowledgeProvider` 暂时把旧检索器适配到新契约，确保升级不是推翻重写。

## 6. 基线指标

- **Recall@K**：标准相关来源中，有多少进入前 K 条；
- **MRR**：第一个正确来源排得多靠前；
- **nDCG@K**：多个相关来源的排序质量；
- **无答案误召回率**：知识库不覆盖的问题是否仍返回内容。

当前第一版评测采用来源级标注。它适合判断文档是否召回，不足以判断具体段落和引用是否正确。阶段后续会升级到 chunk 级标注与引用评测。

运行：

```powershell
python scripts\evaluate_rag_retrieval.py
```

结果写入 `data/evaluation/results/`，用于后续 BM25、Embedding 和融合实验对比。

## 7. 这一步没有做什么

- 没有部署 Chroma、Milvus、Elasticsearch 或 Neo4j；
- 没有引入 Embedding；
- 没有把词法检索包装成“语义 RAG”；
- 没有完成无答案拒答，只是先测量问题；
- 没有实现最终报告的 chunk 级引用。

这些边界保证后续每项增强都能单独验证。
