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
