# ADR-0010：暂缓 LLM Skill Router fallback

## 状态

已接受

## 背景

双 Skill development v2 为 23/23；规则冻结后，independent holdout v1 单次运行
得到 11/12。唯一失败把“分析一下我最近键盘的表现”选为
`recent-form-review`。实现符合“近期范围 + 复盘目标”的字面 Manifest 合同，但
目标实体属于设备而非 LoL 对局，产品期望应拒绝。

当前 GLM Provider 只声明 `text_chat`，尚未端到端实现结构化输出。Router 当前是
零网络、无 Token 成本、可解释的纯函数，排除信号和候选白名单由代码强制执行。
需要决定一条合成语义失败是否足以引入模型兜底。

## 决策

阶段 5C V1 暂缓 LLM Router fallback，继续使用 `DeterministicSkillRouter`，不修改
已冻结的 Router 或两个 Skill Manifest，也不使用 holdout v1 调参。

后续优先使用类型化产品入口提供任务范围，并在会话层支持低上下文请求澄清。只有
新鲜数据出现多个独立语义失败族，且候选模型通过新的 development/holdout、结构化
输出、延迟、成本和故障评测后，才重新评估模型语义复核。

未来即使采用模型，也必须保持以下不变量：

- 硬排除和可用候选由代码控制；
- 模型只能在候选白名单中提议，不能执行 Skill；
- 非法输出、越界候选、超时和 Provider 故障必须 fail closed；
- 不能复用或改写 holdout v1 来证明改进；
- Trace 记录确定性证据、调用原因、Prompt/Provider 版本、Usage 和最终代码决定。

## 影响

### 正面

- 保留 V1 的可解释性、稳定延迟、零路由 Token 成本和 Provider 故障隔离；
- 不因一个小型合成案例过度设计；
- 不通过添加“键盘”黑名单污染 holdout；
- 为未来模型实验建立可验证的采用门槛。

### 负面

- 当前设备域假朋友仍是已知误路由；
- 在类型化入口和澄清机制落地前，泛化输入仍可能出现类似假朋友；
- 未来若采用模型，需要新数据集和独立评测，不能复用现有 holdout 调参。

### 中性

- 这是“暂缓”而不是永久拒绝模型路由；
- GLM 仍是唯一真实 Provider 基线，本决策不选择第二 Provider；
- 本决策不实现 API、Session、Memory、Multi-Agent 或 5D Agent Loop。

## 备选方案

### 添加设备排除词

可修复当前案例，但会形成无穷黑名单并直接利用 holdout 调规则，因此拒绝。

### 强制 LoL 专属信号

保持确定性，但会误拒绝“最近状态怎么样”等合法简写。缺少新鲜语料证明收益，暂不
采用。

### 低上下文时澄清

安全且可解释，是优先后续方向；但需要类型化入口或会话消费者，分别属于 5P/阶段
6，不在 5C-6 实现。

### 立即增加 LLM 语义复核

可能理解目标实体，但必须复核部分 selected 才能捕获本 Bad Case；当前缺少调用
边界、结构化输出能力、独立新评测和成本收益证据，因此暂缓。

### Embedding 或分类器

当前标注数据不足以稳定校准阈值，新增模型资产和维护成本不成比例，因此拒绝。

## 参考

- `data/evaluation/results/skill_router_v1_holdout_baseline.json`
- `docs/plans/2026-08-07-skill-router-model-fallback-decision.md`
- `docs/plans/2026-08-06-deterministic-skill-router-design.md`
- `app/skills/router.py`
- `app/providers/zhipu.py`
- `docs/adr/0007-separate-provider-and-tool-runtime.md`
