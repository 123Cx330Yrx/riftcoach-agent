# 2026-10-12 温度筛查控制集审计

## 结论

有界温度筛查 r2 的控制标签不能继续沿用。抽样计划的五个样本与历史封存结果逐项对照后，两个预设为 `accept` 的样本实际没有资格作为正确控制；只有一个 `accept` 样本和两个 `reject` 样本与历史语义结果一致。r2 因协议硬停止而未完成候选效果判断，这次免费审计进一步证明原控制集本身不足以支撑下一批。

| r2 样本 | 预设 | 历史封存语义结果 | 控制判断 |
| --- | --- | --- | --- |
| `claim-scope:4` initial | accept | `semantic_accepted=false`, `needs_revision` | 错误标签；保留为真错候选 |
| `scope:3` final | accept | `semantic_accepted=false`, `final_verdict=needs_revision` | 错误标签；不能作为正确稿 |
| `scope:4` initial | reject | `semantic_accepted=false`, `needs_revision` | 一致的真错候选 |
| `observed:3` final | accept | `semantic_accepted=true`, `final_verdict=pass` | 当前唯一有历史支持的正确控制 |
| `observed:5` initial | reject | `semantic_accepted=true` 的原案但初评 `needs_revision` | 作为初评需修控制，与 reject 预期一致 |

来源是 `data/evaluation/results/golden_document_full15_time600_result_20261010.json` 和 `data/evaluation/results/golden_document_remaining4_time600_result_20261011.json`；只读读取，未修改封存或旧结果。

## 决策

停止把 r2 的 `accept` 预设当作事实。不能基于这五例继续购买温度筛查，也不能把 sample-2 的 r2 双审通过解释为原报告正确；它只证明那次审查意见本身通过了当前审查门。后续若仍要区分采样变量，必须重新建立有真实历史或独立全文核验支持的正反控制，并把控制标签与实际报告语义分开记录；控制集未重建前不发 Provider。

旧 r2、历史 2/15、3/15、remaining11、后8、后4和正式15仍彼此独立，原件不改，新资格为 0。
