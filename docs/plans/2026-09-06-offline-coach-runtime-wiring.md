# RQ-245：产品 Coach 执行组合离线接线

目标：新报告/查询/用量规则通过实际产品 Runtime 产出一致的报告、Evidence 和 Trace，默认入口不变。
方案：依 ADR-0098 给已有工厂、请求编译、身份快照增加显式合同；复用现有 Agent/Harness 和 Provider。
技术：现有 Python/Pydantic、Skill/Prompt Program、LocalHybrid RAG；零真实 API。

1. 新增 app/runtime/coach_contract.py 与 coach_budget.py；冻结显式组合身份、逐请求64000输入/4096输出、九调用612864墙与45/90/360时间语义。
2. 接线 app/runtime/runtime.py、composition.py、models.py、observed_provider.py 及 app/product/recent_review.py；
   通过同一合同选择请求策略、Context、检索、初稿guard、修订提示、来源下限/回退以及 Trace 身份；旧参数默认None。
3. 在 examples/runtime_profiles/flash_v2 下提供 Skill0.3/程序2.0 独立资产；显式 resolver 重建合同指纹，普通目录不变。
4. tests/test_offline_coach_runtime.py 覆盖产品编译→真实Runtime→报告/Evidence/Trace、三主题、修订、缺来源/未知引用、
   错合同/漂移、预算/超时、长玩家数据/Memory 和 Worker 所有权丢失；至少一项经真实Zhipu适配器与假SDK检验low/replay参数。
5. 聚焦/相邻测试、编译、diff/governance、同SHA公共CI；所有不完整证据明确记录，不将离线结果称为真实模型准入。

可复现入口：python -m pytest tests/test_offline_coach_runtime.py -q。
下一步只有在本批实现公共闭环后，才进入新产品版本的真实验收准备；不重跑旧考卷、不直接打开默认。
学习说明与实际结果见下，作为八维证据，不另起重复教程。

## 实现与离线证据（本地及公共完成）

实现 `cecde250e131a0e81585e2e91ec261fad6817700` 的
[Actions 34026629061](https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/34026629061)
已核对 headSha，pytest、postgres-migrations、packaging-smoke 均 completed/success。
本批已完成，无待执行真实调用；唯一下一步为新产品版本独立真实验收准备，绑定本次真实产品执行组合与
全新验收身份，不能用旧领域回执或本地脚本95分冒充它通过。生产目标档案注册、默认启用与真实质量仍在后面。

执行组合 `recent-form-review-flash-v2@1.0.0` 为 `unadmitted_opt_in`；policy 1.2.0，Skill 0.3.0，
程序 2.0.0；组合摘要 `968c8dc8e2d745ed82bb4cdc1486bde0388d6782603bd833abdba067701e35d1`，
程序摘要 `8b20a492f648ab1ee7e0be9b214fa3affdf3531a01a8ca48c650dd367ec128f4`。
实际调用低思考/4096/保留思考回传；普通 max/2048 档案与 GLM-5.2 disabled-thinking 兼容配置不变。
两种 runtime_profile 字段保持 None，实际未准入组合在 identity/policy 同值存储；旧 JSON 不新增 null 字段。
独立程序指纹重建包括同一组合与完整请求策略；丢失可信 Context、跨 owner Memory、漂移或无从核验的 SDK retries 会被拒绝。

新增测试33项通过；相邻两组共271项通过（178+93），共304个不同用例、27 subtests。
其中三主题各完成五次脚本调用：检索→初稿→70分初评→修订→95分复评并发布；
另三主题各走九次满额模拟 Usage 路径，含三轮检索、两次评测格式修复、一次修订，最终80分按原门槛拒绝。
这些分数是测试预设，不是新增真实模型评分。缺来源/未知引用/缺标题/质量拒绝均不发布，不用确定性回退兜成成功。
真实 ZhipuProvider 经假 SDK 验证五个请求的 low、clear_thinking=false、4096、45秒上限和工具回合 reasoning replay；
Trace 不含推理或报告正文。Worker→Application→真实 Runtime→本地不可变证据核验可完成；失去租约时不提交成功终态。

Memory 测试用真实 MemoryAwareContextBuilder，内层 CoachContextBuilder 继承现有 ContextBuilderV1；
短偏好只在 user 数据段，15017字符长记录整条省略，跨 owner 快照拒绝。必需玩家输入超限时在 Provider 调用前拒绝。
九调用产品路径可达；每请求完整请求包（含工具/结构化参数/已发生的思考回放）重新估算，最大输入估算64000，
输出4096；所以最多九次预留不超过612864。此数字是受控上限而非典型消耗、供应商精确计费或任意输入成功保证。
实际 Usage 若超过估算包络则停止；不能撤销已经发生的供应商用量。SDK重试必须可核验为0，工具额外重试也为0。
推进时钟测试验证剩余10秒会压低下一请求超时、超360秒返回不被接受；运行失败只发一次不重试。
这不等于实测同步 SDK 可硬中断，也不保证所有非模型步骤在360秒内结束；预算计时范围是本轮执行束的模型调用链。
Worker测试使用360秒租约/60秒心跳策略；默认服务器启动代码、数据库并发实现、UI/Auth/路由均未修改。

## 八维学习与操作说明

1. 问题与原理：开发探针成功不代表产品执行了相同规则。要把策略放进现有产品工厂，验证每次调用和最终文件，不能只比较模型名。
2. 设计与实现：显式传入单一可信组合，建立独立资产目录，默认不选新路径；复用 Agent、Harness、检索和租约，不复制一套产品引擎。ADR-0098 记录替代方案与取舍。
3. 代码地图：`app/runtime/coach_contract.py` 管身份；`coach_context.py` 管 Memory 兼容可信指引；`coach_budget.py` 管调用预留/结算。`runtime.py`、`composition.py` 接线；`app/product/recent_review.py` 编译；`app/prompt_program/resolver.py` 验证程序；`app/providers/zhipu.py` 只增加可读 SDK 重试投影。
4. 数据与控制流：产品请求→编译/版本验证→Memory与可信Context→知识工具→初稿→质量评测/一次修订→报告/Evidence/Trace→收据→Worker核验所有权并提交。模型输入、公开Trace、任务可见状态是不同层，不能互相冒充。
5. 验证：`tests/test_offline_coach_runtime.py` 的 socket 禁网夹具覆盖全部33项；相邻测试覆盖旧Runtime/程序/5.2/Flash默认、应用、Worker、Memory、报告预算和智谱适配器。学习覆盖完整，但整个8E仍在进行。
6. 运行手册：在隔离树使用 Python3.11 运行 `python -m pytest tests/test_offline_coach_runtime.py -q`；无需Key/数据库/服务器。调用方用新资产目录和 COACH_CONTRACT 创建组合，注入假Provider，再使用现有请求编译和runtime.run；不要把生产启动目录指到示例资产，也不要据此直接建真实付费客户端。
7. 失败/安全/边界：模型失败、来源/格式不足按现有安全终态处理；错误合同/SDK重试不明在调用前拒绝。保留GLM-5.2、所有旧结果；没有真实API、生产注册、默认启用、完整黄金切片或前端变更。所有权丢失禁止提交用户可见成功，但本地诊断/报告文件可能已生成。
8. 面试表述：可以说“把候选教练规则显式接入产品运行时，并以禁网端到端测试验证版本、证据、资源与任务所有权一致”；不能说“GLM真实领域全通过、公共产品已发布或8E已完成”。持久材料已提供，不代表用户理解已验收；参考资料审计和公共部署成熟度不因离线测试提升。
