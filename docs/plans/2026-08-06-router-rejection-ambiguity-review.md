# 阶段 5C-4：Router 拒绝与歧义验收

## 1. 这一阶段解决什么问题

Skill Router 的职责不是回答用户，也不是执行工具，而是判断“当前请求是否有且
只有一个已声明的工作流可以接管”。如果 Router 在证据不足或多个工作流冲突时
仍然强行选择，后续 Agent Loop 就会带着错误的指令、权限和预算继续运行。

因此 V1 使用 **fail closed** 原则：

- 没有唯一且完整的匹配时，不进入 Skill 执行；
- 没有合格候选时返回 `rejected`；
- 多个候选同时合格时返回 `ambiguous`；
- 候选在列表中的先后顺序不能充当决策证据。

这里的“拒绝”不是说用户的问题永远不能处理，只表示当前可用 Skill 集合和当前
确定性规则不足以安全接管。“歧义”也不是模型报错，而是 Router 明确承认输入
同时满足多个工作流边界，需要后续澄清或更高层策略处理。

## 2. 数据流

```text
RouterRequest
  ├─ utterance: 用户原始表达
  └─ available_skills: 当前可用候选的只读路由元数据
             │
             ▼
规范化用户文本
             │
             ▼
逐个评估所有候选
  ├─ 每个 required signal group 是否至少命中一个信号
  └─ 是否命中任意 excluded signal
             │
             ▼
matched = 所有必需组完整命中 AND 没有排除信号
             │
             ▼
统计完整匹配数量
  ├─ 0 个  → rejected
  ├─ 1 个  → selected
  └─ 2+ 个 → ambiguous
             │
             ▼
RouterDecision
  ├─ outcome
  ├─ reason
  ├─ selected/candidate Skill
  └─ 可解释的正负信号证据
```

Router 会评估所有候选后再统计结果。它不会遇到第一个匹配就提前返回，因此
不能用候选顺序偷偷打破平局。

## 3. 四种决策边界

| 可用 Skill | 完整且未被否决的匹配数 | 结果 | 原因码 |
|---|---:|---|---|
| 0 个 | 0 | `rejected` | `no_available_skills` |
| 1 个或更多 | 0 | `rejected` | `no_matching_skill` |
| 1 个或更多 | 1 | `selected` | `matched_skill` |
| 2 个或更多 | 2 个或更多 | `ambiguous` | `multiple_skills_matched` |

### 3.1 无可用 Skill

Catalog 没有提供任何候选时，Router 不知道有哪些工作流存在。此时不能把用户
表达转给默认 Skill，返回 `no_available_skills`，而且不能伪造路由证据。

### 3.2 无完整匹配

只命中部分必需信号不等于匹配。例如“我最近换了键盘”命中了近期范围，但没有
表达对局表现或复盘目标。Router 返回 `no_matching_skill`，并可保留“最近”这条
部分证据，帮助 Trace 解释为什么差一点匹配但没有执行。

### 3.3 排除信号否决

`recent-form-review` 需要近期范围和复盘目标，但明确排除“这一局”“单局”等
单局信号。即使正面必需组全部命中，只要出现一个排除信号，该候选就不再是
完整匹配。排除信号优先于正面匹配，不是一个可以被正面信号抵消的分数。

本轮同时收紧 `RouterDecision` 合同：被声明为 `selected` 或 `ambiguous` 候选的
证据中不能再含排除信号。这样不仅当前 Router 算法正确，其他调用方也无法手工
构造“已被否决但又被选中”的自相矛盾决策。

### 3.4 多候选歧义

当两个或更多候选都完整匹配时，V1 不使用数组顺序、隐藏分数或随机选择器决定
胜者，而是返回所有实际匹配的候选。调用方以后可以选择向用户澄清，也可以在有
评测证据后引入更精确的规则；这些都不属于 5C-4。

## 4. 代码对应关系

- `app/skills/router.py`
  - `_evaluate_candidate()` 收集每组正面证据和全部排除证据；
  - `matched` 只在必需组全部命中且没有排除信号时为真；
  - `route()` 根据完整匹配数量构造三态决策。
- `app/skills/routing_models.py`
  - 约束 outcome 与 reason 的合法组合；
  - 禁止 rejected/ambiguous 决策携带 selected Skill；
  - 要求 selected/ambiguous 的每个候选有正面证据；
  - 禁止匹配候选同时携带排除证据。
- `tests/test_deterministic_skill_router.py`
  - 验证无 Skill、部分匹配、无匹配、排除否决、唯一匹配和多候选歧义；
  - 正反两个候选顺序都必须返回歧义；
  - 被否决候选不能把另一个合法匹配变成歧义。
- `tests/test_skill_router_models.py`
  - 验证非法 outcome/reason、候选、证据组合无法进入上层系统。

## 5. 本阶段证明了什么

- Router 在没有唯一完整匹配时不会擅自执行工作流；
- 排除信号在算法和输出合同两层都是硬否决；
- 多个候选同时成立时，候选顺序不会产生一个伪造的唯一选择；
- 上层可以通过稳定原因码和证据区分“系统没有 Skill”“请求没有匹配”和
  “请求存在多个匹配”。

## 6. 本阶段没有证明什么

- 当前只有 `recent-form-review` 一个真实业务 Skill；歧义算法使用合成候选测试，
  不能证明三个真实业务 Skill 的触发边界已经合理；
- 短语规则不能理解所有自然语言改写，也没有证明语义泛化；
- Router 还不会向用户提出澄清问题；
- Router 不执行 Skill、Tool、Agent Loop 或 Harness；
- 没有引入 Embedding、LLM Router、Pi/Claude Agent SDK 或 LangGraph；
- 是否需要模型兜底必须等到 5C-5 的真实评测证据，再在 5C-6 决策。

这些限制不是遗漏，而是当前检查点的刻意边界。下一检查点不能仅凭合成候选就
宣称真实多 Skill 路由已经完成。
