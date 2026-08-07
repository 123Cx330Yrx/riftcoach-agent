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
- 用户在收到明确推荐后以“继续”授权 `5C-5-precondition`，确认保留三个真实
  Skill，但区分用户路由与内部质量调用。
- 接受 ADR-0008：近期复盘和单局复盘为 `user_routable`；报告事实审查为
  `internal`，由 Harness/Runtime 显式调用，不进入用户 Router。
- 固化 `5C-5-prep-1 -> prep-2 -> prep-3 -> 5C-5 -> 5C-6` 的小步顺序；
  本轮只完成决策和文档，不编写调用模式或新 Skill 代码。
- 在准备实现前回查 `app/harness`、`app/evaluation`、独立评测 CLI 和相关测试，
  发现 `report-fact-check` 与现有 `EvaluatorStep` 完整重叠。
- 两份独立源码审查均建议保留 Harness Evaluator，不新增内部 Skill；定向 Harness /
  Evaluation 测试证据覆盖首次评测、复评、非法输出、异常降级与发布门禁。
- 用 RQ-024 和 ADR-0009 修正初步方案：事实审查能力继续强制存在，但不再分类为
  Skill；ADR-0008 保留为未落地且已取代的历史方案。
- `5C-5-prep-1` 调用模式合同与 `prep-3` 内部事实审查 Skill 均标记为写代码前
  取消，没有伪装成已完成；唯一下一步沿用原编号 `5C-5-prep-2`，建立
  `single-match-review`。
- 首次比例化测试命令命中 Hermes 自带 Python，因未安装 pytest 而在测试收集前
  退出；已确认应改用仓库 `.venv`，该结果不计为项目测试失败。
- 改用仓库 `.venv` 后，Harness、Evaluation 与治理定向回归为 `30 passed`；
  `compileall` 通过，`git diff --check` 仅显示既有 LF/CRLF 转换提示，治理预检通过。
- 架构裁决提交 `5f288cb` 已推送到 GitHub `main`；本地 HEAD 与 `origin/main`
  一致，五个未验收 5C-5 WIP 文件保持未跟踪、未提交。
- GitHub CLI 两次查询遇到 TLS 握手超时；等待后改用公开 REST API 成功确认
  Actions run `31066598955` 对提交 `5f288cb` 的结论为 `success`。
- 恢复唯一检查点 `5C-5-prep-2`，运行治理预检通过，并完整复核 Summary Schema、
  MatchAnalyzer、现有 Skill Contract、Catalog、Router、ADRs 和边界测试。
- 比较三种单局输入方案后采用 `player_summary + deterministic_report +
  target_match_id + focus`；不授予 Riot API 权限，短局可审查，Timeline 缺失必须
  保持未知语义。
- 新增 `single-match-review` 的 Manifest、SKILL.md 和独立 Pydantic I/O；输出显式
  携带目标 match ID，唯一工具仍为 `knowledge.search`。
- 初版把 `最近十局里这一场` 设为更具体的单局范围，并尝试用连接词拒绝真正的
  “这场 vs 最近”比较；后续 Bad Case 证明该连接词方案会漏掉双任务语序。
- 先写测试得到预期红灯：缺少 `app.skills.single_match_review`；实现后 Contract、
  Catalog、Router 定向测试通过。
- 全部已跟踪回归为 `238 passed, 57 subtests passed`；五个未验收 5C-5 WIP 文件
  保持未跟踪、未修改。
- `5C-5-prep-2` 完成。当前进入 5C-5 Router Evaluation；第一批先冻结旧单 Skill
  基线并重建双 Skill 数据集角色，不进入 5C-6 或 5D。
- 首次提交前聚合验证因陈旧短语搜索无匹配返回 `rg=1` 而丢失并行输出；这不是
  测试失败，但重复了已记录陷阱。已改为关键门禁与“无匹配即成功”搜索分开重跑。
- 并行只读复核构造“分析最近十局状态，再复盘这一场”，发现初版会静默只选
  单局 Skill；新增两种语序和候选顺序 Bad Case，先得到 3 个预期失败。
- 删除两个真实 Skill 之间的范围互斥词，混合范围统一返回 `ambiguous`；保留版本、
  实时和天气等域外否决。近期 Skill 因触发合同变化升级到 `0.2.0`。
- 补充单局输入缺失目标 ID、坏 Summary、空白报告和裸 Match ID 拒绝测试；修正后
  Contract、Catalog、Router 定向测试为 `37 passed`。
- 最终已跟踪回归为 `240 passed, 57 subtests passed`；compileall、治理预检和
  `git diff --check` 通过，后者只有既有 Windows LF/CRLF 提示。
- 当前状态文件的陈旧短语扫描输出 `NO_STALE_MATCHES`；历史进度与变更记录保留
  已被推翻的初版方案，不参与当前状态冲突判定。
- 只暂存本检查点 18 个文件；五个 5C-5 评测 WIP 文件保持未跟踪。由 Git 索引
  生成的公开树测试为 `240 passed, 57 subtests passed`，全部已跟踪 Python 文件
  编译、治理预检和 cached diff check 均通过。
- 创建并推送 `4103d42 feat(skills): add single match review contract`；GitHub Actions
  run `31068654700` 对同一 SHA 完成且结论为 `success`。
- 进入 5C-5 第一批后，审计五个 WIP 文件，确认旧 15 条结果只有单一
  `recent-form-review@0.1.0` 候选，且精确运行 SHA 无法恢复；旧案例和结果原样移入
  history 目录，以 SHA-256 和重建来源 Manifest 冻结，不再作为当前默认数据集。
- 新增双 Skill development v2（23 条）与 independent holdout v1（12 条），分别
  声明角色、候选版本快照、案例数量、污染记录和封存规则。development 保留用于
  调试，holdout 不能用于调规则。
- 扩展路由评测契约，加入数据集生命周期校验、候选版本漂移校验和 ambiguity accuracy；
  CLI 默认 development 模式拒绝 holdout，未运行任何新数据集正式 Router 评测。
- 第一批定向验证：`12 passed`；完整回归为 `252 passed, 57 subtests passed`；当前唯一下一步改为只运行双 Skill development v2
  并分析误路由，仍不得进入 holdout、5C-6 或 5D。
- 第一批提交 `1d13128` 推送后，Actions run `31075838501` 在 Linux 的历史结果
  SHA-256 测试失败；原因是 Git 把原始 CRLF 文本规范化为 LF，本地字节哈希不能
  跨平台复现。
- 为该单一不可变历史快照增加 Git binary 属性并重新存入原始字节；修复提交
  `8bfb876` 的 run `31076388257` 成功，属性收尾提交 `318755d` 的 run
  `31076432192` 也成功。普通 JSON 仍保持文本 diff，不扩大 binary 范围。
- 运行治理预检通过后，按授权只执行双 Skill development v2；没有运行 holdout，
  也没有调用 Skill、Tool、Harness 或模型。
- development v2 的 23 条全部精确匹配：selection/rejection/ambiguity accuracy 均为
  `1.0`，false-selection rate 为 `0.0`；明细为 10 selected、11 rejected、2 ambiguous，
  mismatch 为 0。
- 结果保存到 `data/evaluation/results/skill_router_v1_development_baseline.json`；
  当前开发规则接受并冻结，唯一下一步改为单次运行 independent holdout v1 并原样分析。
- 收尾验证：Skill/Router 定向测试 `62 passed`；完整回归
  `252 passed, 57 subtests passed`；compileall、治理预检和 `git diff --check` 通过。
  diff check 只有既有 Windows LF/CRLF 转换提示。

## 2026-08-07

- 恢复 `5C-5` 第三批时首次并行读取猜错 ADR-0009 文件名；没有运行评测或修改文件。
  随后先列出 `docs/adr` 并按真实路径读取，错误已写入计划错误表。
- 确认工作树干净、HEAD 为 `4c86e3e`、holdout 结果不存在；治理预检和
  `tests/test_skill_router_evaluation.py` 的 12 个生命周期测试通过。
- 对比 holdout 声明的冻结提交与当前 HEAD，Router、文本规范化和两个 Manifest
  零差异；候选仍为 `recent-form-review@0.2.0` 与
  `single-match-review@0.1.0`。
- 带显式 `--mode held_out --confirm-rules-frozen` 单次运行 holdout v1；结果为
  11/12，selection/ambiguity accuracy 为 `1.0`，rejection accuracy 为 `0.8333`，
  false-selection rate 为 `0.1667`。
- 唯一失败把“分析一下我最近键盘的表现”选为近期复盘；分类为字面 Router 无法
  理解目标实体所属领域的真实 Bad Case。未修改触发词、排除词、Router 或标签。
- 5C-5 完成，当前唯一下一步推进为 5C-6 Model Fallback Decision；本轮不做该决策。
- 收尾验证：Skill/Router 定向测试 `62 passed`；完整回归
  `252 passed, 57 subtests passed`；compileall、治理预检与陈旧状态扫描通过。
