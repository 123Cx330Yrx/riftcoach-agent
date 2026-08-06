# RAG 4M：独立评测门禁

## 目标

阶段 4 的开发集已经验证了当前本地混合检索链路可以稳定复现，但开发集同时参与了证据阈值校准，不能直接作为泛化结论。4M 增加一个明确标记为 `held_out` 的保留集，并把它接入 CI 门禁。

这一步不改 BM25、Embedding、RRF 或证据策略算法，也不引入向量数据库。它只提高评测证据的可信度。

## 数据集边界

`data/evaluation/rag_retrieval_cases.json` 保持为开发/回归集，兼容旧命令。

`data/evaluation/rag_v1_holdout_cases.json` 是独立保留集，包含：

- 未参与初始阈值校准的改写问题；
- 无答案问题；
- 版本/位置过滤问题；
- 需要检查证据文本是否真正支持标注语义的案例。

数据集声明：

```json
{
  "dataset_version": "rag-v1-4m-holdout-1.0.0",
  "role": "held_out",
  "calibration_excluded": true
}
```

`calibration_excluded` 不是模型自动证明的事实，而是维护者对数据集生命周期的声明。修改保留集或使用它调阈值时，必须升级数据集版本并重新说明污染边界。

## 新增评测信号

- `abstention_accuracy`：标注为无答案的查询是否真的返回 `abstained=true`；
- `citation_support_rate`：返回的相关证据块是否包含案例预先标注的支持词；
- 每个结果记录数据集版本、角色、分割名、案例类别和是否 abstain。

引用支持检查是确定性的词语包含检查，不等同于完整的自然语言 Claim-to-Evidence 语义评测。后续可以在独立标注数据足够后替换为更强的人工或模型辅助评测，但不能把当前指标称为完整引用正确率。

## 运行

开发/回归集：

```powershell
python scripts\evaluate_rag_retrieval.py --provider hybrid
```

独立保留集：

```powershell
python scripts\evaluate_rag_retrieval.py `
  --provider hybrid `
  --cases data\evaluation\rag_v1_holdout_cases.json `
  --require-independent `
  --min-recall 1.0 `
  --min-mrr 1.0 `
  --min-ndcg 1.0 `
  --max-no-answer-fpr 0.0 `
  --min-abstention-accuracy 1.0 `
  --min-citation-support 1.0
```

## 当前结果与限制

当前 7 个保留案例的本地 hashing embedding / BM25 混合基线结果为：

```text
Recall@K                 1.0000
MRR                      1.0000
nDCG@K                   1.0000
无答案误召回率          0.0000
Abstention accuracy      1.0000
Citation support rate    1.0000
```

这只能证明当前小型保留集可复现通过。它不代表 RAG 已经具备大规模语义泛化能力，也不证明 hashing embedding 等同于真实语义模型。后续应继续扩充按知识类型、版本和位置分层的独立样本。
