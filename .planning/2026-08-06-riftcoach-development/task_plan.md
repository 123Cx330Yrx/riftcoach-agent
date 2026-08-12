# RiftCoach 持续开发计划

## Goal

在不改变既定阶段 0-8 和用户已确认子阶段的前提下，以可恢复、可审计、逐步
教学的方式推进 RiftCoach；任何当前状态都必须由仓库文件和测试证据支持。

## Current Phase

Phase 6.9 - 5D-6b（in progress: P1-P5 and production adapter offline mapping complete; real adapter protocol slice next）

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

- Status: complete
- 根据真实 Bad Case 和 5C-5 证据决定暂缓还是引入模型兜底。
- 记录收益、风险、替代方案和采用门槛。
- 本阶段是决策门，不默认需要编写 LLM Router。

### Phase 5 - 进入 5D 前复核

- Status: complete
- 只有 5C-1 至 5C-6 全部完成后，才把唯一下一步改为 5D。
- 对照路线、能力矩阵、需求账本和测试，确认没有遗漏或越级。

### Phase 6 - 5D Python 受限 Agent Loop

- Status: in_progress
- `5D-entry-design` 已完成：审计现有接缝、比较三种组合方案并接受 ADR-0011。
- `5D-1` 已完成：统一 Skill I/O 文本、selected name/version、安全 run ID、Harness
  规范输入摘要和 Catalog-backed 执行前校验。
- `5D-2` 已完成：两个 Skill 的 allowlisted 最小上下文、信任标签、确定性
  `ContextSizer`、整段预算选择和不可信知识引用投影均已有 TDD 证据。
- `5D-3` 已完成：Manifest-only `AgentRunCompiler`、完整消息估算、逐轮累计 Context
  门禁和协作式总 deadline 均已有 TDD 证据。
- `5D-4` 已完成：共享知识 evidence converter、`SkillAgentDraftPreparer`、两个真实
  Skill 的 Fake Provider + 真实 `knowledge.search` 以及 provenance/失败边界均已有
  TDD 证据。
- `5D-5` 已完成：统一 `DraftPreparationStep`、旧顺序 Adapter、唯一 ReviewHarness
  控制流、`SkillReviewExecutor` 和 Artifact 驱动 typed terminal output 均已有 TDD
  证据；两个真实 Skill 已通过 Fake Provider + 真实本地知识工具的完整组合测试。
- `5D-6a` 已完成：`StructuredResponseContract` 贯通 ChatRequest、Capability
  Negotiation 与 `llm.chat`；严格 Pydantic Evaluation Schema、最多一次同合同
  repair 和 Harness fail-closed 降级均有 Fake Provider TDD 证据。
- `5D-6b` 进行中：disabled-thinking 下 P1-P5 低层协议 5/5 真实通过；生产
  `ZhipuProvider` 已用离线 TDD 映射四类消息、JSON mode、Function Calling、请求级
  工具别名与 fail-closed 响应边界，尚未执行真实 Adapter 协议或领域 Skill 切片。
- 后续按 5D-1、5D-2、5D-3、5D-4、5D-5、5D-6a、5D-6b、5D-7 和 exit review
  逐项推进，每次只授权一个检查点。
- 5D 及以后仍按 `docs/roadmap.md` 和后续批准的子阶段逐项展开，不得跨到 5E。

## Next Step

进入 5D-6b Real Adapter Protocol Slice 的离线设计与 TDD：为同一生产
`ZhipuProvider` 的真实 structured request 与 `AgentLoop + fixed read-only tool`
往返建立硬调用预算、脱敏结果和失败停止合同。本步不执行领域 Skill、第二厂商或 5D-7。

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
| 5C V1 暂缓 LLM Router fallback | 只有一个小型合成域语义失败；立即引入模型必须复核 selected，且当前 GLM Adapter 没有端到端结构化输出，收益不足以覆盖延迟、成本和故障复杂度 |
| 类型化入口和澄清优先于模型语义复核 | 显式任务上下文比猜测自由文本更可靠；未来只有新鲜数据出现多个独立失败族并通过新 Eval/ADR 时才重开模型方案 |
| 5C 退出复核通过，5D 成为唯一下一步 | 六个检查点均有实现、评测或 ADR 证据；退出审计修复了命中证据身份与冻结点标注，已知执行缺口明确归入 5D |
| 5D 先设计和拆分再实施 | Context、结构化输出、权限预算和 Harness 接线都需要独立教学验收，不能再次把一个大批次等同于整个子阶段完成 |
| AgentLoop 作为 Harness 的 evidence-aware draft preparation | 保留 Agent 的动态白名单工具选择，同时让现有 Harness 继续掌握唯一评测、修订和发布权 |
| 用 `DraftPreparationStep` 作为唯一新接缝 | 旧 Retriever/Generator 可通过顺序 Adapter 兼容，新 Agent 路径返回同一 CoachDraft + KnowledgeEvidence，不制造第二套质量平台 |
| Provider 厂商选择放在 5D-6b 准入门 | 先稳定结构化输出和领域评测合同，再实测 GLM 并最多比较一个候选；不按视频热度提前锁定 DeepSeek/Qwen/Kimi |
| 5D-1 用 selected name + version 锁定路由身份 | 只保留名称无法发现路由后 Catalog Skill 版本漂移；权限仍从当前同名同版本 Manifest 重新取得 |
| run ID 使用一个跨 Harness/Skill 的可移植规范 | Manifest、Store 和执行入口若各自校验会产生安全与兼容漂移；ASCII 单组件同时适配 Windows 和 Linux |
| 输入绑定复用 Harness 真实 Artifact 字节编码 | 对同一语义采用不同 JSON 格式会得到不同哈希；共享编码才能让 5D-5 的真实 Artifact 与 5D-1 内容承诺逐字节对上 |
| 5D-1 只做内容承诺，不创建 Harness run | 真实落盘、状态迁移和 terminal output 属于 5D-5；当前先建立可独立测试的执行前 fail-closed 边界 |
| 5D-2 使用 trust-typed section 再渲染现有 ChatMessage | 先保留来源、指令权限、必需性和优先级，才能机器检查不可信边界；不另造 Provider 消息协议 |
| 近期与单局使用不同 allowlist 投影 | Summary 允许扩展字段；整份序列化会静默扩大模型可见数据，并让单局上下文混入近期聚合与其他对局 |
| 必需段超预算失败，可选段只整段保留或省略 | Policy、Skill 指令和核心事实不能静默截断；完整 section 选择避免半截 JSON、表格行和 citation |
| 默认 ContextSizer 是可注入的确定性 preflight | 真实 Provider 尚未在 5D-6b 准入；当前估算保证可重复选择，不冒充厂商 tokenizer 或真实 Usage |
| 5D-3 采用薄 `AgentRunCompiler` 并扩展现有请求/Loop | 现有 `AgentRunRequest` 已拥有大部分权限预算字段；包装或平行请求会复制控制面 |
| Context ceiling 成为 `AgentRunRequest` 一等字段 | 只写 metadata 无法阻止第二轮 Provider 调用；Loop 必须在累计消息增长后仍能读取硬上限 |
| 完整消息估算包含 ToolCall envelope | 大参数存在于 `tool_calls.arguments` 而非 content；只估 content 会留下可绕过的预算缺口 |
| Manifest `timeout_s` 收紧为 cooperative total deadline | 每次外部调用只获得 remaining budget；同步函数不可硬抢占的限制保留，不伪装成强制取消 |
| 5D-4 新旧路径共用一个 KnowledgeEvidence converter | citation 编号、来源去重与冲突拒绝必须只有一套语义，避免旧 Harness 和 Agent 路径漂移 |
| Agent 证据只来自实际 ToolExecutionRecord | 模型 Markdown 中声明的来源不可作为 provenance；无工具回答合法但 Evidence 必须为空 |
| 5D-4 不重写模型文本补 K1 引用 | 运行后 citation ID 与模型生成时观察到的工具 payload 尚未统一；引用覆盖和支持度留给 5D-5/5D-7 验证 |
| ReviewHarness 只依赖一个 DraftPreparationStep | 新旧路径都进入同一评测、修订与发布状态机，避免可选构造器组合或 `run_prepared()` 形成第二套控制流 |
| AgentRunResult 保留在 SkillReviewExecutor 外层 | Harness 只消费领域中立 draft/evidence，不反向依赖 Agent 模块；Trace 持久化仍留给 5E |
| typed output 只从 terminal Manifest 与已验证 Artifact 构造 | 模型返回和内存对象不是发布真相源；最终报告、最终 attempt 分数、证据来源与输入 commitment 均可独立审计 |
| 5D-5 不从 `app.skills` 根包重导出 executor | 显式子模块导入保持 Agent compiler → Skill execution 的依赖方向，避免 package initializer 循环引用 |
| 5D-6a 采用请求声明 + capability + Adapter 严格验证 | 只替换 parser 不能让 Provider 知道结构化要求；另造 Harness 调用路径又会复制控制面 |
| Coach 报告继续使用 Markdown | 结构化输出首先保护机器消费的 Evaluation 控制数据，不为 JSON 形式牺牲报告可读性 |
| Schema repair 最多一次且必须重新严格验证 | 修复是受限的第二次模型调用，不允许正则抽取、默认补字段或无限自愈 |
| 5D-6a 首先接入 Evaluation 控制数据 | 评测 score/verdict/issues 会影响发布；Coach Markdown 继续使用现有质量门禁而非被强制 JSON 化 |
| 5D-6a 不改 Zhipu SDK 映射 | 合同和本地验证可先稳定；真实厂商能力、响应格式和成本必须由 5D-6b 实测决定 |
| 5D-6b 使用请求级工具别名表 | 智谱函数名不允许点号，而 RiftCoach 内部使用 `knowledge.search`；Adapter 编解码隔离厂商约束，不污染 Manifest 与 ToolRuntime |
| GLM 作为首个生产 Adapter，不是最终厂商锁定 | 先用一套真实实现证明 Provider-neutral 边界；DeepSeek/Qwen 等只在同任务同评测决策门打开后比较，不能把适配正确性与模型优劣混成一个变量 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 授权后的 P1 diagnostic 首次启动被本地 `LLM_PROVIDER=glm` 与内部 ID `zhipu` 的配置门禁拒绝 | 1 | 在 client factory 前失败，真实调用数为 0；沿用首轮实验的子进程级规范化为 `zhipu`，不改 `.env`、不打印 Key，再执行唯一获授权请求 |
| 干净环境验证把 TEMP 内旧 venv 的递归清理与安装串在同一 PowerShell 命令，被终端安全策略拒绝 | 1 | 命令未执行、无文件变化；改用带随机 ID 的全新 TEMP 目录且不做任何递归删除 |
| Task 4 首次公开 CI 因无上界 `openai` 解析到 3.0.0、缺少 SDK 2.x 的 `httpx` 合同而收集失败 | 1 | 不用额外 `httpx` 掩盖大版本漂移；把当前已验证合同收紧为 `openai>=2,<3`，用全新临时环境重装、回归并重新验证 CI |
| Task 4 收尾把唯一下一步写成授权门时漏掉 canonical `5D-6b` 字面键 | 1 | 治理预检阻止接受状态；保持授权范围不变，只在唯一下一步补回检查点键后重跑 |
| Task 4 陈旧状态扫描把 `*` 直接放进 Windows `rg` 路径参数 | 1 | 命令在只读扫描阶段返回路径语法错误且未运行后续门禁；改为显式列出两个设计文件，不重复通配路径 |
| 5D-6b 状态/决策同步补丁把 `截至` 误当独立一行 | 1 | `apply_patch` 原子拒绝且无部分修改；拆为 canonical state 与真实相邻日期文本两个补丁 |
| canonical status 改为进行中时移除了治理要求的“唯一下一步”固定元数据行 | 1 | 保留 `status: in_progress`，恢复唯一一条“唯一下一步”并在该行注明当前只做实验设计 |
| 提交前把多个 Git 检查用分号串行，cached diff 的 EOF 空行失败未阻止后续 commit | 1 | 立即删除多余 EOF 空行并补记错误；后续检查与 commit 分开调用，成功检查后才提交 |
| 5D-6b 实施计划 Next Step 只写实施文件与 Task，漏掉 canonical checkpoint 字面键 | 1 | 治理预检在功能代码前阻止；补回 `5D-6b` 后重跑，不改变阶段或任务范围 |
| 5D-6b 宽回归命令猜测了不存在的 `tests/test_provider_structured.py` | 1 | pytest 未收集任何测试；先列出真实测试路径，再改跑 `test_structured_output.py` 与实际评测测试，获得有效回归证据 |
| 5D-6b 受控诊断提交前 cached diff 发现两份新设计文档 EOF 多余空行 | 1 | 检查阻止 commit；用小补丁删除尾部空白，并重新暂存后独立复跑 cached diff check |
| P1 改为精确哨兵校验后，P4 失败案例的旧夹具仍返回泛化 `ok` | 1 | 严格边界正确让案例提前停在 P1；只把该夹具改为精确哨兵，保留 P4 才是目标失败点并重跑完整回归 |
| 5D-6b P1 诊断恢复时猜错 ADR-0011 文件名 | 1 | 只读命令未改文件；先用 `rg --files docs/adr` 列出真实路径，再读取 `0011-compose-skill-agent-loop-through-harness-preparation.md` |
| 原始 5C-1 至 5C-6 未持久化，文档误写 5C 完成 | 1 | 恢复完整账本，建立根级约束和活动计划，并修正所有冲突状态 |
| 旧规划目录无 active pointer 且停在 2026-08-01 | 1 | 新建持续开发计划并写入 `.planning/.active_plan` |
| `session-logs` 说明依赖的 `jq` 在本机不可用 | 1 | 使用 `rg` 和 PowerShell `ConvertFrom-Json` 流式读取同一原始 JSONL |
| PowerShell 默认读取 UTF-8 中文出现乱码 | 1 | 所有中文审计统一显式使用 `Get-Content -Encoding utf8` |
| 最终并行一致性扫描因 `rg` 无匹配返回退出码 1 | 3 | 5D-3 收尾再次复发但未修改文件；无匹配搜索必须单独运行并显式输出 `NO_STALE_MATCHES`，严禁与测试、编译或治理门禁共享失败传播 |
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
| 静态搜索把复杂正则和 PowerShell 双引号混用，导致解析错误 | 2 | 5D-1 状态扫描再次复发但未修改文件；立即改用单引号与多个 `rg -e` 模式，后续禁止把含 `|` 的 rg 表达式放进 PowerShell 双引号 |
| 合并测试补丁时把 Router 测试上下文误指到 Contract 测试文件 | 1 | `apply_patch` 原子拒绝、未产生部分修改；按真实文件拆成小补丁后成功 |
| 历史结果的 Windows CRLF 字节哈希在 Linux CI checkout 后变化 | 1 | 仅将该不可变归档标为 Git binary，保留原始字节；两个后续 Actions run 均成功 |
| 5C-6 首次陈旧短语扫描把“不得进入 5D”和“不能声称 5C 已完成”等保护语句误报为陈旧状态 | 1 | 收窄为检查旧 checkpoint、旧唯一下一步和 5C-6 未开始/进行中等精确矛盾短语，结果为 `NO_CURRENT_STALE_MATCHES` |
| 5C-6 首次暂存区格式检查发现 ADR-0010 文件末尾有多余空白行 | 1 | 删除尾部空行，重新暂存后再运行 cached diff check |
| 5C 退出复核发现 `RouterDecision` 允许命中候选夹带无关证据 | 1 | 先补失败测试，再要求 selected/ambiguous 的 evidence 身份与 candidate 身份完全一致；rejected 仍保留部分证据 |
| holdout 元数据把双 Skill 冻结点误写为前一个文档提交 `cfd2084` | 1 | 用 Git 树确认真实双 Skill 合同首次位于 `4103d42`，只更正 provenance 并加回归断言，不改案例、规则或结果 |
| 治理负例把 `5D` 硬编码为陈旧检查点，状态合法推进到 5D 后不再失败 | 1 | 改用不可能与正式路线重合的 `stale-checkpoint`，让测试验证不一致语义而非某个阶段名 |
| 5D-2 初始并行读取猜测 `app/agent/models.py` 存在，导致命令组返回非零 | 1 | 没有修改文件；停止猜测 Agent 路径，先用 `rg --files app` 列出真实模块再读取 |
| 5D-2 首个合同补丁假设 `app/agent/__init__.py` 的 docstring 文本，原子校验拒绝 | 1 | 确认没有创建半个 context 模块；读取真实小文件后将新增模块与导出补丁拆开 |
| 恢复活动计划时把 `.active_plan` 值误当成仓库根相对路径，漏掉 `.planning/` | 1 | 命令只读且未改文件；改为显式从 `.planning` 拼接活动计划目录，并继续按恢复顺序读取 |
| 读取执行边界测试时猜测不存在的 `tests/test_skill_execution.py` | 1 | 先用 `rg --files tests` 查到真实 `test_skill_execution_boundary.py` 后读取；未改测试或源码 |
| 5D-2 聚焦回归猜测不存在的 `tests/test_provider_models.py` | 1 | 该次 pytest 未收集任何测试；列出真实 Provider 测试后改跑 `test_provider_tool_calling_models.py` 与 `test_provider_contracts.py` |
| 5D-4 共享证据转换首个补丁假设了 Harness `__init__` docstring | 1 | `apply_patch` 原子拒绝且没有产生部分源码修改；读取真实文件后把新增模块、Adapter 与导出拆成独立小补丁 |
| 5D-4 直接回答 Fake Provider 只声明 text chat | 1 | 编译后的 Skill 请求仍携带白名单工具规范，能力协商正确拒绝；修正测试 Provider 声明 `tool_calling`，不放宽生产门禁 |
| 5D-4 聚焦回归猜测不存在的 `tests/test_rag_provider.py` | 1 | pytest 在收集前退出、没有测试运行；先用 `rg --files tests` 获取真实 RAG 文件，再重跑实际测试集合 |
| 5D-4 ToolRuntime 失败测试的 Fake Provider 无条件读取成功 payload | 1 | 真实失败 Observation 的 `data` 为 null，测试 double 先按 `success` 分支，再验证 Preparer 从失败执行记录拒绝草稿并只暴露安全 code |
| 5D-4 项目决策同步补丁假设 `截至` 独占一行 | 1 | `apply_patch` 原子拒绝且无部分修改；按真实相邻日期行拆小补丁后同步 |
| 5D-4 收尾猜测 workflow 名为 `.github/workflows/ci.yml` | 1 | 只读失败且未执行脚本；先用 `rg --files .github/workflows` 找到真实 `tests.yml` 后按其门禁核对 |
| 5D-5 初始并行审计再次让无匹配 `rg` 的退出码 1 传播到整个批次 | 4 | 无文件修改；立即拆分治理预检与只读审计，后续无匹配搜索继续单独运行并显式处理 |
| 5D-5 审计猜测 Skill 输出模型位于独立 `output_schema.py`/聚合 `schemas.py` | 1 | 无文件修改；先读真实 Manifest 的模型引用并用 `rg` 定位到两个现有 Skill 模块 |
| 5D-5 terminal builder 测试 helper 用规范化前报告计算输入 commitment | 1 | 生产边界正确拒绝全部 7 个案例；测试改为先经过真实 Skill Input Model，再生成与未来 Harness 字节一致的 binding |
| 5D-5 从 `app.skills` 根包重导出 review executor 形成 Agent/Skill 循环 import | 1 | 收集阶段失败且无运行时产物；移除根包重导出，保持 executor 仅从显式子模块导入并记录依赖方向 |
| 5D-5 dry-run 临时目录的 `Remove-Item -Recurse` 被终端策略拒绝 | 1 | 已先验证绝对路径位于仓库 tmp；随后用 `apply_patch` 删除本轮生成的全部文件，未改用跨 shell 删除或放宽权限 |
| 5D-5 首次 cached diff check 发现两份新增计划文档尾部多余空白行 | 1 | 删除尾部空白行并重新暂存两份文档，再独立复跑 cached diff check |
| 5D-5 功能提交的 Git smart-HTTP 连续遇到 TLS 握手失败/EOF | 5 | schannel、OpenSSL、HTTP/1.1 与 TLS1.2 均未降低校验且失败；改用 GitHub Git Database API，逐 blob/tree/commit SHA 校验后原子更新 main |
| 5D-6a 恢复时把工具返回包装误当成 `.active_plan` 内容 | 1 | 只读命令未改文件；改为在同一 PowerShell 进程内读取并拼接 `.planning/<active>`，不再从工具展示字符串解析路径 |
| 5D-6a 审计时猜测不存在的 `app/tools/contracts.py` | 1 | 只读失败且未改文件；先用 `rg --files app/tools` 获取真实路径，确认合同位于 `models.py` 与 `schema.py` |
| 5D-6a 首个设计/状态合并补丁猜错错误账本的精确行 | 1 | `apply_patch` 原子拒绝，未创建半份设计；先独立新增设计文件，再读取计划尾部并用小补丁更新状态 |
| 5D-6a Adapter 初稿错误地从函数注解推导 output model | 1 | 在运行测试前发现；改为显式 `EvaluationResponseModel`，保证 transport Schema 与本地验证模型可审计对应 |
| 5D-6a Harness 失败路径测试遗漏 `CoachDraft` 导入 | 1 | 首次只覆盖 draft-preparation failure；补导入后重跑，确认真实覆盖两次非法结构化响应后的 deterministic fallback |
| SSH 诊断在 accept-new 后返回 `Permission denied (publickey)` | 1 | 只新增 GitHub host key，未修改 remote 或上传密钥；确认现有 SSH key 未获 GitHub 授权后停止 SSH 路径 |
| Git Database API 首个内联脚本含 PowerShell backtick，触发 JS 解析错误 | 1 | 脚本未执行、没有外部写入；改用字符串拼接构造 `HEAD:path` 后再运行 |
| GitHub commit API 首次把 PowerShell 多行消息序列化为数组并返回 422 | 1 | blobs/tree 已通过 SHA 校验，remote ref 未更新；改用单行 subject 重做 commit 步骤 |
| GitHub API commit 与本地 CLI commit 因消息尾部换行得到不同 SHA | 1 | 证明 tree/parent/作者/时间/消息均一致，定位仅差最后一字节；精确重建 API commit 对象并用 expected-old 原子同步本地/远端 refs，原提交仍在 reflog |
| 5D-5 公开验证记录组合补丁假设错误账本行顺序 | 1 | `apply_patch` 原子拒绝且没有部分修改；读取真实尾部后拆成状态/历史与计划/进度两组补丁 |
| 5D-6b 严格 JSON 补强补丁把两个文件更新块错误写进同一 hunk | 1 | `apply_patch` 原子拒绝且没有部分修改；立即拆为测试与实现两个小补丁，再单独运行 Zhipu 测试 |
| 5D-6b 能力组合边界补丁两次假设错误的源码相邻顺序 | 2 | 两次 `apply_patch` 均原子拒绝；读取精确行后把请求组合、参数编码与响应 finish reason 拆为独立补丁，不重复猜测上下文 |
| 5D-6b 收尾差异审查把“无陈旧措辞”的 `rg` 退出码 1 直接透传为整条命令失败 | 1 | 差异输出已完整生成且没有陈旧匹配；后续 stale scan 显式把无匹配视为通过，不再与长差异输出串成一个成功条件 |
