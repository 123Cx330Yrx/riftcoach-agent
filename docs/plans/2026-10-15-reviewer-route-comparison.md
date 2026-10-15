# 审查路线比较：保留 GLM 采用决定，不启动厂商迁移

2026-10-15。机制/官方资料比较后，已准备离线筛选材料并核第三方公开配置；无新模型请求、无产品切换、无替代 provider 实施。
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

## 两份完整材料与四请求的离线准备

材料在 `data/evaluation/fixtures/reviewer_profile_screen_20261015`，脚本为
`scripts/prepare_reviewer_profile_screen.py`。从固定公开材料重建两份历史请求的完整可见业务输入，
再派生两份全文：r01为合法观摩建议；r02仅把第5节block19改为依据第三方比赛要求阅读者本人
未来五局训练并用本人死亡下降验收。原稿到r01的四处变化在evaluation逐项保留；不是新的模型生成。
报告、来源、双职责政策、schema均完整，不用局部句子代替全文。请求中没有预期标签或作者意见。

独立作者按checkpoint七项原件完成全文审查，原文件以SHA40350d15a99bbe27d2289de7f50ecf5a9943011ae593f827edd42ad989ff9445归档。
主审随后重读全文/完整来源、两政策与schema，均认为材料usable；主审在回件后复核，不宣称两份互盲判断。
这是普通开发材料复核，不是旧批重判或native业务认证。两职责可能修同一段而补丁重叠；
分别正确不证明现有组合应用成功。未来有据的新问题可以否定材料前提，不能为保标签忽略。

拟顺序r01-facts、r01-completion、r02-facts、r02-completion；每次完整审查结果后才考虑后继。
最多4次、零重试、每次64000输入预留/32768总输出/300秒，共387072tokens/1200模型秒。
漏检、误伤、错误修法停止；协议/超时/未知用量记证据不足并停止，不改词续购或自动换下一个模型。
均通过只支持继续评估投入，不证明优于GLM、可靠率、完整编辑/fresh、自然任务或原15资格。
本地输入估算未核新模型tokenizer，四文件是业务请求，不是已验证的Responses wire。
没有sender或实际通道选择，manifest保持execution_ready/authorized/qualified全false。

## 用户现有第三方接入与参数核对

用户没有官方API账户，只有个人Plus及第三方服务，并提供YJ API与天机阁网址供检查。
Plus不当API额度；原$1.82272仅官方预算参考，已在生成器/manifest与实际通道字段分开。
只读快照见包内channel-check.json；仅公开GET与浏览器页面读取，没有密钥读取、POST或模型请求。

YJ API公开配置列出gpt-6.1-sol，但该模型端点仅标Chat Completions；未证Responses，而非断言其不支持。
天机阁明确列Responses，浏览器实际展示`client.responses.create`及`https://yujianwudi.top/v1`。
其模型详情参数表列tools、tool_choice(auto/none/required)、stream(SSE)、response_format等，
不是完全没文档。但切换Responses后表仍保留相同max_tokens/response_format等聊天字段，
不能把这张通用表直接作为本项目wire合同。新手文档未说明high、Responses回执或流式终态细节。

| 项目 | 已看到的声明 | 本项目需要核实/实现的内容 |
|---|---|---|
| 推理 | 官方Sol支持high，站方通用表未列 | Responses用reasoning.effort=high，实际通道是否接受/保留仍未验证 |
| 工具结果 | tools/tool_choice在表中 | output中的真实function_call、正确name和arguments；纯JSON文本不能冒充工具调用 |
| 输出上限 | 表中max_tokens | Responses使用max_output_tokens；包含推理预算，实际截断及计量待回执核对 |
| Schema | 表称支持JSON/Schema | 保持现有可选block字段；显式strict=false避免自动严格化改变合同，收到结果后完整校验 |
| 流与用量 | stream/SSE在表中 | completed/incomplete/failed终态、完整input/output和推理明细；断线后不得把未知记零 |
| 身份 | 多分组及自动回退链 | 固定分组与模型；GPT-pro是站方分组名，不等于OpenAI reasoning.mode=pro |

依据：[站方模型详情](https://yujianwudi.top/pricing)、[站方文档](https://doc.yujianwudi.top/)、
[官方Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)、
[函数调用](https://developers.openai.com/api/docs/guides/function-calling)、
[推理及计量](https://developers.openai.com/api/docs/guides/reasoning)。实际打开对照，网页兼容声明不是已跑通回执。

| 天机阁分组 | 页面输入/输出元每百万 | 四次无缓存预算页面估价 | 站方显示成功率 |
|---|---:|---:|---:|
| GPT-plus | 0.2 / 1 | 0.182272元 | 96.17% |
| GPT-pro | 0.4 / 2 | 0.364544元 | 99.13% |
| GPT-企业专线 | 0.5 / 2.5 | 0.455680元 | 95.82% |

列表最低价来自plus组，不是企业组价。站方总览标最近24小时、排除业务拒绝且包含当前小时，
分组无障碍说明却另写30 day uptime，样本数/端点/推理配置不明，不能计算本项目可靠率或宣称质量。
费用是页面标准显示的条件估价，账户充值兑换、真实扣账及实际tokens未核，不是账单硬上限。
建议下一接入准备优先固定天机阁GPT-pro，原因是已声明所需端点、报价低且当前展示调用表现较好；
不因分组名认定真实上游或性能保证。这是建议，selected_execution_profile仍null，未采用迁移/授权付费。

浏览器在用户切TUN后恢复过，随后也有调试超时及登录中断，不能证明此前由系统代理造成。
用户要求用完提醒切回；已提醒，未修改网络、未验证其已切回。真实请求前须核当时路径，不能把
清除HTTP_PROXY/NO_PROXY当作已绕过TUN；GitHub进程代理与模型路径继续分开。

## 本包结束条件与后续边界

已完成可审查的路线、两稿四请求、材料复核及第三方公开接入核对；没有选定迁移或新付费批。
下一动作是针对拟固定通道准备最小Responses请求/回执转换和离线边界检查，再以具体wire、分组、
费用与真实网络提出有界执行决定。不得把业务请求文件存在写成执行已ready，也不先建设通用评测框架。
漏检、误拒、错误修法、协议失败、超时和未知用量分别报告；任一结果不能只导向无限重试。

原产品5次、已确认候选6次、GLM角色合同、automation PAUSED、发布关闭、旧封存和缺口保持。
正式同版本15、自然Coach/Training、四块联动/journal、前端/头像、Memory、身份运维、两树整合、
独立评估及学习仍是既有依赖。比较完成不推进8E，也不表示此前工程投入都失效。
