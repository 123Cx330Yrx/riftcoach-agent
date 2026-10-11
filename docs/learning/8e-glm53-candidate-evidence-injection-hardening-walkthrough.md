# 8E 学习记录：候选领域门的证据与注入边界加固（RQ-228）

## 1. 这次解决什么问题

RQ-227 暴露了两个不同的缺口：检索工具可能返回“调用成功”但没有任何可归因来源；
用户或知识资料也可能夹带看起来像指令的文本。前者会让报告失去证据基础，后者会让
模型把数据误当成控制指令。两种情况都不能因为最终评分高就发布。

## 2. Agent 原理

Agent 的工具结果是数据，不是新的系统指令。可靠运行时要把“事实是否存在”“输出是否
安全”“是否达到质量线”拆成独立的闸门，并在发布前由 Harness 做最终裁决。候选实验
可以复用同一个控制面，但必须用显式版本和作用域隔离，不能把实验参数偷偷变成产品默认。

## 3. 实现地图

- `app/harness/models.py`：`HarnessConfig.minimum_evidence_sources`，默认 0，候选显式设 1。
- `app/harness/runtime.py`：写入检索证据后先执行来源数闸门，再执行候选稿 guard。
- `app/skills/review_executor.py`：把两个可选边界安全地传入现有 Harness。
- `app/agent/context.py`：候选专用可信 policy 附录；默认上下文字节不变。
- `app/agent/draft_safety.py`：marker 无关的拒绝性脱敏与 fail-closed 决策器。
- `app/evaluation/provider_domain_production.py`：只在显式 `quality_hardening=True` 的候选
  执行器中接线，并把检索状态投影成 body-free 诊断计数。
- `app/evaluation/domain_e2e.py` 与 `provider_domain_experiment.py`：以冻结、受限的
  `EvidenceDiagnostics` 记录调用/片段/来源计数，兼容旧回执字节。

## 4. 数据与控制流

```text
冻结 Input Plan
      ↓
可信 system policy（仅候选）
      ↓
AgentLoop → knowledge.search → KnowledgeEvidence 工件
      ↓
来源数 ≥ 1？ ─否→ evidence_required / 不发布
      ↓是
候选 draft guard：明确拒绝可脱敏；其余出现 fail closed
      ↓
引用/事实/注入评测 → Harness 唯一发布权
      ↓
body-free EvidenceDiagnostics
```

## 5. 如何验证

本地聚焦和相邻集合合计 `102 passed`，覆盖：默认上下文不变、候选 policy 位于 system
trust、空检索拒绝、明确拒绝时脱敏、执行式/歧义 marker 拒绝、真实本地 RAG 的诊断计数。
`compileall`、`git diff --check` 与 `scripts/check_project_governance.py` 均通过。

## 6. 失败、安全和边界

脱敏器不识别具体 RQ-227 字符串，而是要求调用方提供当前案例 marker；异常只返回安全
错误码，不带原始文本。空证据仍然失败，不增加重试或恢复。旧 RQ-227 回执不可覆盖，
也不能用这批离线代码反推模型已准入。GLM-5.2、正常 Runtime、Portal、Account、
Workbench、Auth 和 `production_media=0` 都保持不变。

## 7. 后续运行手册

本实现 `e2efe8fd75e8cf27cbee7e90484fc90d288ce065` 已由 Actions `33832025848`
完成 exact-SHA 三 job 公共验证；下一步创建全新的协议/题目版本并重新做 no-I/O admission。
只有新的明确授权才可发起一次有界真实领域观察。观察结果仍需独立
通过证据、安全、质量、成本/延迟和黄金切片闸门，不能直接注册为默认模型。

## 面试表达

> 我把 RQ-227 的失败拆成“检索有调用但没有来源”和“数据块里的指令越过边界”两条，
> 在候选作用域内增加来源数硬门、可信策略附录和 marker 无关的拒绝性脱敏；默认产品
> 行为保持不变，所有公开诊断只留安全计数，避免把一次修复或高分误写成生产准入。

当前检查点：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-evidence-injection-hardening / completed-public / pending-next-decision`
