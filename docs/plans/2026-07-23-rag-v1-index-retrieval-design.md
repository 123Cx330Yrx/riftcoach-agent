# RAG v1 第二批设计：结构化索引与混合召回

- 日期：2026-07-23
- 范围：阶段 4 Task 4–6
- 前置：`KnowledgeProvider` 契约和 v0.1 检索基线已完成

## 1. 目标与非目标

本批目标是把“Markdown 标题切块 + 简化 TF-IDF”升级为可替换的本地检索核心：

```text
带元数据 Markdown
→ 结构化解析
→ 父块与子块
→ BM25 词法召回
→ Embedding 召回
→ RRF 混合融合
→ KnowledgeSearchResult
```

本批不实现最终拒答阈值、版本冲突、过期策略、重排器、Harness chunk 引用和在线向量服务。这些属于 Task 7–8。

## 2. 方案比较

### 方案 A：直接使用 Chroma 与 sentence-transformers

优点是向量存储和语义模型现成；缺点是模型下载、Torch 依赖、CI 体积与部署复杂度会显著上升。在四篇短文阶段，基础设施成本超过业务收益。

### 方案 B：直接采用 Saber 的 Milvus + Elasticsearch

优点是接近生产级混合检索；缺点是需要多个外部服务，调试重点会从检索质量转向部署。当前也没有规模或并发证据支持这一选择。

### 方案 C：本地可替换索引（采用）

使用标准库实现结构化索引和 BM25，定义 `EmbeddingProvider`，用确定性 hashing embedding 验证向量检索与融合链路。未来可以替换为智谱 Embedding、本地模型或向量数据库，而不改变 `KnowledgeProvider` 和 Harness。

## 3. 文档与父子块

Markdown 文件增加受限 front matter：

```yaml
---
source_id: metric_interpretation
knowledge_type: coaching_rule
version: evergreen
updated_at: 2026-07-23
positions: ALL
---
```

解析器不引入完整 YAML 依赖，只支持本项目需要的标量和逗号分隔列表，并对日期、必填字段和未知结构显式报错。

切分规则：

- H1 定义文档标题；
- H2 章节形成父块，保留完整章节上下文；
- 父块按段落和长度形成多个子块；
- 子块负责召回，命中后返回父块作为生成上下文；
- 父块、子块 ID 由来源、标题和内容摘要稳定生成。

这避免“小块召回准确但上下文残缺”和“大块上下文完整但匹配不精确”的矛盾。

## 4. BM25 与 Embedding

BM25 相比当前简化 TF-IDF 增加：

- 文档长度归一化；
- 词频饱和，避免重复词无限加分；
- `k1` 与 `b` 参数控制。

Embedding 使用协议：

```text
EmbeddingProvider.embed(texts) → vectors
```

首个 `HashingEmbeddingProvider` 把 token 稳定映射到固定维度并归一化。它是可复现的稠密向量基线，不声称理解同义词；其价值是先验证批量向量化、余弦相似度、索引和替换边界。

## 5. 混合融合

BM25 和向量分数不在同一量纲，不能直接相加。本批使用 Reciprocal Rank Fusion：

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

RRF 只使用各召回器的排名，因此不依赖厂商分数尺度。融合结果保留各通道排名和分数，方便后续 Trace 与评测。

## 6. 错误与降级

- front matter 非法：索引构建失败并指出安全文件名，不静默吞掉；
- 单篇文档无有效章节：跳过该文档，但空知识库整体失败；
- Embedding Provider 失败：混合 Provider 可配置降级到 BM25；
- 查询为空或 `top_k` 越界：由 `KnowledgeQuery` 拒绝；
- 本批不根据任意分数自动拒答，避免未经评测设定阈值。

## 7. 测试与完成标准

- front matter、标题层级、稳定 ID 和父子回填单元测试；
- BM25 对长度与相关词排序的测试；
- Embedding 维度、归一化和确定性测试；
- RRF 跨通道融合与 Embedding 降级测试；
- 固定八题基线可运行，并记录新 Provider 的结果；
- 全量测试和 Harness dry-run 不回归。

## 8. 与参考项目的关系

本批吸收 Saber 的父子块、混合召回和 RRF 思想，但索引、契约、测试和轻量降级由 RiftCoach 自主实现。EchoMind 的查询改写与重排思想留到 Task 7；Sea 的 Artifact/质量门控仍由阶段 2 Harness 承担。
