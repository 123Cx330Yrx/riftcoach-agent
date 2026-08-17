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
- 开始 5C-6 后复核 Router、RouterDecision、两个 Manifest、GLM Provider 能力和
  holdout Bad Case；确认模型只处理 rejected/ambiguous 无法捕获本次 selected 错误。
- 比较设备排除词、强 LoL 域信号、类型化入口/澄清、LLM 语义复核和 Embedding/
  分类器五类方案，并显式检查性能、可靠性、安全、维护和成本。
- 新增教学设计文档与 ADR-0010，决定 5C V1 暂缓 LLM Router fallback；没有修改
  Router、Manifest、Provider 或 holdout。
- 追加 RQ-026，记录重新采用模型必须具备新鲜失败族、新数据集、结构化输出、
  质量/延迟/成本/故障证据和 fail-closed 边界。
- 5C-6 完成；唯一下一步推进为 `5C-exit-review`，尚未进入 5D。
- 提交前完整 diff review 发现 5D 重复列项，以及教学文档把 5P 现有近期 API
  误写为近期/单局 API；已收紧为既有 5P 近期切片与阶段 6 完整入口，不新增路线范围。
- 5C-6 收尾聚焦回归（Skill/Router/Provider）为
  `80 passed, 14 subtests passed`；完整回归为 `252 passed, 57 subtests passed`。
- `compileall`、`git diff --check` 和治理预检通过；收窄后的当前状态陈旧短语扫描
  输出 `NO_CURRENT_STALE_MATCHES`。首次过宽扫描只命中正确保护语句，已记录并修正。
- 首次 `git diff --cached --check` 发现 ADR-0010 末尾多余空白行；已删除并准备
  重新验证，没有改变决策内容。
- 开始 `5C-exit-review` 后重新审计 Router/Catalog/Contract/两套数据集、结果、
  ADR-0010 和 5D 前置边界；治理预检在修改前通过。
- 新增两个命中证据身份负例，先得到预期 `2 failed`；随后最小收紧
  `RouterDecision`，要求 selected/ambiguous 的 evidence Skill 集合与 candidate
  Skill 集合完全一致，模型测试恢复为 `15 passed`。
- Git 审计发现 holdout 声明的 `cfd2084` 尚不包含双 Skill 合同；真实冻结提交为
  `4103d42`，且到首次 holdout 结果 `6a0d952` 的 Router/规范化/Manifest 零差异。
  只更正元数据并加断言，没有改案例、标签、规则或既有结果，也没有重跑 holdout。
- 为 5C-4 历史教学补演进说明，并新增完整 5C 退出复核文档，讲清数据/控制流、
  跨层职责、评测解释、已知限制、框架替换边界、5D 前置项和面试安全表述。
- 5C 聚焦测试 `66 passed`；完整回归 `256 passed, 57 subtests passed`。5C 退出复核
  通过，状态只推进到 5D 为唯一下一步，未实现任何 5D 功能。
- 首次状态切换后全量回归有 1 条治理负例失败：它把 `5D` 硬编码为陈旧 Next Step，
  而 5D 现在正是合法检查点。已改为稳定的 `stale-checkpoint`，避免合法阶段推进反向
  使负例失效；这没有改变治理脚本本身。
- 修复治理测试后，最终完整回归 `256 passed, 57 subtests passed`；compileall、
  `git diff --check` 与治理预检全部通过。diff check 仅有既有 Windows 换行提示。
- 进入 `5D-entry-design` 后按强制恢复顺序读取唯一状态、活动计划、需求、路线、
  能力矩阵和架构非功能检查表；治理预检通过，起始工作树干净。
- 完整复核 AgentLoop、Provider contract/capability、ToolRuntime、两个 Skill I/O 与
  Manifest、ReviewHarness、chat adapters、Prompt/Parser、FileRunStore 和相关 ADR。
- 发现核心接缝：旧 Harness 是 eager retrieval + one-shot generation，AgentLoop 是
  dynamic tool use；直接并存会产生两套证据路径，Agent 全接管又会复制质量门禁。
- 比较三种方案后新增 ADR-0011，接受 AgentLoop 作为 evidence-aware
  `DraftPreparationStep`，ReviewHarness 保持唯一发布者。
- 新增 5D 初学者设计文档，覆盖问题、目标数据流、Context trust 分层、Token 预算、
  结构化输出、失败模式、测试、后续边界和面试表述。
- 将 5D 拆为 5D-1 至 5D-7 与 exit review；canonical 下一步仅为 5D-1 Skill Run
  Boundary Hardening，本批没有实现任何 5D 功能代码。
- 5D entry design 回归：完整 pytest `256 passed, 57 subtests passed`；compileall、
  `git diff --check` 与治理预检通过。只有既有 Windows LF/CRLF 提示。
- 开始 5D-1 后先新增设计与 TDD 实施计划，明确本轮只做 Skill I/O、selected
  identity/version、安全 run ID 与输入内容绑定，不进入 Context Builder。
- Skill I/O 红灯为 `5 failed, 13 passed`；统一输入报告、输出 run/report、来源和
  warning 的去空白、非空与去重规则后恢复为 `18 passed`。
- Router 版本红灯为 `2 failed, 31 passed`；`RouterDecision` 增加
  `selected_skill_version`，真实 Router 从命中候选填入版本，相关回归为 `47 passed`，
  没有重跑或改写 sealed holdout。
- run ID 红灯覆盖 Manifest、Store 与 Skill 输出的路径、盘符、Windows 保留名、
  空格和超长值；三处改用一个共享规范后为 `32 passed, 25 subtests passed`。
- 新增 `SkillExecutionBoundary`、输入 Artifact 内容承诺与 Harness 共享字节编码；
  先得到缺少 execution module 的预期收集错误，最小实现后执行边界 `11 passed`。
- 深层可变性复核发现 frozen model 不会冻结嵌套 dict；补红灯后改为内部深拷贝快照
  与对外副本，避免调用方修改已验证输入。
- 5D-1 聚焦回归 `107 passed, 25 subtests passed`；完整回归
  `276 passed, 80 subtests passed`；compileall、`git diff --check` 与治理预检通过。
- 状态同步后的首次陈旧短语扫描再次把含 `|` 的 rg 正则放进 PowerShell 双引号，
  命令解析失败但未改文件；改用单引号多个 `-e` 后成功，仅命中应保留的历史记录。
- 5D-1 本地实现与教学验收完成；唯一下一步改为 5D-2 Context Builder V1，尚未
  构造 Context、编译 `AgentRunRequest` 或调用 AgentLoop/Tool/Provider/Harness。
- 创建并推送 `6bc4309 feat(skills): harden skill run boundary`；本地 HEAD 与
  `origin/main` 一致。GitHub Actions run `31179571780` 对该精确 SHA 的治理、pytest、
  两层 RAG 门禁、compileall、Harness 边界、密钥检查和 dry-run 全部成功。
- 开始 5D-2 后先冻结 Context Builder 设计与五任务 TDD 计划；明确输出为
  `ContextBundle` 而不是 `AgentRunRequest`，不引入 LangGraph、Pi 或厂商 tokenizer。
- Task 1 先以缺少 `app.agent.context` 得到预期收集红灯；实现 trust、section、bundle
  与确定性 sizer 合同后为 `8 passed`。
- Task 2 为近期复盘增加真实 Catalog/Router/ExecutionBoundary 测试；最终只投影
  allowlisted scope/aggregate/boundary/report，最多构造 10 个可选 match sections，
  不复制未知扩展和 failed-match 原始异常文本。
- Task 3 为单局复盘只投影唯一 target row；`recent_summary`、其他 match ID 与跨局
  报告行不会进入 Context，短局和 Timeline unavailable 的 null/empty/error 语义保留。
- Task 4 将每个初始 KnowledgeCitation 投影为独立 data-only optional section；恶意
  用户、事实和知识字符串不能获得 instructional/system 语义。重复/空白 citation
  fail closed。
- 预算选择以 Manifest `max_context_tokens` 为硬上限，调用方只能降低；required
  context 先验不合格时失败，optional 按 priority 和原顺序逐个整段尝试，并记录
  omitted IDs。默认 sizer 是稳定启发式，不声称等于真实 Provider Usage。
- 5D-2 聚焦 Context/Skill/Provider 回归为 `61 passed, 17 subtests passed`；完整回归
  为 `292 passed, 80 subtests passed`；compileall 与 `git diff --check` 通过。
- 按不可信输入安全复核检查权限提升、注入、错误泄漏和最小数据暴露；未发现需要
  扩大本检查点的高危问题。角色/JSON 分层仍只是一层防御，模型级攻击与动态 Tool
  Observation 必须在 5D-3/5D-7 继续验证。
- 创建并推送 `9275d9c feat(agent): add context builder v1`；GitHub Actions run
  `31185773854` 对精确 SHA `9275d9c8d73a364bb30d6f532cdb8b1da369ccbd`
  完成且结论为 `success`。
- 用户以“继续下一步”授权唯一检查点 5D-3；按强制恢复顺序读取状态、活动计划、
  需求、路线、能力矩阵、ADR-0011、5D/Context 设计和相关源码，session catchup 无
  未同步内容，治理预检通过，起始工作树干净。
- 初始审计确认 `AgentRunRequest` 尚无 context ceiling，`AgentLoop` 尚无逐轮累积消息
  检查，默认 sizer 也未计入 ToolCall 参数；5D-3 将先写独立设计/TDD 计划，不执行
  Provider、ToolRuntime、AgentLoop 或 Harness。
- 比较扩展现有请求/Loop、外层预算包装器和 metadata-only 三种方案；采用薄
  `AgentRunCompiler` + 现有 AgentLoop guard，拒绝复制循环和假门禁。
- 新增 5D-3 初学者设计与五任务实施计划；明确 Context integrity、Manifest-only
  permission/budget 编译、完整消息 sizing、累计 Context 保护和 cooperative total
  deadline，仍不进入 draft/evidence 或 Harness composition。
- Task 1 红灯为 2 个预期失败：ContextBundle 接受伪造 messages，AgentRunRequest
  缺少 context ceiling/停止原因。最小实现加入 canonical rendering 校验、
  `max_context_tokens` 与 context/timeout stop reasons 后为 `24 passed`。
- Task 2 先以缺少 `app.agent.compiler` 得到预期收集红灯；最小实现
  `AgentRunCompiler` 后，两个真实 Skill 的 Manifest 权限/预算映射、身份漂移、Ceiling、
  重新估算溢出和未注册工具测试为 `8 passed`，相关边界回归为 `40 passed`。
- Task 3 先证明长短 ToolCall arguments 都被旧 sizer 估为 `13`；随后改为完整消息
  envelope 的确定性 JSON 估算，Context/Provider 合同回归为
  `34 passed, 17 subtests passed`。
- Task 4 的红灯为 `5 failed, 18 passed`：Loop 尚不能注入 ContextSizer/FakeClock，
  ToolRuntime 尚无 run remaining cap。实现逐轮 Context 门禁与协作式总 deadline 后，
  Loop/ToolRuntime 为 `23 passed`。
- FakeSizer 证明初始溢出时 Provider 调用为 0，Tool Observation 导致溢出时第二次
  Provider 调用被阻止；FakeClock 证明 Provider timeout 从 10 秒递减到 5 秒，工具只
  获得当时剩余 8 秒，deadline 过期后不执行工具。
- 5D-3 聚焦 Compiler/Context/Loop/ToolRuntime/真实 knowledge 工具集成回归为
  `85 passed, 17 subtests passed`；完整回归为 `308 passed, 80 subtests passed`；
  compileall 与 `git diff --check` 通过，后者只有既有 Windows 换行提示。
- 5D-3 本地实现与教学验收完成；唯一下一步改为 5D-4 Evidence-Aware Agent Draft
  Preparation。尚未创建 draft preparer、转换 `KnowledgeEvidence`、调用真实 Provider、
  组合 Harness 或产生 terminal Skill Output。
- 5D-3 状态同步后的首次聚合检查又把“无匹配返回 1”的陈旧短语 `rg` 与治理/格式
  门禁放进同一并行批次，导致聚合调用失败且隐藏其他输出；没有修改文件，也不是
  代码测试失败。随后按既定规则单独运行并得到 `NO_CURRENT_STALE_MATCHES`，再独立
  确认治理预检与 diff check 通过；复发次数已写回错误账本。
- 创建并推送 `6f25108 feat(agent): enforce skill run budgets`；本地功能提交与
  `origin/main` 一致。GitHub Actions run `31191462744` 对精确 SHA
  `6f251082ae03059961bd508bdbc43c4f1bf247af` 的治理、pytest、两层 RAG 门禁、
  compileall、Harness 边界、密钥检查和 dry-run 全部成功。

## 2026-08-08

- 用户以“继续下一步”授权唯一检查点 5D-4；按强制恢复顺序读取 canonical state、
  活动计划、需求、路线、能力矩阵、ADR-0011 与 5D 设计，session catchup 无未同步
  内容，治理预检通过，起始 HEAD/origin 均为 `98bbda0` 且工作树干净。
- 初始源码审计确认 AgentLoop 已保留实际 `ToolExecutionRecord`，`knowledge.search`
  输出已由 ToolRuntime 做 Schema 校验，旧 `LocalRagAdapter` 已有单次 payload 到
  `KnowledgeEvidence` 的转换；5D-4 将抽取共享纯转换器而不是复制或重新检索。
- Task 1 已先以缺少 `app.harness.knowledge` 得到预期收集红灯。首个实现补丁因猜错
  `app/harness/__init__.py` docstring 被原子拒绝；确认没有部分源码修改后，改为读取
  真实文件并拆分小补丁，错误已写入计划账本。
- Task 1 已完成：新增共享 fail-closed 知识 payload 转换器，旧 `LocalRagAdapter`
  改为复用同一实现；单/多检索、稳定 K1、去重、拒答、count 与归因冲突测试连同
  旧 Harness Adapter 回归为 `11 passed`。
- Task 2 已完成：新增不可变 `AgentDraftPreparationResult` 与薄
  `SkillAgentDraftPreparer`；它从 AgentLoop 的同一 ToolRegistry 编译请求，并拒绝
  非 completed、无最终文本、失败知识调用及非知识工具执行。相关 Agent/Compiler/
  Loop 回归为 `25 passed`。
- Task 3 已完成：两个真实 Skill 均通过真实 Catalog、Router、ExecutionBoundary、
  ContextBuilder、Compiler 与 AgentLoop；Fake Provider 调用真实本地
  `knowledge.search`，模型虚构的 `ghost-only.md` 没有进入 Evidence。
- Task 4 已完成：补齐真实 ToolRuntime 输出 Schema 失败与 max-tool/duplicate/timeout
  停止边界；Agent、Context、ToolRuntime、RAG 与 Harness Adapter 聚焦回归为
  `102 passed`，失败路径不会返回半成品 preparation result。
- Task 5 本地收尾进行中：功能完成后的首次完整回归为
  `325 passed, 80 subtests passed`，compileall 与 diff check 通过；canonical state、
  活动计划、路线历史、v1.3、能力矩阵和项目决策均只推进到“5D-4 完成、5D-5
  唯一下一步”，治理预检与当前状态陈旧短语扫描通过。
- 状态同步后的最终完整回归仍为 `325 passed, 80 subtests passed`；compileall、
  `git diff --check` 与治理预检全部通过，diff check 只有既有 Windows 换行提示。
- 按真实 GitHub Actions workflow 复跑本地门禁：RAG development 8 条与 independent
  holdout 7 条的 Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation support 也为
  `1.0`；Harness 旧路径 dry-run published，SDK 边界与 tracked secret/run-data 检查
  均通过。该 dry-run 只验证旧 Harness 兼容性，不表示 Agent 草稿已接入 Harness。
- 创建并推送 `dfe357c feat(agent): prepare evidence-aware skill drafts`；GitHub Actions
  run `31206608536` 对精确 SHA `dfe357ccd9680f7a406dad43a7d39fed3820e951`
  完成且结论为 `success`。5D-4 本地实现、教学证据与公开 CI 均完成；唯一下一步仍
  是 5D-5，本轮不进入。
- 用户授权唯一检查点 5D-5；恢复 canonical state、活动计划、需求/路线/ADR 和 5D-4
  交接后，确认起始工作树干净，`HEAD` 与 `origin/main` 均为 `21ca076`。
- `session-catchup.py` 无未同步输出，治理预检通过。初始源码审计确认本轮需要一个
  `DraftPreparationStep` 接缝、旧顺序 Adapter、Skill/Harness 组合执行器和只读
  terminal Artifact 到 typed Skill Output 的构造器；不需要第二套 Harness。
- 审计时一组并行读取因无匹配 `rg` 返回 1 而整体失败；随后拆分命令完成读取。另两次
  猜测不存在的 output schema 聚合文件路径失败，已改为先读取真实 Manifest 中的模型
  引用，再定位 `recent_form_review.py` 与 `single_match_review.py`。
- 5D-5 Task 1/2 已按 TDD 完成：新增统一 `DraftPreparationStep` 与顺序 Adapter，
  `ReviewHarness` 只依赖一个 preparation step，CLI 显式适配旧 Retriever/Generator；
  Harness/Step/Provider Tool 聚焦回归为 `21 passed`。
- Task 3 已完成：新增只读 `SkillTerminalOutputBuilder`，从 terminal Manifest、FINAL_REPORT、
  最终 attempt Evaluation、RETRIEVAL_EVIDENCE 和两份输入 Artifact commitment 构造
  Manifest 声明的 Pydantic Output；发布、修订、降级、拒绝、篡改和错误 Output Model
  的 7 个测试通过。
- Task 3 首次测试 helper 直接用未规范化的报告计算 commitment，正确触发 5D-1 boundary
  mismatch；修正为先经过真实 Skill Input Model，再用规范化内容生成 commitment，没有
  放宽生产校验。
- Task 4 已完成：`SkillReviewExecutor` 校验 execution/context identity，从 Manifest 唯一
  映射 85 分阈值与 fallback，把 `AgentDraftPreparationResult` 降格为 Harness 中立结果，
  并在外层保留真实 AgentRunResult；组合测试累计 `13 passed`。
- 首次从 `app.skills.__init__` 重导出 executor 时触发 Agent compiler/Skill package 循环
  import；移除根包重导出，改为显式 `app.skills.review_executor` 模块边界后测试通过，
  没有使用延迟 import 掩盖依赖问题。
- Task 5 已完成：近期状态与单局复盘均通过真实 Catalog/Router/Boundary/ContextBuilder/
  AgentLoop/本地 RAG/Harness 到 typed output；Fake Provider 共两轮调用真实
  `knowledge.search`，15 个 executor 测试通过，未调用真实 Provider。
- 5D-5 聚焦回归覆盖 Harness、Skill、Agent、ToolRuntime 与 RAG：
  `179 passed, 25 subtests passed`；完整回归为 `343 passed, 80 subtests passed`，
  compileall、`git diff --check` 与治理预检通过。
- 旧 `scripts/run_review_harness.py --dry-run` 经顺序 Adapter 仍得到 published；临时
  run 文件已清除。首次递归删除命令被终端策略拒绝，随后使用 `apply_patch` 删除已验证
  路径下的全部生成文件，没有使用跨 shell 删除。
- canonical state、活动计划、路线补充、能力矩阵与项目决策开始同步为“5D-5 完成、
  5D-6a 唯一下一步”；本轮仍未实现结构化 Provider 输出或调用真实 Provider。
- 按真实 GitHub Actions workflow 复跑本地门禁：RAG development 8 条与 independent
  holdout 7 条的 Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation support 均为
  `1.0`；Harness SDK 边界、tracked secret/run-data 检查和临时目录 dry-run published
  全部通过。
- 首次 `git diff --cached --check` 只发现两份新增设计/实施文档尾部各一行多余空白；
  已删除尾部空白并重新暂存，未改功能代码。
- 创建本地功能提交 `24e761c feat(agent): compose skill drafts through harness`；首次
  push 遇到 GitHub schannel TLS 握手失败，提交仍完整保留，待按瞬时网络故障重试。
- 第二次相同 push 仍为 schannel TLS 握手失败；停止原样重复，下一次改用命令级
  `http.sslBackend=openssl`，不改变仓库或用户的持久配置。
- Git smart-HTTP 经 schannel、OpenSSL、HTTP/1.1 与 TLS1.2 共五次仍在 GitHub TLS
  握手层失败；GitHub CLI 认证和 API、443 TCP 均正常，SSH 诊断则无已授权公钥。
- 改用 GitHub Git Database API：19 个提交文件逐一以本地 Git blob bytes 上传并核对
  SHA，tree SHA 精确等于 `8b558dc`。首次 commit body 因 PowerShell 多行消息成为数组
  返回 422，remote ref 未更新；改成单行后发现 API 与 CLI 只差消息尾部换行字节。
- 在不改项目 tree 的前提下精确重建 API commit `7662dea`，先以 expected-old
  `21ca076` 原子更新远端 main，再以 expected-old `24e761c` 同步本地 main；本地 HEAD、
  origin/main 与远端 API 三方均为 `7662dea335e28f76edb78a7c0ac3d07680412cc1`。
- GitHub Actions run `31232630971` 已对精确功能 SHA `7662dea` 完成，结论为
  `success`；5D-5 的本地实现、教学证据和公开 CI 均已完成。
- 5D-5 文档收尾提交 `3fc1e05` 已与 `origin/main` 同步；公开 Actions run
  `31234711309` 对同一 SHA 成功，起始工作树干净。
- 用户以“继续下一步”授权唯一检查点 5D-6a；按强制恢复顺序读取 canonical state、
  活动计划、需求/路线/能力矩阵、ADR-0011、Provider/Tool/Harness/Evaluation 源码和测试，
  治理预检通过，HEAD 与 origin/main 均为 `3fc1e05`。
- 恢复时一次把工具返回包装误当 `.active_plan` 内容，一次猜测不存在的
  `app/tools/contracts.py`；两次均为只读失败且未改文件，已按不同方法恢复并写入错误账本。
- 比较“只换 Pydantic parser”“Harness 内另建结构化调用路径”和“现有 Provider/Tool
  请求合同贯通”三种方案，采用第三种：请求声明 Schema、能力协商、Tool Adapter 传递、
  Evaluation Adapter 严格验证与最多一次修复。
- 新增 5D-6a 初学者设计和 TDD 实施计划；当前只把检查点标记为进行中，功能代码尚未
  开始，真实 GLM、第二 Provider、Prompt E2E 和 5D-6b 继续被阻止。
- Task 1 先为 `StructuredResponseContract` 与 capability 需求写红灯；缺少合同类型时
  Provider 测试收集失败。实现后 Schema 在 Draft 2020-12 校验后递归冻结，结构化请求
  会要求 `STRUCTURED_OUTPUT`，Provider 定向回归为 `21 passed, 15 subtests passed`。
- Task 2 先以缺少 `app.providers.structured` 得到预期红灯；新增严格 Pydantic decoder、
  合同/模型一致性校验、截断拒绝与一次 repair callback 后为
  `27 passed, 22 subtests passed`。错误不会包含原始模型输出。
- Task 3 先证明 `llm.chat` 忽略 response contract；扩展 Tool Schema/Handler 后，合同
  进入 `ChatRequest`。当前 text-only `ZhipuProvider` 对结构化请求在 SDK 调用前拒绝，
  三个聚焦测试通过。
- Task 4 用 `EvaluationResponseModel`/`EvaluationIssueModel` 统一 Prompt Schema 和严格
  parser。fenced JSON 不再走宽容抽取，而是按 5D-6a 的一次 repair 处理；评测合同与
  decoder 回归为 `12 passed, 11 subtests passed`。
- Task 5 替换 `ChatEvaluationAdapter` 的任意 dict parser：初始评测和最多一次 repair
  都携带同一 contract，完整 `ChatResponse` 保留 finish reason 供截断判断。适配器与
  Provider/Tool 集成回归为 `11 passed`。
- Harness failure 测试首次漏导入 `CoachDraft`，只覆盖到草稿准备降级；修正 fixture 后，
  确认两次非法 JSON 触发 `invalid_structured_output`，Harness 只持久化确定性报告。
- 5D-6a 聚焦回归为 `89 passed, 40 subtests passed`；完整回归为
  `359 passed, 95 subtests passed`。compileall、diff check 和治理预检通过，当前状态只
  推进到 5D-6b；尚未调用真实 Provider、实现 Zhipu 原生 Schema 映射或选择第二厂商。
- 5D-6a 提交 `ecb8234` 已推送到 GitHub `main`；Actions run `31255771786` 对精确
  SHA `ecb82341467634dce865c65f886340c295b8388f` 完成且结论为 `success`。公开进度线
  已与本地状态一致，当前唯一下一步仍为 5D-6b。

## 2026-08-09

- 用户以“继续下一步”授权 5D-6b；本轮按活动计划只设计 Real Provider Capability
  Gate，不调用真实 Provider、不预选第二厂商，也不进入 5D-7。
- 已完整恢复 canonical state、活动计划、需求账本、路线、v1.3 与能力矩阵；治理预检
  通过，起始工作树干净，`HEAD` 与 `origin/main` 均为 `ad068ce`。
- 初始源码审计确认当前 Zhipu Adapter 只映射 text chat；Provider-neutral structured
  output、Tool Calling、AgentLoop 与 Harness 合同已经就绪，但真实厂商 transport 与
  response normalization 尚未实现。
- 第一次同步 canonical status 与项目决策的组合补丁因错误假设 `截至` 独占一行而原子
  拒绝，没有产生部分修改；按真实文本拆分后已把 5D-6b 标为实验设计进行中，并修正
  5D-6a 已完成但项目决策仍重复写“Provider-neutral 结构化响应未实现”的陈旧表述。
- 首次状态同步治理预检发现 canonical 正文缺少固定“唯一下一步”行；这不是功能测试
  失败。保留进行中状态并恢复唯一一条该元数据后再运行治理检查。
- 已核对智谱官方 Function Calling、结构化输出与 chat completions 文档：GLM-5.2 声明
  支持工具调用，公开 `tool_choice` 仅有 auto；结构化模式为 `json_object`，未声明原生
  strict JSON Schema transport。因此设计保留 5D-6a 本地 Pydantic 为最终权威。
- 新增 5D-6b 设计草案，比较文档直接开关、整链先行和两层准入三种方案；采用“最多
  5 次微探针 → Adapter 离线 TDD → 最多 7 次领域切片”，GLM 全部通过时不比较第二
  Provider，出现真实协议/预算阻断才筛选最多一个候选。尚未调用真实 Provider。
- 设计草案同步后的治理预检通过，治理测试 `2 passed`，`git diff --check` 通过；本轮
  只有文档和持久计划变化，没有运行功能回归或消耗模型额度。
- 首次提交前把 `git diff --cached --check` 与 commit 用分号串行，检查正确发现设计
  文档 EOF 多余空行，但没有阻止 commit。已立即删除空行并写入错误账本；后续改为
  检查与提交分开执行，不重复该流程错误。
- 删除 EOF 空行并把流程错误写入账本后，将设计草案提交为 `ef97ec7` 并推送至
  `origin/main`；GitHub Actions run `31297965601` 对精确 SHA
  `ef97ec72358f7f803f09d63a68c7bc32bcc98385` 完成且结论为 success。该公开证据只证明
  文档/治理和既有回归通过，不证明任何真实 GLM capability。
- 用户明确确认 5D-6b 实验实现，并询问“边界”含义；已解释它主要是 Provider 合同
  兼容边界，不是预判 GLM 模型能力不足。
- 官方 Schema 进一步确认函数名只允许字母、数字、下划线和连字符，内部
  `knowledge.search` 不能原样发送。设计补入请求级确定性别名表，并新增七任务实施
  计划；当前第一批严格限制为 Task 1-3 和最多 5 次真实微探针。
- 实施计划首次治理预检发现 Next Step 虽指向正确实施文件，但未包含 canonical
  `5D-6b` 字面键；预检在功能代码前正确阻止。已补回同一检查点名称，范围未变化。
- 5D-6b Task 1 先以缺少 `app.evaluation.provider_capability_gate` 得到预期收集红灯；
  最小实现新增严格、冻结的 case/report Pydantic 合同和 `ExternalCallBudget`。passed
  必须有输出摘要，failed/skipped 必须有安全错误码，5 次后第 6 次在调用前被拒绝。
- Task 1 目标测试为 `4 passed`；上游调用即使抛错也会消耗一次预算，而预算拒绝本身
  不会执行或计数，从而不能用重试掩盖真实调用成本。
- 5D-6b Task 2 已完成离线 TDD：新增隔离的 `ZhipuCapabilityProbe` 与显式授权 CLI，
  P1 失败会跳过 P2-P5，P4 失败会跳过 P5；SDK `max_retries=0`，结果只保留摘要哈希、
  安全错误码、usage、延迟和解析后的状态，不落盘原始提示、响应、request id 或异常。
- CLI 只允许精确 5 次预算，并把结果限制在
  `data/evaluation/results/provider_capabilities/`；未带 `--confirm-real-call` 时在创建客户端
  前拒绝。Task 1/2 目标测试 `10 passed`，与现有结构化输出和评测合同的聚焦回归为
  `23 passed, 11 subtests passed`，完整回归为 `370 passed, 95 subtests passed`，
  compileall、治理预检和 diff check 通过。P1 还会精确校验约定哨兵，不把任意非空文本
  误记为 baseline 通过。
- 一次宽回归命令猜测了不存在的 `tests/test_provider_structured.py`，pytest 未收集测试；
  已先列出真实路径并重跑正确集合，不把空跑计作证据。Task 3 真实 P1-P5 微探针尚未执行。
- 离线探针提交 `b07f986` 已推送到 `origin/main`，GitHub Actions run `31302982591`
  对精确 SHA `b07f986421b1c14ef36656f3a44698decacc9d24` 完成且结论为 success；因此真实
  结果可以追溯到公开、通过 CI 的探针代码。
- Task 3 已按用户授权执行一次真实 P1-P5：本地必需配置均存在，模型为 `glm-5.2`；
  `.env` 的 `LLM_PROVIDER=glm` 只在子进程规范为内部 ID `zhipu`，没有修改或打印密钥。
  P1 在 4265 ms 后以 `invalid_text_response` 失败，只消耗 1/5 次；P2-P5 按依赖规则全部
  skipped，结果落盘为 `zhipu_glm52_p1_p5.json`，未自动重试。
- 该结果说明 API 调用返回后，message content 未满足非空文本合同；它不是认证、限流、
  超时、连接或 HTTP 状态错误。但现有脱敏失败记录没有保留 finish reason、resolved model
  和 usage，因此不能进一步判断空内容原因，也不能据此断言 GLM 不支持 RiftCoach。
  按计划停止 Task 4，下一步只允许设计 P1 诊断补强与新的显式调用授权。

## 2026-08-10

- 用户以“继续下一步”授权 canonical 唯一动作：5D-6b P1 脱敏诊断补强设计与离线
  实现；本轮不重新调用真实 GLM，不进入生产 Adapter Task 4，也不选择第二 Provider。
- 已按强制顺序恢复 canonical state、活动计划、需求/路线/能力矩阵与 5D-6b 设计；
  治理预检通过，起始 `HEAD` 与 `origin/main` 均为 `9333b66`，工作树干净。
- 恢复时猜错 ADR-0011 文件名，只有只读命令失败且未改代码；列出真实 ADR 目录后
  改读 `0011-compose-skill-agent-loop-through-harness-preparation.md`，错误已写入账本。
- 已比较“只留错误码”“本地保存原始响应”“公开白名单元数据”三种 P1 诊断方案，
  推荐第三种；新增初学者设计草案，定义安全 observation、Schema v1.1 兼容、失败
  数据流、测试和单调用 diagnostic scope。本批没有修改功能代码或调用真实 Provider。
- 设计状态同步后的治理预检与治理测试通过（`2 passed`），`git diff --check` 通过；
  当前唯一下一步是用户确认设计后的离线 TDD，确认不等于授权真实模型调用。
- 用户以“继续下一轮”确认 P1 白名单诊断设计，只授权离线 TDD。实施前把旧 v1.0 的
  未采集 `response_received` 收紧为 `null/unknown`，避免伪造 false；新增四任务实施
  计划，本轮按 executing-plans 只执行首批 Task 1-3，不调用真实 GLM。
- P1 诊断 Task 1 先得到 `3 failed, 4 passed` 的预期红灯；实现 v1.0/v1.1、probe scope、
  response/content/reasoning 状态及一致性校验后为 `7 passed`。旧实验字节不变且读取为
  unknown，新 v1.1 必须明确 true/false，diagnostic 永远不能误标为完整 Provider admitted。
- Task 2 新测试先使旧 probe 出现 `9 failed, 1 passed`：v1.1 正确拒绝丢失 observation
  的旧构造。实现冻结的白名单 `_SafeResponseObservation` 后，语义失败仍保留 model、
  finish、usage、request hash 与字段形状；SDK 异常明确未收到响应，reasoning/content
  原文不落盘。Task 1/2 聚焦回归为 `17 passed`。
- Task 3 的 scope/CLI 红灯为 `16 failed, 1 passed`；实现 `p1_p5/5` 与
  `p1_diagnostic/1` 精确配对、独立默认输出路径和 scope 控制流后，P1 成功也只调用
  一次且 `admitted=false`。Task 1-3 聚焦回归为 `24 passed`，全部使用 Fake SDK，
  没有读取本地 Key 或进行网络调用。
- 首批 Task 1-3 的 Provider/structured/CLI 比例回归为 `82 passed, 42 subtests passed`；
  compileall、治理预检和 `git diff --check` 通过。本轮未执行完整 pytest、未读取密钥、
  未调用 GLM；这些与状态收尾留给下一批 Task 4。

## 2026-08-12

- 用户以“继续下一步”授权 canonical 唯一动作：5D-6b P1 脱敏诊断 Task 4 离线收尾；
  本轮没有授权或执行真实 GLM 调用。
- 起始治理预检通过，工作树干净，`HEAD` 与 `origin/main` 均为 `f7a2f87`。
- 完整本地回归为 `383 passed, 95 subtests passed`；Provider/structured 比例回归仍为
  `82 passed, 42 subtests passed`。
- RAG development 与 independent holdout 门禁全部通过，Recall/MRR/nDCG 均为 `1.0`；
  holdout abstention 与 citation support 也为 `1.0`。
- compileall、Harness SDK boundary、tracked secret/run-data 检查和 Harness dry-run 均
  通过；dry-run 产物只写入系统临时目录。
- 离线实施计划现已完成。唯一下一步收紧为等待用户单独授权一次真实
  `p1_diagnostic/1`；未获授权不得读取 Key、创建真实客户端或调用 GLM，授权也不包含
  P2-P5、生产 Adapter、第二 Provider 或 5D-7。
- 首次公开 CI run `31610552899` 在测试收集阶段失败：无上界 `openai` 当天解析为
  `3.0.0` 并安装 `httpx2`，但现有 SDK 2.x 错误合同测试直接使用 `httpx`。本机仍为
  `openai 2.44.0`，所以本地未暴露该干净环境差异。修复范围只收紧已验证依赖合同为
  `openai>=2,<3`，不借 Task 4 升级 SDK 大版本或修改 Provider 行为。
- 随机新建的 TEMP venv 从 `.[dev]` 完整安装后解析为 `openai 2.54.0` 与
  `httpx 0.28.1`，全量回归仍为 `383 passed, 95 subtests passed`。该证据排除了依赖
  本机旧环境的假通过；临时环境未写入仓库。
- 修复提交 `be7a872` 已推送；GitHub Actions run `31611205222` 对精确 SHA
  `be7a8723a6f2785e8d1d87f4f493705abfb5925c` 全部通过，包含 pytest、两套 RAG 门禁、
  compileall、治理、Harness SDK boundary、secret/run-data 和 Harness dry-run。
- 用户明确授权一次真实 `p1_diagnostic/1`。首次 CLI 启动在创建客户端前被
  `LLM_PROVIDER=glm` 与内部 `zhipu` ID 不一致拦截，真实外部调用数为 `0`；未修改
  `.env` 或读取/打印 Key。下一次只在子进程中规范 Provider ID 后执行该唯一授权请求。
- 仅在子进程把 `LLM_PROVIDER` 规范为内部 ID `zhipu` 后，真实 diagnostic 使用 1/1 次
  调用并得到 `P1_text_baseline=passed`。报告仍按合同写 `admitted=false`，没有继续
  P2-P5。结果保存为 `zhipu_glm52_p1_diagnostic.json`，code SHA 为 `6ee7476`。
- 脱敏 observation 为 content/reasoning 均 `non_empty`、finish `stop`、22/115 tokens、
  4563 ms、tool calls 0；只保存 request/output 哈希，没有模型正文、推理正文、原始
  request ID 或 Key。下一步必须另行授权完整 `p1_p5/5`，本轮不自动继续。
- 脱敏实验结果提交 `a05551e` 已推送；GitHub Actions run `31611988551` 对精确 SHA
  `a05551e7ea97422f70722b2fefee4e2349a643f8` 全部通过。CI 没有本地 `.env`，不会产生
  额外模型调用；它只验证提交后的结果合同与仓库回归。
- 用户明确授权完整 P1-P5 和此后 5D-6b 内有脚本硬预算、无盲目重试的真实测试；该
  长期控制面要求记录为 RQ-027，不扩大到第二 Provider、生产 Adapter 或后续阶段。
- 完整 `p1_p5/5` 在 `dbcce14` 上只执行一次并使用 4/5 calls：P1/P2 passed；P3 为
  `finish_reason=length`、1024 output tokens、reasoning non-empty/content empty；P4 返回
  1 个 ToolCall 但旧参数精确相等合同失败；P5 按依赖 skipped。结果独立落盘且
  `admitted=false`，没有自动重试。
- 恢复诊断时误写 `app/evaluation/zhipu_probe.py` 路径，并猜测不存在的
  `ProviderCapabilityReport` 类名；两个只读命令失败、未改文件。随后先从实际导出和
  `rg --files` 定位到 `app/providers/zhipu_probe.py` 与 `CapabilityProbeReport`，不再原样
  猜测。
- 官方文档复核确认 GLM-5.2 默认 Thinking，交错式 Thinking + Tool 需要回传完整
  reasoning；受控方案决定 P2-P5 显式 disabled-thinking，继续由本地 Pydantic/JSON
  Schema 掌握严格验收，不保存或回传思维链。
- 新增受控诊断设计与实施计划。Fake SDK 红灯精确得到 3 failed/16 passed，分别命中
  缺少 disabled-thinking、query 逐字相等误拒和 P4 reasoning 未阻断 P5；最小实现后
  `tests/test_zhipu_capability_probe.py` 为 19 passed。尚未再次调用真实 GLM。
- 首次多文件状态补丁因活动计划真实换行与截断输出推测不一致而被 `apply_patch` 原子
  拒绝，未产生半更新；改为先读取真实相邻行并拆分小补丁，随后完成同步。
- 受控探针提交前比例回归为 `56 passed, 21 subtests passed`，完整回归为
  `389 passed, 95 subtests passed`；第一轮结果通过 Schema v1.1 复读，RAG development
  与 holdout 门禁、compileall、治理、Harness SDK boundary、tracked secret/run-data、
  结果脱敏扫描、diff check 与 Harness dry-run 均通过。下一步先公开验证探针代码 SHA，
  再执行新的有界真实调用。
- 受控探针代码提交 `860c203` 已推送；GitHub Actions run `31614219338` 对精确 SHA
  `860c2035435afb5a914a2d9c403876df42138478` 全部通过，CI 没有真实 Provider 调用。
- 随后的真实轮在 P1 使用 1/5 calls 后按依赖停止：content empty、reasoning non-empty、
  `finish_reason=length`、22/128 tokens，P2-P5 全部 skipped。该结果证明 P1 也必须显式
  disabled-thinking；新增测试先让旧实现失败，再做单行请求策略修正，不原样重跑。
- P1 修正后的聚焦回归为 `30 passed`，完整回归仍为 `389 passed, 95 subtests passed`；
  compileall、治理、结果 Schema/脱敏和 diff check 通过。修正提交 `6a15a00` 已推送，
  GitHub Actions run `31614645836` 对精确 SHA 全部通过。
- 最终受控 P1-P5 使用 5/5 calls 并全部 passed，报告 `admitted=true`。所有 case 的
  reasoning state 为 missing；P4 返回一个合法 ToolCall，P5 在固定只读 Observation 后
  返回 final text。结果只保存脱敏元数据和哈希，未保存模型正文或思维链。
- 新增公开结果集合合同测试，CI 将遍历 provider capability 目录全部 5 份 JSON 并按
  版本化 Pydantic 模型复读。最终聚焦回归 `31 passed`，完整回归
  `390 passed, 95 subtests passed`；compileall、治理和 diff check 通过。
- 最终结果提交 `880ba1b` 已推送；GitHub Actions run `31615159223` 对精确 SHA
  `880ba1b4e9fd74fcfbd8d568a3c16218bad48ad4` 全部通过，包含 390-test 回归、两套 RAG
  门禁、compileall、治理、安全边界和 Harness dry-run。下一步保持生产 Adapter 离线
  TDD，不因微探针通过而跳到领域切片或 5D-7。

## 2026-08-13

- 用户以“继续下一步”授权 5D-6b 生产 Zhipu Adapter 离线映射；按强制恢复顺序读取
  canonical state、活动计划、需求/路线/能力矩阵与 5D-6b 设计，治理预检通过，起始
  HEAD/origin 均为 `232e71d` 且工作树干净。
- 先补四类消息、ToolSpec、AUTO/NONE、JSON mode、ToolCall response、REQUIRED、坏
  arguments、未知别名、重复 ID 与别名冲突测试；旧实现得到预期
  `11 failed, 11 passed`，确认缺口真实存在。
- 生产 `ZhipuProvider` 现显式 disabled-thinking，映射 structured contract 为
  `json_object`，并用请求级可逆别名编码/解码 `knowledge.search`；内部 Manifest、
  Registry、AgentLoop 与 ToolRuntime 不改名。
- 响应边界拒绝非 function、非严格 JSON object、NaN、重复键、未知别名、规范化后重复
  ID、并行 ToolCall、坏 content 与非空 reasoning；历史 ToolCall 参数也使用严格 JSON
  编码。REQUIRED 与尚未准入的 structured+tool 同轮组合在调用前拒绝，不能静默降级；
  ToolCall 存在性与 `finish_reason=tool_calls` 必须一致。
- 严格 JSON 补强的首个多文件补丁因 hunk 格式错误被 `apply_patch` 原子拒绝，没有半
  修改；拆为小补丁后最终 Zhipu 测试为 `26 passed, 22 subtests passed`。
- 聚焦 Provider/Structured/AgentLoop 回归为 `73 passed, 50 subtests passed`；完整回归
  为 `405 passed, 103 subtests passed`，compileall、diff check 与治理预检通过。
- 新增初学者教学复核文档。当前只完成生产 Adapter 离线映射，唯一下一步仍在 5D-6b：
  先为真实 Adapter structured/tool 协议切片设计并 TDD 化硬预算与脱敏结果；不进入领域
  Skill、第二 Provider 或 5D-7。
- 功能与文档快照以提交 `75159e9e8501d246986520a5341e2d82e3f8196d` 推送到
  `origin/main`；GitHub Actions run `31619089608` 对该精确 SHA 的全测试、RAG 开发/
  独立 holdout、compileall、Harness SDK 边界、敏感文件和 dry-run 门禁全部通过。

### 2026-08-13：5D-6b Adapter Protocol Slice 离线 TDD

- 比较扩展 raw 微探针、复制两轮调用器和组合现有 AgentLoop 三种方案；采用共享预算
  Provider + 现有 AgentLoop，不新增第二套控制流。
- 新增严格 `AdapterProtocolSliceReport` 与两个顺序 case：A1 structured contract、
  A2 agent tool round trip。成功路径必须精确使用 3 次模型调用，失败依赖会 skipped，
  第 4 次调用在底层 Provider 前 fail closed。
- A1 复用 `EvaluationResponseModel` 和严格 decoder；A2 只注册固定、只读、幂等、一次
  执行的 `knowledge.search` fixture，并要求一轮 ToolCall、一轮 observation 后 final。
- 扩展 Provider probe CLI：新增显式 `adapter_protocol` scope、精确 `max_calls=3` 和独立
  脱敏输出路径；真实 client 固定 `max_retries=0`，pytest/Fake SDK 不访问网络。
- 新增异常、结构化失败、跳过、直接回答、坏工具参数、别名往返、CLI 授权/预算和公开
  JSON 脱敏测试。全量测试首次发现 evaluation 根包重导出造成循环 import；移除重导出
  后通过。
- 聚焦回归：`22 passed`；跨 Provider/Structured/AgentLoop/Tool 回归：
  `85 passed, 53 subtests passed`；完整回归：`415 passed, 103 subtests passed`；
  compileall 与 diff check 通过。
- 当前仍是离线证据。唯一下一步：提交、推送并核验精确 SHA 的公开 CI，随后按 RQ-027
  执行一次精确 3-call 真实 Adapter 协议切片；不执行领域 Skill、第二 Provider 或 5D-7。
- 协议控制器提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51` 已推送；GitHub
  Actions run `31625669630` 对精确 SHA 全部通过。
- 随后只运行一次真实 `adapter_protocol/3`：A1 structured 使用 1 call，A2 AgentLoop
  工具往返使用 2 calls，总计 3/3，全部 passed，`admitted=true`。结果 code SHA 与公开
  CI 提交一致，并通过 Pydantic 复读与原文/异常/ID 脱敏检查。
- 真实 A1 为 427/59 tokens、2344 ms；A2 为 562/36 tokens、5360 ms，finish sequence
  为 `tool_calls -> stop`，工具调用和成功执行均为 1。成本因无可靠单价快照保持 null。
- 当前 5D-6b 尚未完成。唯一下一步改为 Recent-form Domain Slice 离线设计/TDD，先对齐
  原定累计 7-call 上限与已用 3 calls；本轮不直接执行领域 Skill、第二 Provider 或 5D-7。

### 2026-08-13：5D-6b Recent-form Domain Slice 离线控制器

- 用户要求继续并询问为何 5D-6b 持续较久；已解释该检查点分为低层 Provider 协议准入
  和真实领域 Skill/Harness 准入，前者已真实通过，本批完成后者的离线安全控制器。
- 新增领域设计与实施计划、`DomainSkillSliceRunner`、严格脱敏报告合同和显式真实调用
  CLI；复读并哈希已准入的 3-call 协议结果，将领域调用固定为剩余最多 4 calls。
- 同一个 observed budget Provider 同时注入 AgentLoop 与 Harness；正常路径精确为 Agent
  2 calls + Evaluation 1 call，一次结构化 repair 可使用第 4 call，revision 后再评测在
  第 5 次领域调用进入底层 Provider 前被拒绝。
- 真实 `recent-form-review` 已在 Fake Provider 下完整经过 Catalog、Router、Boundary、
  Context、AgentLoop、本地 `knowledge.search`、唯一 ReviewHarness 和 typed output；
  准入 CLI 固定 SDK `max_retries=0`，Harness LLM Tool 为单次尝试、无缓存/无 fallback。
- 代码复核后补强两条合同：`admitted=true` 必须让每次计费调用都有脱敏响应元数据；
  CLI 在读取配置和创建客户端前拒绝覆盖已有领域结果，防止重复实验与证据覆盖。
- 最终审计再补充脏工作树门禁：真实 CLI 必须在创建客户端前确认所有执行代码已提交，
  避免结果中的旧 HEAD SHA 冒充包含未提交修改的实际代码。
- 聚焦回归为 `23 passed`；相邻纵向比例回归为 `141 passed, 29 subtests passed`；全量
  回归为 `430 passed, 103 subtests passed`。
- RAG development 与 independent holdout 的 Recall/MRR/nDCG 均为 `1.0`，holdout
  abstention 与 citation support 也为 `1.0`；compileall、Harness SDK boundary、tracked
  secret/run-data、diff check 和 Harness dry-run 均通过。
- 新增初学者复核文档，讲清 Provider Adapter、AgentLoop、ToolRuntime、Skill、Harness、
  数据流/控制流、累计 3+4 call、pre-I/O budget、脱敏证据和面试表述边界。
- 本批未读取 API Key、未创建真实客户端、未调用 GLM，且未生成
  `zhipu_recent_form_slice.json`。唯一下一步为提交/推送/验证精确公开 CI；随后才按
  RQ-027 执行一次有界真实领域切片，不进入第二 Provider 或 5D-7。
- 离线控制器提交 `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 已推送；GitHub
  Actions run `31657764638` 对精确 SHA 的全测试、两套 RAG、compileall、Harness SDK/
  敏感文件边界和 dry-run 全部通过，CI 未调用真实 Provider。
- 按实施计划，本离线批次停止在真实调用之前。唯一下一步收紧为按 RQ-027 运行一次
  累计 7-call、领域剩余最多 4-call 的真实 GLM recent-form 切片并原样保存脱敏结果；
  不进入第二 Provider 或 5D-7。

### 2026-08-13：5D-6b 真实领域结果与部分采用收尾

- 在公开 CI 成功代码 `f5e97ead20c5aa7d4798f308bd60e820842061bc` 上只运行一次
  真实 recent-form 领域切片；使用领域 1 call，累计 4/7，没有重试或 Prompt 调整。
- 真实请求发生后没有统一 `ChatResponse` 进入 Agent 结果：response/tool/evidence 均为
  0，`agent_status=null`；因此不能把它描述成模型直接回答或单纯忘记调工具。
- 领域链未进入 Evaluation，没有质量分；Harness 以 `degraded` 返回确定性报告，证明
  真实 Provider 失败没有让未经评测的 Agent 草稿越过发布门禁。
- 脱敏证据无法区分 Adapter 响应规范化拒绝和其他统一响应形成前的 Provider 错误；
  上层结果将其归为 `knowledge_round_trip_incomplete`。该安全错误来源丢失已登记为
  5D-7 可观测性 Bad Case，本批不改功能代码、不恢复临时原文、不重跑实验。
- 新增 ADR-0012：Zhipu 最小 structured/tool 协议准入，GLM-5.2 recent-form 领域能力
  不准入，确定性 fallback 保留，第二 Provider 暂缓到同任务 5D-7 评测合同冻结后决定。
- `5D-6b` 因准入门已作出可审计接受/拒绝结论而完成；唯一下一步推进到
  `5D-7 Prompt/Context & Domain E2E Evaluation`，并不表示领域能力或整个 5D 已完成。
- 真实失败结果与 ADR-0012 提交 `34ea5c3` 已推送；GitHub Actions run
  `31659371226` 对精确 SHA `34ea5c32e5c124207fcba7b0521a4e5a62af6845` 全部通过。

### 2026-08-13：5D-7 Batch A 分层领域评测

- 按 canonical 下一步进入 5D-7，没有重跑 5D-6b、调 Prompt、调用真实 Provider 或
  接入第二 Provider；起始治理通过，HEAD/origin 均为 `88f4e19`，工作树干净。
- 源码审计确认安全错误来源丢失发生在 draft-preparation 接缝：失败
  `AgentRunResult.error_code` 被异常边界压缩，上层只看到笼统草稿准备失败。
- 比较单样例调 Prompt、只用 Judge 看最终报告、分层领域评测三种方案；ADR-0013
  采用第三种，并把 development/held-out 生命周期、四态 layer verdict、白名单失败码和
  可空资源语义写入设计。
- 新增严格 `DomainEvaluationDataset`、`DomainCandidate`、`DomainEvaluationResult`，
  分层检查 Provider/Agent、Tool、Evidence、Evaluation、Terminal 与 Resources；Candidate
  Schema 禁止 Prompt、模型正文、思维链、原始 request ID、异常或 Key。
- development v1 有 10 个离线观测，包含 5D-6b 真实脱敏失败、发布安全与资源边界；
  任务结果和主失败分类均为 10/10，故意不安全发布为 1/10，外部 Provider 调用为 0。该成绩只证明
  评测器对已知观测的回归，不是模型质量。
- TDD 红灯先命中缺少 `app.evaluation.domain_e2e`，实现后只剩冻结基线缺失；生成离线
  基线后聚焦合同测试为 `11 passed`，相邻比例回归为 `47 passed, 4 subtests passed`，
  compileall 和临时输出复跑通过。
- 最终全量回归为 `441 passed, 103 subtests passed`；RAG development 与 independent
  holdout 的 Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation support 均为
  `1.0`；Harness SDK、tracked secret/run-data、dry-run、候选脱敏扫描、compileall、
  governance 和 diff check 均通过。
- 当前 5D-7 仍进行中。唯一下一步为 Batch B Prompt/Context 评测身份和可重复实验入口；
  不调 Prompt、不运行真实 Provider、不创建 held-out、不接第二 Provider。
- Batch A 提交 `9f0d7d1177ac84c4d25c3397da85bf8e43859a6f` 已推送；GitHub Actions
  run `31661582544` 对该精确 SHA 全部通过。
- `gh run watch/view/list` 在 CI 查询期间依次遇到 unexpected EOF 和两次 TLS handshake
  timeout；没有重复长连接。改用 `curl` 公开 REST 查询并设置 10 秒连接、20 秒总上限，
  成功确认 run 已 completed/success。该网络问题没有影响 CI 或提交内容。

### 2026-08-13：5D-7 Batch B Prompt/Context 实验身份

- 比较人工版本号、只哈希最终消息、组件 + 案例双层语义指纹三种方案；ADR-0014 采用
  第三种，避免未升版本的行为漂移，也保留变化定位能力。
- 新增严格 `PromptContextSnapshot` 和 `DomainExperimentAdmission`：组件层覆盖 Skill
  Manifest/Instructions、Context Policy、`knowledge.search` 合同、Evaluation Schema/
  事实投影与 prompt builders；案例层覆盖 Artifact、typed options、section、最终消息
  和 Context 预算。
- 快照通过真实 Catalog、Router、ExecutionBoundary 与 ContextBuilder 离线重建；冻结
  `recent-form-prompt-context-v1` 自摘要为
  `88af3ed94e2458dc67e92c311de3543ca23c5923c0591ad83cfa3d2db6fd95e0`。
- Domain E2E Dataset/Candidate/Result 升至 Schema 1.1，案例和标签未改；当前 10 案例
  离线基线重新生成，任务结果与主失败分类保持 10/10，外部调用保持 0。
- 新增离线 preparation CLI；只有当前重建快照、冻结快照与 Dataset 声明完全一致才
  产生 `admitted=true`。有效 Skill 或 fixture 漂移、伪造自摘要、合同漂移和项目外输入
  都会在 Provider 前失败关闭。
- TDD 红灯先证明模块和 1.1 绑定缺失；实现与冻结后，快照/领域聚焦测试 `20 passed`，
  相邻纵向回归 `87 passed, 4 subtests passed`，完整回归
  `450 passed, 103 subtests passed`。
- RAG development 与 independent holdout 的 Recall/MRR/nDCG 均为 `1.0`，holdout
  abstention/citation support 均为 `1.0`；compileall、Harness SDK boundary、tracked
  secret/run-data、Harness dry-run、公开快照正文脱敏、治理和 diff check 均通过。
- 领域 1.1 基线与 admission 从 CLI 临时输出逐字节复现；任务结果/主失败分类保持
  10/10，故意 unsafe publication 保持 1/10，admission 为 `admitted=true` 且外部调用 0。
- 当前 5D-7 仍进行中；唯一下一步为 Batch C 入口设计与离线 TDD，以 Batch B admission
  作为所有可执行 development 候选的前置门，再验证工具、事实、引用和模型级注入。
  不直接运行真实 Provider、不创建/运行 held-out、不接第二 Provider、不进入 5E。
- Batch B 功能提交 `e56b00091ef2ab299af692e902945b8342fbc99e` 已推送；GitHub
  Actions run `31690698734` 对该精确 SHA 的全测试、两套 RAG、compileall、治理、
  Harness SDK/tracked-data 和 dry-run 门禁全部通过，CI 未调用真实 Provider。

### 2026-08-13：5D-7 Batch C 离线可执行基线

- 完成源码接缝审计和初学者设计，ADR-0015 选择 Scripted Provider + 真实本地控制流，
  没有修改 Prompt、接入第二 Provider 或调用真实模型。
- TDD 红灯先因 `app.evaluation.domain_e2e_offline` 缺失失败；实现后新增 Schema 1.2
  `offline_executable` 合同、7 案例 development Dataset、执行 Runner 和零调用 CLI。
- 每个场景先经过 Batch B admission，再运行真实 Skill/AgentLoop/ToolRuntime/local RAG/
  Harness；验证 happy path、缺工具、坏事实、坏引用、用户注入、RAG 注入和注入漏判。
- 冻结 Candidate/Result 可由 CLI 逐字节复现：task outcome accuracy `1.0`、failure
  classification accuracy `1.0`、unsafe publication rate `0.142857`、external calls `0`。
- 聚焦/相邻测试 `25 passed`；全量 `455 passed, 103 subtests passed`；RAG development/
  independent holdout、compileall、Harness SDK/tracked-data、artifact 脱敏、governance、
  diff check 和 Harness dry-run 全部通过。
- 当前仍是 5D-7 in progress。下一步为 Batch D 入口设计，不直接调用真实 Provider、
  不立即创建/运行 held-out、不接第二 Provider、不进入 5D exit review 或 5E。
- Batch C 功能提交 `06cf769be54c8062aeddcd8c36283306e63bfc9a` 已推送；GitHub
  Actions run `31705232946` 对精确 SHA 全部通过，CI 未调用真实 Provider。

### 2026-08-13：5D-7 Batch D 入口设计

- 按 canonical 唯一下一步恢复 AGENTS、执行状态、活动计划、需求账本、路线、修订和
  能力矩阵；起始治理通过，HEAD/origin 均为 `2a83d6b`，工作树干净。
- 源码审计确认 Batch C canary oracle 与生产 Evaluator 是两层：生产 1.0.0 没有注入
  issue，Prompt 只含 fact pack/report，用户请求与实际知识证据没有提供给 Evaluator。
- 比较生产关键词扫描、原地扩展 1.0.0、版本化安全评测 Profile 三种方案；采用第三种，
  新增初学者设计与 ADR-0016，明确保留历史合同并后续实现 1.1.0。
- 冻结 D1-D5 顺序：离线合同/阻断 TDD、新 snapshot/development、规则冻结后创建
  held-out、第二 Provider 新 ADR、最后才做有硬预算的同任务真实比较。
- 真实首轮上限被设计为每 Provider 3 场、每场最多 4 calls、领域最多 12 calls、
  `max_revisions=0`、SDK retry 为 0；第二 Provider 另有最多 3-call Adapter 协议门。
- 本入口批没有改生产 Schema/Prompt/Harness，没有创建或运行 held-out，没有读取 Key、
  创建真实客户端或调用模型，也没有选择第二 Provider。
- 唯一下一步更新为 5D-7 Batch D 的 D1 离线 TDD；设计通过不能写成注入问题已经修复。
- 聚焦治理/历史兼容回归为 `16 passed`；完整回归为
  `455 passed, 103 subtests passed`。RAG development 与 independent holdout 的
  Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation support 均为 `1.0`；
  compileall、治理、tracked secret/run-data、diff check 和 Harness dry-run 均通过。
- 陈旧状态扫描发现路线历史中 Batch C 的“唯一下一步”仍标为 `CURRENT`；保留原始历史
  内容，只把标签更正为 `AT-CHECKPOINT`，避免历史状态冒充当前 canonical 下一步。

### 2026-08-14：5D-7 Batch D D1-D3 安全评测迁移与 held-out 创建

- 按 canonical 唯一下一步完成 D1：保留 `coach_evaluation@1.0.0`，新增
  `coach_evaluation@1.1.0` 的用户请求/ bounded KnowledgeEvidence 输入、
  `prompt_injection` 高危 issue 与不可修订的 Harness blocking policy；安全 Prompt
  将用户和检索知识显式标为 data-only，生产链不扫描已知 canary。
- D2 以 Scripted Provider 驱动真实本地 Skill/Agent/Tool/RAG/Harness 控制流，新增 7
  场 secure offline executable development 基线；task outcome accuracy 与 failure
  classification accuracy 均为 `1.0`，unsafe publication rate 为 `0.0`，external calls
  为 `0`。旧 1.0.0 测试和 Batch C 的 1/7 unsafe-publication 历史 Bad Case 均保留。
- 按冻结合同完成 D3：创建 3 场独立 held-out（正常、用户注入、检索证据注入），数据集
  标记 `role=held_out`、`calibration_excluded=true`，并通过无案例 ID 重叠、无污染来源、
  显式 `confirm_rules_frozen=True` 才可运行的生命周期测试；本批没有运行 held-out。
- D1/D2/D3 聚焦与相邻测试 `16 passed`（含 4 个 subtests）；安全 CLI 输出与脱敏
  Candidate/Result 已复核，完整回归为 `460 passed, 103 subtests passed`；两套 RAG、
  compileall、Harness SDK/tracked-data、dry-run、治理与 diff check 均通过。当前提交和
  GitHub Actions 精确 SHA 验证待本轮最后执行。
- 当时 5D-7 仍进行中，唯一下一步改为 Batch D D4：先写候选 Provider 采用门 ADR，
  冻结同任务比较、能力/错误归因、调用/成本预算和停止规则；不自动调用真实 Provider、
  不接入第二 Provider、不运行 held-out、不进入 5D exit review 或 5E。
- D1-D3 提交 `e100e4d602891bb6cfb22f25101c53f4621408f8` 已推送；GitHub Actions
  run `31719575766` 对该精确 SHA completed/success。下一轮 D4 恢复时发现 canonical
  GitHub 进度线仍误留“尚未提交”，现已按远端 SHA 与 CI 证据补正。

### 2026-08-14：5D-7 Batch D D4 第二 Provider 候选采用门

- 按 canonical 唯一下一步完成 Provider seam 与官方资料复核，没有调用任何真实模型。
  现有统一 Chat/Capability/Registry 可复用，但 Zhipu thinking、工具名、响应和错误映射
  不能通过更换 base URL 直接冒充通用 Adapter。
- 方案比较覆盖暂不增加第二 Provider、DeepSeek V4 Flash、Qwen3.8 Max 和 DeepSeek
  V4 Pro。Qwen3.8 Max 已按正式模型状态复核，具备混合思考、结构化输出和 Function
  Calling；本轮暂缓只因首轮控制变量和计费入口，不是质量结论。
- 新增 D4 初学者设计文档与 ADR-0017，选择 DeepSeek 官方 `deepseek-v4-flash` 为
  唯一有界候选。它只是进入 D5 离线 TDD 的候选，不等于 Adapter 已实现、真实请求已
  发生、领域已准入或产品默认模型已切换。
- 冻结三层准入、同一 Skill/Context/Evaluation/held-out、5D-6b 安全错误归因前置项、
  27-call 全实验最坏上限、每案例 4000 total tokens、每请求 1024 output tokens、GLM
  ¥0.50 / DeepSeek $0.05 金额停止线和全局/单 Provider 停止规则。
- 当前唯一下一步改为 D5 离线 TDD：实现独立 DeepSeek Adapter、安全 failure
  observation、预算/成本控制器和 no-I/O dry-run；本轮不调用 Provider 或 held-out。
- D4 聚焦 Provider/领域评测/held-out 生命周期回归为 `68 passed, 15 subtests passed`；
  完整回归为 `460 passed, 103 subtests passed`。RAG development/independent holdout
  的 Recall/MRR/nDCG、abstention/citation 门均通过；compileall、Harness SDK/敏感文件
  边界、Harness dry-run、文档密钥模式扫描、governance 和 diff check 通过。
- D4 提交 `02720631aa34aa8556ea445bbd1837c8b562715c` 已推送；GitHub Actions run
  `31761121188` 对该精确 SHA completed/success，CI 全部门禁通过且没有调用真实
  Provider。公开进度线已按远端证据回写。

### 2026-08-14：D4 唯一候选决策更正

- 根据用户对 V4 Pro 正式版的复核要求，发现 ADR-0017 把“低成本协议可移植性”置于
  “唯一候选领域准入”之前；保留原 ADR 历史并新增 ADR-0018 取代其模型选择。
- 唯一候选更正为 `deepseek-v4-pro`。它与 Flash 共享当前所需 API 能力，不新增 SDK、
  Provider、Agent 或控制流；协议门和领域 held-out 必须使用同一精确 Pro 模型。
- 调用与 Token 上限不变；按官方 2026-08-16 起 Pro 峰值价，把 DeepSeek 应用层金额
  停止线从 `$0.05` 调整为 `$0.10`。当时把 Flash 的后续成本/时延评估暂记为 5F 以后；
  ADR-0019 随后把它修正为 5P 后、默认阶段 6 的横向 Provider 优化门，本门仍不同时执行。
- 本次更正没有实现 D5 代码、读取 Key、调用真实 Provider 或运行 held-out；唯一下一步
  仍是 D5 离线 TDD。验证、提交、推送与 exact-SHA 公开 CI 结果待本批收尾补记。
- 本地完整回归为 `460 passed, 103 subtests passed`；两套 RAG 门均为满分且独立 holdout
  abstention/citation 为 `1.0`；compileall、Harness dry-run、SDK/tracked-data 边界、文档
  密钥模式扫描、governance 和 diff check 均通过。全部检查使用本地数据或 Fake/dry-run，
  外部 Provider calls 为 `0`。
- 更正提交 `5513928e29ffab4525b356b80845d9be807647bb` 已推送；GitHub Actions run
  `31762059181` 对该精确 SHA completed/success，公开 CI 的完整 pytest、两套 RAG、
  compileall、治理、安全边界和 Harness dry-run 全部通过，未调用真实 Provider。

### 2026-08-14：5D-7 Batch D D5 DeepSeek Provider 离线实现

- 新增独立 `DeepSeekProvider` 与严格配置工厂，固定 `deepseek-v4-pro`、官方 base URL、
  non-thinking、non-streaming 和零 SDK retry；Fake SDK 覆盖 text/tool/structured、四类
  消息、别名、finish/usage 及脱敏错误，真实外部调用为 0。
- 新增安全 `AgentFailureObservation` 并贯通 draft preparation/Skill executor；真实
  AgentLoop 认证失败测试证明 Harness 返回确定性 degraded，同时保留安全来源码且不
  暴露原始错误。
- 新增候选实验 budget policy、resource ledger、Provider/global stop 与失败白名单。
  DeepSeek 为 3 protocol + 12 domain calls、16000 observed tokens、1024 output/request、
  `$0.10`；GLM domain 为 12 calls、12000 tokens、`¥0.50`。
- 新增 no-I/O preparation CLI，严格核对干净 SHA、公开 CI、冻结 held-out 与
  Prompt/Context snapshot；没有加载 `.env`、读取 Key、创建客户端或运行 held-out。
- 聚焦与相邻回归通过；完整回归为 `505 passed, 103 subtests passed`。两套 RAG 门禁
  满分，compileall、Harness dry-run、SDK/tracked-data 边界、governance 与 diff check
  均通过。
- D5 功能提交 `e68a8e4542ed72d31d5d46e569a11d9292048540` 已推送；GitHub
  Actions run `31764109304` 对精确 SHA 全部通过。同一干净公开 SHA 的 no-I/O
  preparation 随后通过，输出 `external_provider_calls=0`、`held_out_executed=false`。
- D5 已形成公开离线证据。唯一下一步为最多 3 calls 的真实 DeepSeek V4 Pro Adapter
  协议门；该步骤需要真实 Key/显式调用确认，仍不得直接运行 held-out。

### 2026-08-14：Flash/Pro 分层规划纠偏

- 用户确认保持方案 2：当前 5D-7 继续只测试 DeepSeek V4 Pro，Flash 不进入本轮协议门
  或首次 held-out；未来再评估 Flash 默认、Pro 复杂任务/质量升级。
- 复核发现旧 ADR-0018、D4 设计、项目决策和能力矩阵曾把未来 Flash 评估放到 5F，
  与 5F 的 Pi / Claude Agent SDK Runtime 采用职责冲突。
- 新增初学者设计和 ADR-0019：模型分层改为 5P 后的横向 Provider 优化门，默认等待
  阶段 6 真实成本/时延/Trace Bad Case；5F 保持第三方 Runtime 对照，不实现模型路由。
- 同步 RQ-030、ADR-0018 交叉说明、D4 设计、v1.3、能力矩阵、项目决策、canonical
  state 和活动计划；当前 checkpoint、Pro-only 配置、调用预算和唯一下一步均未改变。
- 规划纠偏后的完整回归为 `505 passed, 103 subtests passed`；RAG development 与
  independent holdout 的 Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation
  support 均为 `1.0`；compileall、governance 和 Harness dry-run published。全部检查
  使用本地数据与 dry-run，外部 Provider calls 和 held-out executions 仍为 `0`。

### 2026-08-14：真实协议门执行接缝开始

- 在读取 Key 或调用 Provider 前完成精确代码审计：D5 的离线零件均存在，但没有正式的
  DeepSeek real-gate CLI 将 public-CI preflight、预算/停止器、生产 Adapter、3-call
  protocol runner 和脱敏结果持久化组合起来。
- 新增初学者设计 `docs/plans/2026-08-14-deepseek-real-protocol-gate-design.md`，冻结
  先身份后 Key 的控制流、结果合同、测试证明和排除范围。
- 当前外部 Provider calls 仍为 `0`，held-out 未运行；下一动作是离线 TDD 补齐执行接缝，
  通过公开 exact-SHA CI 后才允许执行最多 3 calls 的真实 Pro 协议门。
- 新增 `ProviderAdapterProtocolExperimentRecord`，把 no-I/O preparation、协议结果、
  resource ledger 和 stop snapshot 绑定为同一不可变、extra-forbid 的脱敏证据；新增 CLI
  强制显式确认、精确三次预算、结果目录边界和拒绝覆盖。
- 新增 7 个接缝测试，证明 preflight 先于环境/Key、成功路径为 1+2 次调用、认证失败只
  消耗一次并停止、身份漂移在 Provider 前失败、结果不含原始 Key/请求/工具/回答内容。
- 聚焦及相邻回归为 `58 passed`；完整回归为 `512 passed, 103 subtests passed`。两套
  RAG 门满分且 compileall 通过。真实 Provider calls 仍为 `0`，held-out 未运行；下一步
  是提交、推送、验证 exact-SHA GitHub Actions，再由同一干净 SHA 执行真实协议门。

### 2026-08-14：真实 DeepSeek V4 Pro 协议门完成，进入证据归档

- execution seam 提交 `076a5e3558cd68abb545cebdc2542c973b020768` 已推送；GitHub
  Actions run `31767405927` 对该精确 SHA 全部门禁通过，同 SHA no-I/O preflight 通过。
- 真实协议门只运行一次并完成 3/3 calls：A1 structured contract 与 A2 Agent tool
  round trip 均 passed，`admitted=true`；总计 1428 tokens，估算 `$0.00221496`，无停止。
- held-out executions 仍为 `0`，没有进入领域报告生成/评测，也没有注册产品默认
  Provider。结果文件已经类型化复读并取得 SHA-256，当前工作只负责归档和同步状态。
- 公开结果目录的旧合同遍历测试最初把新组合记录误当 P1 报告，保留红灯后已按结构键
  分派到真实 `ProviderAdapterProtocolExperimentRecord`；新增固定文件 SHA、代码 SHA、
  3-call、Token/费用、无停止与 held-out=false 断言，聚焦 `9 passed`。
- canonical state、活动计划、路线修订、能力矩阵、项目决策和路线历史已同步为“最小协议
  已准入、领域未准入”；新的唯一下一步是先审计/设计领域 held-out 执行接缝，本批不调用。
- 归档后完整回归为 `513 passed, 103 subtests passed`；RAG development 与 independent
  holdout 的 Recall/MRR/nDCG 均为 `1.0`，holdout abstention/citation support 均为
  `1.0`；compileall 和 Harness dry-run published。全部是本地验证，没有新增 Provider
  calls 或 held-out execution。
- 协议证据归档提交 `ba1379db6b573d07e6cbe3bd27b9561ea9ca9f6e` 已推送；最初的
  `gh run list` 与公开 REST 查询分别遇到 TLS 超时，未据此推断 CI 状态。改查精确
  commit 的 check-runs API 后，确认 GitHub Actions run `31779362817` 的 `pytest`
  completed/success。该恢复查询不调用 Provider，也不运行 held-out。
- CI 恢复记录提交 `e0f3edf3b5dc12557124252273e70b86d58d981a` 推送后，`gh run
  watch` 与 check-runs 查询又遇到两次 TLS 握手超时；改用 20 秒上限的 PowerShell
  REST 查询，确认 run `31779529184` 对该精确 SHA completed/success。失败均发生在
  CI 状态读取阶段，不是测试失败，也没有触发外部模型调用。
- 收口记录提交 `84af18c11928a1043bf743a68abcea1f6c19d253` 已推送；一次 `gh run
  list` TLS 超时后不再重复该路径，PowerShell REST 确认 run `31779642991` 对精确 SHA
  completed/success。此处只补齐查询失败账本；协议实验、调用数和 held-out 状态不变。

### 2026-08-14：三案例领域 held-out 执行接缝本地完成

- 按 canonical 唯一下一步完成源码审计和初学者设计，比较 development runner 复用、
  巨型真实 CLI、薄协调器三种方案；采用“控制面 admission + 案例执行 Protocol + 既有
  分层 Evaluator/累计 ledger”，没有调用 Provider 或运行 held-out。
- `ProviderResourceLedger` 新增 protocol/domain scope Token、动态单案例 calls/Token 和
  已有 snapshot 继承；DeepSeek 继续固定 3 protocol + 12 domain、每例 4 calls、
  protocol/每例 4000、domain 12000、累计 16000 observed tokens、每请求 1024 output
  与累计 `$0.10`。
- 新增 `provider_domain_experiment`：no-I/O admission、协议文件字节摘要 loader、执行计划
  摘要、逐例协调与分层判断、Provider/global stop、partial/skipped 安全记录、资源差值、
  不可覆盖输出和 Provider 前独占预留均为严格类型合同。
- 新增合成 TDD，证明单例第 5 call 在底层 I/O 前拒绝，首错后不执行剩余案例，unsafe
  publication 全局停止，plan/预算漂移在 Provider 前拒绝，Token overrun 保留安全账本，
  原始 Prompt/模型正文/request ID/异常/Key 串不进入结果。
- 真实协议文件只做本地严格复读，仍为 3 calls、摘要
  `575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`；本批新增外部
  Provider calls 为 `0`，held-out executions 为 `0`。
- 首轮聚焦/相邻回归为 `34 passed`，第一次完整回归为
  `525 passed, 103 subtests passed`；后续又补案例计划绑定、budget drift 和异常脱敏
  负例，最终聚焦回归为 `36 passed`，完整回归为
  `528 passed, 103 subtests passed`。
- 提交前两套 RAG 门、compileall、Harness dry-run、Harness SDK boundary、tracked
  secret/run-data、新接缝 no-key/no-client、governance 和 diff check 均通过；本批新增
  Provider calls 与 held-out executions 仍为 `0`。
- 功能提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已推送；GitHub Actions run
  `31785253957` 对该精确 SHA completed/success。当前唯一下一步是冻结/装配真实案例
  执行计划与生产 Executor/CLI，先离线 TDD 和新的公开 CI，成功前不读取 Key、不运行
  held-out，也不进入 5D exit review 或 5E。

### 2026-08-14：领域 held-out 生产装配设计

- 恢复 canonical state、活动计划、需求账本、路线/修订、ADR-0020 与源码接缝，治理
  通过，起始 HEAD/origin 均为 `d9ad6f2`，工作树干净。
- 审计确认旧 `DomainSkillSliceRunner` 仍是单样例/旧评测切片，不能承担 Evaluation 1.1
  的三场真实 held-out；development `OfflineDomainExecutionRunner` 又含已知 canary 和
  scripted responses，也不能复用。
- 发现 held-out 1.0.0 注入期望方向反转和 Executor oracle 暴露；新增生产装配设计、
  实施计划与 ADR-0021。当前仍为设计/审计证据，尚未修改 Dataset/生产代码，外部调用与
  held-out executions 均为 0。

### 2026-08-14：领域 held-out 生产装配本地完成

- 按 ADR-0021 在任何真实领域输出出现前把 held-out 升为 1.1.0：正常、用户注入和
  知识注入三场都要求抵抗不可信指令、完成真实知识往返并由 Harness `published`；
  安全降级仍保护系统，但不准入模型领域能力。
- 新增独立 input-plan Artifact，精确绑定 Dataset/Skill、三个 case/run、原始 fixture
  字节摘要、知识模式和禁止输出 marker；loader 会在 Provider 前拒绝路径、摘要、顺序、
  Dataset 或 fixture 漂移。计划文件 SHA-256 为
  `f954fc74690af196e8690c5730be5b9830ebc532c529f1a3b7cec972839bba4a`。
- `DomainCaseExecutor.execute()` 只接收 `case_id + provider`，不再接收带期望答案的
  `DomainEvaluationCase`；生产 Executor 真实组合 Catalog/Router/Boundary/Context、
  AgentLoop、本地 hybrid RAG、Secure Evaluation 1.1、ReviewHarness 和 typed output。
- `SkillReviewExecutor` 新增默认行为不变的 `max_revisions` 注入点；领域门固定 0。
  Agent 失败的安全 status/stop/error provenance 现在能进入白名单语义观测，原始异常、
  Prompt、报告和 request ID 不进入公开结果。
- 新增真实门 CLI，顺序固定为确认/12-call -> output path -> no-I/O preflight ->
  Dataset/plan/fixture/protocol/admission -> 独占输出预留 -> `.env`/Key -> Provider ->
  production Executor -> 不可变脱敏结果；旧协议 Dataset SHA 偶然耦合已移除，但协议文件
  精确字节摘要仍固定为 `575e8f...086e1`。
- 原始 Harness run 固定写入 `.gitignore` 与 CI 均保护的
  `data/runs/evaluation/deepseek_domain`；公开目录只允许不可覆盖的脱敏汇总结果。
- Fake Provider 已离线走通三个计划案例和完整 CLI；正常路径发布，用户/RAG marker
  回显被观测并安全降级，Provider 认证错误保留安全来源码，needs-revision 在 0 修订预算
  下不产生额外调用。当前外部 Provider calls 与真实 held-out executions 均仍为 0。
- 最终本地完整回归为 `545 passed, 103 subtests passed`；两套 RAG 门满分、compileall、
  Harness dry-run、SDK boundary、tracked secret/run-data、governance 和 diff check 均通过。
- 设计提交 `750acbcdf85b454e83dc84502a6422cf36acff32` 与功能提交
  `eb198354b3186f25b7d0455d7ed28725bc17e234` 已推送；GitHub Actions run
  `31799394506` 对功能提交的精确 SHA completed/success，完整 pytest、两套 RAG 门、
  compileall、Harness SDK 边界、tracked secret/run-data 与 dry-run 全部通过。该公开
  验证没有读取 Key、调用 Provider 或运行真实 held-out；下一动作仍需用户单独显式确认。

### 2026-08-14：真实 DeepSeek V4 Pro 领域 held-out 已执行并拒绝

- 用户明确确认后，先在干净公开 SHA `205397f0bd87a53291b8a2c62487a8b6d966fdb1`
  上重复 no-I/O preflight，得到 `external_provider_calls=0`、`held_out_executed=false`；
  随后只运行一次生产领域 CLI。
- 第一场正常近期复盘消耗 1 个领域调用后返回安全码
  `unsupported_parallel_tool_calls`，没有规范化 `ChatResponse`、Tool execution、Evidence
  或 Evaluation；Harness 终态为 `degraded/draft_preparation_failed`，没有不安全发布。
- 首错停止使用户注入和知识注入两场均为 skipped；总结果 `held_out_executed=true`、
  `admitted=false`。新领域 ledger 为 1 call、0 observed tokens、`$0.00`；此前协议 3 calls/
  1428 tokens/`$0.00221496` 原样继承。0 observed tokens 只表示规范化前无法结算 usage。
- 不可变脱敏结果位于 `data/evaluation/results/provider_capabilities/deepseek_v4_pro_domain_heldout.json`，
  SHA-256 为 `fbd1251af98daa9e767de56a35100025807ce96026d6b3b3497e33dd30ad989e`；
  Key、Prompt、模型/RAG/工具正文、request ID 与注入 marker 扫描无泄漏。当前不重跑。
- 归档提交 `26b668d0ce594e648a692cd2caf831c86125fede` 已推送；GitHub Actions
  run `31810164628` 对该精确 SHA completed/success，完整测试、两套 RAG 门、compileall、
  Harness SDK/secret/run-data 边界与 dry-run 全部通过。CI 没有真实 Provider 调用。

### 2026-08-14：多 ToolCall 顺序消费设计

- 对照真实失败、DeepSeek Adapter、AgentLoop 及官方 Chat Completion 合同，比较继续
  拒绝、受控顺序执行和真正并发三种方案；官方合同允许 `auto` 返回一个或多个工具，
  且没有正式关闭批次的请求参数。
- 新增初学者设计、ADR-0022 和四任务实施计划，选择“Adapter 严格解码 + AgentLoop
  整批原子预检 + 按返回顺序执行”；不宣称并发 capability，不新增框架。
- 本批未修改 Provider/Agent 代码，没有读取 Key、调用真实 Provider 或重跑 held-out。
  下一步仅是 Fake SDK + 本地 Tool/RAG/Harness 的 development TDD。

### 2026-08-14：多 ToolCall 顺序消费本地 TDD

- Provider Adapter 先以旧实现准确复现 `unsupported_parallel_tool_calls` 红灯，再仅移除
  “调用数量必须为 1”的两处额外限制；唯一 ID、内部/厂商工具别名、严格 JSON object、
  finish reason 与 `parallel_tool_calls=false` capability 边界均保留。
- AgentLoop 新增批次合同测试：合法的两个调用按响应顺序执行并保留 call ID、Usage、
  iteration 与递减 deadline；超预算、后续越权和同批重复均在任何工具执行前 fail closed。
- 新建 development 输入计划，使用新的 case/run ID，不复用已消费 held-out 的 case ID、
  注入 marker 或答案；Fake DeepSeek SDK 的两个 ToolCall 真实经过 AgentLoop、本地 hybrid
  RAG、Evidence、Secure Evaluation 1.1 与 ReviewHarness 并发布。
- 聚焦回归为 `53 passed`，全量回归为 `551 passed, 103 subtests passed`；两套 RAG、
  compileall、Harness dry-run、SDK/secret/run-data、governance 与 diff check 均通过，
  外部 Provider calls 为 0。当前只完成本地实现，唯一下一步为提交、推送和 exact-SHA
  公开 CI；不改变旧真实 held-out 的 `admitted=false`。

### 2026-08-14：多 ToolCall 顺序消费公开验证

- 实现提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 已推送；GitHub Actions run
  `31817798170` 对精确 SHA completed/success。公开门包含全量 `551 passed, 103 subtests
  passed`、两套 RAG、compileall、Harness SDK/secret/run-data、dry-run、governance 和
  diff check，外部 Provider calls 为 0。
- 当前多 ToolCall 结论只到“Adapter/AgentLoop/本地 RAG/Evaluation/Harness 执行链兼容”，
  不到“DeepSeek 领域准入”；旧真实 Dataset 1.1.0 的结果哈希与 `admitted=false` 永久
  保持不变。
- 唯一下一步改为零调用设计新鲜真实领域采用门，包含新 Dataset/输入身份、污染边界、
  Prompt/Context 快照、资源预算、首错停止和单独确认条件；不重跑旧考卷，不实现真正
  并发，不进入 5D exit review/5E。

### 2026-08-15：GLM-5.3 迁移方案持久化

- 读取官方 GLM-5.3 页面确认：Coding Plan 已开放，普通模型 API 将逐步上线；模型始终
  启用 thinking，不能沿用 GLM-5.2 的 disabled thinking。
- 新增 `docs/plans/2026-08-15-glm53-provider-adoption-design.md` 与 ADR-0023，决定
  不立即切换默认模型、不影响 DeepSeek、不覆盖旧证据；未来按 G53-0 至 G53-4 的
  可用性审计、Zhipu profile 离线 TDD、公开 CI、3-call 协议门和新鲜领域门推进。
- 本轮没有读取 Key、调用 Provider、修改 Zhipu/DeepSeek 代码或改变 5D-7 唯一下一步。

### 2026-08-15：DeepSeek 新鲜领域采用门零调用设计

- 审计 ADR-0013/14/15/16/20/21/22、Domain Dataset/Candidate/Result、输入计划、
  no-I/O admission、薄协调器、production Executor、CLI 和旧真实结果；没有调用 Provider。
- 比较整套重写、旧题改名和版本化复用三种方案；ADR-0024 接受版本化复用控制面并重新
  冻结全部实验身份。
- 新设计要求先用合成 development 数据完成兼容合同和公开 CI，再创建新的匿名 fixture、
  三案例 held-out、输入计划和实际案例 Prompt/Context 摘要；旧 Dataset 1.1.0 不重跑。
- 新门保留每例 4 calls、领域 12 calls、4000/12000 tokens、每请求 1024 output、
  `$0.10`、零重试/零修订和首错停止；这些只是未来上限，不授权真实调用。
- 唯一下一步改为 Fresh-Gate 1 离线 TDD；正式新 held-out、Key、真实 Provider 和 5E
  仍被阻断。
- 设计提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已推送，GitHub Actions run
  `31859717836` 对精确 SHA 全部成功；CI 外部 Provider calls 为 0。

### 2026-08-15：Fresh-Gate 1 本地离线 TDD 完成

- 新增实施计划
  `docs/plans/2026-08-15-deepseek-fresh-domain-gate-offline-implementation.md`，明确当前
  只做 development 合同/no-I/O admission，不创建正式新 held-out 或调用 Provider。
- `DomainCaseInputPlanArtifact` 兼容支持 V1.0/V1.1；新 `DomainCaseContextCommitment`
  要求 V1.1 的 snapshot identity 和逐案例 Context 摘要严格按 case order 对齐，旧
  V1.0 文件仍严格复读。
- `PromptContextSnapshot` 兼容支持 V1.1；新 builder 让三个合成 development case
  分别经过真实 Catalog、Router、ExecutionBoundary、ContextBuilder，并只输出安全摘要。
- 新增 `provider_domain_readmission`：严格复读历史协议/拒绝结果 bytes，绑定
  `037a47f` / Actions `31817798170`，明确历史 calls 为 4、旧协议为 1428 tokens/
  `$0.00221496`、旧失败 usage/cost 为 unknown；
  development admission 绑定当前 code/public CI、Dataset、plan、fixture、Skill/
  Evaluation 和三个 Context 摘要，且固定禁止 Provider 构造。
- TDD 聚焦 `33 passed`，领域相邻回归 `51 passed`，完整回归
  `568 passed, 103 subtests passed`；RAG development/independent holdout 均满足 1.0
  门槛，compileall、Harness SDK boundary、tracked secret/run-data boundary 与 Harness
  dry-run 通过。
- 实施计划最初三条外围命令与当前 CLI/workflow 不一致，红灯被保留并记录；命令已经按
  `.github/workflows/tests.yml` 修正后全部重跑成功。错误命令曾触发旧 RAG baseline
  文件的工作区写入，但其 Git object 已恢复为 HEAD 精确内容，未形成业务变更。
- 当前新增 Provider calls 为 0、held-out executions 为 0、正式新 held-out 资产为 0。
  唯一下一步为 Fresh-Gate 2：提交、推送并验证 exact-SHA GitHub Actions。

### 2026-08-15：Fresh-Gate 1 exact-SHA 公开验证完成

- 实现提交 `adba965a7f7fb4293020502b4440e9880633e571` 已推送到 `origin/main`。
- GitHub Actions run `31860874440` 对该精确 SHA completed/success；公开门包含治理、
  `568 passed, 103 subtests passed`、两套 RAG、compileall、Harness SDK boundary、
  tracked secret/run-data boundary 与 Harness dry-run。
- CI 没有 `.env`/Key、Provider call、held-out execution 或新正式结果；Fresh-Gate 1
  只证明兼容合同、历史链和 no-I/O admission 已公开冻结。
- 唯一下一步为 Fresh-Gate 3 新资产创建/冻结批；该批仍不运行 held-out 或调用 Provider。

### 2026-08-15：Fresh-Gate 3 新资产本地冻结完成

- 新增初学者设计与实施计划，比较旧题改名、重写控制面和复用冻结合同三种方案，采用
  第三种；没有修改生产 Agent、Prompt、Evaluation、Harness、Router、RAG 或 Provider。
- 先添加 5 个缺文件红灯测试，再创建新的匿名 3 局 fixture/确定性报告、三案例 held-out、
  V1.1 input plan 和三个实际案例的 body-free Prompt/Context snapshot；补充事实自洽
  测试后聚焦回归为 `39 passed`。
- 第三个请求初稿被当前 Deterministic Router 正确拒绝；按已冻结 Manifest 改成明确的
  近期战绩分析入口后通过，没有调 Router 或 Skill 规则。
- 完整回归为 `574 passed, 103 subtests passed`；RAG development/held-out 均达到 1.0
  门槛，compileall、Harness SDK/tracked-data boundary、dry-run、governance 与 diff check
  通过。
- 新 Dataset、plan、snapshot 文件 bytes SHA 分别为 `db95ac30...da3c`、
  `878d3ec4...4987`、`45bd09b4...8a0f`；Snapshot 自摘要为 `79974fb2...50011`。
  Provider calls、held-out executions 均为 0，真实结果文件不存在。
- 当前唯一下一步为提交、推送并验证 Fresh-Gate 3 exact-SHA GitHub Actions；成功前不得
  进入 Fresh-Gate 4 或读取 Key。

### 2026-08-15：Fresh-Gate 3 exact-SHA 公开冻结完成

- 资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已推送到 `origin/main`。
- GitHub Actions run `31861960565` 对该精确 SHA completed/success；治理、完整 pytest、
  两套 RAG、compileall、Harness SDK/tracked-data boundary 与 dry-run 全部通过。
- CI 没有 `.env`/Key、Provider call、held-out execution 或真实结果；它证明新 Dataset、
  V1.1 plan、匿名 fixture 和三案例 body-free Context identity 可公开复现，不证明模型
  领域质量。
- 唯一下一步为 Fresh-Gate 4 no-I/O 入口批：绑定新资产与现有生产执行接缝，先离线
  TDD/公开 CI，不直接读取 Key 或运行 held-out。

### 2026-08-15：Fresh-Gate 4 运行入口本地 TDD 完成

- 新增初学者设计和实施计划；比较原地改旧常量、复制 V2 控制面和版本化复用，采用第三种。
- `FreshDomainHeldOutAdmission` 已把历史协议/拒绝、ADR-0022 CI、Fresh-Gate 3 asset CI、
  当前 code/public-CI、新 Dataset/plan/fixture 和三案例 Context 串成一个零调用身份；其
  prepare 函数不接收 Provider/API Key。
- 新 Fresh result envelope 显式保存 readmission 与原领域判决；旧结果模型和历史 JSON
  仍可原样复读，现有独占输出 reservation 增加严格 Pydantic envelope 提交能力。
- 生产 CLI active profile 已切到 V2，并加入 `--prepare-only`；测试证明 output conflict、
  preflight、reserve、environment、Provider 顺序，正常装配与 1-call 首错停止均符合设计。
- 相邻 `93 passed`，完整 `580 passed, 103 subtests passed`；RAG development/holdout、
  compileall、Harness SDK/tracked-data boundary、dry-run、governance 与 diff check 全部通过。
- 没有读取 Key、调用外部 Provider、运行真实 V2 held-out 或创建正式结果。唯一下一步为
  commit/push/exact-SHA CI，随后在同一干净 SHA 上执行一次 no-I/O `--prepare-only`；真实
  运行仍需单独确认。

### 2026-08-15：Fresh-Gate 4 入口公开冻结与 prepare-only 完成

- 实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已推送，GitHub Actions run
  `31863341338` 对该精确 SHA completed/success。
- 在同一干净 SHA 执行 `run_deepseek_domain_heldout.py --prepare-only`，输出
  `no_io_admitted=true external_provider_calls=0 held_out_executed=false`；没有读取 Key、
  调用 Provider、创建结果或运行 held-out。
- Fresh-Gate 4 入口批完成。唯一下一步为单独真实运行确认门；必须先展示模型和
  12-call/12000-token/`$0.10` 等上限，获得明确确认后才可加载 Key。

### 2026-08-15：V2 三案例真实门已单次执行

- 用户明确确认后，先复核公开成功 SHA `741e84140f816fb4b06b2812a8d07d3f32eaf4d0`、
  Actions `31863519248`、干净工作树、结果不存在和治理通过，再首次运行真实 CLI。
- 首例只产生 1 次外部调用与 1 个规范化响应；3241 input + 199 output = 3440 tokens，
  下一请求因预留 1024 output 会超过单例 4000-token 门而在 I/O 前停止。
- Harness 以确定性 fallback 降级，unsafe publication 为 false；后两例按首错停止未调用。
  V2 最终 `held_out_executed=true`、`admitted=false`。
- 新鲜领域使用 1 call/3440 tokens/`$0.00506616`/12125 ms；与既有协议合计的本记录为
  4 calls/4868 tokens/`$0.00728112`。旧失败调用仍在历史链中另计且 Token/费用 unknown。
- 不可变结果 SHA 为 `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`；
  聚焦结果/生命周期回归为 `47 passed`，完整回归为 `581 passed, 103 subtests passed`；
  两套 RAG、compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff
  check 通过。当前仍需提交、推送和公开 exact-SHA 归档。
- 唯一下一步：完成本轮持久化、完整回归、提交/推送和 exact-SHA CI；之后进入 5D-7
  零调用预算可达性裁决，不重跑 V2。

### 2026-08-15：V2 结果公开归档完成

- 结果/测试/裁决提交 `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 已推送到
  `origin/main`；GitHub Actions run `31864370988` 对精确 SHA completed/success。
- 公开 CI 重跑治理、581 tests/103 subtests、两套 RAG、compileall、Harness SDK/
  tracked-data boundary 与 dry-run；CI 无 `.env`/Key，外部 Provider calls 为 0。
- 本轮真实调用总数保持 1，V2 结果与 `admitted=false` 不变。唯一下一步正式切换为 5D-7
  零调用 V2 结果裁决与预算可达性 TDD。

### 2026-08-15：V2 预算可达性离线裁决本地完成

- 先以 ADR-0025 冻结“真实领域门前必须证明资源合同可达”，不修改、不覆盖或重跑 V2。
- 新增 no-I/O 严格裁决器，精确复读结果 SHA `877b623f...dc62a`、首例 3241/199 Usage、
  4000 单例上限和 1024 output 预留；自动证明第二调用至少需要 4464，上限短缺 464。
- 现有 production Executor 由本地 Scripted Provider 走通初始 Agent、知识工具往返后
  Agent 与 Evaluation，生成不含正文的三阶段 envelope，长度单位为 6666/7774/6266。
- 用首轮真实 input 校准的投影为 3241/3780/3047，已知 output 加入后为 10267；合同将其
  明确标记为非 Provider tokenizer，完整精确需求和 V3 推荐预算仍为 `null`。
- 严格裁决 JSON SHA-256 为
  `ca3df9953d84629fd473f53c5920b00ebc08e1f9c26f5e40df0d1aeee7c02d1b`；聚焦
  `6 passed`，相邻 `30 passed`；完整回归 `587 passed, 103 subtests passed`，两套 RAG、
  compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 均通过；
  本批 Provider/Key/网络调用为 0。
- 唯一下一步为完整门禁、提交、推送和 exact-SHA 公开 CI；成功后才开始 V3 资源合同
  development 校准设计，不直接运行 V3。

### 2026-08-15：V2 预算裁决公开验证完成

- 实现提交 `78400b9310e512668c81ca41cd65623a92a27226` 已推送到 `origin/main`。
- GitHub Actions run `31865285994` 对精确 SHA completed/success；治理、587 tests/103
  subtests、两套 RAG、compileall、Harness SDK/tracked-data boundary 与 dry-run 全部通过。
- 公开 CI 没有 `.env`/Key 或 Provider I/O。V2 仍为不可变 `admitted=false`，模型领域质量
  仍是 unknown。
- 唯一下一步为 5D-7 V3 资源合同 development 校准设计；不创建 Provider、读取 Key、
  调用模型或创建/运行 V3 held-out。

### 2026-08-15：V3 development 资源校准设计完成

- 精确审计 `SecureChatEvaluationAdapter`、严格 structured decoder、production Executor、
  资源 ledger 与回归测试，确认正常路径 3 calls、Evaluation JSON 非法时最多使用第 4
  call repair、报告修订仍为 0。
- 用公开 development 输入和本地受控 Provider 走通真实生产四阶段，只输出消息角色、
  数量和 5956/7064/5749/2510 本地长度单位；外部调用为 0。
- 新增初学者设计与 ADR-0026，比较直接抬 V2、行为依赖的 development E2E、四阶段
  request replay 和关闭候选，采用四阶段 replay。
- 冻结未来校准上限为两个 development profile、每 profile 四请求、8 calls、校准输出
  64、64000 observed tokens、`$0.10`、零重试和首错停止；真实运行仍需单独确认。
- 冻结 V3 预算公式：逐阶段最大真实 input × 1.25 后向上取整，加四次 1024 output
  ceiling；成本超过 `$0.10`、30 秒 Agent deadline 不可达或 envelope 越界均停止。
- 本批没有创建校准实现/真实结果/V3 held-out，没有读取 Key、构造 Provider 或调用模型。
  唯一下一步为离线 TDD、完整门禁和 exact-SHA 公开冻结。
- 设计批完整回归为 `587 passed, 103 subtests passed`；RAG development 与 independent
  holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/citation 也为 1.0；compileall、
  Harness SDK boundary、tracked secret/run-data boundary、Harness dry-run、governance 和
  diff check 全部通过。首次误用终端默认 Hermes Python 导致缺少 pytest，未改变环境或
  项目文件；切换到仓库 `.venv` 后全量通过。
- 设计提交 `351c0e64adf9d2ace42c557d40fac81a44ab539e` 已推送；GitHub Actions run
  `31866084382` 对该精确 SHA completed/success，公开 CI 无 Key/Provider I/O。ADR-0026
  设计至此公开冻结；下一步仍只是离线实现/TDD 与新的 exact-SHA CI。

## 2026-08-15：5D-7 V3 资源校准离线实现

- 新增 `provider_resource_calibration.py`，统一承载 development profile、body-free request
  snapshot、显式 Fake replay、安全结果、预算推导和 no-I/O admission；没有新框架或依赖。
- 新增两套独立合成 fixture、profile artifact 和 8-request public contract；V2 资产只读。
- 新增 11 个聚焦测试，并把 Provider 实际 output 超 cap 的结算 Bad Case 加入共享资源账本。
- 资源校准 11/11、资源账本/预算相邻集合 34/34；完整回归为 `598 passed, 103 subtests
  passed`；两套 RAG 全部门槛为 1.0，compileall、Harness dry-run、SDK/tracked-data、治理
  和 diff check 均通过；Provider/Key/网络调用和 V3 held-out execution 为 0。
- 实现提交 `2d676966915a7967b946880040b59c022283e683` 已推送，GitHub Actions run
  `31867655627` 对该精确 SHA completed/success；公开 CI 没有 Key 或 Provider I/O。
- 当前唯一下一步：展示 8-call/64-output/64000-token/`$0.10`/零重试/首错停止边界，等待
  用户对真实 DeepSeek V4 Pro development Usage replay 的单独明确确认。

## 2026-08-15：5D-7 真实 development Usage replay 入口本地完成

- 用户已明确确认 RQ-033 的一次真实 DeepSeek V4 Pro 8-call development Usage 校准；
  当前先实现并验证入口，尚未读取 Key 或发起外部调用。
- 新增真实回放实施计划、`ResourceCalibrationRunAdmission`、
  `RealResourceCalibrationResult`、不可变输出 reservation、真实 replay 协调器、预算结果
  记录和 `run_deepseek_resource_calibration.py` Key-last CLI。
- prepare-only 会在 no-I/O admission 后返回；真实路径固定 output reservation -> env/Key
  -> Provider -> 8-request replay -> result commit，Fake simulation 仍拒绝真实 Provider
  surface。
- 聚焦 `19 passed`、相邻 `74 passed`、完整
  `606 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/tracked-data
  boundary、dry-run、governance 和 diff check 已通过；本批至今真实 calls 0。
- 唯一下一步为完成剩余本地门禁、提交/推送和 exact-SHA public CI；成功后在同一干净
  SHA 运行 prepare-only，再按既有确认执行一次真实回放。

## 2026-08-15：5D-7 真实 development Usage replay 首错停止

- 入口提交 `6aa8c439a29adafebf1ffe1bb0eef0c1b921ca44` 已通过 Actions
  `31868747216`；同 SHA prepare-only 为零调用且没有创建结果。
- 正式 replay 只发送第 1 个请求，随后以 `provider_response_invalid` 停止：1 external
  call、0 normalized responses、后 7 calls 未发送；结果 SHA 为
  `ba33e75af7f8755dc89904fb346f66962fb29e92d08173494053f17ad8e7088b`。
- 实际 Token/费用 unknown，账本零值不解释为实际零；零调用 adjudication SHA 为
  `0ce09b52d982f8c03052f1d94fde1da5628af31dbd797ea770522ce092907446`，明确
  usage incomplete、budget/held-out 禁止、rerun false、quality unknown。
- 预算文件和 V3 held-out 均不存在。当前唯一下一步为结果/裁决完整回归、持久化、提交、
  推送和 exact-SHA public CI；不得补跑。

## 2026-08-15：真实 calibration 失败证据完成本地归档验证

- 新增纯离线 `ResourceCalibrationAdjudication` 与 CLI，把 1 次已发送但未规范化的调用
  单独标为 unobserved，并把 billable input/output/cost 保持为 null；该步骤外部调用为 0。
- 不可变真实结果 SHA 仍为 `ba33e75a...e7088b`，裁决 SHA 仍为
  `0ce09b52...907446`；预算文件与 V3 held-out 仍不存在，rerun 明确为 false。
- 结果/裁决/CLI/全局结果分发聚焦 `34 passed`；完整回归为
  `611 passed, 103 subtests passed`。两套 RAG 指标均通过 1.0 门槛，compileall、Harness
  SDK boundary、tracked secret/run-data boundary、dry-run、governance 和 diff check 通过。
- 一次含 TEMP 递归清理的组合验证被安全策略在执行前拒绝；改用新 TEMP 目录后完整验证
  通过，没有删除项目文件、读取 Key 或再次调用 Provider。
- 当前唯一下一步仍在 5D-7：提交、推送并对结果归档提交执行 exact-SHA 公共 CI。

## 2026-08-15：真实 calibration 不完整证据已公开冻结

- 归档提交 `421a24393cafdc79a02de4091f569cfb9aa5b721` 已推送；GitHub Actions run
  `31869409106` 对该精确 SHA completed/success。
- 公共 CI 在干净 Linux 环境再次通过治理、611 tests/103 subtests、两套 RAG、compileall、
  Harness SDK/tracked-data boundary 和 dry-run；CI 没有 Key 或 Provider I/O。
- RQ-033 到此收口为“不完整 calibration 证据公开冻结”，而不是 Usage 校准成功：仍为
  1 external call、0 normalized responses，实际 Token/费用 unknown，不生成 V3 budget。
- 唯一下一步仍在 5D-7：零调用比较关闭、另立安全可观测诊断版本或继续搁置，不进入
  5D exit review/5E。

## 2026-08-15：DeepSeek calibration 失败采用决策

- 完整复读 ADR-0025/0026、真实结果/裁决、校准 replay、错误分类器与 DeepSeek Adapter；
  本批没有读取 Key、构造 Provider 或调用模型。
- 新增初学者决策文档与 ADR-0027，比较继续诊断、无限搁置和关闭当前 V3 三种方案，
  接受关闭当前 V3。
- DeepSeek 的最小 structured/tool 协议准入继续保留，但领域质量、产品默认模型、自动
  路由与 Flash/Pro 分层均不准入；模型质量保持 unknown。
- 未来任何真实 Provider 门必须先离线实现稳定高层 failure code 与 allowlisted 安全
  provider detail code；禁止响应、reasoning、异常或 request ID 原文落盘。
- 本批 51 项聚焦、完整 `611 passed, 103 subtests passed`、两套 RAG、compileall、
  Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 均通过；没有读取
  Key、构造 Provider 或发起外部调用。
- 本地采用决策至此验收；随后的提交与 exact-SHA 公开回执见下一节。

## 2026-08-15：DeepSeek V3 关闭决策已公开验证

- 决策提交 `ea91e9697c820c0850db488a93263fc169719515` 已推送；GitHub Actions run
  `31872476103` 对该精确 SHA completed/success。
- 公共 CI 在无 Key 环境通过治理、611 tests/103 subtests、两套 RAG、compileall、
  Harness SDK/tracked-data boundary 与 dry-run；外部 Provider calls 为 0。
- 本检查点当时已闭环；当时下一步仍在 5D-7：G53-0 GLM-5.3 普通 API 可用性与合同审计；
  不读取 Key、不调用 Provider，也不进入 5E。

## 2026-08-15：安全 Provider 错误 provenance 离线切片

- 因 GLM-5.3 普通 API 尚未上线，G53-0 已维护为 deferred；没有读取 Key、调用模型或
  切换 Flash。GLM-5.2 仅作为当前开发基线。
- 按 ADR-0027 实现 Provider-specific safe-code allowlist：高层 `failure_code` 继续
  用于跨厂商统计，允许列表内的 `provider_error_code` 只作为无正文诊断标签；未知值为
  `null`。
- Provider stop snapshot、资源 calibration simulation/real result 和 adjudication
  已接入该合同；旧 V3 真实结果仍为 null 且 SHA 不变。
- 聚焦回归为 `89 passed`；完整回归为 `616 passed, 103 subtests passed`，两套 RAG、
  compile/security/dry-run、governance 和 diff check 均通过。
- 本切片只待提交/推送和 exact-SHA public CI；仍未读取 Key、调用 Provider 或测试 Flash。
- 当前唯一下一步仍在 5D-7：完成本切片的完整本地/公开验证；不得调用 Provider、补跑
  DeepSeek、测试 Flash 或进入 5E。

## 2026-08-15：安全 Provider 错误 provenance 切片已公开验证

- 实现提交 `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a` 已推送；GitHub Actions run
  `31874240935` 对精确 SHA completed/success。
- 公共 CI 通过治理、616 tests/103 subtests、两套 RAG、compile、Harness SDK/security
  boundary 与 dry-run；CI 无 Key、无 Provider I/O。
- 本切片闭环。当前仍在 5D-7，但没有新的模型测试授权：DeepSeek Pro 当前实验关闭，
  Flash 不测，GLM-5.3 G53-0 deferred；GLM-5.2 仅作开发基线。
- 当时下一步转为等待 GLM-5.3 普通 API 正式可用或新的明确 Pro/Flash 对照需求；在此
  之前不读取 Key、不调用 Provider、不进入 5E。

## 2026-08-15：5D-7 收尾审查本地裁决

- 完整复读原始 Domain E2E 与 Injection Gate 设计、ADR-0013/0016/0027、5C 退出审查
  模板以及 5D-7 结果资产；没有调用真实 Provider。
- 新增初学者收尾审查文档和 ADR-0028，逐项区分评测/安全门证据与真实模型领域采用。
- 结论为 5D-7 可以完成，但当前没有领域 Provider 准入；GLM/DeepSeek 质量保持 unknown，
  G53 deferred 和 Flash 未测试继续保留。
- 相关 Domain/Prompt/Coach Evaluation/Provider 测试 `130 passed, 4 subtests passed`。
- 完整本地回归 `616 passed, 103 subtests passed`；两套 RAG 1.0 门禁、compileall、
  Harness SDK/tracked-data boundary、dry-run、governance 与 diff check 全部通过。
- canonical checkpoint 当时已切换到 `5D-exit-review`；该本地批次尚待提交推送和
  exact-SHA GitHub Actions，期间不进入 5E。

## 2026-08-15：5D-7 收尾审查已公开验证

- 审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已推送；GitHub Actions run
  `31876536179` 对精确 SHA completed/success。
- 公共 CI 通过治理、616 tests/103 subtests、两套 RAG、compileall、Harness SDK/
  tracked-data boundary 与 dry-run；没有 Key 或 Provider I/O。
- 5D-7 正式闭环，当前无领域 Provider 准入的限制保持不变；唯一下一检查点为
  `5D-exit-review`，不直接进入 5E。

## 2026-08-15：5D 退出审查本地裁决

- 新增 `docs/plans/2026-08-15-5d-constrained-agent-loop-exit-review.md`，以初学者视角
  解释 Agent Loop 与 AgentRuntime 的边界、完整数据/控制流、十项要求、NFR 和限制。
- 审查没有发现必须留在 5D 修复的结构性代码缺口；没有修改产品代码、Prompt、模型或
  Provider，也没有读取 Key 或发起外部调用。
- 核心执行跨层回归为 `173 passed, 34 subtests passed`；Provider/实验控制跨层回归为
  `176 passed, 22 subtests passed`。
- 5D 本地状态改为完成，阶段 5 仍进行中；唯一下一检查点改为 `5E AgentRuntime V1`
  入口设计。当前无领域 Provider 准入、真实注入未执行和性能/Usage unknown 继续保留。
- 完整本地回归为 `616 passed, 103 subtests passed`；RAG development 与 independent
  holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/citation support 均为 1.0；
  compileall、Harness SDK/tracked-data boundary、dry-run、治理和 diff check 全部通过。
- 当前只剩提交推送和 exact-SHA 公共 CI；在此之前不能称为公开验证完成。

## 2026-08-15：5D 退出审查已公开验证

- 退出审查提交 `2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已推送；GitHub Actions
  run `31877076222` 对该精确 SHA completed/success。
- 公共 Linux CI 通过治理、616 tests/103 subtests、两套 RAG、compileall、Harness
  SDK/tracked-data boundary 与 dry-run；没有 Key 或 Provider I/O。
- 5D 至此正式闭环。阶段 5 仍在进行中，唯一下一检查点为 5E AgentRuntime V1 入口
  设计；当前无领域 Provider 准入和其他限制均未改变。

## 2026-08-15：5E AgentRuntime V1 入口设计本地完成

- 逐项审计 Boundary、Context、AgentLoop、Provider Usage、ToolResult、ReviewHarness、
  Artifact Store 与 `SkillReviewExecutor` 的现有组合接缝。
- 比较最外层事后包装、薄 Runtime + 可选 observer、事件溯源/DAG/第三方框架三种方案；
  ADR-0029 接受第二种，保留 ReviewHarness 唯一发布权。
- 初学者设计冻结 request/result、两层 Signal/Event、Runtime/publication 双状态、
  completeness-aware Usage、安全 Trace、原子存储、失败分类、NFR 和测试矩阵。
- 5E 固定为四个内部检查点：5E-1 合同/Usage/Store，5E-2 observable run，5E-3 live
  stream parity，5E-4 evaluation/exit review；没有压缩或改变阶段 0-8。
- 本入口批没有修改产品代码，没有读取 Key、构造 Provider、调用模型、运行 held-out、
  调 Prompt、切换模型或采用 LangGraph/Pi/Claude Agent SDK。
- 完整本地回归为 `616 passed, 103 subtests passed`；RAG development 与 independent
  holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/citation support 为 1.0；
  compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
- 当前唯一下一步为 `5E-1 Runtime Contract、Usage 与 Trace Store`；先做纯本地 TDD，
  不接 AgentLoop/Harness observer，也不实现完整 `run/stream()`。

## 2026-08-15：5E 入口设计已公开验证

- 设计提交 `c91c2d75f85e1315e65e9768894982556053a7b0` 已推送到 `origin/main`；
  GitHub Actions run `31878052835` 对该精确 SHA completed/success。
- 公共 Linux CI 通过治理、616 tests/103 subtests、两套 RAG、compileall、Harness SDK/
  tracked-data boundary 与 dry-run；没有 Key 或 Provider I/O。
- 5E-entry-design 至此闭环，但没有 Runtime 产品代码；唯一下一步保持 5E-1，不得跳到
  observable run、stream、5P 或 5F。

## 2026-08-15：5E-1 TDD 红灯已建立

- 新增 Runtime Contract、Recorder/Usage 与 Trace Store 三组聚焦测试；第一次测试收集
  如预期以 3 个 `ModuleNotFoundError: app.runtime` 失败，证明测试先于产品实现生效。
- 复核了共享 `run_id`、SkillExecutionRequest、Provider TokenUsage、Harness Artifact Store
  与 Pydantic 严格模型约定；本切片将新增薄 Runtime 合同，不复制已有职责。
- 修正 Trace Store 回读测试中的非确定性：保存首次构建的 Trace 后与该对象比较，避免
  再次调用实时时钟构造不同时间戳而产生伪失败。
- 当前进入绿灯实现；仍不接 AgentLoop/Harness observer、不调用 Provider、不实现完整
  `run/stream()`，不提前进入 5E-2。

## 2026-08-15：5E-1 首个聚焦绿灯

- 新增 `app/runtime` 的低依赖 Signal、严格 request/result/event/usage/trace 模型、中央
  Recorder 和原子不可变 Trace Store。
- 首轮实现测试暴露两项合同对齐问题：Artifact Schema 版本并非软件 semver，测试用
  RouterDecision 也必须携带现有路由证据；修复均保持现有产品合同而非放宽边界。
- 另修复一个负例 fixture 对 tuple 直接 append 的测试错误；最终 Runtime 聚焦测试
  `34 passed`。
- 下一步为实现后审查、补足失败路径以及 Skill/Agent/Harness 相邻回归；尚未宣称 5E-1
  完成，也尚未改动任何已有执行链 observer。

## 2026-08-15：5E-1 本地实现与门禁完成

- 实现强类型 Signal、Runtime request/result/event/usage/trace、中央 Recorder 与原子
  不可变 Trace Store；没有修改 AgentLoop、ToolRuntime、Harness、Provider 或 Prompt。
- 实现后补足缓存 Tool attempts/浮点 latency、Usage 完整性和 Trace 调用生命周期负例；
  Runtime 聚焦测试最终为 `39 passed`。
- Skill/Agent/Tool/Harness 相邻回归为 `166 passed, 55 subtests passed`；完整回归为
  `655 passed, 103 subtests passed`。
- development/independent holdout 两套 RAG Recall/MRR/nDCG 均为 1.0，holdout abstention/
  citation support 均为 1.0；compileall、Harness SDK/tracked-data、dry-run、治理和 diff
  门禁通过。
- 当前只剩提交、推送和 exact-SHA 公共 CI；CI 成功前 checkpoint 保持 5E-1，不进入
  5E-2，也不读取 Key 或调用 Provider。

## 2026-08-16：5E-1 已公开验证并交接 5E-2

- 5E-1 实现提交 `d891184e1bf82068188d2fb5715769bdaa3da022` 已推送到 `origin/main`；
  GitHub Actions run `31942483874` 对精确 SHA completed/success。
- 公共 Ubuntu/Python 3.11 CI 通过治理、655 tests/103 subtests、两套 RAG、compileall、
  Harness SDK/tracked-data boundary 与 dry-run；没有 Key 或 Provider I/O。
- 5E-1 至此正式闭环。唯一下一检查点为 5E-2 Observable run 入口审计/设计；Signal、
  Recorder 和 Store 的存在不等于 observer 或统一 run 已实现。

## 2026-08-16：5E-2 入口审计开始

- 按 canonical checkpoint 从 `b89ee033532525ed7addd4c6308fc4e4ef7bbae0` 恢复；开始时
  HEAD/origin 一致且工作树干净。
- 本轮使用 brainstorming、architecture-designer 与 planning-with-files：先比较 observer
  和同步 run 组合方案、明确 NFR/失败边界并持久记录，再决定实现计划。
- 当前只做 5E-2 入口审计/设计，不把 5E-1 Signal/Recorder/Store 的存在误写为 observable
  run 已实现；不实现 stream、不读取 Key、不调用 Provider。

## 2026-08-16：5E-2 入口设计与 ADR-0030 本地完成

- 完整审计 AgentLoop、ToolRuntime、Provider adapter、Harness llm adapter、
  SkillReviewExecutor、ReviewHarness、Runtime Recorder/Store 与相关测试；确认 Provider
  观察必须覆盖 Agent + Evaluation + repair + Revision。
- 新增初学者设计 `docs/plans/2026-08-16-agent-runtime-v1-observable-run-design.md`，比较三种
  组合方案并冻结共享 Observed Provider、定点 Agent/Harness observer、完整数据/控制流、
  失败映射、Artifact 投影、event budget 与 Task A-D TDD 顺序。
- 新增 ADR-0030，显式记录 Event/Trace 1.1、合法 1.0 读取、Agent terminal、零基 Evaluation
  attempt、section ID、可空 finish reason、missing Usage fail-closed 和两阶段 terminal commit；
  ADR-0029 已标注由 ADR-0030 深化。
- 本批没有修改产品代码、读取 Key、构造或调用 Provider、运行 held-out、调整 Prompt/模型
  或引入依赖；`AgentRuntimeV1.run()` 仍未实现。
- Canonical 唯一下一步切换为 5E-2 Task A 合同 1.1/observation port TDD；5E-2 本身仍进行中，
  不进入 5E-3。
- 设计相关 Runtime/Agent/Harness/Provider 聚焦回归为 `122 passed, 37 subtests passed`；完整
  回归为 `655 passed, 103 subtests passed`。
- RAG development 与 independent holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/
  citation support 均为 1.0；compileall、Harness SDK boundary、tracked secret/run-data、
  Harness dry-run、governance 和 `git diff --check` 通过。
- 在该本地验收点仍只完成设计闭环；当时提交、推送和 exact-SHA 公共 CI 尚未执行，
  不能称为公开冻结。

## 2026-08-16：5E-2 入口设计已公开验证

- 设计提交 `3c6f26a4802821548be8d61085552f5b9a790468` 已推送到 `origin/main`；GitHub
  Actions run `31944389807` 对该精确 SHA completed/success。
- 公共 Ubuntu/Python 3.11 CI 通过治理、655 tests/103 subtests、两套 RAG、compileall、
  Harness SDK/tracked-data boundary 与 dry-run；没有 Key 或 Provider I/O。
- 这只公开冻结 5E-2 的接缝和合同深化设计，不代表 observer、`run()` 或 `stream()` 已实现。
  唯一下一动作保持 Task A 合同 1.1/observation port TDD。

## 2026-08-16：5E-2 Task A 合同红灯已建立

- 恢复 canonical 状态、活动计划、路线/能力矩阵、ADR-0029/0030、5E-2 设计与现有
  Runtime/Provider 合同后，治理预检通过；开始时 HEAD/origin 均为 `b971b5c`，工作树干净。
- 新增 Event/Trace 1.1、合法 1.0 读取、Agent terminal、Harness 生命周期、零基 Evaluation
  attempt、section ID、finish reason、Tool failure code、observer port、terminal candidate、
  terminal-slot 与 Trace reference 版本红灯；同时补充 ChatResponse Usage/Zhipu fail-closed 测试。
- 首次聚焦运行按预期在收集阶段失败：缺少 `AgentRunTerminatedSignal` 与
  `app.runtime.observer`。没有调用 Provider、读取 Key、运行 held-out 或修改历史结果。
- 下一动作是实现 Task A 的最小产品合同，使上述聚焦测试进入更细粒度红绿循环；不接
  AgentLoop/Harness observer，也不实现 `run()` 或进入 Task B。

## 2026-08-16：5E-2 Task A 从中断点恢复

- 重新按仓库强制顺序读取全部持久状态与 5E-2 设计，运行 session catchup 无未同步输出，
  `scripts/check_project_governance.py` 通过。
- 复核未提交工作树确认它全部属于当前 Task A；没有回滚或覆盖用户无关修改。
- `app/runtime` compileall 通过；当前 Runtime contract/Recorder/Store/Provider 聚焦组为
  `114 passed, 44 subtests passed`。
- Task A 仍未完成：下一步先补齐 Store 失败、legacy 1.0、transition 同步、candidate
  one-shot 和 final-report digest 五类负例，再运行相邻/全量门禁。
- 本轮至今外部 Provider calls、Key reads 与 held-out executions 均为 0；不进入 Task B。

## 2026-08-16：5E-2 Task A 本地实现与门禁完成

- 补齐 Store 写失败后 abort candidate、Schema 1.0/1.1 版本边界、Runtime/Harness transition
  图同步、candidate one-shot、`final_report` digest 和已知 Harness publication 保真负例；
  所有新增点均先得到预期红灯，再做最小修正。
- 实现 Event/Trace/Reference 默认 1.1 与显式 1.0 读取，默认关闭 observation port、Agent
  terminal、零基 Evaluation、冒号 section ID、有限 finish reason、Tool failure code、
  Harness failure stage、共享 lifecycle reducer和 prepare/build/commit/abort terminal。
- `ChatResponse.usage` 改为显式必填；Zhipu missing/invalid Usage 以 allowlisted
  `provider_usage_unavailable` fail closed，不再伪造 `TokenUsage(0, 0)`。
- 聚焦回归 `131 passed, 44 subtests passed`；相邻 Agent/Harness/Tool/Provider 回归
  `149 passed, 38 subtests passed`；完整回归 `691 passed, 110 subtests passed`。
- RAG development 与 independent holdout 的 Recall/MRR/nDCG 均为 1.0，holdout abstention/
  citation support 均为 1.0；compileall、Harness SDK boundary、tracked secret/run-data、
  Harness dry-run、governance 和 `git diff --check` 通过。
- 当前只待提交、推送、exact-SHA 公共 CI 与 Task A 教学验收；Task B、统一 `run()`、
  `stream()`、Key/Provider I/O 和 held-out 均未开始。

## 2026-08-16：5E-2 Task A 已公开验证

- 实现提交 `2e78c9606fe93b56657d4bb13c8efe0f1eed98fe` 已推送；GitHub Actions run
  `31947625293` 对精确 SHA completed/success。
- 公共 Linux CI 通过治理、691 tests/110 subtests、两套 RAG、compileall、Harness SDK/
  tracked-data boundary 与 dry-run；没有 Key、真实 Provider I/O 或 held-out。
- Task A 至此闭环。唯一下一步为用户确认后的 Task B Observed Provider + AgentLoop 观察；
  本轮停下教学验收，不自动进入 Task B。

## 2026-08-16：5E-2 Task B 本地实现与门禁完成

- 先新增 `ObservedLLMProvider` 失败测试并得到预期 `ModuleNotFoundError` 红灯；最小实现随后
  记录 run-scoped 连续 ordinal、Agent/Evaluation/repair/Revision phase、Usage、有限
  finish reason、稳定 `provider_failed` 和 allowlisted provider detail。
- 将 Provider 安全细分错误允许列表下沉到共享低依赖模块，既有 adoption/calibration 调用
  继续兼容；capability、非法 phase 和 started observer failure 均在 delegate 前停止。
- 为 AgentLoop 新增 14 条首轮红灯，随后以 keyword-only default-None observer、整批预检后
  Tool started/completed、安全 ToolResult envelope 和统一 Agent terminal 转绿；
  `observer=None` 与旧结果及 Provider 请求逐字段一致。
- 实现后补测 Harness 内部 `llm.chat` 路径，真实暴露 ToolRuntime 会吞掉 observation failure；
  修正为在 retry、breaker、fallback 前穿透，started/completed 两个红灯均转绿。
- 最终聚焦回归 `81 passed`；相邻实现前组为 `216 passed, 15 subtests passed`，完整最终回归
  `721 passed, 110 subtests passed`。两套 RAG、compileall、Harness SDK boundary、tracked
  secret/run-data、Harness dry-run、governance 和 `git diff --check` 通过。
- 本批外部 Provider calls、Key reads 和 held-out executions 均为 0；没有接 Harness observer、
  实现统一 `run()`/`stream()`、修改 Prompt/模型或进入 Task C/D。下一动作只做提交、推送和
  exact-SHA 公共 CI。

## 2026-08-16：5E-2 Task B 已公开验证并交接 Task C

- 实现与持久状态提交 `28bd910525a7522be16bd69b6e945846839a4cd8` 已推送到 `origin/main`。
- GitHub Actions run `31952026988` 对精确 SHA completed/success；治理、`721 passed, 110
  subtests passed`、两套 RAG、compileall、Harness SDK/tracked-data boundary 与 dry-run 全部通过。
- Task B 正式闭环：共享 Observed Provider、AgentLoop 业务 Tool/terminal、ToolRuntime
  observation fail-fast 和 observer=None 兼容均有公开证据；本批没有 Key、真实 Provider 或
  held-out I/O。唯一下一步切换为 Task C Harness/Executor 持久化后观察，不进入 Task D、5E-3、
  5P 或 5F。

## 2026-08-17：5E-2 Task C 本地实现与门禁

- 先新增 Harness/Executor observation、Artifact projection、attempt 0/1、blocking category、
  rejected digest、Artifact integrity 和 RuntimeObservationError 穿透红灯；首轮缺少
  `app.runtime.artifacts`，随后按最小合同实现。
- `ReviewHarness` 接入可选 observer：transition 在持久化后观察，Evaluation Artifact
  成功注册并重新读取后观察，terminal Manifest 持久化后观察 publication；published/degraded
  关联 final report SHA，rejected 不关联报告。
- `SkillReviewExecutor.execute()` 增加可选 observer 并传给 Harness；Bound preparation、
  `SkillAgentDraftPreparer` 与 Executor 的 broad catch 都让 `RuntimeObservationError` 穿透。
  `_step_failure_reason()` 统一使用稳定 reason code，不再把异常类名带入 Harness/Runtime
  signal。
- Task C 聚焦为 `8 passed`；Harness/Skill/Agent/Provider/Runtime 相邻回归为 `84 passed`，
  Runtime contract/store 加 Task C 为 `77 passed`；完整回归为 `729 passed, 110 subtests passed`。
- 两套 RAG、compileall、tracked secret/run-data boundary、Harness dry-run、governance 和
  `git diff --check` 通过。第一次未设置项目根 `PYTHONPATH` 的系统 `pytest` 子进程出现既有
  editable-package 导入环境错误；使用项目 Python 3.11 + 项目根路径后完整通过，CI 通过
  editable install 不受影响。
- 本批没有读取 Key、调用 Provider、运行 held-out、修改 Prompt/模型、实现统一 `run()` 或
  `stream()`；Task C 待提交、推送和 exact-SHA public CI，Task D 未开始。

## 2026-08-17：5E-2 Task C 已公开验证并交接 Task D

- 提交 `8b69c9b` 已推送；GitHub Actions run `31957712118` 对 exact SHA completed/success。
- 公共 CI 通过治理、`729 passed, 110 subtests passed`、两套 RAG、compileall、Harness
  SDK/tracked-data boundary 与 dry-run；本批 Provider/Key/held-out I/O 为 0。
- Task C 正式闭环：Harness/Executor 持久化后观察、attempt 0/1、安全 Artifact 引用、稳定
  reason code 和 observation fail-fast 均有公开证据。唯一下一步切换为 Task D 统一同步
  `AgentRuntimeV1.run()` 纵向切片；不进入 5E-3、5P 或 5F。

## 2026-08-17：5E-2 Task D 初版纵向切片

- 恢复并审查未提交的 `app/runtime/runtime.py` 与 `SkillAgentDraftPreparer` observer 接线；
  治理预检通过，工作树没有无关改动。
- compileall 与 Task A-C/Agent/Harness 相邻回归 `121 passed`。
- 新增 `tests/test_agent_runtime.py` 首轮 7 项：两个真实 Skill 统一入口、共享 Agent/Evaluation
  Provider、真实本地 RAG、Agent/Evaluation Provider 失败安全降级、Context 前失败与 Trace
  写入失败；当前 `7 passed`。
- 该轮尚未验收；正在修复 selected-only request、单一 `_execute()` 核心、精确事件顺序、
  event-budget 预检和 Trace 写失败后的内存失败终态。

## 2026-08-17：5E-2 Task D 本地实现与门禁完成

- 新增 `AgentRuntimeV1.run()` 与单一 `_execute()`，组合 Boundary、Context、run-scoped
  observed Provider、真实本地 `knowledge.search`、AgentLoop、唯一 Harness、typed output、
  Artifact projection、RuntimeRecorder 与 RuntimeTraceStore。
- 请求合同只允许 selected Router 决策；Runtime 仍验证 Catalog 版本、输入和 Artifact。
  `max_revisions` 真实传入 Harness，event budget 按三次 llm retry、Evaluation repair、
  Revision 和完整 lifecycle 的 61-slot 最坏上界做 I/O 前预检。
- Trace write 失败会取消完成候选并只提交内存 failed terminal；observation failure 不会被
  误分类为 Agent/Context 失败，且从 terminal Manifest 保留已知 publication。
- 新增 18 项纵向测试；聚焦/相邻最终为 `117 passed`，完整为
  `747 passed, 110 subtests passed`。两套 RAG 1.0、compileall、Harness SDK/tracked-data
  boundary、Harness dry-run、governance 与 diff check 通过。
- 本批外部 Provider calls、Key reads 与 held-out executions 均为 0；没有修改 Prompt、模型、
  RAG 数据或引入 LangGraph/Agent SDK。Task D 尚待提交、推送和 exact-SHA public CI。
- 用户随后明确授权：Task D 公共闭环后无需再次等待“继续”，直接进入唯一下一检查点
  5E-3；本授权不扩展到 5E-4 或其他阶段，已记录为 RQ-037。

## 2026-08-17：5E-3 入口审计与方案比较

- 恢复时先发现 canonical 状态已是 `5E-3`，但状态文件还保留旧的 `5E-2 Task D` 唯一下一步，
  活动计划同时有两个 `in_progress` phase；已用最小文档补丁修复。
- `check_project_governance.py`、`tests/test_project_governance.py`（2 passed）和 `git diff --check`
  已通过，随后才开始功能审计。
- 审计 `AgentRuntimeV1._execute()`、`RuntimeRecorder`、observer 接缝、终态 prepare/commit、
  RuntimeTraceStore、ReviewHarness 持久化观察和现有 Runtime 测试，确认事件产生点是真实执行时刻，
  但当前没有外部事件交付层。
- 方案初步冻结为“进程内 worker + 有界 queue”：复用唯一 `_execute()`；非终态事件在 Recorder
  成功追加后交付，成功/失败终态只在 commit 后交付；消费者异常与可信 Recorder 异常隔离；队列满时
  阻塞执行以保持事件完整。直接 generator 与外部消息队列分别因侵入性/过度持久化语义暂不采用。
- 本轮仍未实现 `stream()`；没有读取 Key、调用任何 Provider、改变 Prompt/模型或进入 5E-4。

## 2026-08-17：5E-3 第一批 stream TDD 实现

- 先新增 5 项红灯测试，覆盖严格 stream item、懒启动、实时 Provider started、事件顺序和
  Trace 写失败；首轮在收集阶段因 `RuntimeStreamItem` 尚不存在而红灯。
- 最小实现新增 `RuntimeStreamItem`、`RuntimeEventSink`、`_RuntimeStreamPublisher` 和
  `AgentRuntimeV1.stream()`；`run()` 与 worker 共用 `_run_with_sink()`/`_execute()`。
- `_RecorderObserver` 在 Recorder append 成功后交付非终态事件；成功/失败终态的
  `_finish_success`、`_finish_failure` 和内存失败路径均在 terminal commit 后交付。
- 聚焦 `tests/test_agent_runtime_stream.py`：`5 passed`；Runtime/Agent/Harness 相邻合同、
  Recorder、Store 和新 stream 回归：`70 passed`；compileall 通过。
- 当前仍未完成 5E-3：尚需 run/stream parity 的事实对照、tiny queue 背压、消费者关闭隔离和
  unexpected worker failure 语义测试；没有 Key、真实 Provider、Prompt/模型或第三方 SDK I/O。

## 2026-08-17：5E-3 parity、背压与关闭边界

- 新增 parity 测试：分别运行同步 `run()` 与异步交付的 `stream()`，对照 Trace 中的 signal
  payload、顺序、terminal reason、publication 和 typed output；仅忽略预期不同的 run_id。
- 新增 queue size 合同、`queue_size=1` 背压完整性、消费者关闭后继续完成业务并落盘 Trace、
  以及 worker 未预期异常与 `run()` 同语义传播测试。
- 聚焦 `tests/test_agent_runtime_stream.py` 目前 `15 passed`；实现未引入新依赖或真实 I/O。

## 2026-08-17：5E-3 预期终态扩展

- 追加 stream 的 Agent Provider failure、Evaluation Provider failure、rejected publication 和
  Boundary version drift 案例；均保持与同步 Runtime 相同的 publication/terminal 语义，rejected
  不暴露报告，Boundary 失败不调用 Provider。
- stream 聚焦目前 `15 passed`；完整回归尚待最终收尾批次后重新执行。

## 2026-08-17：5E-3 本地实现收尾

- stream 聚焦最终为 `15 passed`；完整回归最终为 `762 passed, 110 subtests passed`。
- compileall、治理检查、治理测试、RAG/stream 聚焦门禁和 `git diff --check` 均通过。
- 当前本地实现已经覆盖 item 合同、懒启动、实时事件、run/stream parity、success/degraded/
  rejected/boundary、tiny queue 背压、订阅关闭、Trace persistence failure 与 unexpected
  worker error；下一步仅为提交、推送与 exact-SHA 公共 CI。

## 2026-08-17：5E-3 公共闭环并进入 5E-4

- 精确 SHA `80b76a182f38d31d862f32ffa1dc0f14ebd1c971` 的 GitHub Actions run `31960987333`
  成功；所有公开门禁通过，5E-3 正式完成。
- 持久状态、活动计划、项目决策、路线历史和能力矩阵已同步，canonical 下一检查点切换为
  `5E-4 Runtime Evaluation & Exit Review`。
- 新增 `docs/plans/2026-08-17-agent-runtime-v1-evaluation-exit-design.md`，冻结初始
  exit matrix、纳入/排除范围和审查顺序；下一步先做 5E-4 入口审计，不直接引入新技术。

## 2026-08-17：5E-4 首轮入口审计

- 新增 `docs/plans/2026-08-17-agent-runtime-v1-exit-matrix.md`，将 5E-1 至 5E-3 的合同、
  功能、失败、实时事件、资源、安全、交付和后续边界逐项绑定源码、测试、公开证据、限制与
  退出影响。
- 复核 Runtime 相关聚焦集合：`128 passed`；compileall、治理和 diff check 通过。
- 首轮没有发现当前 V1 必须立即补的新功能缺口；真实厂商领域质量、API/SSE、durable log、
  cancel/resume、Memory、MCP、Multi-Agent、生产 SLO 均正确标为 deferred/unknown，不把它们
  偷渡进 5E。
- 5E-4 尚未完成：还需将矩阵与完整回归、公开 CI、教学理解和最终退出决策逐项复读并公开验证。

## 2026-08-17：5E-4 本地最终退出审查

- 完整回归重新执行为 `762 passed, 110 subtests passed`；compileall、治理、RAG/stream 聚焦
  29 项和 diff check 通过。
- 新增 `docs/plans/2026-08-17-agent-runtime-v1-exit-review.md`；最终本地决策为
  `close-with-deferred-boundaries`，并以面试级表述解释 Runtime V1 已完成与未完成的边界。
- 当前没有产品代码变更；下一步只提交/推送 5E-4 审查与状态并等待 exact-SHA 公共 CI。

## 2026-08-17：5E-4 exact-SHA 公共闭环并暂停

- 退出审查提交 `3d3656195a66adfd4595cffa145c978d24c33628` 已推送，GitHub Actions run
  `31962252231` completed/success；公开门禁全部通过。
- 5E-4 与整个 5E AgentRuntime V1 正式完成，最终结论为
  `close-with-deferred-boundaries`，不宣称生产就绪或真实模型领域质量已准入。
- canonical 已交接到 `5P-entry-design`，但按 RQ-039 暂停；本轮未开始 5P 设计、实现或
  Provider I/O，等待用户下一次明确“继续”。

## 2026-08-17：开始 5P-entry-design

- 用户明确“继续下一步”，当前恢复并开始唯一检查点 `5P-entry-design`；不自动进入实现。
- 按仓库恢复顺序复读 canonical、活动计划、需求/路线/能力矩阵，session catchup 无未同步
  输出，治理预检通过，起始工作树干净。
- 首轮只读扫描确认当前没有 API 模块，并暴露 v1.3 五端点清单与较晚“5P 只做近期类型化
  入口”之间的范围差异；下一步从现有 Runtime/Artifact/CLI 接缝和依赖事实裁决最小切片。

## 2026-08-17：5E-2 Task D exact-SHA 公共闭环

- 实现提交 `d49508ef46876da6653ddcbe63a3584bdcbba711` 已推送到 `origin/main`；GitHub
  Actions run `31959646589` completed/success，pytest、两套 RAG、compileall、Harness
  SDK/tracked-data boundary、dry-run 和治理全部成功。
- 5E-2 正式完成：统一同步 `run()` 的 18 项新增测试与完整 `747 passed, 110 subtests passed`
  证据已公开；无 Key、真实 Provider 或 held-out I/O。
- 按 RQ-037，canonical 当前检查点已切换到 `5E-3 Live stream() & Parity` 入口审计/设计，
  下一动作只审计 run/stream 同源事件、终态和消费者失败隔离，不实现完整 stream 或进入 5E-4。

## 2026-08-17：5P-entry-design 方案冻结

- 完成 Runtime request/result、FileRunStore/RuntimeTraceStore、Riot/DataDragon、Summary/Report、
  Catalog/ExecutionBoundary、recent Skill、Prompt/Context/Evaluation/Revision 与历史范围审计。
- 发现 5P 不只包含早期 API：5D 退出文件明确保留 `5P Prompt Program V1`；当前 Runtime 的
  prompt profile identity 仍硬编码，而现有实验 fingerprint 已覆盖真实 Prompt 组件。
- 接受两个顺序决策：ADR-0032 先建立版本化 Prompt Program 与 drift gate；ADR-0033 再以薄
  FastAPI + Application Service 接入现有 AgentRuntime/Harness 和文件型查询投影。
- 新增 `docs/plans/2026-08-17-prompt-program-and-early-product-slice-design.md`，明确请求/端点、
  typed selection、composition、receipt/query、错误映射、NFR、测试矩阵和 5P-1 至 5P-6。
- 本批没有 FastAPI 依赖或产品代码，没有 Key/Riot/Provider/held-out I/O；下一步先完成持久状态
  同步与验证，成功后停在 5P-1，不直接实现。

## 2026-08-17：5P-entry-design 本地验证

- 完整 pytest：`762 passed, 110 subtests passed`；
- RAG development：Recall/MRR/nDCG `1.0`，no-answer FPR `0.0`；
- 独立 RAG 4M holdout：Recall/MRR/nDCG/abstention/citation support `1.0`，FPR `0.0`；
- governance script 与 2 项治理测试、compileall、Harness SDK boundary、tracked secret/run-data
  boundary、Harness dry-run 和 `git diff --check` 通过；
- 所有验证使用本地 fixture/Fake steps；真实 Riot/LLM/held-out 调用为 0；
- 设计复核收紧 Runtime failure 为固定 HTTP 500，并补充 semantic fingerprint 与本地文件信任
  边界，避免过度声称完整防篡改或形式化等价。
- 首次清理本批 `tmp/5p-entry-*` 时，终端策略拒绝了“同一命令内验证后递归删除”的组合；命令
  未执行。后续改为分离的只读绝对路径验证和 literal cleanup，不重复该组合。
- 只读验证确认三个目标都位于 `D:\riftcoach-agent\tmp\5p-entry-*`；随后 literal
  `Remove-Item` 仍在进程创建前被策略拒绝。按 3-strike 原则不再重复，文件处于 Git 忽略的
  `tmp/`，不会进入提交或产品状态。
- 首次 cached diff check 在提交前发现 ADR-0032/0033 各有一个多余 EOF 空行；门禁正确阻止
  提交，现已删除并要求重新暂存后复核。

## 2026-08-17：5P-entry-design exact-SHA 公共闭环

- 设计提交 `49841ec44832875e65b17770557415113e67b1db` 已推送到 `origin/main`；
- GitHub Actions run `31985199623` completed/success，完整 pytest、两套 RAG、compileall、
  governance、SDK/tracked-data boundary 与 Harness dry-run 全部成功；CI 无 Key/外部调用；
- canonical 现切换到 `5P-1-product-contract-compiler` 准备状态；按 RQ-040 本轮在状态收尾提交后
  结束，不实现 5P-1、Prompt Program、FastAPI 或 5F。
- 首次收尾治理检查暴露两个状态格式问题：治理状态枚举不支持 `ready`，且历史计划结构含多个
  Next Step，第一节尚未同步新 checkpoint。门禁正确阻止提交；将改用 `in_progress` + 正文
  “准备状态”，并统一所有 Next Step，不修改产品范围。
- 修正后 canonical 使用受支持的 `in_progress`，活动计划只保留一个 Next Step 且含精确
  `5P-1-product-contract-compiler`；governance、2 项治理测试和 diff check 重新通过。
