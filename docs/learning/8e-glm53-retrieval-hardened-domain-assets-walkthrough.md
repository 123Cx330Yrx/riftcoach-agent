# RQ-237：检索加固领域资产实现 walkthrough

## 问题与原则

RQ-235 的真实领域首案在 Provider 和工具调用成功后仍因检索零片段触发
`evidence_required`。RQ-236 的 `coaching-query-recovery-v1` 只允许单一安全教练主题
在零命中且原因为 `insufficient_evidence` 时补查一次；本批把该策略绑定到全新、候选专用
V3 领域资产，不重跑旧考卷，也不降低事实、引用、注入、来源或 85 分门槛。

## 实现地图与数据流

- `app/evaluation/glm53_retrieval_hardened_domain_v3_assets.py` 负责协议、Dataset、输入计划、
  Context、预算证明和 fixture 的 SHA 交叉校验，并拒绝历史 RQ-227/V2 身份复用。
- `app/evaluation/glm53_retrieval_hardened_domain_v3_gate.py` 是候选隔离门控入口；在 Provider
  构造前要求 exact-SHA 公共 CI 与新鲜 G53-3-L 证据，并要求执行器显式开启检索加固。
- `data/evaluation/glm53_flash_retrieval_hardened_*` 保存新 Dataset、输入计划、协议和预算；
  `data/evaluation/contracts/glm53_flash_retrieval_hardened_context_v3.json` 保存 body-free
  Context 身份；两份新 fixture 只用于离线重建。

运行顺序是：冻结输入 → 重建 Context → 验证预算包络（每案 9 次/203000 token、全域 27 次/
608000 token）→ no-I/O 资产准入 → 公共 CI → 新鲜 G53-3-L → 另行授权的真实领域观察。

## 验证与边界

本批聚焦测试 5 passed，compileall、`git diff --check` 和 governance 通过；Provider calls=0。
准入回执只含版本、SHA、case ID、固定 marker 摘要和资源上界，不含查询正文、答案、reasoning、
工具参数、注入文本或凭据。候选未注册、生产准入仍为 false；默认 Runtime、GLM-5.2 回退、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均未改变。下一步是同一实现 SHA
的公共 CI，之后才可建立新鲜 G53-3-L，不自动发送真实请求。

## 面试表述

“我没有把一次检索失败改成放宽门槛，而是把恢复策略版本化并绑定到全新 held-out 资产：先用
原查询，再对单一安全主题最多补查一次，同时把旧证据隔离、预算可达性和 body-free 诊断作为
进入真实验证的前置条件。”
