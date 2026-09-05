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

## 2026-08-17：开始 5P-1 Product Contract Compiler

- 用户明确“继续”，本轮只恢复并开展 canonical `5P-1-product-contract-compiler`。
- 按 `AGENTS.md` 顺序复读 canonical、活动计划、需求/路线/能力矩阵、5P 设计/ADR 和相关
  Skill/Runtime 源码测试；session catchup 无未同步输出。
- 治理预检通过；起始 `HEAD == origin/main == a2c3ba71cf07373cfbe0d2bd3252ada241e43e97`，
  工作树干净。
- 已完成初学者问题/原理/范围/数据流/测试/限制讲解，并新增 TDD 实施计划
  `docs/plans/2026-08-17-5p1-product-contract-compiler-implementation.md`。
- 当前尚未写产品代码或测试；Key reads、Riot/Provider calls、held-out executions 均为 0，
  不进入 5P-2 或安装 FastAPI。

## 2026-08-17：5P-1 首轮 TDD 红灯

- 新增 `tests/test_recent_review_product_compiler.py`，一次覆盖产品 DTO、服务器字段隔离、Riot ID
  边界、typed selection、Router 零调用、Manifest policy 投影、run ID、Artifact digest、
  Catalog version drift 和既有 ExecutionBoundary 二次校验。
- 首次聚焦运行在收集期按预期以 `ModuleNotFoundError: No module named 'app.product'` 红灯；这证明
  测试没有误命中旧实现，下一步只新增最小 `app.product` 合同和编译器。
- 红灯前后没有读取 Key、调用 Riot/Provider 或运行 held-out；没有进入 FastAPI/Prompt Program。

## 2026-08-17：5P-1 最小实现与相邻回归

- 新增 `app/product/recent_review.py` 与包导出：严格 frozen/strict/extra-forbid 产品 DTO、最后一个
  `#` Riot ID 拆分、本地长度/控制字符边界、服务器 run ID、Catalog-backed typed selection、
  Manifest-derived Runtime policy 和完整 `RuntimeRunRequest` 编译已实现。
- typed selection 只使用 `entrypoint:reviews.recent` 机器证据；测试把
  `DeterministicSkillRouter.route()` 替换成必失败函数，仍能完成编译，证明本路径没有重新猜路由。
- Artifact 继续复用 `SkillInputArtifactBinding.from_content()`；编译结果能通过现有
  `SkillExecutionBoundary`，篡改 payload/digest 或编译后 Catalog version drift 均被拒绝。
- 首轮聚焦为 `32 passed`；加强 Manifest 动态映射和服务器字段负例后，产品/Boundary/Runtime
  相邻为 `63 passed`；更广的 Skill/Router/Context/Compiler/Harness/Runtime 回归为
  `213 passed`。
- `app/product` compileall 通过；当前 Key reads、Riot/Provider calls、held-out executions 均为 0。
  尚未进入完整项目门禁或 5P-2。

## 2026-08-17：5P-1 完整本地门禁

- 完整回归为 `796 passed, 110 subtests passed`。
- RAG development 的 Recall/MRR/nDCG 为 `1.0`、no-answer FPR 为 `0.0`；独立 4M holdout
  的 Recall/MRR/nDCG/abstention/citation support 均为 `1.0`，FPR 为 `0.0`。
- `compileall app scripts tests`、2 项治理测试、Harness SDK boundary、tracked secret/run-data
  boundary、Harness dry-run 和治理脚本通过。
- 第一次跨多文件状态补丁把真实中文句首误写成 `current唯一`，`apply_patch` 在上下文校验时
  原子拒绝、没有部分修改；随后拆成精确小补丁完成 canonical/计划/路线/矩阵/决策同步。
- 当前 canonical 仍保持 5P-1，状态为本地完成等待公共 CI；下一动作只提交、推送并验证 exact-SHA，
  不进入 5P-2。本批外部调用仍为 0。

## 2026-08-17：5P-1 exact-SHA 公共闭环

- 实现与状态提交 `57bd36adcd289b7cc51c1c430e04398daf0683f3` 已推送到 `origin/main`。
- GitHub Actions run `31987501935` 对精确 SHA completed/success；完整 pytest、两套 RAG、
  compileall、治理、SDK/tracked-data boundary 和 Harness dry-run 全部通过。
- 5P-1 正式完成：本地代码、公开证据和当前 owner understanding 已同步；参考项目审计与部署/
  作品集成熟度没有被错误提升，真实 Provider/Key/held-out I/O 仍为 0。
- canonical 已只交接到 `5P-2-prompt-program-runtime-composition`，等待用户再次明确继续；本轮
  不实现 Prompt Program、FastAPI 或 5F。

## 2026-08-17：5P-2 交接措辞修正

- 最终只读复核发现 canonical 仍保留旧句“不得自动进入 5P-2”，与当前“5P-2 是唯一下一检查点、
  但等待用户明确继续”语义不一致；已改为等待用户授权后实现 5P-2，且不得自动进入 5P-3/FastAPI/5F。
- 这是持久状态措辞修正，不改变 5P-1 代码、测试、提交或公开证据；修正后需再次通过治理和 exact-SHA CI。

## 2026-08-17：5P-2 Prompt Program V1 与 Runtime composition 本地实现

- 按 canonical 唯一检查点先写实施计划
  `docs/plans/2026-08-17-5p2-prompt-program-runtime-composition-implementation.md`，
  没有进入 5P-3、FastAPI 或 5F。
- 暴露 `build_component_fingerprints()` 公共入口，继续复用既有
  `PromptContextSnapshot` 的 canonical probe；没有创建第二套 Prompt 摘要算法。
- 新增严格 frozen/extra-forbid `PromptProgramManifest`、`PromptProgramCatalog`、
  `PromptProgramResolver` 和 checked-in `recent-form-review-coach@1.0.0` manifest。Manifest
  只保存 program/Skill/Context/Evaluation 身份与组件 SHA-256，不保存 Prompt 正文；自身 digest、
  secure Evaluation 1.1、Skill/version/context 匹配和当前组件重算均是 fail-closed 门禁。
- 新增 `RuntimeCompositionRoot`，在组合时验证所有 Program，再把 resolver 注入 `AgentRuntimeV1`；
  Runtime identity 不再硬编码 `<skill>-coach@1.0.0`。旧 direct Runtime 测试显式使用
  `LegacyRuntimeIdentityResolver`，不能冒充产品 Program 验证。
- 新增产品 composition 纵向测试；Prompt Program/Runtime/identity/产品编译相邻聚焦回归
  `142 passed`，完整回归 `805 passed, 110 subtests passed`；compileall、RAG development/
  independent holdout、Harness dry-run、secret/tracked-data、governance 与 diff check 均通过。
- 本批 Key reads、Riot/Provider calls、held-out executions 均为 0；真实 Provider 领域质量仍
  unknown；当前尚待最终状态/路线同步、提交、推送与 exact-SHA 公共 CI。

## 2026-08-17：5P-2 exact-SHA 公共闭环

- 实现与计划 EOF 修正提交最终形成 exact SHA
  `0a9651f4e305616626c58ea28e2c300a491f2a3b` 并推送到 `origin/main`。
- GitHub Actions run `31988837293` completed/success；完整 pytest、两套 RAG、compileall、
  governance、SDK/tracked-data boundary 与 Harness dry-run 全部通过，CI 无 Key/外部调用。
- 5P-2 正式完成：Prompt Program V1、drift gate、verified Runtime identity 与 composition root
  已获得本地和公开证据；这不提升真实 Provider 领域质量，也不表示 API 产品完成。
- canonical 已只交接到 `5P-3-domain-application-service`，等待用户再次明确继续；本轮不实现
  Domain/Application Service、receipt/query、FastAPI 或 5F。

## 2026-08-17：开始 5P-3 Domain/Application Service

- 用户明确“继续下一步”，本轮只恢复 canonical `5P-3-domain-application-service`。
- 按 `AGENTS.md` 恢复 canonical、活动计划、需求/路线/能力矩阵并运行治理预检；起始
  `HEAD == origin/main == 866820e4d78a74f5e9a9f13aa515bfce3afc7f02`，工作树干净。
- 已完成初学者问题/原理/范围/数据流/测试/限制讲解，并新增 TDD 实施计划
  `docs/plans/2026-08-17-5p3-domain-application-service-implementation.md`。
- 审计发现 5P-2 已验证 Program identity，但 product root 仍允许任意 execution factory；5P-3
  作为首个正式消费者将用既有 Secure Evaluation 1.1 合同做窄幅向后深化并独立测试，不改写
  5P-2 历史证据。
- 当前尚未写 5P-3 产品代码或测试；Key/Riot/Provider/held-out I/O 为 0，不进入 5P-4/FastAPI。

## 2026-08-17：5P-3 本地实现与门禁完成

- 先建立 Domain Service 导入红灯，再提升 Summary Builder/Report Renderer 并让两个 CLI 复用；
  Domain/Stage 1 聚焦 `7 passed`，报告输出逐字节一致。
- Application Service 先以缺模块红灯冻结 published/degraded/rejected、顺序、上游错误、零比赛、
  Schema/compiler/Prompt drift、Runtime failed/不一致和脱敏边界；实现后 `20 passed`。
- secure execution factory 先以缺符号红灯冻结实际 Evaluator/Reviser 类型；实现后 Prompt Program
  聚焦 `10 passed`，产品默认不再依赖任意外部 factory，显式测试 factory 兼容保留。
- 5P 相邻纵向回归 `263 passed`；完整回归 `830 passed, 110 subtests passed`；两套 RAG、
  compileall、治理测试、Harness SDK boundary、tracked secret/run-data、Harness dry-run、governance
  和 diff check 均通过。
- 本批没有安装 FastAPI、写 receipt/query、读取 Key、调用 Riot/Provider 或运行 held-out；当前
  5P-3 仍为 in_progress，只待实现提交、推送与 exact-SHA 公共 CI。

## 2026-08-17：5P-3 exact-SHA 公共闭环

- 实现提交 `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 已推送到 `origin/main`。
- GitHub Actions run `31998739178` completed/success；完整 pytest、两套 RAG、compileall、
  governance、SDK/tracked-data boundary 与 Harness dry-run 全部成功，CI 无 Key/外部调用。
- 5P-3 正式完成：Domain/Application Service、body-free 安全错误和 secure product factory
  已获得本地与公开证据；这不表示 receipt/query、FastAPI 或真实模型质量完成。
- canonical 只交接到 `5P-4-file-backed-run-receipt-query`，等待用户再次明确继续；本轮不实现 5P-4。

## 2026-08-17：开始 5P-4 File-backed Run Receipt & Query

- 用户再次明确“继续”，RQ-044 只授权 canonical `5P-4-file-backed-run-receipt-query`；不授权
  FastAPI/5P-5、SQL/Memory、恢复扫描、5F 或真实外部 I/O。
- 按 `AGENTS.md` 恢复 canonical、活动计划、需求/路线/能力矩阵、ADR-0033 与 5P 总设计；治理
  预检通过，起始 `HEAD == origin/main == 4389b3a0e6cd22447812dcc0f7887c0ee35125bf`，工作树干净。
- 已完成 receipt/Trace/manifest/final Artifact 的初学者职责说明，并审计 Store、Runtime terminal、
  Application Service 与现有测试接缝。
- 新增 TDD 实施计划 `docs/plans/2026-08-17-5p4-file-backed-run-receipt-query-implementation.md`；
  当前尚未写功能代码或测试，Key/Riot/Provider/held-out I/O 为 0。

## 2026-08-17：5P-4 本地 TDD 与完整门禁

- Batch A/B 首轮按预期因 `app.product.run_receipts` / `run_query` 不存在而 collection 红灯；最小
  实现后 receipt/query `26 passed`。
- Batch C 先因 Application Service 不接受 `receipt_writer` 形成 `23 failed` 红灯；接入显式
  writer、先校验服务器 run_id、在 terminal projection 前写 completed/failed receipt 后转绿。
- 新增 `ApiRunReceipt`、`FileRunReceiptStore`、`RunView`、`RunQueryService` 与 body-free
  `RunQueryError`；Trace/manifest/final Artifact 状态、身份和真实字节均交叉校验。
- receipt/query/Application 聚焦最终 `50 passed`；Store/Runtime 相邻 `103 passed, 12 subtests
  passed`；5P/Runtime/Harness 比例回归 `179 passed, 12 subtests passed`；完整回归
  `860 passed, 110 subtests passed`。
- RAG development 与 independent holdout 全部门槛为 `1.0`（no-answer FPR `0.0`）；compileall、
  Harness SDK boundary、tracked secret/run-data、Harness dry-run、governance 和 diff check 通过。
- 本批 Key/Riot/Provider/held-out I/O 为 0；5P-4 仍为 in_progress，只待提交、推送和 exact-SHA
  公共 CI，不进入 FastAPI/5P-5。

## 2026-08-17：5P-4 exact-SHA 公共闭环

- 实现提交 `932a863120a4561f58c477a69becbccd2ec9ff45` 已推送到 `origin/main`。
- GitHub Actions run `32002994441` completed/success；完整 pytest、两套 RAG、compileall、
  governance、SDK/tracked-data boundary 与 Harness dry-run 全部成功，CI 无 Key/外部调用。
- 5P-4 正式完成：receipt、strict query、Trace/manifest/final Artifact 完整性链和 Application
  receipt 接缝已有本地与公共证据；这不表示 FastAPI、SQL/恢复或真实模型质量完成。
- canonical 只交接到 `5P-5-thin-fastapi-adapter-no-io-vertical-slice`，等待用户再次明确继续；
  本轮不安装 FastAPI 或实现 5P-5。

## 2026-08-17：开始 5P-5 Thin FastAPI Adapter

- 用户明确“继续5P-5”，按 RQ-045 恢复唯一 canonical 检查点；先完成恢复顺序、治理检查和
  初学者范围说明，未读取 Key、未调用 Riot/Provider、未运行 held-out。
- 新增实施计划 `docs/plans/2026-08-17-5p5-thin-fastapi-adapter-implementation.md`，冻结
  四个端点、显式依赖注入、错误映射、TestClient/no-I/O 和不进入 5P-6/5F 的边界。
- 当前工作树尚未写 5P-5 产品代码；下一动作是新增红灯 API 合同测试。

## 2026-08-17：5P-5 本地 TDD 与完整门禁

- 首轮红灯在 `app.api` 缺失处停止；随后加入 `fastapi>=0.115,<1` 与 dev `httpx>=0.27,<1`，
  `.venv` 实测 FastAPI 0.141.1 / Starlette 1.6.0 / httpx 0.28.1，`pip check` 无冲突。
- 新增 `create_app(review_service, query_service)`、严格 HTTP DTO、四个固定端点、422 请求
  收敛、Application/Query 安全状态映射、受控 Retry-After 和 Markdown report；handler 不导入
  CLI、Provider、Harness、Runtime implementation 或 Skill Router。
- API 聚焦 24 项通过；其中一个真实 no-I/O 纵向案例走过 TestClient、Application Service、
  Catalog、Prompt Program、真实 Runtime/Harness/本地 RAG、Fake Provider、receipt/Trace/Artifact
  与真实 RunQueryService，Fake Provider 3 个本地响应，Key/Riot/网络/held-out I/O 均为 0。
- API/Application/receipt/query 相邻为 `71 passed`；最终完整回归为
  `884 passed, 1 warning, 110 subtests passed`。唯一 warning 来自 FastAPI 0.141.1 当前
  TestClient 对 httpx 的上游 deprecation 提示，不影响行为或依赖完整性，未通过屏蔽警告伪装。
- 两套 RAG 质量门、compileall、Harness SDK boundary、tracked secret/run-data、Harness dry-run、
  2 项治理测试、治理脚本和 diff check 均通过；当前只待状态收尾、提交、推送和 exact-SHA CI，
  不进入 5P-6/5F。

## 2026-08-17：5P-5 exact-SHA 公共闭环

- 提交 `6d1e5b0af186f523bee35c24c6873578a149b824` 已推送到 `origin/main`。
- GitHub Actions run `32005648179`（pytest job `95314459966`）completed/success；公开门禁
  全部通过，包含完整 pytest、两套 RAG、compileall、治理、Harness SDK boundary、tracked
  secret/run-data 和 dry-run。
- 5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice 正式关闭：本地代码、owner understanding、
  公开证据已同步；参考项目审计与真实 Provider/部署成熟度没有被错误提升。
- canonical 只交接到 `5P-6-product-slice-evaluation-exit-review`，等待用户明确继续；本轮不实现
  5P-6、5F、阶段 6 或任何真实 Provider I/O。

## 2026-08-17：开始 5P-6 Product Slice Exit Review

- 用户再次明确“继续”，RQ-046 只授权 canonical `5P-6-product-slice-evaluation-exit-review`。
- 已按 AGENTS 顺序恢复 canonical/活动计划/需求/路线/能力矩阵并通过治理预检；起始
  `HEAD == origin/main == 1ba9355eabeab3d7b636eedbb9c80a4cf7864525`，工作树干净，最终
  5P-5 Actions run `32005901066` completed/success。
- 新增退出审查计划 `docs/plans/2026-08-17-5p6-product-slice-exit-review-plan.md`；当前尚未
  编写 exit matrix 或修改产品代码，Key/Riot/Provider/held-out I/O 为 0。

## 2026-08-17：5P-6 本地退出审查完成

- 新增 `docs/plans/2026-08-17-product-slice-exit-matrix.md`，逐项覆盖原设计十项功能要求、
  分层职责、NFR/安全/no-I/O 与 deferred/unknown 边界。
- 新增 `docs/plans/2026-08-17-product-slice-exit-review.md`，面向初学者解释 5P 的数据流、
  控制流、各层职责、测试证据、生产限制、参考项目/框架采用边界和面试表述。
- 审查未发现 5P 结构性代码缺口；本地裁决为 `close-with-deferred-boundaries`。聚焦
  `121 passed, 1 warning`、相邻 `166 passed`、完整 `884 passed, 1 warning, 110 subtests passed`
  与两套 RAG/compileall/安全/治理/dry-run 门禁通过，外部 I/O 为 0。
- 当前仍停在 5P-6，只待提交、推送和 exact-SHA 公共 CI；成功前不正式关闭 5P，不进入 5F。

## 2026-08-17：5P-6 exact-SHA 公共闭环与 5F 交接

- 退出审查提交 `8c8acc6911209e645cfaee18bd40870f78d8704f` 已推送；Actions run `32010604551`
  对 exact SHA 全部门禁成功。
- 5P-6 与整个 5P 正式完成，四条进度线已保持分离：本地产品代码/理解与公共证据闭环，真实
  Provider 领域质量和正式部署仍未提升。
- canonical 当前为 `5F-entry-design` 准备状态，等待用户再次明确继续；不自动实施 Pi/Claude
  Agent SDK、模型切换、真实 Provider 或阶段 6。

## 2026-08-17：开始 5F-entry-design（Pi-only）

- 用户明确确认 `Pi-only`：5F 不再实测 Claude Agent SDK；Claude 只作为书面替代方案和排除依据，
  不安装、不调用、不改变主 Runtime。
- 本轮范围固定为：Pi 官方实现/许可证/版本审计、当前 Runtime 合同映射、同一 recent-form-review
  切片的无 I/O 对照设计、跨语言/sidecar 成本、Trace/Harness/错误安全和采用/拒绝门槛。
- 尚未写 Pi 适配代码、安装 Node/Pi、读取模型 Key、调用 Provider 或执行真实模型；下一步是形成
  ADR 与 5F entry design 文档，并通过治理和 exact-SHA 公共验证。

## 2026-08-17：5F-entry-design exact-SHA 公共闭环与 5F-1 交接

- ADR-0034 与 Pi-only entry design 提交 `ce979752808271696b1dfe499317ead66de6aacb` 已推送；
  Actions run `32013948784` 对 exact SHA 全部门禁成功。
- 5F-entry-design 正式完成；当前四条进度线保持分离，Pi 尚未安装/接入，真实模型质量与产品默认
  Runtime 没有任何提升。
- canonical 只交接到 `5F-1-pi-source-license-contract-audit` 准备状态，等待用户再次明确继续；
  不自动开始源码审计、安装 Pi 或调用 Provider。

## 2026-08-17：5F-1 官方 Pi Source / License / Contract Audit（本地）

- 用户再次明确继续；已按 RQ-048 只读审计当前官方 `earendil-works/pi`，冻结 release
  `v0.84.2` / commit `914cf1472e715297caa30db4b9535d534a9eb718`、Agent/AI package `0.84.2`、
  official-registry integrity、MIT license 与 Node `>=22.19.0`。
- 已将 Pi Agent/StreamFn/Tool/Event/State/Abort/Usage 与当前 AgentRunRequest、ToolRuntime、
  RuntimeUsage/Trace、ReviewHarness 逐项映射。确认整批 Tool 原子预检、跨轮 duplicate、总预算、
  Usage completeness、body-free Trace 和发布门不能由 Pi 自动替代。
- 新增 `docs/plans/2026-08-17-5f1-pi-source-license-contract-audit.md`；本地结论是允许进入隔离、
  no-I/O 的 5F-2 protocol spike，但不采用 Pi、不修改主 Runtime。
- 完整回归 `884 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、governance、
  Harness SDK/tracked-data boundary、dry-run 与 diff check 全部通过。
- 本轮 Pi/Node package 安装、adapter、Key/Provider/Riot I/O 均为 0；下一步只做提交、推送和
  exact-SHA 公共验证，成功后才交接 5F-2。

## 2026-08-17：5F-1 exact-SHA 公共闭环与 5F-2 交接

- 审计提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 已推送；GitHub Actions run
  `32016852979` 对该精确 SHA 的 pytest、两套 RAG、compileall、治理、SDK/tracked-data
  boundary 与 Harness dry-run 全部成功。
- 5F-1 正式完成，结论保持“允许有条件进入离线 adapter spike”，不提升为 adopt；Pi/Node package
  安装、adapter、Key/Provider/Riot I/O 仍为 0。
- canonical 已交接到 `5F-2-offline-protocol-adapter-spike` 准备状态，等待用户再次明确继续；
  当前没有安装依赖、创建 lockfile/sidecar 或实现协议。

## 2026-08-17：开始 5F-2 Offline Protocol Adapter Spike

- 用户再次明确继续；RQ-049 只授权 5F-2 离线协议实验，不授权 5F-3、真实 Provider 或主 Runtime
  切换。起始 `HEAD == origin/main == 2244f06274572c6a66873fc74b56faa8003407fa`，工作树干净，
  治理预检通过。
- 比较直接迁移 Node、完整 Pi Coding Agent RPC 与低层 Agent Core JSONL sidecar 后，ADR-0035
  选择第三种；Python 保留 ToolRuntime/deadline，Node 每 run 一个 Agent，只使用 Scripted StreamFn。
- 新增 5F-2 实施计划，冻结 protocol/frame/Usage、供应链、sidecar、十类 scripted case 与同切片
  退出顺序；该入口批当时尚未安装 Pi、写 adapter、读取 Key 或调用 Provider/Riot。

## 2026-08-17：5F-2 Batch A 协议合同 TDD

- 新增 `tests/test_pi_runtime_protocol.py`，首次运行按预期因 `app.evaluation.pi_runtime` 不存在而
  collection 红灯；随后实现严格 Pydantic request/script/policy/result、安全 event/tool projection、
  RuntimeUsage 映射和 256 KiB canonical JSONL framing。
- 聚焦 13 项、与 RuntimeUsage/Recorder 相邻 50 项全部通过；compileall 和 diff check 通过。
- complete/partial/unknown/not_applicable 继续使用现有 RuntimeUsage 不变量；未知 Usage 不会变成
  complete zero，safe event extra fields 会被拒绝。
- 本批仍未创建 package.json/lockfile、安装 Pi、启动 Node、读取 Key 或调用 Provider/Riot；下一步
  进入 Batch B 供应链冻结。

## 2026-08-17：5F-2 Batch B 本地供应链冻结（进行中）

- 新增私有 `experiments/pi_runtime/package.json`、official-registry `.npmrc` 和 lockfile v3；直接
  依赖精确固定 `pi-agent-core`/`pi-ai` 0.84.2，`.gitignore` 排除 `node_modules/`。
- 本机 Node `v24.18.0` / npm `11.17.0` 先生成 lock，再用 `npm ci --ignore-scripts` 成功重建；
  Agent/AI integrity 与 5F-1 审计一致，`npm ls --all` 通过。
- 安装树为 94 packages、11,355 files、62,364,713 bytes，首次 ci 约 4844 ms；两个传递包声明
  install script 但均被 ignore-scripts 阻止。当前仍未启动 Pi sidecar 或调用 Provider。

## 2026-08-17：5F-2 Batch C sidecar 首轮修复（进行中）

- 已实现并启动隔离 Node sidecar；首次 11 个 sidecar 测试全部失败，最小诊断确认不是
  Permission Model，而是 controller 在严格对象模式下错误解析 JSON enum/nested payload。
- 已修复两个 JSON 反序列化接缝：事件和 `run.result` 均使用 Pydantic JSON mode，再交给 strict
  合同校验；并修正 `provider_aborted` 的 `stopped` 状态映射。
- 当前聚焦回归 `tests/test_pi_runtime_protocol.py tests/test_pi_runtime_sidecar.py` 为 `24 passed`。
  下一步仍在 Batch C/D：补充非法 JSON、错误 run_id、异常退出、stderr、超时和环境隔离测试，
  然后再运行相邻/完整回归与治理门禁；尚未进入 5F-3、真实 Provider 或主 Runtime。

## 2026-08-17：5F-2 Batch C/D 聚焦接线与安全边界完成

- 已补充非法 JSON、错误 run_id、崩溃、stderr、deadline、credential/HOME 环境隔离与 Tool contract
  drift 测试；controller 对 stderr reader 竞态、严格 JSON enum/nested payload 和 pre-spawn 配置错误
  均 fail closed。
- sidecar 已对齐当前 AgentLoop 的最后迭代零 Tool 副作用，并让失败 Tool 同样占用 max-tool-call
  预算；成功 Tool round-trip 和 max-iteration 两个同输入对照测试通过。
- 当前 Pi 聚焦为 `34 passed`，加 AgentLoop/ToolRuntime/RuntimeUsage/Recorder 相邻回归为
  `96 passed`（该数值来自加入最后 2 个测试前的一轮，相邻回归将在收尾重新运行）。
- 本地 `npm ci --ignore-scripts` 约 6063 ms，94 packages / 11,355 files / 62,364,713 bytes；
  六次 fresh sidecar process 为 399.75-453.15 ms，后五次中位数 413.71 ms。CI 已增加 Node 24
  setup 与隔离 npm ci；尚待完整本地门禁和 exact-SHA 公共验证。

## 2026-08-17：5F-2 本地退出审查完成，等待公共 CI

- 新增窄 parity 测试，真实比较当前 Python AgentLoop 与 Pi sidecar 的成功 Tool 顺序/终态及最后
  迭代零副作用；没有把 5F-3 的完整 Harness/Trace 对照提前计入。
- 最终 Pi 聚焦 `35 passed`、相邻 `99 passed`、完整
  `919 passed, 1 warning, 110 subtests passed`；两套 RAG、compileall、Node syntax/tree、Harness
  SDK/tracked-data boundary、dry-run、governance 和 diff check 均通过。
- 新增 5F-2 退出审查；本地结论为 `pass-with-boundaries`。当前唯一下一步是提交、推送并等待
  exact-SHA GitHub Actions；公共成功前不关闭 5F-2、不进入 5F-3。

## 2026-08-17：5F-2 exact-SHA 公共闭环与 5F-3 交接

- 提交 `f62f078faca0d93494478011d2fe18cdeb85970f` 已推送；Actions run `32022258177` 对精确 SHA
  的 Node 24 setup、`npm ci --ignore-scripts`、完整 pytest、两套 RAG、compileall、治理、
  Harness/secret boundary 与 dry-run 全部成功。
- 5F-2 正式关闭，四条进度线保持分离：本地协议实现/理解和公共证据提升，真实 Provider 领域
  质量、Pi adopt、完整 Trace/Harness parity 和部署没有提升。
- canonical 唯一下一检查点已交接为 `5F-3-contract-security-harness-evaluation` 准备状态，
  等待用户明确继续；未读取 Key、调用 Provider、修改主 Runtime 或自动开始 5F-3。
## 2026-08-17：用户恢复 5F-3，完成入口恢复与方案冻结

- 用户再次明确“继续”；按 RQ-050 只恢复 canonical 的
  `5F-3-contract-security-harness-evaluation`，不授权 5F-4 或真实外部调用。
- 恢复时 `HEAD == origin/main == 1454f59b0e07d96defedfc093807a8ef03391839`，工作树干净，
  `scripts/check_project_governance.py` 通过；5F-2 实现与状态收尾公共 CI 均为 success。
- 已修正 RQ-049 的陈旧“执行中”，清除 canonical 的等待确认 pause reason，并保留 5F-3 为唯一下一步。
- 源码审计确认现有 `SkillReviewExecutor`/`ReviewHarness` 可作为唯一发布接缝，同时发现 Context
  token-unit 与 sidecar char guard、扩展失败终态与现有 Runtime enum、聚合 Usage 与 per-call Trace
  三类差异。ADR-0036 选择评测专用 adapter 和严格 projector：兼容路径走真实 Harness，不能无损
  映射的路径显式 fail closed，不为实验成功而扩展生产合同。
- 已建立 `docs/plans/2026-08-17-5f3-contract-security-harness-evaluation.md`；当前进入 Batch A
  红灯测试。本批至此未读取 Key、调用 Provider/Riot、运行 held-out 或修改主 Runtime/FastAPI。
## 2026-08-17：5F-3 本地实现与退出审查

- 新增 evaluation-only `PiSkillDraftPreparer`：先复用现有 Compiler，再把 canonical system/user、
  Manifest budgets 和唯一 `knowledge.search` 映射到 sidecar；没有接主 Runtime/composition。
- controller 新增 process-local detailed Tool records；public result/event 继续不保存 query/chunks。
  adapter 从实际成功 Tool data 构造 Evidence，并重建 Assistant/Tool transcript。
- safe provider event 新增逐调用 token 和 finish reason；严格 projector 的成功信号已真实进入现有
  Recorder，形成 Usage 一致、Artifact body-free 的 RuntimeTrace。
- Pi draft 只有经过原 ReviewHarness 的 passing Evaluation 才由 `review_harness.publisher` 写 final；
  坏 citation、失败 Tool、process failure、missing Usage 均安全降级。Pi 直接 final producer 为 0。
- Context char/token 单位、extended terminal vocabulary 和 post-hoc event timing 三项 hard gap 未被
  近似映射或通过扩大生产合同修补；本地退出裁决为
  `harness-compatible-but-runtime-gate-failed`，不准入 5F-4 真实调用。
- 聚焦 Pi/Harness/Trace `45 passed`，相邻 `196 passed`，完整
  `929 passed, 1 warning, 110 subtests passed`；warning 为既有 FastAPI TestClient 迁移提示。
- 当前唯一下一动作是完成剩余本地门禁、提交、推送和 exact-SHA 公共 CI；成功前 5F-3 仍为
  in progress，不进入 5F-4/5F-5，不读取 Key 或调用 Provider/Riot。
- 最终本地门禁全部通过：development/independent RAG 均为满阈值；compileall、Node syntax、
  `npm ls --all`、Harness SDK boundary、tracked secret/run-data boundary、dry-run、governance 与
  `git diff --check` 成功；安全加固后的最终完整回归仍为
  `929 passed, 1 warning, 110 subtests passed`。当前只待提交、推送和 exact-SHA 公共 CI。

## 2026-08-17：5F-3 exact-SHA 公共闭环与 5F-5 交接

- 实现/退出提交 `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已推送；GitHub Actions run
  `32025522606` 对该精确 SHA 的 Node 24、`npm ci --ignore-scripts`、完整 pytest、两套 RAG、
  compileall、治理、安全边界和 Harness dry-run 全部成功。
- 5F-3 正式完成，裁决保持 `harness-compatible-but-runtime-gate-failed`；这不等于模型质量失败，
  而是候选 Runtime 的强制合同门失败。
- 5F-4 按入口设计的条件分支标为“未进入（前置门失败）”；真实 Provider/Riot/Key calls 保持 0，
  不使用真实模型调用掩盖 Context/terminal/live timing 差异。
- canonical 唯一下一检查点交接为 `5F-5-adoption-decision-exit-review` 准备状态，等待用户再次明确
  继续；本收尾不提前选择 partial-adopt/reject。

## 2026-08-17：开始 5F-5 Adoption Decision / Exit Review

- 用户再次明确“继续”；RQ-051 只恢复 5F-5 最终采用、实验资产生命周期和退出裁决，不补做 5F-4，
  不读取 Key，不调用 Provider/Riot，不接主 Runtime/FastAPI，也不自动实施阶段 6。
- 新增 5F-5 计划、ADR-0037、最终 adoption/exit matrix 与初学者总退出审查。
- 本地裁决为 `partial-adopt-evaluation-assets-only`：产品拒绝 Pi；冻结保留 exact package/sidecar、
  evaluation adapter、tests/lockfile/CI 复现和采用门方法。
- 已同步 canonical、路线修订、能力矩阵、项目决策和发现；当前尚待比例/完整测试、全部门禁、提交、
  推送和 exact-SHA 公共 CI。成功前 5F 仍未正式关闭，不交接 `6A-entry-design`。

## 2026-08-17：5F-5 本地门禁完成

- Pi protocol/sidecar/parity/Harness/Trace 聚焦 `45 passed`；完整回归
  `929 passed, 1 warning, 110 subtests passed`，唯一 warning 为既有 FastAPI TestClient 迁移提示。
- `npm ci --ignore-scripts` 从 exact lockfile 重建 94 packages，`npm ls --all` 与 Node syntax 通过；
  未读取 Key、未调用 Provider/Riot/held-out。
- development/independent RAG 门全部通过；Recall/MRR/nDCG/abstention/citation support 为 `1.0`，
  no-answer FPR 为 `0.0`。
- compileall、governance、Harness dry-run、SDK boundary、tracked secret/run-data boundary 和
  `git diff --check` 通过。
- 5F-5 仍 in progress，当前只待差异审查、提交、推送和 exact-SHA 公共 CI；成功前不关闭 5F。

## 2026-08-17：5F-5 exact-SHA 公共闭环与阶段 5 关闭

- 最终采用/退出提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已推送；GitHub Actions run
  `32028206103` completed/success，完整 pytest、两套 RAG、Node/npm、compileall、governance、
  安全边界和 Harness dry-run 全部通过。
- 5F-5 与阶段 5 正式完成；裁决保持 `partial-adopt-evaluation-assets-only`，产品拒绝 Pi，
  evaluation-only 资产冻结保留。
- canonical 只交接到 `6A-entry-design` 准备状态，等待用户再次明确继续；尚未设计或实现阶段 6。

## 2026-08-17：开始 6A-entry-design

- 用户再次明确“继续”；RQ-052 只授权完整 FastAPI/SQL 任务模型的入口设计，不直接实现阶段 6。
- 已按 canonical 恢复、治理预检和源码审计确认：5P 是同步、文件型、显式依赖注入的本地切片；
  SQL/task worker/production app/lifespan/鉴权/Session/Memory 均未实现。
- 已只读复核 EchoMind `api/main.py`、`conversation_memory.py`、compose 和依赖：可参考 lifespan 与
  user/conv 分层，但其全局组件、宽泛 CORS、Redis/Chroma 和非持久 background task 不直接迁移。
- 当前按 brainstorming 设计门等待一个 SQL 生产/测试目标确认；尚未创建 6A ADR/最终设计、安装依赖、
  修改产品代码、读取 Key 或调用 Riot/Provider。

## 2026-08-17：6A 数据库方案 A 已确认

- 用户明确选择 A：PostgreSQL 为唯一生产语义基线，采用 SQLAlchemy 2 + Alembic。
- 快速普通逻辑测试可使用 Fake；事务、迁移和并发任务领取必须由真实 PostgreSQL Docker/CI 验证，
  不使用 SQLite 绿灯替代 PostgreSQL 语义。
- canonical 仍停留在 `6A-entry-design`；下一单项设计门改为任务执行架构。尚未安装依赖、修改产品
  代码、启动数据库、读取 Key 或调用外部 Provider/Riot。

## 2026-08-17：6A 任务执行方案 3 已确认

- 用户确认独立 PostgreSQL polling worker；API 与 Worker 保持同仓库同部署，不引入额外消息队列。
- FastAPI 的职责收缩为请求校验、任务创建和查询；Worker 事务领取 queued task 后复用既有
  `RecentReviewApplicationService`，最终状态回写 SQL，大正文仍由 Artifact/Trace 持有。
- canonical 仍为 `6A-entry-design`，下一步是向用户逐节讲解并确认“架构与数据流”；task schema、
  状态机、事务细节和失败恢复尚未冻结。产品代码、依赖安装、数据库启动和外部 I/O 仍为 0。

## 2026-08-17：6A 架构与数据流章节已确认

- 用户确认模块化单体、API/Worker 分工、短事务以及 SQL 控制面/Artifact 数据面分离。
- 现有 `RecentReviewApplicationService` 保持业务用例所有者；FastAPI 不接管 Agent 业务，Worker 只
  负责持久任务生命周期和调用 Application Service。
- canonical 下一设计节为 task schema 与状态机。仍未创建 ADR/最终设计、安装依赖、修改产品代码、
  启动数据库或执行外部 I/O。

## 2026-08-17：6A task schema 与状态机章节已确认

- 用户确认 `task_id`/`run_id` 双身份、服务器预留 run、`queued → running → succeeded|failed` 四态
  不可逆状态机，以及 owner/idempotency/terminal projection 等控制字段边界。
- 这一步解决“重复提交”和“Artifact 无 SQL 归属”的设计问题，但没有实现自动恢复或公网鉴权。
- canonical 下一设计节为 SQL/Artifact 分工、事务、幂等、ownership 与 crash reconciliation；代码、
  依赖、数据库启动和外部 I/O 仍为 0。

## 2026-08-17：6A SQL/Artifact 核心确认，hard-crash 边界重开

- 用户确认 SQL 控制面/Artifact 数据面、三段短事务、幂等指纹、Worker ownership 与成功交叉校验。
- 在进入失败章节时发现多 Worker 存活判定缺口；自动把无 receipt 的 running task 标记 failed 暂停，
  先比较三个可验证方案，避免把阶段 8 lease 能力偷渡成已经解决。
- canonical 仍为 `6A-entry-design`；代码、依赖、数据库和外部 I/O 保持 0。

## 2026-08-17：6A hard-crash 方案 A 已确认

- 用户确认“有确定终态证据才自动协调；无证据需人工确认且不自动重跑”。
- 6A 不提前实现 lease/heartbeat/fencing；这一限制会进入 ADR、测试和运维说明。
- canonical 下一节为完整失败分类与 HTTP 投影；产品代码、依赖、数据库和外部 I/O 仍为 0。

## 2026-08-17：6A 失败语义与 HTTP 投影章节已确认

- 用户确认 POST 202/GET task 语义、分层安全错误，以及 task succeeded 与 publication status 分离。
- 现有同步 POST 将在后续实施中演进为异步 receipt 合同，但当前尚未修改 API 代码或 Schema。
- canonical 下一节为作品集规模 NFR；产品代码、依赖、数据库和外部 I/O 仍为 0。

## 2026-08-17：6A 作品集规模 NFR 已确认

- 用户确认单服务器起步、默认 Worker 单并发、可增加 Worker、owner/global 背压、API/claim p95 目标、
  退避轮询、liveness/readiness 分离和诚实可用性边界。
- 这些均为待实现/待测的验收目标，不是已测性能或 SLA。
- canonical 下一节为安全与数据生命周期；产品代码、依赖、数据库和外部 I/O 仍为 0。

## 2026-08-17：6A 安全与数据生命周期章节已确认

- 用户确认可信 ActorContext、owner-scoped 资源访问、默认关闭 CORS/公网能力、Secret/日志脱敏和
  7/90/30 天保留策略；terminal 删除与 active cancel 保持分离。
- 安全技能复核使 production fail-closed、越权 404 和公开部署硬门进入正式设计边界。
- canonical 下一节为测试矩阵；产品代码、依赖、数据库和外部 I/O 仍为 0。

## 2026-08-17：6A 分层测试矩阵已确认

- 用户确认 Fake/纯逻辑、真实 PostgreSQL、API、Worker、离线产品纵向、安全/生命周期和性能分层；
  PostgreSQL CI 为阻塞门，SQLite 不替代。
- 这只是验收设计，当前没有新增测试、启动数据库或调用外部服务。
- canonical 下一节为 6A 原子实施顺序；确认后才创建正式 ADR/设计/实施计划。

## 2026-08-17：6A 全部设计章节已确认并落盘

- 用户确认 6A-1 至 6A-7；已新增 ADR-0038、完整 design 与 implementation plan。
- 计划保持一次一个 canonical 子阶段、先教学/TDD、每批 exact-SHA CI；不使用 subagent 或额外
  worktree。
- 当前尚未实现 6A 产品代码，也未安装 SQL 依赖或启动数据库；下一步只执行文档一致性/回归门、
  提交、推送和公共 CI。

## 2026-08-17：6A entry-design 本地门禁通过

- ADR-0038、design、implementation plan 与 canonical 完成一致性检查；governance/diff check 通过。
- 首次 `python -m pytest -q` 指向桌面代理 Python 且未安装 pytest，因此未进入测试；改用仓库
  `.venv\\Scripts\\python.exe` 后完整回归为 `929 passed, 1 warning, 110 subtests passed`。这是命令
  解释器修正，不是产品红灯。
- development/independent RAG 两套门均为 Recall/MRR/nDCG 1.0，holdout abstention/citation 1.0；
  compileall、Harness dry-run、tracked Secret/run-data 和 Harness SDK boundary 通过。
- 本批未安装 SQL 依赖、启动 PostgreSQL、读取 Key 或调用 Riot/Provider；下一步只提交、推送并等待
  exact-SHA 公共 CI。

## 2026-08-17：6A-entry-design exact-SHA 公共闭环

- 设计提交 `c0b5af0eec1654c35afddb3c8a66b774a233a688` 已推送，GitHub Actions run
  `32041343696` 对该精确 SHA completed/success。
- ADR-0038、完整 design/implementation plan、治理、完整 pytest、两套 RAG、compileall、安全边界和
  Harness dry-run 均获得公共验证；CI 未读取 Key、调用 Riot/Provider 或启动本轮未实现的产品 DB。
- `6A-entry-design` 正式关闭；canonical 只交接 `6A-1-postgresql-foundation` 准备状态，等待用户再次
  明确继续。尚未安装 SQL 依赖、创建 migration、启动 PostgreSQL 或实现阶段 6 产品代码。

## 2026-08-17：开始 6A-1 PostgreSQL Foundation

- 用户明确“开始”；RQ-053 只授权 SQLAlchemy 2/Alembic/psycopg 配置、task ORM row、initial
  migration、Compose PostgreSQL 与真实 PostgreSQL CI 门。
- 已按 `AGENTS.md` 恢复 canonical/active plan/需求/路线/ADR/设计/实施计划；治理检查通过，HEAD 与
  `origin/main` 均为 `493d183a1067e469a4f2e18225e8eaf352697e22`，工作树起始干净。
- 已完成初学者入口教学；本机无 Docker，故本地真库测试将明确 skip，真实 migration 阻塞证据必须由
  GitHub Actions PostgreSQL service 提供，不用 SQLite 或 Fake 冒充。
- 当前下一步为 TDD 红灯配置/迁移合同；尚未安装 SQL 依赖、创建 migration 或实现 Repository/Worker/API。

## 2026-08-17：6A-1 本地实现与门禁通过

- 红灯先后为 `sqlalchemy` dependency 缺失与 `app.persistence` 模块缺失；随后只增加 SQLAlchemy 2、
  Alembic、psycopg 3，并实现 fail-closed settings、lazy Engine/Session、metadata/ORM row 与 0001 migration。
- 新增 PostgreSQL 17 Compose service 和独立 `postgres-migrations` Actions job；原 `pytest` job 保留。
- Alembic offline PostgreSQL SQL 编译通过；期间发现并修复 CHECK constraint 双前缀命名，head/history 为
  单一 `0001_review_tasks`。
- 聚焦 `19 passed, 3 skipped`；三个 skip 只因本机无真实 PostgreSQL。完整回归
  `948 passed, 3 skipped, 1 warning, 110 subtests passed`。
- development/independent 两套 RAG 门均满阈值；compileall、Harness dry-run、governance、tracked
  Secret/run-data、Harness SDK boundary 和 diff check 通过；未读取 Key 或调用 Riot/Provider。
- 本地实现完成但 6A-1 仍为 in progress；下一步仅提交/推送并用 exact-SHA public CI 执行真库 upgrade/
  downgrade/upgrade、JSONB/timestamptz/CHECK round-trip 和 Alembic metadata check。

## 2026-08-17：6A-1 exact-SHA 公共闭环

- 实现提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 已推送；Actions run `32043214500`
  对同一 SHA completed/success。
- `pytest` job 与 `postgres-migrations` job 均成功；后者在 PostgreSQL 17 上执行可逆 migration、
  JSONB/timestamptz/status CHECK round-trip 与 metadata drift check，外部 Riot/Provider I/O 为 0。
- 6A-1 正式关闭；canonical 只交接 `6A-2-task-contract-repository` 准备状态，等待用户再次明确继续。
  尚未实现 Repository/create/query、claim、Worker、异步 API、Session/Memory 或前端。

## 2026-08-18：开始 6A-2 Task Contract & Repository

- 用户再次明确“继续”；RQ-054 只授权 task models/ports/fingerprint/service、owner-scoped idempotent
  create/query、容量与真实 PostgreSQL Repository，不授权 claim/Worker/API。
- 已按 `AGENTS.md` 恢复 canonical/active plan/RQ/路线/ADR/设计/实施计划；治理通过，HEAD 与
  `origin/main` 均为 `ca486a10e3837c509fbee66e9a4b4118f83a6cab`，工作树起始干净。
- 已完成初学者入口教学和 brainstorming 设计复核；既定 Service/Repository 分层无未决用户选择。
- 当前下一步为完成最终本地门审查、提交/推送并用 public PostgreSQL CI 验证 5 项 Repository 测试；本机
  不连接数据库。

## 2026-08-18：6A-2 domain/service/Repository 本地实现

- 红灯先确认 `app.tasks` 与 `app.persistence.task_repository` 尚不存在；随后实现严格 TaskStatus、
  ReviewTask/ReviewTaskView、capacity policy、canonical SHA-256 fingerprint、TaskRepository port 和
  ReviewTaskService。
- Fake service 聚焦回归为 `29 passed`，覆盖 created/replayed/conflict、owner/global capacity、terminal
  不占容量、body-free projection、owner-scoped not-found、safe error 与 identity immutability。
- PostgreSQL Repository 已实现短事务 advisory-lock create/replay/conflict/capacity、JSONB round-trip、
  owner-scoped task/run query 和 rollback-safe error mapping；新增 5 项真实真库测试，本机因无 DB 明确 skip。
- 6A-1 migration 测试职责已修正，`upgrade → downgrade → upgrade` 在同一测试函数内断言。
- 当前尚未运行本轮完整回归、RAG/安全/治理最终门，也未提交/推送 6A-2；下一步运行全部本地门禁。

## 2026-08-18：6A-2 本地门禁完成

- 聚焦 task models/service 为 `29 passed`；完整回归为 `977 passed, 8 skipped, 1 warning, 110 subtests
  passed`。8 个 skip 为本机无 PostgreSQL 的 3 个 migration + 5 个 Repository 测试。
- 两套 RAG 门均达到 Recall/MRR/nDCG `1.0`，holdout abstention/citation `1.0`；compileall、Harness
  dry-run、governance、tracked Secret/run-data、SDK boundary、Compose/workflow YAML 和 diff check 通过。
- 未读取 Key、未调用 Riot/Provider、未启动本地数据库；真库 Repository 的 replay/conflict/capacity/
  rollback/owner/concurrent same-key 证据只由下一次 public PostgreSQL job提供。
- 当前本地实现和门禁完成，下一步提交/推送并等待 exact-SHA CI；成功前不关闭 6A-2、不进入 6A-3。

## 2026-08-18：6A-2 exact-SHA 公共闭环

- 实现提交 `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 已推送；Actions run `32046532695` 对同一 SHA
  completed/success。
- `pytest` 与 `postgres-migrations` 均成功；真实 PostgreSQL 通过 5 项 Repository 测试，外部
  Riot/Provider/Key I/O 为 0。
- 6A-2 正式关闭；canonical 只交接 `6A-3-atomic-claim-polling-worker` 准备状态，等待用户再次明确继续。
  尚未实现 claim、Worker、Application/Artifact、异步 API、Session/Memory 或前端。

## 2026-08-18：开始 6A-3 Atomic Claim & Polling Worker

- 用户再次明确“继续下一轮”；RQ-055 只授权 PostgreSQL 原子 claim、worker ownership/terminal CAS、
  polling backoff/jitter、graceful shutdown 与 Fake Executor 控制流。
- 已按 `AGENTS.md` 恢复 canonical/active plan/RQ/路线/ADR/设计/实施计划；治理通过，HEAD 与
  `origin/main` 均为 `69731871fa54c904d5c291a3d60d050ea703b023`，工作树起始干净。
- 已完成初学者入口教学，明确短 claim transaction、事务外执行、CAS 与 hard-crash deferred 边界。
- 当前下一步为审计 task port/repository/schema 并先写 Fake polling/Worker 与真库 claim/CAS 红灯；
  尚未接真实 Application/Artifact、修改 FastAPI、读取 Key 或调用 Riot/Provider。

## 2026-08-18：6A-3 本地实现与门禁完成

- 红灯先固定 `PollingPolicy`、Fake Worker 控制流、终态 CAS 和 PostgreSQL `SKIP LOCKED` 并发合同；
  随后实现 `TaskTerminal`、Repository claim/succeed/fail、`PollingPolicy`、`ReviewWorker` 与
  fail-closed Worker CLI。已公开 migration 未修改。
- 聚焦回归为 `30 passed, 7 skipped`；完整回归为 `1008 passed, 15 skipped, 1 warning, 110 subtests
  passed`。skip 仅来自本机无 PostgreSQL；新增真库测试覆盖锁住首行时跳过、单任务不双领、N 任务双 Worker
  drain、确定性顺序、短事务释放、错误 owner CAS 和终态不可逆。
- 两套 RAG 均达到冻结阈值；compileall、Harness dry-run、governance、秘密/运行数据边界、SDK 边界、
  YAML 与 diff check 通过；未读取 Key、未调用 Riot/Provider、未启动本地 DB。
- 当前本地裁决为“实现完成、等待 exact-SHA 公共 PostgreSQL CI”；下一步只提交/推送并等待阻塞真库
  job，成功后才关闭 6A-3 并交接 6A-4，不提前接 Application/Artifact 或 API。

## 2026-08-18：6A-3 exact-SHA 公共闭环与 6A-4 交接

- 提交 `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 已推送；GitHub Actions run `32097561436` 的
  `pytest` 与 `postgres-migrations` 两个 job 均 completed/success。
- 真实 PostgreSQL 17 job 补齐 7 项本地 skip：deterministic order、锁住首行时 SKIP LOCKED 跳过、
  单任务并发不双领、N 任务双 Worker drain、claim 短事务释放、错误 owner/迟到终态 CAS、失败终态
  不可逆与 Worker 时钟领先时的 timestamp invariant。
- 6A-3 正式关闭，RQ-055 标为已执行；四条进度线已同步。canonical 唯一下一检查点交接为
  `6A-4-application-artifact-integration` 准备状态，等待用户明确继续；本轮未实现真实
  Application/Artifact、reconciliation、异步 API、Session/Memory、SSE、鉴权或前端。

## 2026-08-18：开始 6A-4 Application & Artifact Integration

- 用户再次明确“继续”；RQ-056 只授权 SQL 预留 `run_id` 贯穿 Application/Runtime/receipt、真实
  Recent Review Task Executor、receipt-proven terminal coordination、保守 reconciliation 与受限人工
  recovery CAS。
- 已按 `AGENTS.md` 恢复 canonical、活动计划、需求/路线/能力矩阵、ADR-0038 与 6A design/implementation
  plan；治理通过，工作树起始干净，HEAD 与 `origin/main` 均为
  `79c5f396a71b02c33de326187971b2f721a8bc65`。
- 已完成初学者入口教学，明确 SQL/文件无法共享事务、crash window、跨存储 `run_id`、receipt-proven
  reconciliation 以及无 lease 时禁止自动判死/重跑的原因。
- 当前下一步为审计相邻合同并先写 run_id/Executor/reconciliation/manual recovery 红灯；尚未修改
  FastAPI、读取 Key、调用 Riot/Provider，且不会进入 6A-5。

## 2026-08-18：6A-4 本地实现与门禁完成

- `RecentReviewRuntimeRequestCompiler.compile()` 与 `RecentReviewApplicationService.review()` 已增加
  keyword-only trusted `run_id`；SQL 预留值会贯穿 input binding、Runtime result、Trace 与 immutable
  receipt，且不会再调用随机 run factory。Application 会核对 receipt writer 返回的完整终态身份。
- `TaskTerminal` 现在要求同一 run 的 Trace/receipt 引用，published/degraded 还必须带 final Artifact；
  Repository success CAS 同时匹配 task/status/worker/run 并持久化 body-free references/SHA。先验证
  completed ApplicationResult、再写 completed receipt，消除了非法 completed receipt 被对账成成功的窗口。
- 新 `RecentReviewTaskExecutor` 会复核 task payload fingerprint，调用现有 Application/Runtime/Harness，
  再由 `RecentReviewTerminalEvidenceVerifier` 复读 receipt、Trace、manifest、final Artifact 与精确 receipt
  bytes SHA；published/degraded/rejected 都形成 task succeeded，Application/证据失败交回 Worker failed。
- `ReviewTaskReconciler` 只用完整 immutable receipt 补齐 succeeded；missing/invalid/non-completed receipt
  只返回 `recovery_required`，绝不 fail/requeue/replay。`ManualReviewTaskRecovery` 与恢复 CLI 必须二次匹配
  worker ID，再用 running+worker CAS 写 `worker_confirmed_dead`；旧 Worker 的迟到 success 被终态 CAS 拒绝。
- 聚焦相关回归 `130 passed, 12 skipped`；完整回归
  `1033 passed, 20 skipped, 1 warning, 110 subtests passed`。20 个本地 skip 为既有 15 个 PostgreSQL 项
  加本轮 5 个 reconciliation/真实离线产品纵向真库项；本机无数据库，必须由 GitHub Actions 补齐。
- 两套 RAG 均达到冻结阈值；compileall、Harness dry-run、governance、tracked Secret/run-data、SDK boundary、
  YAML 与 diff check 全部通过。本轮真实 Riot/Provider/Key I/O 为 0；Fake Provider 纵向只证明接线。
- 当前下一步只提交、推送并等待 exact-SHA `pytest` 与 `postgres-migrations`；公开真库成功前 6A-4
  保持 in progress，不进入 6A-5。

## 2026-08-18：6A-4 exact-SHA 公共闭环与 6A-5 交接

- 提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 已推送；Actions run `32102522662` 的 `pytest` 与
  `postgres-migrations` 两个 job 均 completed/success。公开完整 pytest 为
  `1033 passed, 20 skipped, 1 warning, 110 subtests passed`。
- PostgreSQL 17 job 执行 6 个数据库测试文件并得到 `40 passed`，其中本轮新增的 5 项 reconciliation/
  产品纵向测试真实执行；migration upgrade/downgrade/upgrade 与 metadata check 也通过。
- 6A-4 正式关闭：SQL 预留 run_id、真实 Task Executor、receipt/Trace/final Artifact 证据、保守
  reconciliation、recovery-required 与人工 recovery CAS 已获得真实 PostgreSQL 公共证据。CI 无
  `.env`/Key、Riot/Provider I/O；Fake Provider 纵向仍不代表模型质量。
- 四条进度线已同步：本地代码与公开证据均到 6A-4；项目理解已覆盖 SQL/Artifact crash window 与
  保守恢复；参考项目没有被整体接入；GitHub/部署有新的 exact-SHA CI 证据但异步 API/网页未部署。
- canonical 唯一下一检查点改为 `6A-5-async-fastapi-composition` 准备状态；等待用户明确继续，
  本轮不自动实现异步 FastAPI、ActorContext、lifespan、Session/Memory、SSE、Auth 或前端。

## 2026-08-18：开始 6A-5 Async FastAPI & Composition

- 用户再次明确“继续吧”；RQ-057 只授权 POST 202 task receipt、owner-scoped task/run/report、可信
  ActorContext、FastAPI lifespan、PostgreSQL/Alembic readiness 与 production-like API composition。
- 已按 `AGENTS.md` 恢复 canonical、活动计划、需求/路线、ADR-0038、6A design/implementation plan 和
  相邻 API/Task/Repository/RunQuery 代码；治理检查通过，工作树起始干净。
- 已完成初学者入口教学：这里的异步是“HTTP 持久入队后立即返回，独立 Worker 后续执行”的产品语义，
  不是把同步 SQLAlchemy 机械改成 async ORM。owner 只能来自服务器 ActorContext。
- 当前下一步为先写 HTTP、ActorContext、readiness 与 lifespan 红灯；本批不实现 Session/Memory、SSE、
  JWT/OAuth、前端、lease/retry/reclaim、真实 Riot/Provider I/O 或 6A-6。

## 2026-08-18：6A-5 本地实现与门禁完成

- FastAPI V2 已把同步 201 报告响应演进为 POST 202 task receipt；同 key replay 仍返回原 task/run，缺失或
  非法 key 为 422，不同 fingerprint 为 409，数据库/容量/身份不可用安全投影为 503。POST 不执行 Agent。
- 新 ActorContext 只由服务器 dependency 提供；固定 owner 仅允许显式 local/test profile，production
  未注入 Auth Provider 时 liveness 可用、readiness 为 `actor_context_unavailable`、产品请求 fail closed。
- GET task/run/report 先 owner-scoped 查询 SQL task；非法/不存在/越权统一隐藏，queued/running 返回 409，
  succeeded 才读取严格 receipt/Trace/Artifact，SQL 承诺成功但文件证据缺失会升级为 integrity 500。
- composition import/OpenAPI 零环境/Key/网络/DB I/O；FastAPI lifespan 才惰性创建进程级 Engine、Session
  factory、Repository/Task Service/RunQuery，并在 shutdown dispose。liveness 不依赖 DB；readiness 执行
  `SELECT 1` 并要求数据库 Alembic revision 精确等于代码 head。
- 聚焦 API 回归 `38 passed, 1 skipped`；完整回归
  `1047 passed, 21 skipped, 1 warning, 110 subtests passed`。新增 1 个 skip 为本机无 PostgreSQL 的 API
  create/replay/owner/query/readiness 真库测试，已加入 `postgres-migrations` 阻塞 job。
- 两套 RAG 门均满阈值；compileall、Harness dry-run、governance、tracked Secret/run-data、SDK boundary、
  workflow YAML 与 diff check 均通过。本轮未读取 Key、未调用 Riot/Provider，也未启动本地 PostgreSQL。
- 范围复核裁决：6A-5 正式清单只覆盖 API composition；真实 Riot/Data Dragon/Provider Worker 可执行组合
  必须在 6A-7 的 API+Worker+PostgreSQL packaging 中闭环。当前 Worker CLI 继续 fail-closed，不能把 API
  可入队误报为已经具备可部署的自动消费进程。
- 当前下一步只提交、推送并等待 exact-SHA `pytest` 与真实 PostgreSQL API CI；成功前 RQ-057/6A-5
  保持执行中，不进入 6A-6。

## 2026-08-18：6A-5 exact-SHA 公共闭环与 6A-6 交接

- 提交 `2492951c20dd6ca897d957d03752b6a2585ce469` 已推送；Actions run `32106378542` 的
  `pytest` 与 `postgres-migrations` 两个 job 均 completed/success。
- 公共 pytest 为 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17 job
  为 `41 passed, 1 warning`，新增 API 真库测试已明确列入命令并实际执行。
- 两套 RAG、compileall、Harness dry-run、governance、Secret/run-data、SDK boundary 与 migration head
  均通过；CI 未读取 Key、未调用 Riot/Provider。
- 6A-5/RQ-057 正式关闭；四条进度线已同步。canonical 只交接
  `6A-6-security-lifecycle-nfr` 准备状态，等待用户明确继续，不自动开始 6A-6。

## 2026-08-18：6A-6 授权与状态同步

- 用户明确“继续下一步”，按 `AGENTS.md` 解释为只授权 canonical 的
  `6A-6-security-lifecycle-nfr`，不授权 6A-7 或跨阶段功能；新增 RQ-058。
- 已在 requirements/state/roadmap/amendment/capability/project decisions 与本计划同步：状态由
  “等待确认”改为“实施中”，唯一下一步保持 6A-6，历史交接记录保留且不改写。
- 本轮尚未修改产品代码、读取 Key、启动 PostgreSQL 或调用外部 Provider；下一动作是先面向初学者
  解释并写 CORS、日志脱敏、retention/delete、backpressure、observability 与 performance 的红灯测试。

## 2026-08-18：6A-6 本地实现与横向门禁完成

- 先用红灯确认四个新模块不存在；随后实现 `RetentionPolicy/Service`（注入时钟、7/90/30 天边界）、
  `TaskObservability`（allowlisted body-free events/counters/percentile）、`FileRunDataCleaner` 与
  `TaskDeletionService`（SQL hidden-before-cleanup、幂等、补偿 marker、active conflict）。
- PostgreSQL Repository 新增 owner-scoped terminal delete 与 bounded expired-terminal purge；API 增加
  默认关闭/显式 CORS、production wildcard+credentials fail-closed、capacity env 配置和 DELETE 投影；
  Worker 增加安全 claim/terminal latency/status 观察，不记录 request body 或异常正文。
- 新增 `scripts/purge_expired_task_data.py` 与五个测试文件；PostgreSQL lifecycle/capacity/performance
  测试已加入阻塞 workflow，本机无 PostgreSQL 时明确 skip。
- 聚焦 6A-6 回归为 `30 passed, 6 skipped`；完整回归为
  `1077 passed, 27 skipped, 1 warning, 110 subtests passed`。RAG development/holdout 均满阈值，
  compileall、Harness dry-run、Secret/run-data、SDK boundary、workflow YAML、diff 和 governance 通过；
  本轮 Key/Riot/Provider I/O 为 0。
- 当前只剩 exact-SHA 提交/推送与真实 PostgreSQL CI；公共成功前不关闭 6A-6。

## 2026-08-18：首个 6A-6 公共 run 与性能证据修补

- 实现提交 `fecbb11` 已推送；Actions run `32137687527` 的 `pytest` 与 `postgres-migrations` 均成功。
  公共完整测试为 `1077 passed, 27 skipped, 1 warning, 110 subtests passed`，PostgreSQL job 为
  `51 passed, 1 warning`，包含 lifecycle/capacity/performance 文件。
- 收尾审查没有直接关闭 6A-6：成功日志未打印实际 p95、样本数/环境，且原 claim 样本更接近 SQL
  调用耗时。已把 create/query 增加 warm-up，把 claim 改为入队后累计等待，并让 PostgreSQL job 以
  `-s` 输出安全的 environment/metric/samples/p95/target。
- 该修补只增强证据，不改变产品路径；下一动作是聚焦/治理检查、提交推送并等待新的 exact-SHA CI。

## 2026-08-18：6A-6 exact-SHA 公共闭环

- evidence-only 提交 `31d5e6038943bd3eacbeb485300f63ad53e13bfd` 已推送；Actions run
  `32138025724` 的 `pytest` 与 `postgres-migrations` 均 completed/success。
- 公共完整 pytest `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
  `51 passed, 1 warning`，明确执行本轮 lifecycle/capacity/performance 测试。
- 性能日志：`github-actions-postgresql-17-python-3.11`，create/query 8 样本 p95 `6.220ms`
  （target 300ms），queued→claim 8 样本 p95 `23.359ms`（target 2000ms）。
- 6A-6/RQ-058 正式关闭；四条进度线同步。下一检查点只交接
  `6A-7-packaging-exit-review` 准备状态，等待用户明确继续，不自动实施。

## 2026-08-18：开始 6A-7 Packaging & Exit Review

- 用户明确“继续吧”；RQ-059 只授权可重建 API+Worker+PostgreSQL packaging、真实 Worker executable
  composition、Linux no-I/O smoke 与逐项 6A exit matrix/review。
- 已按 `AGENTS.md` 恢复 canonical、活动计划、需求/路线/能力矩阵、ADR-0038、6A design/implementation
  plan；session catchup 无未同步输出，治理检查通过，工作树起始干净，HEAD/origin 均为
  `155d5c2f296c1697bf1af66b92ca54198160fbf2`。
- 已完成初学者入口教学，区分 packaging 与业务逻辑、API/Worker/PostgreSQL 三进程职责、claim 前
  fail-closed、Linux smoke 证据边界和 exit matrix 的逐项审查职责。
- 第一次大范围持久状态补丁因能力矩阵末尾换行上下文不匹配被 `apply_patch` 原子拒绝，无部分修改；
  随后拆成小补丁完成同步。下一步重跑治理并审计现有 composition/package 缺口，再写红灯合同。

## 2026-08-18：6A-7 packaging 缺口审计完成

- 确认缺少 Dockerfile/.dockerignore/Uvicorn、Compose migration/API/Worker 与真实 Worker composition；
  当前 Worker CLI 仍固定安全退出，API 已有可供 ASGI `--factory` 启动的 composition。
- 确认生产 Worker 可直接复用现有 Riot/Data Dragon/RAG/Prompt Program/Provider/Runtime/Application/
  receipt/evidence/Repository 接缝，无需增加框架或复制 Harness。
- 选择生产 Worker 与 no-I/O Linux smoke 分离：生产路径完整校验后才 claim；smoke 以显式诊断模式验证
  POST/claim/safe failed terminal/query，不构造 Riot/Provider，不冒充 Coach 质量。
- 本机 `docker` 命令仍不存在；本地不能提供镜像/Compose 运行证据，必须由 exact-SHA Linux CI 补齐。
  下一步写 packaging/worker/smoke 红灯合同并确认它们因缺实现失败。

## 2026-08-18：6A-7 packaging 红灯确认

- 新增 `tests/test_packaging_contract.py`、`tests/test_worker_composition.py` 与
  `tests/test_packaging_smoke.py`，冻结镜像/忽略边界、Compose 依赖、Uvicorn、Linux CI、exit assets、
  Worker settings/readiness/Secret 和显式 no-I/O smoke gate。
- 聚焦红灯在 collection 阶段以两个预期缺口失败：`app.workers.composition` 与
  `scripts.run_packaging_smoke` 不存在；退出码 1。Dockerfile/.dockerignore/Compose/CI/docs 仍未实现。
- 下一步先实现 production Worker composition/CLI 和 no-I/O smoke，再实现 Docker/Compose/CI；不会为
  追绿放宽 claim-before-readiness、Secret 或 production smoke 禁止边界。

## 2026-08-18：6A-7 composition/package 本地实现与相邻验证

- 新增 production `app/workers/composition.py`：完整设置/Secret 隐藏、PostgreSQL/Alembic readiness、
  Riot/Data Dragon/RAG/Prompt Program/Provider/Runtime/Application/receipt/evidence/Worker 一次装配；失败销毁
  Engine 并只返回 allowlisted code。Worker CLI 新增 `--check`/`--once`，不再固定拒绝。
- `RiotClient` 在 API Key/region 都显式注入时不再隐式读取 `.env`；旧脚本未显式传参时仍兼容 dotenv。
- 新增 gated local/test `run_packaging_smoke.py`，真实 HTTP create/query + PostgreSQL claim + 安全 failed
  terminal，设置合同没有 Riot/LLM Secret 字段，输出明确为 `external_riot_provider_calls=0`。
- 新增非 root Dockerfile、严格 .dockerignore、migration/API/real-worker/smoke Compose、Uvicorn 依赖、
  blocking `packaging-smoke` Actions job，以及 README/SECURITY/exit matrix/review。
- packaging/Worker/API 聚焦 `43 passed, 1 warning`；相邻 task/API/runtime/provider 回归
  `235 passed, 1 skipped, 1 warning`；compileall、Compose/workflow YAML 解析与 diff check 通过。
- editable install 取得 Uvicorn 0.52.3；真实本地 ASGI factory 启动后 `/health/live` 为 200，缺 DB 配置的
  `/health/ready` 为安全 503 `service_configuration_invalid`。PTY 中受到环境内无关 localhost upgrade 探测，
  Uvicorn 因未安装 WebSocket extra 输出 warning/WinError 10054；项目无 WebSocket/SSE，本次目标端点正常，
  Ctrl-C 后进程完整 shutdown。该噪声不是 Docker/Linux 或产品 WebSocket 证据。

## 2026-08-18：6A-7 人工审查修补与最终本地门

- 人工审查没有直接沿用首版 Compose 命令：根据 Docker 官方合同，`--exit-code-from` 隐含
  `--abort-on-container-exit`，可能与预期退出的 migration 冲突；同时默认 project/volume 会让诊断 Worker
  有机会接触普通本地 queued task。已改为隔离 project，并分成 API stack `up --wait` 与 one-off smoke。
- 新增无效 worker_id 的 pre-I/O 配置测试与实现；移除 `app/workers/__init__.py` 尾部无效字符串。修补后
  packaging/Worker/API 聚焦为 `48 passed, 1 warning`。
- smoke 设置又增加远端 API/PostgreSQL host 拒绝合同，阻止伪装 test profile 后误用诊断器；完整回归为
  `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；两套 RAG 均为
  Recall/MRR/nDCG 1.0，holdout abstention/citation 1.0；Harness dry-run `published`、0 revisions；
  compileall 通过。27 个 skip 仍因本机无 PostgreSQL，不能替代公共真库证据。
- 既定 Harness SDK boundary 与 tracked `.env`/`data/cache`/`data/runs` 门通过。额外的泛化 token-shape
  扫描因文件名子串和安全负例 fake token 误报，已分类而未删除测试。
- 最终 packaging contract、compileall、Compose/workflow YAML、pip check、Harness SDK、tracked data、
  `git diff --check` 与 governance 快照均通过。当前退出裁决保持
  `keep-open-pending-exact-sha-linux-ci`；下一动作只做提交推送并等待 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke` 三个 job。
- 首次独立 cached diff check 在 commit 前发现 Dockerfile EOF 多余空行；已用最小补丁删除并重新暂存。
  这是格式门命中，不是 image 合同或测试失败；必须在新的 cached diff check 成功后才允许 commit。

## 2026-08-18：6A-7 首个 exact-SHA run 与诊断修补

- 实现提交 `b0f61ca` 已推送；Actions `32145005904` 中 pytest（公开 `1100 passed, 27 skipped,
  110 subtests passed`）和 PostgreSQL（`51 passed`）成功；packaging 的 Compose config、image build、
  migration 与 API ready 也成功。
- one-off smoke 唯一失败输出为过宽 `packaging_smoke_worker_failed`；image boundary 随后正确跳过，teardown
  成功。没有把另外两个绿 job 或前半段 build 误报为 package 全绿。
- 已先写两个红灯：DB preflight 与 claim failure 都被旧实现压成 worker_failed；随后增加 allowlisted
  database/claim/claim-invalid/terminal-update/iteration/query 分层码，并给 workflow 增加失败时 bounded
  `ps` 与 API/PostgreSQL tail logs。红灯 2 failed/6 passed，绿灯 14 passed；完整 1102/27 skipped。
- 当前未修改 Agent、Repository、API 业务语义，也未调用 Riot/Provider。下一动作是完成本修补横向门、
  提交推送并用新 exact-SHA Linux smoke 取得真实失败层或全绿结果。

## 2026-08-18：6A-7 第二个 run 根因与 module-entry 修复

- `d8c5063` / Actions `32146113582` 的 pytest 与 PostgreSQL 再次成功；Linux one-off 精确返回
  `packaging_smoke_database_not_ready`。bounded API logs 同时证明 readiness 200、POST 202，PostgreSQL
  healthy，因而没有把根因误判为数据库宕机。
- 源码/镜像路径审查确认 direct script 让 Python 从 wheel 导入 `app.api.composition`，其相对
  `PROJECT_ROOT` 找不到 `/opt/riftcoach/alembic.ini`；API 模块入口从工作目录源码导入则正常。真实 Worker
  的 direct script command 有相同隐患。
- 先改 packaging contract 期待 `python -m scripts.run_review_worker` / `run_packaging_smoke`，取得 1 个
  预期红灯；再只改 Compose command，48 项聚焦和两个模块 `--help` 均通过。readiness 仍严格比较 DB
  revision 与代码 head。
- 下一动作：完整/横向门、提交推送并等待新 exact-SHA 三 job；不进入 Session/Memory 或外部 I/O。
- 首轮状态回写治理检查发现 canonical 的“唯一下一步”自然语言漏掉精确 checkpoint 字面键；门禁在提交前
  阻止。已补回 `6A-7-packaging-exit-review` 并保持 module-entry 修复范围不变，随后必须重跑治理。

## 2026-08-18：6A-7 与 6A 公共闭环

- module-entry 修复提交 `adf53e56d1eb624746b493ad8b281598c9a0dd32` 已推送；Actions
  `32146760003` 的 pytest、postgres-migrations、packaging-smoke 三 job 全部成功。
- 公共 pytest 为 `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；RAG 两门满阈值、Harness
  published；真实 PostgreSQL 为 `51 passed, 1 warning`。
- Linux smoke 真实输出 `external_riot_provider_calls=0` 与安全 failed terminal；随后非 root/image
  exclusion 检查成功。失败诊断 step 因 smoke 成功而正确跳过，teardown 成功。
- exit matrix/review 改为 `close-with-deferred-boundaries`；RQ-059 与 Phase 15 完成。canonical 只交接
  `stage-6-session-memory-entry-design` 准备状态，等待用户明确继续，不自动实现 Session/Memory。

## 2026-08-19：RQ-060 恢复与 Session/Memory 入口设计启动

- 按 `AGENTS.md` 顺序恢复 canonical、活动计划、需求/历史/路线/修订/能力矩阵，并运行治理；初始工作树
  干净，`HEAD == origin/main == d1cc2ed`。
- 发现官方 session catch-up 不解析活动计划目录后，改为人工审计 Codex JSONL、Git 与计划尾部；确认无
  半写代码，但补出 `d1cc2ed` / Actions `32147545753` 三 job 成功和用户 RQ-060 授权两项未同步事实。
- 已只读审计现有 ActorContext、owner-scoped task/run、PostgreSQL task schema，以及 EchoMind
  `conversation_memory.py`/API 和 AGI-Saber Memory/Writer 关键源码；没有读取 Key、调用 Riot/Provider、
  安装依赖或实现产品 Session/Memory。
- 已同步 canonical、活动计划、RQ 日志、主路线/修订/能力矩阵、变更历史和项目决策，并为 Phase 16 增加
  原子 checklist。治理与陈旧文本检查随后已通过；下一动作是向用户进行第一节概念与数据流教学。
- `git diff --check` 与治理检查已通过；陈旧扫描命中的“等待授权”均位于 RQ-059/6A 历史段，后续
  RQ-060/current 段已明确覆盖。现有两 owner PostgreSQL/API 测试也已复核，确认可复用 ownership 基线。

## 2026-08-19：Session/Memory 设计第一节确认

- 已向用户讲解并区分 Task/Run、Session、消息/工作上下文、长期 Memory、原始事实/Artifact 与 RAG，
  同时展示 trusted owner → Session → Context Builder → Runtime/Harness → Memory Candidate → write gate 主链。
- 用户明确“确认”。Phase 16 的概念教学项改为 completed，三方案比较项改为 in_progress。
- 下一动作只比较存储/写入架构并取得一个方向确认；不创建 ADR、不实现 schema/repository/API 或新依赖。

## 2026-08-19：Session/Memory 设计第二节确认

- 已比较 PostgreSQL 单一真源、EchoMind 式 Redis/Chroma 拆分、PostgreSQL+Redis+向量首日混合三案，
  并讲清真源、缓存和派生索引的差异。
- 用户明确“采用吧”，确认方案 A。三方案比较项改为 completed，数据模型/write gate 项进入 in_progress。
- 下一动作只确认 owner/conversation/player-subject 身份作用域与关系模型；不创建表、migration 或 Repository。

## 2026-08-19：外服账号归属边界修正

- 用户指出当前只能调用 Riot 官方外服 API，不能查询中国大陆国服；已记录 RQ-061。
- 复核官方 LoL routing/RSO 文档后确认：Riot ID→PUUID 只证明账号存在，不能证明当前 owner 控制该账号；
  RSO `/accounts/me` 可形成登录 Riot 账号证据，且需要获批 Production-level application/API key 与 RSO
  client；要升级当前 owner-player 关系还必须有正式产品 Auth、安全 callback 绑定和精确 PUUID 匹配。
- 当时只把 `claimed_self` 视为用户声明，私人训练数据按 owner-local player subject 隔离；是否同时提供
  `public_observed` 关系及其受限长期能力仍待本节确认。该临时状态已由下方 RQ-062 确认条目取代。
- 本轮仍没有创建 Session/Memory schema、migration、Repository 或 API；没有读取 Key、调用 Riot/Provider。
  下一动作是向用户讲清认领后的允许/禁止/切换/同账号多 owner 边界并取得一个关系策略裁决。

## 2026-08-19：外服玩家关系策略确认

- 用户明确“确认吧”；RQ-062 已追加，RQ-061 保留当时 pending 历史并标注后续由 RQ-062 确认。
- 当前设计接受 `claimed_self` 与受限 `public_observed`，并采用 role/verification 两维模型；
  `verified_self` 当前不可创建，只保留未来正式 Auth + 安全 RSO callback + PUUID match 升级门。
- canonical、活动计划、路线、修订、能力矩阵、变更历史和项目决策已同步本确认；没有产品代码或外部 I/O。
- 下一动作只讲解并确认 conversation 固定/切换语义及 task 继承关系，不进入 Session/Memory 字段、写入门
  或产品实现。

## 2026-08-19：Conversation 固定玩家方案确认

- 用户明确“确认”；RQ-063 已追加。V1 conversation 创建时绑定 trusted owner 的一个 player subject，
  生命周期不可切换；不同 PUUID 新建 conversation，相同 PUUID 改名可继续。
- 消息/Context/task/run/Memory Candidate 的 owner/conversation/subject 继承、client/model 不可覆盖、
  composite FK/迟到 task/跨 owner 测试已进入设计不变量；没有实现代码。
- 源码复核发现入队时尚无 PUUID，Worker 内才解析；下一动作改为比较异步 link task、首个 review bootstrap
  与 API 同步 lookup，先冻结稳定 subject 的创建顺序，再进入 Memory 字段/write gate。

## 2026-08-19：RQ-064 连续设计与实施授权

- 用户明确授权本轮不再逐节等待方案审批，由 Codex 在已确认边界内选择最佳剩余设计，并在完整说明后
  直接实施第一步、验证/推送后自动继续第二步；持久化裁决将其精确限定为 entry design→6B-1→6B-2，
  三批均独立完成教学、TDD、本地门禁、提交、推送和 exact-SHA 公共 CI，6B-2 后停止在 6B-3 准备态。
- 该授权已追加为 RQ-064，并同步 canonical 与活动计划；治理检查通过。它取代 RQ-060 的“设计后另行
  授权”暂停门，但不授权真实 Riot/Provider 调用、正式 Auth/RSO/HTTPS、SSE/前端、阶段 7/8 或新技术栈。
- 三案源码审计选择独立异步 `player-link`：API 只持久化 link intent，专用 Worker 在事务外调用
  Account-V1，随后在一个 PostgreSQL 短事务中收敛 subject、alias、owner relationship 和 link terminal；
  link 成功后才允许创建 conversation。首个 review bootstrap 与 API 同步 lookup 均被拒绝。
- Memory 模型选择“关系型身份/状态骨架 + 分类型长期记录 + 严格 JSONB 叶子 + 统一 Candidate write gate”；
  拒绝大画像 JSON、万能 memories 表、EchoMind 式双真源和模型直接永久写入。
- ADR-0039、完整 Session/Memory 设计和 6B-1 至 6B-9 实施计划已本地创建；设计批本身没有创建
  migration/schema，也未调用外部服务。
- 后续只读一致性审计发现并修正两项关键问题：自动范围收紧为 entry design→6B-1→6B-2，6B-2 后停止；
  `player_link_tasks` 必须私有持久化 Worker 所需的 bounded normalized `game_name/tag_line`，不能只存 hash。
- canonical、RQ、活动计划、roadmap/amendment/capability/project decisions/history 正在同步为“设计已本地
  冻结但尚未公共验证”。下一动作是运行设计批比例门禁、独立提交/推送并等待 exact-SHA 三 job；全绿前
  不进入 6B-1。

## 2026-08-19：Session/Memory 设计批本地门禁通过

- 完整 pytest：`1102 passed, 27 skipped, 1 warning, 110 subtests passed`；本机无 PostgreSQL/Docker 的
  既有 skip 不能冒充真库/Linux 成功，仍由 exact-SHA CI 补齐。
- RAG development 与独立 holdout 均为 Recall/MRR/nDCG 1.0、无答案误召回 0；holdout abstention/citation
  也为 1.0。Harness 正确命令 dry-run 得到 `published`、0 revisions。
- compileall、governance、SDK boundary、tracked Secret/run-data、YAML 与 `git diff --check` 全部通过；
  本批没有创建 migration/schema，没有读取 Key或调用 Riot/Provider。
- 首次 Harness 外围验证误写为不存在的 `scripts/run_harness.py`，命令以 file-not-found 退出且没有文件
  副作用；随后先从 `.github/workflows/tests.yml` 读取真实入口，使用 `scripts/run_review_harness.py` 成功。
  该错误不作为测试失败掩盖，也不重复猜文件名。
- 首次陈旧短语扫描在 PowerShell 末尾误用了 Bash 风格 `|| exit 0`，扫描主体与前面的 governance/diff 已
  完成，但尾部报 `exit` 不可执行；随后改为显式检查 `$LASTEXITCODE`，结果为无过宽 RQ-064 自动范围短语。
- 下一动作只提交/推送设计批并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；全绿前
  canonical 保持 entry design in progress。

## 2026-08-19：Entry design 公共闭环并进入 6B-1

- 设计提交 `bc11afe9f2f85a39f05b7f3d6135b14821ebb17d` 已推送；Actions run `32222531783` 总状态
  success，公开页面列出的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功。
- 首次 push 因环境变量仍指向失效 `127.0.0.1:7890` 失败；发现 Clash Verge mixed port 在 7897。
  Git 默认 Schannel 经该端口写请求仍握手失败，最终只在单次子进程用 OpenSSL + SOCKS5 成功推送，未改
  系统或 Git 全局配置。GitHub CLI keyring token 已过期，但公开只读 Actions 查询仍可用。
- `gh run view/api` 经代理两次返回 EOF；没有凭模糊状态判断，改用公开 Actions 页面核对精确 SHA、总状态
  与三个 job。entry design 正式关闭。
- canonical/活动计划进入 `6B-1-player-identity-link-foundation`；下一动作先完成初学者教学和 pure domain
  红灯测试，Resolver/Worker/API、Conversation/Memory 与外部 I/O 均保持范围外。

## 2026-08-19：6B-1 本地实现、RQ-065 收口与门禁

- 用户确认权限后恢复到 `42d46bd`，HEAD 与 origin/main 一致；已有 domain/schema 未提交产物完整保留。
- 用户随后以 RQ-065 将本轮目标收紧为只完成 6B-1；已同步 requirement、canonical、活动计划、路线、
  amendment、capability、ADR/design/implementation 与 decisions/history，6B-2 不再自动实施。
- 三个并行子任务均在执行项目命令前遇到平台 `prompt_cache_retention` 兼容错误；另一次指定
  `gpt-5.3-codex` 被当前账户拒绝。检查共享工作树后由主线程接管，没有重复覆盖已有文件。
- pure domain 的历史红灯为 `ModuleNotFoundError: app.players`；Repository 新红灯为
  `ModuleNotFoundError: app.persistence.player_repository`。现已实现 Player models/fingerprint/Service/Port、
  四表 ORM/Alembic 0002、`PostgresPlayerRepository` 与阻塞真库测试清单。
- Repository 行为包括 idempotent create/replay、owner/global capacity、owner-scoped GET、deterministic
  SKIP LOCKED claim、双 Worker 不重复、subject/alias/relationship upsert、same-PUUID convergence、
  role conflict 同事务失败、stale worker CAS、confirmed Riot ID snapshot、SQL rollback 和 UTC 单调时间。
- 首次 Alembic offline SQL 编译发现两个 constraint 名超过 PostgreSQL 63 字符；已同步缩短 ORM、migration、
  Repository ON CONFLICT 和测试名称。全 metadata identifier 扫描与 11930-byte offline SQL 生成通过。
- 本地聚焦 `15 passed, 13 skipped`、相邻 `35 passed, 28 skipped`、完整
  `1117 passed, 40 skipped, 1 warning, 110 subtests passed`。40 skip 是本机无 PostgreSQL 的明确边界。
- 两套 RAG 满阈值，Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked data、YAML、
  initial governance/diff 通过。本批外部 Riot/Provider/Key 调用为 0。
- 下一动作：重跑状态同步后的 governance/stale/line/diff 门，暂存后独立 cached diff check，再提交、推送并
  等待 exact-SHA 三 job；全绿后关闭 6B-1 并按 RQ-065 停止。

## 2026-08-19：6B-1 首个公共 run 失败与 Alembic revision 修补

- 实现提交 `656117abb049f7ef653f6febd44df9d630daed2d` 已推送；Actions `32227457202` 总状态 failure。
  普通 pytest 无错误 annotation；`postgres-migrations` 在 reversible migration step 失败，
  `packaging-smoke` 在启动包含 migration 的 API stack 失败，不能关闭 6B-1。
- 首轮 push 的 OpenSSL+SOCKS 路径持续 TLS EOF；只读检查确认 HTTP mixed proxy 可用后，改用单次
  Schannel+HTTP/1.1 代理成功推送，未更改全局配置。
- 共同失败点审计发现 Alembic revision `0002_player_identity_and_link_tasks` 为 35 字符，而默认
  `alembic_version.version_num` 只有 32。先新增无数据库合同测试并得到明确红灯 `assert 35 <= 32`，再把
  revision 缩短为 `0002_player_identity_link`；migration 文件名和 down_revision 顺序无需改变。
- 修补后 6B-1 聚焦为 `16 passed, 13 skipped`，完整为
  `1118 passed, 40 skipped, 1 warning, 110 subtests passed`。下一动作是重跑横向门、独立修补提交并等待
  新 exact-SHA 三 job；旧失败 run 只作失败证据，不重跑或冒充成功。

## 2026-08-19：6B-1 第二个公共 run 与 CHECK 命名修补

- revision 修补提交 `b8fa2e36a32ac941e7d1f08eb254c744c5a88b71` 已推送；Actions `32227937252`
  中 pytest 与 packaging-smoke 成功，reversible migration 也成功，只有 PostgreSQL test step 失败。
- 通过已登录 GitHub 的只读 job 日志取得精确结果：`66 passed, 1 failed`；唯一失败是
  `test_player_identity_migration_creates_postgresql_schema`，数据库把 role-verification CHECK 名变成带 hash
  的截断名，未匹配冻结的稳定名称。
- offline SQL 复现 migration 把完整 `ck_owner_player_relationships_*` 再套一层 naming convention；先加
  无数据库红灯，随后对 0002 全部 22 个显式 CHECK 名使用 `op.f(...)`，避免只修当前首个断言后再逐个失败。
- 新 offline test 与双前缀扫描通过；6B-1 聚焦现为 `17 passed, 13 skipped`，完整为
  `1119 passed, 40 skipped, 1 warning, 110 subtests passed`。下一动作重跑横向门并推送第三个精确 SHA。

## 2026-08-19：6B-1 公共闭环并停止

- 全 CHECK 命名修补提交 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 已推送；Actions
  `32229024069` 总状态 completed/success，pytest、postgres-migrations、packaging-smoke 三 job 均成功。
- 这补齐本机 40 个 PostgreSQL/Docker skip，6B-1 正式完成；三次 run 保留了“失败→红灯→最小修补→新
  exact-SHA”的证据链，没有重跑旧 SHA 或放宽 schema 断言。
- RQ-065 已满足：本轮不进入 6B-2。canonical/活动计划现只把
  `6B-2-async-player-link-worker-api` 置为 prepared/waiting authorization。
- 下一动作仅是提交/推送本状态交接并验证其自身 exact-SHA 三 job；成功后结束本轮。

## 2026-08-19：RQ-066 恢复 6B-2

- 用户在 6B-1 收尾后的新一轮明确“继续开工”，并在桌面权限重置后恢复 `D:\riftcoach-agent` 写权限；
  这授权 `6B-2-async-player-link-worker-api`，不授权 6B-3。
- 已按 AGENTS 顺序恢复 canonical/活动计划/RQ/路线/ADR/design/implementation plan，治理通过，起始
  `HEAD == origin/main == 270d08b` 且工作树干净；6B-1 基线 `17 passed, 13 skipped`。
- 已讲清 API 短事务、Worker 事务外 Account-V1、Resolver 安全错误边界与 Repository 短事务的数据流；
  计划审查无架构阻塞，当前进入 Task 1 Resolver 红灯。
- 本批禁用子代理以规避重复的 Codex `prompt_cache_retention` 平台兼容故障；该故障不来自 RiftCoach
  配置或代码。开发/测试/CI 继续保持真实 Riot/Provider/Key I/O 为 0。

## 2026-08-19：6B-2 Tasks 1–4 本地实现与门禁

- 反向审查确认工作树中的 Resolver、PlayerLinkWorker、Link API、composition/CLI 和 packaging smoke 均
  对应 ADR-0039/6B-2 实施计划，没有把 Conversation/Memory 或 Review Task subject binding 偷带进来。
- 先以红灯固定三个边界修补：smoke 不得把外部 `worker_id` 拼接成可能超长的 Link worker ID；Worker routing
  policy 必须完整覆盖 API 接受的 `americas/asia/europe/sea`；Link Worker 的最小 `StopSignal` 不依赖
  Review Worker 内部协议。修补后新增/相邻回归通过。
- 6B-2 聚焦/相邻测试：`149 passed, 2 skipped, 1 warning`。
- 完整 pytest：`1216 passed, 42 skipped, 1 warning, 110 subtests passed`（约 44.87s）。本机 skip 仅是无
  PostgreSQL/Docker，不能替代公共真库/package 证据。
- 横向门禁：RAG development Recall/MRR/nDCG `1.0`、no-answer FPR `0.0`；独立 holdout Recall/MRR/nDCG/
  abstention/citation 全 `1.0`；Harness dry-run `published`、0 revisions；compileall、YAML、governance、
  SDK boundary、tracked Secret/run-data 与 diff check 均通过。
- 本批未读取真实 `.env`/Key，Fake client/resolver 和离线 smoke 的外部 Riot/Provider calls 为 `0`；真实
  PostgreSQL API/迁移/Compose 证据仍待同一提交的阻塞 GitHub Actions。
- 当前将 Task 1–4 标为 completed、Task 5 标为 in_progress/local-complete-pending-public-CI；下一动作是
  更新持久状态后独立提交/推送，等待 exact-SHA 三 job，全绿前不关闭 6B-2。

## 2026-08-20：桌面中断后的 6B-2 Task 5 恢复与最终本地复核

- 再次严格按 `AGENTS.md` 恢复 canonical、活动计划、RQ/历史/路线/修订/能力矩阵与 ADR/design/implementation；
  `HEAD == origin/main == 270d08b`，未提交 6B-2 工作完整保留，治理预检通过，没有 6B-3 代码。
- 提交前逐文件审查只发现 `tests/test_player_link_api.py` 的参数表有 6 行超过 120 字符；已做等价换行，
  不改变 API、Worker、Resolver、Repository、smoke 或安全语义。
- 最终聚焦复跑为 `111 passed, 2 skipped, 1 warning`；完整复跑仍为
  `1216 passed, 42 skipped, 1 warning, 110 subtests passed`。42 个 skip 仍仅因本机无 PostgreSQL/Docker。
- 两套 RAG 指标仍全部达门，Harness dry-run 为 `published`/0 revisions；compileall、YAML 和 governance
  复跑通过。下一动作保持不变：完成安全/diff/cached-diff 门后提交推送，等待 exact-SHA 三 job。

## 2026-08-20：6B-2 提交、推送与公共闭环

- cached diff 首次阻止提交，因为 `tests/test_player_link_worker.py` 文件末尾多一个空白行；只删除该空行，
  重新暂存后 cached diff 与 governance 通过，未改变功能。
- 独立实现提交 `0c13a583ea51a7c18301fc29bf5c2931790d6693` 已推送到 `main`；一次性使用本机已监听
  的 7897 HTTP proxy + Schannel/HTTP 1.1，未修改 Git 全局配置。
- Actions run `32301852042` 精确对应该 SHA；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。公开 pytest 为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`，真实
  PostgreSQL 为 `70 passed, 1 warning`。
- Linux smoke 输出 `task_status=failed`、`link_status=succeeded`、`external_riot_provider_calls=0`，并通过
  非 root 与 image exclusion。6B-2 正式关闭；Phase 19/6B-3 只置为 prepared/waiting authorization，
  当前停止且没有 Conversation/Message/Memory 代码。

## 2026-08-20：RQ-067 教学/工程说明补齐与 6B-3 条件授权

- 用户要求重新从阶段 0 起确认最早持久说明缺口，并从真实缺口开始补齐；范围不只包含初学者文档，
  还包括设计/实现复盘、代码地图、数据/控制流、证据矩阵、运行示例、失败/安全边界、面试表述、README、
  学习索引和防复发治理门。
- 采用覆盖矩阵驱动的混合方案：充分材料直接链接复用，缺口才新增成品，避免按文件数量制造重复内容。
- RQ-067 已追加；Phase 19 保持唯一 in-progress 指针，但 6B-3 产品代码受文档公共闭环前置门阻塞。
  补齐经治理、回归、独立提交/推送与 exact-SHA CI 确认后，无需用户再次回复即可进入 6B-3。
- 当前只读审计进行中；尚未创建 Conversation/Message schema、migration、Repository、API 或测试代码。

## 2026-08-20：RQ-067 本地材料与治理门完成，等待公共闭环

- 从阶段 0 到 6B-2 的覆盖审计已完成：最早真实缺口在阶段 0；阶段 1、4、5A、5B、6B-1、6B-2 需要新增或扩充，阶段 2、5C、5D、5E、5P、5F、6A 与 Session/Memory entry design 复用成熟材料。
- 新增 `docs/learning/README.md`、`coverage.yaml`、阶段 0/1/4/5B/6B-1/6B-2 walkthrough；扩充 `agent_loop_v1.md`、`provider_tool_runtime_usage.md`，为 5C 短设计补统一退出复核链接。
- README、AGENTS、roadmap、amendment、capability matrix、project decisions/history 与 canonical 已纳入持久学习合同；coverage 防复发治理采用 TDD，当前治理聚焦为 `9 passed`。
- 当前工作树仍没有 6B-3 Conversation/Message/Memory 产品代码；下一动作是完成剩余路线/决策历史同步、比例/完整门禁与独立公共 CI。全绿后按 RQ-067 自动进入 6B-3 初学者设计复核与 TDD。

## 2026-08-20：RQ-067 本地完整门禁与退出复核

- 新增 `docs/plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md`，固定最早缺口裁决、覆盖动作、八维合同、本地证据、限制和 6B-3 交接。
- 治理聚焦最终为 `10 passed`；Agent Loop/Skill `34 passed`，Provider/Tool `101 passed, 68 subtests`，领域/RAG 代表性集合 `37 passed`。
- 完整 pytest 为 `1224 passed, 42 skipped, 1 warning, 110 subtests passed`；RAG development/holdout、Harness dry-run、compileall、secret/tracked-data、SDK boundary、Markdown/YAML/link/diff 与治理均通过。
- 本地退出裁决为 `pass-local-pending-public-ci`；42 skip 仍只表示本机无 PostgreSQL/Docker。下一动作是独立提交、推送并等待 exact-SHA 三 job，全绿前不进入 6B-3。

## 2026-08-20：RQ-067 文档门公共闭环并进入 6B-3

- 文档批提交 `63435d90f5153309fce98b92a2ff58425d54a684` 已推送；Actions `32308631289` 精确对应同一 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 success。
- RQ-067 前置门关闭，Q11 公共证据成立；这只验证文档/治理/现有回归/真库 migration 与 package 边界，不表示 6B-3 Conversation/Message/Memory 已完成。
- canonical/活动计划现正式进入 `6B-3-conversation-message-foundation` 的初学者设计复核与 TDD；下一动作是讲固定 owner/relationship/subject、消息角色/长度、并发序号和生命周期，再写红灯合同。

## 2026-08-20：6B-3 接缝审计与设计冻结

- 只读审计确认 6B-3 可以复用现有 SQLAlchemy Base、Player relationship 复合 identity、短事务
  Repository、FastAPI Port/proxy/lifespan 与 PostgreSQL blocking CI；不需要引入 EchoMind、Saber、
  LangGraph、Redis、向量库或新 SDK。
- 冻结六个实现前不能含糊的点：复合 FK 不证明 relationship active；Conversation POST 需要
  owner-scoped Idempotency-Key；公共 Message 只能写 user；序号从 1 开始由 Conversation 行锁分配；
  archived 与 hidden 分离；绑定字段必须由 PostgreSQL trigger 防 direct SQL rebind。
- 新增 ADR-0040 与 `docs/plans/2026-08-20-conversation-message-foundation-design.md`，包含初学者
  原理、FR/NFR、schema、数据/控制流、API/error、安全、测试矩阵、退出条件和面试边界；没有创建产品
  schema/migration/code，也没有外部 I/O。
- 复核 backfill 审计发现 README 前置条件已在 `63435d9` 修正，日期记录与当前仓库日期一致；真正的
  governance 顺序弱点是“重排并同时重编号”。已加固定 canonical coverage order 与对应红灯，治理
  聚焦 `12 passed`，主治理仍通过。
- 下一动作是纯模型/Service/API 红灯合同；PostgreSQL migration/Repository/并发测试仍必须在后续红灯
  批和真实 CI 中验证，不能把设计稿当成实现证据。

## 2026-08-20：6B-3 设计批本地门禁

- 治理聚焦 `12 passed`，完整 pytest `1226 passed, 42 skipped, 1 warning, 110 subtests passed`；42 个
  skip 仍只因本机无 PostgreSQL/Docker，不能冒充真库证据。
- RAG development/independent holdout 均满既有阈值；Harness dry-run 为 `published`/0 revisions；
  compileall、SDK boundary、tracked Secret/run-data、YAML、治理和 diff 门均通过。
- 首次把并行验证与 TEMP 递归清理放在同一工具批，终端策略在进程创建前拒绝整个批；随后把四项验证
  拆开并成功运行。两次对已验证 TEMP 目标的递归清理仍被策略在进程创建前拒绝，未改仓库且临时产物
  只位于用户 TEMP；停止重复删除，不把清理噪声当测试失败。
- 下一动作是独立暂存/cached diff、提交、推送和 exact-SHA 三 job；全绿后直接进入红灯合同。

## 2026-08-20：6B-3 设计批公共闭环并进入 TDD

- 提交 `b6a7112d9c3fa8744b9713737bbbf54fe5011084` 已推送；Actions `32313707301` 总结论
  success，三个 job `pytest`、`postgres-migrations`、`packaging-smoke` 均 completed/success。
- 公共 run 同时执行 governance、完整 pytest、两套 RAG、compile、SDK/secret 边界、Harness dry-run、
  真实 PostgreSQL migration/test/metadata 和 Linux no-I/O image smoke；仍不代表 6B-3 产品实现。
- 当前工作树在状态回写前为 clean；下一动作无缝进入 pure model/Service/API 红灯，再实现数据库与 API。

## 2026-08-20：6B-3 未提交实现恢复与最终证据补强

- 按 AGENTS 顺序恢复 canonical、活动计划、RQ、路线、capability 与 learning coverage；治理预检通过。
- 确认 `HEAD == origin/main == b6a7112d9c3fa8744b9713737bbbf54fe5011084`，完整 6B-3 实现仍在未提交工作树，
  没有回滚或覆盖。
- 收到 persistence 只读审查：无 P0/P1；确定一个提交前 P2——原生命周期/append 并发测试没有控制谁先拿锁；
  另记录读取串行取舍和 trigger/Repository 责任边界。
- 新增干净子进程 import/OpenAPI no-I/O 测试，避免模块缓存把首次 import 证据变成假绿；聚焦
  `tests/test_api_composition.py` 为 `10 passed, 1 warning`。
- 下一动作：补 archive/hide 与 append 的双向确定性锁顺序测试，随后完成 walkthrough 与全部状态材料。
## 2026-08-20：6B-3 本地实现收尾，公共验证前

- 已从中断点恢复，确认 `HEAD == origin/main == b6a7112d9c3fa8744b9713737bbbf54fe5011084`，未提交实现仍完整，未回滚或越级。
- 6B-3 聚焦 `85 passed, 25 skipped`；完整 `1295 passed, 67 skipped, 1 warning, 110 subtests passed`。
- 两套 RAG、Harness dry-run（published/0 revisions）、compileall、SDK boundary、tracked Secret/run-data、YAML、治理和 diff 门均通过；本机无 Docker，Compose/真库留给公共 CI。
- 现在唯一下一动作是独立暂存、cached diff、提交/推送并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；全绿后才用独立状态批关闭 6B-3，并只交接 6B-4 prepared/waiting authorization。

## 2026-08-20：6B-3 首次公共门失败与最小修复

- 实现提交 `0ca7fde` 已推送；Actions `32329394058` 中 `pytest`、`packaging-smoke` 成功，
  `postgres-migrations` 失败。
- 真实日志显示全部失败集中在 PostgreSQL fixture 的父表未先 flush，触发
  `owner_player_relationships → player_subjects` FK violation；不是 Conversation Repository 业务断言失败。
- 已加入测试 fixture 的显式 parent flush；下一步只复跑本地相关测试、cached diff、提交新修复 SHA，再等待新的
  exact-SHA 三 job。6B-3 仍保持 `in_progress`，coverage 仍为 `planned`。

## 2026-08-20：6B-3 实现公共闭环与状态收尾

- 恢复后确认实现修复已在 `7e4f23361ec331e53c5190f6a5f7f3532f533081`，工作树干净且 `HEAD == origin/main`；
  没有重复实现或回滚。
- Actions run `32329686381` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 `completed/success`；公开 pytest 为 `1295 passed, 67 skipped, 1 warning, 110 subtests passed`，
  PostgreSQL 为 `100 passed, 1 warning`，package smoke 与 migration upgrade/downgrade 通过。
- 独立收尾批将 canonical 状态置为 `complete`、coverage 6B-3 置为 `complete`，并把唯一下一检查点写为
  `6B-4-conversation-bound-recent-review-identity` 的 prepared/waiting authorization；本轮不实施 6B-4。
- 收尾验证中系统 Python 因没有 `pytest` 首次退出；改用 `.venv\Scripts\python.exe` 后，6B-3 聚焦为
  `71 passed, 25 skipped, 1 warning`，完整回归为 `1295 passed, 67 skipped, 1 warning, 110 subtests passed`。
- 状态收尾横向门再次通过：RAG development 与 independent holdout 的既定指标均为 `1.0`（FPR `0.0`），
  Harness dry-run 为 `published`/0 revisions，compileall、coverage YAML、governance 与 `git diff --check`
  通过；本批只修改持久状态/教学材料，没有 6B-4 产品文件或外部 Riot/Provider/Key I/O。

## 2026-08-20：RQ-068 开始 6B-4 Conversation-bound Review Identity

- 用户明确授权 6B-4；按 AGENTS 恢复 canonical、活动计划、RQ/历史/路线/修订/能力/learning coverage，
  读取 ADR-0039 与 Session/Memory 总设计/实施计划，治理预检通过。
- 起始 `HEAD == origin/main == 4fb66a88f5e5bc761e4604a359ae7e130a130cfd` 且工作树干净；6B-3 已由
  `7e4f233` / Actions `32329686381` 三 job 公共闭环，没有需要恢复的未提交 6B-4 代码。
- 已完成初学者教学与三方案比较，推荐 nullable schema 2.0 identity columns + atomic server-derived
  Conversation binding；旧 1.0 保持 read/execute compatibility，不把 identity 只藏在 JSON payload。
- 当前先同步 RQ-068、canonical、Phase 20、planned coverage、治理固定顺序与陈旧状态；治理再次全绿后
  再建立 ADR-0041/专用设计/任务计划和红灯合同。尚未修改产品 schema/code/tests，外部 I/O 为 0。

## 2026-08-20：6B-4 设计冻结，进入 pure domain/API 红灯

- 完成 Task/Conversation/Player Subject/Alias/Summary/Application/API/Worker/migration/package 接缝审计；
  确认原子身份绑定必须落在 `PostgresTaskRepository` 单事务，不能拆成 Service 两次调用。
- 新增 ADR-0041、`2026-08-20-conversation-bound-recent-review-design.md` 和对应 implementation plan，
  冻结 nullable schema 2.0 columns、复合 FK、identity fingerprint、private PUUID target、legacy 1.0 分支。
- 活动计划把治理同步与设计任务置为 completed，唯一 in-progress 任务切到 pure domain/API 红灯；
  尚未修改产品代码、migration 或测试，Riot/Provider/Key I/O 为 0。

## 2026-08-20：6B-4 中断恢复至 Repository 红灯

- 恢复确认 `HEAD == origin/main == 4fb66a88f5e5bc761e4604a359ae7e130a130cfd`，既有未提交 6B-4 工作树完整保留；治理和 `git diff --check` 通过，没有 6B-5 文件或外部调用。
- pure domain/API 已完成 25 项聚焦与 42 项相邻绿灯；0004/ORM migration 已完成 offline SQL 与 21 项聚焦（本机真库 2 项明确 skip），但尚无当前提交的真实 PostgreSQL CI 证据。
- 已写 `tests/test_conversation_review_repository_postgres.py`，当前从该红灯继续实现 Repository 的单事务 server-derived binding、v2 private target mapping、alias rename 与 late claim；不重复前两批实现。

- Repository 测试本机实际结果为 `4 skipped`（未配置真库），没有冒充红灯或绿灯；随后完成 legacy helper、Player/Conversation record 与 alias 排序接缝审计，准备进入最小 Repository 实现。
- Repository 最小实现现已加入：单事务 active tuple 锁定、identity-aware fingerprint、schema 2.0 insert、session-aware target mapping，以及 create/get/claim/replay 的统一 v2 投影；本地兼容/聚焦为 `28 passed, 11 skipped, 1 warning`，compileall 与 diff check 通过。下一步补 capacity/rollback/create-vs-lifecycle 真库合同，不在缺少并发证据时提前关闭 Task 3。
- Task 4 红灯已实际观察：聚焦测试收集分别因缺少 `build_player_summary_by_puuid` 与 `app.product` 尚未导出 `ConversationRecentReviewRequest` 失败；这证明可信 PUUID Summary/Application 接缝尚未被旧代码误判为已存在。下一步只实现共享后半段与 1.0/2.0 Executor 分支。

## 2026-08-20：6B-4 Task 3/4 恢复裁决与 Task 5 接续

- 严格恢复后确认 `HEAD == origin/main == 4fb66a88f5e5bc761e4604a359ae7e130a130cfd`，未提交
  6B-4 工作树完整保留，治理与 `git diff --check` 通过，没有进入 6B-5。
- Repository 已实现单事务 server-derived binding、v2 私有 target 装配及 legacy 映射；本机真库套件
  结果为 `1 passed, 14 skipped`，skip 全因没有 PostgreSQL，必须由阻塞 CI 补证。
- trusted-PUUID Summary/Application/Executor 已完成，聚焦 `51 passed`；v2 Account-V1 调用为 0，
  alias 只影响显示，binding/target/fingerprint 篡改在 Application 前拒绝，legacy 1.0 保持兼容。
- Task 5 审计发现 composed `_TaskServiceProxy` 尚未转发 `create_conversation_review()`；package smoke 也只到
  Link→Conversation→Message，PostgreSQL job 尚未列入两个 6B-4 真库测试文件。下一动作先写 composition/
  package 红灯，再做最小接线，不创建第二套 Worker。

## 2026-08-20：6B-4 Task 5 本地完成

- composition 红灯实际得到 503，因为 `_TaskServiceProxy` 缺少 v2 转发；加入类型化方法后 composed/API
  聚焦 `24 passed`，证明 lifespan 绑定的真实 Service 可以收到 trusted Actor/path/body command。
- package 红灯实际暴露缺少 v2 结果字段和四个 allowlisted failure code；最小实现将 smoke result 升为
  1.1，并覆盖 Link→Conversation→Message→schema 2.0 Task→同一 Worker→safe failed terminal；package
  套件 `18 passed`，外部调用字段保持 0。
- CI 合同红灯证明两个新 PostgreSQL 文件尚未进入 job；现已加入 `postgres-migrations` 阻塞列表。
- Task 5 聚焦/相邻合计 `114 passed, 11 skipped, 1 warning`；11 个 skip 全因本机无 PostgreSQL，
  compileall 与 diff check 通过。下一动作进入 Task 6 walkthrough、八维 coverage、完整门禁和公共闭环。

## 2026-08-20：6B-4 Task 6 本地门禁完成，等待提交

- 新增 `docs/learning/6b-4-conversation-bound-recent-review-identity-walkthrough.md`，按八维合同讲清
  server-derived identity、schema 方案、代码地图、创建/执行流、证据矩阵、runbook、安全和面试边界；
  coverage 路径已完整但在公共三 job 全绿前保持 `planned`。
- 完整 pytest 为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`；78 个 skip 仍全部是本机无
  PostgreSQL/Docker，不能写成真库/package 成功。
- RAG development 与 independent holdout Recall/MRR/nDCG 均 `1.0`、FPR `0.0`，holdout abstention/
  citation `1.0`；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked data、YAML、
  pip、governance 与 diff 门通过。
- canonical、roadmap、capability matrix、decisions、history、learning index 与 active plan 已同步为“本地完成、
  待公共闭环”。唯一下一动作是最终静态审查、独立暂存/cached diff、提交推送并等待 exact-SHA 三 job；
  6B-5 未进入。

## 2026-08-20：6B-4 实现提交、公共闭环与状态收尾

- 暂存范围复核为 47 个 6B-4 文件、无未跟踪/未暂存混入项；治理与 cached diff check 通过。实现提交
  `d63f9085f66e49557b4674d0698495dcb7335c82` 已推送到 `main`。
- Actions run `32347834279` 精确对应实现 SHA；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。公开 pytest 为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`，真库为
  `113 passed, 1 warning`，Linux package smoke 的外部调用为 0。
- 状态收尾把 6B-4 coverage 改为 complete，并登记 6B-5 planned；canonical/active plan 只交接到
  `6B-5-memory-candidate-write-gate` prepared/waiting authorization，不实施 6B-5。
- 首次收尾完整回归为 `1 failed, 1332 passed, 78 skipped`，唯一失败是治理测试仍硬编码 6B-4 为当前
  checkpoint；只更新该测试夹具为 6B-5 后，治理聚焦 `12 passed`，完整回归恢复为
  `1333 passed, 78 skipped, 1 warning, 110 subtests passed`，没有放宽 coverage 或阶段顺序约束。

## 2026-08-20：RQ-069 开始 6B-5 Memory Candidate & Write Gate

- 按 AGENTS 顺序恢复 canonical/活动计划/RQ/路线/能力/learning coverage，治理预检通过；起始
  `HEAD == origin/main == 405e10941830e28be2a9086390f161c66fecc359` 且工作树干净。
- 已完成初学者入口教学、6B-3/6B-4 持久接缝审计和四方案比较；选择事务内 typed materializer，生产在
  6B-6 前 fail closed，不用 receipt 或万能表冒充长期 Memory。
- 已登记 RQ-069、ADR-0042、专用设计与原子实施计划，并同步 canonical/roadmap/capability/learning。
- 当前仍没有 6B-5 产品 migration/model/Repository/API/test；下一动作是 Candidate pure-contract 红灯。

## 2026-08-20：6B-5 本地纵向切片完成，等待公共验证

- TDD 已完成 Candidate models/Gate、Service/Port、ORM/0005、PostgreSQL Repository、materializer seam、API、
  composition、package smoke 与 blocking CI 清单；实现不含具体长期 Memory target。
- 本地 6B-5 聚焦为 `50 passed, 10 skipped, 1 warning`；10 skip 仅为无 PostgreSQL/Docker 的真实锁/FK/
  trigger/事务/并发证据。此前完整回归出现 2 个旧 OpenAPI exact-path 断言，已按新增 Candidate routes 修正。
- walkthrough 八维材料已加入，coverage 继续 planned；RAG、Harness、compileall、secret/SDK/YAML/governance/
  diff 仍需最终完整复跑。
- 唯一下一动作保持为完整本地门禁→cached diff→提交/推送→exact-SHA 三 job；全绿前不关闭 6B-5、不进入 6B-6。

## 2026-08-20：6B-5 提交、公共修复与状态收尾

- 实现提交 `7156cb52e1ab2a976828b5a0a164c163943b56f3` 已推送；本地完整回归为
  `1358 passed, 88 skipped, 1 warning, 110 subtests passed`，两套 RAG、Harness、compileall、治理、
  SDK/secret/YAML/diff 门通过。
- Actions `32372854457` 的 pytest/package 成功，PostgreSQL 只因测试 target 未在 downgrade 前删除而
  teardown 失败；最小测试清理提交 `dd7c9c8f43bac19756272aaf9555f0519e22341c` 已推送。
- Actions `32376405150` 对修复 SHA 的三 job 全绿：公开 pytest `1358 passed, 88 skipped, 1 warning,
  110 subtests passed`；真实 PostgreSQL `126 passed, 1 warning`；package Candidate 为 rejected，
  `external_riot_provider_calls=0`。
- coverage 现置为 complete；canonical/active plan 只交接 `6B-6-preferences-profile-review-memory`
  prepared/waiting authorization。本轮不实施 6B-6。

## 2026-08-20：RQ-070 授权并完成 6B-6 设计批

- 用户最新“那继续”只授权 canonical 的 `6B-6-preferences-profile-review-memory`；已按恢复顺序重新读取
  canonical、活动计划、RQ/路线/能力矩阵、learning coverage、ADR-0039/0042 与 6B-5 接缝源码，并通过治理预检。
- 初学者教学先区分 Preference、Player Profile、Review Memory 与 Candidate：本批建立真正长期 target，
  不做 RAG、Context、Plan/Progress 或 assistant terminal。
- 冻结 ADR-0043、`docs/plans/2026-08-20-memory-types-design.md` 和
  `docs/plans/2026-08-20-memory-types-implementation.md`：三张 typed 表、严格 envelope、self/observed
  规则、版本 supersede、Review append 单 active 语义、advisory lock、查询 API 与公共 CI 门。
- 本轮只修改设计/治理/持久计划文件，没有创建 6B-6 migration/model/Repository/materializer/API 产品代码，
  外部 Riot/Provider/Key I/O 为 0。
- 设计批治理首跑发现唯一下一步缺少固定机器前缀，聚焦测试为 `1 failed, 11 passed`；只修复 canonical
  元数据格式后，治理测试 `12 passed`、治理脚本、compileall 与 diff check 通过。
- 完整本地回归为 `1358 passed, 88 skipped, 1 warning, 110 subtests passed`；88 个 skip 仍是本机无
  PostgreSQL/Docker，不能外推为 6B-6 真库证据。
- 设计提交 `e44d48f0531f0ee1786cba9b38c8fc8b2589af00` 已推送；Actions run `32381553145` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job exact-SHA 全绿。该公共 run 只证明设计/治理
  与既有基线兼容，不证明 6B-6 target 业务代码已实现。
- 设计批关闭后，canonical/active plan 唯一 in-progress 任务切换为 Task 1 pure typed contract；外部
  Riot/Provider/Key I/O 仍为 0。

## 2026-08-20：6B-6 Task 1 pure typed contract 完成

- 新增 `app/memory/typed_models.py`：严格 `value + expected_version` envelope、三类 target/key allowlist、
  self/observed 权限、payload schema/长度/控制字符/finite number 与规范化输出；该模块无 SQL/文件/网络依赖。
- 首轮聚焦红灯为 3 failed/8 passed：strict Enum 不接受字符串输入、未知 preference key 原因码过宽；只增加
  显式 allowlist Enum 规范化并拆分未知 key 原因码后为 11 passed。
- 与既有 Candidate model/gate/service/records 相邻回归为 30 passed，compileall/diff check 通过；没有 migration、
  Repository、materializer、API 或外部调用。
- 下一动作切换为 Task 2 materializer pure contract/Fake writer 边界。

## 2026-08-20：6B-6 本地纵向切片完成，进入公共验证前审查

- Task 2 完成三个 materializer + 同一事务 writer port；错误 kind 零调用、无 commit/rollback 依赖和异常传播
  聚焦通过。Task 3 完成三张 ORM 表、0006 可逆 migration、partial unique、复合 FK 与 insert/update trigger；
  离线 SQL 可生成，真库仍待 CI。
- Task 4 完成 PostgreSQL advisory lock、active row lock、expected-version、supersede/insert、source replay；
  typed payload/version 冲突映射为 422/409 且 Candidate 保持 pending。真库首写、历史、并发 stale writer、
  rollback 与 direct SQL trigger 合同已加入阻塞 job。
- Task 5 将完整不可变 materializer registry 接入 production lifespan；Task 6 完成 owner-scoped
  Preference/Profile/Review active/history GET，Profile 对 observed/cross-owner 安全 not-found，无 target PATCH。
- package smoke 升级为 Candidate pending→accept→Preference active query，结果 schema 1.3；仍强制
  `external_riot_provider_calls=0`。旧 migration-head 与 OpenAPI exact-path 测试已同步到 0006/三个新 GET。
- 当前聚焦/相邻为 `128 passed, 19 skipped, 1 warning`；19 skip 全因本机无 PostgreSQL/Docker，不能视为
  真库/package 成功。walkthrough 和八维 evidence 已建立，coverage 保持 planned。
- 提交前复核修正 typed error disposition 曾误放在 Candidate create 异常块的问题，并新增 metrics/page
  两项纯合同与 terminal-source/supersedes-chain 两项真库合同；最终完整本地回归为
  `1402 passed, 100 skipped, 1 warning, 110 subtests passed`。相对 6B-5 公共基线新增 12 个本地 skip，
  均为 0006/typed target 真库测试。RAG development/independent holdout 指标满门槛，
  Harness dry-run `published`/0 revisions，compileall、YAML、治理、SDK/Secret/tracked-data 与 diff 门均通过。
- 下一动作是完整回归与横向门禁、最终 diff/cached review、提交推送和 exact-SHA 三 job；公共全绿前
  canonical 保持 `6B-6 / in_progress`，不得进入 6B-7。

## 2026-08-20：6B-6 首个实现 SHA 的真库测试夹具失败

- 实现提交 `da87cdeefc6b104b8f9faf3546091ec8b80c1bfb` 已推送；Actions run `32386630063` 的普通
  pytest 与 Linux package smoke 成功，PostgreSQL job 为 `141 passed, 1 failed`。
- 唯一失败发生在创建 observed `public_trend` Candidate：测试 helper 沿用默认
  `user_structured_input`，而 6B-5 Gate 既定合同只允许该 observed Review 来自确定性事实或已发布观察，
  因此 Repository 正确返回 `SOURCE_INVALID`。
- 最小修复只把该测试案例 provenance 显式改为 `deterministic_run_fact`；不放宽 Gate、schema、trigger、
  materializer 或生产事务。下一动作是聚焦验证、提交新 SHA 并等待新的三 job。

## 2026-08-20：6B-6 最小修复公共闭环与状态交接

- 修复提交 `5531c81ec7117f5c454d320e406153086baae3ea` 已推送；Actions run `32387026797`
  精确对应该 SHA，pytest、postgres-migrations、packaging-smoke 三 job 全绿。
- 公共 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；PostgreSQL 17 为
  `142 passed, 1 warning`，可逆 migration、0006 约束/trigger、并发/回滚和 metadata-head 一致性通过。
- Linux package smoke 为 schema 1.3，Candidate accepted、Preference v1=`zh-CN`，
  `external_riot_provider_calls=0`。6B-6 coverage 已置 complete。
- canonical 只交接 `6B-7-training-plan-progress` prepared/waiting authorization；本轮没有实施 6B-7。

## 2026-08-21：RQ-071 恢复并启动 6B-7 设计批

- 完成 AGENTS canonical 恢复链与 `python scripts/check_project_governance.py`，起始工作树干净，
  `HEAD == origin/main == 8fa3ac94fbcb8fa2dba0f8328124b5d4cf2b463d`。
- 用户授权连续完成 `6B-7→6B-8→6B-9`，已追加 RQ-071；不再逐步询问，但每个 checkpoint 仍须独立
  教学、设计、TDD、八维证据、本地门禁、提交/推送和 exact-SHA 三 job。
- 已完成 6B-7 初学者教学与 Candidate/gate/materializer/Task Artifact 接缝审计，新增 ADR-0044、专用
  设计和实施计划。当前没有 Plan/Progress 产品代码或测试，也没有进入 6B-8/6B-9。
- 下一动作：运行设计批本地门禁、独立提交/推送并等待 exact-SHA 公共 CI；全绿后从 pure contract 红灯开始。

## 2026-08-21：6B-7 设计批本地门禁完成

- 治理首跑因活动计划 Next Step 缺少完整机器 checkpoint 字符串得到 `1 failed, 11 passed`；只修正
  Next Step 固定格式后为 `12 passed`，治理脚本通过，未放宽规则。
- 完整本地回归 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；100 skip 仍全部来自本机
  无 PostgreSQL/Docker，设计文档不增加真库成功声明。
- RAG development/independent holdout 指标均满足全部冻结阈值，Harness 标准 fixture dry-run 为
  `published`/0 revisions；compileall、SDK boundary、tracked Secret/run-data、YAML、governance 和 diff
  门通过。首次 Harness 命令漏传两个必需 fixture，仅在 argparse 阶段退出；按 runbook 重跑成功且无外部 I/O。
- 当前本地裁决为 `pass-local-pending-public-ci`。下一动作：审查 cached diff，独立提交/推送设计批并等待
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；三 job 全绿后才写 Task 1 红灯。

## 2026-08-21：6B-7 设计批 exact-SHA 公共闭环

- 设计提交 `d678a7a93e7b5f04d5733b9c0abae4a26dc4dd1b` 已推送；Actions run `32394585411`
  精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。
- 该 run 证明 ADR/design/plan/治理与既有真实 PostgreSQL/Linux 边界兼容，不证明 Plan/Progress 产品
  代码存在。canonical 保持 `6B-7 / in_progress`，内部下一动作切到 Task 1 pure contract 红灯。

## 2026-08-21：6B-7 本地实现与完整门禁完成

- pure Plan/Progress/trend、两个 materializer、五类 production registry、两张 ORM 表、0007 migration/
  trigger、同事务 writer、final Artifact gate、owner-scoped query/Service、两个 GET 与 lifespan 已实现。
- Linux package smoke schema 1.4 真实规划为 Link→Conversation→Preference→Training Plan accept/query，
  `external_riot_provider_calls=0`；Progress 的 succeeded final Artifact gate 由真实 PostgreSQL job 证明，
  不用 package 的故意 failed Review 冒充成功 Artifact。
- 聚焦/相邻最终为 `103 passed, 6 skipped, 1 warning`；完整本地回归为
  `1445 passed, 106 skipped, 1 warning, 110 subtests passed`。新增 6 个 skip 全部是本机无 PostgreSQL，
  不能视为 migration/trigger/transaction 成功。
- 两套 RAG 满冻结阈值，Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked
  Secret/run-data、YAML、governance 与 diff 门通过。coverage 八维路径已齐但保持 planned。
- 唯一下一动作：最终 diff/cached review，独立提交/推送并等待 exact-SHA 三 job；全绿后才关闭 6B-7
  并按 RQ-071 进入 6B-8。

## 2026-08-21：6B-7 公共闭环并启动 6B-8 设计批

- `f6d89225ac5dbd568b6fad7c3c09b7c497c50762` / Actions `32397290175` 已核验 exact-SHA；三 job
  completed/success。公共 pytest `1445 passed, 106 skipped, 1 warning, 110 subtests passed`，真库
  `151 passed, 1 warning`，`alembic check` 无新 upgrade，Linux package schema 1.4/外部调用 0。
- 6B-7 coverage 置 complete；canonical 按 RQ-071 切到 `6B-8-memory-aware-context-typed-turns / in_progress`。
- 完成 ContextBuilder/Runtime/Application/Task/Conversation/typed Memory 接缝审计与三方案比较；采用
  run-scoped decorator、server-derived binding、legal snapshot、body-free manifest 与 terminal writer。
- 新增 ADR-0045、专用 design/implementation plan；当前没有 6B-8 产品代码。下一动作是设计批本地门禁、
  独立提交/推送和 exact-SHA 三 job，全绿后开始 pure contract 红灯。

## 2026-08-21：6B-8 设计批本地门禁完成

- 完整 pytest `1445 passed, 106 skipped, 1 warning, 110 subtests passed`；本机真库/Docker skip 如实保留。
- 两套 RAG 满冻结阈值，Harness dry-run published/0 revisions；compileall、governance、SDK boundary、
  tracked Secret/run-data、YAML、pip 与 diff check 全绿。
- 设计批当前为 `pass-local-pending-public-ci`；下一动作是 cached diff/独立提交/推送并等待 exact-SHA 三 job，
  不提前写 6B-8 产品代码。

## 2026-08-21：6B-8 exact-SHA 公共闭环与 6B-9 设计启动

- 6B-8 最终 SHA `aacc11a1993e9d7d660f9d8d15b761dc641954b1` / Actions `32403187972` 三 job 全绿；
  pytest `1465 passed, 112 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL `157 passed, 1 warning`，
  Linux package schema 1.5/context records 3/assistant 0/external calls 0。
- 首轮漏提交 walkthrough、非法 `MID` fixture、Task binding 与 Compose API/smoke owner 不一致均由公开门发现；
  失败 SHA 保留，只做最小修复，未放宽生产 owner/role/schema/selector。
- coverage 已置 complete，canonical 切到 `6B-9-lifecycle-export-exit-review / in_progress`。
- 已完成 6A deletion/retention 与 6B FK/query 接缝审计，新增 ADR-0046、专用 design/implementation plan；当前无
  0009 或 lifecycle/export 产品代码。下一动作是设计批本地门禁和独立 exact-SHA 公共验证。

## 2026-08-21：6B-9 设计批本地门禁完成

- 治理负例从硬编码旧 checkpoint 改为读取 canonical，12 项治理聚焦通过；完整本地 pytest
  `1464 passed, 113 skipped, 1 warning, 110 subtests passed`。
- 两套 RAG、Harness dry-run、compileall、pip、governance、SDK/Secret/tracked-data 与 diff 门全绿。
- 当前 `pass-local-pending-public-ci`；下一动作是设计批独立提交/推送和 exact-SHA 三 job，不提前写 0009。

## 2026-08-21：6B-9 本地实现与退出矩阵

- `app/lifecycle`、0009、集中式 PostgreSQL Repository、薄 API/composition 与 package 1.6 已完成。
- package 先导出 Conversation/Message/Preference/Plan，再做 `conversation_only`；预期 Message/Conversation
  不可见而 Preference/Plan 保留，外部调用为 0。
- 0009 offline SQL 审计捕获并修复 CHECK naming convention 双前缀；所有已展开 CHECK 名都用 `op.f()`。
- 首轮完整回归 `1488 passed, 117 skipped, 1 warning, 110 subtests`，唯一失败是第二处 OpenAPI path
  allowlist 未加入新 endpoint；同步后最终完整回归 `1489 passed, 117 skipped, 1 warning, 110 subtests`。
- walkthrough 已覆盖八维与 Session/Memory V1 exit matrix；公共 exact-SHA 三 job 前不关闭 coverage/阶段 6。

## 2026-08-21：6B-9 exact-SHA 公共闭环与阶段 6 收尾

- 设计 SHA `4bdb1bb9e720bd853c677ce2f650476f19ab6e41` / Actions `32404203265` 已先独立
  完成三 job 公共门。
- 实现 `2e37bd4e156d750634d67d64c07ddb4784f048f4` / Actions `32407862496` 的 pytest/package
  成功，真库 `163 passed, 1 failed`；失败夹具非法逆转 hidden Conversation，数据库正确拒绝。
- 最小测试修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` / Actions `32408101770` 的三 job
  completed/success。公共 pytest `1490 passed, 116 skipped, 1 warning, 110 subtests passed`；真库
  `164 passed, 1 warning`，0009 可逆、metadata=head；Linux package schema 1.6 完成 export/delete/survival
  断言，输出 `external_riot_provider_calls=0`。
- 6B-9 coverage 已 complete；Session/Memory V1 与阶段 6 正式关闭。canonical 只交接
  `stage-7-standard-mcp-dynamic-meta-entry-design` prepared/waiting authorization，不开始阶段 7 工作。

## 2026-08-21：RQ-072 开始 Stage 7 入口设计

- canonical 已恢复为 `stage-7-standard-mcp-dynamic-meta-entry-design / in_progress`，等待授权原因已清除；
  当前仅做教学、接缝审计、方案比较和设计资产，不实现产品 MCP/Meta、不安装 SDK、不读取 Key、不执行外部 I/O。
- 已新增 ADR-0047、Stage 7 entry design、implementation plan 与八维学习材料；冻结 Adapter-first、
  `MetaEvidence`、OP.GG 条件准入、RiftCoach 受限 Server 和 7-1…7-5 原子顺序。
- coverage 保持 `planned`，因为没有 MCP 产品代码、OP.GG 准入证据或真实外部 Server/Client 互操作；既有
  ToolRuntime/Application/Context/Harness 测试仍是兼容性基线。
- 当前唯一下一动作：完成治理、完整回归、横向安全/数据门和 exact-SHA 三 job 设计闭环；公共全绿后才进入
  `7-1-mcp-client-contract` pure TDD。

## 2026-08-21：Stage 7 入口设计 exact-SHA 公共闭环

- 设计提交 `e50a54618157c84a545ad5786e6c820502f967ee` / Actions `32436092074` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全绿；入口设计正式关闭。
- 公共 pytest 与本地完整基线分别为 `1489 passed, 117 skipped, 1 warning, 110 subtests passed`；本机
  skip 不外推为真实 PostgreSQL/部署证据。入口设计仍无 SDK、MCP 产品代码、Key 或外部调用。
- coverage 八维已置 complete；canonical 交接 `7-1-mcp-client-contract` prepared/waiting authorization，
  新增 sequence 250 与治理 canonical order。授权前不开始 pure TDD。

## 2026-08-21：RQ-073 授权并开始 7-1 pure TDD

- 用户“继续下一步”已记录为 RQ-073；canonical 清除 pause reason，唯一 checkpoint 保持
  `7-1-mcp-client-contract / in_progress`。
- 已按恢复顺序复核 requirements、roadmap/history/amendment、capability、learning ledger、ADR-0005/0047、
  Stage 7 design/implementation plan 与现有 Tool/Provider strict contract 接缝；治理预检通过，起始工作树 clean，
  `HEAD=origin/main=28ef28103475d9d33df153c77b09ca51c0f0de85`。
- 初学者边界已固定：envelope 判断消息是否合法，transport 决定消息如何到达；7-1 只做前者。控制流为
  initialize/version → tools capability → bounded list snapshot → allowlist/schema checked call → safe result/error。
- 当前唯一动作是创建 `tests/test_mcp_contracts.py` 并确认 ImportError 红灯，然后最小实现 `app/mcp` pure models/errors；
  不安装 SDK、不读 Key、不调用外部服务、不进入 7-2。

## 2026-08-21：7-1 本地实现完成，等待 exact-SHA 公共门

- 红灯在 `ModuleNotFoundError: app.mcp` 处确认；`app/mcp/{models,errors,__init__}.py` 与
  `tests/test_mcp_contracts.py` 随后以小步绿灯实现。审查又补标准 annotations、argument bytes、catalog/server
  drift 与 repr body safety，没有引入 SDK/transport/external I/O。
- 最终聚焦 `20 passed, 17 subtests passed`；相邻 Tool/Provider contracts `55 passed, 62 subtests passed`；
  完整回归 `1509 passed, 117 skipped, 1 warning, 127 subtests passed`。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation 均 1.0；
  Harness dry-run published/0 revisions；compileall、pip、YAML、governance、SDK boundary、tracked Secret/run-data
  和 diff check 通过。
- `docs/learning/7-1-mcp-client-contract-walkthrough.md` 已覆盖八维 evidence；coverage 仍 `planned`，因为实现
  exact-SHA 三 job 尚未运行。唯一下一动作是 cached diff→独立提交/推送→等待公共三 job；不进入 7-2。

## 2026-08-21：7-1 exact-SHA 公共闭环

- 实现 SHA `37f16bc54de1d6e41c3ae65ddc9d9c5e11efa4cb` / Actions `32439753589` 三 job
  completed/success；pytest `1510 passed, 116 skipped, 1 warning, 127 subtests passed`，真库
  `164 passed, 1 warning`，package schema 1.6 且外部 Riot/Provider 调用 0。
- coverage 已置 complete，RQ-073/roadmap/history/decisions/capability/learning/canonical 已同步关闭 7-1。
- 唯一下一检查点为 `7-2-mcp-transport-and-discovery` prepared/waiting authorization；当前停止，不写 7-2。

## 2026-08-21：RQ-074 授权 7-2 transport/discovery

- 用户明确“继续7-2”，等待原因清除；canonical 唯一检查点保持
  `7-2-mcp-transport-and-discovery / in_progress`。
- 已复核 7-1 pure models/errors、ToolDefinition/ToolRegistry/ToolRuntime 接缝，并运行治理预检通过；
  先写 `tests/test_mcp_transport.py` 红灯，再实现 in-memory 与隔离 stdio session/discovery。
- 本批边界冻结为 no SDK/no Key/no OP.GG/Riot/Provider/no MetaEvidence/no MCP Server/no ordinary HTTP；
  fixture/subprocess 仅证明本地 transport 合同。

## 2026-08-21：7-2 本地 TDD 实现完成

- 首轮红灯为 `ModuleNotFoundError: app.mcp.client`；随后新增 `McpClientSession`、
  `InMemoryMcpTransport`、有界 JSONL `StdioMcpTransport` 与 allowlisted transport/session errors。
- 7-2 聚焦 `11 passed`；7-1 合同、7-2 与 ToolRuntime 相邻集合为 `43 passed, 17 subtests passed`。
- 已覆盖 initialize/list/call trace、capability gate、cursor 分页、schema refresh、disconnect/restart、
  总 deadline、stdio malformed/timeout 和 Runtime retry 单一所有权；适配器不复制 retry/cache/breaker/fallback。
- 八维 walkthrough 已写入 `docs/learning/7-2-mcp-transport-and-discovery-walkthrough.md`，coverage 在
  exact-SHA 三 job 前保持 `planned`。当前本地实现仍不接 SDK、普通 HTTP、OP.GG、Meta、Server、Key 或外部 I/O。
- 下一动作：完整本地门禁与最终 diff 审查，独立实现提交/推送并等待 exact-SHA 三 job；公共全绿后才关闭 7-2，
  再只登记 7-3 prepared/waiting authorization。

## 2026-08-21：7-2 exact-SHA 公共闭环与 7-3 交接

- 实现 SHA `f12166665d437a9479afff508709435a23096dd2` / Actions `32441793585` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 run 完成 exact-SHA 验证。
- 7-2 coverage 已置 complete，canonical 切换为 `7-3-opgg-meta-adapter / prepared/waiting authorization`。
- 公共证据仍只证明本地 transport/session/discovery 与既有真库/Linux package 基线兼容；不证明 OP.GG、
  MetaEvidence、RiftCoach MCP Server、真实外部互操作或公网部署。

## 2026-08-21：RQ-075 授权 7-3 并开始候选准入审计

- 用户确认官方候选仓库后明确继续；canonical 已清除 waiting 状态，唯一 checkpoint 保持
  `7-3-opgg-meta-adapter / in_progress`。
- 治理预检通过，起点工作树 clean，`HEAD=origin/main=9bab4d7b3053c772ad52ac1a08d6cc4d947cf641`。
- 本批先审计官方 endpoint/protocol/transport/schema/license/freshness/rate-limit/deployment；准入通过后才写
  MetaEvidence 红灯。有限候选探针不算 7-5 双向互操作，Key/Riot/LLM Provider 和 Memory 写入保持 0。

## 2026-08-21：RQ-076 修正为真实接入与分级 provenance

- 真实探针已通过 initialize `2025-06-18`、tools/list 和一次只读幂等 lane-meta tools/call；这证明 OP.GG
  标准 MCP 可达，不应因 provenance 不完整直接拒绝集成。
- 当前 18 个 LoL 工具均无 outputSchema；目标工具返回 text、无 structuredContent/current patch/source
  generated_at/TTL，DELETE 为 405。修正后的实现锁定 schema/字段并用安全 grammar 解析，以本地 retrieval
  TTL 标记缓存时效，同时把上游 patch/freshness 保持 unknown。
- admission fixture 已改为 `admitted_with_restrictions`；允许 current snapshot recommendation，禁止精确
  patch/历史比较/上游 freshness 声明。下一动作是 Streamable HTTP 与 MetaEvidence TDD。

## 2026-08-21：7-3 本地产品链与真实 body-free smoke

- 新增 HTTPS-only Streamable HTTP transport、initialized notification、session/JSON/SSE/大小/安全错误；
  OP.GG 远端 underscore 名映射到固定本地 `opgg.lane_meta_champions`，可靠性仍由 ToolRuntime 所有。
- 新增 partial `MetaEvidence`、typed lane facts、15 分钟本地 expiry、用途门和无 eval 的 allowlisted AST parser；
  注入、非法 rate/重复 rank、schema drift、超限和过期均 fail closed。
- Context 新增 `external_meta_evidence`，只接受 optional `meta:` user-role data section，不写 Memory/Candidate/
  Plan/Progress，也不覆盖 Riot 官方事实。RQ-077 已将 Riot 版本/静态/patch 与 OP.GG 分层融合边界持久化。
- 首次真实产品 smoke 暴露未获准 Valorant 数组 outputSchema 阻断全目录的问题；修复为“总量资源门 + admitted
  subset 严格解析”。聚焦/相邻当前为 `83 passed, 17 subtests passed`。
- 成功真实 smoke 只调用 lane-meta 一次并写入 body-free result；Riot/Provider/Key 为 0。ADR-0048、专用设计
  与八维 walkthrough 已建立；coverage 在完整本地门和 exact-SHA 三 job 前继续 `planned`。

## 2026-08-21：7-3 最终本地门完成，等待 exact-SHA 公共 CI

- 聚焦/相邻最终 `95 passed, 1 skipped, 17 subtests passed`；完整 pytest
  `1542 passed, 117 skipped, 1 warning, 127 subtests passed`。skip 均保持本机环境限制原义。
- 两套 RAG 指标满冻结阈值；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked
  Secret/run-data、pip、6 个 YAML、governance、body-free evidence scan 与 diff check 全绿。
- 已修正 roadmap/learning/ADR/decisions 的当前状态旧句，明确 7-3 的真实单向 OP.GG 调用不等于 7-5
  双向互操作；coverage 继续 planned。
- 唯一下一动作：最终 cached diff，独立提交/推送并等待 exact-SHA 三 job；公共全绿前不关闭 7-3，
  不进入 7-4/7-5。

## 2026-08-21：7-3 恢复后的最终审查补强

- 从未提交工作树恢复后先重跑 governance，并审查 transport/session、selected catalog、strict parser、
  MetaEvidence、Context 和持久 smoke 接缝；没有重复真实外部调用。
- 四个提交前 edge case 均先以红灯确认：server-negotiated protocol header、拒绝字符串 rate、未获准畸形
  descriptor 不阻断获准工具、complete provenance 必须有 patch/source time；相关集合
  `94 passed, 17 subtests passed`。
- 最终完整 pytest 为 `1545 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG 满阈值，Harness
  dry-run `published`/0 revisions，compileall、pip、全部 YAML、SDK boundary、tracked Secret/run-data、
  body-free evidence 与 governance 再次通过。
- coverage 继续 planned；唯一下一动作仍是独立 cached diff、提交/推送与实现 exact-SHA 三 job，不进入 7-4/7-5。

## 2026-08-21：RQ-078 授权并启动 7-4 Server

- 7-3 `64311a1` / Actions `32455219404` 已完成 exact-SHA 三 job；用户“继续完完整整开发”授权当前
  唯一 checkpoint `7-4-riftcoach-mcp-server`，pause_reason 已清除。
- 已完成 Server 初学者边界与 Application/ActorContext/DTO/Harness 接缝审计；冻结 strict
  protocol/session → owner-scoped read-only Facade，四个工具和拒绝字段；不进入 7-5。
- 当前下一动作：先写 `tests/test_mcp_server.py` external-client fixture 红灯，再实现
  `app/mcp/server.py` 与最小 composition seam。

## 2026-08-21：7-4 本地实现与全部门禁完成

- 新增 transport-neutral Server Session、in-process transport、固定四工具 catalog、owner-scoped Query
  Facade 和最小 service-port composition；不监听网络、不直连 Repository、不读取 Key。
- Product Query 新增 verified recent aggregate DTO 与 single-match published digest；Skill/publication、
  receipt/Trace/manifest/input digest/Artifact file 任一漂移均 body-free fail closed。
- 聚焦 `33 passed`；相邻 MCP/Product `109 passed, 17 subtests passed`；完整回归
  `1566 passed, 117 skipped, 1 warning, 127 subtests passed`。117 skip 仍是本机 PostgreSQL/Docker/Linux 限制。
- RAG development/holdout 满阈值，Harness dry-run `published`/0 revisions；compileall、pip、6 YAML、SDK
  boundary、tracked Secret/run-data、body-free MCP evidence、governance 与 diff check 全绿。
- walkthrough 已覆盖八维，coverage 保持 planned。唯一下一动作是最终 diff/cached review、独立提交/推送和
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；三 job 全绿前不关闭 7-4、不进入 7-5。

## 2026-08-21：7-4 exact-SHA 公共闭环与 7-5 准备态

- 实现提交 `431c584c6f07731233e6e32fd6f98505a661f910` 已推送；Actions run `32480827952`
  精确对应该 SHA，三个 job 全部 completed/success。
- 公共 pytest `1567 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`、migration metadata=head；Linux package schema 1.6 且外部调用 0。
- 7-4 coverage 已 complete。canonical 交接 `7-5-mcp-interoperability-exit-review`
  prepared/waiting authorization；当前不实施真实外部 Client、双向互操作或 Stage 7 exit review。

## 2026-08-21：RQ-079 授权并启动 7-5

- 用户明确“那继续7-5”；canonical pause 已清除，唯一 checkpoint 保持
  `7-5-mcp-interoperability-exit-review / in_progress`，不进入 Stage 8。
- governance 起点通过，工作树起始 clean，`HEAD=origin/main=4fc062656094e34de4946c698929229850499788`。
- 已审计官方 MCP SDK `1.30.0`/MIT/Node>=18 与 newline-delimited stdio wire；设计选择隔离 Node Client
  → Python RiftCoach stdio Server，并保留 RiftCoach Client → OP.GG Streamable HTTP 的真实另一方向。
- 下一动作是完成 ADR/专用设计与测试红灯；外部调用必须等离线实现和门禁稳定后再执行，且只允许一次
  有界 body-free 证明。

## 2026-08-21：7-5 本地实现与全部离线门完成

- ADR-0050、专用设计、八维 walkthrough、官方 SDK 1.30.0 lock、stdio Server、no-I/O restricted runner、
  external Client 与 clean-SHA exit/evidence validator 已完成；不增加 Python 产品或 Docker runtime 依赖。
- TDD 红灯与协议协商 Bad Case 已留痕；最终聚焦 `10 passed`，相邻
  `74 passed, 17 subtests passed`，完整 `1576 passed, 117 skipped, 1 warning, 127 subtests passed`。
- RAG development/holdout 全指标 1.0/FPR 0，Harness `published`/0 revisions；compileall、pip、Node syntax、
  npm ci/audit、6 YAML、governance、tracked Secret/run-data、body-free evidence 与 diff check 全绿。
- coverage 保持 planned；当前没有新 OP.GG/Riot/Provider/Key 调用。唯一下一动作是 cached diff review、
  独立实现提交/推送与该 exact SHA 的三 job；公共全绿后在 clean SHA 上执行一次双向真实门。

## 2026-08-21：7-5 实现 exact-SHA 与真实双向门通过

- `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 的 pytest、
  postgres-migrations、packaging-smoke 全部 completed/success；公共 pytest 1577/116 skips，真库 164，
  package schema 1.6/外部调用 0。
- 同一 clean SHA 的官方 SDK→RiftCoach stdio 与 RiftCoach→OP.GG Streamable HTTP 均通过；两侧各 1 次
  tools/call、Riot/Provider/Key 为 0。OP.GG 仍为 partial provenance，不伪造 patch/freshness。
- 已生成 `data/evaluation/results/mcp/stage7_interoperability_exit_v1.json`，body-free、SHA-bound、不可覆盖。
  当前只提交证据/自动验证/退出材料；coverage 与 Stage 7 在证据 SHA 公共三 job 前继续 open。
- 证据批提交前聚焦 interoperability/governance 为 `23 passed`；compileall、6 YAML、body-free 持久
  evidence validator、治理脚本与 `git diff --check` 全绿。首次治理红灯只因人类可读下一步漏写 canonical
  checkpoint 名，已补为同一 `7-5-mcp-interoperability-exit-review`；本批未重跑 OP.GG 门或发生新外部 I/O。

## 2026-08-21：7-5 evidence exact-SHA 公共闭环与 Stage 7 关闭

- `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736` 三 job completed/success；
  公共 pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`，真库 `164 passed, 1 warning`，
  package schema 1.6/外部调用 0。
- 7-5 coverage 已置 complete，Stage 7 关闭；canonical order/ledger 增加
  `stage-8-multi-agent-reliable-runtime-productization-entry-design` planned。
- 当前只完成独立状态收尾并等待该状态 SHA 的 exact-SHA 三 job；Stage 8 仍 prepared/waiting authorization，
  没有运行 OP.GG/Riot/Provider、读取 Key 或实现任何 Stage 8 产品代码。
- 状态批最终本地回归 `1577 passed, 117 skipped, 1 warning, 127 subtests passed`；聚焦 governance/
  interoperability `23 passed`，compileall、6 YAML、governance 与 diff check 全绿。117 skip 继续只表示
  本机 PostgreSQL/Docker/Linux 环境限制，真实真库/package 证据由公共 job 提供。

## 2026-08-22：Stage 8 entry design 本地收尾准备

- 恢复顺序复核确认 canonical 唯一检查点为
  `stage-8-multi-agent-reliable-runtime-productization-entry-design`，RQ-080 已授权；没有开始 8A–8F
  产品实现。
- 已完成 Stage 8 初学者教学、Runtime/Task/Harness/Memory/MCP/Riot/Data Dragon/OP.GG 接缝审计，冻结
  8A–8F、8-Core/8-Advanced 双轨、证据驱动 Multi-Agent 采用门、Riot+OP.GG EvidenceBundle 分层，及
  五模块 React 前端蓝图与 MotionSites/离线 Excel 逐项资源采用门。
- 修正当前状态、路线、路线修订、项目决策和 coverage 的旧“尚未开始设计/仅准备态”镜像；entry-design
  coverage 仍保持 `planned`，但八个维度已绑定有效 ADR/计划/教学 Markdown，等待公共闭环后再改 `complete`。
- 当前下一动作：运行完整本地门禁，复核 diff，独立提交/推送 entry design，并等待该 SHA 的
  `pytest`、`postgres-migrations`、`packaging-smoke` exact-SHA 公共 CI。

## 2026-08-22：Stage 8 entry design exact-SHA 公共闭环

- `3431e8b47dd992b6c4741e12158855feb64ef917` / Actions `32564500421` 的 pytest、
  postgres-migrations、packaging-smoke 全部 completed/success。
- 公共 pytest `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6、外部调用 0。
- entry-design coverage 已置 complete；Phase 32 关闭。唯一下一检查点为
  `8a-advanced-adoption-gate` prepared/waiting authorization，本批停止且未写 Stage 8 产品代码。
- 当前只剩状态收尾提交/推送及其 exact-SHA 三 job；全绿后本轮正式结束。

## 2026-08-22：RQ-081 授权与 8A 本地 TDD

- 用户明确“开始”，RQ-081 只授权 `8a-advanced-adoption-gate`；8B–8F 继续 deferred。
- ADR-0052、专用设计/实施计划、3 development + 3 calibration-excluded holdout synthetic cases、
  strict gate JSON、Pydantic evaluator 与八维 walkthrough 已建立。
- 首次 TDD 在 collection 阶段以 `ModuleNotFoundError: app.evaluation.stage8_adoption` 红灯；最小实现后
  聚焦 `14 passed`。提交前 strict-contract 复核新增 6 个负例，实际先得到 `6 failed, 14 passed`，
  锁定 duplicate JSON key、baseline kind、active candidate registry 和 exact role contract 后为 `20 passed`；
  AgentLoop/Runtime/Context/OP.GG Meta/Harness 相邻集合 `129 passed`。
- cached diff 公平性复核再新增第二 baseline、串行 baseline role、普通并行 comparator role 三个负例，
  实际先得到 `3 failed, 20 passed`；锁定唯一 baseline 和三路 exact role contract 后最终 `23 passed`。
- gate 固定 `single-runtime-serial-v1` baseline、`bounded-parallel-evidence-v1` comparator、
  `role-isolated-multi-agent-v1` primary candidate；DAG/Agentic Retrieval deferred。
- case-set SHA 为 `d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e`，gate digest 为
  `88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；未执行 holdout、真实 I/O 或 Provider。
- coverage 继续 planned；下一动作是完整本地门禁、diff/cached diff 审查、独立提交/推送和 exact-SHA
  三 job。公共闭环前不关闭 8A、不实现或运行 8B。

## 2026-08-22：8A 完整本地门禁通过

- 完整 pytest `1600 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 仅为本机无
  PostgreSQL/Docker/Linux 条件，真实真库和 Linux package 仍等待公共 job。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation
  均 1.0；Harness dry-run `published`/0 revisions。
- compileall、pip、6 YAML、SDK boundary、tracked Secret/run-data、governance 与 diff 门通过；stale phrase
  扫描命中均为 append-only 的历史 8A handoff，并由后续 RQ-081 本地实现记录明确取代。
  本批外部 Riot/OP.GG/Provider/Key I/O 仍为 0，holdout executions 为 0。
- 唯一下一动作：完整/cached diff 终审、独立 implementation 提交/推送并等待 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke`。公共全绿前 coverage planned，不进入 8B。

## 2026-08-22：8A implementation exact-SHA 公共闭环

- implementation `12ad83532d99990f5523d6ecc6def0b8a325d7d0` 已推送；Actions `32567642315`
  精确对应该 SHA，三个阻塞 job 全部 completed/success。
- 公共 pytest `1601 passed, 116 skipped, 1 warning, 127 subtests passed`；RAG 两套门、Harness
  published/0 revisions、compileall、SDK/secret/tracked-data 边界均通过。
- PostgreSQL 17 真库 `164 passed, 1 warning`，0001→0009 upgrade/downgrade/upgrade 可逆且
  `alembic check` 无新 upgrade；Linux package schema 1.6、外部 Riot/Provider 调用 0、image boundary 通过。
- 8A coverage 已置 complete。canonical 只前移到 `8b-conditional-multi-agent-experiment`
  prepared/waiting authorization；当前只做独立状态收尾提交与其 exact-SHA 三 job，不实现或运行 8B。
- state-only 收尾本地完整回归 `1600 passed, 117 skipped, 1 warning, 127 subtests passed`，治理聚焦
  `35 passed`；治理首次准确拦住陈旧 Next Step 和 0 个 in_progress phase，修正机器状态后全绿，
  Phase 34 正文仍明确 waiting authorization/未实现。

## 2026-08-22：RQ-082 授权 8B 并冻结设计

- 用户明确“继续推进”，授权唯一 checkpoint `8b-conditional-multi-agent-experiment`，不要求逐小步重复审批；
  canonical 清除 waiting authorization，保持 `in_progress`。
- 专用设计选择 evaluation-only Scripted/Fake 角色 + fixture 工具 + 真实 `ReviewHarness`；拒绝真实 Provider/MCP
  和产品 Runtime 改造，避免把模型/网络变量混入架构比较。
- 三路固定为 serial baseline、bounded-parallel comparator、role-isolated Multi-Agent candidate；只有 evidence
  acquisition/Context isolation 可变，Coach/Harness/fixture/阈值/Usage 模型保持一致。
- 一次性生命周期固定为：TDD/development/preflight → implementation exact-SHA 公共 CI → clean SHA development
  admission → 唯一 holdout → result/ADR/evidence 提交与第二次 exact-SHA 公共 CI。
- 当前 holdout executions 和 external I/O 仍为 0；下一动作是按实施计划先写 runner/lifecycle 红灯。

## 2026-08-22：8B runner/lifecycle 本地 TDD 通过

- 首次聚焦测试因 `app.evaluation.stage8_experiment` 不存在形成 2 个 collection error；最小实现后
  `14 passed`，没有把先写代码冒充 TDD。
- isolated evaluation package 已实现三路 acquisition、typed/digest-bound references、Scripted Usage、
  同一 Coach/Evaluator/zero-revision Config 与真实 `ReviewHarness`；产品 Runtime/Harness 未修改。
- lifecycle/CLI 现在绑定 clean code SHA = confirmed public-CI SHA；development result、holdout admission、
  预期 experiment ID 和正式 output 均不可覆盖。结果复读重算 identity、exact role、Artifact binding、
  Token/calls、metrics/verdict，并拒绝 duplicate JSON key。
- synthetic holdout-path 只用重标记 development 副本，发现并修复了跨角色 tool probe 时串行路径先产生
  Knowledge Artifact 的原子性缺口；现在所有路径均先整批预检，零工具副作用失败。正式 holdout 仍为 0 次。
- 最终聚焦 `22 passed`；8A/Harness/Context/AgentLoop/OP.GG Meta/Runtime 相邻集合
  `168 passed, 12 subtests passed`。下一动作是完整本地门禁、最终 diff 审查和实现提交/public CI。

## 2026-08-22：8B 实现完整本地门禁通过

- 完整 pytest `1622 passed, 117 skipped, 1 warning, 127 subtests passed`；skip 只保留既有本机环境限制，
  PostgreSQL/Docker/Linux 证据仍必须由公共阻塞 job 提供。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation
  均 1.0；Harness dry-run `published`/0 revisions。
- compileall、pip check、39 YAML、Harness SDK boundary、tracked Secret/run-data、governance 与 diff check
  全绿。测试生成物均在 ignored `tmp/`/pytest temp；正式 8B holdout result 不存在。
- coverage 保持 planned；当前只允许实现 diff/cached diff、提交/推送与 exact-SHA 三 job。公共全绿前
  development admission 和 holdout 均不得执行。

## 2026-08-22：8B 实现公共门、development 与唯一 holdout

- implementation `180bc8b452603572d010b6e25b14ed71f6470ce7` / Actions `32572085065` 三 job
  completed/success：公共 pytest `1623 passed, 116 skipped, 1 warning, 127 subtests passed`；真库
  `164 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6、外部调用 0。
- HEAD/origin/main/工作树精确一致后，development 唯一执行并得到 `eligible_for_holdout`；候选 latency
  improvement 27.05%、Token ratio 1.45、extra calls/例 2、match/safe degraded 1.0。
- 随后 holdout 在 case 前预留正式路径并唯一执行一次；strict 复读为 `reject_multi_agent`。候选 latency
  18.95% 未达 20%，普通并行为 22.88%，两者 isolation 均 1.0，因此没有增量收益。
- result SHA 为 `94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8`，experiment ID
  `0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494`；hard gates/retry/external I/O 0。
- ADR-0053 拒绝产品采用角色隔离 Multi-Agent，保留 evaluation assets，并把普通受限并行作为 8D 优先设计
  输入。新增结果回归后聚焦 `25 passed`；coverage 仍 planned，下一动作是 evidence 提交/public CI。

## 2026-08-22：8B result/evidence 提交前门禁

- 三个冻结结果回归锁定 exact result SHA/code/public-CI/experiment identity、三路 holdout metrics、逐案例
  terminal/preserved Artifact、hard gates 和 body-free 字段；聚焦总数 `25 passed`。
- 完整本地 pytest `1625 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG、Harness dry-run、
  compileall、pip、39 YAML、SDK/Secret/tracked-data、result body-free、governance 与 diff check 全绿。
- 正式结果仍是同一个 20107-byte 不可覆盖文件，SHA `944258...445e8`；测试只复读，没有再次执行 holdout。
- 唯一下一动作是独立 result/ADR/evidence cached diff、提交/推送和 exact-SHA 三 job；coverage 保持 planned。

## 2026-08-22：8B exact-SHA evidence 公共闭环与 8C 交接

- result/ADR/evidence 提交 `783a329537682b5413d74af4cc3e1ac818f75da2` / Actions `32572610725` 三 job
  completed/success；公共 pytest `1626 passed, 116 skipped, 1 warning, 127 subtests passed`，真实
  PostgreSQL `164 passed, 1 warning`，Linux package schema 1.6/外部调用 0。
- 8B 八维 coverage 置 `complete`，ADR-0053 的 `reject-role-isolated-multi-agent / prefer-bounded-parallel-evidence-design`
  成为最终产品裁决；8B 不修改产品 Runtime。
- canonical 已只交接 `8c-reliable-runtime-core` prepared/waiting authorization；8C 未获授权、未实现、未开始。

## 2026-08-22：RQ-083 授权并启动 8C 设计

- 用户明确“继续啊，咋停了”，授权唯一 checkpoint `8c-reliable-runtime-core`；canonical 已清除 waiting authorization。
- 本批先完成初学者教学、Task/Worker/Runtime/Harness 真实接缝审计、方案比较、ADR、专用设计与实施计划，
  再从 pure contracts 红灯开始；无需逐小步重复审批，但每批仍保持 TDD 和比例验证。
- 8B 唯一 holdout result/SHA 保持不可覆盖且不重跑；不进入 Multi-Agent、DAG/第三方 Runtime、SSE/前端、
  8D Riot+OP.GG fusion 或真实 Provider/Riot/OP.GG I/O。

## 2026-08-22：8C 设计批本地门禁完成

- ADR-0054、专用设计与实施计划已冻结 PostgreSQL 增量可靠控制面、task event/Runtime Trace 分工、
  generation+private-token fencing、持久 cancel、safe checkpoint/Receipt recovery 和 conservative limitations。
- 治理聚焦 `12 passed`；完整 pytest `1625 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 仍只
  表示本机无 PostgreSQL/Docker/Linux 条件，不能冒充真库/package 成功。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0；holdout abstention/citation 均 1.0；
  Harness dry-run `published`/0 revisions。compileall、pip、6 YAML、SDK/Secret/tracked-data、governance 与 diff 门通过。
- 首次 YAML 扫描因 PowerShell 引号截断 Python `-c` 表达式产生 `IndentationError`，没有文件变化；修正为单引号
  外壳后 `yaml_ok=6`。当前唯一下一动作是独立设计提交/推送与 exact-SHA 三 job；公共全绿前不写 0010 或产品红灯。

## 2026-08-22：8C 设计 exact-SHA 公共闭环，进入 pure TDD

- 设计提交 `3ac12a35f75db8dc28021614a0a9828607ff7a59` / Actions `32575190136` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- 该公共证据只证明 ADR-0054、专用设计、实施计划与现有基线兼容，不证明 event/lease/fencing/cancel/
  checkpoint/recovery 已实现。当前下一动作是 Task 1 pure contracts/projector 红灯；暂不创建 0010 migration。

## 2026-08-22：8C Task 1–6 本地实现与 evidence 收尾

- 已实现 strict reliable contracts/projector、0010/ORM、Repository event/lease/fencing/cancel/replay、
  lease-aware Worker、Receipt/checkpoint-proven recovery 和 owner-scoped cancel/event API；公共 event DTO
  不暴露 operation identity，package smoke 显式查询 body-free event replay。
- 红灯证据包括缺模块/Recovery/API、event 时间篡改、`recovery_required` status 宽度、Worker cancel-terminal
  竞态和 queued cancel lifecycle；最后的 API/privacy + package replay 补强先为 `2 failed`，后为 `29 passed`。
- 最新完整本地 pytest `1670 passed, 133 skipped, 1 warning, 127 subtests passed`；skip 只说明本机无
  PostgreSQL/Docker/Linux 条件，真库和 package 仍需 public CI。
- 八维 walkthrough 与 coverage 路径已补齐，coverage 继续 `planned`。下一动作是全部横向门、cached diff、
  独立 implementation/evidence 提交和 exact-SHA 三 job；不进入 8D。

## 2026-08-23：8C PostgreSQL CI 修复本地收尾

- 公共 run `32579514636` 日志确认 migration downgrade 约束名双前缀与 queued JSONB `null` 两个根因。
- `_drop_reliable_task_constraints()` 已统一 `op.f(...)`；`ReviewTaskRecord.checkpoint_reference` 已设置 `JSONB(none_as_null=True)`。
- 新增离线 downgrade 名称、metadata 与真实 queued insert 回归；完整 pytest `1672 passed, 134 skipped, 1 warning, 127 subtests passed`。
- RAG development/holdout、Harness dry-run、compileall、pip、SDK/Secret/tracked-data、governance、diff 全绿；真实 PostgreSQL/Linux 仍待公共 repair SHA。

## 2026-08-23：8C 第二轮公共 CI 发现与修复

- repair run `32584144522` 的 migration downgrade 与 pytest 已通过；真库发现既有终态没有 heartbeat、strict checkpoint JSON 读回失败，package claim 也因此未形成成功证据。
- lifecycle CHECK 已改为仅运行期状态要求 heartbeat；Repository 通过 `model_validate_json` 解析 JSONB checkpoint；新增 strict JSON round-trip 回归。
- 该轮修改尚未提交；修复后需重新跑完整本地门并推送新的 exact-SHA。

## 2026-08-23：8C 第三轮真库修复

- `b2b4737/32584944802` 已证明 migration downgrade 与 pytest 通过，真库失败从 34 降为 2；剩余 recovery requeue 的 strict JSON 读回与既有测试导入问题已修复。
- package smoke 已推进到 event query；Repository task/event/requeue 三条路径统一 strict JSONB parser，并处理 psycopg `Jsonb` wrapper。
- 最新修复待提交，coverage 仍 planned。

## 2026-08-23：8C 第四轮 event JSONB 修复

- 最新公共 SHA 的 pytest 与 PostgreSQL job 已全绿，package smoke 只剩 event replay query；event checkpoint 的 JSONB `None` 映射已与 task row 统一为 SQL `NULL`。
- 本轮为无 schema 变更的最小 ORM 修复，待提交/推送后重跑 exact-SHA 三 job。
- 为避免继续猜测，package smoke 增加 status/code/JSON-key-only 的 body-free diagnostics；下一次公共日志用于区分 API error 与 response shape。

## 2026-08-23：8C clean implementation 公共闭环与状态收尾

- 真库 Repository 诊断返回合法 `TaskEventPage`（6 events），最终根因不是 JSONB/event projection，而是
  `app/api/composition.py` 的 `_TaskServiceProxy` 没有转发 `request_cancel` 与 `read_events`；新增 composed-app
  cancel/event 回归覆盖这两个部署接缝。
- clean implementation `2df5349d85e48138c05d6293d4e3885b6b4756ec` / Actions `32587659678` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 均 completed/success；临时 body-free diagnostics 随后移除。
- 本地完整回归 `1673 passed, 134 skipped, 1 warning, 127 subtests passed`；RAG development/holdout、Harness
  dry-run、compileall、pip、SDK/Secret/tracked-data、governance 与 diff 全绿。8C coverage 可置 complete，
  canonical 只交接 `8d-riot-opgg-evidence-fusion-core / prepared / waiting authorization`。

### 2026-08-23：RQ-084 授权并启动 8D Evidence Fusion

- `AUTHORIZED`：用户明确继续正常下一步，授权 `8d-riot-opgg-evidence-fusion-core`；README 广泛研究按
  RQ-085 留到 8F 横向积累，不打断当前开发。
- `DESIGN`：ADR-0055 与 8D design/implementation plan 选择 immutable typed EvidenceBundle + pure fusion
  kernel；拒绝 JSON merge，暂缓 claim graph，no-I/O/fail-closed。
- `TDD`：首红 `ModuleNotFoundError: app.evidence`；实现 strict source/join/conflict/gap/claim/confidence、
  canonical digest、public projection 与 Summary/Data Dragon adapters 后 focused `18 passed`，相邻 `48 passed`。
- `BOUNDARY`：partial OP.GG 只支持 current snapshot，不继承 Riot patch/source time/freshness；missing/expired/
  mismatch 降级。Key、真实 Riot/OP.GG/Provider/LLM 调用和 8B holdout execution 均为 0。
- `LOCAL-GATES`：完整 pytest `1691 passed, 134 skipped, 1 warning, 127 subtests passed`；RAG development/holdout
  满阈值、Harness `published`/0 revisions、compileall/pip/YAML/governance/diff 全绿；本机 skip 不冒充真库/Linux。
- `NEXT`：独立提交/推送当前 implementation/evidence，等待 exact-SHA `pytest`、`postgres-migrations`、
  `packaging-smoke` 三 job；公共全绿前 8D 保持 in_progress，8E 未进入。

### 2026-08-23：8D exact-SHA 公共闭环与 8E 准备态

- `PUBLIC-CI`：implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions
  `32598480400` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1692 passed, 133 skipped, 1 warning, 127 subtests passed`；真 PostgreSQL 17
  `186 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6/外部调用 0。
- `CLOSED`：8D strict typed fusion、no-I/O adapters、digest/provenance/freshness/join/conflict/gap/claim、
  public projection 与八维 coverage complete。真实刷新、全部 OP.GG、React/SSE/Auth/部署仍未实现。
- `HANDOFF`：唯一下一 checkpoint `8e-productization` prepared/waiting authorization；本批停止，不开始 8E。

### 2026-08-23：RQ-086 授权 8E preflight

- `AUTHORIZED`：用户授权一次真实 Riot + OP.GG 验证并进入 8E preflight，明确前端慢慢分批推进；账号不得硬编码为 ShowMaker，必须支持自填外服 Riot ID、自己的账号和公开观察对象。
- `DESIGN`：创建 ADR-0056 与 `docs/plans/2026-08-23-8e-productization-preflight.md`；冻结 external validation、player profile selection、routing 和 legacy endpoint 审计边界。
- `OPGG-REAL`：使用项目 `.venv` 执行 `scripts/run_opgg_meta_smoke.py --execute`；真实 OP.GG initialize/list/call 通过，1 次 lane-meta 工具调用、top 3 facts、body-free digest `24b49ea9eb9c4c6c6ee682ad21309c7a643fbdde70a8ea18ba8fdf1d26a8c1ec` 已保存到 `data/evaluation/results/mcp/opgg_external_validation_2026-08-23.json`。
- `IDENTITY-AUDIT`：仓库没有 ShowMaker 硬编码；`/player-links` 已接受 Riot ID、regional routing、self/observed；Conversation 固定 player subject；旧 `/reviews/recent` 仍使用环境地区默认，列为 8E 缺口。
- `RIOT-READY`：`.env` 中 Riot Key 存在但未输出；用户授权公开核验后已用 `DK ShowMaker#KR1 / asia / observed` 完成 Account/Match gate，结果已 body-free 归档。
- `PUBLIC-CI`：preflight commit `8c0cc187e93e76c26e9d03f9e8f2371333c783a3` / Actions `32611044101` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 success；CI 仍保持外部 Riot/OP.GG/Provider/LLM 调用 0。
- `NEXT`：真实 mid replay 已暴露 `opgg_meta_result_invalid`；先做 schema-drift 诊断/回归裁决，再冻结 owner-scoped profile list/selection DTO 和首个静态/fixture-backed 前端小批。

### 2026-08-23：8E body-free schema-drift diagnostic 本地与公共闭环

- `TDD`：先加入 `null` 形状的受控失败测试，确认缺少诊断接缝后红灯；实现 `OPGGMetaSchemaDiagnostic`、字段级 AST 位置摘要与 fusion validation 的安全投影后，OP.GG/融合聚焦 `18 passed`。
- `BOUNDARY`：诊断只保存 stage、position/row、allowlisted field/index、AST node type、text length/digest；异常 `str/repr` 和持久 fixture 均不含 raw body/field value。受控 fixture 不冒充 live schema。
- `LOCAL`：完整 pytest `1695 passed, 134 skipped, 1 warning, 127 subtests passed`；compileall、governance、diff 全绿。
- `PUBLIC-CI`：`c5cbc94` / Actions `32613573022` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job exact-SHA 全绿，外部调用为 0。
- `NEXT`：若获新的有界外部授权，才重跑一次真实 mid replay 取得字段级 diagnostic；随后裁决 allowlist/degraded，再冻结 player profile selection DTO；前端仍未开始。

### 2026-08-23：RQ-086 真实 Riot 通过与 mid replay 失败证据

- `SEARCH`：AutoGLM token 服务恢复；公开搜索与 OP.GG 当前页面交叉核对 `DK ShowMaker#KR1`、KR、Dplus KIA/ShowMaker 关联；不把候选写成默认账号。
- `RIOT-REAL`：`DK ShowMaker#KR1 / asia / observed` Account-V1、recent match IDs、Match Detail 共 3 calls 通过；真实 game version `16.16.804.9184`、queue 420、MIDDLE/Akali、6/9/12、1925s；结果只保存 digest/allowlisted facts。
- `FUSION-REAL`：使用 Riot body-free result 调用一次真实 OP.GG `mid` lane-meta 并进入纯 `fuse_evidence()` 前的 adapter；远端内容触发 `opgg_meta_result_invalid`，未创建 bundle，raw body 未保存。
- `BOUNDARY`：该失败归类为真实上游内容/schema 与严格 allowlist 的差异，不修改 8D parser，不把 Riot/OP.GG 分别通过冒充两源融合通过。
- `NEXT`：安全诊断真实 mid schema drift，补 body-free regression case，再决定扩大 allowlist 或保留 degraded/unavailable；之后才冻结 player profile selection DTO 和前端小批。

### 2026-08-23：RQ-087 live diagnostic 与 JSON-null 最小修复

- `AUTHORIZED-IO`：复用既有 Riot body-free result，真实 OP.GG `mid` replay 恰好 1 次；Riot/LLM/Key calls
  均为 0，raw MCP body 未保存。结果文件为
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v2.json`。
- `LIVE-DIAGNOSTIC`：失败位置为 `Mid.rank_prev_patch` / field 7 / AST `Name`；live length/digest 与受控 fixture
  不同，证明它是新的外部观察而不是 fixture 复读。
- `TDD`：新增 nullable JSON-null 正例先以 `1 failed, 13 passed` 红灯；ADR-0058 的最小实现后 OP.GG/fusion
  聚焦 `16 passed`、MCP/Evidence 相邻 `60 passed`。`null` 只允许在 field 6/7；`NULL`、`missing`、非 nullable
  字段和可执行 AST 继续拒绝。
- `BOUNDARY`：本授权 call 已用完；完整本地/公共门正在进行。新的明确授权前不执行修复后 live replay，
  因而不把离线修复称为真实两源 bundle 已通过。
- `LOCAL-GATES`：完整 pytest `1699 passed, 134 skipped, 1 warning, 127 subtests passed`；development/holdout
  RAG 满阈值，Harness `published`/0 revisions，compileall、pip、governance、SDK/Secret/tracked-data、JSON 与
  diff 门全绿。本机 skip 不冒充真实 PostgreSQL/Linux；下一动作是独立 implementation/evidence 提交与三 job。

### 2026-08-23：ADR-0058 implementation exact-SHA 公共闭环

- `PUBLIC-CI`：`83fde7d014aae8fdccf2ebd91929967868101075` / Actions `32615340228` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1700 passed, 133 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `186 passed, 1 warning`，migration/head 一致；Linux package schema 1.6、`external_riot_provider_calls=0`。
- `EVIDENCE`：live diagnostic 文件 SHA-256 为 `796c539d04f1d2009d97af38f6248d8576f61877fd55dc12741ecb5d2195f099`；
  raw body/Key/PUUID/Match ID 未持久化。受控 fixture 明确标记为 retained pre-fix evidence。
- `NEXT`：当前 code/public-CI 修复闭环；8E 仍 in progress。若用户再次明确授权，下一步只执行一次修复后
  `mid` live replay；成功才登记真实两源 bundle，随后进入 player profile selection DTO/legacy region。

### 2026-08-23：RQ-088 必要外部调用持续授权

- 用户纠正逐次等待授权的过度保守做法：必要、有界、低费用、隐私可控的只读真实调用可由 Codex 直接执行并记账。
- 高费用/批量抓取、敏感数据发送、不可逆外部写入或权限扩大仍需确认；本条不等于无限调用或放宽 body-free 合同。
- 当前直接进入 ADR-0058 修复后的单次 OP.GG `mid` replay；复用既有 Riot projection，Riot/LLM/Key calls 0。

### 2026-08-23：ADR-0058 修复后 live replay 通过

- `LIVE-PASS`：RQ-088 下执行一次 OP.GG `mid` tools/call，strict adapter 成功解析 10 facts 并与既有 Riot
  projection 创建 bundle `69ed8a83140da73818ed46a7857947d780d0132a309a6317036438161fbfff1a`。
- `BOUNDARY`：external I/O 为 OP.GG 1、Riot/LLM/Key 0，无重试、无 raw body；结果 SHA-256
  `1dd8039baee1260ba17da07810a31a50233f37feeb95250bc174ae8a9ac54d1d`。
- `HONEST-DEGRADE`：bundle 为 `degraded/unjoined`，因为 Akali 未命中本次 top-10 mid Meta，且 replay 不含
  Data Dragon/official patch；这不是 parser/fusion failure，不换样本追绿、不继承 patch。
- `NEXT`：增加 frozen success evidence regression、更新 canonical 后做比例本地门、独立 evidence 提交与
  exact-SHA 三 job；随后 8E 下一实现批为 owner-scoped player profile selection DTO/legacy region。
- `LOCAL-GATES`：success evidence regression、OP.GG/MCP/Evidence 相邻 `61 passed`；governance、JSON 与
  diff check 全绿。当前只待独立 evidence 提交/推送和 exact-SHA 三 job。

### 2026-08-23：修复后 live-success evidence exact-SHA 公共闭环

- `PUBLIC-CI`：`efaccd9a8022f0d75e9baca5470450be6a1a3357` / Actions `32615821339` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1701 passed, 133 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `186 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6/外部 Riot Provider calls 0。
- `CLOSED-BATCH`：OP.GG JSON-null parser Bad Case 已完成 live diagnosis → red/green fix → code public CI →
  post-fix live pass → frozen evidence public CI 的完整链。8E 仍 in progress，下一批为 owner-scoped player
  profile list/selection DTO 与 legacy region 修正；不把当前 degraded join 说成 exact Meta match。
### 2026-08-23：8E Batch B 本地实现与真库/Linux 验证

- `AUTHORIZED`：RQ-086/RQ-088 的 8E 连续推进授权保持有效；RQ-089 又要求消除可避免的本地 DB/Docker skip，并继续保留 exact-SHA 公共关闭门。
- `DESIGN`：ADR-0059、专用 design/implementation plan 采用已有 Player Link 的 owner-scoped latest-success projection；不新增 default/profile 表或 migration。
- `IMPLEMENTED`：profile domain/port/service/SQL/API、Conversation canonical selection + legacy alias、legacy required routing、SQL execution-target routing、四地区 exact-select builder、Worker/Compose 去 ambient region 与 package smoke 已完成。
- `TDD`：profile 隔离/去重/hidden/PUUID-free、双字段 422、region required/CN/unknown、fingerprint、legacy/conversation propagation、无 fallback 与 Compose/package 合同均有回归。
- `LOCAL-INFRA`：Docker Desktop + WSL2、PostgreSQL 17 容器和用户级测试 URL 已配置；CI-equivalent PostgreSQL collection `187 passed`，migration/check 与真实 Linux Compose package smoke 已通过。
- `LOCAL-GATES`：focused `268 passed`；完整 `1842 passed, 1 skipped, 1 warning, 127 subtests passed`；两套 RAG 满阈值，Harness `published`/0 revisions，compileall/pip/YAML、SDK/Secret/tracked-data、governance/diff 全绿。Linux Compose schema 1.6/外部调用 0/image boundary 通过并清理资源。
- `BOUNDARY`：8E 仍 in progress/coverage planned；前端、Auth/RSO、SSE、EvidenceBundle persistence、HTTPS、备份与部署没有开始。唯一下一动作是独立提交/push 与 exact-SHA 三 job。

### 2026-08-23：8E Batch B exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `e844bdd673ee051568e8611160f6ba53e8c745c4` / Actions
  `32622696087` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1709 passed, 134 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `187 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6/外部调用 0/image boundary 全绿。
- `CLOSED-BATCH`：owner-scoped profile list/selection、opaque alias、explicit legacy/Conversation routing 和本机
  Docker/PostgreSQL 补环境正式闭环。整个 8E 与 coverage 仍 in progress/planned。
- `HANDOFF`：按既有 preflight 顺序唯一下一内部批为 Batch C EvidenceBundle persistence/refresh/expiry、
  event replay→SSE DTO 与四态产品状态合同；Batch C 公共闭环前不进入 Batch D 静态前端。

### 2026-08-23：RQ-090 授权并启动 8E Batch C

- `AUTHORIZED`：用户再次明确继续，授权 Batch C 连续实施；不跳到 Batch D React。
- `RECOVERY`：clean HEAD/origin `3488d7b`，canonical `8e-productization/in_progress`，治理检查通过；本机
  PostgreSQL/Docker 已可用，唯一 Windows symlink skip 继续由 Linux exact-SHA pytest 补证。
- `DESIGN`：ADR-0060、专用 design/implementation plan 采用 PostgreSQL append-only Evidence revision、
  refresh idempotency、query-time expiry、cursor SSE 与四态 product projector；file store/reconstruct-on-read 拒绝。
- `BOUNDARY`：本批新的 Riot/OP.GG/Provider/LLM calls 为 0；8B holdout 不重跑；Auth/HTTPS/backup/frontend deferred。
- `NEXT`：先写 storage round-trip/digest/expiry/product-state pure red tests，再实现最小合同。

### 2026-08-23：8E Batch C 本地实现与八维材料完成

- `TDD`：pure storage/snapshot/expiry/four-state、0011/PostgreSQL Repository、Product Service/API、cursor
  SSE、composition 与 package smoke 均从缺模块/缺合同红灯进入绿色。
- `IMPLEMENTED`：append-only Evidence revision、strict nested/bundle/snapshot digest、refresh replay/conflict、
  owner latest、query-time expiry、四态 DTO、Last-Event-ID reconnect/keepalive/terminal/error close 已落地。
- `REAL-POSTGRES`：Repository `6 passed`，包含并发连续 revision、tamper、trigger 和 cascade；Repository→
  Service→HTTP 纵切通过，cross-owner evidence/product-state 均 404。
- `REPAIR`：修复 shallow-copy tamper 假阳性、retry timestamp 误冲突、0011 head 旧断言和 import-order
  circular dependency；没有放宽 typed/storage/owner 合同。
- `EVIDENCE`：新增 `docs/learning/8e-evidence-product-api-walkthrough.md`，coverage 八维路径齐全但 8E 继续
  `planned`；Batch C 公共关闭前不进入 Batch D。
- `BOUNDARY`：本批 Riot/OP.GG/Provider/LLM calls 0，8B holdout 未重跑；Auth/React/HTTPS/backup/deployment
  未实现。该记录时的下一动作是完成全部本地/真库/Linux 门、独立提交/push 与 exact-SHA 三 job。

### 2026-08-23：8E Batch C 全部本地门闭环

- `ROOT-CAUSE/TDD`：本地 Compose 默认 API owner 与 smoke 硬编码 owner 不一致，导致严格 Memory binding
  正确返回 unavailable；红灯覆盖 settings 动态 owner 与 Compose 环境同源，最小修复后 package suites
  `39 passed`，没有削弱 owner/relationship/conversation identity。
- `LOCAL-LINUX`：无手工 owner 覆盖的全新 Compose project 通过 schema 1.6 no-I/O smoke；Memory Context
  3 records、terminal assistant 0、外部调用 0，非 root UID 999 与 image exclusion 通过，资源已清理。
- `LOCAL-GATES`：focused `79 passed`；CI-equivalent PostgreSQL `194 passed, 1 warning`；完整
  `1888 passed, 1 skipped, 1 warning, 127 subtests passed`；Alembic head→base→head/check 无 drift。
  两套 RAG 满阈值，Harness `published`/0 revisions，compileall/pip/6 YAML、SDK/Secret/tracked-data、
  Evidence/SSE OpenAPI body-free 扫描均通过。
- `BOUNDARY/NEXT`：唯一 skip 为 Windows symlink；Batch C 新的 Riot/OP.GG/Provider/LLM calls 0，8B
  产品 holdout 未重跑。当前只待 governance/diff/cached diff、独立 implementation/evidence commit/push 和
  exact-SHA 三 job；公共全绿前不进入 Batch D React。

### 2026-08-23：8E Batch C exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions
  `32629160732` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1750 passed, 139 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `194 passed, 1 warning`，0011 head→base→head 与 `alembic check` 无 drift；Linux package schema 1.6、
  Memory Context 3 records、terminal assistant 0、外部调用 0、非 root/image boundary 全绿。
- `CLOSED/HANDOFF`：Batch C 正式关闭，整个 8E/coverage 继续 in_progress/planned。唯一下一内部批为
  Batch D 静态/fixture-backed 前端设计门，当前 prepared/waiting authorization；本状态批不创建 React。

### 2026-08-23：RQ-091/RQ-092 授权并冻结 8E Batch D 设计

- `AUTHORIZED`：用户明确开始/继续 Batch D；视觉研究必须广撒网、统一横评、精挑选和自主重构，
  MotionSites 不得成为主要或单一来源。
- `CALIBRATED`：采用硬门不能成为过度简约的借口；过门候选继续以视觉完成度、fashion/cool、品牌
  记忆点与 LoL 语义择优，允许为少量高价值效果承担可验证复杂度。
- `AUDIT`：API/fixture 审计确认首批应做近期复盘工作台；安全 Summary 尚无 HTTP endpoint，Evidence
  projection 仍需未来 runtime decoder，运行历史与完整 Timeline DTO 尚不存在，静态 UI 不得伪造。
- `DESIGN`：ADR-0061 与专用 design/implementation plan 采用 `Rift Command Center`、React/Vite/
  TypeScript + vanilla CSS tokens、Motion、Radix Dialog、本地 OFL 字体；其余组件/动效库只作机制参考。
- `BOUNDARY/NEXT`：整个 8E coverage 保持 planned；当前进入 fixture contracts 与 web shell 的 red→green
  TDD，不接真实 API/SSE/Auth，不实现 HTTPS、backup、deployment 或公网发布。

### 2026-08-23：8E Batch D 本地实现、浏览器门与视觉 QA

- `PUBLIC-DESIGN`：design `88a5ab6` / Actions `32631766013` exact-SHA 三 job 全绿；只证明设计门。
- `TDD`：fixture/依赖先形成 25 项绿灯；UI 首红为缺 `App` 的 3 suites，CI contract 首红为缺 web
  lockfile；最终 unit `6 files / 35 passed`，Python workflow/Docker contract `2 passed`。
- `IMPLEMENTED`：React/Vite/TypeScript + vanilla tokens、Rift SVG/CSS atmosphere、产品四态、聚合 Summary、
  quality-gated Coach brief、relationship-safe Training、Radix/Motion Evidence Drawer 和七客户端场景完成。
- `BROWSER`：Playwright `12 passed`；1440/1024/390/320、Drawer keyboard/Escape/focus return、observed
  binding、reduced-motion、no remote I/O 和 axe critical/serious 0 均通过。
- `VISUAL-QA`：逐张查看 desktop/mobile/tablet/degraded/Drawer/reduced-motion；修复 tablet Evidence grid
  拉伸。接受 JPEG 保存 `docs/assets/8e-batch-d/`，不把测试自动截图冒充未审查证据。
- `SUPPLY-CHAIN`：strict build JS gzip 109.89 kB / CSS gzip 10.99 kB；npm 官方 registry production audit
  0 vulnerabilities。直接 runtime dependency license 为 MIT/OFL-1.1，未复制 React Bits/Aceternity 源码。
- `CONTEXT`：RQ-093 session-logs/focused export 回查确认五模块、Image2/Photoshop、ECharts/Timeline、广泛
  资源池与 8F README 要求仍在；首批工作台不是 scope reduction。
- `SECOND-RESEARCH/POLISH`：用户指出第一版可能过快后，补 8 组 AutoGLM、35 站可访问性、MotionSites
  live Apps 和 Riot/Langfuse/TrainingPeaks/Mobalytics/21st.dev/Aura 深读；正式五模块资源矩阵已创建。
  研究只推动 Drawer 增加 body-free Safe Run Path，没有引入重依赖或提前购买/复制 Prompt。
- `LOCAL-GATES`：带真实 PostgreSQL 的完整 `1890 passed, 1 skipped, 1 warning, 127 subtests`；0011
  head→base→head/check、两套 RAG、Harness、compile/pip/6 YAML、Secret/tracked-data/governance/diff、
  隔离 Linux Compose schema 1.6/外部调用 0/non-root/image exclusion 全绿。唯一 skip 为 Windows symlink。
- `BOUNDARY/NEXT`：外部 Riot/OP.GG/Provider/LLM calls 0，8B holdout 未重跑，Dockerfile 不 COPY web。
  该记录时等待独立提交/push 与 exact-SHA 三 job；下节公共闭环已经完成该动作。8E coverage 继续 planned。

### 2026-08-23：8E Batch D exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `f7ebedd7c6cfd135201847a327dfd06c01cc7205` / Actions
  `32636771507` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1752 passed, 139 skipped, 1 warning, 127 subtests passed`；frontend
  `6 files / 35 passed`、Playwright `12 passed`、typecheck/build 也在同一 job 通过；真实 PostgreSQL
  `194 passed, 1 warning`，0011 可逆且 metadata=head；Linux package schema 1.6/外部调用 0/image boundary
  与资源清理全绿。
- `CLOSED`：Batch D 静态/fixture-backed Rift Command Center 正式关闭；AutoGLM 新一轮可用性复核没有发现
  推翻五模块资源矩阵的新模式，继续坚持跨来源筛选而非单押 MotionSites。
- `HANDOFF`：整个 8E/coverage 仍 `in_progress/planned`。唯一下一动作是 owner-scoped API/SSE 接线设计门，
  先盘点 profile/product/evidence/event DTO 和缺失 Summary/report projection；不自动进入 Auth/RSO、部署、
  电影感入口、完整 Timeline/Training 或 8F。

### 2026-08-23：RQ-094/RQ-095 Live Integration 设计门

- `CONTEXT-RECONCILED`：定向日志复核恢复 A `Rift Awakening`、B `Esports Intelligence`、C
  `Void Holographic Lab` 与 A→B 组合；C 仍只作受限 Hero 实验。小复盘、OP.GG breadth 与完整真实 fusion
  golden slice 已登记为后续必做，不把 lane-meta/degraded replay 冒充完成。
- `AUTHORIZED`：用户明确继续当前唯一下一动作；RQ-095 只授权 live API/SSE 接线设计门，不授权实现、
  Auth/部署、其余五模块、真实外部调用或 8F。
- `DESIGN`：ADR-0062 与 design/implementation plan 采用 owner-scoped latest locator + existing APIs；补
  Recent Summary/typed Evidence，前端使用 same-origin exact decoder、generation/abort、单 EventSource、
  restricted Markdown 与真实 Training 字段。
- `BOUNDARY`：当前没有产品代码、migration、npm 安装、Riot/OP.GG/Provider/LLM 调用、Key 读取或 8B
  holdout；8E coverage 保持 `planned`。
- `NEXT`：同步 roadmap/amendment/capability/learning 与 requirements/canonical，运行 governance/stale/diff，
  创建独立 design commit 并等待 exact-SHA 三 job；公共闭环后才交接 implementation prepared。

### 2026-08-23：Live Integration design 公共闭环

- `PUBLIC-CI`：design `4057c93f4ac1ac9ebd181528e559b084e3425e89` / Actions `32639561338` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1752 passed, 139 skipped, 1 warning, 127 subtests passed`；frontend unit 35、
  Playwright 12、typecheck/build 与 JS/CSS gzip `109.89/10.99 kB` 全绿；真实 PostgreSQL
  `194 passed, 1 warning`，migration 可逆且 metadata=head；Linux package smoke 成功。
- `CLOSED-DESIGN`：RQ-094 context reconciliation 与 RQ-095 design gate 正式关闭；该证据没有产品代码、
  外部调用、Key、8B holdout 或付费资源。
- `HANDOFF`：live integration implementation 只交为 prepared/waiting authorization；整个 8E coverage 仍
  planned，Auth/部署、入口/Timeline/完整 Training、OP.GG breadth 与 fusion golden slice 仍未进入。

### 2026-08-23：RQ-096 Live Integration 本地实现与门禁完成

- `IMPLEMENTED-BACKEND`：owner-scoped latest locator、Recent Summary route、typed Evidence HTTP、composition
  与 package 接线完成；公共 PostgreSQL collection 已加入 locator repository 真库文件。
- `IMPLEMENTED-FRONTEND`：exact decoders、bounded client、deterministic adapters、generation/abort controller、
  single EventSource、default-live React、真实 Summary/report/Evidence/Training 消费完成；observed 不请求
  personal Training，profile switch 先 clear/abort/close。
- `BUNDLE-DECISION`：`react-markdown` 使 JS gzip 156.52 kB 超过硬门，已按 ADR 移除并使用 escaped plain
  text；流式 body 读取又增加真正的 byte-limit cancel，最终 JS/CSS gzip `122.01/11.35 kB`，official npm audit 0 vulnerabilities。
- `BAD-CASES`：修复 native fetch illegal receiver、OpenAPI exact paths、E2E ledger reuse、Windows worker
  资源饥饿、failed-task Evidence smoke ordering，以及提交前审查发现的 `/player-profiles` generic exception
  映射错位，以及无 Content-Length body 原先在限额检查前被完整缓冲；后两者分别由 RuntimeError 红灯和
  streaming cancel 红灯修复；invalid profile selection 也先清理旧 fetch/stream，且默认 App 已把
  `player_profile_id` URL 参数接入 server-list-only initial selection。未放宽 decoder、Evidence repository 或 bundle budget。
- `LOCAL-EVIDENCE`：backend focused 58、package/composition 59、完整
  `1939 passed, 1 skipped, 1 warning, 127 subtests`、真 PostgreSQL 200、frontend unit 66/e2e 17、可逆
  Alembic、两套 RAG、Harness、compile/pip/YAML/security/governance/diff 与 Linux package schema 1.6 全绿。
- `LEARNING`：新增八维 walkthrough 并登记 8E coverage paths；整个 group 继续 planned。
- `BOUNDARY/NEXT`：外部 Riot/OP.GG/Provider/LLM calls 0，8B holdout 0；唯一下一动作是独立
  implementation/evidence commit/push 与同 SHA 三 job，公共闭环前不进入 Auth/部署、其余五模块、breadth、
  golden slice 或 8F。

### 2026-08-23：RQ-096 Live Integration 公共闭环

- `PUBLIC-CI`：implementation/evidence `f441061e7444fa6d1d3c213b81e05a02f0fc68c5` / Actions
  `32647933692` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- `COUNTS`：公共 pytest `1796 passed, 144 skipped, 1 warning, 127 subtests passed`；frontend unit 66、
  Playwright 17、JS/CSS gzip `122.01/11.35 kB`；真 PostgreSQL `200 passed, 1 warning`；Linux package
  schema 1.6、Memory Context 3、terminal assistant 0、外部调用 0 与 image boundary 全绿。
- `CLOSED`：RQ-096 Live Workbench integration 正式关闭；整个 8E/coverage 继续 in_progress/planned。
- `HANDOFF`：唯一下一检查点 `8e-batch-e-security-deployment-entry-design` prepared/waiting authorization；
  Auth/部署实现、入口/Timeline/完整 Training、breadth/golden slice 与 8F 均未自动进入。

### 2026-08-23：RQ-097 Batch E 入口设计

- `AUTHORIZED`：用户最新“那继续”恢复唯一设计检查点，不授权 Batch E 实现或 8F。
- `DESIGN-CLOSED-LOCAL`：新增 ADR-0063、Batch E design/implementation plan 和八维 walkthrough；冻结
  Auth/RSO 分离、single-node edge topology、security headers/limits、Secret、backup erase、privacy、
  observability 与 E1–E5/W1–W5 顺序。
- `NO-IO`：本轮不修改产品代码、不安装依赖、不读 Secret、不调用 Riot/OP.GG/Provider/LLM、不部署。
- `NEXT`：完成 stale/diff/比例门，独立 design commit/push，等待 exact-SHA 三 job；公共全绿后只交接
  `8e-batch-e-security-deployment-implementation` prepared。
## 2026-08-24：RQ-098 视觉前置开始

- 已完成恢复顺序、治理基线检查和用户确认方向的 ADR/视觉合同/实施计划/学习 walkthrough。
- 已登记 Image2/Photoshop、MotionSites、Riot 官方语言、成熟数据产品和动效库的角色边界；未购买付费
  Prompt、未安装新依赖、未调用外部服务、未改动真实数据合同。
- 已完成 Task 1 presentation state、Task 2 语义入口 shell 和 `?surface=awakening` 隔离 preview；前端 unit
  `79 passed`、typecheck/build、Playwright `19 passed`、desktop/mobile/reduced-motion 截图检查通过。
- Task 3 已接入一张无文字/无 UI 的 Image2 氛围 plate，压缩为 77.8 kB WebP，并登记来源、fallback、
  bundle 和移除路径；CSS/SVG 路线与核心仍可独立工作。服务重启后 `127.0.0.1:4173` 返回 200。
- 下一动作：继续 Task 3 的 Hextech 面板材质、状态边缘和 Portal → Workbench handoff polish，再做真实
  profile/产品状态接线，不把当前 preview 误报成成品。

### 2026-08-24：RQ-098 Task 3 视觉 polish 与 Batch E implementation 接续

- `AwakeningScene` 的 Task 3 已完成本地视觉门：Image2 instrumentarium 由 screen/high-contrast overlay
  收敛为低对比 soft-light 支撑层；去掉 calibration panel 的重复网格；Core、边框、输入材质和 cyan
  action 统一减弱机械噪声，同时保留 Hextech square/diamond/circle 语义与 Rift atmosphere。
- SVG route 现在按 `idle/editing/calibrating/ready/degraded/rejected/client-error` 编排；calibrating 才有
  明显 dash choreography，ready/degraded handoff 使用一次 820ms transition，reduced-motion 会冻结所有
  连续/transform 动效。桌面、390px mobile、ready handoff 截图人工检查通过；Impeccable detector 为空。
- 前端门：unit `80 passed`、typecheck/build 通过，JS/CSS gzip `123.91/13.20 kB`；强制隔离 fake API/Vite
  的 `CI=1 npm run test:e2e` 为 `20 passed`。第一次并行复用旧 Vite 的 5 个 live 失败确认为环境 proxy
  指向未启动 `127.0.0.1:4174`，不计入代码回归。
- 随后继续 Batch E implementation 本地 TDD：新增 opaque HTTP session issuance/revoke、Secure/HttpOnly/
  SameSite cookie、server-side owner resolve、启用 session 时全写请求 CSRF、header/body budget、单机
  IP rate limiter、Versioned SecretSource 注入到 Worker composition；E1/E2/E3 focused backend `56 passed`
  （含原有回归）和 compileall 通过。Auth/RSO、PostgreSQL session repository、真实 Secret Manager、HTTPS
  edge 和多副本 rate store 仍未声称完成。
- `NEXT`：补齐 Batch E implementation walkthrough/coverage 与 canonical 状态，跑完整比例后创建独立
  implementation/evidence commit；公共 exact-SHA 三 job 全绿前不关闭 Batch E 或进入 8F。

### 2026-08-24：RQ-099 E1/E2/E3 exact-SHA 公共闭环

- implementation/evidence `92b768591183e8a7fbe6d12a86359aac862b7efb` / Actions `32658277570` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest/RAG/Harness/gov、真实
  PostgreSQL control-plane 与 Linux package smoke 均通过。
- E1 opaque session/CSRF、E2 bounded request/header/body + 单机 rate policy、E3 versioned SecretSource 与
  key-last Worker composition 取得公共代码证据；仍不声称 OIDC/RSO、PostgreSQL session repository、真实
  Secret Manager、HTTPS/HSTS、多副本 rate store 或 backup/restore/erase 完成。
- `NEXT`：进入 E4 backup/restore/erase；先补 restore replay、erase-before-ready、partial failure compensation
  的红灯合同与实现计划，再按同一八维/本地/独立提交/exact-SHA 节奏推进。

### 2026-08-24：E4 backup/restore/erase 本地实现

- 先以红灯测试冻结 manifest digest 篡改拒绝、restore marker replay、partial failure compensation、
  readiness fail-closed、重复 restore 幂等，以及 owner/conversation/relationship run 目标隔离。
- `app/lifecycle/backup.py` 新增 `OwnerRunReference`、`OwnerRunArtifactTraceCleaner` 与
  `IdempotentDeletionMarkerReplayer`；restore 会校验 deterministic marker digest，并只对本次新应用的
  marker 做补偿，避免把上一次成功恢复的 marker 错误回滚。
- `PostgresOwnerDataLifecycleRepository.locate()` 通过真实 `ReviewTaskRecord` 只读定位目标 run；API
  composition 将 owner lifecycle cleaner 接到已有 `FileRunDataCleaner`，因此 SQL marker commit 后才清理
  run 目录中的 Artifact/Runtime Trace。错误 owner/target 或 run cleanup 失败均保持 body-free pending。
- focused `tests/test_backup_restore.py` 与相邻 lifecycle tests：`16 + 15 = 31 passed`；compileall、
  diff check 通过。该批仍没有对象存储/KMS/备份字节/定时任务，不能声称生产加密灾备或 RPO/RTO。
- `NEXT`：运行完整回归、真实 PostgreSQL locator/migration 与 Linux package smoke，完成 stale/governance
  门后创建独立 implementation/evidence commit；公共 exact-SHA 三 job 全绿前不交接 E5。

### 2026-08-24：E4 exact-SHA 公共闭环，进入 E5

- implementation/evidence `27b9256b8987ade45fbc9eb5f62497cbaef9f518` / Actions `32660145945` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，E4 正式关闭。
- 本批公共 pytest 包含前端合同、全量 Python、RAG/Harness/security/tracked-data/governance；真库 job
  覆盖 migration head、owner lifecycle locator 与控制面回归；package job 覆盖 Compose、Linux no-I/O、
  non-root/image exclusion、资源清理和 external Riot Provider calls = 0。
- E4 不声称 KMS/对象存储/加密 backup bytes、定时备份或 RPO/RTO 实测；这些边界和八维材料已持久化。
- `NEXT`：按连续授权进入 E5 packaging/observability，先审查 Docker/Compose/health/metrics/rollback
  接缝并用 red tests 冻结 readiness、migration order、非 root 和 body-free observability 合同。

### 2026-08-24：E5 packaging/observability 本地首批

- 红灯先冻结 `GET /health/metrics` 的 body-free typed projection；实现 `TaskObservability.emit()` event
  counters、`public_snapshot(max_samples=1000)` latency bound、p50/p95 DTO 与 `/health/metrics` route。
- 健康检查仍分为 liveness/readiness；Compose migration order、non-root/image boundary、Linux no-I/O smoke
  和 rollback runbook 保持单机边界，不引入新 metrics runtime。
- FastAPI + observability focused `17 passed`，最终完整 pytest `1971 passed, 1 skipped, 1 warning, 127
  subtests passed`，compileall/diff/governance 继续通过；当前尚未独立提交和
  公共 CI，E5 仍 in progress。
- `NEXT`：完成 E5 八维 walkthrough/计划同步，跑完整 pytest、RAG/Harness、Alembic、Compose smoke 与 stale
  门，创建独立 implementation/evidence commit 并等待 exact-SHA 三 job。

### 2026-08-24：E5 exact-SHA 公共闭环与产品模块交接

- E5 implementation/evidence `ca6da44be439b0020f231dc0c00d6a70322e723c` / Actions `32661425379` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿，E5 正式关闭。
- 公共 pytest 包含 frontend contract、完整 Python、RAG/Harness/security/tracked-data/governance；真库
  job migration/control-plane 全绿；package job 构建 API、验证 `/health/metrics`、no-I/O smoke、non-root
  image boundary 与资源清理。
- `/health/metrics` 仍只是 bounded body-free operational projection，不是 Prometheus/长期时序/自动告警；
  8E coverage 继续 planned，Auth/RSO、HTTPS、完整前端产品模块、OP.GG breadth/golden slice 和 8F 未完成。
- `NEXT`：按连续授权进入 `remaining-product-modules / production-shell + Auth gate`；先审查现有 React
  live/fixture 状态和 E1 session HTTP seam，冻结未登录/加载/拒绝/登录失败合同，再做前端 TDD，保持真实
  OIDC/RSO provider adoption 独立且不伪造生产登录。

### 2026-08-24：视觉 Task 3 polish 与 production shell/Auth gate 本地完成

- 视觉 polish 根据 1440/390 截图修正：aperture 保留 Rift 水晶氛围，instrumentarium 降为低对比远景，
  route/core/panel 的光晕与重复边框收敛；机械层不再压过标题、身份校准和 handoff。`prefers-reduced-motion`
  仍冻结连续运动，CSS/SVG fallback 不变。
- 新增 `AuthSessionWire`、`decodeAuthSession` 和 `BrowserAuthSessionClient`；同源 `POST /api/auth/session`
  只接受 typed session projection，body-free auth codes 进入 allowlist，错误正文不进入 UI/日志。
- 新增 `AuthGate` 与 `ProductionShell`：checking 时不启动 live controller，authenticated 后才 start；
  `auth_unavailable` 显示安全配置缺失，`auth_session_expired/revoked/required` 显示可恢复 session boundary。
  fixture scenario 与 `surface=awakening` preview 仍显式不走 production auth。
- 本地 frontend unit `87 passed`、Playwright `22 passed`、typecheck/build 通过；JS gzip 仍约 `123.91 kB`；
  detector 无 findings，Riot/OP.GG/OIDC/RSO/LLM 外部调用为 0。
- 八维证据：`docs/plans/2026-08-24-8e-production-shell-auth-gate-{design,implementation}.md` 与
  `docs/learning/8e-production-shell-auth-gate-walkthrough.md`；coverage 仍保持 8E `planned`。
- `NEXT`：创建独立 implementation/evidence commit，运行 Python 完整回归、RAG/Harness、Alembic、
  governance、package/Compose smoke，并等待 exact-SHA 公共 CI；公共闭环后按顺序进入 Timeline DTO/UI，
  不把 OIDC/RSO 或真实 auth provider 宣称为已采用。

### 2026-08-24：RQ-100 production shell/Auth gate exact-SHA 公共闭环，进入 Timeline DTO/UI

- `15a3a9eea5a1e84f1b1ef604ea42a3008f956cb2` / Actions `32663345737` 的 `pytest`、`postgres-migrations`、
  `packaging-smoke` 三 job 全绿；公共 pytest 包含 frontend unit/e2e/build、Python 回归、RAG/Harness、
  governance；真库和 Linux package smoke 也通过。
- production shell/Auth gate 正式关闭：live controller 只有在 typed same-origin session 成功后才启动，
  auth unavailable/expired/revoked/required 各有安全状态；视觉 Task 3 polish 与资产可移除边界保持。
- `NEXT`：进入 `remaining-product-modules / Timeline DTO/UI`，先做设计和红灯合同，禁止从 fixture 生成
  假时间序列；必须绑定 `run_id/task_id`、timeline availability、partial/degraded 和 source posture。

### 2026-08-24：RQ-101 Timeline DTO/UI 本地完整门禁

- `DESIGN/TDD`：ADR-0065 与专用设计/实施计划拒绝未持久化的 Gold/CS/XP 假曲线；Backend 首红为缺 Timeline
  view，Frontend 首红为 exact link/decoder/controller 与缺 component，均已绿。
- `BACKEND`：新增 verified/bounded `RunTimelineView` 与 owner-scoped HTTP；整体/单场 available/partial/
  unavailable、20 match/128 event 上限、total/projected/truncated 和安全 reason code 均为严格合同。
- `FRONTEND`：same-origin exact decoder/controller 增加 Timeline；`TimelinePanel` 用真实秒数几何、三阶段、
  match/event selection 和始终存在的语义 event list；mobile/reduced-motion/keyboard/缺失 fallback 完成。
- `VISUAL`：desktop/mobile/partial-unavailable 三张 durable JPEG 已逐张查看；机械语言压缩为低对比阶段刻度、
  状态边和节点，信息仍是主层。JS/CSS gzip `128.51/15.27 kB`。
- `LOCAL-GATES`：focused query/API `45`、相邻 API/composition/package `123`、frontend unit `92`、Playwright
  `25 passed`、完整 Python `1981 passed, 1 skipped, 1 warning, 127 subtests`、真 PostgreSQL `201 passed`、Alembic reversible/
  no drift、Linux package schema 1.6/no-I/O/non-root/image exclusion/resource cleanup 全绿。唯一 skip 为 Windows
  symlink；首次全量 4 个 DB setup error 来自缺进程级 `DATABASE_URL`，映射既有 test URL 后真库与全量通过。
- `BOUNDARY/NEXT`：Riot/OP.GG/Provider/LLM calls 0；8E coverage 继续 planned。当前只待独立 commit/push 与
  exact-SHA 三 job；公共关闭后先执行 RQ-102 bilingual product-surface foundation，再进入 Evidence/Trace
  深页。Training full、OP.GG breadth/golden slice 与 8F 继续保持后序独立门。

### 2026-08-24：RQ-103 当前视觉非最终签收

- 用户明确当前截图、UI、色调、背景、布局与细节仍须继续 polish；英雄名旁缺头像只是未穷举示例。
- 当前 Timeline 重新校准为“严格功能合同 + 高保真 V1”，不是最终作品集视觉。浏览器证据统一为
  `25 passed`，frontend unit 为 `92 passed`，最新 bundle 为 JS/CSS gzip `128.51/15.27 kB`。
- 顺序保持：Timeline exact-SHA 公共关闭 → RQ-102 双语 foundation → RQ-103 Data Dragon 资产/细节
  enrichment → Evidence/Trace → Training → OP.GG breadth/golden slice → 8E final visual QA/exit。

### 2026-08-24：RQ-101 Timeline exact-SHA 公共闭环

- implementation/evidence `794032f055f2fa37173f9525279870f0adbe5220` / Actions `32682243568` 的三 job
  全绿；公共 pytest 1837/145 skips/127 subtests、frontend unit 92/e2e 25、真库 201、Linux package schema 1.6。
- Timeline 正式关闭的是 verified DTO/API/decoder/controller/phase rail/partial-missing 高保真 V1，不是
  RQ-103 最终视觉；本批外部 Riot/OP.GG/Provider/LLM calls 0。
- `NEXT`：按 RQ-102 与连续授权进入 bilingual product-surface foundation；先教学和冻结 locale contract，
  不提前混入 LoL asset enrichment、Evidence/Trace、Training 或 8F。

### 2026-08-24：RQ-102 bilingual foundation 设计冻结

- 初学者教学已区分 UI copy、Data Dragon entity locale 与 Coach Artifact language；比较整页机翻、第三方
  i18n runtime 和 typed local catalog 后，ADR-0066 采用最后一项。
- 新增专用 design/implementation plan 与八维 walkthrough；冻结 `zh-CN|en`、strict versioned localStorage、
  navigator fallback、canonical code→localized copy、original generated content 不机翻和 asset enrichment 后序。
- 该设计记录时只完成设计与只读代码接缝审计，尚未实现 locale provider/switch/catalog，也未修改 API/Memory、安装
  dependency、调用外部服务或进入 RQ-103。下一动作是先写 locale contract/catalog 红灯。

### 2026-08-24：RQ-102 bilingual design exact-SHA 公共闭环

- design `8969aef689febfb059f72e2fa71c928b2e3bee67` / Actions `32683742229` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- 设计门正式关闭；当前进入 implementation TDD。该公共 SHA 没有 locale 产品代码、依赖、API/Memory 改动、
  Data Dragon 资产或外部调用。

### 2026-08-24：RQ-102/104/105/106 本地实现与三层旅程收口

- 双语：zero-dependency typed `zh-CN|en` catalog、strict storage/navigator fallback、共享 LocaleSwitch、
  structured Workbench copy 与 original Report/Plan 已完成；`MIDDLE`、metric/gap/error code、test scenario、
  RSO/Match-V5 transport 名称不再直接进入普通产品表面。
- 旅程：ADR-0067 的 Portal→Account→Workbench 已实现；默认 Portal core 前 API/SSE=0，Account 读取已有
  profiles 或真实 POST/poll Player Link，明确选择 profile 后才启动一次 live controller；history、reload、
  session failure、abort/late response、unlisted profile 与 focus handoff 均有测试。
- 视觉：按 RQ-106 用母图生成 V2 keyframe，再移除 baked core/beam 形成 122.7 kB runtime background；
  keyframe 只作 docs 证据，aperture fallback-only，instrumentarium 退出 public runtime。React core 保持唯一
  click/keyboard 真值，正常 handoff 720ms，reduced-motion 立即进入；当前仍不是最终电影化签收。
- 当前本地证据：Player Link HTTP 组合 `26 passed, 1 warning`；frontend unit `24 files / 136 passed`、
  Playwright `36 passed`、JS/CSS gzip `142.68/18.50 kB`；完整 Python
  `1982 passed, 1 skipped, 1 warning, 127 subtests`。真 PostgreSQL 17/Alembic、两套 RAG、Harness、
  compile/pip/YAML、npm audit 0、SDK/Secret/tracked-data、governance/diff 与隔离 Linux package 全绿。
- 产品 Riot/OP.GG/Provider/LLM calls 0；内置视觉生成调用 2。gptimage2 因本地代理未监听在请求前失败，
  gptimage2 image calls 0。
- RQ-107 审计确认 Web 仍是 Report viewer + Training summary；其与 RQ-103 的相对顺序现在延后到 RQ-108
  关闭后集中裁决，当前 canonical 顺序不变。
- `NEXT`：完成全部持久同步、比例 Python/RAG/Harness/安全/governance 门与最终视觉/asset 检查；创建独立
  implementation/evidence commit/push，等待该 SHA 三 job。公共成功前不关闭 foundation 或进入 RQ-108。

### 2026-08-25：RQ-108 持久化与用户母图纠正

- `REQUIREMENT`：新增 RQ-108，固定 foundation exact-SHA 公共关闭后的立即下一原子项为
  `portal-motion-polish`；RQ-108 当前只是 next-only，不标 in progress。
- `VISUAL-TRUTH`：用户再次提供并确认母图。中央水晶必须在场景媒体内部重绘/调大并自然呼吸蓄能；透明
  原生 button 只覆盖点击区，不能显示另贴水晶或常规按钮。轻微光点/脉冲提示进入，点击触发汇聚/burst 与
  独立 Account 场景幕切。
- `ASSET-BOUNDARY`：独立水晶候选拒绝采用，不进入当前提交；母图临时附件已本地保全为后续设计源，但不
  进入 foundation staging/runtime。RQ-108 将独立登记 provenance、压缩/codec、poster/mobile/fallback 与预算。
- `STATE-SYNC`：requirements/canonical/roadmap/history/amendment/matrix/learning/active plan 已同步；coverage
  继续只保留 `8e-productization: planned`，不为尚无 ADR/实现的 RQ-108 创建空 evidence group。
- `NEXT`：重新运行 governance/stale/diff 与 frontend/比例门；只提交 foundation 范围文件并等待 exact-SHA
  三 job。公共全绿后才开始 RQ-108 教学、设计和 TDD。

### 2026-08-25：foundation 提交前最新前端复验

- 清理了一个由本仓库遗留的 `vite --host 127.0.0.1 --port 4173` 进程，随后以 `CI=1` 隔离启动 E2E 服务；
  没有复用污染状态的旧服务。
- `npm run test:unit`：24 files / 136 passed；`npm run typecheck`：通过；`npm run build`：通过。
- production bundle：JS gzip `142.68 kB`、CSS gzip `18.50 kB`；JS 仍低于 150 kB 硬门。
- `npm run test:e2e`：36/36 passed，包含 Portal/Account/Workbench 旅程、双语、认证边界、SSE、Timeline、
  键盘/focus、reduced-motion、320/390/1024/1440 和 a11y/overflow 门。
- 该复验只更新 foundation 的本地证据；没有启动 RQ-108，也没有把当前静态 Portal 误称为最终视觉。

### 2026-08-25：foundation exact-SHA 公共闭环

- implementation/evidence `6084937833beed625dbc64fdcd4c8175edbc9d8f` 已推送；Actions run
  `32757872792` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。
- 公共 pytest 包含前端 typecheck/unit/build/E2E、完整 Python、两套 RAG、Harness、compile、治理和安全边界；
  真 PostgreSQL 与 Linux package/non-root/image/resource cleanup 也在同一 SHA 通过。
- RQ-102/104/105/106 foundation 正式关闭；8E parent coverage 仍 planned，不冒充完整 productization。
- `NEXT`：RQ-108 `portal-motion-polish` 当前 prepared/waiting authorization；授权前不写其 ADR/实现或素材 runtime。

### 2026-08-25：RQ-109 授权开始 RQ-108

- 用户明确“开始”，RQ-108 切为 authorized/in progress。
- 已先按教学合同说明问题、progressive-enhancement 原理、范围、控制流、测试和限制；当前进入只读 seam/
  资产/性能审计与 ADR-0068/设计，不提前写 runtime 动效实现。
- `NEXT`：完成 Impeccable animate 上下文、现有 Portal/Account/媒体/测试接缝与母图审计，冻结三方案裁决。

### 2026-08-25：RQ-110 视觉源纠正

- 用户把上一轮暗化截图设为明确 anti-reference；已同步两个并行只读审计，并新增视觉方向审计。
- 当前设计输入改为“确认高清母图 → 全屏 loop 正常体验 + 同源 poster fallback”，禁止阴影/暗幕/模糊/大字；
  多来源素材筛选与少字/字体意见继续有效。

### 2026-08-25：RQ-111 Account 英雄场景化纠正

- 用户允许五个位置各固定一个英雄，但明确拒绝头像式摆放。
- Account 母图改为峡谷光路连接五个全身能量幻影/晶体浮雕；统一蓝金材质、低对比纵深和有界轮流唤醒，
  不侵占右侧账号面板负空间。具体 roster 进入 ADR-0068/概念图审查。

### 2026-08-25：RQ-112 全局 loop 纠正

- 用户否决“全屏载体但仅局部运动”的解释；Portal/Account 正常模式必须是全帧环境循环动态。
- 当前设计将重写 storyboard 与媒体预算；poster 降为首帧/可访问/低流量/错误 fallback，DOM 动效只负责交互提示
  和点击后的汇聚/burst。

### 2026-08-25：官方英雄参考 URL 校验首错

- 为 RQ-111 准备官方 Data Dragon splash 参考时，ClawDefender 首次 5 个 URL 校验均在联网前失败：Windows
  `bash` 实际进入 WSL，`/c/Users/...` Git Bash 路径不存在。
- 无文件下载、无外部正文处理；下一尝试改用 `/mnt/c/Users/...` 调同一安全脚本，不重复原命令。

### 2026-08-25：Account 官方原画参考重做

- ClawDefender 使用 WSL 正确路径后确认五个 `ddragon.leagueoflegends.com` splash URL 安全；下载的 Camille/
  Kindred/Ahri/Jinx/Thresh JPG 均为 1215×717、合法 JPEG，并记录 SHA-256。
- ImageGen 首次尝试“母图 + 5 splash”因工具最多 5 个 path 在请求前拒绝；没有生成。改用 FFmpeg 将五图机械
  拼为 1824×718 参考板，再以“母图 + 参考板”生成 Account v2。
- v2 删除右侧走廊并让五英雄可识别，但用户审查发现整体拼贴感、金克丝右脚与千珏下半身等畸形，判为
  rejected 并移出仓库；不从该图继续修补。
- RQ-113/114 将制作流程改为“无英雄干净内殿 → 单英雄场景化重塑/逐项验收 → 分层合成 → 全局 loop”，
  官方 splash 仅作身份参考，禁止抠图换色。
- 已按新流程生成无英雄底座 v1，但用户指出峡谷被抽象成机械架子，已判 rejected 并移出仓库；下一轮必须
  加入官方 Data Dragon Summoner's Rift map 地理参考，尚未开始五个单英雄生成或 runtime 采用。
- 使用官方 `16.16.1 map11` 参考生成无英雄底座 v2：峡谷地貌已可辨识、右侧平墙留白成立；当前等待用户
  对底座方向签收，不提前生成/合成五英雄。
- 用户指出 v2 双方都为蓝色；按 RQ-116 对同一底座做单项 edit，v3 已明确左下蓝方/右上红方并保留中性河道、
  紫色男爵坑、暖色小龙坑。仍等待底座签收，不进入英雄层或 runtime。

### 2026-08-25：RQ-117/118 / RQ-108 design gate 本地完成

- `REQUIREMENT`：RQ-117 已追加并校准 RQ-115：保留官方三路/河道/双坑/基地/红蓝方向，但用有意概括的
  terrain masses/轮廓/符号节点表达地形，禁止伪造具体树墙塔等微型细节；v3 仍是未签收 preview。
- `REQUIREMENT`：RQ-118 取代早期水晶放大/重绘要求，确认母图原水晶/塔体/构图保持不变；放大 edit 与
  独立/CSS/贴图水晶均保持 rejected。
- `DESIGN`：ADR-0068 与正式 design 已同步 viewport-aware poster policy、playback sticky failure、archival
  source→runtime poster 感知一致性、Account topology/abstraction gate 和 preview/adoption 状态机。
- `PLAN/EVIDENCE`：新增详细 TDD implementation plan 与 design-stage 八维 walkthrough；coverage 继续挂在既有
  `8e-productization: planned`，不新增/重排 checkpoint，也不把计划路径冒充 runtime evidence。
- `BOUNDARY`：本批 `web/` runtime 修改、正式 loop、Account source adoption、Riot/OP.GG/Provider/LLM calls
  均为 0；没有继续生图。
- `NEXT`：完成 canonical/stale 同步和 design 比例门，独立 commit/push，等待 exact-SHA 三 job；公共全绿后
  才按 implementation plan 进入 media policy/component/activation TDD。

### 2026-08-25：RQ-119/120 Kimi 实测与替代路线设计

- `LIVE-LOCAL-AUDIT`：只读认领用户 Chrome 的 `localhost:7100`，确认 12s/1080p Kimi MP4 正常播放；临时
  提取视频做 ffprobe/六帧/首尾审查，仓库不保存视频。SHA `57043c...c95`，产品外部 calls 0。
- `RESULT`：母图→首帧 SSIM `0.412818`，人工 source/composition/texture/motion language 不通过；裁决
  rejected，不进入 source/runtime。完整 body-free 技术结果写入 I2V candidate audit。
- `RESEARCH`：官方资料确认 Wan 2.7 与 Veo 3.1 支持 first+last，Luma 有 Loop/keyframes，Seedance 2.x 有
  官方生成 API/reference，Runway/Firefly 可作多模型工作台；HyperFrames/Remotion 提供确定性 frame render。
- `DECISION`：设计横评扩为生成式、确定性、混合式，推荐混合式为 primary candidate；本批未安装 skill、
  购买/调用模型或改 `web/` runtime。NEXT 仍是修完 design review、跑门、独立 design exact-SHA。
- `LOCAL-GATES`：governance tests 12、frontend unit 136/E2E 36/typecheck/build、Python no-DB
  `1837 passed, 146 skipped, 1 warning, 127 subtests`、两套 RAG、Harness `published/0 revisions`、compileall、
  SDK/Secret/tracked-data/governance/diff 全绿；JS/CSS gzip `142.68/18.50 kB`。本机 Docker daemon/测试
  PostgreSQL 当前不可达，未把真库等待冒充代码失败，exact-SHA `postgres-migrations`/Linux job 仍是阻塞门。
- `INDEPENDENT-REVIEW`：两轮只读设计复核先发现并随后确认修复 mobile source、asset-before-integration、
  zero-prefetch、cover geometry、provenance/CSP、阈值、session-sticky/pause、RQ-120 ledger 等问题；最终
  blocker/major findings 为 0，可进入独立 design commit。

### 2026-08-25：RQ-108 design exact-SHA 公共闭环

- `PUBLIC-CI`：design `b3b5280cbcc81fa202b52f9cf8437e71956032ac` / Actions `32812868683` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 success。
- `PUBLIC-EVIDENCE`：frontend unit 136/E2E 36、Python 1838/145 skips/127 subtests、两套 RAG、Harness、
  governance/security、真实 PostgreSQL migration/control-plane 与 Linux package 同 SHA 全绿。
- `CLOSED`：ADR-0068、RQ-117–120、Portal provenance、Kimi rejected Bad Case、三路线 bake-off、媒体/激活/
  provenance/预算 TDD plan 与八维 planned evidence 取得公共设计证据；这不等于 runtime 或视频已完成。
- `NEXT`：进入 runtime Task 1 manifest/geometry/policy red tests；外部视频 skill/model/credits/Key 保持 0。

### 2026-08-25：RQ-121 中转目录补充（不打断 Task 1）

- 用户提供 Seedance/Kling/Grok/Hailuo/Sora/Veo/Vidu/Wan 的正规中转候选截图；已按“official first、relay
  secondary”记录采用门，目录 slug/`official` 后缀/价格不冒充厂商身份事实。
- 当前没有读取/写入 relay Key/base URL，没有上传母图或调用视频模型；Task 1 manifest/geometry/policy TDD 顺序不变。

### 2026-08-25：RQ-108 runtime Task 1 本地完成

- `RED→GREEN`：manifest/geometry 两个缺模块红灯；policy/hook 两个缺模块红灯；独立审查又用 legacy API 和
  render→commit preference race 复现 3 项红灯，均以最小合同修复。
- `IMPLEMENTED`：8 个新 TS/test 文件完成 strict 4-rendition manifest、cover/object-position/focal/hitBox math、
  760px viewport policy、poster/preflight、reduced-motion/Save-Data priority、useSyncExternalStore 与
  modern/legacy/StrictMode cleanup。无 production manifest、asset、video、network/storage。
- `LOCAL`：focused `71 passed`；frontend `28 files / 207 passed`；Playwright `36 passed`；typecheck/build 通过；
  JS/CSS gzip unchanged `142.68/18.50 kB`；Python no-DB `1837 passed, 146 skipped, 1 warning, 127 subtests`；
  两套 RAG、Harness published/0 revisions、compileall、SDK/Secret/tracked-data、governance tests 12/diff 全绿。
  两轮 independent final review 均为 blocker/major 0。
- `NEXT`：同步 walkthrough/canonical、governance/diff/比例门后独立 commit/push，等待 exact-SHA 三 job；
  公共成功前 Task 2 不进入，视频 skill/model/relay calls 0。

### 2026-08-25：RQ-108 runtime Task 1 exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `1b146e6116587b855a6208e998b5254eac8cba1d` / Actions
  `32826953474` 精确绑定；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `CLOSED`：strict 4-rendition manifest、cover/focal/hitBox geometry、760px viewport、poster/preflight、
  reduced-motion/Save-Data 与 modern/legacy/StrictMode listener 取得公共代码、真库与 Linux package 证据。
- `BOUNDARY/NEXT`：仍无 production manifest、`<video>` 组合、媒体资产或视频/relay/model 调用。唯一下一动作
  是 Task 2 `mediaSession` + `CinematicSceneMedia` 红灯；Task 5 bake-off 与素材采用不提前进入。

### 2026-08-25：RQ-108 runtime Task 2 本地完成

- `RED→GREEN`：先以缺少 `mediaSession`/`CinematicSceneMedia` 得到预期收集红灯；随后以 39 项聚焦测试冻结
  reducer、DOM、Promise race、visibility、pause、poster 和 StrictMode 合同。
- `IMPLEMENTED`：`mediaSession` 采用 controlled semantic events；组件始终渲染 poster，只有 motion 且非
  `failed-sticky` 才挂载 video。attempt token、play-request token、mounted guard 和 distinct poster/video keys
  防止旧 source、迟到 Promise、卸载事件及 React StrictMode 串台。
- `LOCAL`：focused `39 passed`；frontend `30 files / 246 passed`；typecheck/build、Playwright `36`、
  bundle `142.68/18.50 kB`、governance 与 Impeccable detector 全绿；无数据库环境下完整 Python 为
  `1837 passed, 146 skipped, 1 warning, 127 subtests passed`。
- `BOUNDARY/NEXT`：Task 2 尚未公共关闭；无 App import、production manifest/media、视频模型/relay/skill 调用。
  下一动作是独立 implementation/evidence commit 与 exact-SHA 三 job，Task 3 之前保持等待。

### 2026-08-25：RQ-108 runtime Task 2 exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `2111a7868bffb3d4d8525536afbb4c88cf8de1bc` / Actions
  `32833608622` 精确绑定；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `CLOSED`：media session 与 poster-first component 的状态、竞态、visibility、pause、StrictMode、旧 rendition
  和最小 cover/opacity 保障取得公共证据；公共门没有新增生产媒体或外部调用。
- `HANDOFF`：唯一下一动作切为 Task 3 单次 Portal 激活与跨幕 overlay TDD；Task 4 媒体审计、Task 5 bake-off、
  App 组合和生产素材仍按计划后置。

### 2026-08-25：RQ-108 runtime Task 3 本地完成

- `RED→GREEN`：先以缺少 `portalActivation`/`PortalActivationOverlay` 得到预期红灯，再补纯状态机、overlay、
  Awakening 受控语义和 ProductJourney 集成测试。
- `IMPLEMENTED`：generation/latch 使重复 click/Enter/Space/StrictMode/迟到 timer 幂等；reduced-motion 立即
  commit；popstate 取消并失效 generation；committed navigation 只 push 一次；overlay 在 Account mount 后有界退出。
- `LOCAL`：focused `27 passed`；frontend `32 files / 257 passed`；typecheck/build、Playwright `36`、JS/CSS gzip
  `144.07/18.50 kB`、governance 与 existing journey 门全绿。
- `BOUNDARY/NEXT`：Task 3 尚未公共关闭；未接 production video/media、Account source、Auth 新行为或视频模型/relay。
  下一动作是独立 implementation/evidence commit 与 exact-SHA 三 job。

### 2026-08-25：RQ-108 runtime Task 3 exact-SHA 公共闭环

- `PUBLIC-CI`：implementation/evidence `0198fc9efd64d99b0af3a90d3cf468d14120461f` / Actions
  `32836430378` 精确绑定；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `CLOSED`：单次 activation、reduced-motion/Save-Data、generation cancellation、唯一导航、focus handoff 与
  跨幕 overlay 取得公共代码、真库与 Linux 证据；旧 V1 视觉仍未签收。
- `HANDOFF`：唯一下一动作切为 Task 4 媒体审计器与预算门 TDD；Task 5 bake-off、生产媒体与 Account source 仍后置。

### 2026-08-25：RQ-108 runtime Task 4 本地完成

- `RED→GREEN`：新增 `tests/test_cinematic_media_contract.py`，先冻结 planned/adopted manifest、四 rendition
  matrix、policy/toolchain/anti-reference、codec/SSIM/seam/budget fail-closed 红灯，再实现只读审计器。
- `IMPLEMENTED`：`scripts/check_cinematic_media.py` 不联网、不转码、不上传、不写素材；固定 PATH `ffprobe`，
  通过显式 probe/digest 注入测试证明本地文件 digest/bytes/尺寸、poster/video schema、VP9/H.264、24fps、
  yuv420p/BT.709/no-audio、faststart/metadata/keyframe、SSIM/seam/dropped-frame 与预算门。
- `LOCAL`：focused `25 passed`；planned CLI `audit:cinematic`、frontend unit `257`、typecheck/build、Playwright
  `36`、Python no-DB `1862 passed, 146 skipped, 1 warning, 127 subtests`、RAG/Harness/compile/governance/npm
  official audit 全绿。
- `BOUNDARY/NEXT`：没有 adopted production rendition、Account source、视频模型/relay/HyperFrames 调用；Task 4
  尚未公共关闭，下一动作是独立 implementation/evidence commit 与 exact-SHA 三 job。

### 2026-08-25：RQ-108 runtime Task 4 exact-SHA 公共闭环

- `PUBLIC-CI`：implementation `52def9cf2384b8dc1161c4788f89a87c5f567ebc` 与 CI toolchain fix
  `d58ba154e6ee9d4b887401a9530a450052cae574` 的 run `32841900909` 三 job 全绿；此前 run `32841579832` 因 Ubuntu
  缺 ffprobe 以 exit 127 停止，保留为环境 Bad Case，未放宽审计门。
- `CLOSED`：planned/adopted media audit contract、fixed PATH ffprobe、codec/SSIM/seam/budget/toolchain 与
  anti-reference ledger 取得公共证据；仍没有 adopted media 或外部视频调用。
- `HANDOFF`：唯一下一动作切为 Task 5 三路线 bake-off；先冻结 official-first/relay-secondary 的候选映射、
  许可、隐私、费用、调用上限与失败停止规则，再决定工具/模型采用。

### 2026-08-25：RQ-108 runtime Task 5 preflight/design

- `RESEARCH`：定向复核官方 Veo 3.1 first+last、Luma Ray loop/keyframes、Wan 2.7 first/last/continuation；Seedance/relay 仍需实际 model mapping，未提升为准入事实。
- `DESIGN`：新增 `docs/plans/2026-08-25-8e-video-bakeoff-preflight.md`，冻结生成式/确定性/混合三路线、source fidelity/geometry/full-frame/seam/codec/privacy/cost 评分顺序、最多调用/首错停止和 body-free provenance。
- `BOUNDARY`：本批没有安装 skill、读取 Key、上传母图、购买 credits 或视频模型调用；下一步须先冻结实际账号/费用/敏感图边界。

### 2026-08-25：RQ-122 official/relay 广筛与 HyperFrames 隔离结果

- `RESEARCH`：DragonAPI 三个可见标签页已核对通用/媒体/模型广场；Veo 3.1、Seedance 2/2.5、Kling v3、Vidu Q3、
  Grok、Wan 2.6、MiniMax H3 均存在目录证据；官方 Wan 3.0 页面/用户截图又证明邀测 access 与 API 入口。
- `PERSISTED`：新增 relay admission、HyperFrames vetting；RQ-122、state、roadmap、capability、learning 和
  active plan 已同步；coverage 仍 planned，8E parent 未关闭。
- `SPIKE`：HyperFrames exact install 135 packages/no scripts；system Chrome singleton failure；cached headless
  shell check 0 errors/9 layout samples；raw frame 0/191 repeat SHA exact，raw seam SSIM `0.999600`；default
  H.264 5,650,074 B 与 seam DSSIM `0.039327` 均不通过。无产品代码、无 external model call、无母图上传。
- `NEXT`：Wan 3.0 official endpoint/region/Key presence body-free preflight；通过后再冻结一项实际 A1 请求，
  A2 保留 Veo/Vidu，Grok 3 等待 schema/mapping evidence。

### 2026-08-25：Task 5 admission/spike exact-SHA 公共闭环

- `PUBLIC-CI`：`7067ea1d2a9ebfb17d0cec1831b248404eee52e2` / Actions `32862942549` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- `CLOSED-SCOPE`：只关闭 official/relay candidate admission、RQ-122 correction 和 HyperFrames isolated spike；
  不关闭 Task 5/RQ-108，不产生模型调用或 production media。
- `HANDOFF`：唯一下一动作是 Wan 3.0 official endpoint/region/Key presence body-free preflight。

### 2026-08-25：RQ-123 executable preflight 本地完成

- official Wan/DashScope 与 DragonAPI 的 endpoint/model/access/Key presence 已核对；没有读取或复制 Key。
- 同一 Portal source 与 prompt digest、RQ-112 全帧 motion language、Wan→Dragon/Veo 单样本顺序、失败替补池、
  无充值/无重复提交边界已写入 executable preflight。
- 外部视频调用、母图上传和远程任务仍为 0。下一动作是独立 preflight commit/push/exact-SHA 公共门。
- Account v3 仍未签收；已把 Portal bake-off 后的 Account source/英雄/loop 固定为同一 Task 5 的阻塞后继。

### 2026-08-26：RQ-124 Portal source v2 本地迁移

- `7fe47db/32869447853` executable preflight 三 job 已公共全绿，但 v1 source binding 随后被用户清噪要求 supersede。
- 轻清噪 v2 已保存并签收；v1 不覆盖。provenance、audit manifest、auditor/tests、ADR/design/implementation、
  adoption ledger、coverage 与 canonical 已迁移；focused `26 passed`。
- 外部上传/视频调用仍为 0。下一动作是 source migration 独立 SHA/公共三 job。

### 2026-08-26：Wan 3.0 Portal v2 单样本完成并拒绝

- v2 migration `2a2da0e/32872452053` 已公共全绿；随后完成一次有效 free-quota Wan call，无重试/充值。
- 本地 MP4、0/2/4/6/末帧、region/full SSIM、adjacent p95/seam、ffprobe/watermark 人工审查已完成；结果因
  source identity、seam、coherent full-frame motion、水印与发布规格 rejected。
- 当前 external video calls 1；production media 0。下一动作是负面 audit commit/public gate，再进入 Dragon/Veo。

### 2026-08-26：Wan negative audit exact-SHA 公共闭环

- `69fc4ab/32876134114` 的 pytest、真实 PostgreSQL migrations/control-plane 与 Linux package smoke 三 job 全绿。
- Wan sample 正式 rejected；external video calls 保持 1，production media 0。
- 下一动作：Dragon/Veo A2 secure local runner 单次调用。

### 2026-08-26：Dragon/Veo A2 单样本完成并拒绝

- secure local runner 只执行一次 POST；Dragon 控制台 task 成功/100%/162s，Key 不落盘，外部视频调用累计 2。
- `/content` 对成功 task 返回 403；从同一 query response 的 `result.data[0].url` 恢复 raw output，下载恢复
  `post_attempts=0`。原始文件/兼容预览/抽帧/log 全部只在 research scratch。
- raw 1920×1080/24fps/8s/H.264 yuv444p/no-audio/254,156,130 B；source→first `0.587962`，seam DSSIM
  `0.161631 > 0.03`，人工全幕运动分布失败。样本 rejected，production media 仍 0。
- RQ-125 又修正路线：字段映射正确，但当前 prompt 过密且多处主动压低 motion，没有充分遵守 motion-only
  best practice；不把 sample rejection 外推为 Provider/A 线 ceiling。唯一下一动作是本负面审计独立公共门；
  随后优先 no-paid-call C proof，并保留校正 A comparator。

### 2026-08-26：Veo 负面审计 exact-SHA 公共闭环

- `e79a76ef8de82d56f3b97ba84623def8ea656a5b` / Actions `32918278259` 的 pytest、真实 PostgreSQL 与 Linux
  packaging 三 job 全绿；Veo negative sample 与 RQ-125 sample-reject/provider-open 裁决正式关闭。
- 当前唯一下一动作进入 C-line no-paid-call Portal proof；在 scene graph/mask/motion coverage/frame clock/A
  fallback gate 冻结并通过前，不创建新视频任务、不采用 production media、不跳 Account/Task 6。

### 2026-08-26：C-line Portal proof 设计冻结

- 设计比较校正 A、局部 CSS 与 scene-graph hybrid；C 只获优先 proof，不是不可逆采用。
- 冻结 8 个 motion systems、7.958333s/192 帧闭合时钟、source/seam/三分区/3×3 coverage/manual/budget 门，
  以及 `pass / fail-reopen-A / inconclusive-layer-gate` 三态 verdict。
- 计划只跟踪 composition/contract/renderer/tests；PNG/MP4/log/node_modules 全部留 repo 外，proof 前半程外部模型调用 0。
- 下一动作：design commit/push/exact-SHA 三 job；成功后才 red→green 实现。

### 2026-08-26：C-line proof design exact-SHA 公共闭环

- 最终设计 SHA `78ae6e3875cee7ad02b2dbbb607ea7ff1d98a3d8` / Actions `32919447127` 的 pytest、
  PostgreSQL、Linux packaging 三 job 全绿；前一 `be75112` 的 EOF 空行警告已由修订提交移除，不作为最终门。
- design gate 正式关闭；implementation 进入 Tasks 1–3，外部模型调用继续 0，输出继续 repo-excluded。

### 2026-08-26：C-line proof Tasks 1–3 与首个 render Bad Case

- contract TDD 为 `5 failed → 3 failed/2 passed → 5 passed`；tracked contract、8-system HTML/SVG scene graph 与
  isolated renderer wrapper 已实现，runtime/product media 未改。
- dry-run 验证 v2 SHA、HyperFrames 0.8.14、repo-excluded output、external model calls 0 和命令边界通过。
- 第一次 execute 在 HyperFrames `check` 120s 超时，未进入 PNG sequence/FFmpeg。诊断发现新 HOME 下工具自行
  建立 browser cache，而 wrapper 没有显式复用已验证的 cached headless-shell；这违反“渲染不下载浏览器”的
  意图。下一尝试必须先定位并绑定旧 cached shell，测试固定 env/path 后使用新 output dir，不原样重跑。

### 2026-08-26：C-line proof v2/v3 结果与 RQ-126

- wrapper 新增 explicit `HYPERFRAMES_BROWSER_PATH/PRODUCER_HEADLESS_SHELL_PATH` 和 UTF-8 subprocess；测试 6 pass。
- v2 完成 192 PNG，但暴露 `frame_`/start-number 编码路径 bug；修复后 v3 完整 wrapper 成功。
- v3 SHA `64cf285...0d95b`，3,895,112 B、8s/1080p/24fps/yuv420p/BT.709/no audio；raw frame 1/192
  byte-exact，raw source→first 0.982996，encoded seam DSSIM 0.026613，九宫格均有变化，external calls 0。
- v2 粗 HUD 明显；v3 降低线宽/opacity 后仍本质是母图上覆线条、圆环、节点，环境本身没有有机运动。用户
  明确拒绝；verdict `proof_fail_reopen_corrected_a`。下一动作是负面证据公共门，再执行一次校正 A comparator。
- RQ-127 把 comparator 视觉标准补成全幕 breathing 与明显 cool 动态：所有空间层/大区持续参与，允许小幅
  构图锚定 camera float/parallax，不再以完全 locked camera 和 subtle motion 压低幅度。
- C proof evidence commit `e215f7e` 首个公共 run `32922688081` 的 PostgreSQL/packaging 通过，pytest 以
  `1869 passed, 145 skipped` 后因新 proof fixture 无条件创建 Windows `hyperframes.cmd` 在 Linux 失败；实现本身
  未执行外部工具。修复按 `os.name` 创建 executable/browser fixture，并让 wrapper 接受无后缀 headless-shell；
  当前必须用新 exact-SHA 三 job 重新闭环，绿灯前不调用 corrected Veo。

### 2026-08-26：C proof 公共关闭与 corrected A preflight

- portable fix `557dac1` / Actions `32923151197` 的 pytest、PostgreSQL、packaging 三 job 全绿；负面 proof/RQ-127
  正式公共关闭。
- corrected positive 819 B/SHA `b02264...8e29`，negative 357 B/SHA `931f0b...a348d`，runner 7,136 B/SHA
  `cee5ac...ba850`；PowerShell parse pass。
- first-only/no lastFrame、one POST/same task/no retry、motion-only/full-scene/evident/cool 与 Key/body-free 边界
  已冻结。下一动作是 preflight 独立 public gate；尚未弹窗或创建 task。

### 2026-08-26：Corrected Veo task failure 与 Vidu Q3 Pro preflight

- corrected Veo task `task_c3y...77mT` one POST，158s/100% 后 failed；控制台只给 `task processing failed`，无
  output，不能评价 prompt，按首错停止不重跑。external video calls 3，production media 0。
- Vidu `viduq3-pro` 专用 schema 已核：单 image 为 first frame、8s/1080p、aspect_ratio 16:9、audio false、seed 127；
  不用 metadata/payload/off-peak/callback。
- Vidu motion-only prompt 1,007 B/SHA `a38bdc...bb72`，runner SHA `60e4f8...24f5`，PowerShell parse pass。
- 下一动作是 failure + Vidu preflight 独立 public gate；绿灯前不弹 Vidu Key 窗口。
- RQ-128 纠正 failure adjudication：corrected Veo 无 output，fault domain 保持 request/relay/upstream unresolved；
  Vidu 只改变 model/schema 并保持其余变量。如果 Vidu 也 generic failed，必须停下审计 relay/request，不能再换模型。

### 2026-08-26：Vidu generic failure 与 minimal request hypothesis

- Vidu task `task_yaHF...KF90` one POST，queued 160s 后 failed/100%，控制台同样只给 `task processing failed`；
  无 output/quality unknown，external calls 4。
- source HEAD 200 image/png/2,268,033B、Range 206；local auth/create、model ID 与核心 schema 正常。
- Studio 登录态只读审计证明 Vidu Q3 Pro/首帧/8s/1080p/16:9/5.28 额度存在，但 `生成音频` 固定开启；提示词
  增强可关闭且已关闭。隐藏 input 上传 chooser 两次连接失败，未上传/生成/扣费，不继续死磕 UI。
- 唯一 API 重试改为 Studio-contract：删除 seed、audio=true、保留 aspect_ratio；runner SHA `7f6d2e...0011`。
  若再 generic failed，停止模型/API 切换，转平台 task-id/official transport 诊断。

### 2026-08-26：Vidu Studio-contract 成功与 RQ-129

- audio=true/no-seed 后 Vidu completed；output SHA `6e1ce9...251a`，12,616,484B、8.0417s/193f/1080 container/
  H.264+yuvj420p+AAC，AIGC metadata ProduceID 却含 720p。
- source→first 0.790736、seam DSSIM 0.425097；九宫格变化大，但视觉主要依赖 camera push/global drift，用户
  正确拒绝。证明 API/first-only 可工作，也证明 pixel motion 大不等于目标正确。
- RQ-129：目标是 locked-frame refined animated matte painting，景内多层同时中强度运动。下一对照保持成功
  Veo first=last/model/transport/source，只重写 refined storyboard；Seedance/Grok 后置。
- Veo positive 1,277B/SHA `4dbdf0...41f9`，negative 435B/SHA `b6d7b4...9cbd`，runner 6,804B/SHA
  `70332e...8406` parse pass；尚未调用。

### 2026-08-26：Veo refined POST 403 与账单门诊断

- refined runner 在提交阶段直接 403，`task_id=""`、无任务/输出/质量结论；没有扣本次生成费用。
- Dragon common log 已证实当时 `$15.008 < $19.712` 导致预扣失败；同时间四条 pipeline 日志不是四个 task，
  task log 仍为原 4 项。用户充值 `$50` 后余额 `$65.01`，billing gate 已满足。
- 之前成功的 Veo/Vidu task 与本次不同：这次未进入上游，不能把 403 写成模型或 prompt 失败。
- RQ-130 又明确付费前必须把提示词/约束和请求做到 ready，不能因余额足够直接发。
- v5 positive 1,478B/SHA `99cce1b...e72a6`、negative 551B/SHA `310b281...b8ab`；motion-only/单镜头、
  locked/deep-focus/crisp linework、left/center/right + near/mid/far simultaneous、八秒 phase/illumination/velocity
  闭环与 unwanted-phenomena negative 已完成静态 preflight。
- source remote HEAD 200 image/png/2,268,033B、local/expected SHA 一致；runner SHA `70332e...8406` parse 0 errors；
  retry1 output/status 均不存在。下一步先独立 commit/public gate，再 one POST/no retry。

### 2026-08-26：Veo v5 one-task upstream failure

- preflight `d57b026` / Actions `32951125621` 的 pytest、真实 PostgreSQL、Linux packaging 三 job 全绿。
- 唯一 task `task_I5iJQDEiEOpZtsQCSOi3qELNTMFAk9Mw` one POST 创建；159 秒/100% 后 generic failed，无 output。
- source/prompt/negative digest 与请求合同匹配；relay 接受 task，但没有足够证据区分 schema 语义与 upstream；
  successful-output quality/method 保持 unknown/open。
- `$19.712` 先扣后全额异步退款，钱包最终 `$67.01`；calls 6，production media 0。
- 用户输入 Key 时父终端被误关是本地操作事故；子 runner 已 POST 后退出，未产生第二 POST；status 已按远端终态修正。
- 下一步只关闭审计，不重发或换模型；需 task-id 诊断、transient 证据或新可证伪假设才重开调用。
- audit `ac76f74/32952793297` 三 job exact-SHA 全绿；当前下一动作收敛为零成本 task-id/platform diagnosis
  decision gate。可先准备 body-free support packet，但代表用户发送给 Dragon 前必须单独确认。
- support packet 与 QQ 视频管理员私聊草稿已准备但未发送；用户选择 Studio，故保持未发送。
- Studio 已预设 Veo 3.1 Quality Official、首尾帧、8s、1080p、16:9、enhancement off、预计 19.71；Chrome
  file chooser 因扩展 file URL permission 未捕获，确认 0/2、无上传/调用。RQ-131 改由用户按手动 handoff 操作。
- v5 Studio task `task_Rdr...maHP` 93s/100% generic failed，无 output，19.712 全退；calls 7、production media 0。
- exact diff 显示早期成功 v1 要求 subtle/slow/restrained/almost imperceptible；后续失败 v2/v5 同时要求整幕
  medium/strong motion。用户拒绝 QQ，并授权 exact v1 Studio reproduction；参数/prompt 已填，等待 2/2/public gate。
- exact v1 reproduction 仍 generic failed/no output，证明 v5 constraint 不是必要原因；Veo 当前通道暂停，calls 8。
- Studio contract compare：Seedance 2.5 first+last + exact 8s/720p，Kling V3 first+last/10s/720p，Grok 3 无尾帧。
  Seedance primary 已填 v5/2 images；按钮 `--`，catalog 预计 11.9568，未生成。
- Seedance 首次 submit 在 task 前返回明确 ratio constraint；费用 0。Studio `adaptive` 是可证伪修复，已选择并
  恢复 prompt/其它参数，等待用户重新 2/2；若再 ratio error 即停止该 Studio mapping。
- adaptive task `task_w6...ULvW` 137s/100% NewAPI success；Studio 403 仅 result fetch，GET-only 恢复 output。
  SHA `acf68ba6...d56c4`，720p/24fps/8.041667s/5.43MB/no-audio。source-first 0.864923、first-mid 0.852572、
  seam diff 0.060443；三大区均运动、镜头初审稳定。等待用户视觉签方向，不 adopted/不重抽。
- 用户担心 Video1 放大现有雾层；v6.1 改为 double-anchor：Video1 保留运动，Image1 锁原几何/材质，严格只改热图
  静区。prompt 2368B/SHA `9cdcf28e...64ac8`，runner `08834b8a...173b0` parse 0；1 POST/2 GET，
  source task GET→临时 result URL→edit POST→poll/download，不保存签名 URL，预计约 12.0191。该条为执行前
  冻结记录；随后 POST 400/费用 0 见下节。

### 2026-08-26：Seedance v6.1 submit 400 与官方即梦只读预检

- `LIVE-SUBMIT-REJECTED`：source GET 成功；edit POST 返回 HTTP 400，task id 空、output 无、费用 0、task log
  无隐藏任务。calls 继续 9，production media 0。
- `INCIDENT`：原 runner 只保存 HTTP status，response body 丢失；旧 ratio common-log 行不能冒充本次错误。
  当前 fault layer 只到 request/schema，exact field unknown。
- `RED→GREEN`：`tests/test_dragon_video_error.py` 从缺模块红灯到 3 passed；strict sanitizer 对合法 nested error
  投影 code/param/type/bounded message，未知或敏感形状 digest-only。
- `NO-I/O`：revised runner SHA `e7eb8c9...c0807f`，sanitizer SHA `f5c4f67...58f5a`；PowerShell self-test 通过，
  静态 1 POST/2 GET，唯一 output/status 不存在，未重试。
- `OFFICIAL-UI`：即梦官方五模式已只读比较；Seedance 2.5 `智能编辑` 提供单 MP4/MOV 编辑视频槽 + 多参考槽、
  自动比例/时长和 720P，最贴合双锚点。未上传、购买或生成；不先订高价会员/API 套餐。
- `DOUBAO-WORK`：首发 30 天标准套餐有客户端/公开发布交叉证据，当前账号显示标准套餐；Seedance 2.5 以
  月度额度、附件+prompt 触发，没有即梦同等显式模式/高清度控件。未读到期日/剩余额度，未上传或调用。
- `DOUBAO-LIVE`：用户授权后 only one Seedance 2.5 comparator completed。Skill 抽原片首尾帧 + v2 母图进行
  image-to-video，不是真 edit；输出 SHA `e4b2f91...352cf`，720p/24fps/8.041667s/AAC/移动水印。
- `REJECTED`：source-first 0.407604、seam diff 0.144582；暖金光轨有可迁移动作语言，但重绘 source、色彩冲突、
  三主体内部/整体环境 motion 不完整。calls 10、production media 0，不重跑豆包。
- `RQ-134/NEXT`：三主体全部增强（右侧单列）+ 整体环境同步增强；光轨转冷蓝/青蓝、暖金低占比。下一即梦
  `智能编辑` 文件由用户选择；Codex 只在上传后读回参数/积分并填修订 prompt，生成前不点。
- `RQ-135/PREFLIGHT`：第一轮只用成功 MP4 + v2 母图，不堆审美参考；v7 prompt 1,439 chars/4,115 bytes/SHA
  `edbc0d3...6f388` 已冻结。Chrome 插件重装/重启后 general connection 恢复，但即梦页仍页面级超时。
- `ADVANCED-EDIT/RQ-136`：用户指出高级编辑需具体到时间点；公开教程与 ByteDance timestamp 能力复核后，旧
  单帧 note 作废。当前为 00:00/00:04/00:07 三个独立帧标注，分别表示启动/峰值/回收；每次定位→暂停→标注→
  写时点说明→添加至输入框。右侧每次都在完整矩形内，不使用文字工具、不增加第三张图。
- `NEXT`：先提交/push 本 diagnosis/audit/preflight 批并取得 exact-SHA 三 job；全绿后用户手动上传，Codex按
  截图/页面读数复核模式、素材、积分、高级编辑、音频和 prompt，再决定唯一生成。
- `NEXT`：先独立 implementation/evidence commit 与 exact-SHA 三 job。公共闭环后，relay 需精确 error body/
  可证伪字段才重开；官网需先上传后读回实际积分和参数，再决定一次智能编辑。

### 2026-08-27：即梦 Smart Edit raw 与零费用 post-process

- 用户在本 evidence batch exact-SHA public-close 前手动完成 official JiMeng `Seedance 2.5 / 智能编辑`；执行
  顺序偏差已写入 audit，未倒写历史。
- 实际 compact main prompt 534 chars/SHA `d003f047...cff10`；三个 timestamp instruction 独立 digest，稳定
  placeholder projection SHA `6dcd29d4...9d411`。长版 `edbc0d3...6f388` 只保留 design intent。
- raw output SHA `4d3660b...155b`：三大区/九宫格均变化且 camera/architecture 初审稳定；v2-first 0.889072、
  seam 0.046536、AAC/non-fixed-fps fail。calls 11、production media 0、verdict revise-candidate/not-adopted。
- A–P repo-excluded FFmpeg 对照完成。delivery contract 可修；最佳 J fixed24/no-audio/BT.709/2.99MB，SHA
  `dadd7c3...a0b37`，但 seam 0.042684、mother-first 0.849216，reject runtime。停止 crossfade/settle 追绿。
- 新增 `2026-08-27-8e-jimeng-seedance25-smart-edit-result-audit.md`，同步 preflight/ledger/state/roadmap/
  amendment/matrix/decisions/learning/coverage/active plan；当前开始本地门。
- `NEXT`：本批 local gates → independent commit/push → exact-SHA three jobs；公共成功后 no-cost identity fault
  split，不先重生成。

### 2026-08-27：本地门与 Portal-first 顺序

- RQ-137 明确当前先完成 Portal，不把 GLM-5.3/Flash 插入当前脏批；模型采用门保留为 Portal 闭环后的高优先项。
- focused media/error/governance `42 passed`；无 DB 全量 `1873 passed, 146 skipped, 1 warning, 127 subtests`。
- Docker Desktop 4.87 backend 因 stale `sailor-ingest.sock` reparse point 无法删除而崩溃，PostgreSQL 54329
  不可达；普通移动/删除与 fsutil metadata 清除均被系统拒绝。未做 factory reset、未删镜像/卷/WSL 数据。
- 两套 RAG 满门、Harness `published/0 revisions`、compileall、pip check、SDK/secret/tracked-data、planned
  cinematic media audit、governance 与 diff check 通过。真库证据必须由 exact-SHA public job 补齐。

### 2026-08-27：Portal T/X identity fault split

- 对已存在的 source-anchored T (H.264) / X (VP9) 研究候选，统一使用 active v2 缩放到 1280×720 后的
  yuv420p/BT.709 口径，补齐了 geometry/edge、material/color、intended energy/light 三层证据。
- 母图直接编码→解码 baseline SSIM 为 `0.995139`；T/X 首帧分别为 `0.954464/0.958294`，edge correlation
  为 `0.995571/0.997081`，说明大结构仍稳定，不能把 source-first loss 简化成“整图重绘”。
- q95 WebP poster 的母图 SSIM 为 `0.987838`；poster→T/X 首帧为 `0.992257/0.988248`。AVIF 候选低于
  poster gate，暂不选用。T/X seam `0.027807/0.029357` 均在 `0.03` floor 内，但仍未过浏览器两轮与人工签收。
- 三大区及 near/mid/far 的时域亮度变化均大于 0；该证据证明 coverage，不证明自然材质运动。完整数值写入
  `docs/assets/8e-portal/portal-motion-candidate-tx-v1.json`，候选仍是 research-only/not-adopted。
### 2026-08-27：RQ-138 motion direction gate

- Prior evidence/audit public CI is green (`33042204532`); production media remains `0`.
- Rejected the three AutoGLM concept images as non-source-preserving, watermarked, and visually off-target.
- Added provisional motion direction plan and compact first-frame prompt. After correcting the stale proxy port to the
  active user port `12000`, two mother-image edit previews completed; a third request returned `403 insufficient balance`
  and was not retried. No video request was made.
- Next action: review the two previews against the exact mother SHA, then decide whether a single first-frame video
  preflight is justified; do not treat either preview as a new master or runtime asset.
- Review result: both previews are effectively color/brightness variants and fail the intended static motion-direction gate;
  keep the exact mother as the only source and do not spend another Image2 request until a non-color-changing edit brief is
  explicitly prepared.
- RQ-140 now allows skipping Image2 entirely. Added a first-frame-only regeneration preflight with a shorter positive
  motion brief and bounded negative brief; current state is prepared, waiting for model/price/source readback before one
  video call.

### 2026-08-27：Seedance 2.5 v3 result review / RQ-141

- v3 was submitted once with the confirmed v2 source, first-frame-only, `adaptive`, 720p, 12 seconds and audio off.
  Codex restart interrupted local polling at 50%; a fixed-task GET-only recovery downloaded the existing result with
  zero recovery POSTs. Output SHA `76be77750c8932666117e2e3ecdbb0e9fc1b3e845bb41f66532eb8802d1d2a04`.
- The 12-second file is technically playable (1280×720, 24 fps, H.264/yuv420p, no audio) and has an obvious middle
  event, but visual review rejects it: the Rift resolves into hard concentric rings, road flow starts late, the center
  event is an overexposed white flash with crossing beams, the right field is mostly static outside the event, and the
  near/mid/far environment lacks a stable breathing rhythm. It remains research-only and is not runtime media.
- RQ-141 narrows the next contract before any new paid call: baseline road/Rift-underflow/right-field/building seams/
  reflections/clouds/air must move continuously from frame 1; the burst is a restrained 2–3 second central vertical
  pulse that gently excites the crystal and returns to baseline; no cross-frame straight-line network, HUD-like drawing,
  white exposure spike or burst-only right-side activity. Next action is brief/contract revision, not blind regeneration.

### 2026-08-27：v4 source-side contract / no-cost preflight

- 将 v3 的错误时序拆开：常驻基础层从首帧起让左 Rift、道路下方、中央水晶/平台、右星图/地形与
  near/mid/far 环境持续运动；中央事件只保留 4.5–7.0 秒的圆润纵向呼吸，不再写跨画面汇聚或连线。
- prompt 已落盘并完成 SHA 绑定；v4 runner 从仓库读取 prompt、校验 digest、固定 source SHA 和
  `adaptive/720p/12s/first-only/audio-off`，静态解析 0 error 且只存在一个 POST 调用点。未运行 runner，
  未读取 Key，未创建远端 task。
- Image2 刻意跳过：已有两张稿只证明调色/提亮，不能回答时间编排问题；只有未来出现静态遮挡/反射 Bad Case
  才做功能性同构 keyframe。当前等待付费调用门，不把 v4 预检误写为视频质量证据。
- `0006858` / Actions `33078261349` 的 exact-SHA pytest、真实 PostgreSQL migrations、packaging-smoke 三 job
  已全部成功；v4 文档证据正式公共闭环，视觉采用门与 production media 仍保持未完成。
- 首次执行 v4 runner 在本地 prompt digest 门发现 Windows CRLF 与末尾换行差异并安全停止；修复为 LF 规范化后
  parser 0 error、唯一 POST 1，未产生 task/费用。Dragon pricing readback 为 `¥1.494570/s`，12 秒估算
  `¥17.934840`，已写入 manifest；修复后的公共 gate 随后通过并再执行唯一一次 v4。
- v4 通过公共 gate 后实际只 POST 一次并下载成功（task `task_s03TcAumrRVriOhr3qj7RxigZqBRLnYF`，输出
  SHA `1fab5d0f10efe13402f8d31ddfa136ecc68c19875ca4d6a092982d4a1f49cb02`）。审查确认 prompt/mode 把变化
  集中到中央发光圆顶，左 Rift、右场和整体环境未形成持续运动；按 RQ-142 rejected，production media 仍为 0。
- `c964016` / Actions `33083670925` 的 exact-SHA 三 job 已全部成功，v4 失败审计正式公共闭环；下一步只做
  prompt/mode fault split 与方法裁决，不继续盲目付费重抽。

### 2026-08-28：RQ-142 method fault split

- 证据表明 v4 的问题不是下载/编码：source→first `0.989914`、first→last `0.994464`，但运动集中在中心圆顶；
  首帧模式没有提供足够的区域/时间控制，抽象词又与平台几何锁定冲突。
- 已形成三路线裁决：A 首帧 I2V 暂停；B 真实视频编辑 + 三时间点 mask 为下一优先；C 采用母图锁定的纹理/位移型混合
  作为 fallback，避免重演线条/HUD proof。下一步只做 B contract/no-cost preflight。

### 2026-08-28：B1 Smart Edit contract preflight

- B1 主 prompt 1,977 字符，三时间点说明与 Video1/mother 双锚点 digest 已绑定；中心只允许水晶/现有光柱
  局部呼吸，平台几何不可变，左/右/环境从首帧持续运动。
- 当前仅完成文本与 manifest 预检，未上传、未付费、未调用；下一步先 readback 页面是否保留这些时间/区域输入。
- 即梦页初始只读快照确认默认是 `全能参考`；后续语义 DOM、可见 DOM 与截图均因扩展/页面超时未完成，未点击
  Smart Edit、未上传素材。当前保持 readback blocked，不把页面能力猜成已验证。

### 2026-08-28：B1 defer / C' hybrid material proof

- 对照旧 Smart Edit 记录后确认 B1 不是新方法，只是 prompt ablation；不重复上传或付费。
- 新路线 C' 设计完成：母图结构底 + 各区域遮罩内低频纹理位移/折射/分层视差 + 确定性时钟，明确禁止旧 C-line
  的线条/HUD 叠加。下一步实现本地 contract/TDD 和 research proof，不调用外部模型。

### 2026-08-28：C′ proof rejection / Kling candidate

- C′ 已渲染并审查：left/center/right 0→4s 变化均衡、结构和编码通过，但视觉运动太轻且 mask 边界有贴层风险，
  按用户目标 rejected；不继续调 opacity/位移。
- 依据“失败后先归因再换方法”原则，下一候选改为 Kling v3 Omni 单图片引用，不复用 Seedance/Smart Edit prompt。

### 2026-08-28：Kling v3 Omni preflight

- Kling 专用 image-reference prompt 已压至 1,833 字符，绑定母图 SHA、`metadata.image_list` 与
  `<<<image_1>>>`，并冻结 8s/std/720p/16:9/audio-off；价格 readback 为 ¥0.462/s，估算 ¥3.696。
- runner parse 0 error、唯一 POST 1；当前未上传旧视频、未调用 Kling、未扣费，等待页面/账户 readback。
- `cc35fae` / Actions `33098493865` 的 pytest、真实 PostgreSQL migrations、packaging-smoke 三 job 已全部成功，
  Kling preflight 公共闭环，仍保持 post observed 0。

### 2026-08-28：Kling v3 Omni image-only result

- Kling 只 POST 一次并成功下载（task `task_7iQRNXGQRrnbk1KdW6WYDpG1dRSoZHC0`，output SHA
  `3eb0720c1b80d02ab43f8975f765c0444b1dd40239fad4fe5bfe43ff483c7fc6`）；首帧 source SSIM `0.860618`。
- 左 Rift 变成廉价厚环，中心强光柱，右场/环境静止；按 source/full-scene/人工门 rejected。下一步停止 image-only，
  只评估 reference-video/多模态控制或其他模型 preflight。

### 2026-08-28：Kling video+image B2 preflight

- B2 以历史 Seedance success task GET-only 取得 Video1 临时 URL，v2 母图为 Image1；临时 URL 不写盘。
- Kling 专用 prompt 明确保持 Rift 原不规则边界，禁止 solid torus、gold star decoration 和 solid laser block；
  runner/price/schema/source digest 已完成静态门，当前 GET/POST 均为 0。

## 2026-08-28：Kling v3 Omni video+image B2 result review

- 已完成唯一一次 B2 生成并用 GET-only recovery 下载；两次瞬时轮询异常后完成，未重复 POST。输出为
  8.041667s/1280×720/24fps/H.264 Main/yuv420p/no-audio，SHA
  `5a9509ee3efdd2dbc0e8264bba88bba1315f3880e2c0932c8ac56da56f02cbba`。
- 首帧身份/编码门通过，但视觉门拒绝：左 Rift 塑料环、中央硬亮柱、右场/远景和整体材质运动不足；候选审计
  与复盘文档已落盘，production media 仍为 0。
- 用户要求暂停并完整复盘；下一动作不再是付费生成，而是 method-review-hold 下的 no-cost 分层材质载体证明。

## 2026-08-28：source-derived layer assets proof v1

- 新建 source-derived layer renderer/contract/tests，聚焦测试 `3 passed`；本地完成 1920×1080/24fps/8s/no-audio
  proof，外部调用 `0`。底图清晰、无全屏纱罩，亮部层可独立检查。
- 人工结论为 `foundation-pass-with-visual-boundary`：运动仍偏弱且缺少真实 occlusion/backplate，不进入 runtime。
  证据 JSON 已落盘，下一检查点为 `material-plate-generation-gate`，先补独立材质 plate 再回到合成。

## 2026-08-31：RQ-171 GLM-5.3-Flash 适配器修复与 G53-5 准备

- 用户明确要求先修复 GLM-5.3-Flash 适配器，再在普通 API Key 可用的前提下尽可能全范围真实测试；旧 G53-4
  的首错考卷与脱敏结果不可覆盖，也不因本批改变默认模型。
- 本地实现将 Flash profile 设为 `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`；
  中立消息的 `reasoning_content` 只在内部保留并精确回放，公开投影不暴露；多个 ToolCall 按原顺序进入
  AgentLoop 顺序执行，能力声明继续不承诺并发。
- 适配器/模型/探针/AgentLoop/上下文的离线聚焦回归已通过（计数以本轮终端记录为准）；这不等于真实模型质量。
- 下一步是新的 `g53-5-fresh-flash-capability-gate`：使用独立输入/输出身份、有界预算和脱敏产物，覆盖文本、
  思考回放、结构化输出、多 ToolCall、上下文与 Agent 链路。真实 Provider 调用仍 pending；Stage 8/8E
  保持 `in_progress`，Workbench/Auth/前端和 `production_media=0` 不变。

## 2026-08-31：RQ-170 G53-4 真实领域门执行

- no-I/O preflight 通过：全新匿名三案例、Input Plan、Prompt/Context snapshot、G53-3 协议结果、SHA 与预算
  均一致；没有构造 Provider 或读取凭证，`external_provider_calls=0`。
- 用户授权后只执行一次真实门。首案第 1 次 Provider 响应触发 `unsupported_parallel_tool_calls`，Adapter
  fail closed；没有进入工具执行、RAG/Evidence、Evaluation 或发布，剩余两案立即 skipped，不重试。
- 结果：领域 `1/12` calls、`0/12000` normalized tokens；累计含协议 `4/15` calls、`1115` tokens；费用
  状态为 `unknown`。不可变结果 SHA-256 为 `ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`。
- 聚焦测试 `5 passed`，结果 schema 解析通过。结论为 `admitted=false` / `completed-local-rejected`；不改默认模型、
  Workbench、Auth、前端或 `production_media=0`，不在已见考卷上重跑。

## 2026-08-31：G53-1 GLM-5.3-Flash 适配档案离线 TDD

- 按 RQ-165 将官方普通 API 合同落实为独立 profile：`glm-5.3-flash` 使用
  `thinking.type=enabled` 与 `reasoning_effort=low`；GLM-5.2 和未知测试模型继续使用
  `thinking.type=disabled`。没有改 `.env` 或默认模型。
- Provider、capability probe 与 CLI 共用 profile；Flash 文本/结构化 reasoning 不进入中立响应，
  工具回合因缺少回传字段继续 fail closed；并行 ToolCall 边界保持原样。已知模型的 probe 默认
  输出文件名前缀隔离，旧结果不覆盖。
- 聚焦回归 `70 passed, 29 subtests passed`；compileall、`git diff --check`、governance 通过，
  外部 Provider/Riot/OP.GG 调用为 `0`。下一步是 G53-2 exact-SHA CI，不是 G53-3 真实调用。

## 2026-08-31：G53-2 exact-SHA 公共 CI

- 提交前将 profile、Provider、probe、CLI、registry 与 worker composition 聚焦回归扩到
  `82 passed, 29 subtests passed`；compileall、cached diff check 和治理检查均通过。
- 仅暂存并提交 9 个 G53 代码/测试文件：`0f97b92683e4981842e745a695864deb611bb630`
  (`feat(provider): add isolated GLM-5.3 Flash profile`)；现有 Portal/Account/文档/截图/资产改动全部保留在工作树。
- 推送后 Actions run `33325222755` 精确验证同一 SHA；`pytest`、`postgres-migrations`、
  `packaging-smoke` 三个 job 全部成功，公共 Python 汇总为
  `1912 passed, 145 skipped, 1 warning, 127 subtests passed`。
- 本批没有真实 API 调用、Key 读取/输出、默认模型或 `.env` 修改，也没有改 Workbench/Auth/路由/媒体采用。
  G53-2 标记 `completed-public`；下一指针为 `g53-3-bounded-protocol-gate`，等待用户单独明确授权。

## 2026-08-31：G53-3 有界真实协议门首次尝试

- 用户“继续”触发一次、最多三次的普通 API 协议门；进程临时覆盖 `zhipu` + 普通端点 + `glm-5.3-flash`，
  现有 `.env`、默认 `zhipu`/`glm-5.2` 和工作树代码均未改。
- 第 1 次 A1 结构化请求返回 `authentication_failed`，A2 被安全跳过；报告 `calls_used=1/3`、
  `admitted=false`，没有重试或追加调用。结果文件为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol.json`，已通过 schema 校验。
- 结果 SHA-256 为 `b10827f18dc810085a0d3883ebb7175709f4c244c30c937d5d220ab1ec1d0d9a`；聚焦协议/能力/Profile
  回归 `36 passed`。该错误码不能区分 Key 无效、权限不足或端点接缝错误，不能据此进入领域门。
- 本批下一动作改为等待用户确认/修正普通 API 凭证接缝并明确是否重开 G53-3；不自动使用剩余 2 次预算，
  不进入 G53-4，`production_media=0` 与 Workbench 边界保持不变。

## 2026-08-31：G53-3 更换普通 API Key 后重开通过

- 用户确认旧 Key 已删除，创建新普通 API Key，并将 `.env` 的 `LLM_PROVIDER`、普通 API 基址和模型名改正；
  本轮未输出或记录 Key 值，前两次脱敏失败结果保留。
- 预检无网络且通过；真实 `adapter_protocol` 严格使用 3 次调用：A1 结构化合同 1/1 通过，A2 Agent 工具往返 2/2
  通过（1 次 ToolCall/执行），`admitted=true`。
- 脱敏结果为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json`，
  SHA-256 `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`；聚焦回归 `36 passed`。
- G53-3 标记 `completed-public`；不自动进入 G53-4。领域质量、默认模型切换、生产媒体、安全部署和 8F 仍未完成。

## 2026-08-31：RQ-163 Agent 主线交接与 README 事实版

- 已按用户确认把 Portal/Account 视觉切片阶段性收口，执行重心转回 Agent；本批没有改 `app/`、`web/`、Workbench、
  Auth、路由、默认模型或媒体运行时。
- 新增 Agent 主线交接实施计划和八维 walkthrough；README 已补充 8A–8D 完成边界、8E/8F 状态、GLM-5.3 G53 闸门、
  受限 Coach 缺口和安全/部署限制。RQ-067 与 RQ-085 的两个 README 任务已明确区分。
- 已更新 requirements、canonical、roadmap、learning index 与 coverage evidence；治理和差异检查待本批最后统一运行。
- `production_media=0` 保持不变。下一候选为 `g53-0-no-io-audit`，本批不提前执行 Provider I/O。

## 2026-08-31：G53-0 GLM-5.3 无 I/O 审计

- 按 RQ-164 执行本地静态审计：复核 G53 设计、ADR-0023/0028、`.env.example`、`compose.yaml`、Zhipu
  settings/Adapter/probe、CI 与历史脱敏结果；没有读取/输出 Key 值、创建 Provider client 或发起外部调用。
- 确认产品默认仍为 `LLM_PROVIDER=zhipu`、`LLM_DEFAULT_PROVIDER=zhipu`、`LLM_MODEL=glm-5.2`；旧 Adapter 和 probe
  固定 `thinking=disabled`，尚无 GLM-5.3 profile、model allowlist 或账号/Plan/region 合同。
- 本机 `.env` 只做遮罩式非敏感核对：Key 记为 present，provider/端点/model 为 `glm`、Coding Plan 形态端点、`glm-5.2`；
  `glm` 与当前 loader 的严格 `zhipu` provider 合同不一致。账号权限、正式 model ID、endpoint/region 和 `enabled + low`
  可用性继续 unknown。
- 聚焦 Zhipu/settings 与 registry 回归为 `.venv\\Scripts\\python.exe -m pytest -q tests/test_zhipu_provider.py tests/test_provider_registry_config.py`：
  `32 passed, 29 subtests passed`；Provider/evaluation compileall、治理检查与 diff 检查也通过。工作树既有 Portal/Account、文档、截图和未跟踪资产全部保留。本批结论为
  `completed-local / blocked-deferred`，不把它写成模型失败或准入成功；后续需非敏感账户证据后再决定 G53-1 离线 TDD。

## 2026-08-30：RQ-161 Account panel / control typography hygiene

- `account-access__panel` 的桌面位置改用独立 `top` 微调上移，`<=760px` 归零；既有 handoff transform、焦点时序
  和 Account 路由不变。
- Riot ID input 与两个原生 select 统一 Manrope body/560/0.95rem，三条 caption 统一到可读字阶；补充
  computed-style E2E，避免浏览器原生 input 回退 Arial 后再次出现视觉断层。
- LOCAL：Account focused unit `3/3`、frontend unit `297/297`、完整 E2E `50/50`、typecheck/build、live DOM、
  Impeccable detector、governance 与 diff check 均通过。历史记录中的 E2E `49/49` 保留为当时事实。
- BOUNDARY/NEXT：Workbench 未改，8E/媒体采用仍未关闭，`production_media=0`；继续用户视觉复核及来源/许可、
  production rendition/fallback、最终响应式 QA。

## 2026-08-29：RQ-160 Portal/Account title typography closure

- Portal 中文标题改为显式 `从一方之地，`／`启程。`，Account 改为 `选择一位`／`召唤师。`；英文也固定两行，
  完整句子继续作为无障碍 heading 名称。
- 新增/更新 unit 与 E2E expectation；frontend unit `297/297`、完整 E2E `49/49`、typecheck、build 均通过。
- desktop/390px 中英文 live DOM 与截图复核无标题溢出。未提交/推送，Workbench 未改，8E 与媒体权利边界不变。

## 2026-08-29：RQ-157–160 Region Focus Rail / copy / handoff local result

- 13 个地区 identity 已全部进入横向 focus rail；selected hero 使用高细节研究徽章并回退 Universe crest，CTA 固定为
  `进入登录界面` / `Continue to sign in`。identity、media readiness 与 Riot API routing 保持分离。
- 新建 13 区中英双语 presentation-copy registry。正常 UI 只显示地区名、氛围句和真实操作，移除了“动态素材、本地
  候选、尺寸、时长”等内部审计语言；句子为 RiftCoach 自写，不冒充官方/英雄逐字台词。
- Portal→Account 现在由 shared shell 驱动 `closing → background-handoff → idle`：选中 rail 附近的 aperture 接管，
  Account 背景、地区身份和表单分层进入，heading focus 在 overlay 释放后移动；reduced-motion 即时提交。
- 最终本地门：frontend unit `297/297`、完整 frontend E2E `49/49`、typecheck、Vite build 通过；桌面和 390px 中英文视觉复核通过。
  Workbench 未改，研究媒体权利未核验，`production_media=0`，未提交/推送，8E 仍 in progress。

## 2026-08-29：RQ-157/158 Focus Rail implementation started

- `AUTHORIZED`：用户确认继续推荐的 Region Focus Rail，同时纠正 CTA 必须只写“进入登录界面”，并补充 Portal→Account
  需要更自然、更有范儿的视觉交接。
- `DESIGN`：新增 Focus Rail design/implementation plan；冻结 13 区 identity 与 optional media readiness 分离、
  selected detail hero、rail 下大 CTA、region-aware aperture 和 reduced-motion immediate path。
- `ASSET`：用户指定 Bandle Account WebP 已只读核对为 1200×600、224174 bytes、SHA `f1da72...27cb`；尚未复制到
  runtime。Desktop detail emblems 被确认是扩展名错误的 WebP，当前代码未引用，来源/权利仍未核验。
- `BOUNDARY`：当前只开始文档/TDD，外部调用 0，Workbench 修改 0，production media 0；下一步先取得 RED tests。

## 2026-08-29：Portal source re-review and handoff polish

- 已把历史 source 池拆成细粒度 consumer/provenance/退出门记录：Design Prompts 与 PPT/Photoshop 只用于
  brief/离线展示，Radix 保持行为基础，shadcn/图表/付费 UI 与外部壁纸继续 deferred/research-only。
- 地区 atlas 现在对可明确归属的本地细徽记做渐进加载；缺失、失败和合并的 Piltover/Zaun 图均回退各自
  Universe crest。≤390px 改为单列以保留中文地区名。
- Account 顶栏 CSS 覆盖和地区 handoff generation race 已修复；`from=wallpaper-lab` URL 标记让刷新/复制链接
  仍恢复返回地区选择语义。下一步跑全量前端、浏览器宽度/降动效/媒体失败 QA 和治理门，不进入 Workbench。

## 2026-08-29：Portal source re-review and responsive polish

- 完成一次定向回看：Riot/Universe、视觉 gallery、MotionSites/React Bits/Motion 及其它组件库、电竞数据、
  Agent observability、Training、原型工具、Image2/Photoshop/视频制片工具均重新映射到具体消费者和采用门。
  本轮只推进 Portal/地区/Account，Workbench 的 Timeline、Trace、Training 设计保持后置。
- 将可采用机制落实到当前研究预览：地区卡局部 spotlight 与菱形 active marker；前后 poster 的 560ms 有界
  crossfade；共享 activation overlay 的 aperture/burst 层；详细地区徽章的渐进加载与 Universe crest fallback。
  这些改动没有新增依赖或外部调用，媒体/徽章仍是 `research-only`，`production_media=0`。
- 发现并修复 390px 入口说明与 Enter 按钮重叠；给 activation overlay 的两层增加 data hooks，便于单测证明不是
  “只有一个暗色遮罩”。待跑完整单测、typecheck/build、浏览器四尺寸/reduced-motion/a11y 与治理门。

## 2026-08-29：Region Entry Panel 两地区试水

- 已继续公开检索 MotionSites：browse/catalog 中的 `Cinematic Landing Hero`、`Container Scroll Animation`、
  `Interactive Hover Button`、`Background Paper Shaders`、`Neon Nebula` 等只作为模式参考；实现采用适合
  RiftCoach 的全幅媒体+结构化 atlas+即时切换+focus/reduced-motion/failure 状态，不整页照搬。
- `RegionWallpaperLab` 现在在 Demacia 与 Bandle City 间切换 WebM/MP4/poster；点击 Enter 经过既有语义转场，
  回调以 `/?stage=account&region=...` 进入 Account。Account 背景根据地区切换低对比静态候选，默认 journey
  不受影响。
- focused unit `9 passed`、完整前端单测 `270 passed`、TypeScript/Vite build 和研究预览 E2E `2 passed` 已通过。
- 所有媒体仍为本地 research candidates，`rights=unverified`、`production_media=0`；11 个未具备 ready 动态
  候选的地区显示 pending，不能从 crest 存在推断壁纸可用。
- 下一步转为两地区纵向切片审阅：决定是否扩展第三地区，或先做 Account/Portal 视觉联调；不会因试水通过而自动提升媒体采用状态。

## 2026-08-28：Bandle City candidate added

- 从桌面 `RIFTCOACH` 文件夹核对到 `animated-bandlecity.webm`，完成 1920×1080/25fps/15.04s 与连续运动采样审计；
  已生成无音频 H.264 fallback 和 poster，并加入本地 catalog。Region Wallpaper Lab 现在可在 Demacia 与 Bandle City
  之间切换；其它 11 个地区仍保持 pending，不伪造壁纸可用状态。
- 新增候选审计 JSON 与 `regionWallpaperCatalog`/组件测试；聚焦 10 项、完整前端单测 269 项、E2E 38 项、build/typecheck
  通过。动态素材仍仅为 research candidate，production media 继续为 `0`。
- 用户提供的 Bandle City 静态图 `runeterra-bandlecity-03.jpg` 原始 926×1080；已另存一份 imagegen 修复候选到桌面
  `RIFTCOACH`，未覆盖原图；人工复核认为生成图纹理脆硬、AI 重绘感明显，低于其它已存地区图，已标记 rejected，下一步
  改为寻找真实高分辨率官方源或直接从高质量动态候选抽取静态参考，不继续堆锐化。

## 2026-08-28：region media inventory review

- 已只读盘点桌面 `RIFTCOACH`：12 动态、15 静态；生成动态/静态 contact sheet 与 5fps motion audit。动态候选按分辨率、
  时长、音轨和采样连续性记录，静态候选按地区视觉身份、构图和分辨率做暂定映射。
- 暂定首选见 `docs/assets/8e-portal/portal-region-media-inventory-review-v1.md`；不确定项（Noxus 第二张、Demacia 多张、
  Bandle 低清静态）保持 alternate/rejected，不在未确认前重命名。用户随后纠正两项：`ab3c...-1920x726` 属于暗影岛，
  `ef261...-1920x900` 属于比尔吉沃特；当前不为 Ixtal 硬分配静态图。徽章方面，Universe 13 个官方 crest 已在选择器使用；
  截图中的详细 3D LoR 风格徽章尚未找到完整、可核验的全套来源，暂不替换已稳定的小卡徽记。

- 用户新增 Ixtal 5000×2811 静态图，已生成 `account-ixtal.jpg` 本地研究副本；Ixtal 动态仍缺失，下一步只准备一次
  first-frame-only motion preflight，不把静态图冒充动态壁纸。
- 已生成独立 Ixtal Account 静态概念 `ixtal-account-generated-v1.png`（1672×941）；原 Ixtal splash 不变，继续作为未来
  动态首帧。生成图尚未接入 runtime，等待质感与来源边界复核。
- 详细 LoR 地区徽章的官方附件清单已核对，但旧链接全部重定向，暂存为 reference-only；Universe 13 个小 crest 仍是当前
  选择器的稳定素材。用户若提供高清徽章文件，可再逐个做 hash/来源/尺寸审计并用于选中地区 hero。

## 2026-08-29：Region Entry Panel 两地区试水

- 已继续公开检索 MotionSites：browse/catalog 中的 `Cinematic Landing Hero`、`Container Scroll Animation`、
  `Interactive Hover Button`、`Background Paper Shaders`、`Neon Nebula` 等只作为模式参考；实现采用适合
  RiftCoach 的全幅媒体+结构化 atlas+即时切换+focus/reduced-motion/failure 状态，不整页照搬。
- `RegionWallpaperLab` 现在在 Demacia 与 Bandle City 间切换 WebM/MP4/poster；点击 Enter 经过既有语义转场，
  回调以 `/?stage=account&region=...` 进入 Account。Account 背景根据地区切换低对比静态候选，默认 journey
  不受影响。
- focused unit `9 passed`、TypeScript/Vite build 已通过；E2E 合同已更新，待本地研究预览服务器条件下运行。
- 所有媒体仍为本地 research candidates，`rights=unverified`、`production_media=0`；11 个未具备 ready 动态
  候选的地区显示 pending，不能从 crest 存在推断壁纸可用。
- 虚空缺失徽章已按用户允许生成原创补位；最终平衡版为透明 RGBA、低饱和紫色可辨、深黑曜石材质，保存在桌面
  `RIFTCOACH/badge-void-generated-v3-balanced.png`，暂作 selected-region hero 候选。
- 用户提供的 Image2 Void 徽章候选已保存为 `badge-void-image2-v1.png` 与 `badge-void-image2-v2-muted.png`；
  目前视觉方向优先于自绘版，但仍是 RGB 深色背景，不作为透明小卡直接使用。

## 2026-08-29：Portal/Account UI hygiene and route consistency

- 已将 Portal 的地区路由收敛为 `?surface=wallpaper-lab&region=...`；旧 `?region=...` 只作为
  兼容 presentation alias，未知 query/stage/region 仍 fail-closed，避免刷新后回到旧 Awakening
  场景。Account handoff 使用受限 `from=wallpaper-lab` marker。
- 已修复窄屏 cascade：`<=720px` scene preview 单列、地区卡两列，`<=420px` 地区卡单列；
  721–980px 使用两列以避免卡片压扁。Portal skip link 现在移动焦点到 atlas heading，标题和
  Auth boundary 使用 semantic `main`/`tabindex=-1`，并补齐选择状态 aria 属性。
- 已为 Portal/Account 相关 poster、video、Universe crest 与细徽记声明 intrinsic dimensions；
  保留 WebM→MP4→poster、mobile/reduced-motion/playback-error fallback，细徽记加载失败回退
  Universe crest。`CinematicSceneMedia` 也补齐尺寸属性，降低布局位移风险。
- 选择地区时以 `history.replaceState` 把当前 Portal entry 同步为显式 `surface=wallpaper-lab&region=...`，
  所以复制、刷新和浏览器 Back 都保留选择；1000–1199px 短桌面改为三列，<=420px 手机改为单列，避免四列/两列压扁文案。
- 背景媒体、scrim 与 activation layer 改为固定视口，长的移动/平板 atlas 只滚动内容，不再把 16:9
  壁纸拉伸到文档高度或随滚动改变构图。
- 验证事实：最终定向单测 `56 passed`、完整前端单测 `280 passed`、研究预览 Playwright
  `11 passed`；最终 typecheck/build、Axe serious/critical、governance 与 diff 门均已通过。媒体审计仍为
  `checked_renditions=0/status=planned`。上述为 RQ-154/156
  的本地 hardening，不改变 Workbench、默认 `/`、来源/许可门或 `production_media=0`。

## 2026-08-28：official wallpaper fallback local preview

- Wan first-frame reopen 停在兼容文本 endpoint 的 HTTP 404/no-task，用户明确转战，不再继续找 Host 或发第二次 POST。
- `animated-demacia.webm` 已完成只读审计：1920×1080、15.04s、25fps、VP8 WebM、无音轨；连续运动可见但
  原生首尾不无缝，来源/公开再分发许可仍待核验。
- 已实现 `web/src/wallpapers/regionWallpaperCatalog.ts` 与 `RegionWallpaperLab` 研究预览，入口为
  `/?surface=wallpaper-lab`；本地候选提供 WebM/MP4/poster，包含地区选择、poster/reduced-motion/播放失败降级、
  键盘激活和独立入口转场，不改变默认 `/`、Auth、Account、Workbench 或 product journey。
- 前端单测 `266 passed`、研究预览 E2E `2 passed`、typecheck/build 通过；下一步逐地区补充经来源/许可、格式/
  体积、浏览器/移动端/reduced-motion 和 loop 门核验的候选，再决定是否接入默认 Portal。

- 依据用户提供的 Universe 截图，已改用 Universe 官方 13 个地区 crest（含 Ixtal、Bandle City、Piltover、Zaun、
  Void）作为本地选择卡素材；选区从单个小按钮改为四列大区卡，未有动态壁纸的地区显示“壁纸待核验”，不伪造可用状态。
- 预览 E2E/单测继续覆盖 no-I/O、键盘、poster 降级和双语；官方 crest 来源与本地 SHA 记录在
  `docs/assets/8e-portal/portal-region-icon-provenance-v1.md`。

- 依据新截图补齐 Universe 13 区域（含 Ixtal、Bandle City、Piltover、Zaun、Void）；Bandle City 的 Universe
  动态背景与 League Displays 静态资源差异已记录，后续按 crest/static/dynamic 三态建模。

## 2026-08-28：masked-inpaint plate proof rejected；Wan 3.0 first-frame reopen prepared

- 完成 bounded Rift proof：ImageGen 清洁背板只在局部遮罩内使用，独立 RGBA 流体层只在该遮罩内做周期位移；
  本地输出 960×540/24fps/8s/no-audio，外部模型调用 0。
- 机械审计：192 帧、H.264/yuv420p、source-first SSIM `0.9126610023`、首尾 SSIM `0.9979960032`；
  这些数值只说明局部合成与编码链可复现。
- 人工审查：透明流体层可见时呈廉价贴纸/蓝带，不可见时动效不足；候选判定 `research-proof-rejected`，
  没有进入 runtime 或 production media。证据见 `portal-motion-candidate-masked-inpaint-plate-v1.json`。
- 用户要求重新利用 Wan 3.0 官方通道，已冻结 RQ-144 first-frame-only preflight、motion-only prompt 与
  one-POST runner；先核对同区 endpoint/账号余额/价格，再执行最多一次，失败不重试、不接 runtime。

- 用户新增条件回退 RQ-145：若 Wan 重开仍不达标，停止自制整幕视频，改评估 Riot 官方 League Displays 地区
  动态壁纸（Portal 选地区）与独立静态 Account 壁纸；当前不改变 Wan 这一次的执行顺序。

- Wan runner 首次启动因 `/compatible-mode/v1` 错误路径返回 404；无 task_id、无结果、无模型质量证据。
  已完成 API Host allowlist/路径归一化/Markdown link 兼容和正确 task GET 路径修复，等待独立公共门后一次纠正执行。

## 2026-08-28：切换官方/授权壁纸路线

- 用户明确停止 Wan 路线，未发送第二个模型任务。Demacia WebM 已完成只读审计：1920×1080、15.04s、25fps、VP8、
  无音轨、连续帧变化可见，但原生 loop seam 不过门。
- 已冻结 RQ-146：建立 region wallpaper catalog/local preview；Portal 地区选择后加载对应本地动态壁纸，
  Account 使用独立静态壁纸；来源/许可、WebM/MP4、poster、loop、移动端和 reduced-motion 逐项核验后才可采用。

## 2026-08-28：独立材质 plate 预检结果

- built-in imagegen 完成 5 个局部 plate 候选；Rift/右场/道路/晶体直接叠加分别暴露水团贴纸、宽蓝底、蓝雾和几何替换
  问题，均不进入 runtime。完整 SHA/路径审计已落盘。
- `material-plate-generation-gate` 未通过；下一动作收窄为 `masked-inpaint-plate-proof`，只做一个 Rift bounded 区域的
  清洁 backplate + transparent plate 叠合验证。Image2 代理与 Photoshop 当前不可用，先不继续批量生成。

## 2026-08-28：replace-shifted visible motion rejection

- `motion_scale=2.5` 的 `replace-shifted` 低分辨率对照已完成，聚焦测试保持通过；运动更可见但产生 Rift/道路/晶体
  边缘重影与软化，右场/far 仍弱，按用户反馈判 rejected。
- 新的 material plate/backplate gate 已写入计划；Image2 代理不可达，本轮没有外部图像/视频调用，production media 仍为 0。

## 2026-08-28：分层材质 proof v2 result review

- 新建 v2 分层材质 proof，先红灯后绿灯，聚焦 `3 passed`；HyperFrames GPU 本地渲染完成 8s/1920×1080/24fps/
  H.264/yuv420p/BT.709/no-audio，外部调用 `0`。
- 机械结果均衡且结构稳定，但人工视觉拒绝：仍像低幅 source duplicate/亮度调制，缺少真实材质流、遮挡和纵深；
  不继续 opacity 追绿。研究候选 JSON 已落盘，production media 仍为 `0`。
- 下一动作切为 `layer-assets-and-occlusion-proof`，先补 inpaint 背板/遮挡/材质层，再做一轮本地 proof；不再付费生成。
- 本机完整 pytest 受数据库环境阻塞，`--maxfail=1` 在 PostgreSQL fixture setup 报 `DATABASE_URL is required`，此前
  已得到 `126 passed, 1 warning, 1 error`；不把它误报为本次实验回归，公共 PostgreSQL 门仍需补证。

## 2026-08-28：source-derived layer assets proof v1

- 新建 source-derived layer renderer/contract/tests，聚焦测试 `3 passed`；本地完成 1920×1080/24fps/8s/no-audio
  proof，外部调用 `0`。底图清晰、无全屏纱罩，亮部层可独立检查。
- 人工结论为 `foundation-pass-with-visual-boundary`：运动仍偏弱且缺少真实 occlusion/backplate，不进入 runtime。
  证据 JSON 已落盘，下一检查点为 `material-plate-generation-gate`，先补独立材质 plate 再回到合成。

## 2026-08-31：RQ-172 G53-5 全能力矩阵真实观察

- 新实验 `g53-5-fresh-flash-capability-matrix-v1` 共 `11/11` 次调用、`46,151` tokens，8 个案例中 `7/8` 通过；
  结果文件为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_capability_matrix_v1.json`，
  SHA-256 `BFFF564CF4C6E7B2DD05F88542FD7A872D1565442B6D35C795EC6892CC84BE0C`。
- adapter_core、AgentLoop、多 ToolCall 顺序/思考回放、domain development、vendor text stream 与 vendor
  multimodal 均有观察通过。F7 vendor `tool_stream` 在 `max_tokens=512` 以 `incomplete_chat_response`/`length`
  结束，不足以证伪能力；F4 `cached_input_tokens=0`、`cache_status=unproven`，不宣称缓存命中；F8 仅为
  vendor-only 观察，不能进入 provider-neutral 生产合同。
- 结果标记 `production_admitted=false`、`public_ci_confirmed=false`；HEAD 与 `origin/main` 均为
  `0f97b92683e4981842e745a695864deb611bb630`，工作树保持 dirty。下一步等待用户决定 Agent 主线下一项，
  不重跑 G53-4、不改默认模型、Workbench、Auth、前端或 `production_media=0`，不把本地观察写成 Stage 完成。

## 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

- 独立 follow-up 结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json`
  SHA-256 为 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`；experiment_id
  `49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`，父矩阵 experiment
  `4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`、父结果 SHA
  `bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。
- 本次仅把 F7 的 `max_tokens` 从 512 调至 2048，诊断原 `length` 截断；唯一 `1/1` 调用、`557` tokens，
  `finish_reason=tool_calls`、1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source identity stable、
  `cached=0`；结果为 `production_admitted=false`、`public_ci_confirmed=false`、`vendor_raw_transport_only`。
- 该诊断不证明 provider-neutral streaming、Agent 生产、领域采用或公共 CI；Stage 8/8E 仍 `in_progress`，
  下一步等待用户决定 Agent 主线下一项。不改默认模型、Workbench、Auth、前端或 `production_media=0`，不覆盖 RQ-172
  或旧证据。

## 2026-08-31：RQ-174 G53-6 正式领域采用门（两次首案停止）

- 按用户明确授权保留同一冻结 admission identity
  `4266388ef8ad2083cd59eacfd2c41364b151f286f6cd189334dacb4cb121bd10` 下的两份不可变结果，均不覆盖旧 G53-4。
  首份 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_6_max_replay_v1.json`
  （SHA-256 `48d22c53f9231f3c03038d5047b8abf653450164e1f56bf2a08c90c9f48114ae`）使用 max-replay profile 和旧 512
  默认输出上限，首案 `1/12` calls 以 `provider_response_invalid/incomplete_chat_response` 停止。
- 仅修正默认输出上限为 1024 并补传 `top_p` 后，第二份
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_6_max_replay_1024_v1.json`
  （SHA-256 `7af819999f4e40810eacf925bcda8a2330cc8baf0e5ca763c84e6f43b58efc96`）首案累计 `2/12` calls、`2925`
  domain tokens，因当前 30 秒 Skill deadline 返回 `provider_timeout/timeout`，后两案跳过。
- 两份结果均 `admitted=false`、`production_admitted=false`；这只是一次正式领域门的本地拒绝记录，不证明模型一般
  质量或生产成熟度，也没有新的公共 CI/领域准入结论。Stage 8/8E 继续 `in_progress`，下一步等待用户决定 Agent
  主线任务；不无授权重试、不改默认模型、Workbench、Auth、前端或 `production_media=0`。

## 2026-08-31：RQ-175 G53-7 专属运行时档案离线实现

- [implemented] 新增 `app/model_runtime.py` 的不可变、精确模型绑定档案；Flash 使用 Agent/`llm.chat` 90 秒执行窗、
  Provider 传输 120 秒、2048 输出上限、`temperature=1`、`top_p=0.95`。档案只由受信组合代码注入，GLM-5.2、
  未知模型和无档案路径不继承新预算。
- [wired] 档案已贯通 Agent 编译器、AgentLoop、`llm.chat` 工具、G53 预算包装器和 Flash Provider 构造；预算包装器
  在最终请求边界重新固定 timeout/sampling/max_tokens，并把 profile 身份写入元数据与请求摘要。
- [compat] 旧 G53-4/G53-6 结果仍按 legacy digest fallback 严格读取；无 profile 的旧预算包装器仍为 1024。旧数据集
  的 30 秒保持为质量资源阈值，新档案的 90 秒是执行窗口，两者不混称。
- [verification] 聚焦 profile/domain 回归 `98 passed, 27 subtests passed`，额外 runtime/provider 回归 `108 passed,
  8 subtests passed`；compileall、`git diff --check` 和治理检查通过。未读取/输出 Key，未执行真实 API。
- [boundary] 当前实现只登记 G53-7 evaluation-only 接缝；真实运行会先要求新实现 exact-SHA 公共 CI 并拒绝 dirty
  worktree，不自动改产品 Runtime、默认模型、Workbench、Portal/Account、Auth、路由或 `production_media=0`。
- [next] 等待用户决定先走新实现的 exact-SHA CI/独立 G53-7 领域门，还是转入其它 Agent 主线任务。

## 2026-08-31：RQ-176 Flash-only 产品运行时晋级（本地接线）

- 用户明确选择普通 API `glm-5.3-flash` 作为产品运行时目标；GLM-5.2 仅保留为显式兼容/应急回退，不再
  把 Pro/Flash 比较当作前置决策，也不重开旧地区扩展动作。
- 已将受信 `ModelRuntimeProfile` 接入产品组合根、Worker、RuntimeExecutionFactory、Agent compiler、
  AgentLoop、Harness `llm.chat`、Zhipu Provider、Runtime policy/Trace identity；Skill 的 30 秒质量门与
  Flash 90 秒执行窗分离。Flash Provider 采用 120 秒传输、2048 输出上限、固定 sampling 和 SDK retries=0。
- Flash Worker 使用 360 秒 lease/60 秒 heartbeat 默认值，拒绝少于 300 秒 lease；产品 worker 只允许 GLM-5.2
  或 Flash，Flash 还要求普通 API 标准基址与 concrete profile 绑定。`.env.example`/Compose 默认已对齐 Flash。
- 本地聚焦回归（Runtime/Provider/Worker/compiler/profile）已通过；没有在本批发起真实 API。当前 dirty tree
  不能作为公共证据，新实现 exact-SHA CI 与同 SHA G53-3 必须先完成，随后才是 G53-7/黄金切片。

## 2026-08-31：RQ-178 G53-7 A/B 身份绑定与无 I/O 预检

- [implementation] 新增 `GLM53ABIdentityBinding`，将实现提交 A、协议执行代码 SHA、实现公共 CI 与证据提交 B、
  B 的公共 CI 明确拆开；schema 1.1 admission 才携带该绑定，历史 schema 1.0 结果保持兼容。
- [preflight] 只读检查当前 HEAD=B、B 是 A 的直接单父子提交、B 只新增 capability-result 白名单、B 的 Git blob
  与工作树文件 canonical LF 摘要一致，并验证协议为同一 A 上的 `zhipu/glm-5.3-flash` 三调用通过结果；不读 `.env`、
  不构造 Provider、不发领域请求。
- [verification] 新增 A/B 错配、旧结果兼容、路径/篡改、CLI 缺身份和真实 Git blob 测试；相关聚焦测试 `53 passed`（身份绑定文件 `18 passed`），
  compile 与既有 gate/runtime 回归通过。Windows 原始 CRLF 摘要 `6c6e…` 与提交 canonical LF 摘要 `1fda…` 分开记录，
  绑定只使用后者。
- [历史边界，已由 RQ-179 更新] 这批代码当时尚未形成新的冻结实现 SHA；现在最终 A=`9e6d78be…` 已取得
  exact-SHA 公共 CI。下一项为从干净 A 重取 G53-3 并只新增证据 B，然后才评估 G53-7 领域门；保持
  Portal/Account/Workbench/Auth/默认模型和 `production_media=0` 不变，不自动运行领域 API。

## 2026-08-31：RQ-179 G53-7 最终实现 A 公共冻结

- 最终 A=`9e6d78be51c3a5c512b67f83d2849f9b1261cf77`；Actions run `33378687984` 精确匹配该 SHA，
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿。
- 失败候选 `fe7d577…`/run `33377864183` 与 `3ccd827…`/run `33378168043` 分别暴露历史 HEAD fixture
  和 shallow checkout 缺 Git 历史；两份失败证据保留。最终测试只替换历史 fixture 的私有 reader，生产校验未放宽。
- 本地相关回归 `53 passed`，compile、diff、governance 通过；原有 dirty Portal/Account/文档/资产未被提交。
- 下一项只在干净 A 上重取 G53-3，再让直接子提交 B 只新增新结果；本批没有真实模型调用，不直接进入 G53-7。

## 2026-08-31：RQ-180 G53-7 首次真实领域尝试

- [completed-bounded-attempt] 用户在 A/B 公共证据链完成后授权继续；在干净 LF B checkout 上按冻结身份执行一次
  G53-7。协议 3/3，领域 2/12，累计 5/15 calls，领域 3505 tokens，墙钟 36625ms。
- [result] 首例 `flash_gate_baseline_01` 以 `provider_response_invalid` / `incomplete_chat_response` 停止，
  后两例按首错跳过，`admitted=false`；这不是账号认证失败，也不构成模型一般质量或生产准入结论。
- [evidence] 结果文件为 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`，
  canonical-LF SHA-256=`21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment
  `236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；本地 C=`9157cde…` 承载且未推送/未跑公共 CI。
  原始 finish reason、Key、正文、reasoning 未持久化，不能把安全聚合码解释为 `length`。
- [next] 停止自动重试，等待用户决定是否另立版本化的 Flash 响应完成/截断诊断；旧证据、Dataset/Plan、Portal、
  Account、Workbench、Auth、路由和 `production_media=0` 均不变。

## 2026-08-31：RQ-181 Flash 响应完成度诊断

- [completed-bounded] 用户授权后，在独立工作树只执行首个冻结领域案例一次；供应商调用 `1/4`、SDK
  `max_retries=0`。诊断代码提交 `447c11e85b6da53fe678d68e25d96b589c0d6ca2`，产品实现基线
  `7cb66d218389c0e7d7aa7b2b1969a4678402f857`。
- [finding] `agent_initial` 回合原始 `finish_reason=length`，Usage 为 input `2220` / output `2048`；正文为空、
  reasoning 非空、ToolCall 为 0。现有适配器在结束原因校验处以 `incomplete_chat_response` 拒绝，
  `normalized=0/1`、`settled=0/1`，Agent 为 `failed/provider_error`。这确认最大推理档案先耗尽 2048 输出额度，
  但不覆盖 RQ-180 的旧第二回合。
- [evidence] 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
  canonical-LF SHA-256=`050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，由本地提交
  `baa9cc756ff9e3dfc5eac19119315b7f9f0b56da` 承载，未推送/未取得公共 CI；不含 Prompt、正文、reasoning、Key、
  原始请求 ID 或工具参数。
- [next] 不放宽适配器、不提高全局上限、不改 Dataset/Plan、产品默认、Portal、Account、Workbench、Auth、路由或
  `production_media=0`；下一项先设计版本化响应完成策略并补离线 TDD，进入实现另待用户授权。

## 2026-08-31：RQ-182 版本化响应完成策略与离线 TDD

- 用户明确“继续下一步”后，先以 TDD 新增 `tests/test_response_completion_policy.py`，红灯确认策略模块尚不存在，
  再实现 `app/providers/response_completion_policy.py`。
- 严格 Flash v1 精确绑定当前 runtime profile，保持 2048 输出和零额外调用；候选 fresh-recovery v1 使用未注册
  identity、8192 候选上限和最多一次未来调用，但只能产生离线 `candidate_eligible`，不会发网络请求。
- 聚焦策略测试 `41 passed`；相邻 Flash runtime/Zhipu/structured/thinking 回归 `109 passed, 34 subtests passed`；
  包级导出检查与 compileall 通过。
- 已补计划、ADR-0071、八维学习材料和 coverage 引用；下一步需先设计候选的 attempt/预算/Trace 合同并取得新
  exact-SHA 证据，不能直接重跑领域门或静默升高产品默认。

## 2026-08-31：RQ-183 候选 fresh-recovery runtime/attempt/预算/Trace 合同

- [completed-local] 用户明确继续 RQ-182 的唯一下一项；先以 TDD 新增 `tests/test_response_recovery_contract.py`，
  再实现独立的 `app/providers/response_recovery_contract.py`，没有 Provider/SDK/网络调用。
- [implemented-local] 候选 profile 精确绑定 `zhipu/glm-5.3-flash` 与
  `glm-5.3-flash-runtime-v2-candidate/2.0.0`，计划最多有 `primary` 与一次 `fresh_recovery`；账本预留/结算
  每个底层调用，按单次和累计 token/时间 fail closed，并拒绝并发、重复、错序和伪造判定。Trace 使用独立
  schema 1.0，仅保留脱敏状态、身份和资源数字。
- [verification] 聚焦测试 `30 passed`；相邻响应策略、Flash runtime、Runtime models、Observed Provider 和领域门
  回归 `128 passed`；compileall、`git diff --check`、治理检查均通过。
- [boundary-next] 候选保持 `activation_state=candidate` 与 `execution_allowed=false`，严格 Flash v1 仍为
  2048/零额外调用。下一步是新 exact-SHA 公共 CI 与同 SHA G53-3；真实候选诊断、G53-7、黄金切片、生产安全/部署/合规
  和 8F 仍需后续授权与证据。

## 2026-08-31：RQ-184 候选合同 exact-SHA 公共 CI 与同 SHA G53-3

- [completed-public] 实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的公共 Actions run `33405110692` 三 job 全绿；
  同一 A checkout 的 G53-3 严格 `3/3` 真实调用通过，A1 `1/1`、A2 `2/2`，`admitted=true`，SDK retries 为 `0`。
- [completed-public-evidence] 结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`
  由直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 唯一新增；B 的 Actions run `33405881172` 三 job 全绿。
  A/B identity preflight 通过，结果 canonical-LF SHA-256=`275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。
- [boundary-next] 候选仍未注册、`execution_allowed=false`；严格 Flash v1 仍 2048/零额外调用。下一步不自动发请求，
  只有在用户另行授权后才做一次有界候选恢复诊断，并审查成本、延迟、失败和脱敏 Trace；G53-7、黄金切片、生产安全/部署/合规与 8F 不提前。

## 2026-08-31：RQ-185 候选恢复诊断中断

- [offline-ready] 隔离诊断实现提交 `76de589a128b7a71f1def3316da3f30ebdd3a4c8`；聚焦响应恢复/完成策略测试
  `75 passed`，compileall 与差异检查通过。实现基线为候选证据提交
  `eca01ce1393286dbbe83992c2985f600ea2b30b0`。
- [attempt-1-interrupted] 第一次启动只进入 `primary`，沿用 120 秒传输边界；约 60 秒无返回后按工具规则停止，
  无结果文件、无可观察响应，未发 `fresh_recovery`。
- [attempt-2-interrupted] 用户再次明确“继续”后，使用全新结果名并临时将客户端传输上限收窄为 20 秒；
  进程仍未在约 60 秒内结束，随后明确终止。无响应、Usage、finish reason、Trace 或结果 JSON，费用状态 `unknown`。
- [cleanup] 两次诊断进程均已退出，无后台服务器或残留诊断进程；主工作树既有 Portal/Account/Workbench/文档/资产
  修改未清理、未覆盖。没有保存 Key、Prompt、正文、reasoning、工具参数或原始 request ID。
- [boundary-next] 候选保持 `candidate` / `execution_allowed=false`，严格 Flash v1 保持 2048/零额外调用。
  下一项为 `candidate-recovery-diagnostic-review` 的传输/代理边界复核，需新的明确授权；不自动重试、不进入 G53-7、
  不改默认模型、Portal、Account、Workbench、Auth、路由或 `production_media=0`。

## 2026-09-01：RQ-186 请求级截止修复与真实有界诊断

- [root-cause] 确认 RQ-185 的 20 秒客户端默认值被每请求 `ChatRequest.timeout_s=90` 覆盖。
- [implementation] 在隔离诊断代码中加入 `--request-timeout-s` 及 `[30, 90]` 有限值校验；primary 和
  fresh-recovery 均使用同一硬上限。诊断代码提交 `94629161c5d3230629210444b5a1a38212799997`。
- [verification] 新增 payload 级断言后，聚焦及相邻套件 `82 passed`；compileall 与 `git diff --check` 通过。
- [real-call] 实现基线 `eca01ce1393286dbbe83992c2985f600ea2b30b0` 上只发出一个 primary；约 30.141 秒后
  `sdk_error_class=timeout`、`adapter_error_stage=transport`，`terminal_state=fail_closed`，没有 recovery。
- [evidence] 结果路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_recovery_diagnostic_rq186_request_deadline_v1.json`，
  canonical-LF SHA-256=`0a0b6d058badf3d5001369cef9c4a66a582f0837bd1d645655555196ca8b324c`，
  本地证据提交 `a7874b0`；文件不含 Prompt、正文、reasoning、Key、工具参数或原始 request ID。
- [boundary-next] 候选继续未注册，严格 Flash v1、默认模型和产品模块不变。下一项是候选延迟预算裁决；
  未经新授权不自动执行完整 90 秒窗口、G53-7 或产品激活。

## 2026-09-01：RQ-187 完整候选窗口诊断

- [real-call] 在隔离诊断代码 `94629161c5d3230629210444b5a1a38212799997` 与实现基线
  `eca01ce1393286dbbe83992c2985f600ea2b30b0` 上，以 `timeout_s=90`、`max_tokens=8192`、SDK retries `0`
  只执行一个 primary；90.188 秒后以 `sdk_error_class=timeout` / `adapter_error_stage=transport` 结束。
- [result] `provider_calls_attempted=1`、`candidate_eligible_observed=false`、`recovery_attempted=false`、
  `terminal_state=fail_closed`、`usage_state=missing`、`cost_status=unknown`；未保存正文、reasoning、Key、
  工具参数或 request ID。结果 SHA-256=`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，
  证据提交 `50ce5be`。
- [boundary-next] 30 秒过短假设已排除，但不能把无响应解释为模型失败。下一项为传输/生成路径拆分诊断，
  需新的授权；候选、严格 Flash v1、默认模型、Portal、Account、Workbench、Auth 和 `production_media=0` 不变。

## 2026-09-01：RQ-188 传输与生成路径拆分诊断

- [implemented-local] 在隔离工作树新增三路 body-free 诊断器、受限 CLI、Pydantic 脱敏报告和四项聚焦测试；
  聚焦拆分/响应恢复/完成策略回归 `86 passed`，compileall、`git diff --check` 与 governance 通过。没有改产品
  Provider-neutral 接口、AgentLoop、Workbench、Portal、Auth 或默认模型。
- [real-bounded] 用户新授权后只执行一批 `3/3` 真实调用、SDK `max_retries=0`：合法 `enabled/low` 16 token 控制、
  冻结上下文 256 token max 同步请求、冻结上下文 8192 token max 流式首块请求。三路均 observed；同步两路有有效
  Usage 且 `finish_reason=length`、正文为空、reasoning 非空；流式路 `687ms` 观察到首个 `delta_reasoning` chunk 后
  关闭。资源为输入 `1993`、输出 `272`、缓存 `1920`、总计 `2265` tokens、累计 `17172ms`。
- [evidence] 正式结果路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_final_v1.json`，
  experiment=`41901515decc6d8768abd56ee3fd49ac1d1a4402f3cc1cef497720995fa80c8e`，结果 SHA=
  `60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`；诊断代码/source identity=
  `b67b4500ebdbff934e470fd92c1461184aa7c49b` 且 stable。无效 disabled-thinking 初始结果和带 SHA 输入笔误的更正
  结果均保留为不可变审计，未纳入正式结论。
- [interpretation] 本批确认 endpoint/model 路径可达且已开始生成，提示同步小额度会先耗尽 reasoning；不证明完整
  stream、长请求根因、模型一般质量、领域采用或生产成熟度。候选仍 `candidate`/`execution_allowed=false`，严格
  Flash v1 仍 2048/零额外调用，`production_media=0` 不变。
- [next] 按用户新授权，下一批转入 `candidate-output-budget-calibration`，只比较合法推理档位与可见正文完成度；
  不重跑 RQ-187、不把首块观察写成完整能力、不自动进入 G53-7。

## 2026-09-01：RQ-189 输出额度/推理档位校准

- [implementation] 在隔离树新增 `app/evaluation/glm53_flash_output_budget_calibration.py`、受限 CLI 和聚焦测试；
  固定三路矩阵可按前缀或指定序号执行，SDK retries 固定为 `0`，报告保持 body-free 且不保存零字节占位文件。
- [verification] 校准聚焦 `6 passed`；与 RQ-188、恢复诊断、响应完成策略相邻回归 `92 passed`，compileall 和
  `git diff --check` 通过。主树补齐 RQ-188 所需的恢复诊断模块后，导入接缝已复核。
- [real-call] 三个单路探针各一次：`low+2048` 在 `28.344s` 得到 `stop` 和可见正文（输入 `1973`、输出 `724`）；
  `low+8192` 在 `45.594s` 超时；`max+8192` 在 `45.500s` 超时。后两路没有响应、Usage 或 request ID，费用保持
  `unknown`，没有重试或 recovery。
- [boundary-next] 结果支持“低档短同步可完成、高档长同步窗口过长”的候选假设，但不构成候选注册、生产准入或
  一般能力结论。canonical 下一项切换为 `candidate-stream-visible-completion-probe`，仅验证流式首个可见正文和
  `clear_thinking` 形状；严格 Flash v1、Provider-neutral 接口、默认模型、Workbench、Portal、Auth 和
  `production_media=0` 均不变。

## 2026-09-01：RQ-190 流式首个可见正文探针

- [implementation] 隔离树新增原始 stream body-free 探针与 CLI，最终 SHA=`5ec622c4b651f9aa5e12f54b1e5a4a0dc253a4c7`；
  聚焦 `7 passed`，compileall、diff check 通过。
- [real-call] `clear_thinking=true` 单路首块/首正文为 `1813ms/2547ms`；`false` 为 `1500ms/3875ms`。两路均只发
  一次请求，首正文后主动关闭，终态和 Usage 未观测，预算状态 unknown，费用 unknown。
- [evidence] v2 结果 SHA 分别为 `23e3954c2be65d70b24186a3deba35047e3925b2fc2fde1eb3cfeec82631141a` 与
  `fae64899daaffbd2e9a2a5369ee8d396ea912065f2b7351a782a91eb74a0c77e`；早期 v1 仅作审计。
- [boundary-next] 这只证明两种单轮请求形状的首正文可达，不证明完整 stream/Usage、跨轮语义、候选或生产能力；
  canonical 下一项切换为 `candidate-stream-terminal-completion-probe`，不改产品接线。

## 2026-09-01：RQ-191 完整流式终态/Usage 探针

- [implementation] 隔离树新增完整 stream body-free 探针与 CLI，最终 SHA=`2a01edf58e9f5b11619553a9eeb4448a4cdb87d0`；
  聚焦 `6 passed`，compileall、diff check 通过。
- [real-call] `clear_thinking=false / low / 2048 / stream` 单路首块/首正文 `2203ms/3531ms`，完整流 `24140ms` 结束，
  `stop`、Usage valid（1973/652/0），642 chunks；无重试、无 recovery。
- [evidence] 结果 SHA=`a57fec105859241ea71e32eb8073b4c33b934262a7793b6a47a7b6e4efb4b3c9`，source identity stable，
  public CI 未宣称，报告 body-free。
- [boundary-next] 这只证明单一冻结上下文的完整原始流可终止和计量；canonical 下一项切换为
  `candidate-provider-neutral-stream-adapter-contract`，先离线验证装配边界，不改产品接线。

## 2026-09-01：RQ-192 提供商无关流式装配合同

- [completed-local] 新增纯离线 `ProviderStreamEvent`、`ProviderStreamAdapter`、`ProviderStreamAssembler`、
  `StreamAssemblyResult` 与 body-free `StreamAssemblyTrace`；不导入 SDK、不做网络 I/O、不改变同步
  `LLMProvider`、能力标记或产品默认链路。
- [completed-local] 完成条件固定为 EOF 后显式 `mark_exhausted()`、终止原因与有效 Usage；允许一个 Usage-only
  尾帧，拒绝终止后正文/推理/工具、重复终止/Usage、序号/模型/请求身份冲突，并在首次合同错误后毒化实例。
- [completed-local] 工具片段按连续 index、唯一 id/name、严格 JSON 对象和深度/字符/数量上限装配；copy-on-write
  只复制当前事件触及的 index，增量维护参数字符计数；结果默认 repr 隐去正文和工具参数。
- [completed-local] 正文仅用 `strip()` 判断全空、交付时保留原文；`StreamAdapterError` 不接受不安全自定义消息。
  底层迭代器异常/取消必须 `abort()`，正常 EOF 才能 `mark_exhausted()`。
- [verification] 适配器聚焦 `29 passed`；与 Provider、响应完成策略、恢复合同和 runtime stream 相邻回归合计
  `147 passed, 27 subtests passed`，已在最终代码快照复跑确认。
- [boundary] 候选仍未注册，严格 Flash v1 仍 2048/零额外调用；不接入产品 streaming、Portal、Account、
  Workbench、Auth、路由或 `production_media=0`，8E 仍 `in_progress`、8F 未开始。
- [next] 等待同一新实现 SHA 的公共 CI 与 provider-conformance 测试；本地测试通过不等于公共生产准入。

## 2026-09-01：RQ-193 智谱流式适配器一致性接缝

- [implementation] 提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 新增测试内
  `_FixtureZhipuStreamAdapter`，将代表性智谱 OpenAI-compatible chunks 翻译为中立事件；生产
  `ZhipuProvider`、同步接口与能力声明保持不变。
- [verification] conformance 聚焦 `13 passed`；正文/reasoning、工具别名和分片、坏形状、model/terminal
  边界、异常 `abort()`、空 choices、空白保留和 Trace 脱敏均有断言。测试只使用 fake client，无 SDK/网络/Key I/O。
- [boundary] 该批不注册候选、不改 `capabilities.streaming`、严格 Flash v1 2048/零额外调用、默认模型、
  AgentLoop、ToolRuntime、Runtime Trace、预算、Workbench、Portal、Account、Auth、路由或
  `production_media=0`；Stage 8/8E 仍 `in_progress`，8F 未开始。
- [completed-public] `8bcbaa5` 的同 SHA 公共 CI run `33489903978` 已 `completed/success`，
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿且 `head_sha` 精确匹配；该提交已包含
  全部 conformance 与 Trace 脱敏断言。
- [next] 公共证据已对齐，下一精确项是候选接线裁决：明确是否接入
  runtime、接入范围、预算/Trace/回退门和失败处理；在裁决前不自动启用、不执行 G53-7 或黄金切片。

## 2026-09-01：RQ-194 显式智谱→中立适配接缝设计草案（历史设计阶段）

- [planned-review] RQ-193 公共 conformance 已完成；本轮只留下候选级、仅显式调用的 adapter seam 设计材料，
  模块/API 尚待评审，文档占位符不代表实现文件。
- [planned-boundary] 预期流程为已绑定 Zhipu raw chunks 翻译成 `ProviderStreamEvent`，再交给既有
  `ProviderStreamAssembler`；一条流、EOF+terminal+Usage 完成条件，错误 `abort()`/fail-closed，不 retry、recovery 或 ToolRuntime。
- [no-change] 只支持 fake/local evidence，不调用真实 API、不读取 Key、不注册 recovery；`capabilities.streaming=False`，
  严格 Flash v1 2048/零额外调用、默认模型、AgentLoop、Workbench、Portal、Account、Auth、路由、预算、Trace 和
  `production_media=0` 均保持不变。
- [next] 等待设计评审；通过后才做最小 fake/local 实现并跑同一干净提交的 exact-SHA 公共 CI，之后另行裁决是否允许
  候选 runtime 接线。该阶段已由下方本地实现记录推进；占位符保留为历史过程。Stage 8/8E 继续 `in_progress`，8F 尚未开始。

## 2026-09-01：RQ-194 显式智谱→中立适配接缝本地实现

- [implementation] `app/providers/zhipu_stream_adapter.py` 的 `ZhipuStreamAdapter` 已实现，
  `ZhipuProvider.stream_adapter(*, tool_stream=False)` 提供显式工厂；adapter 实现独立 `ProviderStreamAdapter`，
  不是 `LLMProvider`，调用方必须显式选择。
- [flow] `stream_events(request)` 将一条智谱原始流归一化为 `ProviderStreamEvent`；
  `assemble(request, *, max_output_tokens=None, require_request_identity=True)` 只打开一次 stream，
  由 `ProviderStreamAssembler` 在 EOF+terminal+有效 Usage 后完成。
- [budget-identity] cap 限制为 `1..8192`，runtime profile、显式 cap 与请求 cap 取最小值并同时下传；provider/model
  身份严格绑定，request identity 默认要求，Trace 只存 request ID SHA-256。
- [close-failure] 正常 EOF 才 `mark_exhausted()`；异常/取消/翻译错误调用 `abort("stream_aborted")` 或保留 typed
  provider error，close 失败映射安全码；iterator/raw stream 在 finally 关闭，无 retry/recovery/ToolRuntime，输出和
  诊断保持 body-free。
- [verification] `tests/test_zhipu_stream_adapter.py` fake/local 聚焦 `20 passed`；提交
  `a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588` 三 job exact-SHA 全绿，证明候选
  接缝可公共复现但不等于产品或生产能力。
- [boundary] `capabilities.streaming=False`、严格 Flash v1 2048/零额外调用、默认模型、AgentLoop、Workbench、Portal、
  Account、Auth、路由、统一 Trace/预算、`production_media=0` 均不变；候选/recovery 未注册，不调用真实 API。
- [next] exact-SHA 公共 CI 已完成；下一项是独立裁决候选 runtime 接线；8E 仍 `in_progress`，8F 尚未开始。

## 2026-09-01：RQ-195 候选 runtime 接线架构评审

- [completed-review] 新增 ADR-0075、候选接线评审计划和 8E 学习 walkthrough；评审只冻结边界，不改 `app/`、产品 Runtime
  或默认模型，不发真实 API 请求。
- [finding] `assemble()` 对不完整流 fail-closed，不能把异常当候选资格；未来必须先设计只输出状态的
  `BoundaryObservation`，完整流继续走 provider-neutral assembler。
- [decision] 推荐隔离的 `CandidateStreamEvaluationHarness`，精确校验 zhipu/model/runtime profile/policy 四元身份，
  用独立 ledger 和 allow-list Trace 投影管理候选预算与撤出；拒绝包装成 `LLMProvider` 或改 `AgentLoop`。
- [boundary] 候选未注册且 `execution_allowed=false`；严格 Flash v1、`capabilities.streaming=False`、Workbench、Portal、
  Account、Auth、路由和 `production_media=0` 不变。下一精确项为 `candidate-runtime-wiring-design / pending`。

## 2026-09-01：RQ-196 候选 runtime 接线设计（历史状态）

- [completed-design] 已按用户继续授权完成设计门：冻结 `CandidateRuntimeBinding` 四元身份与尝试序号，定义 body-free
  `BoundaryObservation`、生命周期/字段状态/Usage 聚合、共享事件校验、候选 v2 transport 接缝和独立 Trace 投影。
- [completed-design] 明确完整流与不完整流分流：真实 EOF、terminal、close 和有效 Usage 才能交给完整 assembler；
  `length`、缺终态、缺 Usage、读取/翻译/身份/关闭错误只产生脱敏观察并 fail-closed，不能构造 `ChatResponse` 或自行填写资格。
- [completed-design] 冻结 reserve→open→observe/assemble→settle 的未来调用顺序和硬账本；最多 2 attempts、1 次额外调用、
  32,000 input、16,384 output、180,000ms，unknown Usage 保持未知，第三次调用拒绝；当前 `execution_allowed=false`。
- [verification] 新增 ADR-0076、设计计划、学习 walkthrough，更新状态/需求账本；本批未改 `app/`、Provider、AgentLoop、
  默认模型、产品模块或主工作树，治理与差异检查已通过。
- [boundary-next] 当时下一唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-implementation / pending`；
  只做 fake/local 合同实现、聚焦测试和同 SHA 公共 CI，不自动发真实 API、recovery、G53-7 或黄金切片；该门已由 RQ-197 推进。

## 2026-09-01：RQ-197 候选边界观察合同本地实现

- [implementation-local] 在隔离分支新增 `app/evaluation/candidate_stream_contract.py`，实现精确 candidate binding、
  body-free `BoundaryObservation`、不可变终态快照、字段 presence/状态聚合、候选 v2 注入式 transport port 和独立
  `CandidateStreamTrace`；没有注册候选或接入产品 Runtime。
- [shared-core] `ProviderStreamEvent` 保留显式 null 与缺失的区别；完整 assembler、智谱翻译和候选观察器共享
  `validate_provider_stream_event()` 的 model/sequence/tool/Usage/大小校验，避免事件规则漂移。
- [verification-local] 完整 stop/tool-call、length reasoning-only、缺 EOF/terminal/Usage、身份/序号/工具/预算/时钟/
  关闭异常、状态伪造和 body-free 序列化矩阵均通过；候选及相邻回归 `163 passed`，compileall、diff check、governance 通过。
  全量本地首错是 PostgreSQL fixture 缺少 `RIFTCOACH_TEST_DATABASE_URL`，不归因于本批。
- [boundary] 候选仍 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 2048/零额外调用，
  `capabilities.streaming=False`、默认模型、AgentLoop、Workbench、Portal、Account、Auth、路由、统一 Trace/预算和
  `production_media=0` 均不变；未执行真实 API、recovery、G53-7 或黄金切片。
- [next] 当前唯一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-public-ci / pending`；
  先取得同一干净实现提交的 exact-SHA 公共 CI，再另行裁决 candidate harness、fresh-recovery、G53-7 与生产准入。

## 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

- [public-ci] RQ-197 的实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 已由 GitHub Actions
  run `33507627615` 完成 exact-SHA 公共验证；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 均 `completed/success`，公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
- [boundary] 该公共证据只证明 fake/local 候选边界合同可复现；候选仍未注册、`execution_allowed=false`，
  严格 Flash v1、默认 Runtime、产品模块、`capabilities.streaming=False` 和 `production_media=0` 不变；
  没有真实 API/Key、recovery、G53-7 或黄金切片。
- [next] 当前唯一精确 checkpoint 已切换为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`。
  只在用户明确继续后设计隔离 harness/ledger/Trace 接缝，本轮暂停。

## 2026-09-02：RQ-199 隔离候选评估台设计

- 按 canonical 唯一下一步完成 ADR-0077、候选评估台实现计划和学习 walkthrough；本轮没有修改 `app/`、产品 Runtime、
  Portal/Account/Workbench/Auth、默认模型或统一 Trace，也没有读取 Key、发真实 API 或执行 recovery/G53-7。
- 识别并解决现有恢复合同的时序缺口：首回合快照在 I/O 前未知，但请求必须先记账；设计采用 candidate-only staged ledger，
  primary 先 reserve，真实 `BoundaryObservation` 形成后才映射 snapshot、重算 policy 和冻结 recovery plan，拒绝 sentinel
  snapshot 以及首回合结束后才 reserve。
- 冻结单次 normalized event pump：共享事件校验后同时喂给 body-free observer 和仅内存的 assembler；完整流可短暂交给显式
  evaluation consumer，不完整流不构造 `ChatResponse`，receipt 永远只含 allow-list 状态/计数/安全码。
- 固定候选 activation 当前关闭；命中候选 shape 只能产生 `awaiting_recovery`。候选预算保持 8192/90/120 秒、累计
  32,000/16,384/180,000ms、最多 2 attempts/1 次额外调用，unknown Usage 不当零，第三次/重复 settle fail closed。
- 文档治理与 `git diff --check` 在本批收尾；未运行产品测试，因为没有代码变更。下一精确项切换为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`。

## 2026-09-02：RQ-200 隔离候选评估台本地实现

- [implementation-local] 在隔离分支新增 `CandidateEvaluationHarness` 与 staged ledger：primary 在
  I/O 前预留，单次 normalized event pump 同时驱动 body-free observer 和临时 assembler，观察完成后
  才重算 policy 并 settle；每个槽位严格一次，open/read/clock/close 失败也计入。
- [receipt] 新增独立 body-free `CandidateEvaluationReceipt`/result 与显式 evaluation consumer；完整
  stop/tool 流才可短暂交付，`length`、缺 EOF/终止/Usage、身份/序号/工具/预算错误均 fail-closed，
  unknown Usage 保持 `None`/`unknown`，不执行 ToolRuntime 或隐式 retry。
- [verification-local] harness 聚焦 `15 passed`，与边界观察、流装配和旧恢复合同相邻回归 `102 passed`；
  Python 3.11/3.13 编译、diff check 和治理预检通过。只使用 fake/local transport，未读取 Key 或发真实 API。
- [boundary] activation 仍 sealed `disabled`，候选仍不注册、不打开 `capabilities.streaming`；严格 Flash v1
  2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和
  `production_media=0` 不变，8F 未开始。
- [next] 当前唯一精确 checkpoint 更新为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`；
  先复核候选 recovery 的传输、预算、失败与脱敏边界，之后才另行裁决是否建立新诊断版本、执行 recovery、G53-7、黄金切片和生产准入。

## 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

- [completed-public] RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 Actions run
  `33536168224` 已完成且 `head_sha` 精确匹配；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 全绿，公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
- [boundary] 公共 CI 只证明隔离 fake/local 候选评估台可复现；activation 仍 disabled，候选仍未注册、
  `execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1、默认模型、产品 Runtime、
  AgentLoop、ToolRuntime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；
  没有真实 API/Key、recovery、G53-7、黄金切片或 8F 证据。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`；
  需单独授权后才可复核候选 recovery 的传输、预算、失败和脱敏边界。

## 2026-09-02：RQ-202 候选 recovery 诊断边界复核与最小离线加固

- [completed-local] 在 `CandidateEvaluationReceipt`/`CandidateEvaluationAttemptReceipt` 边界增加
  顶层 state/action/error、attempt decision/reason/assembly 与 budget projection 的派生校验；
  新增伪造回执和预算字段的红绿测试。
- [completed-local] 将候选 observer 的 elapsed 上限绑定到单次 attempt 90 秒（仍受累计 180 秒
  上限约束）；不改变 ledger 的累计预算或 disabled activation。
- [non-reuse] 复核旧同步 recovery 诊断器，确认其 SDK/真实 I/O、旧 ledger 的 unknown Usage
  零值投影和 activation 语义不适合作为新版本基础；旧代码未改、没有真实 API/Key。
- [verification-local] harness `18 passed`；候选流/装配/恢复合同/智谱 adapter/Flash profile
  相邻集合 `127 passed, 1 deselected`；compileall、`git diff --check`、governance 通过。
  deselected 与旧诊断测试阻断来自隔离 Windows CRLF fixture 与计划 canonical-LF 摘要差异，
  未修改冻结资产。
- [boundary] 候选仍未注册、activation `disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`；严格 Flash v1、默认模型、产品 Runtime、Portal、Account、
  Workbench、Auth、路由和 `production_media=0` 不变；没有 recovery/G53-7/黄金切片/8F 证据。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`；
  等待新的单独授权后再设计版本化诊断协议。

## RQ-203 / 版本化候选 recovery 诊断协议设计（2026-09-02）

- [completed-design] 新增 ADR-0079、设计计划和学习 walkthrough，冻结协议
  `glm-5.3-flash-candidate-recovery-diagnostic-v2` / schema `2.0.0`，四元候选身份、body-free 请求摘要和不可伪造的派生字段。
- [lifecycle] 固定 `reserve → open → observe/assemble → settle → receipt`；primary 先预留，fresh recovery 为完整新请求，禁止 resume、隐式 retry 和 ToolRuntime 副作用；activation 仍 disabled。
- [resource] 冻结单次 8192/90s/120s、累计 32000/16384/180000ms、最多 2 attempts；Usage/预算/费用未知保持 null/unknown，延迟记录六个单调分段。
- [failure-boundary] 失败类别和第一现场由观察推导；回执采用原子 create-only、canonical UTF-8/LF、body-free allow-list，不写产品 Runtime Trace 或用户数据。
- [verification] 设计文档与 coverage 已补齐；RQ-202 加固提交 `67031145d3b3e5c864e881576c69e2fda931e950` 的 exact-SHA 公共 CI run `33582049836` 三 job 全绿。
- [boundary] 没有新增代码、真实 API/Key、recovery、G53-7、黄金切片或生产能力；Stage 8/8E 仍 `in_progress`，8F 未开始，`production_media=0`。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`；待再次授权后实现 fake/local v2 协议。

## 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现

- [completed-local] 按 RQ-203 冻结协议新增 `app/evaluation/candidate_recovery_diagnostic_v2.py`、
  `tests/test_candidate_recovery_diagnostic_v2.py` 和实现计划/学习 walkthrough；
  `app/evaluation/__init__.py` 仅导出评估 API，不注册 Provider。
- [verification-local] 新模块聚焦 `22 passed`；候选相关回归 `67 passed`，流式/适配器/恢复合同
  相邻回归 `82 passed`；Python 3.11/3.13 compileall、静态 no-I/O/import 检查和 diff check 通过。
  系统 Python 3.13 用户环境已安装 `pytest 9.1.1`，项目测试继续使用仓库 `.venv` 的完整依赖。
- [boundary] activation 仍 sealed `disabled`，primary 先 reserve、一次事件泵和 body-free receipt
  已落地；没有真实 API/Key、第二次 recovery、候选注册、产品 streaming、Workbench/Portal/Account/Auth
  修改、G53-7、黄金切片或生产准入。严格 Flash v1 2048/零额外调用与 `production_media=0` 不变。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`；
  等待同一干净实现提交的 exact-SHA 公共 CI 和协议 dry-run。

## 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环

- [completed-public] 提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 Actions run
  `33598541029` 三 job exact-SHA 全绿；公共 pytest `2218 passed, 145 skipped, 1 warning,
  127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`，前端契约/typecheck/unit/build/E2E、
  RAG、治理和打包冒烟均通过。
- [completed-dry-run] fake transport 协议演练完成一次 primary 调用并写入临时 canonical body-free
  回执（`calls=1`、`body_free=true`、`3900` bytes）；没有读取 Key、真实 API、第二次 recovery 或持久结果。
- [boundary] 候选仍 disabled、未注册，`execution_allowed=false`、`capabilities.streaming=False`；严格
  Flash v1 2048/零额外调用、默认模型、产品 Runtime、Workbench/Portal/Account/Auth、路由和
  `production_media=0` 不变，G53-7、黄金切片、生产准入和 8F 未进入。
- [next] 当前唯一精确 checkpoint 改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
  真实 recovery 仅待新的明确一次性授权。

## 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察

- [completed-bounded-real] 在干净隔离工作树 `0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 上，
  同 SHA Actions `33603143606` 三 job 全绿；按一次性授权只发送 1 次普通智谱
  `zhipu/glm-5.3-flash` primary，SDK retries 为 0，未发第二次 recovery。
- [observed] 请求使用候选 `max_tokens=8192`、90 秒 attempt、120 秒传输上限；首事件 `3078ms`、
  首个可见正文 `151453ms`、总延迟 `175875ms`。流中确有 reasoning、可见正文、`stop` 和 EOF，
  但 Usage 缺失且 close 失败；90 秒 attempt 门在晚到事件中触发，最终 `fail_closed / elapsed_limit`。
- [evidence] 持久回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`，
  `4355` bytes，SHA-256 `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`；
  canonical 重解析一致，`calls_reserved/settled=1/1`，费用与 Usage 为 unknown。
- [boundary] 这是候选传输/完成度观察，不是 API/Key 失败、模型一般质量结论或生产准入；候选仍 disabled、
  未注册，严格 Flash v1、默认模型、产品 Runtime、前端模块、`production_media=0`、G53-7、黄金切片与 8F 不变。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  先离线设计/测试硬墙钟取消、流关闭和 Usage/终态尾帧处理，再决定是否另行授权真实重测。

## 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧后续

- [completed-local] 新增 `CandidateStreamSession` 和
  `CandidateStreamDeadlineSupervisor`；从 attempt 起点按绝对单调墙钟计时，watchdog
  只调用会话承诺的非阻塞 `cancel`，每次读取前后抑制截止后的晚到事件；legacy iterable
  在没有显式 session opener 时于 opener I/O 前 fail closed，显式 opener 返回值随后验证。
- [completed-local] 新增 `ZhipuStreamSession` 的候选专用 Usage opt-in，持有并关闭原始
  SDK 迭代器/流，支持 `close`/`__exit__` 回退和安全 close-failure 状态；修正取消路径
  的次级关闭证据保留。旧 `stream_events()`、产品 payload、Provider 注册和默认模型不变。
- [verification-local] 候选硬截止、v2 诊断、真实接缝和智谱适配器集合 `67 passed`；
  compileall、diff check 通过；本轮真实 API `0` 次。完整本地回归的 PostgreSQL 缺口
  仍只记录为环境限制。
- [boundary] activation 仍 `disabled`、`execution_allowed=false`、`capabilities.streaming=False`；
  严格 Flash v1 2048/零额外调用、AgentLoop、统一 Trace/预算、Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 不变；没有 recovery、G53-7、黄金切片、生产准入或 8F。
- [limitation] 同步 opener 永久阻塞、或供应商 SDK `close()` 阻塞/不能唤醒 `next()` 时，
  普通 Python 无法提供安全全路径硬截止；真实重测前需 provider-level 连接/取消证据。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-stream-deadline-usage-public-ci / pending`；
  先取得同一干净实现提交的 exact-SHA 公共 CI，之后再另行决定新的真实授权。

## 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

- [completed-public] RQ-207 实现提交 `015b022bfce6d03452f753794ac126a377f8355b` 的 Actions run
  `33613113829` 三 job exact-SHA 全绿；公共 pytest `2241 passed, 145 skipped, 1 warning,
  127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`。
- [verification] 网页契约/生产包、媒体审计工具链、RAG v1 与独立 4M holdout、治理、compileall、
  Harness dry-run 均通过；本地四文件聚焦 `67 passed`。没有新真实 API、没有重试或第二次请求。
- [boundary] 公共 CI 不等于供应商 SDK close 的非阻塞/唤醒能力或生产成熟度证明；候选仍 disabled、
  未注册，严格 Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、
  Auth、路由、`capabilities.streaming=False` 和 `production_media=0` 不变。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  等待新的明确一次性授权后才可做下一次真实观察。

## 2026-09-02：RQ-209 候选真实流硬墙钟与关闭边界观察

- [completed-bounded-real] 在隔离工作树以公共闭环树 SHA
  `015b022bfce6d03452f753794ac126a377f8355b` 作为实现/诊断身份，按用户“继续”仅发送 1 次普通智谱
  `zhipu/glm-5.3-flash` primary；`max_tokens=8192`、attempt 90 秒、transport 120 秒、SDK retries=0，
  显式请求 Usage。没有 recovery、重试或第二次请求。
- [evidence] canonical body-free 回执路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json`，
  文件 `4342` bytes、SHA-256 `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`，由本地证据提交
  `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存；公共 CI 尚未宣称。
- [observed] `calls_reserved/settled=1/1`；首事件/打开计时 `3421ms`，reasoning 非空；`90015ms` 触发 attempt
  硬墙钟，未见可见正文、terminal、EOF 或 Usage，组合会话 `close_state=failed`，`eof_observed=false`，
  最终 `fail_closed / elapsed_limit`，Usage 缺失、费用 unknown。
- [interpretation] 诊断层记录了 attempt 墙钟到点后的 fail-closed 决定；组合 `close_state=failed` 不能归因到
  供应商 response、迭代器或其他具体资源，也不能证明底层 close 非阻塞或能唤醒挂起的 `next()`。回执中的
  `observation.elapsed_ms=0` 是截止前未结算的初始投影，不是零耗时。
- [boundary-next] 候选仍 disabled/未注册，产品默认、Runtime、Workbench、前端、Auth、路由和
  `production_media=0` 不变；当前唯一下一精确 checkpoint 仍为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，
  后续 provider close/wakeup 拆分或新的真实请求须另行取得明确一次性授权。

## 2026-09-03：RQ-210 候选会话分资源关闭报告公共闭环

- [implemented-local] `ZhipuStreamSession` 新增仅内存、不可变、body-free 的 `ZhipuStreamCloseReport`；报告区分迭代器、外层 SDK stream wrapper、组合状态和对象别名，close 逐拥有资源最多调用一次，并继续保留旧 `close_failed` 投影。
- [verification-local/public] adapter/deadline/v2/real 聚焦共 `73 passed`；扩展相邻集合共 `182 passed, 27 subtests passed`；compileall、`git diff --check` 和治理检查通过。实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 的 Actions `33657368435` 三 job 均 `completed/success` 且 head SHA 精确匹配；公共 pytest `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`。
- [boundary] 未修改 RQ-209 v2 receipt/schema 2.0.0 或其 canonical JSON/SHA；没有新增持久字段、正文、异常文本或底层 HTTP response handle。候选仍 disabled/未注册，产品 Runtime、默认模型、Workbench、Portal、Account、Auth、路由和 `production_media=0` 不变。
- [limitation] `cancel()` 仍同步调用 SDK close；本地报告不等于 provider-level 非阻塞 close、唤醒 pending `next()` 或 raw response cancel 证据。并发 close 的报告读取需等拥有者 close 返回，竞态未在本门扩大修复。
- [next] RQ-210 已完成公共闭环；若要持久化分资源状态或重做 provider close/wakeup 真实观察，另立 ADR/schema 版本并重新取得明确授权。

## 2026-09-03：RQ-211 候选 provider close/wakeup 一次真实观察

- [public-precondition] 探针实现/诊断/输入计划身份均为
  `c31127b3c780fe4c493966d8b60f942d3b773fd4`；Actions run `33661910096` 三 job
  exact-SHA 成功。后续测试加固提交 `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c` 的 run
  `33662730304` 被外部取消，不冒充成功，也不替换本次证据身份。
- [completed-bounded-real] 在 c311 干净快照上只发送 1 次普通智谱 `zhipu/glm-5.3-flash`
  请求，SDK retries=0、父进程硬边界 30 秒；没有 retry、recovery 或第二请求。
- [evidence] 新回执路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq211_v1.json`，
  schema `1.0.0`，`908` bytes，SHA-256
  `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`；canonical 重解析通过且
  不含 Key、Authorization、request ID、正文、reasoning 原文或 body。
- [observed] 会话打开且调用数为 1，首段读取 `78ms`，只观察到 reasoning/content 类别；
  `not_pending` / `pending_reader_observed=false`，所以未执行 cancel、`reader_woke=false`。子进程正常退出；
  iterator、SDK stream 与 composite 关闭投影均为 `closed`，`shared_resource=false`。
- [boundary] 本次没有进入 pending-read 分支，因而不能证明或否定 provider close 的非阻塞/唤醒能力或
  底层 HTTP response 取消。候选仍 disabled/未注册，产品 Runtime、默认模型、Workbench、Portal、Account、
  Auth、路由和 `production_media=0` 均不变。
- [next] 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`；
  等待用户决定是否设计新版观察协议，不自动追加真实调用、G53-7、黄金切片、生产准入或 8F。

- [public-verification-addendum] 提交 `1c669e0` 修复 provider capability 目录对 RQ-211 schema 的显式分派；
  Actions `33666132282` 三 job exact-SHA 全绿，公共 pytest `2268 passed, 145 skipped, 1 warning,
  127 subtests passed`，PostgreSQL `201 passed, 1 warning`。这只是回执可复现性验证，没有新增真实请求。

## 2026-09-03：RQ-212 候选 close/wakeup 离线 pending-read 回放（公共闭环完成）

- [authorized-next-substage] 用户要求继续并允许更大步推进；本批只处理 RQ-211 暴露的 `not_pending` 条件缺口，
  不追加真实 API、recovery/retry、候选注册或产品接线。
- [implemented-local] 新增独立 `glm-5.3-flash-candidate-close-wakeup-replay` / schema `1.0.0`，用固定 Event
  闸门回放正常 EOF、取消后唤醒、取消返回但未唤醒、取消超时和取消抛出五场景，复用既有观察器；每个场景只
  打开一次 fake session，并将 fake 打开次数与供应商调用次数分开。
- [evidence-public] 最终 v2 回执路径为
  `data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`，
  `2220` bytes、SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`；
  implementation/observer/input-plan 三个 SHA 均绑定 `1a32012d9dc6424aa012f160d48c8847e21b00ec`，场景 SHA=
  `8a389a9796b0407b3e209ddaab5134b140d4c8379ba659380ae031229011fe26`。v1 仅为绑定旧 HEAD 的提交前演练。
- [verification-public] 实现提交 Actions `33707313651` 三 job exact-SHA 全绿：pytest `2284 passed, 145 skipped,
  2 warnings, 127 subtests passed`；PostgreSQL 控制面 `201 passed, 2 warnings`；packaging-smoke 通过。本地
  RQ-212/RQ-211 聚焦回归 `37 passed`，compileall、diff check、governance 通过。
- [boundary-next] 离线回放只能证明本地分类、脱敏、单次打开和不可变写入可重复，不能证明供应商 SDK close 非阻塞、
  底层 HTTP response 可取消或真实 pending `next()` 可唤醒。候选继续 disabled/未注册，`capabilities.streaming=False`，
  默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变；当前精确 checkpoint
  改为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-real-observation / pending-user-authorization`，
  是否执行新的真实 provider 观察仍需单独授权。

## 2026-09-03：RQ-213 候选 close/wakeup 第二次有界真实观察

- [authorized-next-substage] 用户要求继续并允许更大步推进；在 RQ-212 公共闭环后只发出 1 次真实候选请求，
  不重试、不 recovery、不发送第二请求、不注册候选、不改产品链路。
- [evidence] 使用 exact-SHA 公共绿灯提交
  `a396412f7cd0f2e923536cf55f715dd56251aae5`；回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`，
  schema `1.0.0`，909 bytes，SHA-256=`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`。
- [observed] `call_count=1`、session opened、首段 172ms，事件类别 `reasoning_seen/content_seen`；
  `not_pending`、无 pending reader、cancel 未尝试、reader 未报告唤醒；子进程正常退出，三层 close 投影均为
  `closed`，`shared_resource=false`。
- [boundary-next] 该样本仍不能证明或否定 provider close/wakeup；下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`。
  先等新版 pending-read 协议裁决，不自动追加真实请求、G53-7、黄金切片、生产准入或 8F。

## 2026-09-03：RQ-214 候选 SDK/HTTP transport gate 离线预检

- [decision] 采用 evaluation-only 的 `glm-5.3-flash-candidate-close-wakeup-transport-gate` / schema
  `1.0.0`；通过真实 OpenAI SDK/Zhipu 候选适配器对象链注入本机 `MockTransport`，不把 fake 证据
  写入 provider capability 目录。
- [implemented-local] 新增 `app/evaluation/candidate_transport_gate.py`、离线回放脚本、聚焦测试、
  ADR、计划和学习 walkthrough；两阶段均只产生一次内存 transport 请求，供应商调用数和网络连接数
  均为 0。
- [observed] 两阶段都能形成 pending reader，并在 response close 后唤醒；同时记录到适配器
  iterator/composite close race，结论码为 `client_wakeup_close_race`，不把它改写成 clean success。
- [verification] 本地聚焦测试 `63 passed`、compileall、diff check、governance 已通过；离线 receipt
  已生成并通过 canonical round-trip，文件为
  `data/evaluation/results/offline/zhipu_glm53_flash_candidate_transport_gate_rq214_v1.json`，
  `1693` bytes、SHA-256=`9a952bd6d2798af8796e156d1922f214e6264b67dee12cd86a96b3f886c76bdb`，三份身份 SHA
  均绑定 `4c220c5751288ad77c589d2e0e581690085803c0`；同 SHA 公共 CI run `33712055286` 三 job 全绿：pytest
  `2292 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
  packaging-smoke 通过。
- [boundary-next] 公共闭环后唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / pending-user-authorization`；
  在新的明确一次性授权前不发真实请求、不注册候选、不改产品链路。
## 2026-09-03：RQ-215 候选 transport-gated 一次真实观察

- [authorized-next-substage] RQ-214 离线回执和同 SHA 公共 CI 完成后，用户“继续”授权本批只执行
  一次真实观察；没有 retry、recovery、第二请求、候选注册或产品接线。
- [evidence] 在实现/观察器/输入计划身份
  `2acdf795881733e70c9246c48f7147d5136821b5` 上，Actions `33721483490` 三 job exact-SHA 全绿：
  pytest `2296 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，
  packaging-smoke 通过。真实回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json`，
  `1305` bytes、SHA-256=`732e870bbb0163d354006434c091bd7f15773ffa4e041b25edfc2a5d17739e59`。
- [observed] `provider_call_count=1`、`transport_request_count=1`、`network_used=true`；官方 TLS 外层
  gate 进入，pending reader 形成并在 `31ms` 内唤醒，`upstream_event_seen=true`、
  `upstream_stream_close_seen=true`。取消抛出安全码 `zhipu_stream_close`，iterator/composite
  为 `failed`、SDK stream 为 `closed`，结论为 `client_wakeup_close_race`。
- [boundary-next] 这只说明真实流启动后的本机受控客户端行为，不证明 provider-native close/wakeup、
  底层 HTTP response 独立可取消、模型一般能力或生产 streaming。候选仍 disabled/未注册，产品默认、
  Runtime、Workbench、前端、Auth、路由和 `production_media=0` 不变；当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-real-observation / pending-next-decision`。

## 2026-09-03：RQ-216 候选 reader-owned close 顺序修复

- [authorized-next-substage] 用户要求继续；本批只修复 RQ-215 暴露的客户端关闭竞态，不发新的真实请求，不注册候选，不改产品链路。
- [implemented-local] `ZhipuStreamSession` 增加活跃 reader 计数和延后 iterator close：取消时先关闭外层 SDK response，读取线程退出自己的 `next()` 栈后再关闭 iterator；非活跃路径维持逐资源最多一次关闭。
- [verification-local] 新增阻塞读取回归，并将 RQ-214 两阶段断言收紧为取消返回、reader 唤醒、iterator/SDK/composite 均 `closed`；候选聚焦回归 `61 passed`，compileall、`git diff --check`、governance 通过。此前尝试的全量本地 pytest 在约 60 秒且出现既有 PostgreSQL 环境错误后已中止，不能宣称全量通过。
- [boundary-next] 旧 RQ-215 真实回执保持不可变；候选仍 disabled/未注册，`capabilities.streaming=False`，默认模型、AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation-close-order-fix-public-ci / pending`，下一动作是独立提交/推送并验证同 SHA 公共 CI。

## RQ-216 公共闭环补充

- [completed-public] 实现提交 `3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions `33726209532` 三 job exact-SHA 全绿；公共 pytest `2297 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL 与 packaging-smoke 通过。
- [boundary-next] 公共 CI 只关闭候选本地关闭顺序修复的可复现性，不改变 RQ-215 旧回执，不新增真实 API、候选注册或产品接线。当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-adapter-close-order-fix / pending-next-decision`；等待是否重新观察的用户决定。

## 2026-09-03：RQ-217 关闭顺序修复后的 transport-gated 一次真实观察

- [authorized-next-substage] RQ-216 公共 CI 闭环后，用户授权只执行一次真实候选观察；无 retry、
  recovery、第二请求、候选注册或产品接线。
- [evidence] 实现/观察器/输入计划 SHA 为
  `3e028b1217f1274152ba161993287f29188a1b73`，Actions `33727163550` 三 job exact-SHA 全绿；
  回执 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`
  为 `1284` bytes，SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`。
- [observed] 只发生 1 次 provider/transport 请求；`gate_observation_valid=true`，pending
  reader 被形成并唤醒，`cancel_status=returned`，iterator/SDK/composite close report 均为
  `closed`，结论为 `client_wakeup_clean`。回执 canonical round-trip 通过且 body-free。
- [boundary] 该结果只说明本机受控 transport gate 下的客户端唤醒和 reader-owned 收尾，不证明
  provider-native close/wakeup、模型一般能力、G53-7、黄金切片、生产准入或 8F；候选仍
  disabled/未注册，产品 Runtime、默认模型、Portal、Account、Workbench、Auth、路由和
  `production_media=0` 不变。
- [next] 当前唯一精确 checkpoint 改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`；
  没有新的独立授权前不再发送真实请求。

## 2026-09-03：RQ-218/RQ-219 Flash 协议复核与候选 8192 超时

- [RQ-218] 在实现 `aa22cea0daeb443b635706144ccbfa66185670c4` 上完成 G53-3 精确 3/3；
  证据提交 `4b6cd5807f40f6a8dd469f21c688be861261d20c` / Actions `33735039437` 三 job
  exact-SHA 全绿，脱敏回执 SHA=`feeb7fd7eec2643ca692bd6182fd94a04abed354b17b892029402c0217641e99`。
- [RQ-219] 候选 `glm-5.3-flash-runtime-v2-candidate/2.0.0` 使用 8192 输出、Agent 90 秒、
  传输 120 秒、retries=0，只发 1 次 primary；结果为 `fail_closed / elapsed_limit`，
  未 recovery、retry 或第二请求，回执 SHA=`21350d7883b4d2eea30e0467a7b8c23eed3a3ad5a9deeb309c44f8ded5cf3f84`。
  证据提交 `3f35d150b2f17f919f2be1597c08c6db0178c461` 的 Actions `33735717434` 已三 job
  `completed/success`。
- [boundary] 候选仍 disabled/未注册，严格 Flash v1 仍 2048/零额外调用，
  `capabilities.streaming=False`；默认模型、产品 Runtime、Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 不变。两条回执均 body-free。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / pending`；
  下一批先做零网络 fake/fixture 拆分，不自动追加真实请求。

## RQ-220 / Flash 响应档位—终态—恢复离线拆分（2026-09-03）

- [implemented-local] 新增离线 fixture 矩阵、只读 CLI、create-only receipt 和聚焦测试；
  复用 `CandidateStreamBoundaryObserver`、严格 Flash policy 与候选 policy。
- [verification-local] 9/9 场景通过，相关集合 `133 passed`；compileall、`git diff --check`、
  governance 通过，provider calls=0/network=false。候选 `length` 命中只记录
  `candidate_eligible`，activation 仍阻断恢复。
- [completed-public] 实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` / Actions
  `33738050233` 与回执提交 `ebb09a525b3340f31ba71821b894b4a142dfb4e7` / Actions
  `33738673832` 均三 job exact-SHA `completed/success`；最终回执 SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
- [boundary-next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`；
  不自动追加真实请求。

## 2026-09-03：RQ-221 GLM-5.3 Flash 低思考候选探针

- [implemented] 增加显式 candidate-only `low + 4096` profile、候选 Provider 构造器、
  一次性探针 CLI 与 body-free/create-only 回执；没有改产品 Runtime、默认模型、Portal、
  Account、Workbench 或 Auth。
- [verified] 候选聚焦 `25 passed`，本次相关候选/流/智谱回归 `357 passed`；实现提交
  `c3de5555d0b00d77f402c41a842d00df53f46865` 的 Actions `33746833148` 三 job
  exact-SHA 全绿，compileall、diff check、governance 通过。
- [observed] 在同一实现身份上只发出 1 次真实请求（retries=0、无工具）；结果为
  `observed / finish=stop / usage=valid`，输入/输出 token `1973/498`，延迟约 `20735ms`。
  回执提交 `ef8d4b4133eeb952963e9e5cc112ec1fc458c671`，SHA-256=
  `c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。
- [boundary] 该结果只说明冻结无工具上下文的一次候选响应完成，不是领域门、黄金切片、
  生产准入或 8F 证据；候选仍 disabled/未注册，严格 Flash v1 2048/零额外调用、
  `capabilities.streaming=False`、默认模型和 `production_media=0` 不变。
- [next] 当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`；
  等待低档候选领域门设计/裁决，不自动追加真实请求。

## 2026-09-04：RQ-223 低思考候选领域门离线实现

- [implemented-local] 将候选作用域实现为私有签发、精确对象身份校验的
  `CandidateEvaluationRequestPolicy`；`request_policy` 与产品 `runtime_profile` 互斥，
  正常 Runtime resolver/Worker 未改变。
- [implemented-local] Agent 编译器、`llm.chat`、Draft/Domain executor 和最后一层
  `CandidateEvaluationBudgetedProvider` 统一固定 `low + 4096`、90/120 秒、固定采样、零重试；
  候选执行显式关闭 deterministic fallback。
- [verification-local] Fake Provider 新增测试 `5 passed`；候选/Runtime/Agent/Provider/
  工具/Harness 相邻回归 `118 passed`；compileall、diff check、governance 通过，provider
  calls=0。下一步为同一实现 SHA 的公共 exact-SHA CI。
- [boundary] 未创建 held-out 资产、未读取 Key、未发真实请求、未注册候选，不改变严格 Flash
  v1、默认模型、Portal、Account、Workbench、Auth、路由或 `production_media=0`。

## 2026-09-04：RQ-224 RQ-223 公共 CI 闭环

- [public-ci] 实现提交 `d823cc40c3fcafb7167edccded87e185be4cae8a` 的 Actions run
  `33781369322` head SHA 精确匹配；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 全部 `completed/success`。公共 pytest 为 `2326 passed, 145 skipped, 2 warnings,
  127 subtests passed`，RAG、网页契约/构建、媒体审计、compileall、治理和 Harness dry-run
  也通过。
- [boundary-next] 本批 provider calls=0、候选仍 disabled/未注册，严格产品 Flash v1、默认
  模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / pending-user-authorization`；
  先做最多 3 次低思考 G53-3-L 协议门，再冻结全新三案例 held-out 资产，不重跑旧 G53-4/G53-7。

## 2026-09-03：RQ-222 低思考候选独立领域门设计

- [design-accepted] 已完成 ADR/计划/学习材料，确定候选专用评测作用域、共享请求策略接缝和全新 oracle-blind held-out 三案例路线；拒绝旧考卷换档重跑与全局产品注册。
- [boundary-next] 本批没有改产品代码、创建新考卷或发真实请求；候选仍 disabled/未注册，默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 不变。
- [next] 当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-gate-offline-implementation / completed-local / pending-public-ci`；离线 TDD 已完成，下一步是同 SHA 公共 CI。

## 2026-09-04：RQ-225 低思考 G53-3-L 协议与新鲜资产离线实现

- [implemented-local] 将显式 `request_policy` 接入协议切片运行器，并新增低思考
  G53-3-L 协议组合器；固定 `low + 4096`、90 秒工具窗、最多 3 次调用，报告只保留
  安全身份、计数和终态，真实来源必须显式确认。
- [assets-frozen] 新建三案例 held-out Dataset、V1.1 Input Plan、Prompt/Context Snapshot
  与两个合成 fixture；准入函数交叉核对 case/marker/上下文 SHA，且不加载 Key、不构造
  Provider，`external_provider_calls=0`。
- [verification-local] 协议/资产聚焦集合 `20 passed`，compileall、diff check、governance
  通过，provider calls=0。候选、默认模型、Portal、Account、Workbench、Auth、路由和
  `production_media=0` 不变。
- [boundary-next] 当前精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-local / pending-public-ci`；
  下一步为同一 SHA 公共 exact-SHA CI，之后才等待真实 G53-3-L 的明确授权。

## 2026-09-04：RQ-225 公共 CI 闭环

- [completed-public] 修复协议模块的顶层导入环后，提交
  `411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的 Actions run `33787508488` head SHA
  精确匹配；`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功。
- [evidence] 公共 pytest 为 `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`；
  本批 provider calls=0。此前失败 run `33786726537` 仅暴露新模块顶层导入环，已由
  `411753c` 修复，不把失败 run 当作证据。
- [boundary-next] 候选仍 disabled/未注册，严格 Flash v1、默认模型、Portal、Account、
  Workbench、Auth、路由和 `production_media=0` 不变。当前唯一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`；
  下一步需明确授权后才执行最多 3 次真实 G53-3-L 协议门。

## 2026-09-04：RQ-226 低思考 G53-3-L 真实协议门

- [authorized] RQ-225 公共 CI 闭环后，用户“继续”授权一次最多 3 次的真实协议门；SDK retries=0，
  不执行领域案例、retry、recovery、revision 或产品接线。
- [completed-bounded-real] 在实现/协议 SHA `ac63bf4ee70d61fca78813b200cf7775e5ca61d8` 上，
  A1 结构化合同 `1/1`、A2 工具往返 `2/2` 均通过，协议 `admitted=true`；总计 `3/3` provider
  calls、`network=true`，输入/输出/总 token `1007/84/1091`，累计延迟 `12062ms`。
- [evidence] 脱敏回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json`，
  `2511` bytes、SHA-256=`a3077ce6d4729e676d0c0ce0d9a6429153075ca59e0850529dee4e29c0376e35`；
  body-free/create-only，候选未注册且未获生产准入。
- [boundary-next] 这只证明低思考候选的三调用协议可达性，不证明 held-out 领域质量、成本/延迟
  稳定性、streaming 生产能力、黄金切片、安全/部署/合规或 8F。下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-protocol / completed-real-observation / pending-next-decision`；
  等待是否另行授权独立领域门。

## 2026-09-04：RQ-227 低思考三案例 held-out 领域门真实观察

- [authorized] 用户“继续”授权一次且仅一次的三案例领域观察；固定 `low + 4096`、每案最多 4 次/全域
  12 次调用、24,000/72,000 token 墙，关闭 retry/recovery/revision。
- [completed-bounded-real] 实现 SHA `659757eca7ff1b658dfd164631512d3964c5a2ff` 的 exact-SHA
  CI run `33826568517` 三 job 全绿后执行；领域调用 `6/12`、累计调用 `9/15`，领域/累计 token
  `17834/18925`。第 1 案 Evaluation=96 且安全通过；第 2 案 Evaluation=97 但缺失 evidence source
  IDs、注入检查失败，触发 `unsafe_publication`；第 3 案按首个不安全失败规则跳过。
- [evidence] 回执
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
  为 7537 bytes，SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`，
  body-free/create-only，canonical round-trip 与 dispatcher 验证通过。
- [boundary-next] `admitted=false`、`candidate_registered=false`、`production_admitted=false`；
  这是证据/安全门拒绝，不是 Provider 崩溃。候选、默认模型、产品 Runtime、Portal、Account、
  Workbench、Auth、路由和 `production_media=0` 均不变；当前 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-heldout-domain-gate / completed-real-observation / pending-next-decision`，
  下一步只做失败归因与是否另立版本的裁决，不重跑同一 held-out 资产。

## 2026-09-04：RQ-228 候选领域证据与注入边界离线加固

- [plan] 选择候选专用版本 `glm53-flash-domain-quality-v1`；目标是修复 RQ-227 的证据
  缺失和指令回显边界，不把失败改写成成功。
- [implemented] `ReviewHarness`/`SkillReviewExecutor` 支持显式最低来源数与 draft guard；
  `ContextBuilderV1` 支持可信候选 policy 附录；领域观察新增 body-free `EvidenceDiagnostics`；
  新 `draft_safety` 只对明确拒绝的 marker 做固定占位符脱敏。
- [verified] 聚焦与相邻回归 `102 passed`；compileall、git diff --check、治理检查通过；
  本批没有读取 Key、真实 Provider 调用或旧 RQ-227 重跑。
- [verified-public] 实现 `e2efe8fd75e8cf27cbee7e90484fc90d288ce065` / Actions
  `33832025848` 的 pytest、PostgreSQL、packaging-smoke 三 job exact-SHA 全绿；公共 pytest
  `2344 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL `201 passed, 2 warnings`。
- [boundary] 默认 Harness 行为、GLM-5.2 兼容路径、产品 Runtime、Portal、Account、Workbench、
  Auth、路由和 `production_media=0` 不变；候选仍 disabled/未注册。
- [next] 当前检查点为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-domain-evidence-injection-hardening / completed-public / pending-next-decision`；
  下一步另立新协议/新资产并先做 no-I/O 准入；真实观察仍需新的明确授权。

## 2026-09-04：RQ-229 加固领域 V2 资产离线准入

- [implemented] 新增版本化协议计划、三案例 held-out Dataset、V1.1 Input Plan、带 RQ-228
  候选 policy 的 Prompt/Context Snapshot 和两个全新匿名合成 fixture。
- [admission] 新准入器在 Provider 创建前交叉验证六类文件 SHA、Context 重建、历史污染、
  `glm53-flash-domain-quality-v1`、至少一个来源、低思考/4096、4/12 调用墙、24,000/72,000
  token 墙、零 retry/revision 和首个不安全失败即停。
- [verification] 新增与相邻本地回归 `123 passed`；实现
  `c50cf231957bc54201d0207b99110fcf4b2897b3` 的 Actions `33843064715` 三个任务 exact-SHA
  全绿。公共 Python `2349 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL
  控制面 `201 passed, 2 warnings`，前端 `270 passed`；no-I/O 准入、packaging-smoke、compileall、
  diff check 与治理检查均通过。provider calls=0，未读取 Key，RQ-227 资产与回执保持不可变。
- [next] 当前 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-hardened-domain-v2-assets / completed-public / pending-user-authorization`；
  下一步等待用户明确授权一次新的 V2 有界真实领域观察，当前不调用模型。

## 2026-09-04：RQ-230 加固领域 V2 专用真实运行器

- [authorized] 用户“继续”授权一次新 V2 有界真实领域观察；先补专用运行器和公共 CI。
- [implemented] 新增 V2 Admission/Result/CLI 和只读命名 SHA 投影；强制质量加固、低思考/4096、
  资源墙、既有真实协议证据和 exact-SHA 公共证明。
- [verified-local] 首次红灯为新模块不存在；修复快照语义/文件摘要区分后，聚焦与相邻回归
  `107 passed`，no-I/O preflight、compileall 通过，provider calls=0。
- [next] 当前 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-hardened-domain-v2-real-runner / completed-local / pending-public-ci`；
  下一步提交、推送并等待 exact-SHA 三任务全绿，然后执行本次已授权的唯一一次真实观察。

## 2026-09-04：RQ-230 V2 有界真实领域观察完成

- [public-ci] 实现 SHA `5fe8606f205d49ca5dde969a5823a0eb75587c35` 的 Actions `33846260144`
  三任务 exact-SHA 全绿；no-I/O preflight 通过。
- [real-observation] 使用现有 `GLM_API_KEY` 在进程内映射为仓库约定的 `LLM_API_KEY`，不落盘、不打印；
  只执行一次 V2 观察。首案 `hardened_form_control_41` 3 次调用完成 Provider/工具交互，领域调用
  `3/12`、累计 `6/15`，领域/累计 token `10993/12084`，`network_used=true`。
- [result] 证据检索成功且来源数为 2、注入检查通过，但事实核验/质量门失败；修订预算耗尽，终态为
  `rejected / revision_budget_exhausted`，失败码 `fact_check_failed`、`quality_gate_failed`、
  `terminal_status_mismatch`，运行器以 `domain_case_outcome_mismatch` 停止；其余两案 skipped。
- [evidence] 脱敏回执 7156 bytes，SHA-256=`d1739c5d76da21c1109808b128e8ef82df251df32ea7355836f202d850e01c18`，
  schema/canonical/body-free 校验通过；`admitted=false`。
- [next] 当前进入 `candidate-hardened-domain-v2-real-observation / completed-real-observation /
  pending-next-decision`，只等待失败归因与版本裁决，不重跑旧考卷或本次 V2。

## 2026-09-04：RQ-230 离线失败归因与版本裁决

- [confirmed] 脱敏回执字段显示无 Provider 错误；Agent `completed/final_response`，3 个规范化
  响应，`knowledge.search` 成功、来源 2、注入检查通过。
- [confirmed] 独立评测已通过结构化验证但事实核验为假，分数 `80` 低于技能发布门 `85`；
  `max_revisions=0` 使终态确定为 `rejected / revision_budget_exhausted`。
- [derived] `terminal_status_mismatch` 和 `domain_case_outcome_mismatch` 仅是案例“必须
  published/必须成功”与拒绝终态不一致的派生码。
- [unknown] body-free 回执不含报告和评测 issues，具体错误句/类别无法本地证明。
- [decision] 不修改代码、不另立版本、不重跑模型；未来如要验证新假设，须用户另行授权并新建
  版本化考卷/回执身份。当前 checkpoint 保持 `pending-next-decision`。

## 2026-09-04：RQ-231 V3 有界修订设计完成

- [authorized] 用户以“继续”授权 RQ-230 之后的新版本化假设设计；本批不含真实调用。
- [completed-design] 新增 ADR-0094、V3 设计、详细实施计划与学习 walkthrough；采用
  `max_revisions=1` 的 Harness 原生修订闭环，保持 85 分及全部质量/安全硬门。
- [budget] 调用墙推导为 9 次/案、27 次/域；Token 墙留给离线包络证明后冻结，不复用旧数值。
- [diagnostics] 诊断只保存结构化枚举和计数，不保存任何评测自由文本、正文或 reasoning。
- [verification] 本批 provider calls=0；`git diff --check` 与 governance 结果在本批收口时复核。
- [next] 当前进入
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-hardened-domain-v3-bounded-revision-design / completed-design / pending-offline-implementation`；
  下一批只做离线 TDD、预算可达性证明和全新 V3 资产 no-I/O 准入。

## 2026-09-04：RQ-232 V3 离线实现与资产准入

- [implemented-local] 完成默认零修订兼容、V3 最多一次受控修订、body-free 评测诊断、独立预算墙、
  全新三案例资产和候选专用入口。
- [budget] 离线请求包络证明每案最多 9 次、全域 27 次；Token 墙为每案 `203000`、全域 `608000`，
  报告可在 `external_provider_calls=0` 下重建。
- [verification-local] 初始实现 `730c32d074269fb45e5a5351b1af591ecaa35de1` 的相关与相邻回归
  `54 passed`；公共首跑 `33894351184` 因旧输入计划隔离与 V2 回执分流两处遗漏失败。
- [verification-public] 修复 `f99c142c269df765deb592c463ce6e2555bcc3fe` 的相关回归
  `93 passed`，compileall、diff check、治理检查通过；Actions `33895602378` 三任务 exact-SHA
  全绿，公共 pytest `2379 passed, 145 skipped, 2 warnings, 127 subtests passed`，PostgreSQL
  `201 passed, 2 warnings`，packaging-smoke 通过。
- [boundary-next] 候选仍 disabled/未注册，旧 V2、GLM-5.2 兼容/应急路径、默认 Runtime、Portal、
  Account、Workbench、Auth、路由和 `production_media=0` 不变。当前唯一 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-hardened-domain-v3-bounded-revision-implementation / completed-public / pending-fresh-g53-3l-authorization`；
  exact-SHA 预检为 `pending_protocol_evidence`、provider calls=0。下一步等待新鲜 G53-3-L 的明确授权，
  不自动进入 V3 领域观察。

## 2026-09-05：RQ-233 新鲜 G53-3-L 回执延迟口径修复

- [authorized-attempt] 新鲜协议运行已按授权发起，但在回执构造阶段因
  `latency total does not match protocol` 失败；没有生成结果文件，也不自动重跑。
- [implementation] `GLM53LowProfileProtocolReport.latency_ms` 改为协议案例端到端延迟之和；
  Provider I/O 预算计时和全部请求/资源/准入合同不变。新增推进时钟防止固定时钟再次掩盖差异。
- [verification] 聚焦回归 `18 passed`，协议、预算、V2/V3 相邻回归 `32 passed`；修复提交
  `110f9e8008486bfb976643a6abdaa8e88ea334e6` 的 Actions `33897787039` 三任务 exact-SHA
  全绿，公共 pytest 2380、PostgreSQL 201、packaging-smoke 通过。
- [boundary-next] 当前 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-fresh-g53-3l-receipt-latency-fix / completed-public / pending-fresh-g53-3l-reauthorization`；
  下一步等待重新授权。新的真实协议与 V3 领域观察仍分别需要后续授权。

## 2026-09-05：RQ-234 修复后新鲜协议通过

- [authorized-complete] 用户继续已满足协议授权；执行前隔离树干净，HEAD `28219ed` 与同名
  远端同步、相对 `110f9e8` 只有文档变化；重新查询 Actions `33897787039` 三任务成功。
- [real-result] A1 `1/1`、A2 `2/2`，admitted=true；输入/输出/总 Token `1008/108/1116`，
  12812ms，SDK 零重试；新回执 `zhipu_glm53_flash_candidate_low_4096_g53_3l_rq234_v1.json`
  为 2512 bytes，SHA-256=`fd500c57fbdb12ac408625d6c64b1cc0eb506debbb54525e3e8eb612892488eb`。
- [verified] 严格 Schema/canonical/body-free 校验通过；V3 预检 ready_for_real_call，
  external_provider_calls=0、held_out_executed=false；纠正过时测试路径后 `26 passed`。
- [closeout] 相关模块编译、git diff --check 与项目治理检查均通过；本轮只新增脱敏回执及必要
  状态/学习记录，不增加实现文件或重复学习文档。
- [next] 当前为 `candidate-fresh-g53-3l-protocol / completed-real-observation /
  pending-v3-domain-authorization`，下一次明确继续直接执行一次全新 V3 有界真实领域验收。
  本批未修改产品代码/前端、旧考卷/回执、GLM-5.2 回退或主工作树；不注册候选。

## 2026-09-05：RQ-235 V3 真实领域验收结束

- [authorized] 执行前 HEAD `9c82238ba72ffb65982f96c5358e1c79edc1cc35` 干净且远端同步；
  相对公共代码 `110f9e8` 只有文档与 RQ-234 回执变化。既有 V3 回执不存在，预检通过后仅运行一次。
- [real] 领域 2/27 次调用、6936 Token、29344ms；含既有协议累计 5 次/8052 Token。
  首案检索 0 片段，rejected/evidence_required，未评测/修订；其余 skipped，admitted=false。
- [receipt] `zhipu_glm53_flash_hardened_domain_v3_rq235_v1.json`：7451 bytes，
  SHA-256=`2bf87351e38e4b6617604f4728d46047b710c7c11734630f4b364374ed545fcc`，严格校验通过。
- [verification] 纠正计划过时测试路径后 V3/执行器/预算 48 passed；总检新 V3 分流红灯复现后
  最小修复，相关 22 passed。离线检索对照零 Provider 调用；没有重试真实验收或覆盖旧证据。
- [next] 只做候选检索合同离线诊断/加固，不改产品默认、前端、GLM-5.2 回退或质量/安全门。
- [closeout] 相关模块/测试编译、git diff --check 与治理检查通过；新证据仅配套最小测试分流，
  真实运行身份仍是既有公共代码 `110f9e8`，不是把收口测试提交冒充另一轮模型运行。

## 2026-09-05：RQ-236 候选检索合同离线加固

- [implemented-local] `app/rag/coaching_query.py` 提供 `coaching-query-recovery-v1`：原查询优先，
  只有单一安全教练主题在零命中/`insufficient_evidence` 时最多补查一次；保留 `top_k` 与全部
  过滤条件，不降低 BM25 `15.0` 或查询覆盖率 `0.18`。自然语言采用显式别名与安全连接词白名单，
  混合主题、未知/注入式文本、冲突、无适用资料和异常不补查。
- [implemented-local] `ProductionDomainCaseExecutor` 新增默认关闭 `retrieval_hardening`，必须
  同时绑定候选 request policy 与 `quality_hardening=True`；V2 gate 在 Provider 调用前拒绝，V3
  gate/CLI 显式要求并开启。EvidenceDiagnostics 将本地补查次数与模型工具调用分开投影，旧空值
  字段继续省略以保持历史回执兼容。
- [verification-local] 查询恢复、执行器、V2/V3 版本隔离与完整候选链路共 `51 passed`；compileall、
  `git diff --check`、治理检查通过；provider calls=0。
- [verification-public] 实现提交 `ed62dbbc80506a8bcfae7eefb132348b21e587e0` 的 Actions
  `33943854904` 中 `pytest`、`postgres-migrations`、`packaging-smoke` 三任务均成功且 head SHA 精确匹配。
- [boundary-next] 当前 checkpoint 为 `candidate-retrieval-contract-hardening / completed-public /
  pending-next-decision`；下一步只裁决是否另立新鲜资产/协议，在此之前不重跑 RQ-235、不发真实请求、
  不注册候选、不改默认模型或前端。

## 2026-09-05：RQ-237 全新检索加固领域资产离线实现

- 已新增独立检索加固 V3 Dataset、输入计划、Context 快照、匿名 fixture、协议、预算报告、资产准入
  与候选门控模块；身份与旧 RQ-235/RQ-227/RQ-230 完全隔离。
- 聚焦 no-I/O 资产/门控测试 `5 passed`，compileall、`git diff --check`、governance 通过，provider calls=0。
- 当前从 `completed-design / pending-offline-implementation` 推进至 `completed-local / pending-public-ci`。
- 下一步是同一实现 SHA 的 exact-SHA 公共 CI；随后才建立新鲜 G53-3-L，真实领域观察仍需单独授权。

## 2026-09-05：RQ-237 实现纠正

- 复核发现初版实现的历史排重漏掉 RQ-235、输入计划没有显式策略身份，且预算重建默认关闭检索加固。
- 已将 `coaching-query-recovery-v1` 与 `quality_hardening/retrieval_hardening` 绑定到新计划/协议；
  纳入 RQ-235 旧计划排重，并在准入中锁定 85 分、事实/引用/注入/来源门。
- 开启真实候选检索路径重建后，最坏 token 墙更新为每案 `205000`、全域 `613000`；旧 V3 预算仍为
  `203000/608000`，并将新墙传递到候选预算执行器。
- 修复后的聚焦与相邻测试 `83 passed`，compileall、diff check、governance 通过；下一步为修复提交的
  exact-SHA 公共 CI，provider calls=0。

## 2026-09-05：RQ-237 修复提交公共 CI 与新鲜协议

- 修复提交 `d7a92abdb17ac9ea246f4ed3a29bf63c30408a74` 的 Actions `33963143593` 三任务
  exact-SHA 全绿（pytest、PostgreSQL migrations、packaging-smoke）。
- 同一实现身份的新鲜 G53-3-L 严格 `3/3` 调用通过，`1109` tokens、`12234ms`，SDK retries=0；
  脱敏回执已写入候选能力结果目录。
- 当前 checkpoint 进入 `completed-real-observation / pending-retrieval-hardened-domain-observation`；
  下一步是新资产一次有界真实领域观察，不重跑旧考卷或注册候选。
