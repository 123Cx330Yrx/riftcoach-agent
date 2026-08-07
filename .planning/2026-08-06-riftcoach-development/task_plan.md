# RiftCoach 持续开发计划

## Goal

在不改变既定阶段 0-8 和用户已确认子阶段的前提下，以可恢复、可审计、逐步
教学的方式推进 RiftCoach；任何当前状态都必须由仓库文件和测试证据支持。

## Current Phase

Phase 4 - 5C-6 Model Fallback Decision（in progress）

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

- Status: complete
- 本项是进入 5C-5 前的决策门，不是新增主阶段或替代原 5C-5。
- 先形成用户 Skill / 内部 Skill 的初步方案，再回到 Harness/Evaluation 源码复核。
- 发现事实审查已有完整 `EvaluatorStep` 后，用 ADR-0009 取代未实现的内部 Skill
  方案；保留事实审查能力，但不复制为第三个 Skill。

### Phase 2.6 - 5C-5 第二个真实 Skill 准备

- Status: complete
- `5C-5-prep-1`：Skill Invocation Contract，写代码前取消。
- `5C-5-prep-2`：创建用户可路由的 `single-match-review`。
- `5C-5-prep-3`：内部 `report-fact-check` Skill，写代码前取消。
- 明确单局输入输出、触发边界、工具权限、预算、步骤和成功标准。
- 本项完成后才进入 Phase 3；不创建 `report-fact-check` Skill。

### Phase 3 - 5C-5 Router Evaluation 收尾

- Status: complete
- 审计开发集覆盖、指标、门禁和局限。
- 区分 development/calibration 与 independent holdout。
- 记录可复现的最终基线，但不夸大泛化能力。

### Phase 4 - 5C-6 Model Fallback Decision

- Status: in_progress
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

5C-6 Model Fallback Decision：基于 holdout v1 已原样保存的设备语义假朋友 Bad Case，
比较确定性 LoL 域信号、排除词、澄清机制与模型兜底；记录收益、成本、风险和采用
门槛。本检查点先做决策，不默认编写 LLM Router，也不进入 5D。

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
| 两个用户任务进入 Router，事实审查保留为 EvaluatorStep | Router 选择用户意图；Harness 的强制质量端口不是第三种用户任务 |
| 不实现 Skill Invocation Contract | 当前没有真实内部 Skill；为一个重复包装扩展 Manifest 会增加无消费者的抽象 |
| 用 ADR-0009 取代 ADR-0008 原方案 | 保留决策历史，同时确保最终路线由源码证据而不是“三个 Skill”数字驱动 |
| 单局 Skill 接收完整 Summary、确定性报告与唯一 target_match_id | 复用版本化事实契约，同时避免给 Agent Riot API 权限；5D 再抽取最小上下文 |
| 近期与单局范围同时出现时返回 ambiguous | 字面 Router 无法可靠判断语序语义；澄清优于静默丢失其中一个任务 |
| 旧单 Skill 评测先归档，再重建双 Skill 数据集 | 旧 15 案例参与过规则校准且候选集合已变化；保留历史证据，不能冒充当前泛化成绩 |
| development 与 held_out 由数据角色和候选版本快照强制区分 | 防止把旧题库或新 Skill 版本静默放入错误评测，降低人工调规则造成的泄漏 |
| development v2 以 23/23 精确匹配接受并冻结当前规则 | 没有误路由需要修改；继续调词只会增加过拟合风险，下一步应按既定门禁单次运行 holdout |
| 5C-5 以 holdout 11/12 和原样 Bad Case 收尾 | Evaluation 的目标是获得可信证据而不是强制满分；唯一失败已分类且未用于调规则，足以进入 5C-6 方案决策 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 原始 5C-1 至 5C-6 未持久化，文档误写 5C 完成 | 1 | 恢复完整账本，建立根级约束和活动计划，并修正所有冲突状态 |
| 旧规划目录无 active pointer 且停在 2026-08-01 | 1 | 新建持续开发计划并写入 `.planning/.active_plan` |
| `session-logs` 说明依赖的 `jq` 在本机不可用 | 1 | 使用 `rg` 和 PowerShell `ConvertFrom-Json` 流式读取同一原始 JSONL |
| PowerShell 默认读取 UTF-8 中文出现乱码 | 1 | 所有中文审计统一显式使用 `Get-Content -Encoding utf8` |
| 最终并行一致性扫描因 `rg` 无匹配返回退出码 1 | 2 | 无匹配搜索单独运行并显式输出 `NO_STALE_MATCHES`；不再与测试、编译等门禁共享失败传播 |
| 治理文件已有读取协议，但缺少机器可执行的一致性预检 | 1 | 在继续 5C-4 前增加仓库预检脚本、测试和 CI 门禁 |
| 状态源使用 `5C-5-precondition`，活动计划 Current Phase 只写中文简称 | 1 | 在 Current Phase 保留同一机器键，预检随后通过 |
| 治理负例测试硬编码旧检查点 `5C-4`，状态正常推进后失败 | 1 | 改为断言稳定的“Next Step 与 canonical checkpoint 不一致”语义 |
| 暂存区快照命令把计算路径和递归清理写在同一调用，被终端策略拒绝 | 1 | 改用仓库内固定临时目录，先验证快照，再校验绝对路径并分步清理 |
| 假定 `docs/adr/README.md` 存在，实际仓库只有编号 ADR 文件 | 1 | 改读最新 ADR 实例；以后先用 `rg --files docs/adr` 确认文件 |
| 推测 ADR-0003 文件名时使用了不存在的 `quality-gated-review-harness` | 1 | 先列出 `docs/adr`，按真实文件名 `quality-gated-agent-harness` 读取 |
| 恢复 5C-5 第三批时再次直接猜错 ADR-0009 文件名 | 2 | 停止该并行读取，先运行 `rg --files docs/adr`，再按真实文件名读取；将“列目录后读取”继续作为强制恢复动作 |
| 5C-5 收尾多文件补丁因末尾文档换行上下文不匹配而原子拒绝 | 1 | 确认无部分文档修改后，将补丁拆为状态、计划、路线和项目决策小组分别应用 |
| 初步把事实审查分类为内部 Skill，未先核对既有 EvaluatorStep | 1 | 暂停实现，完整审计 Harness/Evaluation 与测试；用 ADR-0009 取代方案并取消重复代码 |
| `python -m pytest` 命中桌面应用 Hermes Python，缺少 pytest | 1 | 改用仓库 `.venv\\Scripts\\python.exe` 执行项目测试，不重复错误解释器 |
| `gh run view/list` 连续两次遇到 GitHub API TLS 握手超时 | 2 | 等待后改用 PowerShell REST 客户端查询同一公开 run，确认 CI 成功 |
| 静态搜索把复杂正则和 PowerShell 双引号混用，导致 unopened group | 1 | 改用单引号与多个 `rg -e` 固定模式，搜索随后成功 |
| 合并测试补丁时把 Router 测试上下文误指到 Contract 测试文件 | 1 | `apply_patch` 原子拒绝、未产生部分修改；按真实文件拆成小补丁后成功 |
| 历史结果的 Windows CRLF 字节哈希在 Linux CI checkout 后变化 | 1 | 仅将该不可变归档标为 Git binary，保留原始字节；两个后续 Actions run 均成功 |
