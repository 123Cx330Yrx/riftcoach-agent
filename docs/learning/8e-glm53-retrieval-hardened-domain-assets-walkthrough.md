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

运行顺序是：冻结输入 → 重建 Context → 验证预算包络（每案 9 次/205000 token、全域 27 次/
613000 token）→ no-I/O 资产准入 → 公共 CI → 新鲜 G53-3-L → 另行授权的真实领域观察。

## 验证与边界

本批资产与门控聚焦测试 21 passed（含策略漂移、质量门削弱、历史身份、运行时篡改和完整离线门控），
相邻回归合计 83 passed；compileall、`git diff --check` 和 governance 通过；Provider calls=0。
准入回执只含版本、SHA、case ID、固定 marker 摘要和资源上界，不含查询正文、答案、reasoning、
工具参数、注入文本或凭据。候选未注册、生产准入仍为 false；默认 Runtime、GLM-5.2 回退、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均未改变。下一步是同一实现 SHA
的公共 CI，之后才可建立新鲜 G53-3-L，不自动发送真实请求。

## 面试表述

### 开发验证补充

`tests/test_coaching_retrieval_development_chain.py` 使用 demo 数据和14个脚本查询驱动真实本地检索、
真实执行器及文件证据链；通过摘要校验读取持久Evidence，确认来源文件存在、引用K1确实绑定来源，
并读取完整七段最终报告。另有三例零来源拒绝、一例70分拒绝和三例混合/注入不扩展，共21项。
包含相邻版本/回执测试共112项通过。测试替身的95分不是模型质量评分。

运行：`pytest -q tests/test_coaching_retrieval_development_chain.py`。网络连接在测试中禁止，产物只在
pytest临时目录。未使用旧held-out问题；不改前端、默认模型或GLM-5.2回退。失败应定位在查询、工具、
证据文件或发布层，而不能从零来源猜测实际查询原文。下一步仍要验证模型自主查询，不能宣称生产准入。

可准确表述为“我验证了可控模型输出与真实检索证据链的集成，明确区分工程通过和模型质量证据”。

### 自主查询开发观察01

探针 `scripts/probe_glm53_development_retrieval.py` 只用匿名demo，调用真实GLM和原执行器；不指定
工具查询，也不提供固定评分。先保留pending回执，再读取用户明确选择的.env，结果只投影安全字段。
脚本绑定自身SHA与已提交生产代码SHA，临时完整工件随正常退出清除；本地探针不冒充公共CI。

运行入口需显式--confirm-real-call、--implementation-sha、--env-file和--output；最多9次模型调用、
205000 Token、零SDK重试。本次2次调用、6861 Token；GLM提出两条59/65字符查询，检索都未取到来源，
Harness在评分前拒绝。看queries主题/长度与observation终态定位层次，不从摘要猜原文。

本次只证明开发样本的自主查询仍存在检索适配差距。下一步验证开发专用可信语料/查询指引，
不降低检索门或伪造来源，不修改旧正式结果。可表述为“真实开发观察用于定位问题，不与held-out准入混用”。

“我没有把一次检索失败改成放宽门槛，而是把恢复策略版本化并绑定到全新 held-out 资产：先用
原查询，再对单一安全主题最多补查一次，同时把旧证据隔离、预算可达性和 body-free 诊断作为
进入真实验证的前置条件。”
