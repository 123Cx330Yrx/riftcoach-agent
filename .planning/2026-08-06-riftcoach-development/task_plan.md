# RiftCoach 持续开发计划

## Goal

在不改变既定阶段 0-8 和用户已确认子阶段的前提下，以可恢复、可审计、逐步
教学的方式推进 RiftCoach；任何当前状态都必须由仓库文件和测试证据支持。

## Current Phase

Phase 2.5 - 5C-5-precondition Skill 时序裁决（in progress）

## Phases

### Phase 1 - 修复项目治理与上下文连续性

- Status: complete
- 建立根级工作约束、唯一当前状态和追加式需求账本。
- 启用本计划指针，并修正互相冲突的路线状态。
- 验证文档一致性和现有代码回归。

### Phase 2 - 5C-4 Rejection / Ambiguity 检查点

- Status: complete
- 在继续代码复核前，为活动计划、唯一下一步和需求账本增加机器可检查的预检。
- 讲清拒绝与歧义为什么是 Router 的安全边界。
- 审查已经提前写出的代码和测试，不以“代码存在”代替本检查点验收。
- 只在发现缺口时做最小修补，并等待用户确认后推进。

### Phase 2.5 - 5C-5 前置 Skill 时序裁决

- Status: in_progress
- 本项是进入 5C-5 前的决策门，不是新增主阶段或替代原 5C-5。
- 讲清两个新增真实 Skill 的调用性质、Router 边界和两种实施顺序。
- 取得用户明确裁决后，才更新 Phase 3 的进入条件并开始实现。

### Phase 3 - 5C-5 Router Evaluation 收尾

- Status: pending
- 审计开发集覆盖、指标、门禁和局限。
- 区分 development/calibration 与 independent holdout。
- 记录可复现的最终基线，但不夸大泛化能力。

### Phase 4 - 5C-6 Model Fallback Decision

- Status: pending
- 根据真实 Bad Case 和 5C-5 证据决定暂缓还是引入模型兜底。
- 记录收益、风险、替代方案和采用门槛。
- 本阶段是决策门，不默认需要编写 LLM Router。

### Phase 5 - 进入 5D 前复核

- Status: pending
- 只有 5C-1 至 5C-6 全部完成后，才把唯一下一步改为 5D。
- 对照路线、能力矩阵、需求账本和测试，确认没有遗漏或越级。

### Phase 6 - 按固定 0-8 路线继续

- Status: pending
- 5D 及以后仍按 `docs/roadmap.md` 和后续批准的子阶段逐项展开。

## Next Step

5C-5-precondition：向用户交付 5C-4 结果，并裁决 `single-match-review` 与
`report-fact-check` 的真实调用性质和实施时序。取得明确决定前不得进入 5C-5，
也不得进入 5D。

## Decisions Made

| Decision | Rationale |
|---|---|
| 保留阶段 0-8 和原始 5C-1 至 5C-6 | 防止实现批次反向篡改已经确认的教学与验收顺序 |
| 建立唯一当前状态源 | 多份路线文档不能同时承担动态进度真相源 |
| 不回滚提前实现的 5C-4/5 代码 | 有效实现可以保留，但必须回到原检查点审查和验收 |
| 5C-6 作为证据驱动决策门 | 模型兜底不是默认功能，只有真实 Bad Case 才可能触发 |
| 完整 GPT 导出只用于定向查漏 | 全量历史混有早期和已撤回方案，专项导出与后续明确确认更适合判定当前路线 |
| 首批三 Skill 时序标为待裁决 | 历史承诺没有被撤销，但治理修复也不能直接替用户决定继续维持还是调整 |
| 5C-4 只补合同不变量和边界测试 | 保留已正确的匹配算法，同时让排除信号在算法与决策合同两层都成为硬否决 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 原始 5C-1 至 5C-6 未持久化，文档误写 5C 完成 | 1 | 恢复完整账本，建立根级约束和活动计划，并修正所有冲突状态 |
| 旧规划目录无 active pointer 且停在 2026-08-01 | 1 | 新建持续开发计划并写入 `.planning/.active_plan` |
| `session-logs` 说明依赖的 `jq` 在本机不可用 | 1 | 使用 `rg` 和 PowerShell `ConvertFrom-Json` 流式读取同一原始 JSONL |
| PowerShell 默认读取 UTF-8 中文出现乱码 | 1 | 所有中文审计统一显式使用 `Get-Content -Encoding utf8` |
| 最终并行一致性扫描因 `rg` 无匹配返回退出码 1 | 1 | 将“无匹配”显式视为成功结果后重跑，得到 `NO_STALE_MATCHES` |
| 治理文件已有读取协议，但缺少机器可执行的一致性预检 | 1 | 在继续 5C-4 前增加仓库预检脚本、测试和 CI 门禁 |
| 状态源使用 `5C-5-precondition`，活动计划 Current Phase 只写中文简称 | 1 | 在 Current Phase 保留同一机器键，预检随后通过 |
| 治理负例测试硬编码旧检查点 `5C-4`，状态正常推进后失败 | 1 | 改为断言稳定的“Next Step 与 canonical checkpoint 不一致”语义 |
| 暂存区快照命令把计算路径和递归清理写在同一调用，被终端策略拒绝 | 1 | 改用仓库内固定临时目录，先验证快照，再校验绝对路径并分步清理 |
