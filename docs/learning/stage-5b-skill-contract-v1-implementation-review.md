# 阶段 5B：Skill Contract V1 初学者实现复盘

## 1. 结论先行

5B 完成的不是“让 Agent 自动选择并执行一个 Skill”，而是先建立一种严格格式，
让 RiftCoach 能回答：

> 这个本地工作流包是谁、接收什么数据、允许用什么工具、最多消耗多少资源、应该
> 怎样工作、输出什么结构，以及哪些内容绝对不能做？

第一个样板是 `recent-form-review`。5B 建立时它的版本是 `0.1.0`；5C 加入第二个
真实 Skill 并调整相邻路由边界后，当前 Manifest 已升级为 `0.2.0`。这份复盘同时
标出“5B 原始闭环”和“后来在稳定合同上发生的演进”，避免把后续工作倒算成 5B。

5B 的核心产物是一个经过校验的 `LoadedSkill`，不是一次 Agent 运行：

```text
Skill 文件包
→ 严格解析与交叉校验
→ LoadedSkill（合同已知、尚无执行权）
```

## 2. 为什么 Agent 项目需要 Skill Contract

如果只把一段 Prompt 写在 Python 字符串里，程序很难可靠回答这些问题：

- 这段 Prompt 属于哪个业务任务，版本是什么？
- 它合法接收哪些输入，输出字段是什么？
- 它能调用 Riot API、RAG 还是所有工具？
- 最多循环几轮、调几次工具、使用多少 Context？
- 模型草稿是否可以直接发布？
- 文件名、Prompt 说明和代码模型发生漂移时，系统应该相信谁？

Skill Contract 把这些隐含假设变成可验证合同。底层软件原理有三个：

1. **关注点分离**：机器配置、任务方法和运行数据 Schema 分开负责；
2. **最小权限**：Skill 只声明完成任务必需的工具和预算，不能默认得到全部能力；
3. **加载不等于执行**：读取并验证一个工作流包，不会自动运行模型、工具或发布报告。

因此 Skill 不只是 Prompt。它是一个版本化的任务工作流包；`SKILL.md` 只是其中
负责“如何完成任务”的一层。

## 3. 三种事实源分别负责什么

```text
skills/recent-form-review/
├── manifest.yaml   机器可读的身份、触发、权限、预算、质量策略和模型引用
└── SKILL.md        面向执行模型的目标、步骤、证据规则和禁止行为

app/skills/recent_form_review.py
└── Pydantic I/O    运行时输入输出数据的代码权威
```

### 3.1 `manifest.yaml`：机器策略

Manifest 告诉代码：

- `name`、`version` 与 `schema_version`；
- 输入/输出 Pydantic 类的导入路径；
- Router 后来会使用的触发信息；
- `allowed_tools`；
- `max_iterations`、`max_tool_calls`、`timeout_s` 和 `max_context_tokens`；
- 质量门是否强制、最低分和是否允许确定性降级。

它不保存 Python handler，也不直接执行工具。

### 3.2 `SKILL.md`：任务方法

`SKILL.md` 告诉执行模型怎样复盘：只把上游确定性 Summary 当玩家事实、何时查询
知识、怎样区分事实/谨慎解释/训练建议、怎样引用 `source_id`，以及禁止编造版本、
胜率、出装、隐藏信息等内容。

其 frontmatter 只保留 `name` 与 `description`。Loader 要求这两个字段与 Manifest
完全一致，避免机器认为它是 A 任务，而 Prompt 却声称自己是 B 任务。

### 3.3 Pydantic I/O：数据边界

`RecentFormReviewInput` 接收：

```text
player_summary         已通过 Player Summary Schema v1.0 校验的确定性事实
deterministic_report   非空确定性报告
focus                  overall / laning / survival / economy / vision
```

它不接收 Riot API Key，也不让 Skill 自己重新计算比赛指标。

`RecentFormReviewOutput` 则把终态限制为 `published`、`degraded` 或 `rejected`：

- `published/degraded` 必须带报告；
- `rejected` 不得暴露未通过草稿；
- 评测分数限制在 0—100；
- 证据来源与 warning 通过结构化字段传递。

后来 5D-1 又在同一模型上补了严格 run ID、空白文本和重复来源规范化。这是稳定
合同被真实执行消费者深化的例子，不是 5B 当时已经完成的能力。

## 4. 真实加载数据流

调用 `load_skill("skills/recent-form-review")` 时，代码实际经过：

```text
Skill 目录路径
  │
  ├─ 检查 manifest.yaml 存在
  │
  ├─ yaml.safe_load()
  │    └─ SkillManifest.model_validate()
  │         ├─ extra="forbid"
  │         ├─ 名称 / SemVer / 模型引用格式
  │         ├─ 触发组与排除信号不变量
  │         └─ 权限、预算与质量策略范围
  │
  ├─ 目录名 == manifest.name
  │
  ├─ 检查并读取 SKILL.md
  │    └─ frontmatter 只能含 name/description
  │         └─ 两者必须与 Manifest 一致
  │
  ├─ importlib 导入 input/output 模型
  │    └─ 两者必须确实是 Pydantic BaseModel 子类
  │
  ▼
LoadedSkill(root, manifest, instructions, input_model, output_model)
```

加载后若要确认工具权限真实可满足，还要显式调用：

```text
validate_skill_tools(loaded_skill, active_tool_registry)
→ allowed_tools - registry 中已注册工具
→ 有未知工具则 SkillContractError
```

这个动作仍然不执行工具。它只证明 Manifest 声明的依赖在当前 Registry 中存在。

## 5. 控制权到底在哪里

5B 结束时的控制边界是：

```text
load_skill()
  └─ 只产生 LoadedSkill
       ├─ 不读取用户请求来选择 Skill
       ├─ 不把 SKILL.md 发给 Provider
       ├─ 不构造 AgentRunRequest
       ├─ 不执行 knowledge.search
       └─ 不调用 Harness 决定发布
```

后续职责依次属于：

- 5C `SkillCatalog + Router`：发现候选并选择、拒绝或报告歧义；
- 5D `SkillExecutionBoundary + Context/Compiler`：验证输入，把 Manifest 权限/预算
  编译为受限 Agent 请求；
- 5D `AgentLoop + ToolRuntime`：执行模型提出的合法工具调用；
- 5D `ReviewHarness`：评测、受限修订并决定发布/降级/拒绝；
- 5E `AgentRuntime`：统一 Event、Usage、Trace 以及 `run/stream` 表面。

这就是“合同先行”：后续执行层可以演进，Skill 的任务身份、最小权限和 I/O 边界
不需要跟某个 SDK 捆绑。

## 6. 真实代码地图

| 职责 | 权威文件/对象 | 初学者应抓住的重点 |
|---|---|---|
| Manifest Schema | `app/skills/models.py` 的 `SkillManifest` 及子模型 | `extra="forbid"` 和 frozen 模型让未知字段、非法范围与运行时修改 fail closed |
| Skill 包加载 | `app/skills/loader.py` 的 `load_skill()` | 严格读取 YAML、核对目录/Frontmatter、解析 Pydantic 模型，返回 `LoadedSkill` |
| 工具存在性 | `app/skills/loader.py` 的 `validate_skill_tools()` | 声明了未注册工具就拒绝，而不是运行时偷偷忽略 |
| 输入模型 | `app/skills/recent_form_review.py` 的 `RecentFormReviewInput` | 复用 `validate_summary_document()`，不让 Agent 把任意 dict 当可信比赛事实 |
| 输出模型 | 同文件的 `RecentFormReviewOutput` | 把报告可见性和终态组合固化为代码不变量 |
| 机器策略实例 | `skills/recent-form-review/manifest.yaml` | 当前版本、工具白名单、预算与质量门 |
| 任务指令实例 | `skills/recent-form-review/SKILL.md` | 工作流、证据规则和禁止行为，不是权限来源 |
| 合同测试 | `tests/test_skill_contracts.py` | 同时测试成功加载和各种 fail-closed 边界 |

## 7. 要求 → 源码 → 测试 → 公共证据 → 限制

| 要求 | 源码 | 直接测试 | 公共证据 | 仍然不能推出 |
|---|---|---|---|---|
| 合法 Skill 包可加载并解析 typed I/O | `loader.py`、`models.py` | `test_loads_recent_form_skill_and_resolves_typed_models` | 含 5B 的公开快照通过 Actions `31063937488` | Skill 已被 Router 选中或执行 |
| 输入必须是兼容 Summary v1.0 | `RecentFormReviewInput` | `test_recent_form_input_reuses_player_summary_validation` | 同上 | Summary 的每个事实一定来自真实 Riot 网络调用 |
| 终态不能泄露拒绝草稿 | `RecentFormReviewOutput` | `test_recent_form_output_enforces_publication_boundary` | 同上 | 质量评测本身一定正确 |
| Manifest 未知字段和冲突示例被拒绝 | `SkillContractModel`、`SkillTriggers` | `test_manifest_rejects_unknown_fields_and_overlapping_triggers` | 同上 | 自然语言触发已充分泛化 |
| 触发组、正负信号无重复/冲突 | `SkillTriggerGroup`、`SkillTriggers` | 两个 trigger rule 测试 | 同上 | Router 已实现；那是 5C |
| 工具白名单必须能在 Registry 中解析 | `validate_skill_tools()` | `test_skill_tool_permissions_must_exist_in_active_registry` | 同上 | 工具调用一定成功，或 Skill 拥有完整应用权限 |
| 目录、Manifest、SKILL.md 身份一致 | `load_skill()` | `test_loader_rejects_manifest_and_frontmatter_drift` | 同上 | Prompt 内容已经被模型级注入评测覆盖 |

提交 `02528db` 同时包含了 5B 与早期 5C 合同/实现。后续治理审计明确指出：一个
提交跨过多个教学检查点，不能因此把它们合并成一个阶段。表中 CI 只能证明包含
5B 的公开仓库快照可重复构建和回归，不能替代 5B 本身的概念边界。

## 8. RQ-067 时的可复现运行观察

当前仓库可直接观察 Loader，不需要 API Key、网络、Riot 或模型调用：

```powershell
.\.venv\Scripts\python.exe -c "from app.skills.loader import load_skill; s=load_skill('skills/recent-form-review'); print(f'{s.manifest.name}@{s.manifest.version}'); print(f'input={s.input_model.__name__} output={s.output_model.__name__}'); print('tools=' + ','.join(s.manifest.permissions.allowed_tools)); print(f'instructions_chars={len(s.instructions)}')"
```

RQ-067 补齐时的实际输出为：

```text
recent-form-review@0.2.0
input=RecentFormReviewInput output=RecentFormReviewOutput
tools=knowledge.search
instructions_chars=1468
```

这四行分别证明当前 Skill 身份/版本、Pydantic 模型解析、声明式工具权限和指令文件
已被加载。它们不表示模型读过指令、工具已执行或报告已发布。

当前合同聚焦测试可运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_skill_contracts.py -q
```

本次实际结果是 `18 passed`。5B 原始提交只有一个真实 Skill 和八个核心合同测试；
当前数量还包括后续 `single-match-review`、文本硬化和 Timeline 未知语义回归，不能
把 18 项全部冒充为 5B 当时一次完成。

## 9. 失败与安全边界

### 9.1 为什么坏包要在加载时失败

如果缺文件、YAML 损坏、目录名漂移、模型导入失败或工具不存在时仍静默跳过，
同一个服务进程可能在不同请求中看到不同能力。5B 选择 fail closed：启动/组合时
尽早暴露配置错误，不让错误拖到模型已经运行以后。

### 9.2 Prompt 不能给自己授权

`SKILL.md` 即使写了“请调用某工具”，也不能改变 `manifest.permissions.allowed_tools`。
真正的工具定义来自 `ToolRegistry`，实际执行还必须经过 `ToolRuntime`。自然语言指令
不是权限系统。

### 9.3 Typed output 不等于质量正确

Pydantic 能证明字段、范围和终态组合合法，不能证明报告中的结论忠实。发布权仍在
Harness；这也是为什么事实审查后来继续保留为 `EvaluatorStep`，没有为了凑数量包装
成第三个 Skill。

### 9.4 当前仍不包含什么

5B 本身没有：

- 用户意图路由或澄清；
- AgentLoop 执行与真实 Provider Tool Calling；
- Prompt/Context 优先级和注入防护完整评测；
- Session、Memory、MCP、Multi-Agent 或 LangGraph；
- 正式 Auth、数据库、API、SSE 或前端；
- 远程 Skill 市场、热更新或运行中自动重载。

## 10. 后续演进：哪些属于深化，哪些属于职责修正

### 10.1 第二个真实 Skill

5C-5 前新增 `single-match-review`，复用相同三层合同，但使用自己的 typed I/O、目标
match ID 和单局证据边界。它证明“新增业务工作流不用改领域核心”，同时让 Router
第一次面对两个真实相邻任务。

### 10.2 事实审查为什么不是第三个 Skill

源码复核发现事实审查已有独立 `EvaluatorStep` 和强制 `ReviewHarness` 控制流。
再包装 Skill 只会复制 I/O、Prompt 和质量门，并产生“质量检查器还要不要再被质量
检查”的递归语义。ADR-0009 因此把首批 Skill 修正为两个；能力没有删除，只是职责
分类更准确。

### 10.3 5D/5E 的执行深化

5D 把 Manifest 中的权限、预算和质量策略编译到实际 Agent/Harness 运行，并验证
Skill name/version 与输入 Artifact 没有漂移；5E 再记录完整 Trace/Usage。稳定合同
因此成为自有 Python Runtime 与第三方 Runtime 对照的共同基线，而不是被框架替换。

## 11. 面试时可以怎样说

> 我把 Skill 设计成版本化工作流合同，而不是单个 Prompt。Manifest 管理机器可读
> 身份、权限、预算和质量策略，SKILL.md 管理任务方法与禁止行为，Pydantic I/O 管理
> 数据边界。Loader 会严格核对目录、Manifest、Frontmatter、模型引用和工具注册，
> 但加载本身不授予执行权；后续 Router、AgentLoop 和 Harness 分别负责选择、执行和
> 发布控制。

若面试官追问为什么不用 LangGraph 或 Agent SDK 定义 Skill，可以答：

> 这些属于可替换 Runtime/编排层。RiftCoach 的领域任务、最小工具权限、输入输出和
> 质量门必须由项目自己拥有；候选框架必须消费同一合同并通过同一评测，不能反向让
> 领域逻辑依赖某个 SDK。

## 12. 面试时不可以怎样说

- “5B 已经实现了完整 Skill 执行系统”；
- “两个/三个 Skill 就是 Multi-Agent”；
- “SKILL.md 写了允许工具，所以模型可以直接调用该工具”；
- “Pydantic 输出合法，所以报告内容一定真实”；
- “18 个测试和公共 CI 证明自然语言路由或真实模型质量”；
- “事实审查 Skill 已经实现”；它最终保留为 Harness Evaluator；
- “Skill 系统基于 LangGraph/Pi/Claude Agent SDK”；当前合同是框架中立的自有边界。

## 13. 退出判定

5B V1 已建立一个可严格加载、可版本化、工具最小授权、预算有上限、I/O 类型化且
不拥有发布权的真实 Skill 样板。原实现、测试和公开快照证据仍有效；本次 RQ-067
补齐的是项目所有者可独立复习的实现解释，不改变产品代码或历史完成状态。

5C 的 Router 教材见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`；5D 怎样执行 selected Skill，
见 `docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`。
