# 2026-10-12 修正后的温度筛查控制候选

## 用途

这是免费准备清单，不授权 Provider 调用，不修改生产入口，也不重开 r2。它把历史语义结果与控制标签重新绑定，供下一次是否值得筛查的决策使用。

## 候选控制

| 控制 | 类型 | 历史结果 | 报告 SHA256 | 来源封存 |
| --- | --- | --- | --- | --- |
| `claim-scope:1` initial | 正确稿 | pass / semantic_accepted=true | `0a07162210fa087073bb8bf881ff883e910b4df57623e7c301e86b3ccc168498` | full15 `30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576` |
| `observed:3` final | 正确稿 | pass / semantic_accepted=true | `9da8654b8b992f018aae3f5b955f34297140d86d5e38ba5154016867f205707e` | remaining4 `a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec` |
| `observed:4` final | 正确稿 | pass / semantic_accepted=true | `211b2891e7583718dd28c389dba0372c46b4254e1909276ec9d2dab5a4bcffac` | remaining4 `a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec` |
| `claim-scope:4` initial | 真错稿 | needs_revision / host rejected | `2f642924110e98975b7d82baa49f43e039d2876b088e33a861398261354734c2` | full15 `30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576` |
| `scope:4` initial | 真错稿 | needs_revision / host rejected | `a3889a655782132f269f1a4cda7b0506e242dbd783df17d03740f01b1d1b3ba4` | full15 `30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576` |

历史结果来自两个只读封存的 `execution_result.cases` 及其绑定；原件未修改。 离线核验产物为 `data/evaluation/results/corrected_temperature_control_candidate_audit_20261012.json`，SHA256 `232b463f81ac69248e4f6b35d2e0fdb9fdbd45ec25b24600ba189015c9552c39`，五行标签、报告绑定、stage/request/source 存在性全部通过。每个新候选请求仍须重新生成自己的 request/receipt SHA，不能复用上表历史 request 或 response。

## 离线接缝结果

把上述五例注入现有 `scripts.document_sampling_screening.controls()` 的只读构造后，10 个请求（每例 baseline 与 temperature-02）全部重建成功；请求角色顺序、完整来源、policy、工具 schema、温度 `[1.0, 0.2]` 和候选 marker 均按现有身份规则生成。该检查没有构造网络客户端、读取凭据或写入 run，也没有证明 Provider 接受参数或改善语义。

## 保留的限制

这组控制涵盖三份已接受正确稿和两份已拒绝真错稿，但初评与 final 混合、来源封存不同，不能直接证明温度因果或完整15质量。真实筛查前仍需重新绑定完整 source/material、当前 policy、候选 marker、原生双审和硬故障停止规则。任何协议、身份、来源、native 或预算硬故障都停止新批；旧 r2 不重开、不补发、不重评。

在没有新的明确成本授权前，不发送 Provider。
