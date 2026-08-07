# 阶段 5C：Skill Router V1 退出复核

## 1. 结论先行

阶段 5C 通过退出复核，可以进入下一检查点 5D 的设计与实施，但不能据此声称
5D 已经开始或完成。

这次通过代表：RiftCoach 已经能在两个已声明的用户工作流之间做确定性、可解释、
可拒绝的选择，并用开发集、独立保留集和采用 ADR 说明它的能力与局限。它不代表
Router 已经执行 Skill、调用模型、生成报告，也不代表路由对开放世界自然语言已经
充分泛化。

退出复核还修复了两类审计问题：

1. `RouterDecision` 现在要求命中决策的证据身份与候选 Skill 身份完全一致，外部
   调用者不能给一个已选结果夹带无关 Skill 证据；
2. holdout 的 `rules_frozen_at_commit` 从不包含双 Skill 合同的 `cfd2084` 更正为
   真正冻结两个 Manifest 的 `4103d42`。用例、期望标签、Router 规则和既有结果均
   未改变，也没有重跑 holdout 或根据失败调参。

## 2. 先用初学者视角理解 Router

一个 Agent 不是“把用户的话直接丢给大模型”。RiftCoach 把一次请求拆成多层责任：

```text
用户说了什么
    │
    ▼
Skill Router：哪个已声明工作流可以接管？
    │
    ├─ selected  → 恰好一个工作流完整匹配
    ├─ ambiguous → 多个工作流同时完整匹配，不能擅自猜
    └─ rejected  → 没有可用工作流，或没有完整匹配
```

Router 只做“选择”，不做“执行”。这样拆分有三个价值：

- 可解释：能看到命中了哪些声明式信号，而不是只得到模型的一句猜测；
- 可约束：没有唯一匹配时 fail closed，不把错误意图继续放大到工具调用和报告；
- 可替换：未来可以比较确定性、Embedding 或 LLM 路由策略，而不改 Skill、Agent
  Loop、Tool Runtime 或 Harness 的合同。

## 3. 当前完整数据流与控制流

```text
skills/*/manifest.yaml
    │  Loader 严格验证 Skill 合同
    ▼
SkillCatalog 不可变快照
    │  只投影 name/version/description/triggers
    ▼
RouterRequest(utterance, available_skills)
    │
    ▼
统一文本规范化
    │
    ▼
逐个候选检查
    ├─ 每个 required_signal_group 是否至少命中一个信号
    └─ 是否命中 excluded_signal 硬否决
    │
    ▼
完整匹配数量
    ├─ 0 → rejected
    ├─ 1 → selected
    └─ 2+ → ambiguous
    │
    ▼
RouterDecision(outcome, reason, candidates, evidence, explanation)
```

这里的数据流是 Manifest 元数据进入 Catalog，再成为 Router 输入和结构化决策；
控制流是根据完整匹配数量进入三种终态。两者都在本地同步完成，没有网络调用、
模型随机性或隐藏打分。

## 4. 5C-1 至 5C-6 的完成证据

| 检查点 | 解决的问题 | 主要实现 | 验收证据 | 结论 |
|---|---|---|---|---|
| 5C-1 Router Contract | 什么输入和结果才是合法路由 | `routing_models.py` 的 Request、Decision、Outcome、Reason、Evidence | 非法状态/原因、重复身份、空文本、证据不一致测试 | 完成 |
| 5C-2 Skill Catalog | 如何稳定发现可用 Skill 而不泄漏执行权限 | `catalog.py`、`loader.py` 和只读候选投影 | 空目录、坏包、稳定顺序、重复快照、显式重建测试 | 完成 |
| 5C-3 Deterministic Router | 如何依据 Manifest 做可解释选择 | `router.py`、`routing_text.py`、两个 Manifest 的声明式信号 | 唯一匹配、规范化、最长信号、候选顺序无关测试 | 完成 |
| 5C-4 Rejection / Ambiguity | 证据不足或多解时如何 fail closed | 三态决策、排除硬否决、部分证据保留 | 无候选、部分匹配、域外请求、真实双 Skill 混合范围测试 | 完成 |
| 5C-5 Router Evaluation | 如何避免拿训练过的题目冒充泛化成绩 | 版本快照、development/held-out 角色、CLI、历史归档 | development 23/23；holdout 单次运行 11/12；历史文件哈希测试 | 完成，有已知局限 |
| 5C-6 Model Fallback Decision | 出现 Bad Case 后是否马上加模型 | ADR-0010 的方案、成本、故障和重开门槛比较 | 保留唯一失败，不调规则；决定 V1 暂缓 LLM fallback | 完成 |

## 5. 各层职责不能混淆

| 层 | 当前职责 | 5C 是否执行它 |
|---|---|---|
| Skill | 声明工作流的触发边界、输入输出、指令、工具白名单和预算 | 只读取路由元数据，不执行 |
| Router | 从当前候选中选择、拒绝或报告歧义 | 是 |
| Agent Loop | 让模型在预算内决定回答或请求工具 | 否；5A 已有最小实现，5D 才接 Skill |
| Provider | 适配具体模型及其能力 | 否 |
| Tool Runtime | 校验并可靠执行工具，处理超时、重试、缓存、熔断和权限 | 否 |
| RAG | 提供带来源的 LoL 知识证据 | 否；它未来是 Skill 可用工具之一 |
| Harness | 评测、受限修订并决定发布、降级或拒绝 | 否；事实审查继续属于这里 |
| Memory | 保存会话、玩家画像和训练进度 | 尚未实现，阶段 6 负责 |
| MCP | 与外部标准工具服务通信 | 尚未实现，阶段 7 负责 |
| Multi-Agent | 多个独立上下文/权限的 Agent 协作 | 当前不是；阶段 8 仅按证据评估 |

因此“已有两个 Skill”不等于 Multi-Agent，“本地 Tool Runtime”不等于 MCP，
“Router 选中工作流”也不等于工作流已经执行。

## 6. 评测应当怎样解读

### 6.1 Development 23/23

这 23 条用于开发和校准，证明实现满足我们已经知道的正例、负例和歧义规则。
它们不能证明面对新表达也一定正确。

### 6.2 Holdout 11/12

holdout 在双 Skill 合同冻结后建立，随后单次运行。唯一失败是：

```text
分析一下我最近键盘的表现
```

字面规则命中“最近”以及“分析/表现”，所以选择了 `recent-form-review`；产品语义
要求拒绝，因为对象是键盘而不是 LoL 对局。这证明当前规则缺少开放世界实体语义，
不是把“键盘”补进黑名单就能可靠解决的问题。

没有根据该失败修改触发词或排除词。否则这 12 条就会从独立证据变成另一组开发题，
11/12 也失去诚实的解释价值。

### 6.3 为什么仍可完成 5C

Evaluation 的目标不是强行得到满分，而是暴露边界并支持决策。当前只有一个小型、
维护者合成的失败族；引入 LLM Router 还会增加结构化输出、超时、429、成本、延迟、
非法候选和 fail-closed 处理。ADR-0010 因而选择暂缓，并为以后重开实验定义门槛。

## 7. 失败模式与当前限制

- 字面信号可能把域外对象误判为 LoL 复盘；
- 不理解所有同义改写、反讽、省略和长句关系；
- `ambiguous` 目前只返回结构化状态，还没有会话层澄清交互；
- 小型合成 holdout 不能代表生产流量或跨人群泛化；
- Skill 的输入输出模型仍有空白字符串规范化不完全一致的问题，尤其
  `RecentFormReviewInput.deterministic_report`、两个 Output 的 `run_id/report`；
- Router 只选择，不验证输入数据与 Artifact 是否来自同一次事实收集；
- 没有真实 Skill Executor、Context Builder、结构化 Provider 输出或统一 Runtime。

其中空白字符串和 Artifact 关联属于 5D 的执行输入边界，不是 Router 匹配算法。
它们已被明确列为 5D 前置硬化项，不能在 5C 里假装已经解决。

## 8. 为什么没有直接套 LangGraph 或 Agent SDK

5C 的核心边界由普通 Python 和 Pydantic 表达：Manifest、Catalog、RouterRequest、
RouterDecision 都不依赖 LangGraph、Pi 或 Claude Agent SDK。这里的“自定义”不是
重新造一个通用图引擎，而是把 RiftCoach 自己必须拥有的领域合同做清楚。

未来框架可以替换的是编排执行层：

```text
稳定领域合同
  Skill + Router + Tool Policy + Harness Gate
                 │
                 ▼
可替换 Runtime
  自有 Python Runtime / LangGraph / Pi / Claude Agent SDK
```

任何候选 Runtime 都必须消费同一 RouterDecision、遵守同一工具白名单和预算、输出
同一 Trace，并经过同一领域评测。阶段 5F 才用真实切片对照后决定采用、局部采用或
拒绝采用。这样既不会因早期绑死框架，也不会靠“自研”二字跳过成熟框架的可靠性
对照。

## 9. 5D 的进入条件和明确边界

5D 的目标是“执行已选中的 Skill”，不是继续堆 Router 功能。开始实现前应先把
5D 拆成可教学、可单独验收的小检查点，至少覆盖：

1. 统一收紧两个 Skill 输入输出中的非空文本和 Artifact 关联边界；
2. Context Builder V1 只抽取当前任务必需的确定性事实、Skill 指令和有界知识，
   不把完整 Summary 无差别塞入模型；
3. 明确 system/developer/user、可信事实、RAG 文档和工具结果的优先级与不可信边界；
4. 将选中 Skill 的工具白名单和预算转换为受限 `AgentRunRequest`；
5. 建立真实 Provider 结构化输出的解析、拒绝额外字段、截断/非法 JSON 和有限修复；
6. 复用已有 Agent Loop、Tool Runtime 和 Harness，使质量门禁仍是唯一发布出口；
7. 用 Prompt/Context、越权、预算、结构化输出和降级案例验收。

本退出复核只把 5D 设为唯一下一检查点，不实现上述内容，也不预先把 5D 一批写完。

## 10. 面试时可以和不可以怎样说

可以说：

> 我为 RiftCoach 设计了框架无关的 Skill Router。Skill Manifest 声明触发信号，
> Catalog 生成稳定候选快照，Router 在本地输出 selected/rejected/ambiguous 及证据。
> 双 Skill development 为 23/23，冻结规则后的合成 holdout 为 11/12；我们保留
> 设备域误选，并通过 ADR 暂缓 LLM fallback，而不是对 holdout 过拟合。

不可以说：

- 路由准确率达到生产级 91.7%；
- 已实现语义 Router 或 LLM Router；
- 已经使用 LangGraph、MCP 或 Multi-Agent 完成工作流；
- Router 已经生成并发布教练报告；
- holdout 失败已经修复。

## 11. 退出判定

5C-1 至 5C-6 的实现、评测、决策、已知限制和维护边界均已有可追溯证据。退出复核
发现的 RouterDecision 契约漏洞与 holdout provenance 标注错误已做最小修正；旧
5C-4 文档已增加后续演进说明。5D 前置缺口已显式登记，不会被误写成现有能力。

因此 5C 状态改为 **已完成**，阶段 5 仍为 **进行中**，唯一下一检查点改为 **5D**。
