# RAG v1 收尾设计：证据策略、引用与 Harness 接入

- 日期：2026-07-24
- 范围：阶段 4 Task 7–8
- 前置：父子块、BM25、Embedding 接口与 RRF 已完成

## 1. 当前问题

混合基线保持了相关来源召回，但仍有两个明确缺口：

```text
同一来源多个章节挤占前 K
库外问题误召回率为 100%
```

此外，Harness 当前只保存来源文件名，不能追踪具体 chunk、版本和拒答原因。

## 2. 证据策略

RRF 只表达多个召回通道中的相对排名，不能作为绝对相关度。初始证据门控使用：

- BM25 分数；
- 查询信息词覆盖率；
- 位置、版本和有效期；
- 同一来源最大返回数量；
- 同一知识键的版本优先级与冲突检测。

阈值根据当前八题合成集初步校准。它是开发基线，不是生产统计结论；后续必须增加独立保留集，避免对当前题目过拟合。

## 3. 去重与重排顺序

```text
RRF 候选
→ 适用性过滤
→ 证据支持门控
→ knowledge_key 冲突处理
→ 确定性证据重排
→ 来源多样性约束
→ top_k
```

确定性重排综合查询覆盖率、BM25 排名、Dense 排名和原 RRF 排名。它不调用 LLM，因此可复现、低成本。后续可以在同一 Reranker 接口下替换为 cross-encoder 或模型精排。

## 4. 版本、过期与冲突

- `version=evergreen`：不依赖游戏版本；
- 查询指定版本时，只接受相同版本或 evergreen；
- `valid_from` 晚于查询 `as_of` 时不生效；
- `valid_until` 早于查询 `as_of` 时视为过期；
- 相同 `knowledge_key` 中优先最新更新时间；
- 同版本、同更新时间、同优先级但正文不同，视为未解决冲突，该知识键整体不进入上下文。

过滤与冲突信息写入 diagnostics，而不是静默丢弃。

## 5. 正常拒答与系统故障

```text
正常拒答：
Provider 正常运行，但没有证据通过门控
→ success=true
→ abstained=true
→ hits=[]

系统故障：
Provider/Tool 执行失败
→ success=false
→ Harness 按配置发布确定性 fallback 或拒绝
```

正常拒答不能被伪装成异常；异常也不能被伪装成“没搜到”。

## 6. Citation 契约

Harness 为每条证据生成不可由模型决定的 citation ID：

```text
[K1] → source_id / chunk_id / parent_id / title / version / updated_at
```

生成上下文直接包含 `[K1]`。`retrieval_evidence.json` 保存完整映射和 diagnostics。报告只允许使用已提供 ID；本阶段至少进行确定性引用 ID 校验，引用语义正确率仍需要后续更强评测集。

## 7. Tool Runtime 接入

`knowledge.search` 升级为 v2 契约：

- 输入：query、top_k、可选 filters；
- 输出：provider、abstained、diagnostics、结构化 chunks；
- 每个 chunk 包含稳定 ID、父块 ID、来源、版本、匹配子块和父块上下文。

正式脚本改用 `LocalHybridKnowledgeProvider`。兼容旧检索器仅保留在 legacy adapter 和回归测试中。

## 8. 完成标准

- 来源多样性改善早期死亡问题的 nDCG；
- 两个库外问题均正常 abstain；
- 版本、有效期和冲突有自动化测试；
- Harness artifact 保存 chunk 级引用；
- 非法 citation 被确定性检测；
- RAG 故障仍触发原有确定性降级；
- 全量测试、双基线、Harness dry-run 和 GitHub CI 通过。

