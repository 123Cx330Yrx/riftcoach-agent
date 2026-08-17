# ADR-0032：在产品入口前建立版本化 Prompt Program V1

## 状态

Accepted

## 日期

2026-08-17

## 背景

RiftCoach 当前模型行为由 Context internal policy、Skill Manifest/SKILL.md、知识工具合同、
Evaluation 1.1、结构化修复和 Revision 多类资产共同决定。实验层已有 Prompt/Context component
fingerprint，但产品 Runtime 仍把 `prompt_profile_id/version` 硬编码为标签，没有生产
Prompt Program loader 或 drift gate。

5P 已被历史退出审查明确指定为 Prompt Program V1 的落点。若直接先暴露 HTTP，Trace 会记录一个
未与真实资产绑定的 prompt identity，不利于回归、评测和面试解释。

## 决策

1. 在 5P 内建立严格 Prompt Program Manifest/Catalog；
2. 复用现有 PromptContextSnapshot 的规范编码和 component fingerprint，不复制摘要算法；
3. V1 覆盖 Skill、Context、knowledge tool、secure Evaluation 1.1 和 bounded Revision 资产；
4. 加载时重新计算组件 fingerprint，Skill/Context/Evaluation/version 任一漂移均 fail closed；
5. production Runtime 从已验证 program resolver 获取 prompt profile identity，不依赖硬编码标签；
6. 先只为 `recent-form-review` 产品入口准入 program；实验 case-context identity 保持独立；
7. 本阶段不以 Program 合同为名调优 Prompt、不调用真实 Provider、不改变 Harness 发布权。

## 后果

### 正面

- Runtime provenance 对应真实可执行资产；
- Prompt 变更必须显式升级身份并通过回归；
- Evaluation 1.1 安全组合不会被旧 CLI 组合静默替换；
- 未来 Prompt 消融、模型对照和阶段 5F Runtime 对照拥有稳定输入身份。

### 负面

- production composition 增加一个 Program Catalog/Resolver；
- 资产变更需要同步版本与 fingerprint；
- 首批只覆盖 recent-form，single-match 的产品 Program 仍待其真实入口。

### 中性

- ContextBuilder、AgentLoop、ToolRuntime 和 ReviewHarness 不被重写；
- 当前真实 Provider 领域质量仍为 unknown；
- 旧实验 snapshot 与不可变结果不修改。

## 备选方案

### 继续使用硬编码 profile 标签

拒绝。标签不能证明真实 Prompt 资产未漂移，Trace provenance 会名实不符。

### 把所有 Prompt 文本复制进一个新模板文件

拒绝。它会复制现有 Context/Evaluation/Revision 逻辑，并可能产生第二套安全合同。

### 立即引入外部 Prompt 平台

拒绝。当前只需要本地版本、fingerprint 和测试；远程注册、发布、权限和可用性会增加没有 Bad
Case 支持的运维复杂度。

## 参考

- `docs/plans/2026-08-17-prompt-program-and-early-product-slice-design.md`
- `app/evaluation/prompt_context_identity.py`
- `app/agent/context.py`
- `app/evaluation/coach_report.py`
- ADR-0029、ADR-0030
