# 审查路线比较：保留 GLM 采用决定，不启动厂商迁移

2026-10-15。只读机制核对与官方资料比较完成；无新模型请求、无产品切换、无替代 provider 实施。
基线代码为 `5306c6bb9c781c90a40b6d4f9c5c7e5e41523e71`，当前 8E 未完成。

## 本轮决定与授权范围

用户允许“比较替代模型，优先可靠性”，随后指出 Astra 成本，并询问换厂商会否推翻此前
明确选择 GLM-5.3 后完成的适配。比较授权不等于迁移或新付费授权；既有 GLM 采用决定仍有效。
助手曾建议“先验证 Astra”，这早于成本与具体实验取舍，现撤回该执行顺序。
本文件保留备选及真实增量成本，不将任何替代型号排入发送队列，也不先实现多个适配器。

结论是：现有组合没有达到可靠采用要求；证据不足以宣称 GLM 整体不可用，也不足以宣称换厂商
就能解决。跨厂对照可以成为开发诊断选项，产品常驻迁移须另有质量、成本与接入证据。

## 零付费机制核对得到什么

- 实际生成请求已有“观摩不构成本人基线/训练证据”，completion 已明确不把观摩擅改为本人训练，
  facts 覆盖已有建议及论证。没有找到“两个职责都不负责”或确定性要求冲突。
- 七节训练章节与 K3 的训练措辞存在引导压力，但可用观察者的标注/比较任务满足；没有证据
  证明删 K3、改一句提醒或增加数字拦截器即可修好。它们仍是解释假设，不是已证根因。
- 本例双 initial pass 直接走 `candidate_initial_pass_unqualified`，未进入 `direct.preview`。
  本次失败暴露生成与检出问题，不能用来证明或否定逐字补丁效果。
- Training 已拒绝 OBSERVED 写入本人计划/进度；已有两项相关测试通过。增加相同存储拦截
  不会修正报告正文。固定报告逐字补丁与双 fresh 曾成功一次，这份有限开发证据继续保留。

依据：`app/runtime/native_coach_contract.py:18`、`scripts/review_duty_composition.py:35`、
`scripts/prepare_review_duty_probe.py:28`、`app/evaluation/natural_duty_workflow.py:90`。
已核公开完整材料 SHA `8b2343d550a402ca18c58926b8044749342fef7c1ae3126663e3f1aff37192c6`；
路径 `data/evaluation/fixtures/natural_duty_observed_review_20261015/review-evidence/material.json`。
使用其中去除私有 reasoning 的 public_value；本轮没有改原材料、标签、run、seal 或作者原件。

## 三种业务路线的取舍

| 路线 | 能回答什么 | 当前取舍 |
|---|---|---|
| 保留 GLM，调整任务表示或审查负担 | 相同模型在有依据的输入/任务变化后能否减少错误 | 保留；先说明具体机制和对照，不原样重买，也不把重复提醒当确定修法 |
| 只替换审查 provider/model profile | 固定初稿/完整来源时，另一审查组合是否检出错误且不误伤正确内容 | 可比较，未采用；生成器与产品接线不必先换 |
| 高能力模型只作开发诊断 | 故障是否至少能被另一模型在同等完整材料中识别 | 可选的一次性诊断，不是免费 Host 产品服务，不自动成为常驻模型 |

不同时更换生成器、审查、材料、职责和修订方式再声称找到了原因；不增加第三道常驻审查
来绕过原 5 次产品或已批准 6 次候选的预算。新 profile 的参数/协议差异必须公开，不能称只换权重。

## 官方能力与价格快照

以下为 2026-10-15 实际打开的官方页。价格单位为美元/百万 tokens，标准文本、无缓存优惠；
仅作方案量级比较。示例均假设 20000 输入与 4000 **计费输出** tokens，包含模型推理消耗；
不同模型实际分词和推理量不同，该示例不是本项目费用预测，也不是账单或授权额度。

| 候选 | 输入 / 输出单价 | 示例单次 | 与本任务有关的能力及取舍 |
|---|---:|---:|---|
| GPT-6 Astra | 10 / 50 | $0.40 | 1.05M 上下文、128K 输出、high；高价诊断备选，未决定首测，更未采用常驻 |
| GPT-6.1 Sol | 2 / 10 | $0.08 | 同量级上下文/输出、high；较低成本备选，不能由官方定位推出本项目可靠性接近 Astra |
| Claude Opus 5.5 | 4 / 20 | $0.16 | 1M/128K、adaptive thinking；有额外协议差异，暂不优先做接入 |
| DeepSeek-V4-Pro-0813 (`deepseek-v4-pro`) | 峰时 1.32 / 3.96 | $0.04224 | 1M、最高384K输出、thinking/high；现有 DeepSeek 边界可参考，但新版本与审查身份尚未验证 |

来源：[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)、
[Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)、
[Claude](https://platform.claude.com/docs/en/models/overview)、
[DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/)。DeepSeek 非峰时为表中一半，不按优惠预算。
Claude Fable 5.1 也查过：10/50、1M/128K，官方标为较慢；它没有缓解当前成本疑问，暂不扩大候选。
[Fable 官方页](https://platform.claude.com/docs/en/models/fable-5-1/overview)。

最新已关闭自然任务中的 GLM 两次审查共 32302 输入/4770 输出 tokens，按原合同估价为
0.391976 元；这是历史估价，不是当前官方价格或账单。不能把这些 token 数直接当新模型用量。
所有新候选的本项目语义表现、实际延迟、账户可用性及生产成本均未实测。
文档支持的结构输出不能保证意见、修法或保留判断正确；厂商榜单不作为本项目采用证据。

## 哪些已有工作保留，哪些需要新增

| 已有投入 | 替换审查端时的处理 |
|---|---|
| Runtime、工具/RAG、Memory、Training 身份边界、数据库、API、前端 | 继续复用，不整体重写；当前厂商比较不触碰它们 |
| 双职责业务政策、完整来源、逐字补丁与来源校验 | 原则上复用；任何协议转换保持业务语义并单独核对 |
| 智谱 adapter、流式 assembler、冻结 profile、历史回执 | 保留原实现与原身份；新增厂商不能冒充智谱或覆盖旧证据 |
| 发送预算、取消、观察、用量和失败边界 | 复用控制原则，但新增协议映射需针对性验证，不能直接借旧通过 |
| 既有模型开发结果和资格材料 | 保留历史价值；新的模型组合须自己的真实质量证据，不能跨组合拼资格 |

代码确有厂商绑定，不只是一个配置项：`natural_duty_contract.py:62,109,144`、
`natural_duty_workflow.py:54`、`app/runtime/receipted_provider_factory.py:56`、
`app/evaluation/golden_stream_bridge.py:440`。`app/providers/config.py:192,225` 使用 OpenAI SDK，
但返回智谱/DeepSeek adapter；SDK 存在不等于已支持 OpenAI provider。

当前要求一次 `submit_report_review`。Astra/Sol 的 Chat Completions 不支持函数调用，需
Responses 的请求、输出项、流事件与终态映射；可用指定函数调用，但仍核实际响应。
Astra 不支持自定义 temperature/top_p，不能无声沿用原 1/.95。
[推理与接口](https://developers.openai.com/api/docs/guides/reasoning)、
[函数调用](https://developers.openai.com/api/docs/guides/function-calling)、
[Astra 发布说明](https://developers.openai.com/api/docs/changelog)。

Claude Opus 5.5/Fable 5.1 拒绝强制工具选择，需要 auto+strict tool 或结构输出的独立协议；
不能把 JSON 正文伪造成真实工具调用。还需 Messages content block/stream/终态转换。
[Claude 限制](https://platform.claude.com/docs/en/build-with-claude/thinking)。

`TokenUsage` 当前只有 input/output/cached-input；新 provider 要按官方总数计算推理消耗，
不得重复相加。拒绝/截断可有可信已知用量，不能抛错后抹成零或伪造成功 ChatResponse。
保留单次300秒墙钟、32768总输出、零重试、发送前取消和回执失败边界；模型能力上限不是
自动扩容理由。任何新的时间/预算需要显式取舍，官方页不保证在现有时限内完成。
[OpenAI 用量](https://developers.openai.com/api/docs/guides/reasoning)、
[Claude 用量](https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost)。

## 本包结束条件与后续边界

已完成可审查的路线、能力、成本与代码接入差异比较；没有选定迁移，没有新实施或付费批。
下一步如准备诊断，应先固定完整材料、合法正例、真实反例、原判据及次数/成本，比较哪个
检查最能改变决策；本表不是发送清单，也不因此先建设新的通用评测框架。
漏检、误拒、错误修法、协议失败、超时和未知用量分别报告；任一结果不能只导向无限重试。

原产品5次、已确认候选6次、GLM角色合同、automation PAUSED、发布关闭、旧封存和缺口保持。
正式同版本15、自然Coach/Training、四块联动/journal、前端/头像、Memory、身份运维、两树整合、
独立评估及学习仍是既有依赖。比较完成不推进8E，也不表示此前工程投入都失效。
