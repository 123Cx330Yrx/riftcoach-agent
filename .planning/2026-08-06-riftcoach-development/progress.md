# RiftCoach 持续开发进度

## 2026-08-06

- 暂停 5C 功能推进，开始上下文连续性和阶段漂移修复。
- 读取 `planning-with-files` 工作规范。
- 审计 Git 工作树、旧规划目录、路线、能力矩阵、项目决策和 5C 实现/测试。
- 确认真实状态：5C-1 至 5C-3 完成；5C-4 有提前实现但未独立验收；5C-5
  有初步开发评测但未收尾；5C-6 未正式开始。
- 新建根级 `AGENTS.md`、唯一当前状态、追加式需求账本和活动计划。
- 审计 2026-08-01 至今的专项材料和原始 Codex JSONL，区分当前、实现、废止、
  条件采用和待裁决内容。
- 新增 `docs/roadmap_change_history.md`；在工作区根增加指向实际仓库的
  `AGENTS.md`。
- 修正 Roadmap、v1.3、能力矩阵、项目决策、Provider 文档、5C 实施计划和旧
  planning 的冲突状态。
- 恢复 Prompt 分层、多模型边界、SDK 采用门、四条进度线、跨阶段深化和首批
  三个 Skill 的历史约束；首批真实 Skill 时序显式标为待裁决。
- 验证：`225 passed, 57 subtests passed`；compileall 通过；`git diff --check`
  只有既有 LF/CRLF 提示；活动文档之外未再发现“5C 已完成/下一步 5D”状态。
- Phase 1 治理修复完成。下一步等待用户授权 5C-4，不进入 5D。
- 用户授权 5C-4 后，独立复核无 Skill、部分匹配、无匹配、排除否决和多候选
  歧义行为；确认确定性 Router 主算法按 fail-closed 原则运行。
- 用失败测试发现 `RouterDecision` 可手工接受“匹配候选同时含排除证据”的合同
  缺口；增加最小不变量校验后通过。
- 新增候选顺序反转、被否决候选不能制造歧义和“最近天气状态怎么样”域外硬
  负例，形成不依赖 5C-5 开发集的 5C-4 直接证据。
- 新增 `docs/plans/2026-08-06-router-rejection-ambiguity-review.md`，固化问题、
  原理、数据流、代码映射、测试与未证明边界。
- 5C-4 定向测试 `23 passed`；本地完整回归 `232 passed, 57 subtests passed`；
  compileall 与治理预检通过。公开提交树仍将在 Git 分组收尾后独立验证。
- Phase 2 完成。当前进入 `5C-5-precondition` 决策门，不执行 5C-5。
- 将暂存区导出为不含 5C-5 WIP 的独立公开快照；结果为
  `228 passed, 57 subtests passed`，compileall 与治理预检通过，证明公开提交树
  不依赖未验收评测文件。临时快照已在校验绝对路径后清理。
- 按 4M、5A、5B/5C-4、治理状态四个逻辑提交推送到 GitHub `main`；本地与
  `origin/main` 同步。GitHub Actions run `31063937488` 的测试、治理预检、
  两层 RAG 门禁、编译、Harness 边界、密钥检查和 dry-run 全部通过。
- 用户进一步指出“有文件”仍不足以保证后续不会靠模型记忆漂移；复核确认原有
  CI 没有项目状态一致性门禁。
- 为 `project_execution_state.md` 增加机器可读状态头；新增
  `scripts/check_project_governance.py`，检查唯一下一步、活动计划、三份规划文件、
  九阶段编号、需求账本和工作约束。
- 将治理预检接入 pytest 和 GitHub Actions，并加入一个故意把下一步改成 5D 的
  负例，证明阶段漂移会被测试拒绝。
- 治理加固完成后，唯一下一步仍为 5C-4 独立复核，没有推进 5C-5 或 5D。
