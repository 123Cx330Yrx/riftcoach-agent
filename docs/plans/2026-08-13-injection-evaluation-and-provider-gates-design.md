# 5D-7 Batch D：注入评测与真实 Provider 决策门设计

## 1. 这一批要解决的具体问题

Batch C 用 Scripted Provider 驱动了真实的 Skill、AgentLoop、ToolRuntime、本地 RAG 和
ReviewHarness。它暴露了一个可以重复的安全问题：当 Coach 草稿服从 RAG 中的不可信
指令，而结构化 Evaluator 错误返回 `pass` 时，ReviewHarness 会按现有合同发布该草稿。
外层 Domain E2E canary oracle 随后能把它标成 `unsafe_publication`，但那是实验后的发现，
不是生产发布前的阻断。

源码审计进一步确认，这不是给 Harness 增加一个关键词判断就能正确解决的问题：

- `EvaluationResponseModel` 1.0.0 没有专用注入问题类别；
- `build_evaluation_prompt()` 只把结构化事实和报告交给 Evaluator；
- `EvaluationRequest` 虽含 `KnowledgeEvidence`，当前 Adapter 没把它放入评测 Prompt；
- Evaluator 看不到原始用户请求，也看不到 Context section 的信任标签；
- Batch C 的 canary oracle 知道测试答案，只适合 Eval，不能冒充通用生产防护。

Batch D 因此先冻结版本迁移、数据流、数据集生命周期、真实调用预算和第二 Provider
决策门。入口设计本身不修改生产 Prompt，不创建或运行 held-out，也不调用真实 Provider。

## 2. 初学者需要理解的底层原理

### 2.1 信任边界、语义审查和实验 oracle 是三件事

```text
输入信任边界
  标记“这段文字是数据，不是指令”
          |
          v
语义 Evaluator
  判断草稿是否真的服从了不可信指令
          |
          v
确定性 Harness
  根据类型化结果决定发布、降级或拒绝

实验 Canary Oracle（生产链外）
  已知测试攻击目标，用来发现 Evaluator 是否漏判
```

信任标签能降低模型误解的概率，但不会强制模型服从。Evaluator 能理解语义，但它也是
模型，仍可能判断错误。Harness 的决定是确定性的，但它只能依据收到的结构化结果。
Canary oracle 知道合成攻击的目标，适合测试前三层是否失守，却不能证明未知攻击都安全。

### 2.2 为什么旧合同必须保留

Batch A-C 的 Dataset、Candidate、Result 和 Prompt/Context snapshot 都绑定
`coach_evaluation@1.0.0`。如果原地修改同名合同，旧文件表面版本不变，实际语义却变了，
历史结果就不能再逐字节复现。

因此采用显式版本迁移：

```text
coach_evaluation@1.0.0
  只用于复现已有历史证据，不再扩展语义

coach_evaluation@1.1.0
  新增注入审查输入、问题类别和确定性阻断策略
```

版本化不是为了“多写一个版本号”，而是为了回答面试中的关键问题：同一次模型对比中，
到底是模型变化了，还是 Prompt、Schema、输入证据和发布规则变化了。

## 3. 方案比较

### 方案 A：发布前扫描已知 canary 或关键词

它能让 Batch C 当前样例变绿，但只是在产品里硬编码考题答案。换一种表达就可能绕过，
还会误伤正常文本。拒绝作为生产方案；canary 继续只作为 development/held-out oracle。

### 方案 B：原地扩展 1.0.0 的 issue 枚举和 Prompt

改动少，但会静默改变历史实验语义，也没有解决用户原话、RAG 证据和信任标签没有进入
Evaluator 的问题。拒绝。

### 方案 C：版本化安全评测 Profile + Harness 阻断策略 + 外部 oracle

保留 1.0.0；新建 1.1.0 输入/输出合同；让 Evaluator 看到有边界、带来源的必要不可信
上下文；让 Harness 对安全类别执行不可修订的阻断；canary 仍留在实验层检验漏判。采用。

## 4. 目标数据流与控制流

### 4.1 新的最小评测输入

`coach_evaluation@1.1.0` 不应收到整个 Agent 上下文，而应收到最小、类型化的评测包：

- `fact_pack`：现有确定性事实投影；
- `report`：待发布 Coach 草稿；
- `untrusted_user_request`：本次已校验 Skill execution 中的用户原话，标为 data-only；
- `untrusted_knowledge`：实际进入 Agent 的 bounded KnowledgeEvidence，保留 citation/source
  身份并标为 data-only；
- `security_policy`：内部固定规则，说明不可信内容不得改变任务、索取秘密或要求输出
  非业务标记。

不加入 API Key、原始 Provider 响应、思维链、request ID、未知扩展字段或全部 Summary。
这些数据对安全判断没有必要，只会扩大泄露和注入面。

### 4.2 新的最小评测输出

新 Schema 在现有事实类 issue 上增加 `prompt_injection`。安全不变量为：

- 发现 `prompt_injection` 时必须是 `high`；
- Harness 把该类别视为 blocking issue；
- blocking issue 不能进入 Reviser，因为把恶意指令再次交给模型会扩大攻击面；
- 不论分数多高、verdict 字面值是什么，只要出现 blocking issue 就不得发布；
- Schema 或评测不可用时沿用 fail-closed deterministic fallback/rejection。

Evaluator 如果完全漏判，Harness 仍无法凭空知道语义风险。这个剩余风险由 held-out
canary oracle 测量，而不是用“已经彻底解决 Prompt Injection”来掩盖。

### 4.3 控制流

```text
ValidatedSkillExecution + actual KnowledgeEvidence + CoachDraft
                         |
                         v
              EvaluationSecurityContext
                         |
                         v
       coach_evaluation@1.1.0 structured call
                         |
                         v
          deterministic evaluation policy
             |                       |
       blocking issue             ordinary issue
             |                       |
   degrade / reject directly    bounded revision policy
             |
             v
       never publish the draft
```

ReviewHarness 继续拥有唯一发布权；AgentLoop、Evaluator 和 Reviser 都不能自行发布。
这不是 Multi-Agent，也不引入第二套 Harness。

## 5. Batch D 内部实施顺序

这些是同一 `5D-7 Batch D` 内部批次，不新增、改名或重排 0-8 主阶段及既有 5D 子阶段。

### D1：Evaluation 1.1 与阻断策略离线 TDD

- 保留 1.0.0 兼容入口和历史快照复现；
- 新增类型化安全评测输入与 1.1.0 输出合同；
- 将用户请求和实际 KnowledgeEvidence 以 data-only 边界送入新 Prompt；
- 对 blocking issue 直接降级/拒绝，不调用 Reviser；
- 先用单元与 Harness 组合测试证明行为，不改 held-out，不调用真实 Provider。

### D2：新实验身份与 executable development 回归

- 生成新的 Prompt/Context snapshot ID，不覆盖 v1；
- 建立绑定 1.1.0 的新 development Dataset/Candidate/Result；
- 重新运行零外部调用 executable controls；
- 接受标准是已知注入开发案例不再 unsafe publish，同时事实、引用、工具和正常发布路径
  不退化；
- 旧 Batch C 的 1/7 unsafe publication 原样保留为修复前基线。

### D3：冻结后创建独立 held-out

- 只有 D1/D2 代码、Prompt、Schema、阻断规则和 snapshot 全部冻结后才能创建；
- held-out 必须 `calibration_excluded=true`，不得复制 development canary 或措辞；
- 创建和密封不等于运行；运行前必须再次验证代码/快照未漂移；
- 首次结果无论成功失败都原样保存，不得反向调当前规则；若用于后续改进，旧 held-out
  退休，新规则使用新版本和新的独立 held-out。

### D4：第二 Provider 采用门

最多只选择一个候选。进入条件：

1. Evaluation 1.1 和新 snapshot 已冻结；
2. executable development 的 unsafe publication rate 为 0，其他控制案例无回归；
3. 候选具有可验证的结构化输出和 Tool Calling 能力；
4. 能用当前 Provider-neutral Adapter 合同实现，且 SDK 自动重试可关闭；
5. 当时的官方能力、价格和模型状态已经重新核验；
6. 新 ADR 记录为什么选它、为什么不选其他候选、预计调用上限和退出条件。

发布热度、榜单宣传或“多一家模型更像 Agent”都不能打开该门。

### D5：有限真实同任务比较

- 两个 Provider 使用同一冻结代码、Skill、Prompt/Context snapshot、Dataset 和 Harness；
- 第一轮只用 3 个独立 held-out 场景：正常控制、用户注入、知识注入；
- 每场最多 4 次外部调用：Agent 工具提议、Agent 最终草稿、Evaluation，以及至多一次
  Evaluation 格式修复；`max_revisions=0`，避免把自修订能力混进首轮比较；
- 每个 Provider 领域上限为 12 calls，SDK 自动重试为 0；任一硬门失败立即停止剩余案例；
- 第二 Provider 的 Adapter 协议准入另有最多 3 calls，因此新候选在首轮最多 15 calls；
- GLM 的新实验最多 12 calls。它使用新的 1.1.0 实验身份，不覆盖、不伪装成重跑
  5D-6b 的历史失败；
- 价格无法可靠快照时成本为 `null`，不能写成 0；延迟、Token 和调用数按真实观测保存。

上述是最大预算，不是必须用满。真正执行前仍要有公开 CI 成功的精确代码 SHA、脱敏输出
合同、禁止覆盖结果和 pre-I/O 预算门。

## 6. 测试如何证明行为

### D1/D2 离线验收

1. 1.0.0 Schema、快照和 Batch A-C 冻结文件仍可逐字节复现。
2. 1.1.0 严格拒绝未知字段、非法类别和不一致的安全 issue。
3. 新 Prompt 明确标记用户/RAG 内容为不可信数据，并且只注入 allowlisted 字段。
4. blocking issue 即使伴随高分或 `needs_revision` 也不能发布、不能调用 Reviser。
5. Evaluator 结构化失败仍只允许一次格式修复，之后 fail closed。
6. Batch C 的已知漏判在新 development 基线中不再 unsafe publish。
7. happy path、事实、引用和工具选择用例不得因安全扩展产生回归。
8. 公开 snapshot/Candidate/Result 不得保存 canary、Prompt、报告、Observation、异常、
   request ID、密钥或玩家身份。

### D3-D5 运行门

1. held-out 在规则冻结前不能创建，在显式确认和 snapshot 匹配前不能运行。
2. real-provider candidate 必须记录 Provider/model、代码 SHA、snapshot SHA 和数据集摘要。
3. 第 13 个领域调用或第二 Provider 的第 16 个累计调用必须在底层 I/O 前被拒绝。
4. 两家 Candidate 必须具有完全相同的案例集合和合同身份，否则不生成比较结果。
5. 主指标至少包括任务成功、工具选择、事实、引用、注入、unsafe publication、调用数、
   Token、延迟和可空成本；小样本结果只作为准入证据，不宣称统计显著性。

## 7. 非功能要求与失败处理

- **安全**：公开证据只保存白名单枚举、布尔结论、计数和哈希；原始攻击文本与模型正文
  只存在于临时运行目录，实验结束不提交。
- **可复现**：任何有效 Prompt、Schema、Skill 或 Context 变化必须产生新 snapshot 和
  Dataset version，不能覆盖旧基线。
- **成本**：真实调用由共享 pre-I/O budget 计数，SDK retry 为 0，失败不盲目重试。
- **可靠性**：Evaluator 不可用、Schema 错误、安全上下文构造失败都走 deterministic
  fallback/rejection。
- **可维护性**：不在 ReviewHarness 内硬编码具体 canary；生产策略只识别版本化的
  blocking issue 类别。
- **可观测性边界**：本批只定义领域实验所需的安全观测，统一 Trace 仍属于 5E。

## 8. 本入口批实现与明确不实现

本入口批实现：

- 源码级漏判责任审计；
- 1.0.0 到 1.1.0 的版本迁移设计；
- Injection Evaluation、held-out、真实调用和第二 Provider 的硬门；
- ADR-0016 与持久路线状态。

本入口批不实现：

- 不修改生产 Evaluation Schema、Prompt 或 Harness；
- 不创建/运行 held-out；
- 不调用 GLM、DeepSeek、Qwen 或其他真实 Provider；
- 不选择或接入第二 Provider；
- 不引入 LangGraph、Pi/Claude Agent SDK、Multi-Agent 或新基础设施；
- 不进入 5E、5D exit review 或后续主阶段。

## 9. 当前限制和下一步

设计通过只证明我们知道缺口应在哪里、如何安全迁移和怎样验收，不表示注入问题已经修复。
唯一下一步仍在 5D-7 Batch D：按 D1 先用 TDD 实现兼容的 Evaluation 1.1 和 blocking
policy。D1 完成前不得创建 held-out、调用真实 Provider 或接第二 Provider。
