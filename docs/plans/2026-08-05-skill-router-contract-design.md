# 阶段 5C-1：Skill Router Contract V1

## 1. 本轮目标

5C-1 只定义路由边界，不实现匹配算法。调用方提交用户原始请求和可用 Skill 的最小路由元数据，路由器最终必须返回选择、拒绝或歧义之一。

稳定契约先于算法，可以避免关键词规则、相似度算法或未来模型兜底把自己的内部字段泄露给业务层。

## 2. 输入

`RouterRequest` 包含：

- 非空用户表达 `utterance`；
- 名称唯一的 `available_skills`；
- 每个候选只携带名称、版本、描述和触发信息，不携带工具处理器或执行权限。

候选通过 `SkillRouteCandidate.from_manifest()` 从已经验证的 `SkillManifest` 投影而来。Catalog 可以在构建快照时读取完整包做启动校验，但 Router 不接收或执行 `SKILL.md` 正文；只有选中后，后续 Runtime 才能把该 Skill 的任务指令装配进模型上下文。

## 3. 输出

`RouterDecision` 有三个互斥结果：

```text
SELECTED  → 选择且仅选择一个 Skill，并提供匹配证据
REJECTED  → 无可用 Skill 或没有匹配 Skill
AMBIGUOUS → 至少两个候选同时成立，不擅自选择
```

结果同时包含稳定原因码、候选名称、正负匹配信号和面向 Trace 的说明。V1 不输出浮点置信度，避免确定性规则产生没有统计意义的假精度。

## 4. 不变量

- `selected` 必须使用 `matched_skill` 原因，并具有选中 Skill 的证据；
- `ambiguous` 不得选择 Skill，必须至少包含两个候选及其证据；
- `rejected` 不得携带选中项或候选；
- `no_available_skills` 不得伪造匹配证据；
- 候选、证据和信号不得重复；
- 额外未知字段一律拒绝。

## 5. 本轮不做

- 不扫描 `skills/` 目录；
- 不匹配关键词或自然语言；
- 不调用 LLM；
- 不执行 Skill、Tool 或 AgentLoop；
- 不处理 Provider 选择；
- 不把合规策略混入路由原因码。

后续 5C-2 建立 Skill Catalog，5C-3 才实现第一版确定性匹配。
