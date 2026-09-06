# RQ-239：带查询指引的新候选领域资产设计计划

## 目标

为 GLM-5.3 Flash 建立与 RQ-237 隔离的新鲜领域验证资产，验证候选 Context 是否能稳定携带
`coaching-query-guidance-v1`，并保留现有来源、安全、事实和 85 分质量门。

## 执行批次

1. 设计新的四案例 Dataset、输入计划、Context 快照、协议、marker、预算和回执身份；重建新匿名 fixture，
   做旧 RQ-227/230/235/237 的 case/run/utterance/marker/fixture 排重。
2. 实现 no-I/O 资产准入，检查快照中确实包含指引摘要、输入计划逐案承诺与候选策略；运行最坏路径预算证明。
3. 加入聚焦测试和公共 CI；同 SHA 获取新鲜 G53-3-L 后，才执行一次真实领域观察。

当前进度：四个新案例的稳定身份和排重校验已落到 `app/evaluation/glm53_guided_candidate.py`；
V4 Dataset、fixture、Context、Input Plan、预算证明、协议和 no-I/O 准入已在同一实现批中完成，
聚焦测试通过，未进行真实 Provider 调用；提交 `53555f7` 的公共 CI `34013138068` 三项全绿，
当前等待绑定该 SHA 的新鲜 G53-3-L 协议证据。
新鲜协议观察已完成：3 次真实调用、`admitted=true`、1116 tokens、13765ms；回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_guided_g53_3l_rq239_v1.json`。
四案例领域运行器已接入并完成一次真实观察；首案在评测阶段以 `evaluation_failed` fail-closed，后三案跳过，协议通过不等于领域或生产准入。下一步是归因并修复评测响应接线。

## 验收

资产身份、预算、Context 和协议全部可重建；候选入口在漂移/旧资产/指引身份不一致时于 Provider 调用前拒绝；
旧资产测试保持通过。真实领域回执只保存枚举、计数、SHA 和终态，不保存问题正文、答案、reasoning、工具参数或凭据。

## 非目标

不把 RQ-238 单样本结果升级成正式准入，不改默认模型或产品 Runtime，不修改前端，不重跑任何已消费考卷，
不新增模型依赖或放宽现有质量门。
