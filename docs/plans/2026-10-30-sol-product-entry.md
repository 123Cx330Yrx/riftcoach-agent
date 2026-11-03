# Flash / Sol 当前证据复用与产品入口

2026-10-30。承接用户在完整复盘后要求开始当前阶段工作。目标是让已验证候选进入真实产品消费路径，先完成版本证据核对和消费者检查，不再用熟悉稿重复实测代替接线。

## 本包目标与结束条件

1. 对原15三个执行版本、自然正式尾段和当前源码作可复现比较，回答哪些证据可复用。
2. 查清正常 Worker、Runtime、发布、数据库/API 的实际断点；补最新 Sol 合同的数据库消费检查。
3. 固定下一项实现范围及失败分支。阶段仍为8E，不改主树前端、不重跑15、不启动新付费批，不修改旧seal和默认产品合同。

## 已核实的证据复用

| 证据 | 真实版本 | 本次核对结论 |
|---|---|---|
| 原15前12例 | `34abe04e` | 已完成，保留各例原结果、原稿和费用 |
| 第13例重叠补丁恢复 | `58a947ca` | 同一句的协调选择是实际行为变化，恢复后的完整结果有效 |
| 最后2例 | `e7a7ab0b` | 与第13恢复版之间没有app/合同profile源码变化 |
| 自然正式修订尾段 | `227a8373` | 完整14步前缀继承、覆盖审查、唯一应用及同稿双fresh已闭环 |
| 当前开发树 | `b5a99545` | 与自然尾段冻结版本之间没有app/合同profile源码变化 |

禁网执行现有 `scripts.audit_sol_review_qualification.audit()`，当前真实Runtime库存与最终准备库存完全一致。它与10月25日原库存、10月28日协调库存都只有 `component_fingerprints` 和 `program_sha256` 不同，其余28字段相同，包括15例来源/标签、30份初审请求摘要、完整双职责政策、模型/路由和预算。

因此无需因commit变化自动重跑15。这里证明业务输入与合同可复用，没有制造同版本15次新执行，也没有把熟悉数据改称holdout。实际行为差异仍须分别保留：重叠补丁协调、观摩章节识别、漏检后的覆盖审查和持久续接。最新自然尾段为这些变化提供实际闭环证据；不据此改写原completion漏检。

详细机器比较、Git文件差异、原结果摘要和三份seal摘要核对保存在 `data/evaluation/results/sol_product_evidence_reuse_20261030.json`。只读原件，不重新计算历史首stdout冒充原guard，也未重新运行旧付费执行入口。

## 实际产品接缝

| 接缝 | 已有能力 | 尚缺什么，下一动作 |
|---|---|---|
| 普通 Worker composition | 现有注册表、默认Zhipu Provider、RecentReviewApplicationService、可靠任务与取消围栏 | `app/workers/composition.py`尚未选择最新混合候选；需要显式产品路由接线，不能仅改model字符串 |
| 候选 Application / Runtime | `build_natural_duty_candidate(candidate=sol_review_contract)`已实际生成请求、应用补丁并双fresh；支持Memory和Evidence依赖注入 | 复用现有构造，避免另建平行Agent栈 |
| 持久暂停与恢复 | `CandidateSession`、`SessionBudget`、`SessionWorkflow`保存成功步骤、未知用量和显式同项恢复；任务已有`recovery_required`状态 | 普通Worker/API没有消费该session暂停合同；优先核现有恢复状态及租约语义，不能把超时直接写终态或借过期租约自动重买成功步骤 |
| 修订流程 | facts与completion给逐字补丁；程序组装；两fresh对实际同一稿 | 开发Host逐项验收、冲突协调与产品正常自动运行须分开，不能将Codex作者线程当线上组件 |
| 发布 | 既有Evidence发布、owner权限、报告与Trace消费者可以复用 | 当前候选故意always-reject；不能翻一个false当完成产品采用，需独立产品adapter及明确采用记录 |
| 数据库与API | 旧GLM候选已验证真实临时Postgres/Worker/用量API | 本包把同一检查扩展到最新Sol双审合同，验证取消、用量、终态和不发布；不冒充默认注册或浏览器消费 |

### 必须讲清的两项区别

- 正常修订最短是6个模型调用：Flash工具选择/成稿2次、双初审2次、双fresh2次；直接通过最短4次。当前诊断合同实际硬限为10次、739840 tokens、3600活动秒，含4次人工恢复预留，单次300秒。不能写成产品已经采用“6次硬上限”，也不能默默把旧产品5次/401920 tokens/900秒扩成诊断包。
- 旧 `sol_natural_contract`允许有界自动超时重试；最新 `sol_review_contract`继承manual-reaped-timeout-v1，Provider已禁止自动重试。缺少session时不能得到可恢复暂停；不能把旧合同的行为误报成最新合同仍在自动补测。

## 产品实现方向

### 当前实现卡：普通Worker持久续接（已完成）

目标：显式选择 `sol-dual-development-v1` 后，普通任务可以暂停、由owner对准确checkpoint发起恢复，并从同一成功前缀续跑。默认路由与未准入发布策略保持。

路径：独立SQL continuation字段保存首次guard和逐次checkpoint；活跃租约CAS保存暂停，owner恢复事件再排队；每段保留自己的真实Trace，session累计账单单独投影到用量API。来源快照与工具结果随session重放；原始诊断的native gate仍保留，Worker开发入口明确不声称具备人工语义验收。

验证：真实临时Postgres＋确定响应，覆盖超时暂停、普通恢复不补测、显式单次补测、进程重建、成功步骤/来源不重取、用量累计、owner/旧checkpoint拒绝、取消与租约围栏；再跑受影响旧Worker/任务事件与session检查。

失败决策：未知intent、输入/原件变化和互斥修法只暂停该任务，不覆盖原件或重买前缀。普通恢复不授新预算；诊断预算不转成默认产品合同。证据完整性无法满足时保留暂停原因，其他任务继续。

复用 Recent Review：API创建任务 → Worker领取 → Application构建来源与Memory → Flash生成 → Sol双初审 → 必要时程序唯一应用 → 同稿双fresh → 已有Evidence/报告/用量消费者。

正常路径按两份意见的联合修订结果推进；某个审查职责漏检作为质量证据保留，不自动推导整条修订链无效。可选措辞、正常舍入不阻断。真实错误、互斥修法、来源/身份冲突或超时则保留进度，只暂停受影响步骤；不偷偷选一个语义冲突补丁、不自动购买重试、不把暂停伪装成已发布。

开发阶段独立审查用于验收实现和代表性结果，不成为每位产品用户每份报告必须等待的Codex人工节点。实现时先把正常执行、暂停、恢复、取消和发布资格分开；旧候选/封存记录保持原语义。产品模型、预算、发布合同的正式采用应独立记载，不从诊断成功自动推导。

下一项具体实现是**让普通任务生命周期承接最新混合候选的执行状态**：先核准现有任务状态、租约和恢复接口的可复用部分，设计最小持久暂停/同项恢复投影，再接Worker。用确定响应验证正常4/6调用、暂停后不重发成功项、取消不再发、原用量保留、失败不生成报告。实现边界稳定后才选择必要的真实消费检查，不追加全15和无关整套回归。

本包不顺便重做前端或README；它们在复盘的16组后续与62主题映射中单独保留。

## 普通Worker续接实现与运行说明

新增显式 `RIFTCOACH_WORKER_EXECUTION_PROFILE=sol-dual-development-v1`。默认值仍是 `legacy`；候选要求Flash生成配置和独立的 `sol-review-api` SecretSource记录（环境入口名 `RIFTCOACH_SOL_REVIEW_API_KEY`）。这是产品候选的原Sol路由，Codex开发环境切回official不自动替换它。本轮未加载真实凭据、启动队列Worker或调用真实模型。

`compose_continuation_executor`由正常Worker启动构造调用，继续复用原Application、Runtime、数据库任务与取消围栏。迁移 `0015_task_continuation`只新增nullable continuation记录及恢复事件；既有checkpoint和事件哈希格式保持。已经有恢复事件的数据库不能通过降级删去这段历史。本轮只在可丢弃测试库升级，现有产品数据库未迁移。

- `GET /tasks/{task_id}/continuation`：owner读取暂停原因、当前checkpoint SHA和累计用量，不返回原始来源、凭据或本机路径。
- `POST /tasks/{task_id}/resume`：携带新的 `Idempotency-Key` 和JSON `{"checkpoint_sha256":"<当前SHA>","manual_retry":false}`。普通恢复只重放成功结果；遇到原524或可恢复格式错误仍暂停。
- 仅在用户明确补测当前项时设 `manual_retry=true`；授权只供一个claim消费，同一POST重放不会再排队，旧SHA和其他owner被拒绝。不扩展原合同预算、不自动循环。
- 每次checkpoint产生后立即在当前租约下固定到SQL；取消、过期租约及旧Worker不能提交新进度。暂停可直接取消；取消与暂停提交竞争时取消优先。
- 来源、检索、Memory及其manifest复用首次原件；生成、初审与已成功fresh不重发。真实Trace按执行段单独保留，终段原文件create-only投影到旧查询入口。累计session用量由原预算/回执重读核验，API与现有用量面板显示已知tokens、未知预留和显式补测次数；不会把最后一段当全部成本，也不会把被发送围栏拦住的预留当HTTP/未知费用。
- 全部session/source/Memory/transport/segment文件位于 `<runs_root>/<run_id>/.continuation`，归入既有任务删除范围；旧封存目录不变。

代码入口：`app/workers/sol_continuation.py`、`app/persistence/task_continuations.py`、`app/tasks/continuation.py`、`app/product/session_usage.py`。API和Worker通过依赖注入使用同一continuation存储，业务服务不自行创建SQL连接。

边界：当前是未发布的开发候选入口，旧诊断仍要求原native gate。Worker不会伪造人工审查结论；互斥补丁暂停为 `session_awaiting_patch_coordination`，本包没有新增自动语义协调器。硬中断留下的未确认intent/未提交checkpoint、原件变化都不自动重发，仍需原回执核验或局部处理；本包不宣称所有硬中断都可自动恢复。恢复按钮的浏览器旅程、当前组合的真实模型产品消费、正式预算/发布采用合同仍待后续完成。

## 验证记录

- 当前15例/30初审请求禁网库存核对通过；三份完成seal摘要核对通过。
- 最新Sol7项与旧GLM7项的真实临时Postgres/Worker/API检查全部通过，pytest耗时162.39秒；结果写入 `data/evaluation/results/sol_product_worker_consumption_20261030.json`。模型与Riot为替身，数据库为新建可丢弃容器，检查结束后已删除；没有默认注册、浏览器检查或新模型请求。
- 只做与本包相关的pytest、治理和diff检查；不重新跑旧native全前缀或整套CI测试。

## Codex开发环境

用户本日明确从中转切回official。主线程已使用openai；原独立作者线程仍记录custom provider，因此仅将该legacy provider定义改为官方认证兼容，保留模型、历史作者和已封存事件。当前子线程未加载，平台拒绝脱离父会话单独resume；没有派发新任务，也未宣称原作者复用已通过。下次确需独立审查时先核实际父子会话/路由，不改旧事件、不冒用旧身份。配置备份与零模型调用记录保存在本机输出目录；这不是RiftCoach产品Sol路由或凭据的变更。

### 续接包验证结论

30项不同的临时真库检查通过，含8项新增续接边界及22项原任务/迁移检查；依赖注入调整后7项续接复核，终段原件冲突与未发取消2项最终复核。相关Runtime/session/Worker/合同89项、API组合/用量/查询50项、前端27项及typecheck通过。均使用确定模型/Riot替身；本包无真实模型调用、无产品库迁移、无浏览器端到端。新库存相对10月29日只组件/程序指纹不同，其余28字段和30份初审请求不变，旧快照和15例不改。结果见 `data/evaluation/results/sol_product_worker_continuation_20261030.json`。
