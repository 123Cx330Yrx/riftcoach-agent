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
