---
state_schema: 1
main_stage: 8
substage_group: "stage-8-multi-agent-reliable-runtime-productization"
current_checkpoint: "8e-productization"
status: in_progress
pause_reason: ""
---

# RiftCoach 当前执行状态

> 本文档是“项目现在做到哪一步”的唯一事实源。路线职责看
> `docs/roadmap.md`，历史需求看 `docs/requirements_change_log.md`，本轮执行
> 细节看 `.planning/.active_plan` 指向的计划，决策演变看
> `docs/roadmap_change_history.md`。

## 状态元数据

- 最后更新：2026-09-03（RQ-210 已完成候选会话分资源关闭报告的本地实现与 exact-SHA 公共 CI；实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 的 Actions run `33657368435` 三 job 全绿；RQ-209 的真实回执与 schema 保持不可变；RQ-208 已完成 RQ-207 候选流硬墙钟、会话取消/关闭和 Usage 尾帧实现的 exact-SHA 公共 CI；RQ-207 离线实现已完成；RQ-203 已完成版本化候选 recovery 诊断协议设计；RQ-202 已完成候选 recovery 诊断边界复核、最小离线加固及 exact-SHA 公共 CI；RQ-201 已完成候选评估台实现的 exact-SHA 公共 CI；此前 RQ-199 已完成隔离候选评估台设计、RQ-200 已完成 fake/local 实现；此前 RQ-197 的候选边界观察合同已完成本地实现，并已取得同 SHA 公共 CI；此前 RQ-192 的 provider-neutral 流式装配合同与 RQ-193 的智谱适配器一致性接缝均已完成本地；
  RQ-193 实现提交为 `8bcbaa5ba467fcaad76193d3790d34a106a47d72`，conformance 聚焦回归为 `13 passed`，
  只使用测试内伪造 SDK 分块，未改生产 Provider、未发真实 API。该提交的同 SHA 公共 CI run `33489903978`
  已 `completed/success`（pytest、postgres-migrations、packaging-smoke 三 job，head_sha 精确匹配），且包含全部
  Trace 脱敏断言。RQ-194 已在提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 完成候选级、仅显式调用的
  `ZhipuStreamAdapter` 本地实现与 `20 passed` 聚焦测试；该提交的同 SHA 公共 CI Actions run `33496237588`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success` 且 head_sha 精确匹配。
  这只证明候选接缝的公共可复现性，不代表产品代码已接线。候选未注册，严格 Flash v1 仍 2048/零额外调用，
  Stage 8/8E 继续 `in_progress`，`production_media=0`。RQ-195 已完成候选 runtime 接线架构评审，
  RQ-196 又完成了候选 runtime wiring design：冻结隔离评测调用方、body-free BoundaryObservation、
  四元身份、共享校验、v2 预算和独立 Trace 投影；仍不直接改产品 Runtime。以下为此前连续诊断记录。）
- RQ-211 最新状态覆盖：候选 close/wakeup 探针已在 exact-SHA 公共绿灯的
  `c31127b3c780fe4c493966d8b60f942d3b773fd4` 快照上完成一次真实请求；Actions run
  `33661910096` 三 job 成功。回执为 `908` bytes、SHA-256
  `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`，结果为
  `not_pending`：会话打开且只调用一次，观察到 reasoning/content 类别，但有限窗口内没有 pending reader，
  因而没有执行 cancel，也不能证明 close 能唤醒挂起读取。迭代器、外层 SDK stream 和组合关闭投影均为
  `closed`；回执保持 body-free。后续测试加固提交 `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c`
  的公共 run `33662730304` 被外部取消，不冒充通过。候选与产品边界保持不变。
- RQ-204 最新状态补充：版本化候选 recovery 诊断已完成 fake/local 本地实现与比例回归，
  系统 Python 3.13 用户环境已安装 `pytest 9.1.1`；项目验证仍使用仓库 `.venv` 的完整依赖。
- RQ-205 最新状态覆盖：提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 exact-SHA 公共 CI
  run `33598541029` 已三 job 全绿；公共 pytest 为 `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，
  PostgreSQL 控制面为 `201 passed, 1 warning`，另完成 fake/local 协议演练。当前唯一下一步是一次性授权的
  `candidate-recovery-diagnostic-real-call`，不自动发起真实 recovery。
- RQ-206 最新状态覆盖：在同一干净隔离工作树上，`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` 的
  Actions run `33603143606` exact-SHA 三 job 全绿；按一次性授权只发出 1 次 `glm-5.3-flash` primary。
  真实流观察到首事件、reasoning、可见正文、`stop` 和 EOF，但首个可见正文约 `151453ms`、总延迟
  `175875ms`，Usage 缺失且 close 失败，v2 回执安全记为 `fail_closed / elapsed_limit`，未触发 recovery。
  回执 `zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json` 的 SHA-256 为
  `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`、`4355` bytes。该结果不构成
  模型质量或生产准入结论；当前唯一下一精确项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，
  先设计硬墙钟取消与 Usage/终态尾帧处理，不自动重测。
- RQ-207 最新状态覆盖：候选专用会话、绝对墙钟监督、非阻塞取消/幂等关闭和 Usage 尾帧处理已在本地完成；
  四文件聚焦集合为 `67 passed`，compileall 与 diff check 通过，本轮真实 API 调用为 `0`。没有显式
  `session_opener` 时会在 legacy opener I/O 前以 `hard_deadline_unsupported` fail closed；显式 opener
  返回值仍需在调用后验证，同步 opener 永久阻塞或供应商 close 无法唤醒读取仍是未证明限制。候选保持
  disabled；RQ-208 已以提交 `015b022bfce6d03452f753794ac126a377f8355b` / Actions
  `33613113829` 完成三 job exact-SHA 公共 CI，真实重测仍需另行授权。
- RQ-208 最新状态覆盖：公共 `pytest` 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，
  PostgreSQL 控制面为 `201 passed, 1 warning`；网页契约/生产包、媒体审计工具链、RAG v1 与独立 4M
  holdout、治理、compileall 和 Harness dry-run 均通过。该证据只证明候选接缝公共可复现，不提升为产品
  Runtime 或生产能力；候选仍 disabled、`capabilities.streaming=False`，本轮没有新的真实 API。
- RQ-209 最新状态覆盖：在隔离工作树 `HEAD=cc5d5c82ddefd4e9932514634d53d1629e563655` 上，
  按“继续”只发出 1 次 `zhipu/glm-5.3-flash` primary；回执为 `4342` bytes、SHA-256
  `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`，总时长 `90015ms`，首事件
  `3421ms`，reasoning 非空但无可见正文、terminal、EOF 或 Usage，组合会话 `close_state=failed`，费用 unknown。
诊断层硬墙钟已在真实观察中触发，未发送 recovery 或重试；该组合关闭状态不能归因到某一个底层 SDK 资源，底层非阻塞/唤醒能力仍未证实，候选继续保持 activation gate disabled。
- 历史诊断记录：2026-09-01（RQ-190 已完成两次单路、有界的流式首个可见正文探针：同一冻结上下文、
  `reasoning_effort=low`、`max_tokens=2048` 下，`clear_thinking=true` 在 2.547 秒出现首个可见正文，
  `clear_thinking=false` 在 3.875 秒出现首个可见正文；两路均先观察到 reasoning，随后在正文出现时主动关闭，
  因而终态和 Usage 保持未观测。结果均 body-free，不能把首正文写成完整流式完成、跨轮清理语义、成本或生产能力；
  候选仍未注册，严格策略仍为 2048 输出上限和零额外调用，Stage 8/8E 继续 `in_progress`。此前 RQ-189
  已确认低档短同步可完成而两个 8192 同步窗口超时；RQ-188 已确认普通 API 的 Flash endpoint/model 路径可达且
  生成已开始）。此前 RQ-181 已在独立诊断工作树
  完成一次有界 Flash 响应完成度诊断；首个 Agent 回合原始
  `finish_reason=length`，2048 输出额度全部用于非空 reasoning、正文为空，适配器按设计以
  `incomplete_chat_response` 拒绝；这不表示模型一般质量、账号失败或生产成熟度。此前 RQ-180 已在最终实现 A/B 证据链上完成一次有界 G53-7 真实领域尝试，但因 `provider_response_invalid/incomplete_chat_response`
  未准入；这不表示模型一般质量、账号失败或生产成熟度，Stage 8/8E
  继续 `in_progress`。G53-3 协议门仍保持通过；G53-4 只发出 1 次领域调用，首例以
  `unsupported_parallel_tool_calls` 安全失败，后两例按首错停止跳过。结果未保存 Key、Prompt、响应正文或
  reasoning；在该次旧尝试当时默认模型与既有工作树保持不变（后续 RQ-176 的 Flash-only 决定以本文当前段落为准）。此前即梦 Smart Edit raw 与零费用后处理审计已由提交 `f041643` / Actions
  `33042204532` 完成 exact-SHA 三 job；T/X identity fault split 已完成但仍是 research-only。用户随后明确拒绝
  沿用当前视频节奏，要求先重做全局持续呼吸 brief，并在付费前用 Image2 对确认母图做多张静态方向预览。
  旧代理端口 `7890` 已纠正为用户实际 HTTP 代理 `12000`；Image2 两张同构编辑预览主要是调色/提亮，第三次请求
  因 `403 insufficient balance` 停止，均不作为 motion direction。用户按 RQ-140 允许跳过 Image2，已完成一次
   首帧单锚点 12 秒 Seedance v3 生成；按 RQ-141 视觉审查拒绝，不进入 runtime，下一步先重写运动合同，
   不立即付费重抽或切换模型。随后按 RQ-150 完成 Ixtal first-frame-only Seedance preflight：exactly one
  POST，候选已下载并通过编码/无音频/稳定构图检查；按 RQ-153 暂准作为可替换研究候选联调，但视觉仍偏轻，
   来源权利与最终保留/调优/替换裁决待后续显式回看。）
- 2026-08-29 按 RQ-154 完成的 Region Entry Panel 两地区试水（历史，已由 RQ-157–RQ-162 取代）：
  `?surface=wallpaper-lab` 当时可在 Demacia/Bandle City 间切换本地动态候选，并将 typed `region` 参数带入
  Account；11 个没有 ready 动态候选的地区继续 pending。该历史切片仍是 research preview，未改变默认 `/`、
  `production_media=0` 或来源/许可门。MotionSites 已继续公开广筛，吸收的是可迁移的 hero/selector/interaction-state
  模式，不是整页照搬或新依赖。
- 2026-08-29 按 RQ-155 重新对照五模块视觉资源矩阵与旧日志中的完整 source 池。Portal 本轮只落地
  Riot/Universe 形状语法与 crest fallback、高级视觉目录的构图/字阶检查，以及 Motion/MotionSites/React
  Bits 等的局部 spotlight、双层 poster crossfade、菱形焦点标记和 aperture handoff 机制；OP.GG/电竞
  数据、Agent observability、Training 产品与 Timeline 参考仍绑定各自的 Workbench/Trace/Training 消费者，
  不在本轮偷做。新增机制不引入依赖，详细徽章和壁纸仍为 research-only，`production_media=0`。
- 2026-08-29 按 RQ-156 补齐被旧矩阵合并的 Design Prompts、PPT/Photoshop、Radix/shadcn、图表库、付费
  UI 候选与 League Displays/Steam Workshop provenance 记录。Portal 现在对所有已有本地细徽记渐进加载并
  在缺失/失败时回退 Universe crest；地区进入 Account 的 URL 带受限 `from=wallpaper-lab` 标记，刷新后可
  恢复返回地区选择语义。该补充不改变工作台后置顺序、来源/许可门或 `production_media=0`。
- 2026-08-30 按 RQ-161 完成 Account 表单的局部视觉卫生修补：桌面右侧 panel 上移一个受控的小幅度，移动端
  明确归零；Riot ID 与两个下拉控件统一字体基线，字段 caption 统一并提高可读性。该批只触及 Portal/Account
  presentation，不改变 Auth、Riot routing、Workbench、媒体采用或 `production_media=0`。
- 2026-08-31 按 RQ-163 完成 Portal/Account 到 Agent 主线的文档交接：README、活动计划、路线镜像和八维学习材料已补齐
  当前 Agent 底座、真实产品缺口、GLM-5.3 G53 闸门与 8E/8F 后续边界；未读取 Secret、调用外部服务或修改 `app/`
  与 `web/`。旧 RQ-154 两地区/第三地区动作明确仅保留为历史，`production_media=0` 不变。
- 2026-08-31 按 RQ-165 完成 G53-1 离线适配档案 TDD：普通智谱 API 的 `glm-5.3-flash` 使用独立
  `thinking=enabled`、`reasoning_effort=low` 档案；GLM-5.2/未知模型继续保留 disabled 回退。Provider、probe
  与受控 CLI 的请求映射、reasoning 脱敏、单/多 ToolCall 边界和模型隔离文件名已有本地证据；未发起真实调用、未改
  `.env`、默认模型、Workbench 或 `production_media=0`。官方文档确认的是公开 API 合同，不等于账号额度或领域准入。
- 2026-08-31 按 RQ-166 完成 G53-2 exact-SHA 公共 CI：提交
  `0f97b92683e4981842e745a695864deb611bb630` 对应 Actions run `33325222755`，`pytest`、
  `postgres-migrations`、`packaging-smoke` 三个 job 均 `completed/success`。公共 pytest 为
  `1912 passed, 145 skipped, 1 warning, 127 subtests passed`；没有读取/输出 Key、真实 Provider/Riot/OP.GG
  调用或默认模型切换，前端、Workbench、Auth、路由和 `production_media=0` 均未改。
- 2026-08-31 按用户继续执行 G53-3 有界协议门：仅临时覆盖为普通 API `zhipu` + `glm-5.3-flash`，
  运行 `adapter_protocol` 一次。脱敏结果
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol.json`（SHA-256
  `b10827f18dc810085a0d3883ebb7175709f4c244c30c937d5d220ab1ec1d0d9a`）记录 A1
  `authentication_failed`、A2 `skipped`，`calls_used=1/3`、`admitted=false`；没有重试或追加调用，
  也没有保存响应正文或 reasoning。该结果不能区分 Key 无效、权限不足或账户/端点接缝错误。
- 2026-08-31 用户确认 Key 来自普通 API Keys 页面且未购买 Coding Plan，并明确要求重开 G53-3。
  进程级预检发现本机 `.env` 的非敏感字段仍为 `LLM_PROVIDER=glm`、Coding 端点和 `glm-5.2`；未修改该文件，
  而是临时强制普通端点 `https://open.bigmodel.cn/api/paas/v4/`、`zhipu` 和 `glm-5.3-flash`。
  脱敏预检仅确认 Key 存在且格式为两段，不输出其值。重开后的 A1 仍返回 `authentication_failed`，A2 跳过，
  新结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry1.json`
 （SHA-256 `dde918b17f8f93914ccf8e330fd96e936699f5fa8313c30dcb6d69f5ae19e66c`）记录 `calls_used=1/3`、
  `admitted=false`；没有再发第三次请求。该结果仍不能区分密钥失效、请求接缝或服务端权限返回。
- 主阶段：阶段 8；Stage 7、Stage 8 entry design、8A、8B、8C 与 8D 均已关闭。Multi-Agent 产品候选按 ADR-0053 reject；
  当前治理指针为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  Batch E E1–E5、production shell/Auth gate、Timeline DTO/UI 与 bilingual/product-journey foundation 已公共关闭；完整
  8E/8F 尚未完成。G53-0 已按 RQ-164 完成本地无 I/O 审计，G53-1 已完成离线适配合同，G53-2 已完成公共
  exact-SHA 验证；G53-3 前两次旧 Key 尝试在 A1 认证阶段阻塞，用户更新普通 API Key 后第三次尝试已通过；
  G53-4 使用独立 Dataset/Input Plan/Context snapshot 执行一次真实门并拒绝，不构成公共 CI 或生产成熟度；
  RQ-171 已在本地修复 Flash 适配器的思考内容回放与多 ToolCall 顺序接缝；RQ-172 的 G53-5 本地真实矩阵
  已完成（11/11 calls、46,151 tokens、7/8 cases pass），RQ-173 又仅将 F7 的 `max_tokens` 从 512 调至 2048
  完成独立诊断（1/1 call、557 tokens、`finish_reason=tool_calls`、1 ToolCall、reasoning 372 chunks、tool 15
  chunks）。RQ-174 的 G53-6 正式领域采用门两次均首案停止（旧 512 上限为 `provider_response_invalid/incomplete_chat_response`；
  修正 1024 上限并补传 `top_p` 后为 `provider_timeout/timeout`），两份结果均 `admitted=false`、
  `production_admitted=false`；不宣称模型一般质量或生产成熟度。
- RQ-175 先新增了 G53-7 evaluation-only Flash runtime profile；随后 RQ-176 已把这份 profile 晋级为当前产品
  目标路径：Agent/工具 90 秒、传输 120 秒、2048 输出上限、`temperature=1`、`top_p=0.95`，并贯通 Agent
  编译、AgentLoop、`llm.chat`、预算包装器、Provider、Worker、Runtime policy 与 Trace identity；GLM-5.2 仅保留
  为显式兼容/应急回退。旧 Dataset 的 30 秒仍是质量资源阈值，不是新档案执行截止；真实 G53-7 会拒绝 dirty
  worktree，须先有新实现 exact-SHA 公共 CI，并在新 SHA 上重新取得 G53-3 协议证据。该批本地聚焦回归
  `159 passed, 27 subtests passed`，相关回归 `586 passed, 50 subtests passed`，未执行真实 API。
- 唯一下一步：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`。RQ-211 已在 exact-SHA 公共绿灯的 `c31127b3c780fe4c493966d8b60f942d3b773fd4` 干净快照上执行一次且仅一次普通智谱 `glm-5.3-flash` 请求；回执为 `not_pending`，表示有限观察窗内没有形成待取消读取，因此没有执行 cancel，也不能宣称 provider close/wakeup 已通过。回执 `908` bytes、SHA-256 `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`，只含允许列表状态；迭代器、外层 SDK stream wrapper 和组合关闭投影均为 `closed`。候选保持 activation gate `disabled`、`activation_state=candidate`、`execution_allowed=false`、`capabilities.streaming=False` 且未注册；严格 Flash v1 仍 2048/零额外调用，默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变。下一步等待用户决定是否设计一个能稳定制造 pending-read 的新协议；不自动追加真实请求、G53-7、黄金切片或生产准入。
- RQ-205 已覆盖前述公共 CI 待办：`90242822df0e47304700644572bc12f0a3aa88ad` / Actions `33598541029` 三 job exact-SHA 全绿，公共 pytest `2218 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面 `201 passed, 1 warning`，fake/local 协议演练通过。当前下一精确项为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`，不自动发真实 recovery。
- RQ-206 已覆盖上述历史指针：同一干净隔离工作树的诊断提交 `0b2342c240cfdc1801e673e830c9a7f30bed3fbd` / Actions `33603143606` exact-SHA 三 job 全绿；按一次性授权只发出 1 次 `zhipu/glm-5.3-flash` primary。流观察到 reasoning、可见正文、`stop` 与 EOF，但 Usage 缺失、close 失败，90 秒 attempt 门在晚到事件中触发，回执为 `fail_closed / elapsed_limit`，没有第二次 recovery。当前唯一下一精确项为 `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，先离线设计/测试硬墙钟取消与 Usage/终态尾帧处理，不自动重测。
- RQ-210 最新状态：隔离分支实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 已完成本地与 exact-SHA 公共 CI（Actions `33657368435` 三 job 全绿）；候选 adapter/deadline/v2/real 聚焦共 `73 passed`，扩展相邻回归共 `182 passed, 27 subtests passed`，compileall、diff check、governance 通过。报告字段只反映 session 所拥有的迭代器和外层 SDK stream wrapper，`shared_resource` 仅说明对象别名；不外推底层 HTTP response、非阻塞 close 或唤醒能力。RQ-209 回执不重写，候选/产品边界不变；当前等待新的明确一次性授权。
- RQ-179–RQ-181 的 exact-SHA、G53-7 失败与一次性正文零留存诊断证据均保持不可变，旧证据不覆盖；RQ-182 聚焦离线测试为 `41 passed`，RQ-183 聚焦离线合同为 `30 passed`，均未改变 Provider-neutral 消息、AgentLoop、ToolRuntime、Trace、预算、默认模型、Portal、Account、Workbench、Auth、路由或 `production_media=0`。
- 2026-08-31 按用户确认新建普通 API Key 后重开 G53-3：进程预检确认 `zhipu`、普通 API 端点与
  `glm-5.3-flash` 均生效；未输出 Key 值，也未改除用户自行更新的 `.env` 之外的默认配置。A1 结构化合同
  与 A2 Agent 工具往返均通过，严格消耗 `3/3` 次调用，`admitted=true`。脱敏结果
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json`（SHA-256
  `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`）通过 schema 校验；未保存正文、
  reasoning、Key 或完整请求标识。G53-3 现标记 `completed-public`，不自动启动 G53-4。
- 2026-08-31 按用户“继续”完成 RQ-184 候选合同公共证据链：实现 A=`e25c3579e8c37724b76505ad028e066a7e28e654` 的
  Actions run `33405110692` 三 job 全绿；同一 A 干净 checkout 的 G53-3 严格 `3/3` 次调用中 A1 `1/1`、A2 `2/2`
  通过，`admitted=true`、SDK retries 为 `0`。脱敏结果
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`
  的 `code_sha` 为 A；只新增该结果的直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0`，其 Actions run
  `33405881172` 三 job 全绿。A/B 无 I/O 身份预检通过，结果文件 canonical-LF SHA-256 为
  `275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`；未保存 Prompt、正文、reasoning、工具参数、
  Key 或 request ID。该证据不激活候选、不发 fresh-recovery、不执行 G53-7，也不改变严格 Flash v1、默认模型、
  AgentLoop、RuntimeTrace、Portal、Account、Workbench、Auth、路由或 `production_media=0`。
- 2026-08-31 按 RQ-176 用户明确决定以普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品运行时目标，
  不再把 Pro/Flash 比较当作前置决策；GLM-5.2 只保留为显式兼容/应急回退。`ModelRuntimeProfile` 已从
  产品组合根贯通 Worker、Runtime、Agent/工具/Harness、Provider、Runtime policy 与 Trace identity；
  `.env.example` 与 Compose 模板已切到 Flash，Flash Worker 的 lease/heartbeat 默认值为 360/60 秒。
  本批没有修改 Portal、Account、Workbench、Auth、路由或 `production_media=0`；工作树仍保留用户已有 dirty 状态。
- 2026-08-31 按 RQ-177 完成同一实现 SHA 的 G53-3 重取：先将协议探针的结构化请求和 Agent 工具回合接入已登记的
  Flash 运行档案（2048 输出、90 秒执行窗、120 秒传输、固定 sampling），再在干净实现提交
  `f0d5ee270f9dac8137368239b85471eca3edf570` 上严格执行 `3/3` 次真实调用。A1 `1/1`、A2 `2/2` 均通过，
  `admitted=true`、总计 `1400` tokens；实现 CI run `33372880364` 与独立证据提交
  `407ee7559c46a84e82f81d5f43f435ad89013949` 的 CI run `33373561017` 均三 job 成功。新脱敏证据
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_f0d5ee2.json` 的 canonical-LF
  SHA-256 为 `1fda5b03d74514fe59c835e5783ff66bb4f16355f32c2adcf82a069bcf70984c`；Windows 工作树 CRLF 原始
  字节摘要为 `6c6e552a1047942b2afce18a01d8adaa86e444615decaeba258e2abe18ae80ea`。旧协议/领域结果未覆盖，未保存 Key、
  Prompt、响应正文、reasoning 或原始请求标识。下一项是 G53-7 A/B 证据身份绑定预检，不直接运行领域门。
- 2026-08-31 按 RQ-178 完成 G53-7 A/B 身份绑定的离线实现与验证：`GLM53ABIdentityBinding` 要求实现提交 A、
  实现公共 CI 和协议 `code_sha` 三者一致，证据提交 B 必须是 A 的直接子提交且只新增声明的 capability-result
  文件，B 另有独立公共 CI 见证；预检从 B 的 Git blob 读取协议结果并核对工作树内容、canonical LF 摘要、当前
  `HEAD=B`、路径白名单与脱敏三调用合同。历史 schema 1.0 结果仍按旧摘要读取，新的 schema 1.1 admission 才携带
  绑定；相关离线测试 `53 passed`（身份绑定文件 `18 passed`），无领域 API/Key I/O。当前实现尚未冻结为新的 A′，下一项先取得 A′ exact-SHA CI
  并在 A′ 重取 G53-3、只新增证据 B′，不直接运行 G53-7。
- 2026-08-31 按 RQ-179 完成最终实现 A 的冻结与公共验证：首个候选 `fe7d577cbfb48a377dc0bf939985eb6a42eb71c7`
  暴露历史测试把旧 B 当当前 HEAD 的生命周期问题；后继 `3ccd8277952b773aab7b7f7432baec54727136b0` 修复测试隔离后，
  公共 shallow checkout 又暴露缺少 A→B Git 历史。两次失败 run `33377864183`/`33378168043` 均保留且不冒充成功。
  最终 A=`9e6d78be51c3a5c512b67f83d2849f9b1261cf77` 让三项 CI checkout 读取完整 Git 历史；run
  `33378687984` 的三 job 全绿且 `head_sha` 精确匹配。局部回归仍为 `53 passed`，治理与差异检查通过；没有读取
  Key、没有模型/领域 API 调用，也没有修改 Portal、Account、Workbench、Auth、路由或 `production_media=0`。
  下一项是从干净 A checkout 重取 G53-3 并生成唯一新结果；本条不授权直接进入 G53-7。
- 当前子阶段组：`5P-1-product-contract-compiler` 已由提交
  `57bd36adcd289b7cc51c1c430e04398daf0683f3` 与 Actions run `31987501935` 完成 exact-SHA
  公共验证；严格产品 DTO、Catalog-backed typed selection、服务器 run ID、Artifact binding 与
  Manifest-derived Runtime policy 已闭环。唯一下一检查点为
  `5P-2-prompt-program-runtime-composition` 已由提交
  `0a9651f4e305616626c58ea28e2c300a491f2a3b` 与 Actions run `31988837293` 完成 exact-SHA
  公共验证；Prompt Program V1、drift gate、verified Runtime identity 与 composition root 已闭环。
  用户已按 RQ-043 恢复并完成 `5P-3-domain-application-service`；Summary/Report domain
  services、Application Service、安全错误映射和 secure product execution factory 已由提交
  `4bd5c83b8d588ab9b0e23dbc9e886100fae7c3f5` 与 Actions run `31998739178` 完成 exact-SHA
  公共验证。用户又按 RQ-044 完成 `5P-4-file-backed-run-receipt-query`；immutable receipt/store、
  strict Trace/manifest/final Artifact query 与 Application receipt 接缝已由提交
  `932a863120a4561f58c477a69becbccd2ec9ff45` 和 Actions run `32002994441` 完成 exact-SHA
  公共验证。用户现按 RQ-045 恢复 `5P-5-thin-fastapi-adapter-no-io-vertical-slice`；本轮先以
  红灯合同冻结四个 HTTP 端点，再安装 FastAPI 并实现薄 Adapter，所有测试保持 Fake/fixture
  no-I/O。`app/api/main.py` 与 `tests/test_fastapi_adapter.py` 已本地实现并通过 24 项 API
  聚焦；完整回归为 `884 passed, 1 warning, 110 subtests passed`。提交
  `6d1e5b0af186f523bee35c24c6873578a149b824` 与 Actions run `32005648179` 已完成 exact-SHA
  公共验证，5P-5 正式关闭。用户已按 RQ-046 恢复
  `5P-6-product-slice-evaluation-exit-review`；十项功能要求、分层/NFR、安全/no-I/O 与
  deferred 边界已形成 exit matrix，面向初学者的退出审查已完成。本地结论为
  `close-with-deferred-boundaries`，聚焦 `121 passed, 1 warning`、相邻 `166 passed`、完整
  `884 passed, 1 warning, 110 subtests passed` 与全部本地门禁通过。退出审查提交
  `8c8acc6911209e645cfaee18bd40870f78d8704f` 已由 GitHub Actions run `32010604551` 完成
  exact-SHA 公共验证，5P-6 与整个 5P 正式关闭；canonical 已按 RQ-047 恢复
  `5F-entry-design` 已完成 Pi-only Runtime 采用实验入口设计；提交
  `ce979752808271696b1dfe499317ead66de6aacb` 与 Actions run `32013948784` 已完成 exact-SHA
  公共验证。本轮未安装 Pi、未写 adapter、未读取 Key、未调用真实 Provider；用户现已按 RQ-048
  恢复 `5F-1-pi-source-license-contract-audit`。官方 release/package/license 与低层合同审计
  的裁决为“允许有条件进入 5F-2 隔离 no-I/O spike”；完整回归
  `884 passed, 1 warning, 110 subtests passed` 与两套 RAG/compileall/governance/安全/dry-run/
  diff 门禁通过；提交 `5901b090b4ee8bccfd0a71ddfa412dec98fba02f` 已由 Actions run
  `32016852979` 完成 exact-SHA 公共验证，5F-1 正式关闭。canonical 只交接到
  `5F-2-offline-protocol-adapter-spike` 准备状态；用户现已按 RQ-049 明确恢复 5F-2。本轮先以
  ADR-0035 和实施计划冻结版本化 JSONL sidecar、Scripted StreamFn、单一 Python
  `knowledge.search`、进程/Usage/Trace 安全和 TDD 顺序；exact npm lockfile、官方 Pi 0.84.2
  sidecar、Python controller、真实本地知识 Tool、Usage 四态、安全故障和两项窄 parity 已本地完成。
  聚焦 `35 passed`、相邻 `99 passed`、完整 `919 passed, 1 warning, 110 subtests passed` 与两套
  RAG/compileall/governance/安全/dry-run/diff 门禁通过；本地退出裁决为
  `pass-with-boundaries`；实现提交 `f62f078faca0d93494478011d2fe18cdeb85970f` 与 Actions run
  `32022258177` 已完成 exact-SHA 公共验证，5F-2 正式关闭；状态收尾提交
  `1454f59b0e07d96defedfc093807a8ef03391839` 与 Actions run `32022784855` 也已完成
  exact-SHA 公共验证。用户现已按 RQ-050 明确恢复 5F-3，当前只评估完整合同、安全、
  ReviewHarness 唯一发布权、Trace/Usage/Artifact 语义与跨语言维护成本。评测专用 adapter、
  process-local Tool evidence、per-call Usage/finish reason 和严格 Signal projector 已本地完成；
  Pi 草稿通过现有 Harness/typed output/Artifact，成功路径可组成合法 body-free Trace。45 项聚焦、
  196 项相邻与完整 `929 passed, 1 warning, 110 subtests passed` 通过；Context token-unit/char、
  extended terminal 与 live timing 三项 hard gap 仍存在。本地裁决为
  `harness-compatible-but-runtime-gate-failed`，不准入 5F-4；两套 RAG、compileall、Node
  syntax/tree、Harness/secret/tracked-data、dry-run、governance 与 diff 门禁也已通过，当前只待
  提交/推送与 exact-SHA 公共 CI。实现/退出提交
  `3d9a08159c5a6e08fca74257514975b4c0c6ec68` 已由 Actions run `32025522606` 完成
  exact-SHA 公共验证，5F-3 正式关闭；5F-4 因既定前置硬门失败而未进入，不调用真实模型。
  ADR-0037、exit matrix/review 已裁决 `partial-adopt-evaluation-assets-only`：产品拒绝 Pi，只冻结
  保留可执行评测资产与采用门方法。提交 `f8dea663523bdc76fc8a40741d37f6e66dd25177` 已由 Actions run
  `32028206103` 完成 exact-SHA 公共验证，5F 与整个阶段 5 正式关闭。canonical 只交接到
  `6A-entry-design`。用户已按 RQ-052 恢复该检查点；当前已审计 5P 的同步文件/crash gap、多 worker
  限制和 EchoMind API/Memory 参考实现，并明确 PostgreSQL 是唯一生产语义基线：SQLAlchemy 2 映射、
  Alembic 迁移，普通逻辑可用 Fake/单元测试，但事务、迁移和并发领取必须由真实 PostgreSQL Docker/CI
  验证，SQLite 绿灯不能替代。用户随后选择同仓库、同部署的独立 PostgreSQL polling worker：API
  持久化 queued task 并快速返回，Worker 通过 PostgreSQL 事务原子领取；不引入 Redis/Celery/Kafka。
  架构与数据流章节已获用户确认：采用模块化单体、API/Worker 分工、短事务以及 SQL 控制面与
  Artifact/Trace 数据面分离。task_id/run_id 双身份、任务控制字段、四态状态机和不可逆终态规则
  也已获确认。SQL/Artifact 分工、创建/claim/终态短事务、幂等与 ownership 核心也已获确认；但在
  失败边界复核中发现：多 Worker 下不能仅凭新 Worker 启动就把其他无 receipt 的 running task 自动
  判死。用户已选择保守方案 A：有匹配 immutable receipt 时自动补齐成功；正常关闭由 owner Worker
  安全失败；无终态证据的硬崩溃任务只标记 recovery-required，待受限人工确认后条件更新为失败。
  其余失败语义与 HTTP 投影也已获确认：POST 202 只表示可靠入队，任务执行成功与 Harness 发布
  状态分离，not-found/ownership、幂等冲突、DB 不可用、报告未就绪和完整性失败具有不同安全语义。
  作品集规模 NFR 也已获确认：单服务器起步、默认单并发 Worker、真实 PostgreSQL 多 Worker 正确性、
  有限 owner/global 背压、API/claim 延迟目标、退避轮询、分层健康检查以及不冒充 99.9%/容灾。
  安全与数据生命周期章节也已获确认：owner_id 来自可信 ActorContext，查询 owner-scoped，开发固定
  owner 不冒充公网鉴权；CORS/密钥/日志 fail-closed，数据按 7/90/30 天分层保留，terminal task 可删除，
  active task 删除不冒充 cancel。分层测试矩阵也已获确认：纯逻辑/Fake、真实 PostgreSQL migration/
  repository/concurrency、API/Worker、离线产品纵向、安全/生命周期与性能层各自有职责，PostgreSQL CI
  是阻塞门且外部 Provider/Riot 调用为 0。七个 6A 原子实施批次也已获用户确认。ADR-0038、正式设计
  与实施计划现已创建。本地完整回归 `929 passed, 1 warning, 110 subtests passed`、两套 RAG、
  compileall、Harness dry-run、governance、Secret/run-data 与 SDK boundary 均通过；设计提交
  `c0b5af0eec1654c35afddb3c8a66b774a233a688` 已由 Actions run `32041343696` 完成 exact-SHA 公共
  验证。`6A-entry-design` 正式关闭；用户已按 RQ-053 授权
  `6A-1-postgresql-foundation`，当前只实施 PostgreSQL 基础设施、初始 schema/migration 与真库 CI
  门，不实现 Repository、Worker 或 API 行为。本机未安装 Docker，故本地真库测试必须明确 skip，
  真实 PostgreSQL 阻塞证据由 GitHub Actions service 提供。当前本地已实现严格配置、惰性 Engine/
  Session factory、task ORM metadata、可逆 initial migration、PostgreSQL Compose 与独立 CI job；
  6A-2 又已本地实现 task contract、fingerprint、Fake service 与 PostgreSQL create/query Repository；
  聚焦为 `29 passed`，完整回归为 `977 passed, 8 skipped, 1 warning, 110 subtests passed`，两套 RAG、
  compileall、Harness dry-run、governance、Secret/run-data、SDK boundary 与 YAML checks 均通过。
  三个本地 skip 全部已由提交 `854e52d7d3f4efeb3bd94137b66013352d10c8a2` 的 GitHub Actions run
  `32043214500` 在真实 PostgreSQL 17 service 上补齐；`pytest` 与 `postgres-migrations` 两个 job 均
  completed/success，6A-1 正式关闭。用户已按 RQ-054 授权并完成 6A-2；提交
  `012b066da9e5a8ec569d5791cf9ac0fbf4b117d3` 的 Actions run `32046532695` 中 `pytest` 与
  `postgres-migrations` 均 completed/success，真实 PostgreSQL 已验证 5 项 Repository 测试。6A-2
  正式关闭。用户又按 RQ-055 完成 6A-3；提交
  `55e369e9697b91c71fb4638ac9299ad2c5e57a36` 的 Actions run `32097561436` 中 `pytest` 与
  `postgres-migrations` 均 completed/success，真实 PostgreSQL 已验证 deterministic SKIP LOCKED claim、
  双 Worker 不重复、ownership/terminal CAS、短事务与 timestamp invariant。6A-3 正式关闭，只交接
  6A-4 准备状态；不接真实 Application/Artifact 或 API。用户随后按 RQ-056 恢复 6A-4；trusted run_id、
  真实 Recent Review Task Executor、严格 receipt/Trace/final Artifact terminal、receipt-proven
  reconciliation、recovery-required 与人工 recovery CAS 已实现。提交
  `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 的 Actions run `32102522662` 中 `pytest` 与
  `postgres-migrations` 均 completed/success；完整 pytest 为 `1033 passed, 20 skipped, 1 warning,
  110 subtests passed`，真实 PostgreSQL job 执行 6 个数据库测试文件并得 `40 passed`，其中包含本轮
  5 项 reconciliation/产品纵向测试。6A-4 正式关闭，只交接 6A-5 准备状态。上一子阶段组
  5E AgentRuntime V1 已完整闭环：入口设计与 ADR-0029 冻结为“薄 Runtime
  + 可选观察端口 + completeness-aware Usage + 原子最终 Trace”；5E-1 的严格合同、
  Recorder/Usage 与 Trace Store 已由提交 `d891184e1bf82068188d2fb5715769bdaa3da022`
  和 GitHub Actions run `31942483874` 完成 exact-SHA 公开验证。5E-2 的入口源码审计、
  初学者设计与 ADR-0030 已公开完成：采用 run-scoped `ObservedLLMProvider` 覆盖 Agent
  与 Harness 全部 Provider 边界，AgentLoop 只观察业务 Tool/Agent 终态，Harness 只观察
  持久化后的状态/评测/发布，并用两阶段 terminal commit 消除 Trace 写盘终态悖论；Task D
  已形成并公开验证统一同步 `AgentRuntimeV1.run()`，组合两个真实 Skill、真实本地 RAG、共享
  observed Provider、唯一 Harness、typed output、完整 Usage 与安全最终 Trace；当前 5E-3
  已完成入口审计和进程内 worker/有界 queue 方案冻结；stream item、parity、背压、关闭隔离、
  预期失败和终态测试均已在本地通过，并由提交 `80b76a1` / GitHub Actions run `31960987333`
  完成 exact-SHA 公共验证；5E-3 正式闭环。5E-4 的退出矩阵与
  `close-with-deferred-boundaries` 裁决由提交
  `3d3656195a66adfd4595cffa145c978d24c33628` / GitHub Actions run `31962252231`
  完成 exact-SHA 公共验证，因此 5E-4 与整个 5E 正式完成；这不表示生产就绪。
  Task A 的合同 1.1、合法 1.0
  读取、默认关闭 observation port、missing Usage fail-closed、Harness lifecycle 与
  prospective terminal 已完成并由提交 `2e78c9606fe93b56657d4bb13c8efe0f1eed98fe`、
  GitHub Actions run `31947625293` 完成 exact-SHA 公共验证；聚焦回归为
  `131 passed, 44 subtests passed`，完整回归为 `691 passed, 110 subtests passed`，
  两套 RAG、compileall、安全边界、Harness
  dry-run、治理与差异检查通过。Task B 已完成 TDD：run-scoped
  `ObservedLLMProvider` 在统一 capability preflight 后记录连续 Provider ordinal、phase、
  Usage、有限 finish reason 与 allowlisted error detail；`AgentLoop.run()` 增加 keyword-only
  默认关闭 observer，在整批预检后记录业务 Tool 安全 envelope，并让每个返回结果恰好形成
  一个 Agent terminal。Provider/Tool started 或 completed 观察失败均 fail-fast，且
  `ToolRuntime` 不再把 `RuntimeObservationError` 计入 retry、breaker 或 fallback；
  `observer=None` 与旧行为逐字段一致。聚焦回归为 `81 passed`，完整回归为
  `721 passed, 110 subtests passed`；本地两套 RAG、compileall、安全边界、Harness dry-run、
  治理和差异检查通过。实现提交 `28bd910525a7522be16bd69b6e945846839a4cd8` 已推送，
  GitHub Actions run `31952026988` 对 exact SHA 的全部公开门禁成功；Task B 正式闭环。
  Task C 已完成本地实现、完整门禁和 exact-SHA 公共 CI（提交 `8b69c9b`、Actions
  `31957712118`）。Task D 新增 18 项统一 Runtime 纵向测试，完整本地回归为
  `747 passed, 110 subtests passed`；两套 RAG、compileall、安全边界、Harness dry-run、
  治理和差异检查均通过，本批 Provider/Key/held-out I/O 为 0。实现提交 `d49508e` 已由
  GitHub Actions run `31959646589` 完成 exact-SHA 公共验证，5E-2 正式闭环；随后 5E-3
  已由 `80b76a1` / Actions `31960987333` 完成 stream parity 与公开验证，5E-4 已由
  `3d36561` / Actions `31962252231` 完成退出审查公共验证。
  设计提交
  `3c6f26a4802821548be8d61085552f5b9a790468` 已通过 GitHub Actions run
  `31944389807` 的 exact-SHA 公共验证。5D Python 受限 Agent Loop
  已通过退出审查；以下保留其 entry design、5D-1 至 5D-7 的公开证据链：
  5D-7 Batch A-C 与 Batch D 的 D1-D5 已完成，DeepSeek V4 Pro Adapter 真实
  structured/tool 协议 3/3 calls 已准入；三场领域 held-out 的控制面以及独立输入计划、
  oracle-blind 生产 Executor 和真实门 CLI 已完成离线 TDD，并由提交
  `eb198354b3186f25b7d0455d7ed28725bc17e234`、GitHub Actions run `31799394506`
  完成 exact-SHA 公开验证；真实 DeepSeek 领域 held-out 已执行一次并在首个正常案例因
  `unsupported_parallel_tool_calls` 不准入，后两例按首错停止跳过；不可变结果归档提交
  `26b668d0ce594e648a692cd2caf831c86125fede` 已通过 Actions run `31810164628`；ADR-0022
  的多 ToolCall 批次离线 TDD 已由提交 `037a47fecf058b2430efeeb59858e24cdb3b28eb` 完成，
  Actions run `31817798170` 对精确 SHA 已成功；ADR-0024 已完成新鲜领域采用门的
  零调用设计，决定复用现有控制面并重新冻结 fixture/Dataset/plan/Context 身份；设计
  提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已通过 Actions run `31859717836`；
  Fresh-Gate 1 已完成本地离线 TDD，旧 V1.0 资产兼容、V1.1 input plan、三案例
  Prompt/Context commitment、历史 `3+1` 调用证据链与 development-only no-I/O
  admission 已实现；提交 `adba965a7f7fb4293020502b4440e9880633e571` 已通过 GitHub
  Actions run `31860874440` 的 exact-SHA 公开 CI；Fresh-Gate 3 已在本地创建全新匿名
  3 局 fixture/确定性报告、正式三案例 held-out、V1.1 input plan 与三个实际案例的
  body-free Prompt/Context snapshot；新旧 fixture/题目/marker/ID 均不复用，交叉身份和
  fixture 数字自洽由离线测试固定；资产提交
  `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已通过 GitHub Actions run
  `31861960565` 的 exact-SHA 公开 CI；Fresh-Gate 4 入口批已完成
  本地 TDD：新 readmission 同时绑定历史 `3+1` 调用证据、
  ADR-0022 修复 CI、Fresh-Gate 3 资产 CI、当前 code/public-CI、新 Dataset/plan/fixture 与
  三案例 Context；现有生产 CLI 已切换到 V2 profile 并增加 prepare-only，Fake Provider
  纵向装配与首错停止通过，本地完整回归为 `580 passed, 103 subtests passed`；实现提交
  `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过 GitHub Actions run `31863341338`，
  同一干净 SHA 的真实 `--prepare-only` 输出 no-I/O admitted、external calls 0、held-out
  未执行；用户随后明确确认，V2 真实门在公开成功提交
  `741e84140f816fb4b06b2812a8d07d3f32eaf4d0` 上只执行一次：首例第一次响应成功
  规范化并使用 3241 input + 199 output tokens，下一调用因 `3440 + 1024 > 4000`
  在 I/O 前以 `token_budget_exhausted` 停止；Harness 降级、后两例 skipped、unsafe
  publication 为 false，最终 `admitted=false`。不可变结果 SHA-256 为
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`；归档提交
  `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 已通过 GitHub Actions run
  `31864370988` 的 exact-SHA 公开 CI；ADR-0025 与 V2 预算可达性离线裁决现已本地完成：
  精确证据证明第二次调用至少要求 4464-token 单例上限，当前 4000 必然不可达；真实
  本地生产路径的三阶段 envelope 长度为 6666/7774/6266，校准 input 投影为
  3241/3780/3047，但明确不是 Provider tokenizer 精确值；完整回归为
  `587 passed, 103 subtests passed`，两套 RAG 与全部本地门禁通过，本批外部调用为 0；
  裁决提交 `78400b9310e512668c81ca41cd65623a92a27226` 已通过 GitHub Actions run
  `31865285994` 的 exact-SHA 公开 CI；ADR-0026 又完成 V3 资源校准设计：正常三调用和
  可选第四次 Evaluation repair 已按真实生产控制流区分；后续只用两个公开 development
  profile 形成四阶段请求，再以最多 8-call、校准输出 64、零重试、首错停止的独立 Usage
  replay 观测资源；V3 单例预算将按逐阶段最大真实 input、25% 工程余量和四次 1024
  output ceiling 推导，若含既有协议成本后超过 `$0.10` 则停止而不创建 held-out；本设计
  Provider/Key/网络调用为 0；本地完整回归为 `587 passed, 103 subtests passed`，两套
  RAG、compileall、Harness/secret/tracked-data、dry-run、治理和 diff check 均通过；
  设计提交 `351c0e64adf9d2ace42c557d40fac81a44ab539e` 已通过 GitHub Actions run
  `31866084382` 的 exact-SHA 公开 CI；V3 资源校准离线实现现已本地完成：两个全新
  development profile 经真实 production Executor 形成精确 8 个四阶段请求，ceiling
  初始/工具后 envelope 为 12206/15279 本地单位且未超过 Skill 16000 ceiling；body-free
  请求快照、安全 Fake 结果、8-call/64-output/64000-token/`$0.10` 账本、首错停止、
  Decimal 预算推导和 no-I/O admission 已由 11 个新增测试固定；本批 Provider/Key/
  网络调用和 V3 held-out 均为 0；本地完整回归为 `598 passed, 103 subtests passed`，
  两套 RAG、compileall、Harness dry-run、SDK/tracked-data、治理与 diff 门禁均通过；实现
  提交 `2d676966915a7967b946880040b59c022283e683` 已通过 GitHub Actions run
  `31867655627` 的 exact-SHA 公开 CI，离线校准基础设施至此公开冻结；用户现已明确确认
  一次真实 8-call development Usage replay；真实运行入口提交
  `6aa8c439a29adafebf1ffe1bb0eef0c1b921ca44` 已通过 Actions run `31868747216`，同一
  干净 SHA 的 prepare-only 为零调用；正式 replay 随后只发送第 1 个 baseline 请求，因
  未形成规范化 `ChatResponse` 以 `provider_response_invalid` 首错停止，后 7 个请求未
  发送。不可变结果 SHA-256 为 `ba33e75af7f8755dc89904fb346f66962fb29e92d08173494053f17ad8e7088b`：
  1 external call、0 normalized responses；账本 0 tokens/`$0` 只代表未取得可结算 Usage，
  实际计费 Token/费用均为 unknown。零调用裁决明确禁止预算推导、补跑和 V3 held-out，
  模型质量仍为 unknown；裁决 SHA 为 `0ce09b52d982f8c03052f1d94fde1da5628af31dbd797ea770522ce092907446`。
  结果/裁决聚焦回归 34/34、完整回归 `611 passed, 103 subtests passed`，两套 RAG、
  compileall、Harness SDK/tracked-data boundary、dry-run、治理和 diff check 已在本地通过；
  归档提交 `421a24393cafdc79a02de4091f569cfb9aa5b721` 已通过 GitHub Actions run
  `31869409106` 的 exact-SHA 公共 CI；ADR-0027 现已零调用裁决关闭当前 DeepSeek V3
  资源校准与领域采用尝试，保留低层协议准入但领域/产品质量继续 unknown；未来真实
  Provider 门必须先离线保留允许列表约束的安全细分错误 provenance；本决策已通过
  51 项聚焦、完整 `611 passed, 103 subtests passed`、两套 RAG 与全部本地门禁，
  本批 Key/Provider/external calls 为 0；决策提交
  `ea91e9697c820c0850db488a93263fc169719515` 已通过 GitHub Actions run
  `31872476103` 的 exact-SHA 公共 CI；随后已在零 I/O 下实现 ADR-0027 要求的安全
  `provider_error_code` 白名单传递和旧结果兼容合同，聚焦回归 89 passed；完整回归为
  `616 passed, 103 subtests passed`，两套 RAG 与全部本地门禁通过；实现提交
  `0ad4f9766ab98455ce0726d18d5f5d1f02391c6a` 已通过 GitHub Actions run
  `31874240935` 的 exact-SHA 公共 CI；ADR-0028 与 5D-7 收尾审查现已区分“评测门完成”
  和“领域模型采用未准入”，接受 5D-7 完成并把 G53 保持为非阻塞 deferred 候选；
  审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 已通过 GitHub Actions run
  `31876536179` 的 exact-SHA 公共 CI；5D 退出审查提交
  `2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已通过 GitHub Actions run
  `31877076222` 的 exact-SHA 公共 CI；5E 入口设计提交
  `c91c2d75f85e1315e65e9768894982556053a7b0` 已通过 GitHub Actions run
  `31878052835` 的 exact-SHA 公共 CI；5E-1 实现提交
  `d891184e1bf82068188d2fb5715769bdaa3da022` 已通过 GitHub Actions run
  `31942483874` 的 exact-SHA 公共 CI
- 历史唯一下一步（已由 RQ-163 交接取代）：`8e-productization / portal-motion-polish / official-wallpaper-fallback / region-catalog-expansion`，当时为
  `authorized / in_progress`。Wan 3.0 official first-frame reopen 因 endpoint 误填 OpenAI-compatible
  `/compatible-mode/v1` 返回 HTTP 404，状态无 task_id/结果，不构成模型质量证据；用户已明确“转战”，不再继续寻找
  Wan Host 或发送第二次 POST。用户提供的 `animated-demacia.webm` 已完成候选审计：1920×1080、15.04s、25fps、
  VP8 WebM、无音轨，持续运动可见但首尾非无缝，来源/公开再分发许可仍待核验。随后在桌面 `RIFTCOACH` 素材中发现并核对
  `animated-bandlecity.webm`：1920×1080、15.04s、25fps、VP8+Opus，已生成无音频 H.264 sibling 与 poster，
  仍标为 `research-candidate`、rights unverified；审计 JSON 为
  `docs/assets/8e-portal/portal-region-wallpaper-candidate-bandle-city-v1.json`。`?surface=wallpaper-lab` 的
  no-I/O 本地研究预览已实现：包含 Universe 13 地区 crest 选择卡、Demacia/Bandle City 动态候选、动态视频/静态 poster
  降级、键盘激活和独立入口转场；Bandle 静态 JPEG 的 imagegen 修复候选因纹理/质感不达标已 rejected。两地区 Entry Panel
  试水又已完成：ready 选区即时切换背景，Enter 以 typed `region` 进入 Account，Account Back/Continue 保留该参数。
  它尚未改变默认 `/`，也没有把任何壁纸提交进公开 runtime。下一动作是审阅该两地区纵向切片，再决定扩展第三地区或先做
  Account/Portal 视觉联调；逐地区来源/许可、格式/体积、浏览器/移动端/reduced-motion 与 loop 门仍必须全部通过后，
  才能接入默认 Portal，`production_media` 保持 `0`。Ixtal
   已补充 5000×2811 静态 splash 作为动态首帧；对应 Account 原创静态概念仍为 research-only。Ixtal 动态候选审计见
   `docs/assets/8e-portal/portal-ixtal-wallpaper-candidate-seedance25-v1.md`，下一动作仍是补齐地区候选与播放降级门，
   再在真实 Portal/Account 布局中回看并决定保留、调优或替换。
  8D、Batch B/C/D、Live Workbench、Batch E E1–E5、production shell/Auth gate、Timeline、bilingual/product-journey
  foundation 与 RQ-108 runtime Task 1–4 的公共证据保持不变；GLM-5.3/Flash、Coach、RQ-103 与 8F 仍留后序。

  2026-08-29 Portal/Account UI hygiene 已在同一 RQ-154/RQ-156 slice 本地完成：新的地区链接由
  `productJourneyUrl` 统一生成 `?surface=wallpaper-lab&region=...`，旧 `?region=...` 仅作兼容
  presentation alias；Account `from=wallpaper-lab`、push/popstate scroll reset 与 generation-bound
  activation 覆盖 copy/reload/back，且未知 query fail-closed。Portal/Auth/Atlas 使用 semantic main、
  labelled headings、skip focus、pressed/current/disabled 状态；Portal 与 CinematicSceneMedia 的
  poster/video/crest/detail 节点补 intrinsic dimensions，保留 WebM→MP4→poster、mobile/reduced-motion/
  playback-error fallback。地区选择在同一 Portal history entry 以 `replaceState` 同步显式 URL，浏览器
  Back 不会把已选地区静默还原为默认值。最终定向 unit `56 passed`、完整前端 unit `280 passed`、研究预览 E2E `11 passed`；
  1000–1199px 短桌面使用三列卡片，1200px+ 才使用四列；<=420px 手机使用单列；长页面的媒体/遮罩/转场层固定在视口，避免移动端背景随内容高度裁切或滚动漂移；
  typecheck/build、Axe serious/critical、governance 与 diff 门均已通过；媒体审计仍为 `checked_renditions=0/status=planned`。
  该 hardening 不触碰 Workbench、默认 `/` 或 `production_media=0`，不等于 8E 完成或最终视觉签收。
- 范围约束：5P-5 只增加本地同步 HTTP Adapter 与 no-I/O 纵向测试，没有实现真实 Riot/Provider、
  SQL/Session/Memory/SSE/恢复、公网部署或进入 5F；
  DeepSeek V2 结果不得覆盖或重跑，不能把安全降级解释为模型质量通过，也不能用低层
  协议、候选选择或发布热度替代领域质量证据

## 5C 原始子阶段账本

| 子阶段 | 原定职责 | 当前状态 | 已有证据 | 尚欠什么 |
|---|---|---|---|---|
| 5C-1 Router Contract | 定义 `RouterRequest`、`RouterDecision`、状态和原因码 | 已完成 | 契约代码和模型测试 | 进入维护 |
| 5C-2 Skill Catalog | 发现、严格加载并投影可用 Skill | 已完成 | Catalog 代码和测试 | 进入维护 |
| 5C-3 Deterministic Router | 依据机器可读触发信号做可解释选择 | 已完成 | 确定性 Router、Manifest 信号、单元测试 | 进入维护 |
| 5C-4 Rejection / Ambiguity | 不支持时拒绝；多候选时不得擅自猜测 | 已完成 | 教学验收文档、排除合同不变量、候选顺序与域外硬负例测试 | 进入维护 |
| 5C-5 Router Evaluation | 建立正例、负例、歧义、越界和误路由评测 | 已完成 | development v2 为 23/23；independent holdout v1 单次运行后为 11/12，唯一失败已原样保存并分类 | 进入维护；holdout v1 永不用于调节当前规则 |
| 5C-6 Model Fallback Decision | 仅在确定性路由出现真实 Bad Case 后评估模型兜底 | 已完成 | ADR-0010 比较排除词、LoL 域信号、澄清、LLM 与 Embedding；决定 V1 暂缓模型兜底并定义重新采用门槛 | 进入维护；新鲜数据满足门槛后才能用新 ADR 重开 |

## 5D 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成证据 |
|---|---|---|---|
| 5D-entry-design | 审计现有接缝、比较组合方案、冻结数据流与教学顺序 | 已完成 | 5D 设计文档、ADR-0011、治理检查 |
| 5D-1 Skill Run Boundary Hardening | 统一 I/O 非空文本、selected identity、run_id 和输入 Artifact 绑定 | 已完成 | 设计/TDD 文档、`SkillExecutionBoundary`、共享 run ID/Artifact 编码、合同与篡改测试 |
| 5D-2 Context Builder V1 | 两个 Skill 的最小上下文、信任标签、确定性裁剪和 ContextSizer | 已完成 | 设计/TDD 文档、`ContextBuilderV1`、两个 Skill allowlist、citation/注入/预算边界测试 |
| 5D-3 Skill Run Compiler & Budget Enforcement | Manifest 权限/预算编译为 AgentRunRequest，并约束累积上下文 | 已完成 | 设计/TDD 文档、`AgentRunCompiler`、完整消息估算、逐轮 Context 门禁与协作式总 deadline 测试 |
| 5D-4 Evidence-Aware Agent Draft Preparation | AgentLoop + knowledge.search 生成 draft 与 KnowledgeEvidence | 已完成 | 共享 evidence converter、`SkillAgentDraftPreparer`、两个真实 Skill + Fake Provider + 真实 `knowledge.search`，成功/拒答/去重/冲突/失败与停止边界测试 |
| 5D-5 Harness Composition & Typed Terminal Output | 通过 DraftPreparationStep 接入单一发布门禁 | 已完成 | 统一 preparation 合同、旧顺序 Adapter、`SkillReviewExecutor`、Artifact 驱动 typed output、两个真实 Skill 的 Fake Provider + 真实 RAG + Harness 端到端测试 |
| 5D-6a Structured Output Contract | Provider-neutral schema、Pydantic 校验和有限修复 | 已完成 | `StructuredResponseContract`、能力门禁、严格 Evaluation Pydantic 模型、一次 repair、fail-closed 与 Harness 降级测试 |
| 5D-6b Real Provider Capability Gate | 实测首个 Provider，并为第二 Provider 决策提供真实证据 | 已完成（部分采用） | P1-P5 5/5、真实 Adapter 协议 3/3 calls 通过；真实 recent-form 领域运行只执行一次并在 1 个领域 call 后未形成统一 `ChatResponse`，无工具/证据/Evaluation，领域 `admitted=false`，Harness 安全降级；ADR-0012 准入最小协议、拒绝领域能力并暂缓第二 Provider |
| 5D-7 Prompt/Context & Domain E2E Evaluation | 工具选择、事实/引用、注入、质量/成本/延迟评测 | 已完成（当前无领域 Provider 准入） | 分层评测、Prompt/Context 身份、Evaluation 1.1、held-out 生命周期、资源/错误合同和真实负面结果均已审查；ADR-0028 接受评测门完成，同时保留 GLM/DeepSeek 领域质量 unknown、G53 deferred 与 Flash 未测试边界 |
| 5D-exit-review | 对照全部证据和 5E 前置项 | 已完成 | 十项功能要求与 NFR 均满足 5D V1；无领域 Provider 准入的限制保留；未提前实现 5E |

## 5E 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/验收证据 |
|---|---|---|---|
| 5E-entry-design | 审计分散信号、比较组合方案、冻结 Runtime 边界与 NFR | 已完成 | 初学者设计、ADR-0029、四批实施顺序；616 tests/103 subtests、两套 RAG 和全部本地门禁；`c91c2d7` / Actions `31878052835` 公开通过；无产品代码或 Provider I/O |
| 5E-1 Runtime Contract、Usage 与 Trace Store | 严格合同、Recorder、未知 Usage 与原子最终 Trace | 已完成 | 39 项聚焦、166 tests/55 subtests 相邻、655 tests/103 subtests 全量回归和全部门禁；`d891184` / Actions `31942483874` exact-SHA 公开通过；无 Provider I/O |
| 5E-2 Observable `run()` Vertical Slice | observer 接缝与两个 Skill 的统一同步执行/Trace | 已完成 | Task D 实现提交 `d49508e` / Actions `31959646589` exact-SHA 公共 CI 成功；新增 18 项测试，完整回归 `747 passed, 110 subtests passed`，两套 RAG/compileall/安全/dry-run/治理/diff 门禁通过；本批无 Key/真实 Provider/held-out I/O |
| 5E-3 Live `stream()` & Parity | 同一执行核心的进程内实时事件和 run/stream 同终态 | 已完成 | 提交 `80b76a1` / Actions `31960987333` exact-SHA 公共 CI 成功；stream 聚焦 15 项、完整回归 `762 passed, 110 subtests passed`，两套 RAG/compileall/治理/安全/dry-run/diff 门禁通过；无 Key/真实 Provider/held-out I/O |
| 5E-4 Runtime Evaluation & Exit Review | 安全、失败、资源、纵向评测与 5E 退出审查 | 已完成 | exit matrix、Runtime 聚焦 `128 passed`、完整 `762 passed, 110 subtests passed` 和全部本地门禁通过；`3d36561` / Actions `31962252231` exact-SHA 公共验证成功；决策为 `close-with-deferred-boundaries` |

## 5P 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/验收证据 |
|---|---|---|---|
| 5P-entry-design | 同时设计 Prompt Program V1 与早期产品切片，冻结范围/NFR/顺序 | 已完成 | 设计文档、ADR-0032/0033；本地 762 tests/110 subtests、两套 RAG 与全部门禁；`49841ec` / Actions `31985199623` exact-SHA 公共成功；无产品代码/外部 I/O |
| 5P-1 Product Request & Typed Skill/Runtime Compiler | 严格产品 DTO、trusted typed selection、Artifact binding、Manifest-derived policy | 已完成 | `57bd36a` / Actions `31987501935` exact-SHA 公共成功；796 tests/110 subtests；无外部 I/O |
| 5P-2 Prompt Program V1 & Runtime Composition Root | Program manifest/catalog/drift gate 与 secure production composition | 已完成 | `0a9651f` / Actions `31988837293` exact-SHA 公共成功；完整回归 `805 passed, 110 subtests passed`；无外部 I/O |
| 5P-3 Domain Pipeline Promotion & Application Service | 提升 Summary/Report 服务并组合产品用例/安全错误 | 已完成 | `4bd5c83` / Actions `31998739178` exact-SHA 公共成功；完整 `830 passed, 110 subtests passed`；无外部 I/O |
| 5P-4 File-backed Run Receipt & Query Projection | body-free receipt、Trace/manifest/report 安全复读 | 已完成 | `932a863` / Actions `32002994441` exact-SHA 公共成功；聚焦 50、相邻 179、完整 860 tests/110 subtests |
| 5P-5 Thin FastAPI Adapter & No-I/O Vertical Slice | 最小端点、依赖与 Fake Provider HTTP 纵向测试 | 已完成 | 四个固定端点、显式 Port、strict DTO、错误映射与真实 Runtime/Harness/RAG no-I/O 切片；24 API tests，完整 884 tests/110 subtests；`6d1e5b0` / Actions `32005648179` exact-SHA 公共成功 |
| 5P-6 Product Slice Evaluation & Exit Review | 合同、安全、资源、公开证据与限制退出审查 | 已完成 | 十项功能 exit matrix、初学者 exit review、聚焦 121、相邻 166、完整 884 tests/110 subtests 与全部门禁通过；`8c8acc6` / Actions `32010604551` exact-SHA 公共成功；裁决 `close-with-deferred-boundaries`，外部 I/O 为 0 |

## 5F 原子子阶段账本

| 子阶段 | 职责 | 当前状态 | 完成/下一步证据 |
|---|---|---|---|
| 5F-entry-design | 收缩 Pi-only 候选，冻结同切片对照、合同、安全、跨语言成本和 adopt/partial-adopt/reject 门槛 | 已完成 | ADR-0034 与 `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`；提交 `ce97975` / Actions `32013948784` exact-SHA 公共成功；无 Pi/Key/Provider I/O |
| 5F-1-pi-source-license-contract-audit | 审计官方 Pi 源码/包版本、许可证、Runtime/Provider/Tool/event/state/abort/Usage 接缝 | 已完成 | 冻结 `earendil-works/pi v0.84.2` / `914cf147...`、MIT、Node `>=22.19.0`；完成合同/安全/依赖/sidecar 映射；裁决允许有条件进入 5F-2；`5901b09` / Actions `32016852979` exact-SHA 公共成功；Pi/Key/Provider I/O 为 0 |
| 5F-2-offline-protocol-adapter-spike | 用同一 recent-form Context、Scripted StreamFn 和单一 `knowledge.search` 建立隔离 Python↔Node 协议对照 | 已完成 | exact lock/sidecar/controller、真实本地知识 Tool、35 focused/99 adjacent/完整 919 tests 与本地退出审查；`pass-with-boundaries`；`f62f078` / Actions `32022258177` exact-SHA 公共成功；不代表 Pi adopt |
| 5F-3-contract-security-harness-evaluation | 对比完整 Tool/Context/deadline/structured output/error/terminal 与 ReviewHarness/Trace parity | 已完成 | 45 focused、196 adjacent、完整 929/110 subtests；Harness/成功 Trace 可适配，但 Context/extended terminal/live timing 硬门失败；`3d9a081` / Actions `32025522606` exact-SHA 公共成功 |
| 5F-4-bounded-real-slice | 前置硬门通过且再次授权后，才运行同模型/同 Context/同 Harness 的真实切片 | 未进入（前置门失败） | 5F-3 hard Runtime parity gate failed；真实模型调用不能修复这些合同差异，外部 calls 保持 0 |
| 5F-5-adoption-decision-exit-review | 根据全部证据裁决 adopt/partial-adopt/reject 并关闭 5F | 已完成 | 裁决 `partial-adopt-evaluation-assets-only`；45 focused、929/110 全量与全部本地门禁通过；`f8dea66` / Actions `32028206103` exact-SHA 公共成功；产品拒绝 Pi，冻结保留评测资产 |

## 当前真实能力边界

已经存在的实现：

- 三态路由结果：`selected`、`rejected`、`ambiguous`；
- 无可用 Skill、无匹配 Skill、多 Skill 同时命中的明确原因码；
- Manifest 声明式必需信号组与排除信号；
- 排除信号在 Router 算法与 `RouterDecision` 合同两层都是硬否决；
- `recent-form-review` 与 `single-match-review` 两个真实用户 Skill Contract；
- 单局输入会验证 Summary v1.0、唯一目标 match、短局和 Timeline 缺失边界；
- 两个真实候选的近期选择、单局选择、混合范围歧义、裸 ID 拒绝和域外否决测试；
- 旧 15 条参与过单 Skill 规则校准的案例已归档，并有 SHA-256 来源记录；
- 双 Skill development v2（23 条）与 independent holdout v1（12 条）已建立；
- 评测 CLI 会校验数据集角色、案例数量、候选 Skill name/version 快照；
- development v2 已正式运行并保存到
  `data/evaluation/results/skill_router_v1_development_baseline.json`：23/23 精确匹配，
  selection/rejection/ambiguity accuracy 均为 `1.0`，false-selection rate 为 `0.0`；
- development 明细中没有误路由；该结果只支持冻结当前开发规则，不是泛化证据；
- independent holdout v1 已单次运行并保存到
  `data/evaluation/results/skill_router_v1_holdout_baseline.json`：11/12 精确匹配，
  selection/ambiguity accuracy 为 `1.0`，rejection accuracy 为 `0.8333`，
  false-selection rate 为 `0.1667`；
- 唯一失败 `holdout_device_performance_false_friend` 把“分析一下我最近键盘的表现”
  误选为 `recent-form-review`；实现符合当前字面合同，产品期望拒绝，分类为确定性
  Router 的域语义局限；
- 5C-6 已完成采用决策：确定性 Router V1 保持不变，不根据 holdout 增加“键盘”
  排除词，也不引入 LLM/Embedding；优先等待类型化产品入口、会话澄清与新鲜误路由
  数据，具体重新采用门槛见 ADR-0010；
- 5C 退出复核将命中决策的证据身份收紧为必须与候选 Skill 身份完全一致；
- holdout 冻结点元数据已从不包含双 Skill 合同的 `cfd2084` 更正为实际双 Skill
  合同提交 `4103d42`，没有修改案例、期望、规则或既有结果；
- 5D entry design 已完成源码级接缝审计；ADR-0011 决定 AgentLoop 只作为
  evidence-aware draft preparation，ReviewHarness 保持唯一评测和发布控制；
- 5D 已拆为 5D-1 至 5D-7 和 exit review；拆分本身不是功能实现；
- 两个 Skill 的关键输入输出文本现共享去空白、非空、集合去重规则，Skill 输出
  `run_id` 使用统一安全目录组件合同；
- selected `RouterDecision` 现在同时锁定 Skill 名称与版本，执行前必须与 Catalog
  中当前 `LoadedSkill` 的 Manifest 身份完全一致；
- `RunManifest`、`FileRunStore` 与 Skill 执行请求共享同一跨平台 run ID 规范，拒绝
  路径、盘符、Windows 保留名和超长值；
- `SkillInputArtifactBinding` 使用 Harness 实际 JSON/text 字节编码记录 Summary 与
  确定性报告的 kind、schema version 和 SHA-256；5D-5 已在 terminal output 前逐项
  核对真实落盘记录、物理字节与该内容承诺；
- `SkillExecutionBoundary` 会拒绝非 selected、缺失/漂移 Skill、错误 input model、
  run 不一致和内容/元数据篡改，并返回与调用方 payload 脱钩的输入快照；
- `ContextBuilderV1` 把内部 Policy 与已校验 SKILL.md 固定为 system/instructional，
  把确定性事实、用户请求和初始知识引用固定为 user/data-only；
- 近期复盘只接收 allowlisted scope、aggregate、样本边界、完整确定性报告和最多
  10 个可选 match 投影；单局复盘只接收唯一 target row 与不含其他 match 的精确
  报告行，不注入 `recent_summary`；
- Timeline unavailable 的 null/empty/error 与短局边界保持原义；failed-match 原始异常
  和未知 Summary 扩展字段不会自动进入上下文；
- Manifest context ceiling 不可被调用方提高；required sections 超限时 fail closed，
  optional match/citation 按优先级完整保留或省略，省略 ID 可审计；
- `ContextBundle` 消息必须是 sections 的规范渲染；`AgentRunCompiler` 会重新核对
  run/Skill/version、Manifest ceiling、实际消息大小与工具注册状态；
- `AgentRunCompiler` 只从已验证 Manifest 映射工具白名单、迭代、工具调用和总超时，
  从 `ContextBundle` 映射消息及有效 Context ceiling，并记录安全输入摘要 metadata；
- `DeterministicContextSizer` 现在计算 role/content、ToolCall id/name/arguments 与 Tool
  result metadata 的完整消息 envelope，仍只是 tokenizer-free preflight；
- `AgentLoop` 在每次 Provider 调用前重新估算累计消息；初始或 Tool Observation 后
  超限均以 `context_budget_exceeded` 停止，不再继续调用 Provider；
- Manifest `timeout_s` 被收紧为协作式总 deadline；Provider 获得递减剩余时间，
  ToolRuntime 取运行剩余时间与工具 policy timeout 的较小值，耗尽后以 `timeout` 停止；
- 旧 `LocalRagAdapter` 与新 Agent 路径共用 fail-closed 的知识 payload 转换器；只有
  实际成功且归因字段合法的 `knowledge.search` ToolResult 才能生成稳定 K1..Kn、
  去重 source IDs 与 `KnowledgeEvidence`，重复 chunk 归因冲突会被拒绝；
- `SkillAgentDraftPreparer` 使用 AgentLoop 的同一 ToolRegistry 编译并执行请求，只在
  `completed/final_response` 且最终文本非空时生成尚未发布的 `CoachDraft`；失败知识
  工具、非知识工具、坏 payload 与预算/重复/超时停止均 fail closed；
- `recent-form-review` 与 `single-match-review` 已在 Fake Provider 下通过真实 Catalog、
  Router、ExecutionBoundary、ContextBuilder、Compiler、AgentLoop、ToolRuntime 与本地
  `knowledge.search`；模型只在 Markdown 声称的虚假来源不会进入 Evidence；
- `DraftPreparationStep` 现在是 ReviewHarness 唯一草稿准备接缝；旧 Retriever/Generator
  通过 `SequentialDraftPreparer` 兼容，新 Agent 路径返回同一 draft/evidence 合同，
  没有第二套 Harness 控制流；
- `SkillReviewExecutor` 校验 execution/context 身份，只从 Skill Manifest 映射质量阈值
  和 deterministic fallback，并把 Agent 草稿交给现有 Evaluator/修订/发布状态机；
- `SkillTerminalOutputBuilder` 只从 terminal Manifest 和完整性校验通过的 FINAL_REPORT、
  最终 attempt Evaluation、RETRIEVAL_EVIDENCE 及输入 Artifact 构造 Manifest 声明的
  Pydantic Output；rejected 不暴露报告，降级只返回确定性报告；
- 两个真实 Skill 已在 Fake Provider 下完整走过 Catalog、Router、ExecutionBoundary、
  ContextBuilder、AgentLoop、真实本地 `knowledge.search`、唯一 ReviewHarness 与 typed
  output；该证据不等于真实 Provider Tool Calling；
- 生产 `ZhipuProvider` 已在离线 TDD 中实现 system/user/assistant/tool 四类消息、
  ToolSpec、AUTO/NONE、JSON mode、请求级 `knowledge.search` 可逆别名和 ToolCall
  规范化；REQUIRED、别名冲突、未知别名、非严格 JSON、重复/并行 ToolCall、非空
  reasoning、坏 content 与尚未准入的 structured+tool 同轮组合均 fail closed；
- `AdapterProtocolSliceRunner` 通过同一个 `BudgetedProvider` 把结构化直调和现有
  `AgentLoop` 两轮往返约束在精确 3 次外部调用内；A1 失败会跳过 A2，第 4 次调用会在
  进入底层 Provider 前被拒绝；
- A1 复用 5D-6a 的 `EvaluationResponseModel` 与严格 decoder；A2 只注册固定、只读、
  幂等、无重试/无缓存的 `knowledge.search` fixture，并要求一次 ToolCall、一次成功执行
  和精确终止标记；
- CLI 新增显式 `adapter_protocol` scope，必须同时提供真实调用确认与精确
  `max_calls=3`，OpenAI-compatible SDK 自动重试固定为 0；公开结果只保存安全错误码、
  调用/Token/响应计数和 SHA-256，不保存 Prompt、模型原文、observation 或原始异常；
- 当前本地完整回归：`415 passed, 103 subtests passed`；协议/CLI/结果合同聚焦回归
  `22 passed`；compileall 与 diff check 通过；
- 协议控制器提交 `f1d171d5591a511f9d6a9788a1bc8068172b0d51` 的 GitHub Actions
  run `31625669630` 全部通过后，只执行一次真实 `adapter_protocol/3`：A1 使用 1 call，
  A2 使用 2 calls，总计 3/3，二者均 passed，`admitted=true`；
- 真实 A1 为 427/59 tokens、2344 ms；A2 为 562/36 tokens、5360 ms，finish sequence
  为 `tool_calls -> stop`，工具调用/执行均为 1；未取得可靠单价快照，因此成本保持 null，
  不伪造为 0。
- `DomainSkillSliceRunner` 已离线组合真实 `recent-form-review` Catalog/Router/Boundary、
  Context Builder、AgentLoop、本地 `knowledge.search`、唯一 ReviewHarness 和 typed output；
  历史协议结果必须 `admitted=true`、精确 3 calls、Provider/model 一致，并记录文件 SHA-256；
- Agent 与 Harness 共享 `ExternalCallBudget(max_calls=4)`；happy path 为 Agent 2 calls +
  Evaluation 1 call，剩余 1 call 只允许 Evaluation 格式修复；revision 后再评测会在进入
  底层 Provider 前失败关闭，准入专用 SDK/Tool 自动重试均为 0/单次尝试；
- 真实领域 CLI 必须显式确认累计 `max_calls=7`，只允许批准结果目录，要求干净已提交的
  工作树并拒绝覆盖既有领域证据；Harness 原文只写系统临时目录，公开报告不保存
  Prompt、模型正文、Observation、原始 request ID、异常或 API Key；
- 领域控制器聚焦回归为 `23 passed`，相邻纵向比例回归为
  `141 passed, 29 subtests passed`，完整回归为 `430 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness SDK/敏感文件边界和 dry-run 均通过。所有领域证据仍为
  Fake Provider 离线证据，仓库中尚无真实领域结果文件。
- 领域控制器提交 `d51d8fa9da13ca16f47747260a1eca74c1ffdd76` 已推送到
  `origin/main`；GitHub Actions run `31657764638` 对该精确 SHA 的全测试、两套 RAG、
  compileall、Harness SDK/敏感文件边界和 dry-run 全部通过，CI 未调用真实 Provider。
- 真实 recent-form 领域切片随后只执行一次：使用 1 个领域 call，累计调用为 4/7；
  该计费请求没有形成进入 Agent 结果的统一 `ChatResponse`，因此 response/tool/evidence
  均为 0，也没有进入 Evaluation；公开结果为 `admitted=false`、
  `knowledge_round_trip_incomplete` 和 terminal `degraded`；
- 这次 `degraded` 证明确定性 fallback 在真实外部失败时阻止了未经评测草稿发布；它不
  证明 GLM 报告质量。当前脱敏证据不能继续区分 Adapter 规范化拒绝或其他统一响应前的
  Provider 错误，且没有质量分或可靠成本估算；
- ADR-0012 据此分层收尾 5D-6b：Zhipu Adapter 最小 structured/tool 协议准入，
  GLM-5.2 recent-form 领域能力不准入；不重跑、不临场调 Prompt、不立即接入第二
  Provider，真实失败进入 5D-7 的评测与错误归因设计。
- ADR-0014 让后续领域实验强绑定 Prompt/Context 语义身份：组件层覆盖 Skill Manifest/
  Instructions、Context Policy、`knowledge.search` 合同、Evaluation Schema/事实投影与
  prompt builders；案例层覆盖输入 Artifact、typed options、实际 section、最终消息与
  Context 预算；
- 冻结快照 `recent-form-prompt-context-v1` 的自摘要为
  `88af3ed94e2458dc67e92c311de3543ca23c5923c0591ad83cfa3d2db6fd95e0`；
  Domain Dataset/Candidate/Result 已升至 Schema 1.1 并强绑定该 ID/SHA；
- `prepare_domain_e2e_experiment.py` 会在 Provider 前从当前真实 Catalog、Router、
  ExecutionBoundary 与 ContextBuilder 重建快照，核对冻结快照与 Dataset 后才产生
  `admitted=true`；当前 admission 的 `external_provider_calls=0`；
- 快照和 admission 只保存安全元数据及摘要，不保存 Prompt、玩家事实、模型正文、
  Tool Observation、异常、request ID 或 Key；它们是实验前置身份，不是 5E Trace。
- Batch B 聚焦测试为 `20 passed`，相邻纵向回归为 `87 passed, 4 subtests passed`，
  完整回归为 `450 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/
  tracked-data、dry-run、快照正文脱敏、治理和 diff check 均通过；
- Domain E2E 1.1 基线与 admission 已从 CLI 临时输出逐字节复现；功能提交
  `e56b00091ef2ab299af692e902945b8342fbc99e` 已推送，GitHub Actions run
  `31690698734` 对该精确 SHA 全部通过。
- ADR-0015 采用脚本 Provider 驱动真实本地控制流，而不是继续手填 Candidate 或立即
  调用真实模型；新增 Schema 1.2 `offline_executable` Candidate，要求零外部调用且每个
  案例都有安全 provenance SHA-256；
- Batch C 的 7 个 development 场景均先通过 Batch B admission，再真实运行 Catalog/
  Router/Boundary、ContextBuilder、AgentLoop、`knowledge.search`、ToolRuntime、本地混合
  RAG、Evidence 构建和唯一 ReviewHarness；只有 Provider 响应为确定性脚本；
- 可执行场景覆盖成功、缺工具、错误 90% 胜率、未知 `[K999]`、用户注入、RAG 注入和
  Evaluation 漏判注入。最后一个场景实际被 Harness 发布，再由分层评测标记
  `unsafe_publication`，因此 1/7 不安全发布率是保留的开发 Bad Case，不是通过率；
- Candidate 中的 fact/citation/injection 结论从实际 draft、evidence Artifact 和 canary
  probe 提取，公开 Candidate/Result 不保存 canary、错误事实、Prompt、报告、工具原文、
  request ID、异常或 Key；CLI 重跑与冻结文件逐字节一致，外部调用为 0；
- Batch C 聚焦/相邻测试为 `25 passed`；完整回归为
  `455 passed, 103 subtests passed`。两套 RAG、compileall、Harness SDK/tracked-data、
  artifact 脱敏、治理、diff check 和 Harness dry-run 均通过；
- 这些结果证明离线实验接线和本地发布边界可复现，不证明任何真实 Provider 的领域
  质量或通用抗注入能力；当前 Evaluation Schema 也没有专用 injection issue category。
- Batch D 入口审计确认，现有 `ChatEvaluationAdapter` 只把确定性 fact pack 与待审报告
  放入 Prompt；虽然 `EvaluationRequest` 携带 `KnowledgeEvidence`，Evaluator 当前看不到
  用户原话、实际知识证据或信任标签。原地增加 issue 枚举既缺输入又会破坏 Batch A-C
  的 `coach_evaluation@1.0.0` 历史身份；ADR-0016 因此保留 1.0.0，D1-D2 已离线迁移并
  接入 1.1.0 安全评测合同与 blocking policy；D3 已创建独立 held-out，已知 canary 只
  作为实验 oracle，不进入生产关键词黑名单；
- ADR-0016 还冻结了后续门：D1/D2 离线迁移通过并冻结后才创建独立 held-out；真实首轮
  只比较同一冻结合同下的正常、用户注入和知识注入 3 场，每 Provider 每场最多 4 calls、
  领域最多 12 calls、`max_revisions=0`、SDK retry 为 0；第二 Provider 另需新 ADR 与最多
  3-call Adapter 协议门；
- ADR-0017 原先以协议成本为主选择 V4 Flash；经用户追问和 D5 目标复核，ADR-0018
  保留其历史并将唯一候选更正为 DeepSeek 官方 `deepseek-v4-pro`。独立 Adapter、
  non-thinking、最多 3-call 协议 + 12-call 领域预算、每案例 4000 tokens、每请求最多
  1024 output tokens、GLM ¥0.50 与全局/单 Provider 停止规则不变；按 Pro 峰值价把
  DeepSeek 停止线更正为 `$0.10`。选择候选不等于已经实现、调用、准入或设为默认模型。
- ADR-0019 保持当前 Pro-only 5D-7 准入门不变，并纠正未来 Flash 分层的归属：该工作
  最早在 5P 后、默认等待阶段 6 的真实 API 调用、Trace、成本或延迟 Bad Case，以横向
  Provider 优化门比较 Pro-only、Flash-only 和 Flash 默认/Pro 有界升级；5F 仍只负责
  Pi / Claude Agent SDK Runtime 采用实验。当前不增加 Flash 配置、调用或自动路由。
- D4 聚焦回归为 `68 passed, 15 subtests passed`，完整回归为
  `460 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/敏感文件边界、
  Harness dry-run、文档密钥模式扫描、governance 和 diff check 均通过，外部调用为 0。
- D5 新增独立 `DeepSeekProvider`，冻结 `https://api.deepseek.com`、
  `deepseek-v4-pro`、non-thinking、non-streaming、JSON mode、请求级工具别名和严格
  finish/usage/错误语义；它没有注册为产品默认 Provider，也没有复用 Zhipu Adapter
  冒充厂商无关实现；
- D5 让 `AgentRunStatus`、`AgentStopReason` 与安全 `error_code` 组成的不可变失败观察
  穿过 draft preparation 接缝。真实 AgentLoop Provider failure 测试证明 Harness 仍只
  返回确定性 `degraded`，同时上层能区分认证等安全来源，不保存 Prompt、模型正文或
  原始异常；
- 实验 ledger 在 I/O 前占用调用并检查 scope/cumulative call、每请求 output、累计
  observed Token 与估算金额；SDK 失败不退还调用，usage 缺失不按 0 结算，任一
  `unsafe_publication` 会触发全局停止。它是应用层实验门，不是厂商账户硬限额或 5E
  统一 Trace；
- D5 no-I/O preparation 只核对干净 Git SHA、公开 CI SHA、冻结 held-out 与
  Prompt/Context snapshot；不加载 `.env`、不读取 Key、不创建 OpenAI client、不运行
  held-out。Fake SDK 的 3-call 协议回归只证明 Adapter 映射和控制流，不证明 Pro 的
  真实能力；
- D5 聚焦/相邻回归已经通过，当前完整回归为 `505 passed, 103 subtests passed`；两套
  RAG 门禁、compileall、Harness dry-run、SDK/tracked-data 边界、governance 与 diff
  check 均通过。功能提交 `e68a8e4542ed72d31d5d46e569a11d9292048540` 的 GitHub
  Actions run `31764109304` 全部通过；同一干净 SHA 的 no-I/O preflight 随后通过，
  `external_provider_calls=0`、`held_out_executed=false`。

当前不能声称：

- GLM 或任何真实 Provider 已完成领域 Skill/Harness 准入；当前生产 `ZhipuProvider`
  只通过最小 Provider-neutral structured/tool 协议切片，真实近期复盘领域链路已尝试
  但未准入；
- 真实模型生成的新 Coach 报告已经通过当前端到端领域评测；本次没有统一响应进入
  Agent，也没有草稿、知识证据、Evaluation 或质量分；
- 默认 ContextSizer 等于真实厂商 tokenizer 或真实 Token Usage；
- trust/JSON 分层已经彻底解决 Prompt Injection；
- Batch C 的脚本 Provider/canary 已证明真实 GLM、DeepSeek 或 Qwen 抗注入；
- DeepSeek V4 Pro 已通过领域 Skill/Harness 准入、成为产品默认模型或普遍优于
  Qwen/GLM；真实领域 held-out 已运行但未准入，当前只准入最小 structured/tool
  Adapter 协议；
- 已经实现 Tool Observation compaction，或协作式 deadline 能硬中断任意阻塞函数；
- 路由对自然语言具有充分泛化能力；
- 小型合成 holdout 已证明路由对自然语言充分泛化；
- 已把 holdout 失败用于调节 Router 规则；
- 已实现 LLM Router fallback 或修复设备域假朋友；
- Router 已执行 Skill、Tool、Harness 或模型调用。
- 5D-1 的内容承诺已经等同于真实 Harness Artifact 落盘或 Agent 执行。
- `user_utterance` 已通过统一 Runtime/Trace 与最初 `RouterRequest` 形成不可变来源链。

## 四条进度线

| 进度线 | 当前事实 | 不能混淆为 |
|---|---|---|
| 本地代码 | 已公共闭环项不变；RQ-108 Task 1 strict manifest/cover geometry/preflight media policy 已本地完成，但尚无 production manifest、`<video>`、媒体资产或页面集成 | Task 1 合同绿灯等于 Portal Motion Polish、正式 OIDC/RSO、可追问 Coach、完整 8E 或生产 SLA |
| 项目理解 | RQ-108 walkthrough 已补 manifest、CSS cover 数学、poster/preflight、modern/legacy listener、竞态与可讲/不可讲边界 | 持久材料存在等于用户已能独立讲解所有实现；owner mastery 仍需复述、读码和运行验证 |
| 参考资料 | Kimi Bad Case 与生成/确定/混合路线已审计；RQ-121 记录 official-first、relay-secondary，但中转目录仍只是未验证 catalog | 型号更“新”、站内 `official` 标签或低价等于模型身份、能力、隐私或视觉准入 |
| GitHub/部署 | RQ-108 design/state closure 已 exact-SHA；Task 1 当前只本地完成等待独立公共 CI，Docker image 仍不 COPY web | 本地合同/Compose 或公共设计证据等于媒体已部署、HTTPS edge、完整 8E 或公网生产可用 |

当前 Riot 账号身份边界：官方 LoL routing 列表不含中国大陆 CN；外服 Riot ID 查询只能形成公开账号
引用。用户选择“这是我的账号”在正式 RiftCoach Auth、安全绑定的 RSO callback 和精确 PUUID match 前
只能标记为 `claimed_self`，不得表述为已验证授权。owner-global 偏好按 owner 隔离，玩家相关的私人
Session/Memory 再按 owner-local player subject 隔离。RQ-062 已确认 MVP 同时提供受限
`public_observed`：它只承载公开比赛分析与 owner-local 观察备注/趋势，不冒充被观察者本人的偏好或训练
完成度；任一关系都不增加 Riot 数据权限或跨 owner 合并私人 Memory。

## 已裁决的首批 Skill 与事实审查边界

2026-08-05 的讨论同时确认了两点：

1. 先用一个 `recent-form-review` 样板稳定 Skill Contract 和 Router；
2. 首批宏观能力仍包含近期复盘、单局复盘和报告事实审查，并曾把三者都称为
   Skill，要求在 5C-4 后补齐再完成真实多 Skill 路由评测。

源码级复核发现，事实审查并不是缺失的第三个工作流：`EvaluatorStep`、
`ChatEvaluationAdapter` 和 `ReviewHarness` 已经提供类型化输入输出、复用入口、
修订预算和强制发布门禁。把它再包装成 Skill 只会复制合同。

- `recent-form-review`：已存在的用户可路由 Skill；
- `single-match-review`：已建立的第二个用户可路由 Skill；
- 报告事实审查：继续作为 Harness `EvaluatorStep` 强制执行，不是 Skill。

未实现的调用模式合同和 `report-fact-check` Skill 已在写代码前取消。实施顺序修正
为单局 Skill、真实双 Skill 路由评测、模型兜底决策。详细裁决见 ADR-0008 和
ADR-0009。

## 2026-08-06 阶段漂移事件

### 发生了什么

原计划明确包含 5C-1 至 5C-6，但一次实现批次把 5C-3 的代码、5C-4 的部分
拒绝/歧义行为和 5C-5 的初步开发评测一起完成后，文档被直接更新成“5C
完成，下一步 5D”。这把“代码已提前存在”误写成了“原检查点已经逐项完成”。

### 根因

- 原始 5C-1 至 5C-6 清单只存在于长对话，没有写进仓库；
- 旧 `.planning` 任务停在 2026-08-01，且没有 `.active_plan`；
- 没有根级 `AGENTS.md` 强制恢复上下文和同步状态；
- 多份状态文档并存，却没有唯一当前状态源；
- 实现计划错误地把一个批次的测试通过当成整个 5C 的完成条件。

### 修复原则

- 恢复原有 5C-1 至 5C-6 边界，不回滚已经写出的有效代码；
- 提前实现的内容回到原子阶段逐项讲解、复核和验收；
- 以后“继续”只推进本文件列出的唯一下一步；
- 每次状态变化同时更新当前状态、活动计划和冲突文档。

### 持久化与自动保护

- 本文件头部的机器可读元数据与正文共同构成同一个唯一状态源；
- `.planning/.active_plan` 指向当前任务的计划、发现和进度三份持久记忆；
- `docs/requirements_change_log.md` 追加记录跨轮次长期要求，不静默覆盖旧决定；
- `scripts/check_project_governance.py` 在本地和 CI 核对当前检查点、活动计划、
  九阶段编号、需求编号和工作约束；任何冲突都先阻止功能推进；
- 自动检查降低再次漂移的概率并让错误可见，但不能替代用户对阶段验收的确认。

## 下一检查点的范围

RQ-040 已解除 RQ-039 的暂停；`5P-entry-design` 已由 `49841ec` / Actions `31985199623`
完成 exact-SHA 公共验证。源码审计确认产品输入（Riot ID/少量选项）与 Runtime 输入（selected
Skill、Summary、确定性报告、Artifact binding、policy）之间必须有 Application Service；
同时 5D 退出证据明确把 Prompt Program V1 放在 5P，而 Runtime prompt profile 仍是硬编码身份。

因此 ADR-0032/0033 分别接受：

1. 复用既有 component fingerprint 建立版本化 Prompt Program/Catalog/drift gate，让真实
   Skill、Context、knowledge tool、Evaluation 1.1 与 Revision 组合绑定 prompt identity；
2. 采用薄 FastAPI Adapter + `RecentReviewApplicationService` + 现有 `AgentRuntimeV1`，并以
   body-free file receipt/query projection 复读 Trace/manifest/final Artifact。

5P 已固定为 5P-1 产品合同/typed compiler、5P-2 Prompt Program/composition、5P-3 domain/
application service、5P-4 receipt/query、5P-5 FastAPI/no-I/O vertical slice、5P-6 exit review。
entry design 没有安装 FastAPI、实现产品代码、读取 Key、调用 Riot/Provider 或运行 held-out。
5P-2 已由 `0a9651f` / Actions `31988837293` 完成 exact-SHA 公共闭环；RQ-043 随后恢复并完成
`5P-3-domain-application-service`，提交 `4bd5c83` / Actions `31998739178` 已公开通过。
5P-4 receipt/query 已由 `932a863` / Actions `32002994441` 完成 exact-SHA 公共闭环。5P-5
thin FastAPI/no-I/O vertical slice 又由 `6d1e5b0` / Actions `32005648179` 完成 exact-SHA
公共闭环并正式关闭；5P-6 的 exit matrix/review 与全部门禁裁决为
`close-with-deferred-boundaries`，并由 `8c8acc6` / Actions `32010604551` 完成 exact-SHA
公共验证。整个 5P 正式关闭；canonical 只交接到 `5F-entry-design` 准备状态，等待用户再次明确
继续，不自动实施 SDK 对照或进入阶段 6。

本节后续保留从 5C 到 5D 的历史范围账本；其中旧“下一步”只表示当时顺序，不覆盖本文顶部的
canonical checkpoint。

`5C-5-prep-1 Skill Invocation Contract` 与 `5C-5-prep-3 report-fact-check Skill`
已在功能代码开始前由 ADR-0009 取消，并保留在历史记录中。

`5C-5-prep-2` 已完成：单局 Skill 明确了输入、输出、触发/排除边界、工具权限、
预算、步骤和成功标准，Catalog 现在有两个真实用户候选。

`5C-5` 已完成：旧单 Skill 基线原样归档；development v2 以 23/23 冻结规则；
independent holdout v1 随后只运行一次并得到 11/12。唯一失败是设备语义假朋友，
其期望拒绝、实际选中近期复盘，结果已原样保留且不会用于调节本版本规则。

`5C-6` 已完成：ADR-0010 决定 V1 暂缓 LLM Router fallback。单一小型合成 Bad
Case 不足以抵消模型带来的结构化输出、延迟、成本和故障复杂度；现有 GLM Adapter
也只声明 `text_chat`。未来先采用类型化入口和澄清，再以新鲜数据、新 holdout、
结构化输出与质量/成本证据重开模型实验。

`5C-exit-review` 已通过：完整证据、修复项、限制、框架中立边界和面试安全表述见
`docs/plans/2026-08-07-skill-router-v1-exit-review.md`。5C 现已完成。

`5D-entry-design` 已完成。采用 ADR-0011：AgentLoop 负责白名单工具调用和草稿准备，
`ReviewHarness` 仍是唯一评测、修订和发布控制面；通过 `DraftPreparationStep` 接缝
同时兼容旧顺序 Retriever/Generator 和新 Agent 路径。完整设计见
`docs/plans/2026-08-07-constrained-skill-agent-loop-design.md`。

`5D-1 Skill Run Boundary Hardening` 已完成：两个 Skill 的关键文本合同、selected
name/version、共享安全 run ID、Harness 规范输入字节摘要和 Catalog-backed 执行前
校验均已有 TDD 证据。该内容绑定尚未创建真实 Harness Artifact，也没有调用模型或
工具。

`5D-2 Context Builder V1` 已完成：`ValidatedSkillExecution` 被投影为 trust-typed
sections，经 Manifest 硬上限做 required-first、optional whole-section 选择，再渲染为
现有 system/user `ChatMessage`。近期与单局使用不同事实 allowlist；初始 citation
逐条作为 data-only section；设计和 TDD 证据见
`docs/plans/2026-08-07-context-builder-v1-design.md` 与对应 implementation plan。

`5D-3 Skill Run Compiler & Budget Enforcement` 已完成：`AgentRunCompiler` 从已验证
Manifest 与 `ContextBundle` 编译现有 `AgentRunRequest`，不接受权限或预算 override；
完整消息 sizer 覆盖 ToolCall/Tool result envelope；AgentLoop 在每次 Provider 调用前
执行累计 Context 门禁，并把 Manifest timeout 作为 Provider/Tool 共用的协作式总
deadline。设计与 TDD 证据见
`docs/plans/2026-08-07-skill-run-compiler-budget-design.md` 与对应 implementation plan。

`5D-4 Evidence-Aware Agent Draft Preparation` 已完成：知识 payload 转换逻辑已从
旧 `LocalRagAdapter` 抽成共享纯函数；`SkillAgentDraftPreparer` 将受限 AgentLoop 的
最终文本降格为 `CoachDraft`，只从实际成功的 `knowledge.search` 执行记录构造
`KnowledgeEvidence`。两个真实 Skill 已用 Fake Provider + 真实本地知识工具走通；
设计和 TDD 证据见 `docs/plans/2026-08-08-skill-agent-draft-preparation-design.md` 与
对应 implementation plan。该检查点没有运行 Harness 或真实 Provider。

`5D-5 Harness Composition & Typed Terminal Output` 已完成：`ReviewHarness` 只依赖
统一 `DraftPreparationStep`，旧路径由顺序 Adapter 兼容；`SkillReviewExecutor` 把
5D-4 的 Agent draft/evidence 交给同一评测、修订、发布/降级/拒绝控制流；最终 Skill
Output 只从 terminal Manifest 与完整性校验通过的 Artifact 构造。两个真实 Skill
已通过 Fake Provider + 真实本地知识工具的完整组合测试。设计和 TDD 证据见
`docs/plans/2026-08-08-skill-harness-composition-design.md` 与对应 implementation plan。

`5D-6a Structured Output Contract` 已完成：`ChatRequest` 可以显式携带冻结的
`StructuredResponseContract`，能力协商会要求 `STRUCTURED_OUTPUT`；严格 Pydantic
Evaluation 模型同时提供 JSON Schema 和本地验证；非法 JSON、额外/缺失字段、错误嵌套
类型、非法枚举、fence 和截断都会被拒绝。最多允许一次携带同一合同的格式修复，第二次
失败返回安全错误；Harness 只会 deterministic fallback 或 rejected，不能发布 Agent
草稿。该检查点当时保持 `ZhipuProvider` text-only；5D-6b 现已补齐离线厂商映射，
但 Fake SDK 证据仍不等于真实 Adapter 或领域 Skill 准入。

`5D-6b Real Provider Capability Gate` 已由 ADR-0012 收尾。P1-P5 与精确 3-call
Adapter 协议切片通过；真实 recent-form 领域切片只尝试一次，在一个计费请求后未形成
统一 `ChatResponse`，没有工具证据或 Evaluation，并安全降级。结论是最小协议能力
准入、领域能力不准入，而不是 GLM 整体成功或整体失败。

当前检查点为 `5D-7 Prompt/Context & Domain E2E Evaluation`。Batch A 已把上述真实
Bad Case 纳入 development，并建立分层合同和 10 案例离线基线；Batch B 又以 ADR-0014
冻结组件级与案例级 Prompt/Context 语义身份，让 Dataset 1.1 和后续候选绑定相同
Skill、Context、知识工具及 Evaluation 合同。离线 admission 会在 Provider 前重建并
精确核对快照，当前外部调用为 0。它只证明实验条件可重复，不证明 Prompt、真实模型、
未知注入或报告质量已经通过。

Batch C 已用 ADR-0015 建立七场 `offline_executable` development 基线。每场都先经过
Batch B admission，再由 Scripted Provider 驱动真实 Skill/Agent/Tool/RAG/Harness；
事实、引用和注入检查从实际运行产物提取。一个 Evaluation 漏判场景真实发布了含 RAG
canary 的报告，并被分层评测标记为 unsafe publication，明确证明 Harness 的确定性发布
决策仍依赖 Evaluation 输入质量。该结果只验证实验接线，不评价真实模型。

Batch D 的 D1-D2 已完成：保留 `coach_evaluation@1.0.0` 历史路径，新增并接入
`coach_evaluation@1.1.0` 安全评测输入/输出、`prompt_injection` blocking issue 与不可
修订的 Harness policy；secure offline executable development 7 场结果为 task outcome
accuracy `1.0`、failure classification accuracy `1.0`、unsafe publication rate `0.0`、
external calls `0`。D3 已在合同、Prompt、snapshot 与规则冻结后创建 3 场独立 held-out，
带 `calibration_excluded=true` 和无污染声明；D3 只完成创建与生命周期测试，没有运行
held-out。上述结果不证明真实模型质量或通用抗注入能力。

D4 已由 ADR-0018 更正并收尾：ADR-0017 的 Flash 选择保留为历史，唯一有界第二
Provider 候选改为 DeepSeek V4 Pro；同任务比较、协议/领域分层准入和成本/停止规则已经
冻结。D5 已离线实现独立 Adapter、安全失败归因、预算 ledger 与 no-I/O preparation；
Fake SDK 和 scripted response 下的协议与失败回归通过，外部调用为 0。Qwen3.8 Max 与
V4 Flash 暂缓，不代表质量较差。ADR-0019 进一步确认 Flash 不进入当前 5D-7，也不占用
5F；未来模型分层最早在 5P 后、默认于阶段 6 由真实产品成本/时延证据触发。

D5 real-gate execution seam 提交 `076a5e3558cd68abb545cebdc2542c973b020768`
已通过 GitHub Actions run `31767405927` 与同 SHA no-I/O preflight；随后只执行一次真实
DeepSeek V4 Pro 协议门。A1 strict structured contract 与 A2 Agent tool round trip
均 passed，总计 3/3 calls、1428 tokens、估算 `$0.00221496`，无 Provider/global stop，
`admitted=true`。脱敏结果 SHA-256 为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
该证据只准入最小 Adapter 协议，不准入领域报告质量或产品默认模型。5D-7 的唯一
后续先完成了冻结三场领域 held-out 的执行接缝设计与离线 TDD；本批没有调用 Provider，
且不得进入 5D exit review 或 5E。协议结果归档提交
`ba1379db6b573d07e6cbe3bd27b9561ea9ca9f6e` 已通过 GitHub Actions run
`31779362817` 的精确 SHA 公开 CI。

领域 held-out 执行接缝现在把控制面和数据面分开：
`prepare_deepseek_domain_heldout_run()` 不接收或构造 Provider，先核对当前 preparation、
冻结 Dataset/Snapshot、执行计划摘要与已准入协议字节摘要；只有 admission 产生且结果
文件已独占预留后，后续入口才可读取 Key/构造 Provider。`ProviderResourceLedger` 可从
旧协议账本继续，新增 protocol/domain scope Token 和单案例 calls/Token 三层边界；领域
协调器逐例生成 ledger-derived 资源、安全语义观测和既有分层 Evaluation，任一 Provider、
案例 mismatch 或 unsafe publication 会停止剩余案例。合成 Fake Provider/Executor 回归
证明第 5 个单例调用在 I/O 前拒绝、首错后剩余 skipped、异常正文不落盘、结果不可覆盖；
真实协议文件仍严格解析为 3 calls，SHA-256 仍为
`575e8f5423bde6b34a692c63f90764313ba820772ae974109a4328b3dba086e1`。
执行接缝提交 `7986e1ade9ab165b4b2916a62b067587c5c3f027` 已通过 GitHub Actions
run `31785253957` 的 exact-SHA 公开 CI。后续生产装配批已在零外部调用下把 held-out
修正为 1.1.0 安全成功门，冻结输入计划并接入生产 Executor/CLI；功能提交
`eb198354b3186f25b7d0455d7ed28725bc17e234` 已通过 GitHub Actions run
`31799394506` 的 exact-SHA 公开 CI。用户确认后真实领域门只执行一次；首例返回
`unsupported_parallel_tool_calls` 并由 Adapter fail closed，Harness 降级，后两例
skipped，领域 `admitted=false`。当前结果不可重跑；并行 ToolCall Bad Case 需回到
development 独立处理，仍不得直接进入 5D exit review 或 5E。

ADR-0022 的本地 development TDD 随后移除了 DeepSeek Adapter 对调用数量为 1 的额外
限制，但保留唯一 ID、已声明别名、严格 JSON object、finish reason 和 capability 校验。
AgentLoop 用四类测试固定“整批预算/白名单/重复预检后才顺序执行”的零副作用语义；新的
development 案例又通过 Fake DeepSeek SDK 真实串联本地 RAG、Evidence、Secure
Evaluation 1.1 与 ReviewHarness 并安全发布。完整回归为 `551 passed, 103 subtests
passed`，两套 RAG、compileall、Harness dry-run、安全边界和治理门通过，外部调用为 0。
这些证据只证明执行链兼容性；exact-SHA 公开 CI 已由 `037a47f` / `31817798170` 通过，
但仍不准入真实模型领域质量。ADR-0024 已在其后完成新鲜门设计。

### 2026-08-15：GLM-5.3 模型迁移规划边界

官方 GLM-5.3 文档已确认该模型存在；页面说明 Coding Plan 已开放，普通模型 API 将
逐步上线，并明确 GLM-5.3 始终启用 thinking，不能继续发送当前 Zhipu Adapter 固定的
`thinking.type=disabled`。因此 GLM-5.3 不是只改 `.env` 的透明升级。

本次只记录 ADR-0023 和迁移设计，不读取 Key、不调用 Provider、不修改默认模型，也不
改变 DeepSeek 当前实验。GLM-5.2 的历史结果保持只读；DeepSeek Adapter、DeepSeek
协议/领域结果、预算和 Dataset 1.1.0 保持只读且不可重跑。

GLM-5.3 的未来顺序固定为：当前 5D-7 新鲜领域采用门剩余离线 TDD/公开 CI 完成后，
再做 G53-0 可用性与 endpoint 审计、G53-1 Zhipu thinking profile 离线 TDD、G53-2
公开 CI、G53-3 最多 3-call 协议门、G53-4 新鲜领域采用门。GLM-5.3 通过新鲜领域门前
不替换 GLM-5.2 默认值，不进入自动模型路由，不影响 DeepSeek。

### 2026-08-15：DeepSeek 新鲜领域采用门设计

ADR-0024 选择复用已有 no-I/O admission、薄协调器、预算 Provider、production Executor、
分层 Evaluator 和唯一 ReviewHarness，不重写第二套控制面。旧 Dataset 1.1.0、旧输入
计划、真实 3-call 协议和真实拒绝结果继续按精确 bytes 只读保存，禁止复制改名或重跑。

新门必须在合同实现和规则冻结后才创建新的匿名 fixture、Dataset、输入计划与三个实际
案例的 Prompt/Context 摘要。Fresh-Gate 1 先只用合成 development 数据做向后兼容合同、
历史证据链、身份漂移、预算/停止、Key-last 和脱敏 TDD；通过 exact-SHA CI 后才进入
正式新 held-out 创建批。

历史已观察 3 次协议调用和 1 次失败领域调用；新鲜领域范围未来每例最多 4 calls、总计
最多 12 calls、4000/12000 observed tokens、每请求 1024 output、金额停止线 `$0.10`、
零 SDK/Tool retry、`max_revisions=0` 和首错停止。该预算不是当前调用授权。本设计批没有
读取 Key、调用 Provider、创建新 held-out、修改 Prompt/Evaluation/Harness 或进入 5E。

设计提交 `f9edb4b4d8a66e12946ffdb3da36881ea5e5e2fc` 已推送；GitHub Actions run
`31859717836` 对该精确 SHA 的治理、完整 pytest、两套 RAG、compileall、Harness
boundary、tracked-data 和 dry-run 全部成功，CI 没有调用真实 Provider。

### 2026-08-15：DeepSeek Fresh-Gate 1 本地离线 TDD

输入计划合同已向后兼容扩展为 V1.0/V1.1：旧 V1.0 计划仍按精确旧字段读取；V1.1 必须
同时声明 Prompt/Context snapshot ID/SHA，并按案例顺序提供一一对应的 Context 摘要。
Prompt/Context snapshot V1.1 会让三个显式 development case 分别经过真实 Catalog、
Router、ExecutionBoundary 与 ContextBuilder，仅保存 section/message/输入摘要，不保存
用户、fixture、注入或 Prompt 正文；V1.0 快照仍可逐字节复现。

新增的 historical evidence 会严格复读旧协议和旧拒绝结果 bytes，保留 `3 protocol +
1 rejected domain = 4 historical calls`；协议已知资源保持 1303/125/1428 tokens 与
`$0.00221496`，规范化前失败调用的 Token/费用则标为 unknown，不会被旧公开记录里的
统一账本零值误解释为已知零。该证据同时锁定多 ToolCall 修复提交
`037a47f...` 与 Actions run `31817798170`。

`FreshDomainDevelopmentAdmission` 只接受 development Dataset、V1.1 plan、三个当前/
冻结 Context 摘要、历史证据和 `code_sha == public_ci_sha` 的零调用 preparation；函数
签名没有 Provider/API Key，输出固定 `provider_construction_authorized=false`、
`external_provider_calls=0`、`held_out_executed=false`。聚焦测试 33 个、相邻 51 个，
完整回归 `568 passed, 103 subtests passed`；两套 RAG、compileall、Harness SDK/
tracked-data boundary 和 dry-run 已通过。期间实施计划最初写了三个不存在或错误参数的
外围命令，已按 `.github/workflows/tests.yml` 更正并重跑；这是验证命令错误，不是产品
回归。当前没有新 held-out、Key、Provider call 或真实领域结果。实现提交
`adba965a7f7fb4293020502b4440e9880633e571` 已推送，GitHub Actions run
`31860874440` 对精确 SHA 的治理、完整 pytest、两套 RAG、compileall、Harness SDK/
tracked-data boundary 与 dry-run 全部成功，CI 未调用 Provider。下一步单独进入
Fresh-Gate 3 创建/冻结全新资产，仍不运行 held-out。

### 2026-08-15：DeepSeek Fresh-Gate 3 本地资产冻结

新的 `domain-e2e-v2-secure-held-out` 在 Fresh-Gate 1/2 公开冻结后才创建，包含正常复盘、
用户数据指令边界和知识数据指令边界三个案例。它与已消费旧题不复用 fixture bytes、
case/run ID、用户措辞、知识注入正文或 marker；Dataset 为 `held_out` 且
`calibration_excluded=true`，没有污染记录。

新的 V1.1 input plan 只保存实际输入和 fixture/Context commitment，Dataset 单独保存
oracle；production Executor 仍只接收 `case_id + provider`。三个实际案例均通过当前真实
Catalog、Deterministic Router、SkillExecutionBoundary 和 ContextBuilderV1，生成
`recent-form-prompt-context-v1-2` 的 body-free 摘要；Snapshot 自摘要为
`79974fb2089f6c73d66d35d13d419bf9b70e147d5c6890dccf929dc114a50011`。

本地聚焦回归 `39 passed`，完整回归 `574 passed, 103 subtests passed`；两套 RAG、
compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 已通过。
正式结果文件不存在，新增 Provider calls 和 held-out executions 均为 0。当前只完成本地
资产冻结。资产提交 `1e44b130f4f054e06ab92fcc437dcd1fa74a13e8` 已推送，GitHub
Actions run `31861960565` 对精确 SHA 的治理、完整 pytest、两套 RAG、compileall、
Harness SDK/tracked-data boundary 与 dry-run 全部成功，CI 未调用 Provider。

Fresh-Gate 3 至此完成。唯一下一步为 Fresh-Gate 4 入口批：将新资产绑定到 held-out
no-I/O admission 和现有生产 CLI，先做离线 TDD 与新的公开 CI；该入口批仍不读取 Key、
调用 Provider 或运行 held-out，真实 12-call 上限需在后续再次明确确认。

### 2026-08-15：DeepSeek Fresh-Gate 4 运行入口本地完成

Fresh-Gate 4 采用版本化控制面，不复制第二套 Agent/Executor：

- `FreshDomainHeldOutAdmission` 绑定旧协议与旧拒绝结果 bytes、ADR-0022 修复 CI、
  Fresh-Gate 3 资产 commit/CI、当前 code/public-CI、新 Dataset/plan/fixture 和三个逐案例
  Context commitment；其 no-I/O 结果固定 Provider calls 为 0、held-out 未执行，且单凭
  admission 不授权 Provider 构造；
- 旧 Adapter 协议的 Context 身份与新领域 Context 可以不同，因为两者回答不同问题；
  旧协议模型、准入状态、资源和精确 result SHA 仍必须一致，新 Context 由 readmission
  独立绑定；
- 现有 `run_deepseek_domain_heldout.py` 使用 V2 active profile，增加 `--prepare-only`；
  实际顺序保持 output conflict → no-I/O admission → output reserve → env/Key → Provider →
  bounded execution；
- 新 `FreshProviderDomainExperimentRecord` envelope 同时保存完整 readmission 和原领域分层
  结果；旧 `ProviderDomainExperimentRecord@1.0` 与历史 JSON 未改义、未覆盖；
- Fake Provider 在临时目录完整经过 production Executor、RAG、Evaluation 1.1 和 Harness；
  正常路径 3 例共 9 次合成调用并通过，受控鉴权失败路径只调用 1 次、后两例跳过且结果
  不可覆盖。这些是离线控制流证据，不是 DeepSeek 质量或真实 held-out 证据。

聚焦相邻回归 `93 passed`，完整回归 `580 passed, 103 subtests passed`；两套 RAG、
compileall、Harness SDK/tracked-data boundary、dry-run、governance 和 diff check 通过。
真实结果文件不存在，API Key 未读取，外部 Provider calls 和真实 held-out executions 均为
0。唯一下一步是提交/推送并验证本实现的 exact-SHA CI，随后在干净同 SHA 上执行一次
真实 `--prepare-only`；真实模型运行仍需再单独确认。

实现提交 `ed3cc947bfdcf2eed22d57864ff852c5107f601a` 已通过 GitHub Actions run
`31863341338` 的 exact-SHA 全部门禁。随后在同一干净 SHA 执行真实 `--prepare-only`，
输出为 `no_io_admitted=true external_provider_calls=0 held_out_executed=false`；命令未创建
正式结果文件。Fresh-Gate 4 入口至此公开完成，下一步只进入真实运行确认门，不自动读取
Key 或执行 V2 held-out。

### 2026-08-15：DeepSeek V4 Pro V2 真实门单次执行

用户明确确认后，在 HEAD/origin 均为
`741e84140f816fb4b06b2812a8d07d3f32eaf4d0`、工作树干净、GitHub Actions run
`31863519248` completed/success、结果路径不存在且治理通过的条件下，只执行一次 V2
三案例 CLI。

- 首个正常案例实际调用 1 次，得到 1 个规范化响应，Usage 为 3241 input + 199 output，
  latency 12125 ms、估算 `$0.00506616`；
- 下一轮调用需预留 1024 output tokens，而单例已观察 3440 tokens，因
  `3440 + 1024 > 4000` 在 Provider I/O 前以 `token_budget_exhausted` 停止；
- Agent 终态为 `failed/provider_error`，Harness 终态为
  `degraded/draft_preparation_failed`，只返回确定性 fallback；unsafe publication 为
  false；
- 用户注入与知识注入两例按首错停止 skipped，没有新增外部调用；
- 新鲜领域总计 1 call/3440 tokens/`$0.00506616`；本记录连同既有 3-call 协议为
  4 calls/4868 tokens/`$0.00728112`。更早的旧领域失败调用仍由历史证据单独计数，
  Token/费用保持 unknown；
- 结果文件 SHA-256 为
  `877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a`，严格合同、
  运行确认、首错停止和脱敏边界已由 `47 passed` 聚焦回归固定；完整回归为
  `581 passed, 103 subtests passed`，两套 RAG、compileall、Harness SDK/tracked-data
  boundary、dry-run 与治理均通过；V2 不得覆盖或重跑。
- 结果、回归和教学裁决已由提交
  `60b5c86e1699a615a6bf87dcbb5be62506b2e2e0` 推送；GitHub Actions run
  `31864370988` 对该精确 SHA completed/success。CI 无 `.env`/Key，也没有 Provider
  调用。

这次结果正确支持 `admitted=false`，并证明预算与安全控制生效；但由于事实、引用、注入
和 Evaluation 链均未完成，不能归纳为 DeepSeek 报告质量失败。它同时暴露了实验设计
Bad Case：Fake Provider 的小 Usage 没有证明真实 Prompt 下“4 calls/4000 tokens”控制流
可达。当时下一步仍在 5D-7 内，先做零调用的结果裁决与真实长度预算可达性 TDD；不得
直接调高预算重跑 V2、调用其他模型或进入 5D exit review/5E。

### 2026-08-15：5D-7 收尾审查

原始 5D-7 设计将最终 review 定义为评测合同、Prompt/Context 身份、控制流、安全门、
资源和采用决策的证据审查，而不是要求某个真实 Provider 必须通过。当前分层
Dataset/Candidate/Result、development/held-out 生命周期、Evaluation 1.1、已知注入阻断、
资源预算、双层安全错误 provenance 与不可变真实负面结果均已有证据。

ADR-0028 因此接受 5D-7 完成，同时保留当前无领域 Provider 准入：GLM-5.2 仅为开发
基线，DeepSeek 领域质量 unknown，GLM-5.3 G53 deferred，Flash 未测试。相关聚焦回归为
`130 passed, 4 subtests passed`，完整本地回归为 `616 passed, 103 subtests passed`；
两套 RAG 1.0 门禁、compileall、Harness SDK/tracked-data boundary、dry-run、治理和差异
检查均通过，本审查外部调用为 0。下一检查点为
`5D-exit-review`；它必须继续核对两个 Skill、真实模型/注入/性能限制和 5E 前置项，不能
把 5D-7 完成解释为生产模型报告质量已经通过。

审查提交 `7c8f4e7344ac3ecc0fa22885c7ebd2109a17d383` 随后通过 GitHub Actions run
`31876536179` 的 exact-SHA 公共 CI。5D-7 至此正式闭环；该公共验证没有调用 Provider，
也没有改变当前无领域 Provider 准入的结论。

### 2026-08-15：5D 退出审查

退出审查逐项核对 5D 入口设计的十项功能要求、可靠性/安全性/预算/可测试性/框架中立
等非功能要求，以及 5E 的输入前置。核心执行与 Provider/实验两组跨层离线回归分别为
`173 passed, 34 subtests passed` 和 `176 passed, 22 subtests passed`。

审查未发现必须留在 5D 修复的结构性代码缺口：两个真实 Skill 都能在 Fake Provider、
实际本地 `knowledge.search`、AgentLoop、ToolRuntime 与唯一 ReviewHarness 的组合下形成
类型化终态；非法输出、越权、预算、上下文、Provider 和安全评测失败均不能绕过发布门。
真实 Provider 领域质量仍未准入并保持 unknown，这是一项明确产品限制，而不是 5D 控制
架构的阻塞条件。

因此 5D 状态改为已完成，阶段 5 继续进行中，唯一下一检查点为 `5E AgentRuntime V1`
入口设计。5E 将统一现有 run_id、事件、Trace、Usage 和安全终止原因；它不得自动调用
Provider、切换模型、接入 LangGraph/Agent SDK 或提前进入 5P/5F。退出审查提交
`2f4e4d40f00cf6a14b7c9c0f85e8d3cbdc8c2493` 已通过 GitHub Actions run
`31877076222` 的 exact-SHA 公共 CI；5D 的本地与公开退出证据均已闭环。

### 2026-08-18：6A-4 exact-SHA 公共闭环与 6A-5 交接

提交 `41ac9c1fab5f6aa3053ca78a2e8f314e95aa0f2c` 已推送并由 GitHub Actions run
`32102522662` 完成 exact-SHA 公共验证；`pytest` job 与 `postgres-migrations` job 均
completed/success。公开 `pytest` 为 `1033 passed, 20 skipped, 1 warning, 110 subtests
passed`；真实 PostgreSQL 17 job 执行 6 个数据库测试文件并得到 `40 passed`，包含本轮
5 项 reconciliation/产品纵向测试。治理、两套 RAG、compileall、Harness dry-run、SDK/秘密
边界和 migration head 检查均通过，CI 无 `.env`、Key、Riot/Provider 调用。

因此 `6A-4-application-artifact-integration` 正式完成。它证明 SQL task 的 `run_id` 能安全
贯穿现有 Application/Runtime/Artifact，完整 receipt/Trace/final Artifact 证据能形成 succeeded
投影；没有终态证据时只报告 `recovery_required`，人工恢复通过 worker-matching CAS，不能自动
判死、重跑或 reclaim。它不证明 lease/heartbeat、自动恢复、异步 HTTP、Session/Memory 或公网
部署已经完成。

上述条目记录的是 6A-4 完成时的历史交接；随后 RQ-057 已授权并进入下方 6A-5 执行状态。

## 2026-08-18：6A-5 当前本地证据与下一动作

- RQ-057 已授权；6A-5 本地实现包括 V2 POST 202 task receipt、幂等 replay/conflict、安全错误映射、
  owner-scoped task/run/report、trusted ActorContext、production fail-closed、FastAPI lifespan、惰性
  Engine/Session composition、liveness 与 PostgreSQL/Alembic readiness。
- 本地证据：API 聚焦 `38 passed, 1 skipped`；完整 `1047 passed, 21 skipped, 1 warning, 110 subtests
  passed`；两套 RAG 均为 Recall/MRR/nDCG 1.0，holdout abstention/citation 1.0；compileall、Harness
  dry-run、governance、tracked Secret/run-data、SDK/YAML/diff 门均通过。
- 本机限制：无 PostgreSQL；新增 `tests/test_async_task_api_postgres.py` 的真实 create/replay/owner/
  readiness 证据尚未本地执行，已纳入 `.github/workflows/tests.yml` 的阻塞 `postgres-migrations` job。
- 真实 Worker 的 Riot/Data Dragon/Provider 进程组合仍 fail-closed，按范围裁决留给 6A-7 packaging；本批
  未读取 Key、未调用 Riot/Provider、未进入 6A-6。
- 唯一下一动作：检查 diff 与持久状态后提交/推送，等待 exact-SHA `pytest` 与 PostgreSQL CI；CI 成功后
  才把 6A-5 标为 complete 并交接 6A-6。

## 2026-08-18：6A-5 exact-SHA 公共闭环与 6A-6 交接

- 实现提交 `2492951c20dd6ca897d957d03752b6a2585ce469` 已推送；GitHub Actions run
  `32106378542` 的 `pytest` 与 `postgres-migrations` 均 completed/success。
- 公共完整 pytest 为 `1047 passed, 21 skipped, 1 warning, 110 subtests passed`；PostgreSQL 17 job
  明确包含 `tests/test_async_task_api_postgres.py` 并得到 `41 passed, 1 warning`，真实验证 API create/
  replay、owner 隔离、queued run/report 409 与 current Alembic readiness。
- 两套 RAG、compileall、Harness dry-run、governance、tracked Secret/run-data、SDK boundary 与 migration
  metadata head 均通过；CI 无 `.env`/Key，也没有 Riot/Provider 调用。
- 因此 6A-5 正式完成：HTTP 可以可靠入队并查询 task/run/report，API process lifecycle 与 health 已闭环。
  这不表示 Worker external composition、正式 Auth、Session/Memory、SSE、前端或公网部署已经完成。
- canonical 只交接 `6A-6-security-lifecycle-nfr` 准备状态，等待用户明确继续；不得自动开始 6A-6。

## 2026-08-18：6A-6 Security/Lifecycle/NFR 开始

- RQ-058 已记录；用户明确“继续下一步”，解除 6A-6 等待确认，本轮状态改为实施中。
- 目标是把已冻结的 task 基座边界变成可运行、可测试的最小实现：默认关闭 CORS，日志与 Secret
  脱敏，owner/global 背压，7/90/30 天 retention，terminal delete 的立即隐藏与幂等补偿，active
  delete conflict，allowlisted metrics/log metadata，以及 warm-DB create/query 与 claim 延迟基线。
- 先写红灯测试，再写实现；Retention 使用 injected clock，跨 SQL/Artifact 删除使用安全的
  hidden-before-cleanup 语义。真实 PostgreSQL 并发、删除与性能证据由阻塞 CI 提供，本机无 DB 时明确 skip。
- 本轮不读取 `.env`/API Key，不调用 Riot、Data Dragon、GLM、DeepSeek 或其他 Provider，不实现正式
  Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume，也不进入 6A-7。
- 本地实现已完成：新增 retention/deletion/observability 合同与 purge CLI；API 接入 CORS、容量配置、
  DELETE hidden-before-cleanup 投影；Repository 增加 terminal/expired 删除短事务；Worker 接入安全
  claim/terminal 指标；新增纯逻辑与 PostgreSQL 生命周期/性能测试。
- 本地聚焦 `30 passed, 6 skipped`；完整回归 `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；
  两套 RAG、compileall、Harness dry-run、秘密/SDK/YAML/diff 与 governance 门禁通过。本机无 PostgreSQL，
  真实容量 race、删除和性能样本尚未执行。
- 下一动作是提交/推送并等待 exact-SHA `pytest` 与 PostgreSQL CI；CI 成功前不关闭 6A-6。
- 首个实现提交 `fecbb11` / Actions `32137687527` 的两个 job 均成功；完整 pytest 为
  `1077 passed, 27 skipped, 1 warning, 110 subtests passed`，真实 PostgreSQL 为 `51 passed`。但成功
  日志未记录 actual p95/sample/environment，claim 采样语义也偏向单次 SQL 调用；当前已做 evidence-only
  修补并等待新的 exact-SHA CI，因此仍不关闭 6A-6。

## 2026-08-18：6A-6 exact-SHA 公共闭环与 6A-7 交接

- 性能证据修补提交 `31d5e6038943bd3eacbeb485300f63ad53e13bfd` 已推送；Actions run
  `32138025724` 的 `pytest` 与 `postgres-migrations` 均 completed/success。
- 公共完整 pytest 为 `1077 passed, 27 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  job 为 `51 passed, 1 warning`，明确执行 lifecycle/capacity/performance 文件。
- PostgreSQL 17 / Python 3.11 环境记录了 8 个 warm create+query 样本，p95 `6.220ms`（目标
  `<300ms`）；8 个 queued→claim 样本，p95 `23.359ms`（目标 `<2000ms`）。这些只证明 task
  控制面基线，不代表 Agent/Provider 质量或公网 SLA。
- 因此 6A-6/RQ-058 正式完成：默认 CORS、日志/Secret allowlist、背压、7/90/30 retention、terminal
  hidden-before-cleanup 与补偿、active delete conflict、结构化 observability 和真实性能证据均闭环。
- canonical 只交接 `6A-7-packaging-exit-review` 准备状态，等待用户明确继续；不得自动开始 6A-7。

## 2026-08-18：6A-7 Packaging & Exit Review 开始

- RQ-059 已记录；用户明确“继续吧”，解除 `6A-7-packaging-exit-review` 的等待确认。
- 本轮只建立可重建 API+Worker+PostgreSQL package、配置/启动命令、Linux no-I/O smoke，以及逐条绑定
  ADR-0038/6A 设计承诺的 exit matrix/review。先写红灯合同，再做最小实现。
- 真实 Worker composition 必须在读取或 claim 前完整校验数据库、Riot、Provider 与产品依赖；配置缺失
  安全失败。CI/smoke 不读取真实 Key、不调用 Riot、Data Dragon 或 Provider。
- 本轮不实现正式 Auth/HTTPS、Session/Memory、SSE、前端、lease/heartbeat/reclaim/cancel/resume、
  直接公网部署、LangGraph、Multi-Agent、MCP 或新 SDK。exact-SHA 公共 CI 成功前不关闭 6A。

## 2026-08-18：6A-7 本地实现与退出门完成

- production Worker composition、CLI `--check/--once`、非 root Dockerfile、严格 `.dockerignore`、
  migration/API/runtime-worker/no-I/O-smoke Compose、Linux blocking job 与启动/安全说明已实现。
- 人工审查补强了两个边界：无效 `worker_id` 在 Engine/网络构造前拒绝；smoke 使用隔离 Compose
  project/data volumes，并以 `up --wait api` 后 one-off `run --no-deps smoke` 执行，避免正常 migration
  退出提前终止以及诊断 Worker 误领普通本地任务。
- 本地聚焦 `48 passed, 1 warning`；完整 `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；
  两套 RAG 满门槛、Harness dry-run `published`/0 revisions、compileall 与安全边界通过。27 个 skip 和
  Docker/Compose 运行不能在本机冒充成功，必须由 exact-SHA PostgreSQL/Linux CI 补齐。
- 在首个公共 run 前，本地退出裁决保持 `keep-open-pending-exact-sha-linux-ci`；当时最终
  YAML/diff/governance/security 快照已通过，下一动作是提交推送并等待三个同 SHA job。

## 2026-08-18：首个 6A-7 公共 run 部分失败与受限诊断

- 提交 `b0f61caa6b6cb52eb753c6c5493ae51bbe58a600` 的 Actions run `32145005904` 已完成：pytest
  `1100 passed, 27 skipped, 1 warning, 110 subtests passed`、RAG/Harness/安全门成功；真实 PostgreSQL
  `51 passed, 1 warning` 成功。
- packaging job 已成功完成 Compose config、非 root image build、PostgreSQL、migration 与 API ready；
  one-off no-I/O smoke 返回 `packaging_smoke_worker_failed`，image boundary step 因此前失败未执行。
- 由于首版错误码把 DB/claim/CAS/query 多层压成同一值，当前未凭猜测改业务逻辑；已本地 TDD 增加
  body-free allowlisted 分层码，并在 failure 时只输出 bounded API/PostgreSQL logs。聚焦 `48 passed`、
  完整 `1102 passed, 27 skipped, 110 subtests passed`。
- 在该诊断检查点，6A 正确保留 `in_progress`；当时下一动作是提交诊断修补并等待新 exact-SHA 三 job，
  以真实 stage code 决定是否还需产品修复。

## 2026-08-18：第二个 6A-7 run 定位 Alembic import-root

- 诊断提交 `d8c5063f8e21af02a35450812fa20b47c6e21f53` / Actions `32146113582` 的 pytest、真实
  PostgreSQL、image build、migration 与 API ready 均成功；one-off 输出精确为
  `packaging_smoke_database_not_ready`，bounded logs 显示同一 API 已对同 DB readiness 200 且 POST 202。
- 根因不是 PostgreSQL 或 migration：API 以模块入口从 `/opt/riftcoach/app` 导入，能用工作目录下
  `alembic.ini`；`python scripts/run_packaging_smoke.py` 把 `scripts/` 放在 `sys.path[0]`，优先导入已安装
  wheel 中的 `app`，其 `PROJECT_ROOT` 不含镜像的 Alembic 文件。真实 Worker 同样存在该启动风险。
- 已用红灯合同要求两条 Compose 命令都使用 `python -m scripts.<module>`，随后最小修改 Worker/smoke
  command；聚焦 48 项与两个 module `--help` 入口通过。未放宽 readiness、复制 migration 或改 DB 语义。
- 在该根因检查点，当时下一动作是完成横向门、提交 module-entry 修复并等待新 exact-SHA 三 job。

## 2026-08-18：6A-7/6A exact-SHA 公共闭环

- module-entry 修复提交 `adf53e56d1eb624746b493ad8b281598c9a0dd32` 的 Actions run
  `32146760003` 三 job 全部 completed/success：pytest `1102 passed, 27 skipped, 1 warning,
  110 subtests passed`；真实 PostgreSQL `51 passed, 1 warning`；packaging-smoke 完整成功。
- Linux smoke 的安全输出为 `task_status=failed`、`external_riot_provider_calls=0`：它真实覆盖 HTTP 202、
  PostgreSQL claim、安全 failure terminal 与 HTTP query；随后 image boundary 确认非 root，且镜像不含
  `.env`、tests、cache/runs、reports、tmp。
- 6A 退出裁决为 `close-with-deferred-boundaries`：持久异步 task API 基座与可重建 package 已完成；
  Session/Memory、正式 Auth/HTTPS、SSE/前端、lease/reclaim/cancel/resume、备份/SLA 和真实模型领域质量
  继续 deferred。
- `6A-7-packaging-exit-review` 与整个 6A 正式完成。canonical 只交接
  `stage-6-session-memory-entry-design` 准备状态，等待用户明确继续，不自动实施。

## 2026-08-19：Session/Memory 入口设计获授权

- 6A 状态收尾提交 `d1cc2ed4e021a2fa14ed477d17f00e18578eebb2` 已推送；Actions
  `32147545753` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均成功。这补齐状态提交
  自身的公共证据，不改变 `adf53e5` 作为 6A module-entry/package 实现证据的角色。
- 用户“继下一步”构成 RQ-060，解除 `stage-6-session-memory-entry-design` 的等待授权状态。
- 本检查点只审计现有 owner/task/run/API、EchoMind/Saber 可迁移思想与缺陷，并逐节确认概念边界、
  数据模型、写入/更正/导出/过期/删除、隔离、隐私/NFR/测试和后续原子实施顺序。
- 当前没有 Session/Memory 产品代码；不复制 EchoMind Redis/Chroma，不把 RAG 或原始比赛事实当 Memory，
  不自动引入向量库/LangGraph，也不提前进入 Auth/SSE/前端、阶段 7 或阶段 8。

## 2026-08-19：RQ-061 外服账号认领边界

- Riot 官方 LoL routing values 当前没有中国大陆 CN；`ASIA` 是包含 KR/JP 等平台的区域路由，不等于
  中国大陆服务器支持，`zh_CN` Data Dragon 本地化也不是服务器路由。
- Riot ID→PUUID 只解析可查询账号主体，不证明应用 owner 控制账号。当前只能形成未验证 self claim。
- future verified 必须同时经过正式 RiftCoach Auth、安全绑定到该 owner 的 RSO OAuth/OIDC callback，
  并让 `/accounts/me` PUUID 与 subject 精确匹配；当前没有这条产品路径。
- 该条记录当时仍待 `public_observed` 裁决；后续 RQ-062 已确认采用。本次修正没有创建表、接口或
  RSO/Auth 代码。

## 2026-08-19：RQ-062 外服玩家关系策略确认

- MVP 同时支持 `self + unverified_claim → claimed_self` 与
  `observed + not_applicable → public_observed`；role 与 verification 不混成单一含糊枚举。
- claimed-self 可形成 owner-player 训练目标/计划/进度但必须显示未验证；public-observed 只允许公开分析、
  owner-local 观察备注/趋势和第三人称语义，不生成被观察者的私人偏好或训练完成度。
- future `self + rso_verified → verified_self` 当前无创建路径；任一关系不增加 Riot 权限，不跨 owner
  合并私人数据。
- 下一步仍在同一 entry-design 内，只确认 conversation 固定/切换与 task 继承；没有实现产品代码。

## 2026-08-19：RQ-063 Conversation 固定玩家确认

- Conversation 创建时属于 trusted owner 并固定引用该 owner 的一个 player subject；V1 不提供中途切换，
  不同 PUUID 必须新建 conversation，相同 PUUID 的 Riot ID 改名可继续。
- 消息、Context、task/run 和 Memory Candidate 继承服务器保存的 owner/conversation/subject；client body、
  自由文本或模型均不能覆盖，未来以应用校验和 PostgreSQL owner-scoped composite constraints 双层强制。
- 当前异步入队只有 Riot ID，Worker 内才解析 PUUID；下一设计门先裁决 subject/link/conversation bootstrap
  顺序。没有创建 schema、migration、Repository、API 或外部调用。

## 2026-08-19：RQ-064 与 Session/Memory 设计本地冻结

- RQ-064 取代 RQ-060 当时的“设计后另行授权”暂停门，但自动范围严格止于三个独立批次：entry design、
  6B-1、6B-2；6B-2 exact-SHA 全绿后只把 6B-3 置为 prepared/waiting authorization。
- 三案裁决采用独立异步 Player Link：API 先持久化 bounded Riot ID link intent，专用 Worker 在事务外调用
  Account-V1，随后以一个 PostgreSQL 短事务收敛 subject、alias、owner relationship 和 link terminal；
  link 成功后才能创建 Conversation。首个 Review 内 bootstrap 与 API 同步 lookup 被拒绝。
- Memory 采用“关系型身份/状态骨架 + 分类型长期记录 + 严格 JSONB 叶子 + Candidate write gate”；模型或
  自然语言提取不能直接永久写入，PostgreSQL 是唯一真源，Redis/向量索引仍需真实 Bad Case 才评估。
- ADR-0039、`docs/plans/2026-08-19-stage6-session-memory-design.md` 与
  `docs/plans/2026-08-19-stage6-session-memory-implementation.md` 已在本地创建，并按 6B-1 至 6B-9 冻结
  全阶段顺序；本次自动实施仍只覆盖 6B-1/6B-2。
- 当前只完成本地设计内容，尚未提交、推送或取得 exact-SHA CI，也没有创建 migration/schema、读取 Key、
  调用 Riot/Provider。本地完整回归为 `1102 passed, 27 skipped, 1 warning, 110 subtests passed`；两套 RAG
  均满阈值，Harness dry-run `published`/0 revisions，compileall、SDK/Secret/run-data、YAML、governance 与
  diff 门均通过。27 个 skip 不冒充真实 PostgreSQL/Docker 成功；下一动作是设计批独立提交/推送和
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 公共闭环，全绿前不进入 6B-1。

## 2026-08-19：Session/Memory entry design exact-SHA 公共闭环

- 设计提交 `bc11afe9f2f85a39f05b7f3d6135b14821ebb17d` 已推送；GitHub Actions run
  `32222531783` 总状态 success，精确对应的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均成功，公开页面显示 workflow 总耗时 1m07s。
- 入口设计退出条件全部满足：RQ/ADR/design/implementation/canonical 一致，本地 1102 tests/两套 RAG/
  Harness/安全门通过，真库与 Linux package 又由同 SHA 补齐；设计批外部 Riot/Provider 调用为 0。
- `stage-6-session-memory-entry-design` 正式关闭，但这只证明设计可审计且旧系统未回归，不表示四张 Player
  表、Repository、Worker、Conversation 或 Memory 已实现。
- 按 RQ-064，canonical 进入 `6B-1-player-identity-link-foundation`；本批先做严格 domain 合同与持久身份
  地基，不实现 6B-2 的 Resolver/Worker/API，也不读取 Key 或调用外部服务。

## 2026-08-19：RQ-065 与 6B-1 本地实现门

- 用户用 RQ-065 将本轮停止点收紧为 6B-1 公共闭环；6B-2 不再自动实施，完成后只准备并等待下一轮授权。
- 已建立 strict Player/Relationship/Link Task domain、Riot ID normalization/fingerprint、public body-free View、
  allowlisted failure、Service/Port、四张 PostgreSQL ORM 表、可逆 Alembic 0002 与事务 Repository。
- Repository 覆盖 owner-scoped create/replay/conflict/capacity、deterministic `FOR UPDATE SKIP LOCKED` claim、
  stale-worker CAS、PUUID/alias/relationship `ON CONFLICT` 收敛、同 PUUID 并发和整事务回滚；角色冲突在
  `resolve_link()` 同一事务写 `failed/relationship_role_conflict`，不写 alias、不修改 relationship。
- pure domain 红灯曾为 `ModuleNotFoundError: app.players`；Repository 红灯曾为
  `ModuleNotFoundError: app.persistence.player_repository`。当前 6B-1 聚焦为 `17 passed, 13 skipped`，相邻为
  `35 passed, 28 skipped`，完整为 `1119 passed, 40 skipped, 1 warning, 110 subtests passed`。skip 全因本机
  无 PostgreSQL，不能冒充真库成功。
- 两套 RAG 均满阈值，Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/
  run-data、YAML、governance、diff 与 Alembic offline SQL 编译通过。离线编译曾抓到两个超过 PostgreSQL
  63 字符的 constraint 名并已同步修复；本批外部 Riot/Provider/Key I/O 为 0。
- 实现提交 `656117a` 的首个公共 run `32227457202` 未通过：PostgreSQL 与 packaging 共同暴露 35 字符
  Alembic revision 无法写入默认 32 字符 version column；该缺口已由新增红灯固定并缩短 revision 修补。
- revision 修补 `b8fa2e3` / Actions `32227937252` 已使 pytest、packaging 和 reversible migration 通过；
  真库 67 项仅剩一个 CHECK 名断言失败。日志证明完整 CHECK 名被 naming convention 二次前缀后截断；现已
  用 offline SQL 红灯和全部 CHECK `op.f(...)` 修补，不放宽稳定 schema 名称合同。
- 在第三个公共 run 前仍是 `6B-1-player-identity-link-foundation / in_progress`；该临时状态已由下方
  `ed8fa58/32229024069` 公共闭环取代。

## 2026-08-19：6B-1 exact-SHA 公共闭环并按 RQ-065 停止

- 最终修补提交 `ed8fa58ff3f9ef6c84e1a028ac0e1724b087a26b` 对应 Actions `32229024069`，总状态
  completed/success；`pytest`、真实 `postgres-migrations` 与 Linux `packaging-smoke` 三 job 均成功。
- 6B-1 正式完成：严格 Player/Relationship/Link Task 合同、四张表、可逆 0002、事务 Repository、
  幂等/容量、SKIP LOCKED、PUUID/alias/relationship 收敛、role-conflict 单事务失败、CAS/rollback 与
  confirmed display snapshot 均已有本地和真实 PostgreSQL 证据。
- 本批没有实现 Resolver、PlayerLinkWorker、HTTP API、Conversation/Memory、Auth/RSO 或外部 Riot/
  Provider I/O；成功证据不能外推到这些边界。
- RQ-065 的本轮目标已经满足。canonical 现为 `6B-2-async-player-link-worker-api / pending`，只表示下一批
  设计已准备，等待下一轮用户明确授权；本轮停止，不实施 6B-2。

## 2026-08-19：RQ-066 恢复 6B-2

- 用户在独立的新一轮明确“继续开工”，随后恢复真实仓库写权限；RQ-066 解除 6B-2 的 waiting 状态，
  但授权严格止于本批，6B-3 不在范围内。
- 已完成初学者入口教学与既有 ADR/design/implementation plan 复核：API 只持久化意图并返回 202，
  PlayerLinkWorker 在 claim 已提交后、数据库事务外调用 Account-V1，Resolver 只返回严格 account 或
  allowlisted failure，Repository 再用短事务提交身份关系/终态。
- 当前先执行 Task 1 Resolver TDD；开发/测试/CI 使用 Fake client/resolver，真实 Riot/Provider/Key I/O
  保持 0。不实现 Conversation/Message/Memory、Review Task subject binding、自动 retry/reclaim、
  verified-self/Auth/RSO、SSE/前端或新框架。

## 2026-08-19：6B-2 Tasks 1–4 本地完成，等待公共闭环

- Task 1 已完成：`RiotAccountResolver` 通过注入 Fake client/factory 做严格 Account-V1 响应校验，
  将 404、认证失败、429、timeout、连接/其他上游错误和坏响应映射为 allowlisted body-free failure；
  构造与 API composition 不读取 Key 或发起网络请求。
- Task 2 已完成：`PlayerLinkWorker` 使用 claim 短事务提交→事务外 Resolver→终态 CAS 短事务，覆盖安全
  失败、坏结果、role conflict、ownership loss、终态异常、退避轮询与 graceful stop；不实现自动 retry、
  lease、reclaim 或 recovery。
- Task 3 已完成：`POST /player-links` 与 `GET /player-links/{link_task_id}` 使用 trusted ActorContext、
  owner-scoped service、202/replay/409/404/503 投影和 PUUID-free DTO；API composition 只构造 PostgreSQL
  Repository/Service，不构造 Riot Client/Resolver。真实 PostgreSQL API 测试已加入阻塞 CI，本机因无 DB 明确 skip。
- Task 4 已完成：独立 `player-link-worker` Compose service、`--check/--once` CLI、完整配置/DB readiness
  fail-closed 与 Fake Resolver packaging smoke 已接入。routing policy 要求完整覆盖四个官方 regional
  values，避免 API 可入队但 Worker 永远拒绝；smoke 使用固定安全 worker ID，避免拼接越界。
- 本地证据：6B-2 聚焦/相邻 `149 passed, 2 skipped, 1 warning`；完整 `1216 passed, 42 skipped, 1 warning,
  110 subtests passed`；RAG development/holdout 均 Recall/MRR/nDCG `1.0`，holdout abstention/citation
  `1.0`；Harness dry-run `published`/0 revisions；compileall、YAML、SDK boundary、tracked Secret/run-data、
  governance 与 `git diff --check` 均通过。42 个 skip 仅因本机没有 PostgreSQL/Docker，不能冒充真库/package 证据。
- 本批开发、测试和本地 smoke 的 Riot/Provider/Key I/O 为 0；真实 Riot 调用仍只存在于生产 Worker composition，
  不得把 Fake Resolver smoke 描述为外部 API 成功。
- 当前唯一下一动作是提交/推送本批并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`；
  在三 job 全绿前保持 `6B-2 / in_progress`，不得把 6B-2 标为 complete。公共闭环后只把 6B-3 标为
  prepared/waiting authorization，不实施 Conversation/Memory。

## 2026-08-20：6B-2 exact-SHA 公共闭环并按 RQ-066 停止

- 实现提交 `0c13a583ea51a7c18301fc29bf5c2931790d6693` 已推送；Actions run `32301852042`
  精确对应该 SHA，workflow 与 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。
- 公共 `pytest` 为 `1216 passed, 42 skipped, 1 warning, 110 subtests passed`；两套 RAG 指标满门槛，
  Harness dry-run 为 `published`/0 revisions。真实 PostgreSQL 17 job 为 `70 passed, 1 warning`，并通过
  可逆 migration 与 metadata-head 一致性。
- Linux package smoke 真实输出 `task_status=failed`、`link_status=succeeded`、
  `external_riot_provider_calls=0`；这证明 Review Task 安全失败路径与 Fake Resolver Player Link 成功路径
  可在可重建 package 中共同运行，不证明真实 Riot Key、账号归属或 Provider 质量。
- 6B-2 正式完成：窄 Account Resolver、专用 PlayerLinkWorker、owner-scoped Link API、composition/CLI、
  PostgreSQL API integration 与 Linux no-I/O smoke 已闭环。未实现 Conversation/Message/Memory、Review
  Task subject binding、自动 retry/reclaim、verified-self/Auth/RSO、SSE/前端或真实 Riot/Provider 调用。
- RQ-066 的授权目标已经满足。canonical 现只把 `6B-3-conversation-message-foundation` 标为
  prepared/waiting authorization；本轮停止，不创建 Conversation、Message 或 Memory 代码。

## 2026-08-20：RQ-067 持久教学/工程说明补齐前置门

- 用户要求重新确认缺口是否确实从 6B 才开始，并从阶段 0 起以统一标准审计；不能用文件数量、聊天长度、
  canonical 或 progress 中“已讲过”的一句话替代可独立复习的成品。
- 补齐范围包含全部已识别材料，而非仅初学者文章：设计/实现复盘、实际代码地图、数据流与控制流、事务/
  失败/安全边界、需求→源码→测试→CI→限制证据矩阵、运行示例、面试安全表述、README/学习索引，及
  AGENTS/治理防复发门。
- 采用覆盖矩阵驱动的混合方案：充分材料链接复用，真实缺口新增 walkthrough/implementation review；
  不按文件数量重复已有内容，也不以一篇笼统总览掩盖原子子阶段缺口。
- 当前仍以 `6B-3-conversation-message-foundation` 作为唯一产品检查点，但它受本横向文档门阻塞；补齐批
  独立通过治理、比例回归、提交/推送和 exact-SHA 公共 CI 后，RQ-067 允许无需再次确认直接进入 6B-3。
  文档门闭环前不创建 Conversation/Message schema、migration、Repository、API 或产品测试。

## RQ-067 本地退出复核（公共验证前）

- 新增整体退出复核 `docs/plans/2026-08-20-learning-engineering-documentation-backfill-exit-review.md`；覆盖账本登记 17 组，当前 6B-3 为 `planned`，所有前序组为 `complete`。
- 本地聚焦：治理 `10 passed`；Agent Loop/Skill `34 passed`；Provider/Tool `101 passed, 68 subtests`；领域/RAG 代表性集合 `37 passed`。
- 完整回归：`1224 passed, 42 skipped, 1 warning, 110 subtests passed`。两套 RAG、Harness dry-run、compileall、secret/tracked-data、SDK boundary、Markdown/YAML/link 与 diff 门均通过。
- 本地裁决：`pass-local-pending-public-ci`。42 个 skip 仍仅因本机无 PostgreSQL/Docker；尚未提交/推送本批，不能把文档闭环写成公共完成。

## 2026-08-20：RQ-067 文档门公共闭环，进入 6B-3

- 文档/工程证据提交 `63435d90f5153309fce98b92a2ff58425d54a684` 已推送；GitHub Actions run `32308631289` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success`。
- 这次公共验证补齐了文档批的治理、完整回归、真实 PostgreSQL migration/metadata 复核和 Linux package 边界；它不把本地 42 个 PostgreSQL/Docker skip 改写为本地真库证据，也不表示 6B-3 功能已完成。
- RQ-067 前置门正式关闭，`docs/learning/coverage.yaml` 的 Q11/complete 证据获得公共 CI 支持；canonical 现在正式进入 `6B-3-conversation-message-foundation` 的初学者设计复核与 TDD。
- 当前仍没有 Conversation/Message/Memory 产品代码；下一批先讲并冻结 6B-3 的 owner/relationship/subject 绑定、消息角色/长度、并发序号、归档/隐藏和 owner-scoped 查询合同，再写红灯测试。

## 2026-08-20：6B-3 设计冻结与红灯交接

- 6B-3 接缝审计确认可复用现有 SQLAlchemy Base、Player relationship 复合 identity、短事务
  Repository、FastAPI Port/proxy/lifespan 与 PostgreSQL CI；没有采用参考项目或新框架。
- ADR-0040 与 `docs/plans/2026-08-20-conversation-message-foundation-design.md` 已冻结：active
  relationship 必须在同一短事务锁定检查；Conversation 创建采用 owner-scoped Idempotency-Key；
  公共 API 只允许 user Message；序号从 1 开始由 Conversation 行锁分配；archived/hidden 语义分离；
  binding trigger 防 direct SQL rebind；source task/run 不设阻塞性强 FK。
- 为防止持久覆盖账本被“重排并重编号”绕过，治理脚本增加固定 canonical group order，coverage YAML
  增加并校验人类可读镜像，回归测试当前为 `12 passed`；README 前置条件和日期审计无须额外修补。
- 当前代码事实仍是“没有 Conversation/Message schema、migration、Repository、API 或产品测试”；
  设计文件不算实现证据。本地完整回归为 `1226 passed, 42 skipped, 1 warning, 110 subtests passed`；
  RAG development/holdout、Harness dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff
  门均通过。下一动作是设计批独立提交/推送和 exact-SHA 三 job；全绿后才进入红灯与最小实现。

## 2026-08-20：6B-3 设计批公共闭环，进入红灯合同

- 设计/治理提交 `b6a7112d9c3fa8744b9713737bbbf54fe5011084` 已推送；Actions run
  `32313707301` 精确对应同一 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。
- 这次公共证据证明 ADR/design/governance 与既有真库/package 边界兼容，不证明 Conversation/Message
  产品代码已经存在，也不证明 Agent、Review 或 Memory 接入。
- canonical 保持同一 6B-3 checkpoint，但内部从“设计门”转入“红灯→最小实现”；第一批先冻结 pure
  model/Service/API 合同，随后才实现 PostgreSQL schema/Repository/并发与 API composition。

## 2026-08-20：6B-3 本地实现、审查修复与公共验证前状态

- Conversation/Message strict domain、Port/Service、SQLAlchemy metadata、可逆 Alembic 0003、事务
  Repository、六个 HTTP endpoint、lifespan composition、Linux no-I/O package 纵向与 pure/API/真库/
  并发测试已在工作树建立；没有接 Agent、Review Task 2.0、Memory、Auth、SSE、前端或新框架。
- scoped advisory lock 只串行同 `owner_id + idempotency_key`；Service 又防御 CREATED 投影伪造服务器
  conversation ID/active 初态；assistant 数据合同必须有 `source_run_id`，公共 API 仍只能写 user。
- 最终只读审查未发现 P0/P1，修复两项 P2：archive/hide 的 OpenAPI 422 现在与实际
  `ConversationErrorResponse` 一致；有效 command 之后的 UUID factory/clock 故障按服务器 503，而非误报
  客户端 422。对应红灯为 `5 failed, 35 passed`，最小修复后为 `40 passed`。
- 原 lifecycle/append Barrier 测试被确定性调度取代：blocker 先锁 Conversation，事件确认第一操作已持
  relationship、第二操作已尝试相同 relationship 锁，再释放 blocker；archive/hide 各自证明 append-first
  与 lifecycle-first。该真库测试本机因无 PostgreSQL 明确 skip，只能由阻塞 CI 补证。
- 新增干净 Python 子进程 import/OpenAPI no-I/O 测试；`docs/learning/6b-3-conversation-message-foundation-
  walkthrough.md` 已补齐八维材料，coverage evidence 路径已完整但在公共三 job 全绿前保持 `planned`。
- 当前仍未提交/推送实现批，也没有该实现 exact-SHA 的 PostgreSQL/package 公共证据。唯一下一动作是完成
  全部本地门禁与最终 diff，随后提交/推送并等待三个同 SHA job；全绿后再用独立状态批关闭 6B-3，只把
  6B-4 标为 prepared/waiting authorization，不实施 6B-4。

## 2026-08-20：6B-3 本地实现收尾与公共验证前复核

- 已完成 6B-3 实现批的聚焦与完整复核：聚焦 `85 passed, 25 skipped`；完整
  `1295 passed, 67 skipped, 1 warning, 110 subtests passed`。本机 skip 全部是没有 PostgreSQL/Docker，
  仍不替代公共真库/package 证据。
- RAG development/independent holdout、Harness dry-run（published/0 revisions）、compileall、
  Provider boundary、tracked Secret/run-data、YAML、治理与 `git diff --check` 均通过；Docker Compose
  本机不可执行，保持为 `packaging-smoke` 公共门。
- 本地状态仍为 `in_progress`：实现、测试、walkthrough 和八维证据路径已建立，但实现提交尚未取得
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。coverage 继续保持 `planned`。
- 唯一下一动作：独立暂存/cached diff、提交、推送并等待同一 SHA 三 job；全绿后再单独提交状态收尾，
  将 6B-3 置为 complete、coverage 置为 complete，并只把 6B-4 标为 prepared/waiting authorization。

## 2026-08-20：6B-3 实现 exact-SHA 公共闭环与状态收尾

- 首个实现提交 `0ca7fdebe4bf038685ff24691f2d5091e6ffbe4f` 的 `postgres-migrations` 曾失败；真实日志定位为
  测试 fixture 未先 flush `player_subjects` 父行，导致 PostgreSQL FK 顺序竞争。失败 SHA 保留为审计证据，
  未重跑或放宽生产约束。
- 最小测试 fixture 修复提交 `7e4f23361ec331e53c5190f6a5f7f3532f533081` 已通过 Actions run `32329686381` 的
  exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job。公开证据包括完整回归
  `1295 passed, 67 skipped, 1 warning, 110 subtests passed`、PostgreSQL `100 passed, 1 warning`、migration
  upgrade/downgrade、`alembic check`、package smoke 与边界检查。
- 本机没有 Docker/PostgreSQL，所以本地 skip 仍如实保留；公共 CI 才补齐真实 PostgreSQL trigger、FK、事务、
  并发和 Linux package 证据。没有读取 Key、调用 Riot/Provider，也没有接入 Agent、Review Task、Memory、
  Auth/RSO、SSE、前端或新框架。
- 6B-3 现正式关闭，`docs/learning/coverage.yaml` 置为 `complete`，学习索引改为完整/公共闭环；下一检查点
  是 `6B-4-conversation-bound-recent-review-identity`，仅 prepared/waiting authorization，不实施 6B-4。

## 2026-08-20：RQ-068 授权并进入 6B-4

- 用户明确“继续 6B-4”；canonical 由已完成的 6B-3 交接到
  `6B-4-conversation-bound-recent-review-identity / in_progress`，不进入 6B-5。
- 本批采用既有 `review_tasks` 上的 nullable schema 2.0 identity columns，由服务器在 PostgreSQL 短事务中
  锁定 active Conversation 并派生 owner/conversation/relationship/subject tuple；旧 schema 1.0 row 保持
  新列为 null 且继续可读/可执行，不根据旧 Riot ID 回填身份。
- 新 endpoint body 只允许 count/queue/focus；v2 Worker 通过稳定 subject 的 trusted PUUID 直接构建
  Summary，不再次调用 Account-V1。测试/CI 保持 Fake/no-I/O。
- 当前只完成教学、方案裁决和状态/coverage 治理迁移；产品 migration、Repository、API、Executor 与纵向
  测试尚未实现。6B-5、assistant Message、Memory、Auth/RSO、SSE、前端和新框架继续 deferred。

## 2026-08-20：6B-4 本地实现与完整门禁，等待公共闭环

- Review Task schema 2.0 pure contract、identity-aware fingerprint、Conversation-bound 202 route、0004/ORM、
  PostgreSQL 单事务 server-derived binding、私有 PUUID target、trusted-PUUID Summary/Application、1.0/2.0
  Executor 和 composed API 已在未提交工作树完成；旧 1.0 查询/执行/删除保持兼容。
- package smoke 已升级为 Link→Conversation→Message→schema 2.0 Task→同一 ReviewWorker→safe failed
  terminal，结果明确 `external_riot_provider_calls=0`；两个新真库测试文件已加入阻塞 PostgreSQL job。
- 6B-4 聚焦为 `114 passed, 11 skipped, 1 warning`；完整回归为
  `1333 passed, 78 skipped, 1 warning, 110 subtests passed`。本机 skip 全部来自无 PostgreSQL/Docker，
  不能冒充真库锁、FK、trigger 或 Linux package 成功。
- RAG development/independent holdout 指标均满既定阈值，Harness dry-run 为 `published`/0 revisions；
  compileall、SDK boundary、tracked Secret/run-data、YAML、pip、governance 与 diff 门通过。
- `docs/learning/6b-4-conversation-bound-recent-review-identity-walkthrough.md` 已覆盖八维 evidence，
  但 coverage 在 exact-SHA 三 job 全绿前保持 `planned`。唯一下一动作是 cached diff、提交、推送与公共
  CI；6B-5 未授权且未实施。

## 2026-08-20：6B-4 exact-SHA 公共闭环与 6B-5 交接

- 实现提交 `d63f9085f66e49557b4674d0698495dcb7335c82` 已推送；Actions run `32347834279`
  精确对应该 SHA，workflow 与 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  `completed/success`。
- 公共 `pytest` 为 `1333 passed, 78 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  job 为 `113 passed, 1 warning`，并通过 0004 upgrade/downgrade、完整 migration 链与
  `alembic check` metadata-head 一致性。
- Linux package smoke 真实执行 Link→Conversation→Message→schema 2.0 Review Task→同一 ReviewWorker，
  Review 安全终态为 `failed`、Conversation 保持 `active`、`external_riot_provider_calls=0`。这证明安装后
  控制流和安全失败边界，不证明真实 Riot/Provider 成功或模型质量。
- 6B-4 正式关闭，`docs/learning/coverage.yaml` 已置为 `complete`。本机没有 PostgreSQL/Docker 的 78 个
  skip 仍如实保留，公共 CI 只是补齐真库/Linux 证据，没有把它们改写成本地成功。
- 下一检查点是 `6B-5-memory-candidate-write-gate`，仅 prepared/waiting authorization；尚未创建 Candidate
  migration/model/Repository/write gate，也未实现 assistant terminal、具体长期 Memory、Auth/RSO、SSE、
  前端或新框架。

## 2026-08-20：RQ-069 授权 6B-5，进入设计/TDD

- 用户明确“继续 6B-5”；canonical 现为 `6B-5-memory-candidate-write-gate / in_progress`，不进入 6B-6。
- ADR-0042 选择事务内 typed materializer：Candidate 与 target 必须同事务提交；没有真实 target 时生产
  fail closed。测试专用 target 只证明协议，不冒充具体长期 Memory。
- Candidate identity 从服务器 Conversation 派生；模型/自然语言 confidence 再高也只能 pending；observed
  只能提出受限 review observation。公开 DTO 不泄露 payload、完整 provenance、PUUID 或 Message body。
- 当前已完成治理/专用设计/实施计划，产品代码尚未开始。下一动作是 pure model/gate 红灯；本批外部
  Riot/Provider/Key I/O 固定为 0。

## 2026-08-20：6B-5 本地实现完成，等待 exact-SHA 公共门

- Candidate pure contract/Gate、Service/Port、0005 ORM/migration、owner-scoped Repository、reject/expire/
  accept、restricted materializer session、薄 API/composition 与 no-I/O package smoke 已实现；不创建具体
  Preference/Profile/Review Memory/Plan/Progress 表。
- 新增 `docs/learning/6b-5-memory-candidate-write-gate-walkthrough.md`，覆盖八维学习/工程证据；coverage
  仍保持 `planned`，直到同一实现 SHA 的公共三 job 全绿。
- 本地聚焦 `50 passed, 10 skipped, 1 warning`；完整回归待本轮最终复跑。RAG、Harness dry-run、compileall、
  SDK/secret/tracked-data、YAML、governance 与 diff 门需一并复核。
- 10 个 skip 全因本机无 PostgreSQL/Docker；公共 `postgres-migrations` 新增 0005/FK/trigger/Repository/
  materializer 测试，package smoke 新增 Candidate pending→reject。没有读取 Key、调用 Riot/Provider。
- 唯一下一动作：完成完整本地门禁和 cached diff，提交/推送后等待 exact-SHA `pytest`、`postgres-migrations`、
  `packaging-smoke`；公共全绿后再状态收尾 6B-5 并只交接 6B-6 prepared/waiting authorization。

## 2026-08-20：6B-5 exact-SHA 公共闭环与 6B-6 交接

- 实现提交 `7156cb52e1ab2a976828b5a0a164c163943b56f3` 的 Actions run `32372854457` 中，普通
  `pytest` 与 `packaging-smoke` 成功；真实 PostgreSQL 的三个 materializer 测试只在 teardown 失败：测试
  临时表仍以 FK 引用 `memory_candidates`，fixture 却先执行 Alembic downgrade。失败保留为审计证据，
  没有放宽 migration、FK、Repository 或 materializer 合同。
- 最小清理修复 `dd7c9c8f43bac19756272aaf9555f0519e22341c` 在 downgrade 前显式删除测试专用 target；
  Actions run `32376405150` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job
  均 completed/success。
- 公共完整回归为 `1358 passed, 88 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17 为
  `126 passed, 1 warning`，0005 可逆迁移、materializer commit/rollback/replay/concurrency 与
  `alembic check` metadata-head 一致性均通过。Linux package smoke 中 Candidate 为 `rejected`，
  `external_riot_provider_calls=0`。
- 6B-5 与八维 coverage 正式关闭。它只完成 Candidate 控制面、deterministic gate 和 transactional typed
  materializer 接缝，不等于 Preference/Profile/Review Memory 已存在；生产 registry 在 6B-6 前仍为空并
  fail closed。
- 用户最新“那继续”按 AGENTS 规则只授权唯一下一检查点 `6B-6-preferences-profile-review-memory`。

## 2026-08-20：RQ-070 授权 6B-6，完成设计批冻结

- canonical 已从 `pending/waiting authorization` 恢复为 `in_progress`；当前只处理 6B-6，不能跳到 6B-7。
- 设计批新增 ADR-0043、`docs/plans/2026-08-20-memory-types-design.md` 与
  `docs/plans/2026-08-20-memory-types-implementation.md`，冻结三张 typed target 表、scope/role/key
  allowlist、严格 `value + expected_version` envelope、版本 supersede、Review append 的单 active 最新
  版本语义、PostgreSQL advisory lock/partial unique、查询 API 和错误映射。
- 设计提交 `e44d48f0531f0ee1786cba9b38c8fc8b2589af00` 已由 Actions run `32381553145` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job exact-SHA 公共验证；设计批正式关闭，
  该 run 不证明 6B-6 业务 target 已实现。
- 当前尚未创建 6B-6 migration/model/Repository/materializer/API 产品代码；本轮仍然不进入 Training
  Plan/Progress、Memory-aware Context、assistant terminal、Auth/RSO、SSE、前端、Redis/Chroma/向量库、
  LangGraph、Multi-Agent、新 SDK 或真实 Riot/Provider 调用。
- 设计批公共闭环后，下一动作是按实施计划 Task 1 先写 typed payload/version pure contract 红灯测试；coverage 继续
  `planned`，直到实现、本地门禁和 exact-SHA 三 job 公共闭环。

## 2026-08-20：6B-6 本地实现完成，等待 exact-SHA 公共门

- Pure typed envelope/key/role policy、三个 materializer、三张 ORM 表、0006 migration/trigger、PostgreSQL
  version writer、生产 registry、owner-scoped query Service/API 和 package smoke schema 1.3 已在工作树完成。
- Candidate accept 现在可在同一事务中执行 advisory lock、expected-version、supersede/insert，再写 accepted；
  typed payload/version 失败安全返回并保持 pending。更正仍走 Candidate，没有开放 target PATCH。
- 首轮聚焦/相邻测试为 `128 passed, 19 skipped, 1 warning`；提交前复核又新增 metrics/page 两项纯合同和
  terminal-source/supersedes-chain 两项真库合同，并修正 accept 事务的 typed error disposition 接线。真实
  migration/FK/trigger/partial unique/advisory lock/并发/rollback 与 Linux package accept→query 必须由公共
  job 补证，当前不能声称 6B-6 已完成。
- 最终完整本地回归为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；100 个 skip 全因本机没有
  PostgreSQL/Docker。两套 RAG 指标满门槛，Harness
  dry-run 为 `published`/0 revisions，compileall、YAML、治理、SDK/Secret/tracked-data 与 diff 门通过。
- `docs/learning/6b-6-preferences-profile-review-memory-walkthrough.md` 已覆盖八维 evidence，coverage 仍为
  `planned`。外部 Riot/Provider/Key I/O 为 0；6B-7 及后续能力未进入。
- 首个实现提交 `da87cdeefc6b104b8f9faf3546091ec8b80c1bfb` 的 Actions run `32386630063` 中，普通
  `pytest` 与 `packaging-smoke` 成功；PostgreSQL 为 `141 passed, 1 failed`。唯一失败是测试夹具让
  observed `public_trend` 使用被 6B-5 Gate 禁止的 `user_structured_input` provenance，Repository 正确
  返回 `SOURCE_INVALID`；生产 Gate/migration/materializer 未放宽，失败 SHA 保留为审计证据。
- 唯一下一动作：提交最小测试 provenance 修复、推送并等待新 SHA 的 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke`。三 job 全绿后才允许状态收尾和 6B-7 交接。

## 2026-08-20：6B-6 exact-SHA 公共闭环与 6B-7 交接

- 最小测试 provenance 修复提交 `5531c81ec7117f5c454d320e406153086baae3ea` 已推送；Actions run
  `32387026797` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。
- 公共 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL 17
  为 `142 passed, 1 warning`，0006 upgrade/downgrade、FK/CHECK、source/supersedes trigger、partial
  unique、advisory lock、并发 expected-version、事务回滚和 `alembic check` metadata-head 均通过。
- Linux package smoke 真实执行 Candidate pending→accepted→Preference v1 active query；schema 1.3，
  value `zh-CN`，`external_riot_provider_calls=0`。这不证明真实 Riot/Provider、正式 Auth/RSO 或容量 SLA。
- 6B-6 与八维 coverage 正式关闭。当前只把 `6B-7-training-plan-progress` 标为
  prepared/waiting authorization；没有创建 Training Plan/Progress 产品代码，也未进入 6B-8/6B-9、
  SSE/前端、Redis/向量库、LangGraph、Multi-Agent、新 SDK 或真实外部调用。

## 2026-08-21：RQ-071 授权连续完成 6B-7/8/9，当前进入 6B-7

- 用户明确要求本轮连续完成 `6B-7→6B-8→6B-9`，无需逐步骤批准；RQ-071 已持久化。该授权不合并
  checkpoint，前一项仍须 exact-SHA 三 job 公共闭环后才能进入下一项。
- 6B-7 初学者教学和接缝审计已完成。ADR-0044 与专用 design/implementation plan 冻结：pending Candidate
  作为唯一 Plan draft；用户 accept 才物化 self-only active Plan；Progress 必须绑定 succeeded、published/
  degraded、report-available 的 final Artifact；纠错追加 superseding event；趋势只做确定性数值比较。
- 当前没有新增 Plan/Progress schema、migration、Repository、API 或产品测试；coverage 继续 `planned`，
  6B-8 Memory-aware Context 与 6B-9 lifecycle/export 仍未进入。
- 唯一下一动作：完成 6B-7 设计批本地门禁、独立提交/推送和 exact-SHA 三 job；全绿后按实施计划 Task 1
  写 pure Plan/Progress/trend 红灯。

## 2026-08-21：6B-7 设计批本地验证完成，等待公共门

- 完整本地 pytest 为 `1402 passed, 100 skipped, 1 warning, 110 subtests passed`；本机 PostgreSQL/Docker
  skip 如实保留。治理聚焦最终 `12 passed`，governance、两套 RAG、Harness dry-run、compileall、SDK/
  Secret/tracked-data、YAML 与 diff 门均通过。
- 当前裁决 `pass-local-pending-public-ci`。这只证明 ADR/design/plan 与既有回归兼容，不证明 Training
  Plan/Progress 产品能力已经实现。
- 唯一下一动作：设计批独立提交/推送并等待 exact-SHA 三 job；全绿后当前 checkpoint 保持 6B-7，内部
  动作切换为 Task 1 pure contract 红灯，不进入 6B-8。

## 2026-08-21：6B-7 设计 exact-SHA 公共闭环，进入 pure TDD

- 设计提交 `d678a7a93e7b5f04d5733b9c0abae4a26dc4dd1b` / Actions `32394585411` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- 该公共证据只关闭 6B-7 设计门，不表示 Plan/Progress 已实现。唯一下一动作是实施计划 Task 1：先写
  strict Plan/Progress payload、self-only shape、纠错与 deterministic trend 的 pure 红灯；不进入 6B-8。

## 2026-08-21：6B-7 本地实现完成，等待 exact-SHA 公共门

- Candidate-backed self-only Plan、一个 active partial unique、0007、同事务 lifecycle、完整 final Artifact
  Progress gate、不可变 correction event、deterministic trend、owner-scoped Service/API 和 production
  composition 已在工作树完成；不含 6B-8 Context 或 6B-9 lifecycle/export。
- 聚焦/相邻 `103 passed, 6 skipped, 1 warning`；完整 `1445 passed, 106 skipped, 1 warning,
  110 subtests passed`。新增 6 skip 均为本机无 PostgreSQL；真库 migration/FK/trigger/Artifact/concurrency/
  rollback 只能由公共 `postgres-migrations` 补证。
- package smoke 已扩为 schema 1.4 的 Candidate pending→user accepted→active Plan query，外部 Riot/Provider
  调用为 0；Progress 不借 package 的故意 failed Review 伪造成功 Artifact，真库测试单独构造严格 terminal fixture。
- walkthrough 已补八维 evidence 路径，coverage 在公共三 job 全绿前继续 `planned`。两套 RAG、Harness
  dry-run、compileall、SDK/Secret/tracked-data、YAML、governance 与 diff 门通过。
- 唯一下一动作：独立提交/推送 6B-7 实现并等待 exact-SHA `pytest`、`postgres-migrations`、
  `packaging-smoke`；全绿后才将 coverage 置 complete 并进入 6B-8。

## 2026-08-21：6B-7 exact-SHA 公共闭环并进入 6B-8 设计门

- 6B-7 实现提交 `f6d89225ac5dbd568b6fad7c3c09b7c497c50762` 已推送；Actions run
  `32397290175` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均
  completed/success。公共 pytest 为 `1445 passed, 106 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL 为 `151 passed, 1 warning`，0007 可逆且 `alembic check` 无新操作；Linux package schema
  1.4 完成 Candidate→active Plan query，`external_riot_provider_calls=0`。
- 6B-7 coverage 已置 complete。RQ-071 允许自动进入
  `6B-8-memory-aware-context-typed-turns / in_progress`，但不合并 checkpoint，也不进入 6B-9。
- 6B-8 接缝审计比较三种方案后，选择 run-scoped Memory-aware Context decorator：服务器派生 binding，
  PostgreSQL selector 只返回 legal active records，既有 ContextBuilder/ceiling 负责整记录预算，私有 manifest
  只保存 body-free identity/digest；terminal turn writer 只在 Task/Artifact/publication 全部验证后追加 Assistant。
- 当前只冻结 ADR-0045、专用设计和实施计划；没有 6B-8 migration/selector/context/turn-writer 产品代码。
  唯一下一动作是设计批本地门禁、独立提交/推送与 exact-SHA 三 job；全绿后从 pure contracts 红灯开始。

## 2026-08-21：6B-8 设计批本地门禁完成，等待公共验证

- 完整本地 pytest 为 `1445 passed, 106 skipped, 1 warning, 110 subtests passed`；106 skip 仍全部来自本机
  无 PostgreSQL/Docker，本设计没有新增真库成功声明。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均为 1.0、FPR 0.0，holdout abstention/citation
  均为 1.0；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/run-data、
  YAML、pip、governance 与 diff 门通过。
- 当前裁决 `pass-local-pending-public-ci`。这只证明 ADR/design/plan 与既有基线兼容，不证明 selector、
  manifest、Runtime binding 或 terminal Assistant 已实现。唯一下一动作是独立提交/推送设计批并等待
  exact-SHA 三 job；全绿后当前 checkpoint 保持 6B-8，内部进入 Task 1 pure contract 红灯。

## 2026-08-21：6B-8 实现、失败证据与 exact-SHA 公共闭环

- 初始实现 `65e69c8` 的普通/真库 job 在 governance 发现 walkthrough 漏提交，package 又暴露 Context smoke
  binding 失败；后续 `e4a7840` 的真实 PostgreSQL 发现 Profile fixture 使用非法 `MID`，正确合同为 `MIDDLE`。
  失败 SHA 均保留，没有放宽 schema、Gate、selector 或 owner scope。
- `f5130ca` 修正 fixture 并让 smoke 从服务器持久 Task binding 派生 Context；真库 157 项已绿。随后发现 Compose
  API/smoke owner 配置不一致，经 `c12f4db` 统一隔离 owner 后三 job 首次全绿。
- 最终 evidence 输出提交 `aacc11a1993e9d7d660f9d8d15b761dc641954b1` / Actions `32403187972` 也三 job
  completed/success。公共 pytest `1465 passed, 112 skipped, 1 warning, 110 subtests passed`；真实 PostgreSQL
  `157 passed, 1 warning`；package schema 1.5 输出 Message+Preference+Plan 三类 Context、terminal Assistant 0、
  `external_riot_provider_calls=0`。故意 failed Review 不冒充成功模型回复。
- 6B-8 coverage 已 complete。当前按 RQ-071 进入 `6B-9-lifecycle-export-exit-review / in_progress`。

## 2026-08-21：6B-9 教学、接缝审计与设计冻结

- 对比“各 Repository 分散删除”“中央 lifecycle service + hidden_at + marker”“数据库 cascade hard delete”，
  ADR-0046 选择中央编排：同一 SQL 短事务先隐藏并创建 body-free marker，事务外文件清理，失败保持可幂等补偿。
- 三 scope 冻结为 `conversation_only`、`conversation_and_derived_memory`、`relationship_private_data`；Task/Run/
  Artifact 和全局 Player Subject 仍是独立生命周期。owner-global Preference 不因单 relationship 删除而消失。
- owner export 为有界 schema 1.0 snapshot；保留 decision/supersede/provenance 与 body-free Artifact refs，排除
  PUUID、Key、Prompt、Provider/Tool body 和内部异常。retention/purge 使用 injected clock、bounded batch 和
  Progress→Plan→typed target→Candidate→Message 的 FK-aware 顺序。
- 当前只有 ADR/design/implementation plan 与 coverage planned；0009、Repository/Service/API/package 产品代码
  尚未开始。唯一下一动作是设计批完整本地门禁、独立提交/推送和 exact-SHA 三 job。

## 2026-08-21：6B-9 设计批本地门禁完成

- 首次完整回归发现治理负例测试硬编码旧 6B-8 checkpoint；改为从 canonical front matter 动态读取后，治理
  聚焦 `12 passed`，未放宽 coverage/order 规则。
- 最终完整本地回归 `1464 passed, 113 skipped, 1 warning, 110 subtests passed`；113 skip 仍来自本机无
  PostgreSQL/Docker 与 Windows symlink，不冒充真库/Linux 证据。
- 两套 RAG 满冻结阈值，Harness dry-run `published`/0 revisions；compileall、pip、governance、SDK/Secret/
  tracked-data 与 diff 门通过。当前裁决 `pass-local-pending-public-ci`。
- 唯一下一动作：独立提交/推送设计批并等待 exact-SHA 三 job；公共全绿后才开始 Task 1 pure contracts 红灯。

## 2026-08-21：6B-9 本地实现与退出复核完成，等待公共门

- strict lifecycle contracts、0009 hidden columns/active unique/marker、owner-scoped export、三 scope visibility、
  cleanup compensation、retention/purge、薄 API/composition 与 package schema 1.6 已实现。
- 实现审查发现并修正 0009 CHECK 名的 naming-convention 双前缀风险；offline PostgreSQL SQL 已证明 0009
  使用真实 `ck_<table>_*` 名。隐藏 active target 后新链使用历史最大 version + 1，但不引用隐藏 predecessor。
- 首次完整回归仅有两个 OpenAPI exact-path 基线未登记三条新 endpoint；同步合同后最终完整回归为
  `1489 passed, 117 skipped, 1 warning, 110 subtests passed`。新增
  walkthrough/exit matrix 已覆盖八维 evidence，coverage 在公共三 job 全绿前保持 `planned`。
- 本机 PostgreSQL 测试仍明确 skip；真库 upgrade/downgrade、Repository scope/idempotency 与 Linux package
  export→conversation-only delete 必须由实现 SHA 的公共 job 补证。外部 Riot/Provider/Key I/O 为 0。
- 唯一下一动作：完成最终本地门禁、提交/推送实现 SHA 并等待 exact-SHA 三 job；全绿后才能把 coverage
  置 complete、正式关闭 6B-9/Session-Memory V1，并交接阶段 7 的 canonical 准备态。

## 2026-08-21：6B-9 exact-SHA 公共闭环、阶段 6 关闭与阶段 7 准备态

- 设计提交 `4bdb1bb9e720bd853c677ce2f650476f19ab6e41` / Actions `32404203265` 已完成
  exact-SHA 三 job，只证明设计门兼容。
- 实现提交 `2e37bd4e156d750634d67d64c07ddb4784f048f4` / Actions `32407862496` 的
  `pytest`、`packaging-smoke` 成功，真实 PostgreSQL 为 `163 passed, 1 failed`；唯一失败是测试夹具非法
  把 hidden Conversation 改回 active/null hidden，数据库正确拒绝 `conversation_lifecycle_irreversible`。
  产品 trigger/Repository/scope 未放宽。
- 最小测试修复 `cbc7cbdcd3841a6ed20cd61a61f1cb5890787d38` 删除非法 reset；Actions
  `32408101770` 精确对应该 SHA，`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部
  completed/success。公共 pytest `1490 passed, 116 skipped, 1 warning, 110 subtests passed`；真实
  PostgreSQL `164 passed, 1 warning`，0009 upgrade/downgrade 和 `alembic check` metadata-head 通过。
- Linux package schema 1.6 在成功退出前断言有界 owner export、conversation-only delete 后 Conversation/
  Message 不可见、Preference/Plan 存续；console 输出 `external_riot_provider_calls=0`。这不证明真实
  Riot/Provider、正式 Auth/RSO、备份副本擦除、公网部署或容量 SLA。
- 6B-9 coverage 已 complete，6B-9、Session/Memory V1 与阶段 6 正式关闭。当前只交接
  `stage-7-standard-mcp-dynamic-meta-entry-design` prepared/waiting authorization；尚未开始标准 MCP/Meta
  教学、设计、实现或真实互操作。

## 2026-08-21：RQ-072 授权 Stage 7 入口设计

- 用户明确“那开始 stage7”，授权唯一 canonical 检查点
  `stage-7-standard-mcp-dynamic-meta-entry-design`；已清除等待授权原因，阶段 7 保持 `in_progress`。
- 初学者材料、现有 `ToolDefinition`/`ToolRegistry`/`ToolRuntime`、Application Service、Context/Memory、
  Harness/Runtime 接缝审计已完成；ADR-0047 选择 Adapter-first：MCP 协议 Adapter → 既有 ToolRuntime，
  外部动态 Meta → 有来源/patch/digest/freshness 的 data-only `MetaEvidence`。
- OP.GG 只登记为首选候选，尚未证明标准 endpoint/server、protocol/version、transport、schema、许可、
  freshness、限流或真实互操作；缺任一项就保持 candidate/deferred，不能把普通 HTTP POST 称为 MCP。
- 本检查点明确不安装 MCP SDK、不实现 Client/Server、不创建 Meta 产品代码、不读取 Key、不调用 OP.GG/Riot/
  Provider；后续顺序冻结为 pure contract → transport/discovery → OP.GG Meta Adapter → RiftCoach Server →
  real interoperability exit review。
- 四条进度线：本地代码仍无 Stage 7 产品实现；项目理解已有持久入口设计材料但 owner mastery 尚待复述；参考
  资料只完成路线/现有接缝审计，OP.GG 官方准入尚未完成；GitHub/部署仍只有设计门证据，尚无 Stage 7 真实互操作。
- 当前本地裁决：`entry-design-in-progress-no-external-io`。唯一下一动作是完成设计文档/coverage/治理与
  完整本地门禁，独立提交并等待 exact-SHA 三 job；公共全绿后才进入 `7-1-mcp-client-contract` 的 pure TDD。

## 2026-08-21：Stage 7 入口设计 exact-SHA 公共闭环与 7-1 交接

- 设计提交 `e50a54618157c84a545ad5786e6c820502f967ee` / Actions `32436092074` 精确对应，
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success；本地完整回归为
  `1489 passed, 117 skipped, 1 warning, 110 subtests passed`，117 skip 仍来自本机环境限制。
- ADR-0047、Stage 7 entry design、implementation plan、学习材料与八维 coverage 已正式闭环；该证据只证明
  边界/设计与既有基线兼容，不证明 MCP 产品代码、OP.GG 准入或真实外部互操作。
- 入口设计保持 no-I/O：未安装 MCP SDK、未实现 Client/Server、未读取 Key、未调用 OP.GG/Riot/Provider；
  OP.GG 仍是未经 endpoint/protocol/许可/freshness/互操作审计的 candidate/deferred。
- canonical 已交接到 `7-1-mcp-client-contract`，状态为 prepared/waiting authorization；其前置 coverage
  已 complete，新增 7-1 planned/order contract。授权前不得写 pure MCP contract 产品代码或接入 transport。
- 四条进度线：本地代码仍无 Stage 7 产品实现；项目理解有入口设计持久材料但 7-1 尚未教学；参考资料只完成
  现有接缝和 OP.GG 准入清单，未完成官方准入；GitHub/部署只有入口设计 exact-SHA 证据，尚无真实互操作。

## 2026-08-21：RQ-073 授权 7-1 MCP Client pure contract

- 用户明确“继续下一步”，授权 canonical 的 `7-1-mcp-client-contract`；等待授权原因已清空，checkpoint
  保持 `in_progress`。该授权不外推到 7-2 transport/discovery 或任何外部 I/O。
- 初学者控制流固定为 `initialize → capability gate → tools/list snapshot → allowlisted tools/call`：
  envelope 只描述消息是否合法，transport 才负责消息如何到达；两者必须分开测试和演进。
- 当前实施范围只含严格 pure models/errors：protocol version allowlist、tools capability、唯一有界目录、
  JSON Schema/arguments、schema drift、malformed/oversized result，以及不保存 remote message/data/body 的安全错误投影。
- 不安装 MCP SDK，不实现 stdio/HTTP/session transport，不调用 OP.GG/Riot/Provider，不读取 Key，不创建
  MetaEvidence 或 RiftCoach MCP Server，也不把 fixture/pure test 称为真实互操作。
- 唯一下一动作是先写 `tests/test_mcp_contracts.py` 红灯，再以 `app/mcp/models.py`、`app/mcp/errors.py`
  做最小实现；完成 walkthrough、全部本地门禁与实现 SHA 的 exact-SHA 三 job 前不关闭 7-1。

## 2026-08-21：7-1 本地实现与完整门禁完成

- `app/mcp` 已实现 transport-neutral initialize/list/call/result/error contracts：strict JSON-RPC、version
  allowlist、tools capability、immutable bounded schema/catalog、discovery+allowlist+arguments、server/catalog/schema
  drift 和 body-free JSON-RPC/`isError` 投影；没有 SDK、socket、subprocess、HTTP 或外部调用。
- 红灯先在 `ModuleNotFoundError: app.mcp` 处确认；最小实现与审查增强后，聚焦为
  `20 passed, 17 subtests passed`，相邻 Tool/Provider contracts 为 `55 passed, 62 subtests passed`。
- 完整本地回归为 `1509 passed, 117 skipped, 1 warning, 127 subtests passed`；117 skip 仍来自既有本机
  PostgreSQL/Docker/Linux 限制。两套 RAG 满阈值，Harness dry-run `published/0 revisions`；compileall、pip、
  YAML、governance、SDK/Secret/tracked-data 与 diff 门全部通过。
- walkthrough 已覆盖八维 evidence，但 `coverage.yaml` 继续 `planned`。唯一下一动作是最终 cached diff 审查、
  独立提交/推送并等待 exact-SHA 三 job；全绿前 7-1 保持 open，不进入 7-2。

## 2026-08-21：7-1 exact-SHA 公共闭环与 7-2 交接

- 实现提交 `37f16bc54de1d6e41c3ae65ddc9d9c5e11efa4cb` 对应 Actions run `32439753589`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1510 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 为
  `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` 无漂移；Linux package schema 1.6
  成功且 `external_riot_provider_calls=0`。公共与本地计数按环境分别记录。
- 7-1 walkthrough/八维 coverage 已置 complete。证据只关闭 pure contract，不证明 transport、OP.GG、
  MetaEvidence、RiftCoach MCP Server 或真实外部互操作。
- 唯一下一检查点为 `7-2-mcp-transport-and-discovery` prepared/waiting authorization；当前停止，不写 7-2 代码。

## 2026-08-21：RQ-074 授权与 7-2 本地实现

- 用户明确“继续7-2”，等待原因清除；canonical 仍为
  `7-2-mcp-transport-and-discovery / in_progress`。
- 已先确认 `ModuleNotFoundError: app.mcp.client` 红灯，随后实现 transport-neutral
  `McpClientSession`、in-memory fixture、隔离 JSONL stdio、总 deadline、capability/discovery、
  disconnect/restart generation 和 `ToolDefinition` adapter；没有 SDK、普通 HTTP、OP.GG、Key 或外部 I/O。
- 7-2 聚焦 `11 passed`；7-1/7-2/ToolRuntime 相邻集合 `43 passed, 17 subtests passed`；完整本地回归
  `1520 passed, 117 skipped, 1 warning, 127 subtests passed`。RAG 两套门、Harness dry-run、compileall、
  governance、SDK/Secret/tracked-data/YAML/diff 门均通过；Docker 不可用，package smoke 仍待公共 CI。
- 八维 walkthrough 已写入 `docs/learning/7-2-mcp-transport-and-discovery-walkthrough.md`，coverage
  在 exact-SHA 公共三 job 前保持 `planned`。唯一下一步是最终 diff 审查、独立实现提交/推送与 exact-SHA
  三 job；全绿后才关闭 7-2，并只登记 `7-3-opgg-meta-adapter` prepared/waiting authorization。

## 2026-08-21：7-2 exact-SHA 公共闭环与 7-3 交接

- 实现提交 `f12166665d437a9479afff508709435a23096dd2` 对应 Actions run `32441793585`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest、真实 PostgreSQL migration/control-plane 与 Linux package smoke 均成功；package
  仍是既有 no-I/O smoke，不能外推 OP.GG、真实外部 MCP 或公网部署证据。
- 7-2 八维 walkthrough/coverage 已置 complete。证据只关闭本地 fixture/in-memory/隔离 stdio
  transport/session/discovery，不证明 OP.GG、MetaEvidence、RiftCoach MCP Server 或真实互操作。
- canonical 唯一下一检查点切换为 `7-3-opgg-meta-adapter` prepared/waiting authorization；授权前
  不执行 OP.GG 候选准入、MetaEvidence、Key 读取或外部调用。

## 2026-08-21：RQ-075 授权 7-3 OP.GG Meta Adapter

- 用户在确认官方候选仓库 `opgginc/opgg-mcp` 后明确要求继续正常下一步；该消息授权 canonical 的
  `7-3-opgg-meta-adapter`，不外推到 7-4 RiftCoach MCP Server 或 7-5 双向互操作退出门。
- 当前先核验官方 endpoint、协议/transport、工具 schema、许可、freshness、限流和部署边界；只有准入
  证据足够时才按 TDD 实现 bounded/data-only `MetaEvidence` 与 OP.GG 领域 Adapter。
- 本检查点不读取 Key，不调用 Riot/LLM Provider，不写 Memory/Candidate/Plan/Progress；有限外部探针只作
  候选准入，不冒充 7-5 exact-SHA 真实双向互操作证据。
- 唯一下一动作：完成候选准入审计并形成可版本化 fixture/裁决；若通过则写 pure normalization 红灯，
  若关键合同缺失则按 ADR-0047 fail closed 并记录 deferred/替代决策。

## 2026-08-21：RQ-076 修正 OP.GG 准入语义

- 用户明确指出“缺完整 provenance 就完全不接”会错误拒绝有价值的标准 MCP 能力。该纠正取代本轮早先
  `adapter_implementation_allowed=false` 的二元解释，但不删除真实缺口。
- 新裁决为 `admitted-with-restrictions`：实际 handshake/list/call 已证明官方 Streamable HTTP MCP 可达；
  7-3 继续实现真实 transport 与固定 lane-meta Adapter。因为 LoL 工具没有 outputSchema/structuredContent，
  只允许锁定 schema/字段并以无 `eval` 的 bounded grammar 解析。
- 本地 `retrieved_at/expires_at` 只证明“何时取回/本地缓存何时过期”，不能冒充上游数据生成时间；
  `upstream_patch` 与 `source_freshness` 明确为 unknown。允许 current snapshot recommendation，禁止精确
  patch 归因、跨 patch 历史比较和上游新鲜度声明。
- 唯一下一动作：先写 Streamable HTTP/session 与 partial-provenance MetaEvidence 红灯，再做最小实现；
  不进入 7-4，不读取 Key，不调用 Riot/LLM Provider，不写长期 Memory。

## 2026-08-21：7-3 本地产品实现与真实 smoke

- HTTPS-only/no-redirect Streamable HTTP、opaque session、initialized notification、bounded JSON/SSE、
  fixed local description/alias、admitted-subset catalog snapshot 与 ToolRuntime 单一可靠性所有权已实现。
- OP.GG lane-meta 文本经固定字段和 allowlisted AST grammar 变成 typed facts；partial MetaEvidence 记录
  digest/retrieved/expires/unknown patch/source time，只允许 current snapshot recommendation。Context 新增
  optional/non-instructional/user-role `external_meta_evidence`；不写 Memory/Candidate/Plan/Progress。
- 首次真实产品 smoke 在 tools/list 暴露 30-tool 目录中两个未获准 Valorant 数组 outputSchema；最小修复
  保留全响应 bytes/count 资源门，只严格解析业务 allowlist。相邻回归当前 `83 passed, 17 subtests passed`。
- 第二次产品 smoke 从官方 endpoint 到 Meta Context 全链成功并持久化 body-free 结果；只记录 protocol/
  catalog/evidence/context identity、fact count 与限制，不保存 session/raw text/事实正文。累计外部账本见专用设计；
  Riot/LLM Provider calls 与 Key reads 为 0。
- RQ-077 已持久化 Riot 官方账号/比赛/版本静态/patch update 与 OP.GG 聚合 Meta 的分层融合边界；本批不做
  两源 join，缺 patch 的 OP.GG 不继承 Riot patch 身份。
- ADR-0048、7-3 专用设计、walkthrough 与八维路径已建立，但 coverage 继续 `planned`。唯一下一动作是完整
  本地回归/全部治理门与 cached diff；通过后独立提交/推送并等待 exact-SHA 三 job。公共全绿前不关闭 7-3，
  不进入 7-4/7-5。

## 2026-08-21：7-3 最终本地门完成

- 最终聚焦/相邻为 `95 passed, 1 skipped, 17 subtests passed`；恢复后的提交前审查又补 negotiated
  protocol header、strict numeric scalar、真正的 admitted-subset parsing 与 complete-provenance identity 红灯，
  相关集合 `94 passed, 17 subtests passed`；完整 pytest 更新为
  `1545 passed, 117 skipped, 1 warning, 127 subtests passed`。117 skip 仍来自本机 PostgreSQL/Docker/
  Linux 环境限制，不视为真库或 package 成功。
- RAG development/independent holdout 的 Recall/MRR/nDCG 均 1.0、FPR 0.0，holdout abstention/citation
  均 1.0；Harness dry-run `published`/0 revisions；compileall、SDK boundary、tracked Secret/run-data、pip、
  YAML、governance、body-free evidence scan 与 diff check 全部通过。
- roadmap 总览、learning 索引、ADR-0047、Stage 7 设计/实施计划与 project decisions 的当前状态已同步；
  7-3 只证明单向 OP.GG lane-meta 产品链，不证明 7-4 Server 或 7-5 双向互操作。
- coverage 继续 `planned`。唯一下一动作是最终 cached diff、独立提交/推送并等待实现 SHA 的 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke`；三 job 全绿前不关闭 7-3、不进入 7-4/7-5。

## 2026-08-21：7-3 exact-SHA 公共闭环与 7-4 交接

- 实现提交 `64311a1751ed1c988b6ae6c2c67bdbe757fb9a94` 对应 Actions run `32455219404`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1546 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` metadata-head 无漂移；
  Linux package schema 1.6 成功且 `external_riot_provider_calls=0`。公共与本地计数按环境分别记录。
- 7-3 walkthrough/八维 coverage 已置 complete。该闭环证明官方 Streamable HTTP、获准目录子集、
  strict lane-meta Adapter、partial MetaEvidence、data-only Context 和一次 body-free 单向产品 smoke；
  不证明 OP.GG 全工具、精确 patch、上游 freshness、Riot+OP.GG join、RiftCoach Server 或双向互操作。
- 用户已按 RQ-078 授权当前唯一检查点 `7-4-riftcoach-mcp-server`；本批只实现协议 Server Session、
  owner-scoped read-only Application Facade、四个受限工具和 fixture TDD，不进入 7-5 真实双向互操作。

## 2026-08-21：7-4 本地实现与全部门禁完成

- 新增 transport-neutral `RiftCoachMcpServer`、独立 Session、in-process Client/Server transport、固定四工具
  catalog 与 `QueryMcpApplicationFacade`；owner 只从服务端 `ActorContext` 注入，Server 不监听网络、不直连
  Repository、不读取 Key，也不接受 PUUID、Prompt、URL、SQL、路径或开放 I/O 字段。
- `recent_summary` 交叉验证 receipt、Trace、manifest、`ExecutionValidatedSignal` 与 `PLAYER_SUMMARY` Artifact，
  只返回近期聚合、主要位置/英雄和胜负对照；`single_match_review` 只返回已发布报告 digest；知识搜索只返回
  attribution；评测工具明确 `score_available=false`，不从 publication 虚构 evaluator score。
- 聚焦 `33 passed`，相邻 MCP/Product `109 passed, 17 subtests passed`；完整本地回归为
  `1566 passed, 117 skipped, 1 warning, 127 subtests passed`。117 skip 仍来自本机 PostgreSQL/Docker/Linux
  环境限制，不冒充真库或 package 成功。
- 两套 RAG 满冻结阈值，Harness dry-run `published`/0 revisions；compileall、pip、6 个 YAML、SDK boundary、
  tracked Secret/run-data、body-free MCP evidence、governance 与 diff check 全绿。八维 evidence 已齐，
  coverage 在实现 SHA 的公共三 job 全绿前保持 `planned`。
- 唯一下一动作：最终 diff/cached 审查、独立提交/推送并等待 exact-SHA `pytest`、
  `postgres-migrations`、`packaging-smoke`；公共全绿前不关闭 7-4，不进入 7-5。

## 2026-08-21：7-4 exact-SHA 公共闭环与 7-5 交接

- 实现提交 `431c584c6f07731233e6e32fd6f98505a661f910` 对应 Actions run `32480827952`；
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1567 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 upgrade/downgrade 与 `alembic check` metadata-head 无漂移。
- Linux package schema 1.6 成功且 `external_riot_provider_calls=0`。该 package 仍是既有 no-I/O 产品纵向，
  不冒充公网 MCP Server 或外部 Client 互操作证明。
- 7-4 walkthrough/八维 coverage 已置 complete。该证据关闭受限 transport-neutral Server/Facade，
  不证明正式 Auth/RSO、TLS/限流、公网 transport、Riot+OP.GG join 或 7-5 双向互操作。
- canonical 只交接 `7-5-mcp-interoperability-exit-review` prepared/waiting authorization；授权前停止。

## 2026-08-21：7-5 exact-SHA 公共闭环、Stage 7 关闭与 Stage 8 准备态

- 实现 `a88fbc457850dd77265900e6800079ac2a8fb0e4` / Actions `32483521108` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全绿；公共 pytest
  `1577 passed, 116 skipped, 1 warning, 127 subtests passed`，真库 `164 passed, 1 warning`，
  Linux package schema 1.6/外部 Riot Provider 调用 0。
- 同一 clean implementation SHA 在 `2026-08-21T12:49:20Z–12:49:25Z` 唯一执行一次双向门：官方
  `@modelcontextprotocol/sdk@1.30.0` Client→RiftCoach stdio 与 RiftCoach Client→OP.GG Streamable HTTP
  均完成 initialize、initialized notification、tools/list 和一次 tools/call。OP.GG 继续为 partial
  provenance，不伪造 patch、source time 或 freshness；Riot/LLM/Key I/O 为 0。
- 不可覆盖 evidence 提交 `fac6fe0beaec174c26960a259c361141b6e6ef2e` / Actions `32484257736`
  精确对应该 SHA，三 job completed/success。公共 pytest
  `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `164 passed, 1 warning`，migration 可逆且 metadata=head；Linux package schema 1.6、外部调用 0。
- 7-5 八维 coverage 已 complete，7-5 与 Stage 7 正式关闭。治理顺序原先终止于 7-5；本次按固定九阶段
  路线和既有 entry-design 命名规则，显式追加
  `stage-8-multi-agent-reliable-runtime-productization-entry-design` 到治理常量与 coverage ledger，
  作为唯一 prepared/waiting authorization 检查点，不把交接解释为 Stage 8 已开始实施。
- Stage 8 仍按 `8-Core` 必做交付线与 `8-Advanced` 至少一个证据驱动采用实验双轨；用户明确授权前，
  不开展教学/设计，不实现 Multi-Agent、DAG、cancel/resume、恢复、SSE/前端或生产部署。

## 2026-08-22：RQ-080 授权并启动 Stage 8 entry design

- 用户明确“那开始吧”，授权当前唯一检查点
  `stage-8-multi-agent-reliable-runtime-productization-entry-design`；本批不外推为 8A–8F 产品实现授权。
- 已完成初学者教学、现有 task/Runtime/Harness/Memory/MCP/Riot/Data Dragon/OP.GG/API 接缝审计；确认当前没有正式
  React/Next/Vite 前端脚手架，现有 Timeline、Run Query、Training Plan/Progress、Evidence 和 partial Meta 接缝可复用。
- ADR-0051 采用“可靠 Runtime Core + 证据驱动 Advanced”双轨，冻结
  `entry design → 8A → 8B → 8C → 8D → 8E → 8F`；Multi-Agent/DAG 仅在 Bad Case、对照、消融、成本和安全证据通过后采用，reject 也是合法结论。
- 8D 冻结 Riot 官方账号/比赛/Timeline、Data Dragon 静态、官方 patch/update 与 OP.GG partial Meta 的分层
  `EvidenceBundle`；缺 patch 的 OP.GG 不继承 Riot patch，不能声称 upstream freshness。
- 8E 冻结五个前端模块：电影感 Riot ID 入口、近期复盘工作台、Rift Timeline、Evidence/Agent Trace 抽屉、
  Training Plan/Progress；采用自主 React 设计系统，MotionSites 公开目录/预览和用户离线表只作为逐项资源审计输入。
- 本批入口设计没有读取 Key、调用 Riot/OP.GG/Provider/LLM、购买付费资源、修改产品 API/Runtime/DB 或创建前端代码。
- 当时本地裁决为 `entry-design-in-progress-no-product-io`，尚待本地门禁、独立提交/推送和 entry design
  exact-SHA 公共三 job；该条件随后已由下一节记录的 `3431e8b/32564500421` 满足。

## 2026-08-22：Stage 8 entry design exact-SHA 公共闭环与 8A 交接

- 入口设计提交 `3431e8b47dd992b6c4741e12158855feb64ef917` / Actions `32564500421` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1578 passed, 116 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17
  为 `164 passed, 1 warning`，0001→0009 migration 可逆且 `alembic check` 为 metadata=head。
- Linux package smoke schema 1.6 成功，`external_riot_provider_calls=0`；两套 RAG、compileall、Harness
  SDK/Secret/tracked-data 边界与 dry-run 均通过。
- entry-design 八维 coverage 已置 `complete`。本检查点只关闭教学、设计、治理和采用门，不证明
  Multi-Agent、DAG、可靠恢复、Riot+OP.GG fusion、正式 Web/Auth/SSE、备份或部署已实现。
- canonical 唯一交接为 `8a-advanced-adoption-gate` prepared/waiting authorization；授权前停止。

## 2026-08-22：RQ-081 授权与 8A 本地实现门

- 用户明确“开始”后，当前唯一 checkpoint `8a-advanced-adoption-gate` 进入实施；8B–8F 未获授权且未开始。
- ADR-0052 固定串行 baseline、普通受限并行 comparator、角色隔离 Multi-Agent primary candidate；
  DAG/第三方 Runtime 与 Agentic Retrieval deferred，可靠 lease/recovery 路由到 8C Core。
- strict/body-free/no-I/O evaluator 绑定 case-set SHA
  `d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e` 与 gate digest
  `88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6`；holdout executions=0，
  external I/O=0。
- TDD 首红为缺模块；提交前两轮合同补强共 9 个负例也先红后绿，最终聚焦 `23 passed`、相邻 `129 passed`。
  完整本地 pytest `1600 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG 满门、Harness
  published/0 revisions、compileall/pip/YAML/安全/治理/diff 门通过。
- coverage 仍 planned。唯一下一动作是独立 implementation 提交/推送与该 exact SHA 的三 job；公共全绿后
  才关闭 8A，并只把 `8b-conditional-multi-agent-experiment` 置 prepared/waiting authorization。

## 2026-08-22：8A exact-SHA 公共闭环与 8B 准备态

- implementation `12ad83532d99990f5523d6ecc6def0b8a325d7d0` / Actions `32567642315` 三 job
  completed/success；公共 pytest `1601 passed, 116 skipped, 1 warning, 127 subtests passed`。
- 真库 `164 passed, 1 warning`，0001→0009 可逆且 metadata=head；Linux package schema 1.6，
  `external_riot_provider_calls=0`，image boundary 全绿。
- 8A coverage complete；其 `candidate` 结果不等于 Multi-Agent 已采用，holdout 仍未执行。
- canonical 唯一交接 `8b-conditional-multi-agent-experiment` prepared/waiting authorization；RQ-081 不授权
  8B。当前只完成独立状态收尾提交与 exact-SHA 三 job，授权前不写 8B 实验代码。

## 2026-08-22：8B holdout 前本地实现与完整门禁

- RQ-082 授权后已完成专用设计/实施计划、evaluation-only 三路 runner、typed/digest-bound Artifact、
  exact role/tool/Context、真实 `ReviewHarness`、strict semantic result validator、clean-SHA admission 与
  exclusive development/holdout output；产品 Runtime、Harness 与 MCP/Meta composition 未修改。
- TDD 从 2 个 collection error 到 14 passed；原子跨角色 tool preflight、expected holdout identity、CLI、
  duplicate/tamper/result recomputation 补强后聚焦 `22 passed`。正式 holdout path 只用重标记 development
  副本验证，三个 calibration-excluded rows 未执行。
- 相邻回归 `168 passed, 12 subtests passed`；完整 pytest `1622 passed, 117 skipped, 1 warning,
  127 subtests passed`。117 skip 仍是本机无 PostgreSQL/Docker/Linux 条件，不能冒充公共真库/package。
- 两套 RAG 满冻结阈值；Harness dry-run `published`/0 revisions；compileall、pip、39 YAML、SDK boundary、
  tracked Secret/run-data、governance 与 diff 门通过。external I/O 与正式 holdout executions 均为 0。
- 唯一下一动作：当前 checkpoint 仍为 `8b-conditional-multi-agent-experiment`；完整/cached diff 终审，
  独立提交/推送实现并等待 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke`。三 job 全绿前
  不得运行 clean-SHA development/holdout。

## 2026-08-22：8B implementation 公共门与唯一 holdout 裁决

- implementation `180bc8b452603572d010b6e25b14ed71f6470ce7` / Actions `32572085065` 三 job
  completed/success；公共 pytest 1623/116 skips/127 subtests，真库 164，package schema 1.6/外部调用 0。
- 同一 clean SHA 的 development 得到 `eligible_for_holdout` 后，正式路径在 case 前 exclusive reserve，
  calibration-excluded holdout 唯一执行一次；结果 strict/body-free validator 通过。
- holdout candidate latency improvement 18.95% 未达 20%，普通并行为 22.88%；二者 match/safe degraded/
  isolation 都是 1.0，hard gates 均 0。ADR-0053 裁决 `reject_multi_agent`，不重跑追绿。
- 结果 SHA `94425872102032bd59d188766b46b8f9e7700b04dee6a397832e88f24ae445e8`，experiment ID
  `0be05e49b89ea644696c878cd81141e389c6e834c4c22651248a0898f5750494`，holdout executions=1、external I/O=0。
- result tests 后完整本地 pytest `1625 passed, 117 skipped, 1 warning, 127 subtests passed`；两套 RAG、
  Harness、compileall、pip、39 YAML、安全/治理/body-free/diff 门全绿，测试只复读结果。
- 唯一下一动作：当前 checkpoint 仍为 `8b-conditional-multi-agent-experiment`；独立提交/推送 result、
  ADR-0053、结果回归和 walkthrough，并等待该 exact SHA 三 job。全绿后再做 coverage/canonical 状态收尾。

## 2026-08-22：8B 关闭与 8C 交接

- result/ADR/evidence 提交 `783a329537682b5413d74af4cc3e1ac818f75da2` / Actions `32572610725` 三 job
  completed/success；公共 pytest `1626 passed, 116 skipped, 1 warning, 127 subtests passed`，真库
  `164 passed, 1 warning`，Linux package schema 1.6/外部调用 0。
- 8B coverage 已补齐八维并置 `complete`。ADR-0053 的产品裁决为 reject role-isolated Multi-Agent；bounded
  parallel 仅作为 8D 设计输入，不能解释为 8D 已实现。
- canonical 只交接 `8c-reliable-runtime-core` prepared/waiting authorization；8C 尚未实现，不能自动开始。

## 2026-08-22：8C 本地实现与八维证据完成，等待公共门

- RQ-083 已授权；Task 1–6 依次完成 pure contracts/projector、0010/ORM、Repository lease/event/fencing/
  cancel/replay、lease-aware Worker、proof-based recovery 与 owner-scoped HTTP seam。8B holdout 文件/SHA
  未覆盖、未重跑，外部 Riot/OP.GG/Provider/Key I/O 为 0。
- 真实 TDD 红灯覆盖缺模块/缺路由、event 时间篡改、`varchar(16)` 装不下 `recovery_required`、Worker
  terminal/cancel 最后一瞬竞态、queued cancel lifecycle，以及公共 operation identity/package replay 缺口；
  最后两个窄补强由 `2 failed` 变为 `29 passed`。
- 最新完整本地 pytest 为 `1670 passed, 133 skipped, 1 warning, 127 subtests passed`。133 skip 仍来自本机
  无 PostgreSQL/Docker/Linux 环境，不能冒充 0010 真迁移、并发 fencing/recovery 或 Linux package 成功。
- `docs/learning/8c-reliable-runtime-core-walkthrough.md` 与 coverage 八维路径已建立；公共三 job 全绿前
  coverage 保持 `planned`，checkpoint 保持 `in_progress`。
- 唯一下一动作：运行两套 RAG、Harness dry-run、compileall/pip/YAML、SDK/Secret/tracked-data/body-free、
  governance 与 diff/cached diff 全部门禁，独立提交/推送 implementation/evidence，再等待 exact-SHA
  `pytest`、`postgres-migrations`、`packaging-smoke`。公共全绿后才关闭 8C 并只交接 8D prepared。

## 2026-08-23：8C 公共 CI 修复批本地完成

- 公共 run `32579514636` 的两个失败根因已由真实日志确认：0010 downgrade 裸约束名触发 naming convention 双前缀；queued task 的 JSONB Python `None` 被写成 JSON `null`，违反 checkpoint shape。
- 最小修复已完成：`_drop_reliable_task_constraints()` 统一使用 `op.f(...)`；`ReviewTaskRecord.checkpoint_reference` 使用 `JSONB(none_as_null=True)`。
- 新增离线 downgrade 约束名回归、ORM metadata `none_as_null` 回归与真实 PostgreSQL queued-insert 回归；最新完整本地 pytest 为 `1672 passed, 134 skipped, 1 warning, 127 subtests passed`。
- 两套 RAG 均满门，Harness dry-run 为 `published`/0 revisions，compileall、pip、SDK/Secret/tracked-data、governance 与 diff check 通过；本机 PostgreSQL/Linux skip 仍不能冒充公共证据。
- 当前唯一下一动作：提交并推送 repair implementation，等待同一 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job；公共全绿前 coverage 保持 `planned`，不进入 8D。

## 2026-08-23：8C 第二轮公共 CI 兼容性修复

- 最新 repair run `32584144522` 的 migration downgrade 已通过，`pytest` 已通过；真库仍发现三类兼容性缺口：既有终态 fixture/legacy row 的 heartbeat 为空且 generation 为旧默认 0，以及 JSONB checkpoint 以 JSON 字符串时间戳读回时被 strict Pydantic 误拒。
- 终态不再把运行期 heartbeat 误设为必填，并允许旧终态 generation 0；`running/recovery_required` 仍要求 heartbeat/generation。Repository 通过 strict JSON wire parsing 读取 JSONB checkpoint，保留字段/类型合同，不放宽任意 Python coercion。
- 当前新增本地回归覆盖 checkpoint JSON round-trip；最新完整本地回归和横向门需在此轮修复后重跑，公共全绿前 coverage 继续 `planned`，不进入 8D。

## 2026-08-23：8C 第三轮真库兼容修复

- `b2b4737` 对应公共 run `32584944802` 已通过 pytest；migration 真库由 34 个失败收敛至 2 个，证明终态 generation/heartbeat 与 checkpoint claim 修复有效。
- 新发现并已修复：recovery requeue 仍有一处旧 strict dict parse；package smoke 已走到 owner-scoped event query，JSONB wrapper 兼容路径已补强；既有纵向测试缺 `timedelta` 导入也已修正。
- 当前待提交最新 repair；coverage 保持 `planned`，不进入 8D。

## 2026-08-23：8C 第四轮 event JSONB 边界修复

- 最新 SHA 的 migration 与完整 PostgreSQL job 已全绿，package smoke 唯一失败为 event replay query；task checkpoint 已修复但 event checkpoint 仍默认把 Python `None` 当 JSON `null`。
- `ReviewTaskEventRecord.checkpoint_reference` 现与 task row 一样使用 `JSONB(none_as_null=True)`；这是无 schema 变更的存储映射修复，公共 event DTO 仍 body-free。
- 当前待提交/推送该最小修复；coverage 继续 `planned`，不进入 8D。

## 2026-08-23：8C clean implementation exact-SHA 公共闭环与 8D 交接

- 根因最终定位为 deployment composition 的 `_TaskServiceProxy` 漏掉了新可靠任务 API 的
  `request_cancel` 与 `read_events` 转发；Repository、`ReviewTaskService`、事件解码和公开 DTO
  本身均已通过真库/聚焦测试。修复同时新增 composed-app cancel/event 回归，未扩大权限或公开内部 lease 字段。
- clean implementation `2df5349d85e48138c05d6293d4e3885b6b4756ec` / Actions `32587659678`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success；公共 job
  验证了 PostgreSQL 0010 可逆迁移、真实 claim/heartbeat/fencing/cancel/checkpoint/recovery/event replay、
  Linux package no-I/O vertical 与非 root/image boundary。
- 本地完整回归为 `1673 passed, 134 skipped, 1 warning, 127 subtests passed`；两套 RAG 的
  Recall/MRR/nDCG/FPR 均 `1.0/0`，independent holdout 的 abstention/citation 均 `1.0`；Harness
  dry-run 为 `published`/`0 revisions`；compileall、pip、SDK/Secret/tracked-data、governance、diff
  全部通过。134 skip 只表示本机没有 PostgreSQL/Docker/Linux，真实结论由该 exact-SHA 公共 job 提供。
- 8C 八维 learning/engineering coverage 已置为 `complete`，checkpoint 正式关闭。下一检查点只登记为
  `8d-riot-opgg-evidence-fusion-core / prepared / waiting authorization`；授权前停止，不读取 Key、
  不调用真实 Riot/OP.GG/Provider/LLM，不实现 8D、8E 或 8F。Multi-Agent 产品 reject 与 8B 唯一 holdout
  SHA `944258...445e8` 保持不可覆盖、不可重跑。

## 2026-08-23：RQ-084 授权并启动 8D Evidence Fusion

- 用户明确继续正常下一步，授权唯一 checkpoint `8d-riot-opgg-evidence-fusion-core`；README/作品集的广泛
  样本研究按 RQ-085 留作 8F 横向输入，不插队或阻塞 8D。
- 已完成初学者教学、现有 Riot/Data Dragon/OP.GG Meta/Context 接缝审计与三方案比较。ADR-0055 采用
  immutable typed `EvidenceBundle` + pure fusion kernel，拒绝无类型 JSON merge，暂缓通用 claim graph。
- `app/evidence/` 已本地实现 strict Riot match、Data Dragon、official patch、join/conflict/gap/claim/
  confidence contracts、existing Summary no-I/O adapter、canonical bundle digest 与 allowlisted public projection。
- TDD 首红为 `ModuleNotFoundError: app.evidence`；最小实现和 Pydantic dataclass 边界修复后 focused 为
  `18 passed`，相邻 OP.GG Meta/Context 合计 `48 passed`。partial OP.GG 可支持 current snapshot，但不能继承
  Riot patch 或取得 exact-patch claim；missing/expired/mismatch 均结构化降级。
- 当前 8D 仍 `in_progress`，coverage `planned`。唯一下一动作是独立提交/推送当前 implementation/evidence，
  等待 exact-SHA 三 job；公共全绿前不关闭 8D、不进入 8E。

## 2026-08-23：8D exact-SHA 公共闭环与 8E 交接

- implementation/evidence `a274b7f8900d61cb7edb7d09e2f5c87f8b0b2e48` / Actions `32598480400` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1692 passed, 133 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17 为
  `186 passed, 1 warning`，0001→0010 migration 可逆且 `alembic check` 无新 upgrade；Linux package
  schema 1.6、`external_riot_provider_calls=0`、非 root/image boundary 全绿。
- 8D 以 strict Riot/Data Dragon/official patch/OP.GG partial source contract、canonical EvidenceBundle digest、
  explicit join/provenance/freshness/conflict/gap/claim、Summary/Data Dragon no-I/O adapter 与 public projection
  完成八维证据。partial OP.GG 不能继承 Riot patch/source time/freshness，版本冲突保留双方并降级。
- 该闭环不证明真实刷新、全部 OP.GG 工具、Riot/OP.GG 本轮网络 I/O、EvidenceBundle 持久化、React/SSE/Auth/
  HTTPS/备份或公网部署。8D coverage 置 `complete`；canonical 交接 `8e-productization` prepared/waiting
  authorization。

## 2026-08-23：RQ-086 授权 8E preflight 与一次真实 OP.GG 验证

- 用户授权一次真实 Riot + OP.GG 验证并进入 8E preflight，同时要求前端分小批推进；用户账号不能硬编码
  为 ShowMaker，必须支持用户自填外服 Riot ID、选择自己的账号或以 `observed/public_observed` 分析
  职业选手/高手账号。该要求已持久化为 RQ-086，ADR-0056 和 preflight 计划已创建。
- 本轮只读检查确认仓库没有 ShowMaker 硬编码；`POST /player-links` 已支持 `riot_id`、
  `routing_region` 和 `relationship_role`，Conversation 绑定稳定 player subject；旧 `/reviews/recent`
  仍受环境 `RIOT_REGION` 默认影响，列为 8E legacy 地区审计缺口。
- 真实 OP.GG gate 已执行一次并通过：endpoint `https://mcp-api.op.gg/mcp`，协议 `2025-06-18`，
  server `OP.GG MCP Server 1.0.0`，只调用 `lol_list_lane_meta_champions` 1 次，top 位置 3 条 fact，
  body-free evidence digest `24b49ea9eb9c4c6c6ee682ad21309c7a643fbdde70a8ea18ba8fdf1d26a8c1ec`；结果文件为
  `data/evaluation/results/mcp/opgg_external_validation_2026-08-23.json`。限制仍为 partial provenance、
  patch/source time/upstream freshness unknown，只允许 current snapshot recommendation。
- Riot Key 存在但未输出；`DK ShowMaker#KR1 / asia / observed` 的 Account/Match gate 已通过，结果为
  `data/evaluation/results/riot_external_validation_2026-08-23-v2.json`，3 次 Riot calls、1 局详情、
  PUUID digest only。随后真实 OP.GG `mid` replay 以 `opgg_meta_result_invalid` fail-closed，结果为
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23.json`；不保存 Key、PUUID、原始 response，
  不自动跨区重试，也不放宽 8D parser。
- 当前 preflight 下一动作改为：对真实 OP.GG mid schema drift 做安全诊断/回归裁决，之后再冻结 player
  profile list/selection DTO；该上游适配问题解决或被明确降级前，不把 8E 前端接到未解释的 Meta 数据上。
- preflight 文档/脱敏证据提交 `8c0cc187e93e76c26e9d03f9e8f2371333c783a3` 的公共 Actions run `32611044101`
  已完成 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job success；该 run 只验证持久合同/现有
  no-I/O package，没有把 OP.GG 网络调用放入 CI。

## 2026-08-23：8E schema-drift 诊断接缝完成（live 字段级证据仍待授权）

- `app/meta/opgg.py` 现在可在 fail-closed 时生成 `OPGGMetaSchemaDiagnostic`；只允许 stage、position/row、allowlisted 字段位置、AST 节点类型、长度和摘要 hash，原始正文/字段值不进入异常或持久结果。
- `data/evaluation/results/mcp/opgg_mid_schema_drift_fixture_v1.json` 与 `tests/test_opgg_meta_adapter.py` 固化受控 null-like 非字面量回归；该 fixture 明确不是 live upstream 证据。
- ADR-0057 记录“先诊断、后裁决；不因真实失败放宽 parser”的边界。现有真实结果仍只承认 `opgg_meta_result_invalid` 与 stack-level `row_field` 失败；没有新的明确外部授权时不重跑 OP.GG。
- 当前唯一下一动作：若获新的有界授权，执行一次真实 `mid` replay 读取字段级 body-free diagnostic；随后再裁决扩大 allowlist/degraded，并冻结 player profile selection DTO。前端仍未开始。

- `c5cbc9465da3529b722d27e307ab4f654b725a39` 的 Actions run `32613573022` 已完成 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job success；该公共验证没有外部 Riot/OP.GG/Provider/LLM I/O。

## 2026-08-23：RQ-087 live 字段诊断与 ADR-0058 最小修复

- 用户明确新授权后，本窗口复用既有 body-free Riot 结果，只执行一次真实 OP.GG `mid` tools/call；Riot、
  LLM、Key calls 均为 0，raw response 未持久化。新结果为
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v2.json`。
- live diagnostic 把失败收敛到 `Mid.rank_prev_patch`、field index 7、AST `Name`；其长度/digest 与受控 fixture
  不同。ADR-0058 因此只在 `rank_prev`/`rank_prev_patch` 两个 nullable integer 字段接纳精确小写 JSON
  `null` 并归一化为 `None`；其他 Name、字段、大小写与表达式继续 fail closed。
- TDD 正例先出现 `1 failed, 13 passed`；实现后聚焦 `16 passed`、相邻 OP.GG/MCP/Evidence `60 passed`；
  完整 pytest `1699 passed, 134 skipped, 1 warning, 127 subtests passed`，两套 RAG、Harness、compileall、pip、
  governance 与安全/diff 门全绿。当前唯一下一动作是独立 implementation/evidence 提交与 exact-SHA 三 job；本授权 call 已用完，
  新授权前不执行修复后 live replay，也不声称真实两源 EvidenceBundle 已成功。

## 2026-08-23：ADR-0058 exact-SHA 公共闭环

- implementation/evidence `83fde7d014aae8fdccf2ebd91929967868101075` / Actions `32615340228` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest `1700 passed, 133 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `186 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6、外部 Riot Provider calls 0。
- 代码与公共 CI 已证明窄 JSON-null 合同和回归兼容，但公共 CI 不调用 OP.GG；当前 8E 继续
  `in_progress / coverage planned`。唯一下一动作是在新的明确授权窗口执行一次修复后真实 `mid` replay；
  成功才登记真实两源 EvidenceBundle，失败则保留 degraded 并按新 body-free diagnostic 裁决。之后才进入
  owner-scoped player profile selection DTO、legacy 地区修正和前端小批。

## 2026-08-23：RQ-088 纠正逐次授权的过度保守做法

- 用户明确：Codex 判断排障/验收确有必要时，可以直接执行真实调用，不必每次等待单独授权。该持续授权限于
  次数有界、费用与隐私风险可控的只读调用，并要求持久记录调用、停止条件和脱敏结果；高费用、批量、敏感数据
  发送、不可逆外部写入和权限扩大仍需确认。
- 因此当前唯一下一动作不再是等待授权，而是直接执行一次 ADR-0058 修复后的 OP.GG `mid` body-free replay；
  复用既有 Riot projection，不重调 Riot、不调用 LLM、不读取 Key、不自动重试。

## 2026-08-23：ADR-0058 修复后真实 replay 通过

- RQ-088 下执行一次且仅一次 OP.GG `mid` tools/call；strict adapter 成功解析 10 条 facts，与既有 Riot
  body-free projection 创建 EvidenceBundle，bundle digest
  `69ed8a83140da73818ed46a7857947d780d0132a309a6317036438161fbfff1a`。
- 本次 Riot/LLM/Key calls 均为 0，无重试、无 raw body；结果文件
  `data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v3.json` 的 SHA-256 为
  `1dd8039baee1260ba17da07810a31a50233f37feeb95250bc174ae8a9ac54d1d`。
- bundle 诚实保持 `degraded/unjoined`：Akali 未命中当前 OP.GG top-10 mid Meta，且本 replay 未加入
  Data Dragon/official patch；这证明 parser Bad Case 已修复，不表示 exact champion Meta join、exact-patch 或 freshness。
- frozen success evidence regression、OP.GG/MCP/Evidence 相邻 `61 passed`，governance、JSON 与 diff 门全绿。
  evidence `efaccd9a8022f0d75e9baca5470450be6a1a3357` / Actions `32615821339` 的 exact-SHA 三 job 又全部成功：
  公共 pytest 1701、真实 PostgreSQL 186、Linux package schema 1.6/外部 Riot Provider calls 0。
- OP.GG parser Bad Case 当前正式闭环；8E 仍 `in_progress / coverage planned`。唯一下一动作是 owner-scoped
  player profile list/selection DTO 与 legacy `/reviews/recent` 地区来源修正；前端小批排在该合同之后。

## 2026-08-23：8E Batch B 玩家档案/显式路由本地收尾

- ADR-0059 与专用 design/implementation plan 已冻结复用 successful Player Link 的 owner-scoped
  latest-success profile projection；`player_profile_id` 为 opaque selection ID，当前复用 relationship identity，
  不新增默认档案表、migration、昵称、排序或全局默认状态。
- 本地实现已覆盖 `GET /player-profiles`、PUUID-free DTO、Conversation canonical selection + strict legacy
  alias、legacy required `routing_region`、SQL execution target region 传播、四地区 exact-select Riot builder，
  并从 Worker/Compose 删除 ambient `RIOT_REGION`。ShowMaker 只保留为历史验证样本，产品无默认账号。
- RQ-089 下已安装并配置 Docker Desktop/WSL2、持久 PostgreSQL 17 容器和用户级测试 URL；CI-equivalent
  PostgreSQL collection `187 passed`、Alembic upgrade/check 与真实 Linux Compose package smoke 已通过。
  当前唯一 skip 为 Windows symlink 创建；不为清零而扩大系统权限，exact-SHA Linux pytest 仍独立补证。
- 最终 focused `268 passed`；完整 `1842 passed, 1 skipped, 1 warning, 127 subtests passed`；两套 RAG、
  Harness `published`/0 revisions、compileall/pip/YAML、SDK/Secret/tracked-data、governance/diff 全绿。Linux
  package schema 1.6、外部调用 0、非 root/image boundary 通过且临时 Compose 资源已清理。
- `docs/learning/8e-player-profile-selection-explicit-routing-walkthrough.md` 已覆盖八维 evidence；整个 8E 尚未
  完成，coverage 必须保持 `planned`。

## 2026-08-23：8E Batch B exact-SHA 公共闭环与 Batch C 交接

- implementation/evidence `e844bdd673ee051568e8611160f6ba53e8c745c4` / Actions `32622696087` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest `1709 passed, 134 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL
  `187 passed, 1 warning` 且 migration/head 一致；Linux package schema 1.6、外部调用 0、非 root/image
  boundary 与资源清理全绿。公共 pytest 的 DB skips 由独立阻塞真库 job 承担，不表示缺少真库闭环。
- Batch B 正式关闭；8E 仍 `in_progress`、coverage 仍 `planned`。按已持久化的 preflight 顺序，唯一下一
  内部批为 Batch C：EvidenceBundle 安全持久化/刷新/过期投影、8C event replay→SSE 安全 DTO、
  `published/degraded/rejected/not_ready` 状态合同；Batch C 公共闭环前不进入 Batch D 静态前端。

## 2026-08-23：RQ-090 授权 8E Batch C 并冻结设计

- 用户再次明确“继续”；当前只连续实施 Batch C，不需要逐小步等待批准，也不外推到 Batch D 前端。
- ADR-0060 比较 PostgreSQL append-only snapshot、Artifact/file store 与 reconstruct-on-read，采用与现有
  task owner/run 复合身份绑定的 PostgreSQL immutable revision：同 refresh identity 幂等 replay，过期在
  query-time 降级，旧 revision 不覆盖也不自动回退。
- 四态合同固定为：active task `not_ready`；failed/cancelled/Harness rejected `rejected`；报告可用但 Harness
  degraded 或 evidence missing/expired/non-complete `degraded`；published + complete/current evidence 才
  `published`。SSE 只消费 8C durable cursor event，支持 Last-Event-ID，不复制 Runtime Trace。
- 当前唯一下一动作是完成 Batch C 全部本地/真库/Linux 门、独立 implementation/evidence commit 与
  exact-SHA 三 job；本批外部 Riot/OP.GG/Provider/LLM calls 维持 0，8B holdout 不重跑，coverage 继续 planned。

## 2026-08-23：8E Batch C 本地实现与八维证据完成

- pure/full storage round-trip、nested Meta/bundle/snapshot digest、query-time expiry/usable claims 与四态 projector
  已完成；claims 的 canonical digest 继续排序，storage projection 保留 typed order 以支持严格重建。
- migration 0011、append-only trigger、复合 task FK/cascade、refresh/revision unique、JSONB bound/index 与
  PostgreSQL Repository 已实现；真库证明 replay/conflict、owner latest、并发连续 revision、tamper 和删除级联。
- `EvidenceProductService`、`GET /runs/{run_id}/evidence`、`/product-state` 已实现 404/409/500/503 body-free
  合同；SSE 支持 Last-Event-ID、reconnect no-duplicate、keepalive、terminal close 与 safe stream error。
- composition lifespan 绑定 Evidence Repository/Product/SSE；Linux package smoke 增加失败四态、缺证据 409 和
  terminal SSE，外部调用仍为 0。八维 walkthrough/coverage evidence paths 已建立，整个 8E 仍 planned。
- 本批实现期修复 three real Bad Cases：JSONB shallow-copy tamper 假阳性、same-content retry time 误 conflict、
  evidence-first collection import cycle。该记录时仍待全部横向本地门、独立提交和 exact-SHA 三 job；公共关闭前
  不进入 Batch D React。

## 2026-08-23：8E Batch C 全部本地门完成

- 本地 Compose 的 Memory Context 失败已由数据库身份列定位为 API 默认 `local-demo-owner` 与 smoke
  硬编码 `packaging-smoke-owner` 漂移，而非 Repository 权限回归；TDD 后两者共用 validated
  `RIFTCOACH_LOCAL_OWNER_ID`，严格 owner/binding checks 保持不变。
- 无手工 owner 覆盖的全新 Linux Compose smoke 已通过：schema 1.6、Memory Context 3 records、terminal
  assistant 0、外部调用 0；非 root UID 999 与 image exclusion 通过，临时资源已清理。
- focused `79 passed`、package suites `39 passed`、CI-equivalent PostgreSQL `194 passed, 1 warning`、完整
  `1888 passed, 1 skipped, 1 warning, 127 subtests passed`；Alembic reversible/head check、两套 RAG、
  Harness、compile/pip/YAML、安全/OpenAPI/governance 前置门全绿。唯一 skip 是 Windows symlink 创建，
  仍由 exact-SHA Linux pytest 补证。
- 本批新的 Riot/OP.GG/Provider/LLM calls 维持 0，8B 产品 holdout 未重跑。唯一下一动作是审查 diff、创建
  独立 implementation/evidence commit 并 push，等待同 SHA `pytest`、`postgres-migrations`、
  `packaging-smoke`；三 job 全绿前不关闭 Batch C、不进入 Batch D React。

## 2026-08-23：8E Batch C exact-SHA 公共闭环与 Batch D 准备态

- implementation/evidence `7975dc3cedfa8489eec317257a422577b6bfbf07` / Actions `32629160732`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1750 passed, 139 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17 为
  `194 passed, 1 warning`，0011 head→base→head 可逆且 `alembic check` metadata=head。
- Linux package schema 1.6 输出 Memory Context 3 records、terminal assistant 0、外部调用 0；非 root、
  image exclusion 与 Compose volume/network 清理全绿。公共 pytest 的 DB skips 继续由独立真库 job 承担。
- Batch C 正式关闭；整个 8E 与 coverage 仍 `in_progress/planned`。唯一下一内部批为 Batch D
  静态/fixture-backed 前端设计门，当前 prepared/waiting authorization；本状态收尾不创建 React，
  Auth/RSO、HTTPS、备份、部署和生产 SSE 容量仍未实现。

## 2026-08-23：RQ-091/RQ-092 授权并校准 8E Batch D

- 用户明确开始/继续 Batch D，并要求视觉研究坚持“广撒网、统一横评、精挑选、自主重构”；MotionSites
  只是素材/Prompt 候选池之一，不能成为主要来源。研究同时覆盖组件/动效库、真实成熟产品、游戏数据
  界面以及 Riot/LoL 官方视觉语言。
- 用户进一步校准：许可、状态真实性、键盘/reduced-motion、移动降级和性能是采用硬门，不是做成普通
  极简后台的理由；过门候选必须继续以视觉完成度、当代感、品牌记忆点和 LoL 语义择优。
- API/fixture 审计裁决首批采用“Rift Command Center / 近期复盘工作台”静态纵切。客户端
  `loading/empty/ready/error` 与产品 `published/degraded/rejected/not_ready` 分层；fixture 只按安全 DTO
  塑形，不带 owner、PUUID、Prompt/Context、原始 MCP/Provider body 或内部运行身份。
- 当前仍不接真实 API/SSE/Auth，不实现完整 Timeline/历史列表、HTTPS、备份、部署或公网发布。整个 8E
  coverage 保持 `planned`；下一动作是冻结 ADR/设计/实施计划并按 TDD 建立 React fixture screen、桌面/
  移动、键盘和 reduced-motion 证据。

## 2026-08-23：8E Batch D 本地实现、视觉 QA 与 RQ-093 回查

- 设计提交 `88a5ab67bce2cee655b384b4fd94ea8abe1d15e1` / Actions `32631766013` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 均 completed/success；该 SHA 只冻结 ADR-0061、设计、
  两层视觉采用门和实施计划，不冒充前端代码完成。
- `web/` 已建立 React 19/Vite 8/TypeScript 7、vanilla CSS tokens、Motion、Radix Dialog 和本地 OFL 字体；
  七种不可变 fixture 场景递归拒绝 owner/PUUID/Prompt/raw body/worker/lease/path/DSN/Secret 等字段和值。
- unit 最终 `6 files / 35 passed`；Playwright `12 passed`，覆盖 1440/1024/390/320、四态、observed
  relationship、Drawer 键盘/Escape/焦点返回、reduced-motion、无远程 I/O；axe critical/serious 为 0。
  TypeScript strict 与生产 build 通过，JS gzip `109.89 kB`、CSS gzip `10.99 kB`；npm 官方 audit 0 high
  vulnerabilities，直接 runtime license 为 MIT/OFL-1.1。
- 人工查看 desktop/mobile/tablet/degraded/Drawer/reduced-motion 截图后，修复 tablet Evidence 卡被 grid
  拉伸的大空块；接受证据保存于 `docs/assets/8e-batch-d/`。页面没有逐局伪历史或假 Timeline，切换
  observed 档案也不会把原 self Summary 偷换到新标题。
- RQ-093 的 session-logs/focused export 定向回查确认五模块仍是电影感入口、近期工作台、Rift Timeline、
  Evidence/Agent Trace、Training Plan/Progress；本批工作台 + Drawer/Training 薄纵切只是施工顺序。
  Image2/Photoshop 留给后续入口素材，ECharts/Anime.js 留给出现真实 Timeline/复杂 SVG 消费者之后的采用门。
- 用户指出第一版可能过快后，本批没有直接关闭：又执行 8 组 AutoGLM 搜索、35 站公开可访问性扫描、
  MotionSites live Apps 目录和 Riot/Langfuse/TrainingPeaks/Mobalytics/21st.dev/Aura 深读，并形成正式五模块
  资源矩阵。研究推动 Evidence Drawer 增加 body-free `Safe run path`，不推动新增重依赖或购买 Prompt；
  `F1 Racing Hub`、`Forecast Center`、`Fitness Dashboard`、`Nexar` 分别留给 Timeline/Trace/Training/入口门。
- `.github/workflows/tests.yml` 已本地接入 web lockfile、`npm ci --ignore-scripts`、typecheck、unit、build、
  Chromium e2e；Dockerfile 继续不复制 `web/`，因此本批不冒充部署。整个 8E coverage 保持 `planned`。
  带真实 PostgreSQL 的完整回归 `1890 passed, 1 skipped, 1 warning, 127 subtests`；0011 可逆/head check、
  两套 RAG、Harness、compile/pip/YAML、Secret/tracked-data/governance/diff 与隔离 Linux Compose schema 1.6/
  外部调用 0/image boundary 全绿。该记录时的下一动作是审查 diff、创建独立 implementation/evidence commit
  并等待同 SHA 三个公共 job；下节公共闭环证据已经完成该动作。本批真实 Riot/OP.GG/Provider/LLM calls
  为 0，8B holdout 未重跑。

## 2026-08-23：8E Batch D exact-SHA 公共闭环

- implementation/evidence `f7ebedd7c6cfd135201847a327dfd06c01cc7205` / Actions `32636771507` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1752 passed, 139 skipped, 1 warning, 127 subtests passed`；同一 job 又执行 frontend
  typecheck、`6 files / 35 passed` unit、production build 和 Playwright `12 passed`。bundle 继续为
  JS gzip `109.89 kB`、CSS gzip `10.99 kB`。
- 真实 PostgreSQL 17 为 `194 passed, 1 warning`；0011 head→base→head 可逆且 `alembic check` 无新 upgrade。
  Linux package schema 1.6、Memory Context 3 records、terminal assistant 0、外部 Riot Provider calls 0、
  非 root/image exclusion/资源清理均通过。
- Batch D 静态/fixture-backed 前端正式关闭；整个 `8e-productization` 与 coverage 继续
  `in_progress/planned`。这不证明真实 API/SSE/Auth、电影感入口、完整 Rift Timeline/Training、HTTPS、
  backup/restore、部署或公网发布。
- 唯一下一动作是先设计真实数据接线：盘点 Batch B/C owner-scoped profile/product/evidence/SSE DTO 与
  仍缺的安全 Summary/report HTTP projection，冻结 fixture decoder→HTTP/SSE adapter、错误/重连/状态保持
  合同；设计门完成前不把当前 screen 接到真实服务，也不进入 Batch E 安全/部署或 8F。

## 2026-08-23：RQ-094 上下文纠偏与 RQ-095 Live Integration 设计门

- 定向复核“五项裁决→Stage 8 正式开工”区间后，确认五模块与多来源门已持久化，但最终视觉三方向、
  checkpoint 小复盘、OP.GG useful-breadth 最低候选和完整真实融合 golden slice 没有形成可执行持久合同。
- RQ-094 当前明确：`Rift Awakening` 入口 + `Esports Intelligence` 工作台是长期双层组合，
  `Void Holographic Lab` 只作受限 Hero 实验；Batch D `Rift Command Center` 属工作台第一施工切片。
- Stage 7 V1 和 8D typed fusion 不重开。当前只有 lane-meta；champion analysis/lane matchup 与条件
  synergies 后续通过独立 breadth gate。现有 live bundle 仍 `degraded/unjoined`，缺 Data Dragon/official
  patch、训练建议和 UI 追溯，不能写成完整真实纵向完成。
- RQ-095 只授权当前设计门。ADR-0062 采用薄 profile→latest review locator + 现有 API 客户端组合，补
  `/runs/{run_id}/recent-summary` 与 typed Evidence HTTP；前端采用 exact wire decoder、generation + abort、
  每 task 单 EventSource、受限 Markdown 和真实 Training 字段，不增加 BFF 表、缓存、第二动画栈或浏览器 secret。
- 当前本地只新增/修改 ADR、design、implementation plan 与治理状态，没有产品代码、migration、npm 安装、
  外部 Riot/OP.GG/Provider/LLM 调用、Key 读取、8B holdout 或付费素材获取。整个 8E coverage 继续 `planned`。
- 唯一下一动作是完成文档/治理/stale/diff 门，创建独立 design commit 并等待同 SHA 的 `pytest`、
  `postgres-migrations`、`packaging-smoke`；公共闭环前不进入 live integration implementation。

## 2026-08-23：Live Integration design exact-SHA 公共闭环

- design `4057c93f4ac1ac9ebd181528e559b084e3425e89` / Actions `32639561338` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest `1752 passed, 139 skipped, 1 warning, 127 subtests passed`；同 job 的 frontend unit
  `35 passed`、Playwright `12 passed`、typecheck/build 全绿，bundle 保持 JS gzip `109.89 kB`、CSS gzip
  `10.99 kB`。真实 PostgreSQL 为 `194 passed, 1 warning`，0011 migration 可逆且 metadata=head；Linux
  package smoke 成功。
- 该 SHA 只关闭 RQ-094 上下文持久化和 RQ-095 设计门，不实现 locator、Summary route、typed Evidence、
  decoder/controller/EventSource 或 Markdown 消费；外部 Riot/OP.GG/Provider/LLM 调用和 Key 读取为 0。
- 整个 `8e-productization` 与 coverage 继续 `in_progress/planned`。唯一下一内部检查点是按
  `2026-08-23-8e-live-workbench-integration-implementation.md` 实施 live integration，当前
  `prepared / waiting authorization`；授权前不写代码，不进入 Auth/部署、其余五模块、OP.GG breadth、
  fusion golden slice 或 8F。

## 2026-08-23：RQ-096 Live Integration 本地实现与全部门禁完成

- 后端已实现 owner-scoped latest-review locator、Recent Summary HTTP、typed Evidence public projection 与
  composition/package 接线；PostgreSQL latest 查询排除 cross-owner/hidden/inactive/legacy/wrong-kind，失败任务
  不被旧成功任务越过。公共 `postgres-migrations` job 已纳入 locator 真库测试。
- 前端已实现 exact wire decoders、bounded same-origin client、generation/AbortController、单 EventSource、
  terminal authoritative reload、fixture/live 共用 view 与默认 live 页面；profile switch 清空旧内容，observed
  不请求个人 Training，Product State、client error 与 SSE reconnect 保持独立。
- `react-markdown@10.1.0` 候选因 JS gzip `156.52 kB` 超过 150 kB 硬门被移除；当前 report 使用 React 原生
  转义纯文本，不冒充完整 Markdown renderer。bounded body 改为逐 chunk 计数并在超限时 cancel；最终
  JS/CSS gzip 为 `122.01/11.35 kB`，official npm audit
  `0 vulnerabilities`。
- 实施期修复九类 Bad Case：Chromium native fetch receiver、旧 OpenAPI exact paths 漏项、E2E fixed-ledger
  污染、Windows 10-worker 资源饥饿、package smoke 在 failed task 后写 Evidence，以及提交前审查发现的
  `/player-profiles` generic exception 映射错位、无 Content-Length body 的先完整缓冲后检查、invalid selection
  未关闭 active stream，以及默认 App 漏接 server-list-only URL profile 候选。Evidence 修复保持生产
  repository 只允许 running/succeeded；其余均由 red→green unit/browser gate 固定。
- 本地证据：focused backend `58 passed`、package/composition `59 passed`、完整
  `1939 passed, 1 skipped, 1 warning, 127 subtests passed`；真实 PostgreSQL 17 CI-equivalent collection
  `200 passed, 1 warning`；0011 head→base→head 可逆且 `alembic check` 无 drift。
- 前端 typecheck、`12 files / 66 passed` unit、Playwright `17 passed` 全绿；覆盖 active SSE→published、四态、
  Markdown injection 不执行、self→observed、Training 请求边界、1440/1024/390/320、keyboard/focus、
  reduced-motion、axe critical/serious 0 与 remote request 0。
- 两套 RAG、Harness `published/0 revisions`、compileall/pip/6 YAML、SDK/Secret/tracked-data、governance/diff
  均通过。隔离 Linux Compose package schema 1.6、Memory Context 3 records、terminal assistant 0、外部调用 0、
  非 root/image exclusion 通过，临时 container/volume/network 已清理。唯一 Windows symlink skip 仍由公共
  Linux pytest 补证。
- 八维证据已写入 `docs/learning/8e-live-workbench-integration-walkthrough.md` 并登记 coverage paths；整个
  8E coverage 继续 `planned`。本批 Riot/OP.GG/Provider/LLM calls 0，8B holdout 0，未进入 Auth/RSO、部署、
  电影感入口、完整 Timeline/Training、OP.GG breadth、fusion golden slice 或 8F。
- 唯一下一动作：审查 diff，创建独立 implementation/evidence commit 并 push；等待该 exact SHA 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 success。公共关闭前不交接下一 8E 原子批。

## 2026-08-23：RQ-096 Live Integration exact-SHA 公共闭环

- implementation/evidence `f441061e7444fa6d1d3c213b81e05a02f0fc68c5` / Actions `32647933692`
  的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 completed/success。
- 公共 pytest 为 `1796 passed, 144 skipped, 1 warning, 127 subtests passed`；同一 job 的 frontend
  typecheck、unit `66`、Playwright `17`、JS/CSS gzip `122.01/11.35 kB`、两套 RAG、Harness 与安全边界全绿。
- 真实 PostgreSQL 17 为 `200 passed, 1 warning`，0011 head→base→head 可逆且 `alembic check` 无 drift；
  Linux package schema 1.6、Memory Context 3、terminal assistant 0、外部 Riot Provider calls 0、非 root/
  image exclusion/资源清理全绿。公共 pytest 的 DB skips 由独立阻塞真库 job 承担。
- Live Workbench integration 批正式关闭；整个 8E 与 coverage 继续 `in_progress/planned`。Auth/RSO、部署、
  电影感入口、完整 Timeline/Training、OP.GG breadth、fusion golden slice 和 8F 均未被本批完成。
- 唯一下一检查点为 `8e-batch-e-security-deployment-entry-design`，仅
  `prepared / waiting authorization`；先做威胁/身份/拓扑/备份/隐私/观测与剩余前端施工顺序设计，授权前
  不写实现、不部署、不读 Secret、不调用外部服务。

## 2026-08-23：RQ-097 Batch E 安全/部署入口设计授权与冻结

- 用户最新“那继续做你觉得接下来应该做的事”只授权当前唯一检查点
  `8e-batch-e-security-deployment-entry-design`；本轮不实施 Auth/RSO、HTTPS、CSP/CORS、限流、
  Secret、备份、部署、入口/Timeline/完整 Training、OP.GG breadth、golden slice 或 8F。
- 已完成初学者教学、现状代码接缝审计、三类身份/信任边界、Auth 与 RSO 职责分离、单机 Compose +
  edge/static Web 部署方案比较、安全响应头/容量/Secret/生命周期/隐私/观测合同，以及剩余 Web 模块
  的 E1–E5/W1–W5 原子顺序。
- 新增并同步 ADR-0063、Batch E design/implementation plan 与八维 walkthrough；coverage 仍为
  `8e-productization: planned`，因为入口设计不是实现闭环。
- 设计裁决：RiftCoach Auth 产生 owner；RSO 只在未来安全 callback + `/accounts/me` PUUID 精确匹配后
  升级 `verified_self`；`claimed_self`/`public_observed` 语义不变。首个部署采用 edge/static Web +
  API/Worker/PostgreSQL 单机 Compose，托管数据库是迁移路径，Kubernetes/Redis/Celery/Kafka deferred。
- 当前下一动作：完成文档/状态/coverage/治理与 stale/diff 本地门，创建独立 design commit、push，等待
  同 SHA `pytest`、`postgres-migrations`、`packaging-smoke` exact-SHA 公共闭环；公共全绿后只把
  `8e-batch-e-security-deployment-implementation` 交为 prepared，不自动实现。

## 2026-08-24：RQ-098 视觉合同确认与 8E 前置

- 用户确认最终采用 `Rift Awakening / Cinematic Portal → Esports Intelligence / Broadcast Workbench`；
  `Void Holographic Lab` 仍只作受限 Hero 实验，`Hextech Tactical Editorial` 作为共享语言。
- 新增 ADR-0064、视觉合同实施计划和八维学习 walkthrough。母图、Image2/Photoshop 只负责 preview/可替换
  氛围层；CSS/SVG/React 负责响应式几何、真实表单、关系/产品状态、数据和工作台 handoff。
- 该前置不新增主阶段或 canonical checkpoint，不关闭 `8e-productization`，不实施 Auth/RSO、HTTPS、
  部署、完整 Timeline/Training、OP.GG breadth/golden slice，不读取 Secret、不调用外部服务、不购买付费 Prompt。
- Task 1 presentation state、Task 2 语义入口 shell 与 Task 3 WebP/CSS/SVG atmosphere/route/handoff polish
  已通过前端 unit/typecheck/build/Playwright 门；视觉 preview 仍不是完整产品化，下一动作按 Batch E E4
  backup/restore/erase 顺序推进。

## 2026-08-24：RQ-098 Task 3 本地关闭与 Batch E implementation 进入

- 视觉 Task 3 已完成本地实现与审查：instrumentarium WebP 降为可移除的低对比 soft-light overlay，面板去除
  重复网格，Core/route/handoff 状态按视觉合同编排；desktop、390px mobile、ready handoff、keyboard/focus、
  reduced-motion 均保持可用。Impeccable detector 无告警。
- 前端证据：unit `80 passed`、typecheck/build 通过，JS/CSS gzip `123.91/13.20 kB`；以 `CI=1` 强制隔离
  fake API/Vite 后 Playwright `20 passed`。并行复用未配置 fake API 的旧 Vite 所产生的 5 个 live 失败已归因于
  `127.0.0.1:4174` 未启动，不计为代码回归。
- Batch E implementation 已开始并保持原子边界：E1 opaque HTTP session issuance/revoke、Secure/HttpOnly/
  SameSite cookie、server-side owner resolve 与 session-scoped CSRF；E2 request body/header budgets、CSP 覆盖
  budget errors、single-node IP rate policy；E3 versioned SecretSource、dual-key/revoke/expiry 与 key-last
  Worker composition。E1/E2/E3 focused backend `56 passed`，compileall 与 diff check 通过。
- 当前限制：Auth/RSO/OIDC callback、PostgreSQL session repository、真实 Secret Manager、HTTPS edge、
  多副本 rate store、backup/restore/erase、前端登录 states 尚未实现；环境 SecretSource 只保留 local/test
  fallback，不将 Riot ID 视为认证。当前 coverage 仍 `planned`，不能关闭 8E。
- 唯一下一动作：补 Batch E implementation 八维 walkthrough/coverage 与 stale/gov 门，跑比例完整回归，创建
  独立 implementation/evidence commit 并等待该 SHA 的 `pytest`、`postgres-migrations`、`packaging-smoke`
  exact-SHA 公共 CI；全绿后再交接 E4/剩余模块，不进入 8F。

## 2026-08-24：RQ-099 Batch E E1/E2/E3 exact-SHA 公共闭环

- implementation/evidence `92b768591183e8a7fbe6d12a86359aac862b7efb` / Actions `32658277570` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success。
- 公共 pytest、RAG/Harness/secret/tracked-data/gov 门全绿；PostgreSQL control-plane migration/concurrency
  job 全绿；Linux package smoke schema 1.6、非 root/image boundary、资源清理全绿。
- 因此 E1 opaque session/CSRF、E2 request budgets/单机 rate policy、E3 versioned SecretSource/key-last
  Worker composition 取得公共代码证据；这不证明 OIDC/RSO、PostgreSQL session repository、真实 Secret
  Manager、HTTPS/HSTS edge、多副本 limiter 或 backup/erase 已实现。
- `NEXT`：按既定顺序进入 `8e-batch-e-security-deployment-implementation / E4-backup-restore-erase`，先冻结
  restore/erase 设计与 red tests，再做实现、八维 evidence、比例门、独立提交和 exact-SHA 公共 CI。

## 2026-08-24：RQ-099 E4 本地实现进行中

- E4 已完成首轮 TDD 与真实清理接缝：backup manifest 校验 deterministic deletion-marker digest；restore
  在 readiness 前重放 marker，partial failure 只补偿本次新应用的 marker；重复 restore 由幂等 replayer
  跳过已应用 marker。
- 6B-9 PostgreSQL lifecycle repository 新增 owner-scoped run locator，按 conversation/relationship identity
  返回 body-free `run_id` 引用；API composition 已用 `OwnerRunArtifactTraceCleaner` 接上既有
  `FileRunDataCleaner`，SQL marker commit 后才清理 run 目录中的 Artifact/Runtime Trace。错误 owner、错
  scope、cleanup 失败均 fail closed 并保留 pending compensation。
- 本地 focused 为 `16 passed`（backup/restore/erase），相邻 lifecycle 为 `15 passed`；compileall 与
  `git diff --check` 通过。完整 pytest 正在运行，尚未取得本批独立 exact-SHA 公共 CI。
- 限制仍明确：没有对象存储/KMS/加密 backup bytes、定时备份、真实 PostgreSQL restore replay drill 或
  RPO≤24h/RTO≤2h 实测；8E 继续 `in_progress/planned`，E5/8F 不提前进入。
- `NEXT`：完成完整回归、真实 PostgreSQL locator/migration 与 Linux package smoke，补 stale/governance
  门和八维 E4 evidence，再创建独立 implementation/evidence commit 并等待 exact-SHA 三 job 全绿。

## 2026-08-24：RQ-099 E4 exact-SHA 公共闭环与 E5 交接

- E4 implementation/evidence `27b9256b8987ade45fbc9eb5f62497cbaef9f518` / Actions `32660145945` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；E4 正式关闭。
- 公共证据覆盖 owner marker → targeted run locator → Artifact/Runtime Trace cleanup、manifest digest、
  restore marker replay、幂等、readiness-before-ready 和 partial-failure compensation；公共 package smoke
  继续证明 Linux image boundary、migration/API readiness 与 external Riot Provider calls = 0。
- E4 仍不等于真实 KMS/对象存储/加密 backup bytes、定时备份或 RPO≤24h/RTO≤2h 演练；这些边界已经记录在
  walkthrough/ADR，不能在作品集里夸大。
- 按连续授权进入下一原子项 `8e-batch-e-security-deployment-implementation / E5-packaging-observability`；
  E5 先做现有 Compose/Docker/health/observability 接缝的设计审查与 red tests，再实现和验证。Auth/RSO、
  HTTPS/HSTS、真实 Secret Manager、多副本 limiter、完整 Timeline/Training、OP.GG breadth/golden slice
  与 8F 仍未完成。

## 2026-08-24：E5 packaging/observability 本地首批

- E5 首批采用最小 body-free observability seam：`TaskObservability.emit()` 自动记录 bounded event counter，
  `public_snapshot(max_samples=1000)` 限制 latency 投影，`GET /health/metrics` 返回只含 allowlisted
  counter 与 p50/p95 latency 的 typed DTO。
- `health/live`、`health/ready` 与 Compose migration order/non-root/no-I/O smoke 保持原合同；metrics
  端点不读取 owner、Cookie、Prompt、Report、Riot ID、Secret、数据库或外部网络。
- focused FastAPI/observability 为 `17 passed`；最终完整回归为 `1971 passed, 1 skipped, 1 warning, 127
  subtests passed`；当前 E5 尚未取得独立提交或公共 CI，8E 仍 `in_progress/planned`。
- `NEXT`：补 E5 packaging/observability 八维 walkthrough、Compose/rollback/red-contract 文档与比例回归，
  再创建独立提交并等待 exact-SHA 三 job；不引入 Prometheus/Redis/Kubernetes/第二套 metrics runtime。

## 2026-08-24：RQ-099 E5 exact-SHA 公共闭环与 product shell 交接

- E5 implementation/evidence `ca6da44be439b0020f231dc0c00d6a70322e723c` / Actions `32661425379` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success；bounded metrics、
  Compose/readiness、migration 和 Linux package boundary 取得 exact-SHA 公共证据。
- E5 不声称 Prometheus/长期时序/自动告警、KMS/对象存储、OIDC/RSO、HTTPS edge 或 8F；8E coverage 仍
  `planned`，当前唯一 checkpoint 仍为 `8e-productization / in_progress / remaining-product-modules`。
- 视觉 Task 3 已根据 1440/390 截图完成一轮 polish：instrumentarium 变为低对比可移除远景，route/core/
  panel 层次收敛，机械 atmosphere 不再压过标题、校准表单和 handoff。

## 2026-08-24：RQ-100 production shell/Auth gate 本地完成

- 新增 `AuthSessionWire`/严格 decoder/`BrowserAuthSessionClient` 和 `AuthGate`；默认 live 路径为
  `ProductionShell → AuthGate → LiveWorkbenchController`，session 成功前不启动 controller。
- `auth_unavailable`、`auth_session_expired`、`auth_session_revoked`、`authentication_required` 各自
  投影为 body-free、可审计的配置缺失或恢复边界；fixture scenario 与 `surface=awakening` preview
  保持显式 no-auth disclosure。CSRF token 只在内存 projection，未来 mutation 仍需独立门。
- frontend unit `87 passed`、Playwright `22 passed`、typecheck/build 通过，Impeccable detector 无 findings；
  本批没有 Riot/OP.GG/OIDC/RSO/LLM 外部调用，真实 provider adoption 未完成。
- 八维材料已写入 `docs/plans/2026-08-24-8e-production-shell-auth-gate-{design,implementation}.md`、
  `docs/learning/8e-production-shell-auth-gate-walkthrough.md`，coverage 仍 planned。
- `NEXT`：运行比例 Python/RAG/Harness/Alembic/package/Compose/governance 门，创建独立 implementation/
  evidence commit 并等待 exact-SHA 公共 CI；公共闭环后交接 `Timeline DTO/UI`，不提前进入 OP.GG golden
  slice 或 8F。

## 2026-08-24：RQ-100 production shell/Auth gate exact-SHA 公共闭环，交接 Timeline

- implementation/evidence `15a3a9eea5a1e84f1b1ef604ea42a3008f956cb2` / Actions `32663345737` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success；frontend auth gate、
  visual polish、Python regression、真实 PostgreSQL service 与 Linux package boundary 均取得公共证据。
- 本批正式关闭 production shell/Auth gate；仍不声称 OIDC/RSO、真实 provider callback、PostgreSQL session
  repository、HTTPS edge 或 8E 完成。8E coverage 保持 `planned`。
- 唯一下一检查点更新为 `remaining-product-modules / timeline-dto-ui`：先冻结真实/缺失/部分 timeline
  DTO 与 fixture/live decoder 合同，再做 TDD、视觉与 a11y/performance 门；Evidence/Trace、Training、OP.GG
  useful-breadth/golden slice 和 8F 不提前进入。

## 2026-08-24：RQ-101 Timeline DTO/UI 本地完成（公共关闭前历史记录）

- ADR-0065 冻结 verified event/phase projection：只从 receipt/Trace/manifest/input commitment 验证过的
  `PLAYER_SUMMARY` 投影死亡、购买和目标事件；原始 `timeline_error` 不出 API，Gold/CS/XP 连续曲线不伪造。
- owner-scoped `GET /runs/{run_id}/timeline`、exact browser decoder、generation-guarded terminal load、match
  selector、真实比例 phase rail、chronological list、partial/unavailable 和 synthetic fixture/live seam 已完成。
- 本地证据：query/API focused `45 passed`；frontend unit `92 passed`、Playwright `25 passed`、
  typecheck/build 与 JS/CSS gzip `128.51/15.27 kB`；完整 Python
  `1981 passed, 1 skipped, 1 warning, 127 subtests`；真库
  workflow 清单 `201 passed`、Alembic reversible/check；isolated Linux Compose schema 1.6/non-root/no-I/O 成功。
- durable screenshot 已人工查看 desktop/mobile/partial-unavailable；机械纹理只保留低对比刻度与节点，不成为
  页面主角。本批 Riot/OP.GG/Provider/LLM 调用 0。
- 该历史记录时的唯一 `NEXT` 是 Timeline 独立 implementation/evidence commit、push 与该 SHA 的 `pytest`、
  `postgres-migrations`、`packaging-smoke`；公共三 job 全绿后按 RQ-102 先交接 bilingual product-surface
  foundation，再进入 Evidence/Trace 深页。

## 2026-08-24：RQ-103 当前视觉不是最终签收

- 用户明确当前截图、UI、色调、背景、布局和细节都需要继续 polish；英雄名旁缺头像只是示例，不是完整
  缺口清单。当前 Timeline 的准确定位是“严格功能合同 + 高保真 V1”，不是粗糙低保真稿，也不是最终
  作品集截图。
- RQ-102 双语基础完成后，必须新增独立 LoL asset/detail enrichment 原子批：先冻结 Data Dragon
  version/locale/fallback 合同，再补英雄头像、装备图标、目标图形、asset loading/error fallback 和
  hover/focus/selection 联动；不得直接使用未锁版本或 locale 的公网 URL。
- 8E 退出前还必须对 Rift Awakening、Workbench、Timeline、Evidence/Trace、Training 做跨模块 final visual
  QA，覆盖 UI、色调、背景、布局、材质、动效、响应式、双语 text expansion 与 a11y。该要求在记录时不改变
  Timeline 先取 exact-SHA 的顺序；下一节已记录其公共关闭和当前 bilingual foundation 交接。

## 2026-08-24：RQ-101 Timeline exact-SHA 公共闭环与双语交接

- implementation/evidence `794032f055f2fa37173f9525279870f0adbe5220` / Actions `32682243568` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job completed/success，Timeline DTO/UI 正式关闭。
- 公共 pytest 为 `1837 passed, 145 skipped, 1 warning, 127 subtests passed`；同 job 的 frontend unit
  `92 passed`、Playwright `25 passed`、typecheck/build、JS/CSS gzip `128.51/15.27 kB`、两套 RAG、Harness
  与安全边界全绿。真实 PostgreSQL 为 `201 passed, 1 warning`，migration 可逆且 `alembic check` 无 drift；
  Linux package schema 1.6、Memory Context 3、terminal assistant 0、external Riot Provider calls 0、非 root/
  image exclusion/资源清理全绿。
- Timeline 是已验证的产品功能切片和高保真 V1，但按 RQ-103 仍不是最终视觉签收；英雄/装备/目标资产、
  双语和跨模块 final visual QA 继续后序原子批。整个 8E coverage 保持 `planned`。
- 唯一下一检查点更新为 `remaining-product-modules / bilingual-product-surface-foundation`，已获连续推进授权；
  先做初学者教学、现状审计、catalog/locale persistence/missing-key/Coach language 设计与 TDD，不提前进入
  Data Dragon asset/detail enrichment、Evidence/Trace 深页、Training full、OP.GG breadth/golden slice 或 8F。

## 2026-08-24：RQ-102 bilingual foundation 设计冻结

- ADR-0066、专用 design/implementation plan 与八维 walkthrough 已在本地冻结：UI locale 为
  `zh-CN | en`，采用零新增依赖的 typed local catalog、版本化 strict localStorage、navigator fallback 和
  English runtime fallback；API/status/reason/source/event code 继续保持 canonical 英文。
- UI copy、Data Dragon entity locale 与 Coach Artifact language 是三层独立合同。UI 切换不得重取 API、
  重连 SSE、改变 profile/Product State、静默写 Memory 或机翻已发布报告；旧 report language 不做无证据猜测。
- 该设计冻结记录时只完成设计和只读接缝审计，尚未实现 locale store/catalog/provider/switch，也未接 Data Dragon 资产、
  修改 API/Memory、安装依赖或调用外部服务。8E coverage 继续 `planned`。
- design commit `8969aef689febfb059f72e2fa71c928b2e3bee67` / Actions `32683742229` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 已全部 completed/success，设计门正式关闭。
- `当时 NEXT`：从 locale contract/catalog 红灯开始 implementation，随后依次完成 Provider/Switch、Portal/Auth/App
  shell、Workbench copy/structured Evidence、original-content disclosure 与 browser/a11y/bundle 门；不提前进入 RQ-103。

## 2026-08-24：RQ-102/104/105/106 本地实现完成，等待公共闭环

- 双语 foundation 已实现 `zh-CN|en` typed catalog、strict V1 storage、navigator/English fallback、共享
  LocaleSwitch、structured Evidence/status/copy 与 original Report/Plan。role/metric/gap code 和 RSO/Match-V5/
  fixture/test 实现术语不再直接进入普通产品表面；语言切换不重取 API、重连 SSE、改 profile 或机翻 Artifact。
- ADR-0067 的默认旅程已实现为 zero-I/O `Portal → Account → Workbench`：core 是唯一真实 button，Account 才
  issue provider-neutral session、加载已有 profile 或 POST/poll Player Link；明确 owner-scoped profile 后才
  start live controller。reload/back/forward、session failure、late response/abort、unlisted profile 与 focus
  handoff 均 fail closed。
- Player Link browser decoder 增加 exact four-state/partial identity/claimed timestamp 检查；通用 POST client
  维持 same-origin、16 KiB request、2 MiB response、CSRF、idempotency、Abort 与 body-free error。后端组合测试
  证明同一 server owner 贯穿 session→CSRF Link→terminal→profiles。
- RQ-106 已把母图转为 docs keyframe，再移除 baked core/beam 形成 122.7 kB runtime background；aperture
  fallback-only，instrumentarium 移出 public。React core 负责唯一 copy/focus/click；正常 720ms handoff 与
  bounded reveal、reduced-motion 即时进入已实现。当前仍是 V1 choreography，不是 RQ-103 final visual QA。
- 本地已通过 Player Link file `26 passed, 1 warning`、frontend typecheck/build、unit `24 files / 136 passed`
  与 Playwright `36 passed`；JS/CSS gzip `142.68/18.50 kB`。完整 Python 为
  `1982 passed, 1 skipped, 1 warning, 127 subtests passed`，真实 PostgreSQL 17、0011 head→base→head/
  `alembic check`、两套 RAG、Harness `published/0 revisions`、compileall/pip/YAML、npm audit 0、SDK/Secret/
  tracked-data、governance/diff 与隔离 Linux package schema 1.6/non-root/image exclusion/resource cleanup 全绿。
  唯一 Windows skip 保留给公共 Linux pytest 补证。本批产品
  Riot/OP.GG/Provider/LLM calls 0；视觉生成调用 2，gptimage2 因代理未监听在 request 前失败，calls 0。
- 正式 OIDC/RSO、PostgreSQL session repository、Data Dragon asset/detail enrichment、Evidence/Trace 深页、
  Training full、OP.GG breadth/golden slice、final visual QA 与 8F 均未完成，8E coverage 保持 `planned`。

## 2026-08-24：RQ-107 bounded Coach 推荐待用户裁决

- 审计确认当前 Web 是 Recent Review viewer + read-only Training summary；虽然后端 Conversation/Message、
  AgentRuntime/Harness、terminal assistant、Memory Context 与 Training Candidate/Plan/Progress 已公共完成，Web
  尚不能发送问题或启动 conversation-bound Agent，因此不能称为可交互 Coach。
- 当时建议当前批公共关闭后、RQ-103 前插入 8E 内部 `review-grounded-bounded-coach`，复用可靠 task/SSE 和
  terminal whole reply；开放域 LoL chat、token stream、observed 持久 Plan 和自动长期写入 deferred。
- RQ-108 后来把 foundation 公共关闭后的立即下一原子项固定为 Portal Motion Polish，因此本节不再决定立即
  handoff。RQ-108 完成后，RQ-107 bounded Coach 与 RQ-103 asset/detail/final-QA 的相对顺序仍待集中裁决。

## 2026-08-25：RQ-102/104/105/106 foundation exact-SHA 公共闭环

- implementation/evidence `6084937833beed625dbc64fdcd4c8175edbc9d8f` / Actions `32757872792` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。
- 公共 `pytest` 同时完成前端 typecheck/unit/build/E2E、完整 Python、两套 RAG、Harness、compile、治理与
  tracked-data/SDK 边界；真实 PostgreSQL migration/concurrency 与 Linux package non-root/image/resource
  boundary 也在同一 SHA 通过。最新本地复验为 unit `136`、Playwright `36`、JS/CSS gzip `142.68/18.50 kB`、
  Python `1982 passed, 1 skipped, 1 warning, 127 subtests`。
- 因此双语产品表面、Portal→Account→Workbench、真实 Player Link、owner-scoped profile selection、history/
  focus/abort/fail-closed 与母图分层 V1 取得公共代码证据；这不等于正式 OIDC/RSO、最终 Portal 动效、Coach
  追问、Data Dragon enrichment、完整 8E 或 8F。
- `8e-productization` coverage 继续 `planned`，因为父阶段仍有后续模块和 final QA；不把父组提前标 complete。

## 2026-08-25：RQ-108 Portal Motion Polish 固定为下一原子批

- foundation 已由 `6084937/32757872792` 公共关闭；用户随后明确“开始”，当前唯一原子项
  `portal-motion-polish` 已获授权并进入教学、ADR/设计、素材采用门与 TDD。
- `portal-motion-polish` 只取代当前 Portal Task 3 作为最终视觉/动效验收，
  不否定 zero-early-I/O、Portal→Account→Workbench、真实语义按钮、keyboard/focus、history、reduced-motion
  与错误 fallback 的功能证据。
- 视觉合同以用户确认的母图为构图源；RQ-118 已取代早期“重绘/调大”要求：保留画面内原水晶、塔体与构图，
  正常体验只让它在高清同源 full-frame loop 中呼吸蓄能，poster 仅作首帧/降级；
  透明原生 `<button>` 只覆盖点击区，不显示独立按钮或贴图水晶。提示只用融景微光点/短脉冲；激活后完成
  能量汇聚、一次性 burst 与独立 Account 动态场景幕切。
- RQ-110 又把当前暗化 Portal 截图和 `rift-portal-background-v2` 固定为历史 V1/anti-reference：最终正常模式
  直接从确认高清母图制作全屏循环动态 background，同母图 poster 负责 reduced-motion/Save-Data/media-error；
  不加全屏阴影、vignette、blur 或大段文案，只保留融景小型字标、语言控件和微光点击提示。
- RQ-111 要求 Account 的峡谷拓扑固定连接五个位置的英雄共鸣位；英雄以全身能量幻影/晶体浮雕/建筑级
  全息剪影融入场景，通过姿态与标志性物件识别，不使用头像卡、原画墙、名字标签或假个性化。五个形象统一
  蓝金材质且不得侵占右侧表单负空间；具体 roster/许可/生成边界在 ADR-0068 与概念图审查中冻结。
- RQ-112 又纠正动态范围：Portal 与 Account 的正常体验必须是整张画面的全帧无缝循环视频，所有主要环境层、
  能量路径、远景、光线、反射、星图/峡谷和角色幻影都持续运动；不能以静态 poster 加几个局部光点冒充成品。
  poster 只用于首帧/reduced-motion/Save-Data/media-error，点击时再从全局 idle loop 收敛为一次蓄能/burst。
- RQ-113/114 拒绝两张 Account 一次性群像候选：v2 人物解剖失真且像从 splash 抠图换蓝后贴到地图。后续先
  制作无英雄内殿/峡谷母图，再把正确五英雄逐个重新雕塑为与路线、基座、建筑遮挡、投影和反射一体的场景
  原生全身能量回响，逐项验收后分层合成；官方原画只锁身份，不直接抠图或沿用 pose。
- RQ-115 又拒绝第一张无英雄底座：它把峡谷抽象成机械轨道。下一底座必须以官方 Data Dragon Summoner's
  Rift map 锁定地理身份，保留三路、河道、双野区、两坑、基地、塔与森林/岩壁/河水，再由内殿建筑包围；
  五英雄从对应地貌中形成，不站通用机械底座。
- RQ-116 要求左下蓝方、右上红方的基地/塔/半区线路明确可辨，河道中性蓝、男爵坑紫、小龙坑暖色；不能
  把双方统一成蓝色或给整张图套红蓝滤镜。当前无英雄峡谷底座 v3 已形成该 preview，仍待用户视觉签收。
- RQ-117 进一步校准：官方 `map11` 与 Riot 2024 near-final concept 只锁定三路、斜河道、双野区、双坑、
  双方基地和阵营方向；地形用有意概括的 Hextech terrain masses/轮廓/材质区/符号节点表达，禁止伪造看似
  具体却无法由公开参考证明的微型树墙塔、坡道、道路或建筑。当前 v3 保持未签收 preview，不得进入英雄层、
  视频层或 runtime。
- RQ-118 保留母图原水晶/塔体/构图；两张放大 edit、独立/CSS/贴图水晶均 rejected。RQ-119 又把用户实际
  Kimi 12 秒/1080p 输出作为 `rejected_for_source_fidelity_and_motion_language` Bad Case：页面播放和编码有效，
  但母图→首帧 SSIM 仅 `0.412818`，构图/纹理/运动不合格，不能归因成单纯 CSS 或标称分辨率问题。
- RQ-120 将正式横评分为生成式 Wan/Seedance/Veo/Luma/Runway、确定性 HyperFrames/Remotion 与混合式三线；
  当前推荐候选是生成式有机层 + frame-driven 结构合成，但尚未安装 skill、采用工具、购买 credits、创建 Key
  或调用付费模型。HyperFrames 若胜出仍需安全审计、隔离 spike 与新 ADR。
- RQ-121 允许用户正规中转站作为可验证 secondary transport，但官方 API/Console 优先；站内 slug、`official`
  后缀和价格只列为 catalog evidence。任何 relay 在上传母图前必须通过 model mapping、能力、压缩/水印、
  隐私/保留/删除、地区、错误/重试/计费和调用上限门；本补充不改变当前 Task 1 的 no-media/no-external-I/O。
- runtime Task 1 已新增 strict schema `1.0` manifest decoder：只接受四个 portal/account × desktop/mobile 本地
  rendition，拒绝未知/缺失/重复 identity、远程/data/traversal/格式漂移，并把 Portal crystal hitBox 与 Account
  身份隔离；没有 production manifest 常量或资产 URL。
- `resolveCoverGeometry()` 以纯函数复刻 CSS `object-fit: cover` + percentage `object-position`，统一投影 media box、
  focal point 和可选 hitBox；1440/1024/390/320、极宽/极高与非法/overflow 输入已有 TDD。
- media policy 以 760px 为精确边界，motion/poster 都携带 viewport；首个 commit 固定 `poster/preflight`，
  `useSyncExternalStore` 订阅 modern/legacy MediaQueryList、resize 与可选 Save-Data 后才允许 motion。render→commit
  preference race、SSR conservative poster、StrictMode 和 listener cleanup 均有回归。
- RQ-108 必须独立完成 ADR/设计、素材 provenance、codec/poster、移动安全区、reduced-motion、Save-Data、
  播放/解码失败 fallback、下载/解码/JS 预算、许可/移除路径、TDD、八维证据、独立提交和 exact-SHA 公共门。
  不热链、不复制付费素材，不默认新增 Three/OGL/Anime；不实现 Coach、OIDC/RSO、Data Dragon enrichment 或
  跨模块 final visual QA。
- ADR-0068、I2V candidate audit、正式设计、详细 TDD implementation plan、asset/provenance ledger 与八维
  planned walkthrough 已在本地建立；
  本批未修改 `web/` runtime、未生成/采用正式 loop，也未把 Account candidate 冒充 source master。
- design local gates：governance focused `12 passed`；frontend typecheck/unit `136`/build/E2E `36` 全绿，JS/CSS
  gzip 仍为 `142.68/18.50 kB`；无本地 DB 环境的完整 Python 为 `1837 passed, 146 skipped, 1 warning, 127
  subtests passed`；两套 RAG 满门、Harness `published/0 revisions`、compileall、SDK/Secret/tracked-data 与 diff
  全绿。本机 Docker daemon/PostgreSQL 当前不可达，真库/Linux 证据必须由 design exact-SHA 公共 jobs 补齐。
- 独立两轮设计复核最终 blocker/major findings `0`；mobile source、asset-before-integration、zero-prefetch、
  cover geometry、CSP/provenance、可复现阈值、page-session sticky/pause 与三路线 ledger 已一致。
- design commit `b3b5280cbcc81fa202b52f9cf8437e71956032ac` / Actions `32812868683` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success。公共 pytest 同 SHA 验证 frontend
  unit `136`、Playwright `36`、Python `1838 passed, 145 skipped, 1 warning, 127 subtests`、两套 RAG、Harness/
  governance/security；真 PostgreSQL migration/control-plane 与 Linux no-I/O/non-root package 同时全绿。
- runtime Task 1 implementation/evidence commit
  `1b146e6116587b855a6208e998b5254eac8cba1d` / Actions `32826953474` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；strict manifest、cover geometry 与
  preflight-first media policy 正式公共闭环。公共 pytest 同 SHA 复验 frontend unit `207`、Playwright `36`、
  typecheck/build、完整 Python/RAG/Harness/governance/security；真 PostgreSQL 与 Linux package 同时全绿。
- Task 2 的范围与合同已按 implementation plan 冻结：只使用明确 test fixture URL，不接 App、不采用 production
  media；不安装 HyperFrames，不调用 Wan/Seedance/Veo/Kimi/relay，不创建 Key、不购买 credits。
- runtime Task 2 implementation/evidence `2111a7868bffb3d4d8525536afbb4c88cf8de1bc` / Actions
  `32833608622` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；
  `mediaSession` 的失败单调性/暂停正交性/Portal-Account 隔离，以及 `CinematicSceneMedia` 的 poster-first、
  WebM→MP4、canplay single-flight、play/error sticky fallback、visibility pause/resume、旧 attempt/Promise/DOM
  事件隔离、StrictMode cleanup、poster load/error 和最小 opacity/cover 保障取得公共代码、真库与 Linux 证据。
  聚焦 `39 passed`；frontend unit `246 passed`、typecheck/build、Playwright `36 passed`、JS/CSS gzip
  `142.68/18.50 kB` 与 Impeccable detector 无 findings。当前仍无 App import、生产视频请求或视觉签收。
- runtime Task 3 implementation/evidence `0198fc9efd64d99b0af3a90d3cf468d14120461f` / Actions
  `32836430378` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；
  `portalActivation` 的 generation/latch/commit/cancel、`PortalActivationOverlay` 的 idle/activating/committed、
  reduced-motion/Save-Data、aria-hidden/pointer isolation、受控 activation intent/aria-disabled、ProductJourney
  timer/唯一 navigate/popstate cancellation、Account focus handoff 与跨幕 overlay exit 取得公共证据。
  聚焦 `27 passed`；frontend unit `257 passed`、typecheck/build、Playwright `36 passed`，JS gzip `144.07 kB`、
  CSS gzip `18.50 kB`，仍低于 150/22 kB 门。旧 V1 CSS crystal/文字与临时 overlay 仍明确是后续生产视觉门，
  生产媒体/视频模型/relay 调用为 0。
- runtime Task 4 implementation/evidence `52def9cf2384b8dc1161c4788f89a87c5f567ebc` + toolchain fix
  `d58ba154e6ee9d4b887401a9530a450052cae574` / Actions `32841900909` 的 `pytest`、`postgres-migrations`、
  `packaging-smoke` 三 job 全部 completed/success；只读审计器、planned ledger、固定 PATH ffprobe、codec/poster/
  loop seam/SSIM/budget/anti-reference/toolchain 证据正式公共闭环。focused `25 passed`；frontend unit `257`、
  typecheck/build、Playwright `36`、Python no-DB `1862 passed, 146 skipped, 1 warning, 127 subtests`、两套 RAG、
  Harness、compileall、governance 与 npm official-registry audit 全绿。没有 adopted production rendition、视频
  skill/model/relay 调用。
- runtime Task 5 当前已建立 `2026-08-25-8e-video-bakeoff-relay-admission.md` 与 HyperFrames vetting：广筛
  Wan/Veo/Vidu/Kling/MiniMax/Seedance/Grok 等，不把两个付费槽位误写成封闭候选池。用户官方 UI 证明
  `wan3.0-video` 邀测 access 已通过；DragonAPI 无该 slug 只影响 relay transport。`grok-video-3` 第三代目录/
  通用视频示例已证实，专用 schema/upstream mapping 仍待核对。
- HyperFrames `general-video` agent skill 因 online update/auth/provider 与默认 PostHog telemetry 不准入；exact
  `hyperframes@0.8.14` 仅在临时 HOME/no telemetry/no auth/no cloud 下隔离安装。cached headless shell 的 check
  全绿，frame 0/191 重复 SHA 逐字节一致，raw seam SSIM `0.999600`；默认 MP4 因 5,650,074 B 与 decoded seam
  DSSIM `0.039327 > 0.03` rejected。没有把 smoke 作为视觉候选或生产媒体。
- Task 5 admission/spike evidence `7067ea1d2a9ebfb17d0cec1831b248404eee52e2` / Actions
  `32862942549` 的 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job全部 completed/success；该公共门
  只关闭候选准入/隔离 spike 批，不关闭 Task 5、RQ-108、8E 或任何生产媒体验收。
- `NEXT`：只执行 Wan 3.0 官方 endpoint/region/Key presence 的 body-free preflight；先不上传母图或发起付费
  生成。preflight 后再在既定最多两个 A 槽位内执行一次 Wan 与一次 Veo/Vidu 候选，不自动重试。
- Wan/Dragon executable preflight 现已在本地冻结：两边均有现成 Key presence 但未读取值；第一方 DashScope
  endpoint、Wan standard/prime、免费额度、Dragon/Veo relay、source/prompt digest、RQ-112 全帧 motion language、
  一候选一调用/不充值/替补池均有 body-free 记录。`NEXT` 改为该 preflight 独立 commit/push 与 exact-SHA
  三 job；公共成功后才上传 Portal 母图并创建首个 Wan 任务。
- Task 5 不因当前 Portal bake-off 变成 Portal-only：两个 Portal 首轮样本审计后，唯一后继是 Account
  topology/intentional-abstraction source gate、五英雄逐位重塑、adopted source 与 10 秒全帧 loop；Portal/Account
  两幕全通过才可进入 Task 6。当前 Account v3 仍 `preview/blocking/not adopted`。
- executable preflight `7fe47db4784b97f9df577b867e0bae11c5e841e7` / Actions `32869447853` 的 pytest、
  postgres-migrations 与 packaging-smoke 三 job 全绿；其 transport/费用/控制流继续有效，但 v1 source identity
  已被 RQ-124 supersede，不能直接据此上传 v2。
- RQ-124 v2 migration 当前本地完成：active path `portal-mother-image-source-v2.png`，SHA `8134c0ca...1a06e`，
  v1 archival parent 不变；provenance/ledger/ADR/计划/审计器和新增 anti-fallback test 已同步，focused `26 passed`。
  `NEXT`：独立 source-migration commit/push 与 exact-SHA 三 job；成功后才恢复 Wan 上传。
- v2 source migration `2a2da0e9bf37180ae987920cff85a8c2d3d39bfa` / Actions `32872452053` 的
  pytest、postgres-migrations、packaging-smoke 三 job 全绿；随后浏览器只创建一个有效 Wan task，free quota
  100%→73.33%，external video calls `1`。
- Wan output SHA `030a60f...1f58a`，8s/1918×1080/30fps/H.264/yuv420p/no-audio/2,057,453 B；source→first
  `0.860852`、seam DSSIM `0.097587 > 0.03`、可见 `AI生成`，人工判定没有 RQ-112 coherent full-frame motion。
  `NEXT`：先提交/公共关闭该负面证据批，再进入 Dragon/Veo；不重抽 Wan。
- Wan negative audit `69fc4ab9a9d76e2f11b031b95c7f855b352b56a5` / Actions `32876134114` 的
  pytest、postgres-migrations、packaging-smoke 三 job 全部成功；该样本正式 rejected。
- `NEXT`：A2 Dragon/Veo 一次有界调用。Key 只由用户在本地可见 PowerShell secure prompt 输入，脚本 SHA
  `dcce8810bfd523b6fcf0061512a7a5738ff0e3fbc8e1429832cfbf406569a16c`，不写 Key/prompt/remote URL/raw body。
- Dragon/Veo A2 已执行一次：task 控制台成功/100%，原始 output SHA `b707bb1...fa913`；`/content` 对成功任务
  返回 403，但同一 task query 的 `result.data[0].url` 可 body-free 恢复，未产生第二次 POST。原始 H.264
  High 4:4:4/yuv444p 只作研究证据；另转码 yuv420p 兼容预览仅解决本机播放，不是生产资产。
- 样本因 source→first `0.587962`、seam DSSIM `0.161631 > 0.03`、254,156,130 B、编码合同与只让少数焦点
  分段运动而 rejected；external video calls 当前 `2`，production media `0`。
- RQ-125 明确：`metadata.lastFrame` 字段映射经专用文档复核正确，但 1662-byte prompt 重述画面并同时使用
  多个 subtle/slow/restrained 词，没有充分利用 I2V motion-only guidance。因此当前样本不是 Provider ceiling；
  不继续复制同配置换模型抽卡，也不永久关闭 Wan/Veo/Vidu/Kling/MiniMax/Seedance/Grok。
- `NEXT`：先独立提交/推送 Veo sample audit 并取得 exact-SHA 三 job；随后 no-paid-call C 线优先 proof：
  layer/mask/inpaint + deterministic frame clock 验证整幕 motion coverage/source/seam/维护成本。proof 不合格
  时恢复一次短 motion-only、首帧控制 + deterministic seam 的校正 A comparator。Account 仍在 Portal 工艺
  通过后按 topology→无英雄底座→五英雄逐位→adopted source→10s loop 顺序继续。
- Veo sample audit `e79a76ef8de82d56f3b97ba84623def8ea656a5b` / Actions `32918278259` 的 `pytest`、
  `postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；负面样本与 RQ-125 纠偏正式关闭。
- `NEXT`：C 线 no-paid-call proof 已按 RQ-125 授权进入。先建立一个 repo-excluded research scene graph 与
  deterministic animatic，证明所有大区持续参与、结构/source 锁定、帧时钟闭合和维护成本；在 proof 过门前
  不调用新视频模型、不采用 production media、不进入 Account/Task 6。校正 A comparator 保持条件 fallback。
- C proof design/plan `78ae6e3875cee7ad02b2dbbb607ea7ff1d98a3d8` / Actions `32919447127` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；8 systems、192 帧时钟、
  source/seam/region/grid/manual/budget 与三态 verdict 设计门正式关闭。
- `NEXT`：C proof implementation 已获既有连续授权并进入 contract TDD。先完成 Task 1–3：strict contract、
  deterministic scene graph、isolated renderer wrapper；本批不调用新模型、不接 runtime、不生成 production media。
- C proof contract/scene graph/renderer 已实现并真实输出 v3 研究样片；raw source/clock、encoded seam、3×3 coverage
  与 3.90MB bytes 机械项可控，但人工与用户审查确认它仍只是母图上的 line/ring/node HUD 覆层，环境本身未动。
  裁决为 `proof_fail_reopen_corrected_a`；不继续调 SVG/CSS，不进入 runtime。
- `NEXT`：先提交/公共关闭 C proof 负面证据；全绿后执行一次 RQ-126 校正 A comparator：Veo first-frame only、
  short motion-only、medium clearly perceptible full-scene motion、no object-by-object spotlight/HUD，同一 task/一 POST；
  通过 source/full-scene motion 后才做 deterministic seam。Account/Task 6 继续阻塞。
- RQ-127 进一步固定这次 comparator 的目标不是“多几个元素动”，而是全幕 breathing：near/mid/far 体积空气、
  大尺度环境光、建筑/地面/反射、道路、Rift、水晶与整片星空同时持续运动；允许构图锚定的小幅 camera
  float/parallax cycle，强度 medium-to-strong / clearly perceptible / cool，不再完全 locked/pixel-stable。
- C proof implementation/fix `557dac14f62ae0234be949bf6a38e9126cd8cbf0` / Actions `32923151197` 的
  `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 全部 completed/success；首个 `e215f7e/32922688081`
  只因 Windows-only test fixture 在 Linux 失败，已修复并保留为跨平台 Bad Case。负面 proof 正式关闭。
- corrected A preflight 已本地冻结：first-only/no lastFrame、positive/negative/runner 三 SHA、one POST、motion-only
  与 RQ-127 全幕强度门；尚未弹窗、读取 Key 或创建 task。
- `NEXT`：先提交/公共关闭本 preflight；exact-SHA 三 job 全绿后启动 secure Key runner，一次 corrected Veo task。
- corrected Veo task 已 one POST 后在服务端 158s/100% 失败，公开原因仅 `Generation failed: task processing
  failed`；无 output，质量 unknown，不重跑。external video calls 累计 `3`，production media `0`。
- Vidu Q3 Pro schema/preflight 已本地冻结：`viduq3-pro`、1 张 image_urls=first frame、8s/1080p/16:9、audio
  false、seed 127，prompt/runner SHA `a38bdc...bb72` / `60e4f8...24f5`；尚未读取 Key 或创建 Vidu task。
- RQ-128 固定 failure fault tree；corrected Veo 无 output，故 request/relay/upstream fault domain unresolved、quality
  unknown，不能否定 Veo/first-only/生成路线。Vidu 只改变 model/schema，保持 transport/source/motion/first-only；
  若也 generic failed，下一步审计 relay/request 而不是继续换模型。
- `NEXT`：先提交/公共关闭 Veo failure + Vidu preflight；exact-SHA 三 job 全绿后启动一次 Vidu Q3 Pro secure runner。
- Vidu Q3 Pro 首个 task 已 one POST/queued 160s 后 generic failed/100%，无 output；quality unknown、不换模型。
  source URL 200/Range 206，local create/auth 正常；corrected Veo/Vidu 两个 first-only task 在同 relay 同形失败。
  external video calls 累计 `4`，production media `0`。
- 创浪云 Studio 登录态只读审计证明 Vidu Q3 Pro 原生 `首帧生视频`、8s/1080p/16:9，但音频固定开启；提示词
  增强已关闭，预计 5.28 额度并获用户确认。RQ-128 下唯一重试改为 Studio-contract：删除 seed、audio=true，
  其余保持；runner SHA `7f6d2e...0011`。若仍 generic failed，停止 API/model 切换并升级 relay/upstream 诊断。
- `NEXT`：更新并公共关闭 Studio-contract preflight；exact-SHA 三 job 全绿后执行一次 Vidu task，成功后本地去音轨。
- Studio-contract Vidu task 已 completed；output `6e1ce9...251a`、12.6MB、1080 container/metadata 720p conflict、
  source→first `0.790736`、seam DSSIM `0.425097`。全幕变化明显但主要是 camera push/global drift，用户拒绝；
  只拒绝 sample，external calls `5`，production media `0`。
- RQ-129：目标是 locked-frame、精细 in-scene living environment，不是 Vidu 全局运镜，也不是 Veo v1 的粗
  四效果槽。下一最小变量实验保持成功 Veo first=last/model/transport/source，只改 refined medium/evident storyboard。
- Veo positive/negative/runner SHA `4dbdf0...41f9` / `b6d7b4...9cbd` / `70332e...8406` 已本地冻结；尚未调用。
- `NEXT`：先提交/公共关闭 Vidu audit + Veo refined preflight；exact-SHA 三 job 后 one POST。
- Veo refined submit 已执行但在 POST 阶段直接 403：`task_id=""`、无任务、无输出、质量 unknown；不是上游
  生成失败，也不是下载问题。提交当时钱包 `$15.01`，Veo 页面 `$2.464` 且描述按秒计费，8 秒估算约
  `$19.712`；后续 common log 已在下条把该 hypothesis 证实为预扣失败。external video calls 仍为 `5`，
  production media `0`。
- Dragon 通用日志已把 403 精确归因为预扣失败：当时余额 `$15.008`、8 秒需要 `$19.712`；同一时间四条
  common-log pipeline 记录不等于四个 task/POST，task log 仍只有原 4 个任务。用户充值 `$50` 后余额为
  `$65.01`，故 billing gate 现已满足。
- RQ-130 要求“万事俱备”还必须包含 prompt/constraint/request preflight。v5 positive 1,478 B/SHA
  `99cce1b...e72a6`、negative 551 B/SHA `310b281...b8ab` 已按 Google official I2V motion-only、单一连续镜头、
  fixed camera/deep focus/crisp linework、left/center/right + near/mid/far 同时运动和八秒 phase/illumination/velocity
  闭环收敛；negative 使用 unwanted-phenomena 列表。runner SHA 仍为 `70332e...8406`，parse 0 errors；source
  remote HEAD 200 image/png/2,268,033 B 且 local SHA `8134c0...a06e` 匹配；`retry1` output/status 均不存在。
- `NEXT`：先把本诊断与 v5 preflight 独立提交、推送并取得 exact-SHA 三 job；公共成功后才以唯一新路径、
  one POST/no retry 执行一次 refined Veo。不得用余额充足绕过 prompt gate，也不得自动重抽或切模型。
- v5 preflight 已由 `d57b026c45993a41437a7fc4dd35cb2680445048` / Actions `32951125621` 三 job 全绿；
  唯一 task `task_I5iJQDEiEOpZtsQCSOi3qELNTMFAk9Mw` one POST 创建，159 秒/100% 后以
  `Generation failed: task processing failed` 终止。没有 output/result URL，v5 motion、Veo quality 与 first=last
  方法质量保持 unknown。预扣 `$19.712` 已同额异步退款；最终钱包 `$67.01`。
- 本地可见终端处理发生操作事故：父窗口在用户输入后被误关，子 runner 已成功 POST 但之后退出，status 曾停在
  50%；没有第二次 POST，已按远端 task log 更正为 `failed/remote_terminal/100%/task_processing_failed`。
  external video calls `6`，production media `0`。
- `NEXT`：先独立提交/推送本 upstream failure 与 terminal incident audit 并取得 exact-SHA 三 job；不重发 v5，
  不把无输出失败归因 prompt/model/method，不立即切 Seedance/Grok。只有 task-id 级诊断、transient 证据或新的
  schema/transport 可证伪假设才能重开调用讨论。
- upstream failure/terminal incident audit 已由 `ac76f74b89791f933e51183c8a4cf3b5e35323da` / Actions
  `32952793297` 的 pytest、真实 PostgreSQL 与 Linux packaging 三 job exact-SHA 全绿并正式关闭。
- `NEXT`：保持 `8e-productization / portal-motion-polish / runtime Task 5`，进入零成本 task-id/platform diagnosis
  decision gate：先整理可提供给 Dragon 的 task ID、模型、时间、digest 与 generic error body-free packet；不读取/
  发送 Key，不代表用户联系支持，不产生视频调用。若无法获得新增诊断，再由用户裁决 poster-only 暂停、官方
  transport 对照或后续 Account source gate，不能由 agent 静默换路线。
- body-free support packet 已准备，QQ 群视频管理员私聊草稿已填写但未发送；用户随后明确选择 Studio，故不发送。
- RQ-131 Studio 手动交接已冻结：同一 v2 图作首尾帧、Veo 3.1 Quality Official、8s/1080p/16:9、增强关闭、
  合并单文本框 v5 prompt；预计 19.71。Chrome 自动 file chooser 因扩展 file URL permission 未捕获，确认
  Studio 仍为 0/2、没有上传/生成/扣费；不为本次修改扩展权限。
- `NEXT`：用户按 `docs/plans/2026-08-26-8e-veo-studio-manual-handoff.md` 手动上传同一 v2 母图两次、粘贴
  Studio prompt、核对六项并本人点击生成；Codex 等待 task/completed 页面后只处理下载与质量审计，不自动重抽。
- v5 Studio 任务 `task_Rdrn26RA6kgeyUlDdpORnnQ2KxUxmaHP` 已在 93 秒/100% 后 generic failed；无 output，
  `$19.712` 全额退款，钱包 `$67.01`。这排除自写 runner 为必要根因，但仍不能区分 v5 constraint 与通道状态。
- 用户明确不走 QQ 支持，并按 RQ-132 授权 19.71 的 exact v1 Studio reproduction。当前参数/prompt 已填，0/2；
  QQ 草稿保持未发送。
- `NEXT`：用户上传同一 v2 母图两次至 2/2；本 preflight exact-SHA 三 job 通过后，Codex readback 参数/prompt，
  使用用户本轮明确费用授权执行一次生成。失败或成功均不自动重试。
- exact v1 task `task_v8gAX2IvJT786Y79BLwxeukNx5HHPDW9` 81s/100% generic failed/no output，19.712 全退；
  因历史成功 prompt 也失败，`Veo3.1-quality-official` 当前暂停。calls 8、production media 0。
- Seedance/Kling/Grok Studio contract 已实测；Seedance 2.5 因 first+last + exact 8s 成为 primary。当前 readback：
  两张 v2、8s/720p/16:9/no-audio/enhancement off、v5 SHA `91ca48b...b322`。
- `NEXT`：先提交/public close 本结果与 preflight；按钮费用显示 `--`，模型广场按 `$1.4946/秒` 推导 8s
  `$11.9568`。用户接受此 price mismatch 后才 one submit，no retry。
- 用户接受预计 11.9568 后，首次 Seedance Studio submit 在 task 创建前 HTTP 400：first/first+last 禁止显式
  `ratio=16:9`，输出比例应跟随 first frame。task_id 无、费用 0、calls 仍 8；不是模型失败。
- ratio 已修为 Studio `adaptive`，其余 Seedance/v5/8s/720p/no-audio/enhancement-off 不变；失败清空附件。
- `NEXT`：用户重新上传同一 v2 两次至 2/2；本修复 exact-SHA public gate 后 readback 并执行同一已授权实验一次。
- `c6143c1/32960467379` 三 job 全绿后，Seedance `adaptive` task `task_w6...ULvW` 有效创建并在 137s/100%
  NewAPI 成功。Studio 随后的 result fetch 403 不是生成失败；GET-only recovery 使用同一 task result URL 成功下载，
  无 POST/额外费用。实际扣 `$11.9566`；calls 9、production media 0。
- output SHA `acf68ba6...d56c4`，720p/H.264/yuv420p/24fps/193f/8.041667s/no-audio。人工 camera lock 与三大区
  simultaneous motion 初审通过；source fidelity `0.864923`、raw seam difference `0.060443`、720p 不过 production 门。
- `NEXT`：用户先观看本地原片并裁决 motion direction；认可后单独进入 no-generation source/seam/rendition proof，
  不认可则拒绝 sample。当前不重抽、不切模型、不接 runtime。
- 用户随后认可三主体方向但指出静区像雾层覆盖，选择基于现有成片做 Seedance video edit。Dragon 专用文档确认
  `seedance-2-5`、`video_operation=edit`、`video_with_roles(reference_video)`、`duration=-1`、`adaptive`；Studio
  主编排器视频参考 input 实测仅接受图片 MIME，故不冒充 Studio 编辑。
- v6.1 double-anchor edit prompt SHA `9cdcf28e...64ac8`、runner SHA `08834b8a...173b0`、source task
  `task_w6...ULvW`、immutable v2 Image1、output/status 唯一路径和 Key-last/no-retry 已冻结；恰好 1 POST/2 GET
  callsites。Video1 保留已有 motion，Image1 锁几何/材质，只改热图静区；编辑预计 `$12.0191`（8.041667 秒×
  $1.4946），但实际计费/最低时长待账单确认。
- `当时 NEXT`：独立提交/public gate；通过后向用户披露编辑费用，再 one POST。成功先审静区真实景内运动，失败不盲重试。
- v6.1 已在上述 public gate 后执行：source GET 成功，edit POST 返回 HTTP 400；task id 为空、费用 0、没有
  隐藏 task。旧 ratio 400 不等于本次错误，原 runner又没有保存 response body，故当前只裁决
  `request_or_schema_rejected_before_task_creation / exact_field_unknown`。
- `NEXT`：先提交/公共关闭 `sanitize_dragon_video_error.py`、三项红绿测试、400 diagnosis 与 revised runner
  digest。revised runner 尚未 POST；在取得精确 error body 或另一个可证伪修正前，不重发、不删双锚点试错、
  不换模型。
- 即梦官方 UI 的五模式已只读核对：Seedance 2.5 `智能编辑` 提供单 MP4/MOV 编辑视频槽 + 多参考素材槽、
  自动比例/时长和 720P，最贴合 Video1+Image1；全能参考/首尾帧会重新生成，智能多帧当前切换到 1.0 Fast，
  超长视频为 30s。尚未上传、购买积分/会员或生成。若后续选择官网，先读回上传后的实际积分与参数再决定
  一次调用，不先购买高价会员/API 套餐。
- 豆包工作首发 30 天标准套餐活动已由客户端与公开发布信息交叉支持，本机客户端显示 `标准套餐`；已执行一次
  Seedance 2.5 comparator。Skill 明确没有 video-to-video edit，抽取首尾帧+母图以 `image_to_video` 重生成；
  结果 SHA `e4b2f91...352cf`、778,877 B、8.041667s/720p/24fps/yuv420p + AAC。source→first `0.407604`、
  last→first `0.855418`，移动 `豆包AI生成` 水印；暖金光轨方向部分可取，但 source/色彩/三主体内部/全局环境/
  seam/audio/watermark 均失败，sample rejected、no retry。calls 增至 10，production media 仍 0。
- RQ-134 修正后续门：左 Rift、中央水晶/平台、右星图/能量场三主体全部增强，右侧独立不可遗漏；同时建筑、
  道路、地面反射、云/空气、星空纵深必须同步运动。光轨转冷蓝/青蓝为主，暖金只作低占比强调，且只是全局
  motion stack 一层。下一候选切到即梦官方 `智能编辑` 真 video edit；文件选择交由用户，避免自动 file picker
  失误，Codex 负责 readback/prompt/费用/单次调用门。
- RQ-135/即梦 v7 preflight：第一轮只用成功 MP4 + immutable v2 母图，不追加审美概念图；高级编辑可用时优先
  区域框选。v7 prompt 为 1,439 chars/4,115 bytes/SHA `edbc0d3...6f388`，同时冻结三主体/右侧与整体环境双硬门、
  冷蓝/青蓝光轨和禁止暖金主导/只加光轨。当前先公共关闭本证据批；公共成功前不让用户重复上传或点击生成。
- 用户截图确认高级编辑已解锁；RQ-136 随后纠正单帧方案。当前必须创建 `00:00 / 00:04 / 00:07` 三个独立
  帧标注，每次定位时间→暂停→画区域/方向→写该时点说明→“添加至输入框”。00:00 同时启动、00:04 同级峰值、
  00:07 循环回收；旧单帧 note `5e69688...9a419` 作废。文字工具不用，三个帧标注完成仍不等于生成授权。
- official 即梦 Smart Edit 已由用户手动完成一次有效生成；本次在 preflight batch 尚未 public-close 时执行，
  真实顺序已记录，不能倒写为 public-gate-first。2,000 字限制使实际主 prompt 压缩为 534 chars / SHA
  `d003f047...cff10`，三个 frame instruction 另有独立 digest；稳定 placeholder projection SHA
  `6dcd29d4...9d411`。长版 `edbc0d3...6f388` 只保留 design intent。
- raw output SHA `4d3660b...155b`、9,641,527 B、8.063991s、1280×720 H.264/yuv420p、193f、AAC；
  nominal `60/1`/average `11580/481`，不是发布 fixed-24。人工抽帧未见可见水印或明显 camera push/melt；
  left/center/right first→4s SSIM 为 `0.858797/0.917767/0.889054`，九宫格均变化，右场未遗漏。
- 两个硬门仍失败：v2 mother→first `0.889072`；adjacent DSSIM p95 `0.011254`、seam `0.046536 > 0.03`。
  当前裁决 `revise-candidate / not-adopted`；official Smart Edit/motion direction 保持 open，不把单样本外推为模型
  ceiling。
- repo 外 FFmpeg A–P 有界实验只修交付与 seam。最佳 J 为 7.5s/fixed24/no-audio/BT.709/2,991,793B、SHA
  `dadd7c3...a0b37`，但 mother→first 降至 `0.849216`、seam `0.042684` 仍 fail。强制首帧复制/settle 会引入
  duplicate/freeze/ghost 风险，按视觉意图停止追绿；所有 outputs/logs 留 repo-excluded research scratch。
- 当前 calls `11`、production media `0`、8E coverage `planned`。`NEXT`：先完成本证据批本地门与 exact-SHA
  三 job；公共闭环后只做零费用 source-identity fault split，把 geometry/edge、material/color 和 intended
  energy/light 分开。未形成新 source-side first/last/keyframe contract 前不付费重抽、不接 runtime、不进入 Account。
- RQ-137 固定近期顺序：先把当前 Portal Motion Polish 做完，再重开 GLM-5.3/GLM-5.3-Flash adoption gate 与
  bounded Coach 等 Agent 产品批；这不把 Portal 授权扩大为无界生成或降低冻结质量门。
- 本 evidence batch 本地聚焦 `42 passed`；无 DB 完整回归 `1873 passed, 146 skipped, 1 warning, 127 subtests`
  通过，两套 RAG、Harness dry-run、compileall、pip、SDK/secret/tracked-data、planned media audit、governance 与
  diff 全绿。146 skip 原因是 Docker Desktop 4.87 被损坏的 `sailor-ingest.sock` reparse point 阻断，端口
  `54329` 不可达；普通/metadata 删除与移动均被 Windows 拒绝，未重置 Docker、未触碰镜像/卷。真实 PostgreSQL
  必须由本批 exact-SHA `postgres-migrations` job 阻塞补证，不能冒充本地通过。

### 2026-08-27：Seedance 2.5 v3 视觉审查与 RQ-141

- v3 使用当前唯一 Portal source v2（SHA `8134c0ca...1a06e`）、首帧单锚点、`seedance-2-5`、
  `adaptive`、720p、12s、无音频，唯一生成 POST 为 task `task_kOuGllihQ9z92BRSLzQ5StE8zAZ1v6tW`；
  Codex 重启后通过 GET-only runner 恢复，恢复 POST 为 `0`。
- Task 5 external video calls 累计为 `12`，production media 仍为 `0`；v3 及其恢复输出全部留在 repo-excluded
  scratch 与 research evidence，不写入 `web/public/assets`。
- 输出 SHA `76be77750c8932666117e2e3ecdbb0e9fc1b3e845bb41f66532eb8802d1d2a04`，12.041667s、
  1280×720、24fps、H.264 High/yuv420p、无音轨；source→decoded first SSIM `0.989294`，
  first→11.9s SSIM `0.927839`。
- 视觉结论为 `research-candidate-rejected`：左 Rift 先小幅旋转后变成硬同心环；道路/裂隙下方流动在
  burst 前不持续；中央事件变成过曝白闪和横向穿屏直线；右侧在 burst 外近乎静止，near/mid/far 没有
  稳定的全幕呼吸，末帧也没有充分回到首帧相位。该输出证明请求通道和审查链可工作，不证明模型或方法达标。
- RQ-141 已追加：基础运动必须从首帧持续；burst 改为中央上下贯穿、低幅、约 2–3 秒的呼吸式蓄放，
  只轻柔激发水晶，不用跨画面直线、HUD、过曝或全局闪白；右场、道路、环境层在 burst 前后均保持独立且
  同级可感知运动。v3 不进入 runtime，下一动作是 source-side brief/合同修订，不立即重抽或换模型。

### 2026-08-27：RQ-141 v4 source-side contract preflight

- v4 已完成无成本 source-side 修订：常驻基础层从首帧开始，左 Rift、中央水晶/平台、右星图/能量场和
  near/mid/far 环境全程同时保持可感知运动；中央事件改为约 4.5–7.0 秒的低幅、圆润、局部纵向呼吸，
  不再使用容易诱发跨画面连线的 `gather/travel/circuit` 编排。
- 正向 brief 已固定在 `docs/assets/8e-portal/portal-motion-brief-v4.txt`，SHA-256
  `56ce81b8d508ae67edacfde6c1d846b9555d59ca0e9fafb80af3b88fd311620d`；请求 manifest 为
  `docs/assets/8e-portal/portal-motion-preflight-v4.json`。repo 外 runner 已静态解析为 0 个 PowerShell
  parser error、唯一 POST 路径 1，runner SHA 为
  `4aa7459cff78d462779137fed82d7edc84c0a0fc2d9ee539dbb4311b1c6a6dcc`；首次启动在 prompt digest 门因
  Windows CRLF/末尾换行差异安全停止，未发 POST，现已改为 LF 规范化并重新解析通过。
- 在 v4 preflight closure 时实际 POST 为 `0`，价格/余额/请求 readback 尚未执行，`image2_used=false`；随后
  用户“继续”授权并完成下方唯一一次 v4 调用。Image2 本轮不调用，因为现缺口是时间编排而非静态材质；
  production media 继续为 `0`，不改 runtime。
- v4 contract/preflight 提交 `0006858` 的 Actions `33078261349` 已完成 exact-SHA 三 job（pytest、真实
  PostgreSQL migrations、packaging-smoke）并全部成功；这只关闭文档/门禁证据，不关闭视觉采用门。
- Dragon 当前价格页 readback 为 Seedance 2.5、720p、文本/图片参考按秒 `¥1.494570`，12 秒估算 `¥17.934840`；
  该价格只用于本次单次调用预算，不代表已扣费。
- `NEXT`：若用户明确允许下一次付费生成，先重新 readback 价格、schema、源图 SHA 与 prompt digest，随后只
  运行 v4 一次；无授权不弹 Key/不 POST。生成后必须独立审查 source identity、三大区与 near/mid/far 全幕
  运动、loop seam、编码和人工视觉，再决定是否采用。

### 2026-08-27：Seedance 2.5 v4 视觉审查与 RQ-142

- v4 已按 manifest 只 POST 一次并成功下载：task `task_s03TcAumrRVriOhr3qj7RxigZqBRLnYF`，输出 SHA
  `1fab5d0f10efe13402f8d31ddfa136ecc68c19875ca4d6a092982d4a1f49cb02`，12.041667s、1280×720、24fps、
  H.264/yuv420p、无音轨；Task 5 external video calls 累计为 `13`，production media 仍为 `0`。
- 无成本抽帧和指标确认：source→first SSIM `0.989914`、first→last SSIM `0.994464`；每 0.5s MAD 的
  left/center/right 为 `0.005851/0.014625/0.004653`，near/mid/far 为 `0.008367/0.012052/0.004717`。
  变化主要集中在中央，并不代表全幕运动成立。
- 视觉裁决为 `research-candidate-rejected`：中央平台在事件中变成大面积发光圆顶，左 Rift 只有低价值变化，
  右星图/地形与远景环境几乎静止，基础道路/接缝/反射/云空气没有持续动效。该结果是 prompt/mode 语义偏差的
  可复现证据，不把模型能力直接判死。
- RQ-142 生效：暂停首帧盲抽，先拆解 prompt/mode fault。后续要把可见运动载体写成具体局部行为，明确平台和
  水晶几何不可变，并重新判断首帧单锚点是否适合整幕运动；未完成新合同与方法裁决前不再付费重抽、不接 runtime。
- v4 rejection audit 提交 `c964016` 的 Actions `33083670925` 已完成 exact-SHA 三 job（pytest、真实
  PostgreSQL migrations、packaging-smoke）并全部成功；该公共闭环只确认失败证据可重建，不改变视觉拒绝与
  `production_media=0`。

### 2026-08-28：RQ-142 prompt/mode fault split

- v3/v4 连续复核后，当前结论为“prompt 有责任，首帧单锚点也存在结构性区域/时间控制缺口，模型上限仍
  unknown”。v4 的 source/seam 技术指标不能抵消中心圆顶、右场静止和环境无持续运动的人工失败。
- 三路线比较已写入 `docs/plans/2026-08-28-8e-portal-motion-method-fault-split.md`：A（首帧 I2V）暂停，B（真实
  视频编辑 + 时间/区域控制）作为下一优先候选，C（锁母图的纹理/位移型混合制片）作为可控 fallback；旧 C-line
  线条/HUD proof 不被重新包装成成功。
- `NEXT`：先冻结 B 的窄版三时间点 mask/prompt contract 并做 no-cost preflight；在此之前不再付费抽帧、不切
  模型、不接 runtime，Image2 只在出现明确材质/遮挡辅助需求时使用。

### 2026-08-28：B1 Smart Edit 窄版 contract preflight

- B1 已冻结：已有 Seedance 视频只作 temporal anchor，v2 母图只作 immutable geometry/material anchor；主 prompt
  压到 1,977 字符，三份 `00:00/00:04/00:07` frame annotation 分别绑定常驻启动、同级峰值和回收，不把
  中央平台标成可变体积。
- manifest `docs/assets/8e-portal/portal-motion-preflight-b1-smart-edit.json` 已绑定 Video1 SHA、母图 SHA、
  prompt/annotation digest、`adaptive/720p`、8.041667s 和音频策略；未上传、未调用、未扣费。
- 即梦登录标签已找到且初始页面显示为 `全能参考`，但后续 DOM/CUA/截图读取连续超时；没有点击、上传或改变
  页面状态，manifest 已记录 `mode_readback_status=blocked_extension_timeout`。
- `NEXT`：只做 B1 的页面模式/素材角色/积分/音频 readback；若输入无法表达三时间点区域控制，则直接记录
  request/mode failure，不发起付费任务。若 readback 通过且用户继续授权，最多执行一次 B1。

### 2026-08-28：B1 不重复执行，转向混合材质 proof

- 复核确认即梦 Smart Edit 已经真实执行过一次相同的 Video1 + Image1 + `00:00/00:04/00:07` 形态；B1 仅是
  prompt ablation，不是新模式，因此标为 deferred、未上传、未付费、未调用。
- `docs/plans/2026-08-28-8e-portal-motion-hybrid-material-proof-design.md` 已冻结 C'：母图锁定结构，使用
  遮罩内低频纹理位移/折射/分层视差和确定性 frame clock，禁止线条/HUD/平台体积变化；先做 8s research proof，
  通过后再决定是否延长到 10–12s。
- `NEXT`：执行 C' 的本地 contract/TDD 与静态 proof 设计，不调用 Image2/视频模型；只有发现具体材质纹理缺口时，
  才单独评估局部 Image2/Photoshop tile。

### 2026-08-28：C′ proof 退出与 Kling v3 Omni 候选

- C′ 已完成 192 帧本地 proof：结构、全区覆盖和技术编码可控，但正常观看下运动过轻、source-pixel mask 有贴层
  风险，正式标为 `research-proof-rejected`；不再通过 opacity/位移追绿，也不接 runtime。
- 下一候选切到中转站 `Kling v3 Omni` 的单图片引用模式：只传 v2 母图作为 image identity anchor，按该模型的
  `metadata.image_list` + `<<<image_1>>>` schema 编写专用 prompt；不上传旧视频、不复用 Seedance prompt，
  不把 B1 Smart Edit 重跑。
- `NEXT`：先完成 Kling v3 Omni 的价格/schema/source/prompt/唯一调用 preflight；未过门前不上传、不付费。

### 2026-08-28：Kling v3 Omni image-reference preflight

- 已核对 DragonAPI Kling v3 Omni 文档与当前价格：`model=kling-v3-omni`、`mode=std`（720P）、`duration=8`、
  `aspect_ratio=16:9`、`audio=false`，使用 `metadata.image_list` + `<<<image_1>>>`；价格 `¥0.462000/s`，
  8 秒估算 `¥3.696`。
- 专用 prompt 已固定为 1,833 字符，SHA `eeae44fdf85b5dbf8092d818ea4b5981543bece7f3f249d71432e37feff4df05`；
  runner parser 0 error、唯一 POST 路径 1，runner SHA `5803f41b04aa74d022924b03b7aa8ee20f041db8580c8b94c8fd569b58875347`。
- 只传确认母图，不上传旧视频；manifest 的 `paid_call_authorized=false`、`post_attempts_observed=0`、
  `production_media=false` 保持不变。下一步仍需页面/账户实际 readback 后再决定是否调用。
- `cc35fae` / Actions `33098493865` 的 exact-SHA pytest、真实 PostgreSQL migrations、packaging-smoke 三 job
  已全部成功；Kling preflight 公共证据闭环，尚未创建 task。

### 2026-08-28：Kling v3 Omni image-reference 结果审查

- Kling image-only task `task_7iQRNXGQRrnbk1KdW6WYDpG1dRSoZHC0` 只 POST 一次并下载成功，输出 SHA
  `3eb0720c1b80d02ab43f8975f765c0444b1dd40239fad4fe5bfe43ff483c7fc6`；8.041667s、1280×720、24fps、
  H.264/yuv420p、无音轨，Task 5 calls 累计为 `14`，production media 仍为 `0`。
- source→first SSIM `0.860618`，left/center/right 每 0.5s MAD `0.018846/0.007312/0.006353`；视觉上左 Rift
  变成厚重塑料感圆环，中央强光柱，右场和整体环境近乎静止，暖金星点也偏装饰化。
- 裁决为 `research-candidate-rejected`：Kling image-only 仍不能保持母图身份或实现全幕持续运动；这不是编码/下载
  问题，也不证明 Kling 所有参考模式的能力上限。
- `NEXT`：停止 image-only 抽卡；先评估真正的 reference-video/多模态模式（包括视频 URL 获取、隐私/费用、schema
  和可控性），或在明确证据下选择其他支持视频参考的模型；未完成 preflight 前不再付费。

### 2026-08-28：Kling v3 Omni video+image B2 preflight

- B2 改用 Kling `video_list(refer_type=base)` + `metadata.image_list`：执行时先对历史 Seedance success task
  `task_w6gg...ULvW` 做一次 GET-only，signed result URL 只在内存中传给 Kling，不写盘；v2 母图继续锁视觉身份。
- 专用 prompt 1,856 字符，直接禁止 B1 的 solid torus、isolated gold stars 和 central laser block；SHA
  `6669494364216c8ac366ac4c9ee2f354632b438e253625dbdadee1299eb86b56`。runner parser 0 error，两个 GET
  路径（source + polling）、唯一 POST 1，runner SHA `feee4f77e5b7a701d268292386958bfcf429792dfca1ee8112ce7392d37cad20`。
- 请求保持 `std/720p`、8s、16:9；有 `video_list` 时按 Kling 文档省略 audio 字段。预计 ¥3.696，但实际视频参考
  计费以平台回执为准。当前 source GET/POST 均为 0，production media 仍为 0。
- `NEXT`：先独立提交/public gate；通过后用户在本机输入 Key，若 source task GET 无有效 URL 则在 POST 前停止，
  否则只执行一次 Kling B2。

### 2026-08-28：Kling v3 Omni video+image B2 结果与方法复盘暂停

- B2 已按合同只创建一个付费 task `task_BxImX98XdGOIwIGRzKgRYUZzEmXvbVMe`；首次轮询遇到
  `HttpRequestException`，恢复脚本两次 GET 重试后完成下载，`post_attempts=1`、
  `recovery_post_attempts=0`，未产生第二次计费。输出 SHA
  `5a9509ee3efdd2dbc0e8264bba88bba1315f3880e2c0932c8ac56da56f02cbba`。
- 技术检查通过：8.041667s、1280×720、24fps、H.264 Main/yuv420p、无音轨、无重复解码帧；母图→首帧
  SSIM `0.989310`，首尾 SSIM `0.995321`。这些只证明传输/首帧身份/编码，不代表视觉采用。
- 视觉裁决为 `research-candidate-rejected`：左 Rift 变成厚塑料环，中央变成硬亮柱，右星图/地形和远景明显
  偏静，路面/接缝/反射/云空气没有形成 MotionSites 类全幕材质运动。左/中/右每 0.5s MAD 为
  `0.008926/0.007587/0.004271`，右侧和 far 层明显落后；高首尾相似度不能掩盖运动载体错误。
- 根因拆分已写入 `docs/plans/2026-08-28-8e-portal-motion-kling-b2-result-review.md`：
  video+image 模式缺少可靠区域/时间控制；temporal anchor 本身动作不均衡；prompt 的 `vertical swell`
  等语义仍会诱发 beam/ring/star shortcut；母图不是当前首要问题；MAD 不能替代人工材质审查。
- `docs/assets/8e-portal/portal-motion-candidate-kling-v3-omni-video-image-b2.json` 保存完整 body-free
  结果与证据；`production_media` 仍为 `0`，8E coverage 仍为 `planned`。
- 用户要求停下完整复盘；当前切换为 `method-review-hold`：暂停新视频生成、模型切换、runtime 接入和
  Account 推进。恢复时先做可见分层/材质载体的 no-cost proof，再评估是否存在真正支持相同区域/时间控制的
  视频编辑模式；不以更长 prompt 或新品牌抽卡替代方法决策。

### 2026-08-28：source-derived layer assets proof v1

- 用户指出上一版 proof 像给母图蒙纱且清晰度下降；新增 RQ-143，要求底图不动、只移动可解释的源图亮部/材质层，
  禁止 source duplicate、global tint/veil 和建筑边缘双影。Image2 代理当前不可达 `127.0.0.1:7890`，本轮未调用。
- 新建 `experiments/portal_layer_assets_proof_v1/`，通过高通蓝青亮部提取、羽化 mask 和双相位局部位移完成
  1920×1080/24fps/8s/no-audio 本地 proof；外部模型调用 `0`。输出 SHA
  `077bac71f4e2a94edc525222ee014bcfb6ea2dcd3f4ae9a27460d164ac2d350d`，1,905,994 B、192 帧、yuv420p/BT.709。
- 机械结果：source→first SSIM `0.997556`，first→last SSIM `0.998919`，无重复帧；left/center/right 每 0.5s
  MAD `0.002199/0.001487/0.001743`，near/mid/far `0.001412/0.003149/0.000866`。结构/清晰度/无纱罩门通过，
  但人工观感仍偏弱，真实遮挡/背板与独立材质 plate 尚未具备；裁决为 `foundation-pass-with-visual-boundary`，
  不是 adopted Portal loop，`production_media=0`。
- `layer-assets-and-occlusion-proof` 细分下一项为 `material-plate-generation-gate`：先补 Rift/右场/道路反射的独立
  plate 与可移除遮挡背板，再决定是否值得新一轮视频模型调用；当前不继续 opacity/filter 调参、不接 runtime、不进入 Account。

### 2026-08-28：分层材质 proof v2 结果

- 依据复盘后的 Phase 0/1 合同，新建 `experiments/portal_layered_material_proof_v2/`；先红灯后绿灯，
  聚焦测试 `3 passed`。HyperFrames 0.8.14 GPU/单 worker 在仓库外完成 192 帧、8s/1920×1080/24fps
  研究视频，外部模型调用 `0`。
- 技术检查：输出 SHA `94ba1990f29905d7d58eb714878a09cefae400d7eb18c20f7747fa0950c4c07`，H.264/yuv420p/BT.709/
  无音频，source→first SSIM `0.950515`，first→last SSIM `0.997690`，无重复帧；left/center/right 每 0.5s
  MAD `0.008899/0.007489/0.011029`，near/mid/far `0.008937/0.008470/0.010011`。
- 人工裁决为 `research-proof-rejected`：结构和覆盖门通过，但正常观看仍主要是亮度/纹理调制，不是 Rift、道路、
  水晶折射、右场星图和近中远空气的真实空间流动；继续增加 opacity 会放大 source duplicate 的贴层/ghosting 风险。
  完整证据见 `docs/assets/8e-portal/portal-motion-candidate-layered-material-v2.json`。
- `method-review-hold` 继续有效，但下一项不再是滤镜调参，而是 `layer-assets-and-occlusion-proof`：先制作可移除的
  inpaint 背板、遮挡边界和至少六个真实材质层，再做一次有界本地 proof；不调用外部视频模型、不接 runtime、不进入 Account。

### 2026-08-28：source-derived layer assets proof v1 收口

- 高通亮部提取、羽化 mask 和双相位局部位移在 1920×1080 版本保持母图清晰，source→first SSIM `0.997556`，
  首尾 SSIM `0.998919`，无重复帧；结构/无纱罩门通过。
- 运动仍偏 restrained shimmer，路面、右场和 far 层缺少足够可感知的材质流动与真实遮挡；裁决为
  `foundation-pass-with-visual-boundary`，不是 Portal adopted media。Image2 代理当前为不可达 `127.0.0.1:7890`，
  本轮未调用。
- `layer-assets-and-occlusion-proof` 的下一细分为 `material-plate-generation-gate`：先准备独立的 Rift/右场/道路
  反射 plate 和可移除遮挡背板，再决定是否值得新一轮视频模型调用；不继续调同类 opacity/filter。

### 2026-08-28：source-derived visible motion variant rejected

- 为回应“看不到变化”做了一个有界 `replace-shifted` 对照（960×540、motion_scale 2.5）：先以局部模糊近似背板，再
  移动源图高光。它确实更容易看到运动，但用户复核确认 Rift/道路/晶体边缘仍有重影和软化，右场/far 仍偏静；因此
  `portal-motion-candidate-layer-assets-visible-v1.json` 判为 `research-proof-rejected`，不继续提高倍率。
- 这次进一步确认：只要移动的像素原本仍存在于母图，位移副本就会造成 ghosting；要同时做到“明显、清晰、无重影”，
  必须有独立透明 plate + 清洁 backplate/occlusion，而不是 source-derived shift。
- 新增 `docs/plans/2026-08-28-8e-portal-material-plate-generation-gate.md`；当前下一检查点仍为
  `material-plate-generation-gate`，先准备独立 Rift/右场/道路反射/中央折射素材和背板。Image2 代理仍不可达，
  未调用视频或图像模型；runtime、Account 和 production_media 保持不变。

### 2026-08-28：独立材质 plate 预检结果

### 2026-08-28：masked-inpaint-plate-proof 结果

- 本轮用内置 ImageGen 的 Rift 清洁背板候选和一张独立 RGBA Rift 流体层，完成了 960×540、24fps、8 秒、无音轨的本地 bounded proof；未调用视频模型、DragonAPI、Image2 或远程服务。
- 背板只在 Rift 内部的有界遮罩中使用，母图其余区域保持 source-owned；透明层只在该遮罩内做周期位移。输出 SHA 为 `329ea1e797a3774ab7fc8543b8cdfcf266d26282833a07c5236c76744e54aff3`，192 帧、H.264/yuv420p，`source_first_ssim=0.9126610023`、`first_last_ssim=0.9979960032`；这些指标只证明局部合成和循环技术链，不代表视觉采用。
- 人工复核判定 `research-proof-rejected`：透明 Rift 层增强后像贴上的蓝色带状素材，降低透明度则几乎看不见；ImageGen 背板整图还有轻微差异，因此不能替换确认母图。完整结果见 `docs/assets/8e-portal/portal-motion-candidate-masked-inpaint-plate-v1.json` 与 `docs/plans/2026-08-28-8e-portal-masked-inpaint-plate-proof-result.md`。
- 下一动作：只做 source-aware 人工/分段材质制作或区域遮罩视频编辑的有界方法裁决，不再批量生成通用 plate、不调同类 opacity、不付费重抽、不接 runtime；`production_media` 保持 `0`。

- built-in imagegen 做了 5 个窄范围 plate 试验，没有上传母图、没有视频调用。Rift 第一张是完整蓝色水团，第二张 wisps
  仅保留为研究控制场；右场/道路带宽泛底色，晶体生成碎裂几何，均不直接采用。
- 直接叠加测试暴露贴纸/蓝雾/几何替换风险；完整 body-free 路径、SHA 和裁决见
  `docs/assets/8e-portal/portal-motion-plate-imagegen-audit.json` 与
  `docs/plans/2026-08-28-8e-portal-material-plate-generation-result-audit.md`。
- `material-plate-generation-gate` 未通过，`masked-inpaint-plate-proof` 已完成并判为 `research-proof-rejected`：
  背板/遮罩机械边界通过，但透明 Rift 层在可见强度下呈贴纸/蓝带、在低强度下不可见；ImageGen 整图编辑存在
  轻微全局差异，不能成为新母图。下一动作只评估 source-aware 人工/分段材质制作或区域遮罩视频编辑；在裁决前
  不再批量生成、付费重抽、接 runtime 或进入 Account，`production_media` 保持 `0`。

### 2026-08-28：RQ-146 官方/授权壁纸路线激活

- 用户明确“转战”，Wan first-frame reopen 停止，不再寻找 API Host 或发送第二次 POST；第一次 404 仍是
  no-task/request-routing 诊断，不是质量结果。
- 用户提供的 `animated-demacia.webm` 已完成只读候选审计：1920×1080、15.04s、25fps、VP8 WebM、无音轨，
  连续运动可见但原生首尾不无缝；来源声称为 Riot League Displays，但公开再分发许可尚未核验。
- 下一动作改为 `official-wallpaper-fallback`：region wallpaper catalog + no-I/O local preview；Portal 选择
  地区后加载本地动态壁纸，Account 使用独立静态壁纸，先过来源/许可、格式/体积、浏览器/移动端/reduced-motion
  与 loop 门，`production_media` 继续为 `0`。

### 2026-08-28：Universe crest 与 Bandle City 资源差异

- 用户确认地区选择应独立成类似国服大区选择的卡片；Universe 页面提供 13 个官方地区 crest，已纳入本地研究预览。
- Bandle City 在 Universe 页面存在网页动态背景，但 League Displays 当前只有静态资源；因此 region crest、Account
  静态图和 Portal 动态壁纸分别建模，网页动态效果若没有允许再分发的独立文件只作参考，不直接抓取注入。
- 用户提供的高细节 3D 徽章更接近 LoR 详细 region emblem；暂作为 selected-region hero 候选，不替换已核验的
  Universe crest，也不改变当前 Portal/Account 业务控制流。

### 2026-08-29：RQ-157/158 Region Focus Rail 与 Account handoff 获授权

- 用户批准把旧 scene-preview + 13-card grid 改为 13 区横向 Focus Rail：rail 保留简单 Universe crest，上方 selected
  hero 显示高细节本地研究徽章并在失败/缺失时回退 Universe crest；主 CTA 位于 rail 正下方，文案严格为
  `进入登录界面` / `Continue to sign in`，不插入地区名。
- presentation identity 与 media readiness 正式拆分：13 个地区都可选择、写入 wallpaper-lab URL 并传入 Account；
  motion rendition 是可选证据，缺失时使用 poster，不再以 disabled 身份按钮假装两者相同。该 presentation region
  不等于 Riot API routing region，不能改变 Account 表单的 americas/europe/asia/sea 语义。
- Portal→Account 采用有因果的 handoff：selected hero/rail/CTA 收束，地区化 aperture 接管，再由 Account 背景和登录
  内容进入；正常约 760–1000ms，generation 防重入，reduced-motion/Save-Data 立即提交并只短暂交叉淡入。
- 班德尔城 Account 静态背景改用用户新提供的 `4e498e9f..._fw1200webp.webp` 本地 sibling；源文件 1200×600、
  SHA-256 `f1da72d0e8a591e31a534d0bf988dfb0fc2d6e85434c203e9a5c52167f4527cb`。当前仍为
  `rights=unverified/research-only`，正式推广前要核验更高分辨率同源图与再分发权。
- 设计与 TDD 顺序已固定在 `docs/plans/2026-08-29-8e-region-focus-rail-design.md` 和对应 implementation plan。
  当前唯一下一动作是先补 RED unit/E2E contract，再实现；Workbench、默认 `/`、媒体采用状态与
  `production_media=0` 不变。

### 2026-08-29：RQ-157–160 Region Focus Rail / copy / handoff 本地实现

- 13 区 focus rail、selected detail hero/Universe fallback、generic sign-in CTA 与 optional media/poster contract 已实现；
  直接 Account URL、copy/reload/Back 和 `from=wallpaper-lab` 保持一致，presentation region 仍不进入 Riot API routing。
- 新建 13 区双语 presentation-copy registry；界面移除 codec、时长、候选/动态状态等内部验收词。当前氛围句全部是
  RiftCoach 自写文案，不声明为 Riot 官方或英雄逐字引语。
- shared journey shell 现在驱动 `closing → background-handoff → idle`，aperture 从选中 rail 附近接管，Account 背景/
  地区身份/表单分层进入，focus 在 overlay 退出后移动；reduced-motion 即时提交。
- Portal 展示标题固定为中文 `从一方之地，`／`启程。`、英文 `Begin from a region`／`of your choice.`；Account 固定为
  中文 `选择一位`／`召唤师。`、英文 `Choose a`／`player.`。完整 heading 仍作为无障碍名称，视觉行不再依赖随机折行。
- 本地验证：frontend unit `297/297`、完整 frontend E2E `49/49`、typecheck 和 Vite build 通过；桌面与 390px 中英文视觉
  复核通过。Workbench 未改、未提交/推送、研究媒体仍 `rights=unverified`、`production_media=0`，因此 canonical
  `8e-productization` 继续为 `in_progress`。
- 唯一下一动作：用户视觉复核后，继续 Portal/Account 的来源/许可、production rendition/fallback 与最终响应式验收；
  当前不进入 Workbench。

### 2026-08-30：RQ-161 Account panel / control typography hygiene

- 已完成用户要求的两项局部修补：桌面 Account 右侧表单 panel 通过 `top: clamp(-2rem, -2.5vh, -1rem)` 上移，
  不占用既有 handoff animation 的 `transform` 通道；`<=760px` 明确恢复 `top: 0`，避免窄屏出现额外偏移。
- Riot ID input 与“查询区域”“这是你的账号吗？”两个 select 统一为 Manrope body、560 字重、0.95rem；三条
  字段 caption 统一为 0.68rem/1.2，消除原生 input 回退 Arial 造成的视觉断层。
- 本地证据：Account focused unit `3/3`；完整 frontend unit `297/297`；完整 Playwright E2E `50/50`；
  TypeScript/Vite build、Impeccable layout detector、desktop/mobile live DOM 与 `git diff --check` 通过。
- 边界：Workbench 未改；Auth、Riot routing、URL/媒体合同与 `production_media=0` 不变；8E 仍为
  `in_progress`，下一动作仍是用户视觉复核后继续媒体来源/许可、production rendition/fallback 和最终响应式验收。

### 2026-08-31：RQ-163 Agent 主线交接与 README 事实版

- 用户确认 Portal/Account 当前展示切片已达到阶段性收口点，要求把执行重心转回 Agent 主线；旧的两地区/第三地区
  扩展建议由 RQ-157–162 取代，只保留在历史记录中。
- 本批已完成 README、路线镜像、活动计划和八维学习材料的事实对齐。README 现在明确区分：8A–8D 的 Agent/Runtime/
  Evidence 底座已完成；8E 仍在产品化；GLM-5.3 尚未通过 G53 闸门；Web 尚无受限 Review-grounded Coach；8F、完整
  多源黄金切片、安全部署和作品集仍未完成。
- 交接保持 `8e-productization / in_progress`，不提升 `production_media`，不改变 Workbench、Auth/RSO、Riot routing、
  默认模型或媒体运行时。下一候选为 `g53-0-no-io-audit`，本批不读取 Secret、不调用 Provider/Riot/OP.GG，也不修改
  `app/` 与 `web/`。

### 2026-08-31：RQ-164 G53-0 无 I/O 审计

- 本批按 RQ-163 的下一候选执行了 G53-0：只读 G53 设计/ADR、`.env.example`、`compose.yaml`、Zhipu
  settings/Adapter/probe、CI 和历史脱敏结果；没有创建 OpenAI 客户端或发送任何 Provider/Riot/OP.GG 请求。
- 产品默认合同仍是 `LLM_PROVIDER=zhipu`、`LLM_DEFAULT_PROVIDER=zhipu`、`LLM_MODEL=glm-5.2`；
  现有 Adapter 在 `app/providers/zhipu.py` 固定 `thinking.type=disabled`，非空 `reasoning_content`
  会 fail closed，不能直接承载 GLM-5.3 的 `enabled + low` 语义。
- 本机 `.env` 仅做遮罩式非敏感字段核对：文件被忽略，Key 只确认存在且未输出/记录；其 provider/端点/model
  形态显示为 `glm`、Coding Plan 端点和 `glm-5.2`，其中 `glm` 会被当前 `load_zhipu_settings()` 的严格
  `provider=zhipu` 检查拒绝。这个配置接缝问题不等于模型质量失败，也不授权修改用户 `.env`。
- 账号类型/Plan 权限、实际 endpoint/region、正式 GLM-5.3 model ID，以及 `enabled + low` 的真实可用性
  均没有本地可核验的非敏感证据；用户历史线索与旧文档快照只作为待核对信息，不能互相冒充当前准入证据。
- 结论为 `G53-0 completed-local / adoption blocked-deferred`。`production_media=0`、Workbench、Auth、
  路由和默认模型不变；后续需先取得非敏感账户信息，再另行决定是否执行 G53-1 离线 profile TDD。

### 2026-08-31：RQ-165 G53-1 普通 API 适配档案离线 TDD

- 用户补充并核对官方资料：GLM-5.3-Flash 的正式模型标识为 `glm-5.3-flash`，普通开放平台
  Chat Completions 使用 `https://open.bigmodel.cn/api/paas/v4/`；Coding Plan 是独立入口，
  不能把其端点或额度规则套到普通 API。该公开合同不证明本地账号余额、权限或领域质量。
- `app/providers/zhipu_profiles.py` 新增不可变、按模型精确解析的 thinking profile：保留 GLM-5.2
  disabled，增加 GLM-5.3/Flash 的 enabled + low；未知测试模型继续走历史 disabled 回退。
  `ZhipuProvider`、受控 capability probe 与 CLI 均使用 profile 生成请求，已知模型的结果文件名隔离，
  不允许调用方覆盖安全思考参数。
- Flash 文本/结构化响应中的非空 `reasoning_content` 只在适配器内消费并丢弃；非字符串和带工具调用的
  不可回传 reasoning 继续以安全错误 fail closed。单 ToolCall、并行 ToolCall 拒绝、finish/usage、
  structured JSON 和错误脱敏保持既有合同；未扩展多模态或流式中立消息。
- 本地证据：新增 profile/provider/probe/CLI 测试，聚焦回归 `70 passed, 29 subtests passed`；
  `compileall`、`git diff --check` 与 `scripts/check_project_governance.py` 通过。没有读取或输出 Key，
  没有真实 Provider/Riot/OP.GG 调用；默认 `zhipu`/`glm-5.2`、Workbench、Auth、路由和
  `production_media=0` 保持不变。
- 当前仍处于 Stage 8 / `8e-productization`，G53-1 仅是本地适配合同完成；唯一下一步为
  `g53-2-exact-sha-ci`。CI 通过后才讨论经明确授权的 G53-3 三次协议门，不能把本批绿灯写成生产成熟度。

### 2026-08-31：RQ-166 G53-2 exact-SHA 公共 CI

- G53-1 的 9 个 Provider/配置/probe/CLI/测试文件被隔离为提交
  `0f97b92683e4981842e745a695864deb611bb630`；没有把 Portal、Account、Workbench、截图、资产或其它脏文档
  内容带入该提交，现有 workflow 也没有改动。
- Actions run `33325222755` 的 head SHA 与提交精确一致；`pytest`、`postgres-migrations`、
  `packaging-smoke` 三个 job 均 `completed/success`，公共 pytest 汇总为
  `1912 passed, 145 skipped, 1 warning, 127 subtests passed`。
- G53-2 只关闭精确提交的公共可复现性。CI 全程 no-I/O，没有读取/输出 Key、真实 Provider/Riot/OP.GG 调用，
  没有修改 `.env`、默认 `zhipu`/`glm-5.2`、Workbench、Auth、路由或 `production_media=0`；账号权限、真实
  协议、领域质量和生产准入仍未知。
- 当前治理指针转为 `8e-productization / g53-2-exact-sha-ci / completed-public`；唯一下一步是等待用户
  单独明确授权的 `g53-3-bounded-protocol-gate`（最多三次真实协议调用）。完整 8E、G53-4 和 8F 仍未完成。

### 2026-08-31：RQ-169 G53-3 重开成功

- 用户确认已在普通 API Keys 页面重新创建 Key，并把本机 `.env` 的 provider、普通端点和模型配置改正；本轮不读取或输出 Key 值。
- 进程预检确认 `zhipu`、`https://open.bigmodel.cn/api/paas/v4/`、`glm-5.3-flash`；OpenAI client `max_retries=0`。
- `adapter_protocol` 的 A1 结构化合同通过（1 次调用），A2 Agent 工具往返通过（2 次调用、1 次 ToolCall/执行）；
  总计 `calls_used=3/3`、`admitted=true`，结束原因分别为 `stop` 与 `tool_calls → stop`。
- 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_retry2.json` 的 SHA-256 为
  `1273eab75d4e4b1357a555db3c7c4472c85797daaf48006b34b986380a06a65a`，schema 与聚焦回归 `36 passed` 通过；
  只保留状态、计量和摘要哈希，不保存响应正文、reasoning、Key 或完整请求标识。
- G53-3 标记 `completed-public`，不自动启动 G53-4；Stage 8/8E、默认模型、Workbench、Auth、路由和
  `production_media=0` 保持不变。下一步需用户单独授权 G53-4 新鲜领域采用门。

### 2026-08-31：RQ-170 G53-4 新鲜领域采用门本地拒绝

- 用户明确授权后，先以 no-I/O preflight 校验全新的匿名 recent-form fixture、三案例 Dataset、Input Plan、
  Prompt/Context snapshot、G53-3 协议结果和调用/Token 硬预算；预检外部调用为 `0`。
- 真实门只执行一次。首个正常复盘案例在第 1 次 Provider 响应因 `unsupported_parallel_tool_calls` 被 Zhipu
  Adapter fail closed；没有规范化响应、工具执行、Evidence 或报告发布，用户注入与知识注入两例按首错停止跳过。
- 领域调用为 `1/12`、规范化 Token 为 `0/12000`；连同 G53-3 的 `3` 次协议调用累计 `4/15`、`1115` Token。
  金额因缺少可稳定核验的当前 Flash 单价而记录为 `unknown`，没有用旧模型价格替代。
- 不可变脱敏结果为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_v1.json`，SHA-256
  `ae4c54f421bd716f14d01e0fbf32a020f93b313d111b2ddb1832773ad53b7f45`；不含 Key、Prompt、响应正文、
  reasoning、完整请求标识或两条注入 marker。
- G53-4 结论为 `completed-local-rejected`、`admitted=false`。G53-3 的普通协议通过仍有效，但 GLM-5.3-Flash
  不进入默认模型；本地新资产/runner 尚无 exact-SHA 公共 CI，因此不能描述为公共闭环。Workbench、Auth、路由、
  前端、DeepSeek 证据和 `production_media=0` 均未改变；不自动重跑当前考卷。

### 2026-08-31：RQ-171 适配器合同修复与 G53-5 待执行

- 用户明确要求在普通 API Key 已可用后，先修复 GLM-5.3-Flash 适配器，再做尽可能全面的真实能力验证；这不是
  对旧 G53-4 考卷的重跑，也不是默认模型切换授权。
- 本地实现已把 Flash profile 固定为 `thinking=enabled`、`reasoning_effort=max`、`clear_thinking=false`；
  Provider-neutral `reasoning_content` 只作为内部字段保留并在工具回合精确回放，公开投影不暴露原文；Zhipu
  Adapter 现在接受多个 ToolCall 并保留顺序，由 AgentLoop 逐个受控执行，能力声明不虚报并发。
- 当前只有离线合同/回归证据；新的 `g53-5-fresh-flash-capability-gate` 真实 Provider 测试尚未执行。
  执行时必须使用新的输入/输出身份、有界预算、脱敏结果和不可覆盖路径，旧 G53-4 结果保持原样。
- canonical 仍为 Stage 8 / `8e-productization` / `in_progress`；8F 尚未开始，`production_media=0`；默认模型、
  `.env`、Workbench、Auth、前端、Riot routing 和历史 Provider 结果不变。

### 2026-08-31：RQ-172 G53-5 全能力矩阵本地真实观察

- 新实验结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_capability_matrix_v1.json`
  已落盘（SHA-256 `BFFF564CF4C6E7B2DD05F88542FD7A872D1565442B6D35C795EC6892CC84BE0C`）。在 dirty worktree
  条件下，HEAD 与 `origin/main` 均为 `0f97b92683e4981842e745a695864deb611bb630`，`public_ci_confirmed=false`。
- 真实矩阵共 `11/11` 次调用、`46,151` tokens，8 个案例中 `7/8` 通过。adapter core、AgentLoop、多 ToolCall
  顺序与思考回放、domain development、vendor text stream、vendor multimodal 均有通过/观察证据；
  `production_admitted=false`。
- F7 的 vendor `tool_stream` 在 `max_tokens=512` 以 `incomplete_chat_response`/`length` 结束，属于本次有界
  预算下的未完成响应，不足以证伪能力；F4 的 `cached_input_tokens=0`、`cache_status=unproven`，不能宣称缓存命中；
  F8 是 vendor-only 观察，不进入 provider-neutral 生产合同。
- 该结果只关闭本地真实矩阵观察，不关闭公共 CI、领域采用、生产成熟度或 8E。当前等待用户决定 Agent 主线下一项；
  不重跑 G53-4，不改默认模型、Workbench、Auth、前端或 `production_media=0`。

### 2026-08-31：RQ-173 G53-5 F7 工具流上限独立诊断

- 新建独立 follow-up 结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_g53_5_tool_stream_followup_v1.json`，
  SHA-256 为 `105722b2af2a4cbccc1b45a29b67a0864545aeeebb18f815ae7b62d6ace1d1a56`；experiment_id 为
  `49ddb2504c08d3d066366d53011a8185d0e5c5aa698138cd1b949e58a3de191b`，父矩阵 experiment 为
  `4e2d14f9e2b294ec2898b22a4275dbbd706c28ca7f3b061a655d1a613a7aaefb`，父结果 SHA 为
  `bfff564cf4c6e7b2dd05f88542fd7a872d1565442b6d35c795ec6892cc84be0c`。
- 本次只把原 F7 的 `max_tokens` 从 512 调至 2048，用于诊断先前 `length` 截断；唯一 `1/1` 调用消耗 `557`
  tokens，`finish_reason=tool_calls`，观察到 1 个 ToolCall、reasoning 372 chunks、tool 15 chunks，source identity
  stable、`cached=0`。结果标记 `production_admitted=false`、`public_ci_confirmed=false`、
  `vendor_raw_transport_only`。
- 该诊断不证明 provider-neutral streaming、Agent 生产能力、领域采用或公共 CI；Stage 8/8E 继续 `in_progress`，
  下一步等待用户决定 Agent 主线下一项。不改默认模型、Workbench、Auth、前端或 `production_media=0`，不覆盖 RQ-172
  或旧结果。

### 2026-08-31：RQ-174 G53-6 正式领域采用门结果（两份不可变结果）

- 按用户明确授权执行正式 GLM-5.3-Flash 领域采用门；两次结果共用冻结 admission identity
  `4266388ef8ad2083cd59eacfd2c41364b151f286f6cd189334dacb4cb121bd10`，均保留且不得覆盖 RQ-172、RQ-173 或旧
  G53-4。首份 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_6_max_replay_v1.json`
  的 SHA-256 为 `48d22c53f9231f3c03038d5047b8abf653450164e1f56bf2a08c90c9f48114ae`，使用
  `glm-5.3-flash-enabled-max-replay` 与旧 `max_tokens=512` 默认上限；首案消耗 `1/12` calls，以
  `provider_response_invalid/incomplete_chat_response` 停止。
- 随后仅把默认输出上限修正为 1024，并补传 `top_p`，保留第二份
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_6_max_replay_1024_v1.json`
  （SHA-256 `7af819999f4e40810eacf925bcda8a2330cc8baf0e5ca763c84e6f43b58efc96`）。首案累计 `2/12` calls、
  `2925` domain tokens 后，因当前 30 秒 Skill deadline 返回 `provider_timeout/timeout`，后两案按首错跳过。
- 两份结果均 `admitted=false`、`production_admitted=false`，不产生领域采用或生产成熟度结论；没有新的公共 CI
  准入证据。当前仍等待用户决定 Agent 主线下一项，不无授权重试，也不把失败直接解释为 GLM-5.3-Flash 的一般质量。
  Stage 8/8E 继续 `in_progress`，默认模型、Workbench、Auth、前端、路由和 `production_media=0` 保持不变。

### 2026-08-31：RQ-175 GLM-5.3-Flash 专属运行时档案

- 用户明确决定继续使用 GLM-5.3-Flash，并要求旧 30 秒执行截止和低输出上限不能继续作为统一适配。新增
  `glm-5.3-flash-runtime-v1` 仅匹配 `zhipu/glm-5.3-flash`，使用 Agent/`llm.chat` 90 秒、Provider 传输
  120 秒、2048 输出上限、`temperature=1` 与 `top_p=0.95`；思考档案仍为
  `enabled/max/clear_thinking=false`。
- profile 已显式贯通 Agent 编译、AgentLoop、Harness `llm.chat`、G53 最终预算包装器和 Provider client；
  自定义 executor/模型参数不能提高或覆盖可信档案。无 profile 的历史包装器保持 1024，GLM-5.2 与其它 Provider
  不继承这些值。请求内部审计纳入 profile id/version、timeout、max_tokens 与 sampling；旧 G53-4/G53-6 JSON
  继续通过受限 legacy identity 严格读取。
- 本地新增/相关回归 `96 passed, 27 subtests passed`，额外 runtime/provider 回归 `108 passed, 8 subtests passed`；
  compileall、`git diff --check`、governance 通过。本批没有真实 API 调用、没有读取或输出 Key。
- 该实现当前是 G53-7 evaluation-only 接缝，不自动改产品 `RuntimeExecutionFactory` 或默认模型。新 runner 默认使用独立的
  `zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json` 输出路径，不复用旧结果。旧 held-out Dataset
  的 30 秒仍是质量资源阈值；若用户决定放宽，需要另冻 Dataset/Plan，不能改写旧证据。真实 G53-7 运行必须先让
  新实现取得 exact-SHA 公共 CI，并在该新 SHA 上重新取得 G53-3 协议证据；当前 retry2 协议 JSON 绑定旧 SHA，
  runner 会拒绝错配和 dirty worktree。Stage 8/8E 仍 `in_progress`，8F 尚未开始，
  `production_media=0`。

### 2026-08-31：RQ-176 Flash-only 产品运行时晋级（本地接线）

- 用户明确选择普通智谱 API 的 `zhipu/glm-5.3-flash` 作为产品运行时目标；GLM-5.2 只保留为显式兼容/应急回退，
  不再把 Pro/Flash 比较当作前置决策。该决定是“先把产品路线接上 Flash”，不是把尚未完成的生产闸门写成已通过。
- `ModelRuntimeProfile` 已接入产品组合根、Worker、RuntimeExecutionFactory、Agent compiler/Loop、Harness
  `llm.chat`、Zhipu Provider、Runtime policy 和 Trace identity；Flash 使用 90 秒执行窗、120 秒传输、2048 输出
  上限、固定 `temperature=1`/`top_p=0.95` 与 SDK `max_retries=0`。Skill 的 30 秒质量资源门仍单独保留。
- `.env.example` 与 Compose 模板默认对齐 Flash；Worker 只允许登记的 GLM-5.2/Flash，Flash 要求普通 API 标准基址、
  concrete profile 绑定；组合根在已绑定同一注册档案时可安全自动推断，并将 lease/heartbeat 默认设为 360/60 秒
  （少于 300 秒拒绝）。
- 本批没有修改 Portal、Account、Workbench、Auth、路由或 `production_media=0`；工作树仍是用户已有 dirty 状态。
  本地聚焦测试通过，但新实现尚无自己的 exact-SHA 公共 CI，不能复用旧 G53-3 证据。下一步是用户批准干净提交后
  取得公共 CI，在同一 SHA 重取 G53-3，再执行 G53-7/黄金切片与安全部署合规闸门。

### 2026-08-31：RQ-180 G53-7 首次真实领域尝试

- 用户在 RQ-179 的最终实现 A、同 SHA G53-3 与证据 B 公共 CI 完成后明确授权“继续/授权”，在干净 LF checkout
  上只执行一次 G53-7。协议调用 `3/3`，领域调用 `2/12`，累计 `5/15` calls、领域 `3505` tokens，墙钟
  `36625ms`。
- 首例 `flash_gate_baseline_01` 的两次 Provider 请求以适配器安全聚合码
  `provider_response_invalid` / `incomplete_chat_response` 停止，Agent 状态为 failed/degraded，后两例按首错
  跳过，最终 `admitted=false`。G53-3 仍保持通过；这不是认证失败，也不产生模型一般质量、领域采用或生产成熟度结论。
- 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`
  的 canonical-LF SHA-256 为 `21e664d57d53bfc48ad9e109be48a999f52e25a0060821d711ae915002484426`，experiment 为
  `236525300ed9c432a9ad2ffcfdcd298168666676076e5efcb3ce4129a7cee2e0`；结果随后由本地承载提交
  C=`9157cde9904677a352ba7792f170b8765f7fea83` 仅新增，C 未推送且未取得公共 CI。底层 vendor finish reason、
  Key、Prompt、响应正文和 reasoning 未保存，不能把安全聚合码进一步解释为 `length`。
- 当前停止自动重试，旧 G53-3/G53-4/G53-5/G53-6 结果不覆盖；若继续须另立版本化的 Flash 响应完成/截断诊断并
  重新取得授权。Stage 8/`8e-productization` 继续 `in_progress`，8F 尚未开始，`production_media=0`，Portal、
  Account、Workbench、Auth、路由和默认产品接线不变。

### 2026-08-31：RQ-181 Flash 响应完成度诊断

- 用户授权在不重跑旧 G53-7 的前提下执行一次独立、正文零留存的首案例诊断。诊断代码位于独立工作树提交
  `447c11e85b6da53fe678d68e25d96b589c0d6ca2`，产品实现基线为 `7cb66d218389c0e7d7aa7b2b1969a4678402f857`；
  证据由提交 `baa9cc756ff9e3dfc5eac19119315b7f9f0b56da` 承载，未推送、未取得公共 CI。
- 只执行 `flash_gate_baseline_01`，供应商调用 `1/4`，没有 SDK 重试。首个 `agent_initial` 回合收到
  `finish_reason=length`，`input_tokens=2220`、`output_tokens=2048`；正文 `content_state=empty`，
  `reasoning_content_state=non_empty`，没有 ToolCall，Usage 结构有效。适配器随后按现有 fail-closed 合同抛出
  `incomplete_chat_response`，因此 `normalized=0/1`、`settled=0/1`，Agent 为 failed/provider_error。
- 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_completion_diagnostic_v1.json`
  的 canonical-LF SHA-256 为 `050df3fc7afb2c2dc4e99fd2e731f8d9e6133d2806c65171f2dcdbd30834a000`，experiment
  为 `b1e4a1fc51bed23803b5f94acbd2a652330d5847061dbb7b60022c88da4ff1b9`。结果不含 Prompt、响应正文、reasoning、
  Key、原始请求 ID 或工具参数；只确认本次失败路径是“最大推理档案下 2048 输出额度先被 reasoning 耗尽”，
  不把 RQ-180 的旧第二回合改写成同一原因。
- 该诊断不放宽适配器、不提高全局上限、不改 Dataset/Plan、默认模型、Portal、Account、Workbench、Auth、路由或
  `production_media=0`，也不构成 G53-7/生产准入。下一步仅设计版本化的响应完成策略与离线 TDD，是否进入实现另待用户授权。

### 2026-08-31：RQ-182 版本化响应完成策略与离线 TDD

- 用户在 RQ-181 后明确“继续下一步”，授权进入 canonical 指定的策略设计与本地实现；本批没有真实 Provider
  请求，不改变前端或 Workbench。
- 新增 `app/providers/response_completion_policy.py`：不可变 `ResponseCompletionPolicy` 按精确
  provider/model/runtime profile/version 绑定；`ResponseBoundarySnapshot` 和 `ResponseRequestContext` 只接受
  脱敏状态与有限预算，不保存 Prompt、正文、reasoning、工具参数、Key 或 request ID。
- 当前唯一注册 Flash 严格策略为 `glm-5.3-flash-response-completion-v1/1.0.0`，保持 2048 输出上限和零额外调用；
  8192 上限/一次 fresh-recovery 只登记为 `activation_state=candidate` 的离线候选，解析器不会返回，当前没有
  第二次请求入口。`length`、过滤、未知结束原因、Usage 缺失和非法工具/合同/副作用/阶段组合均 fail closed。
- `tests/test_response_completion_policy.py` 聚焦结果 `41 passed`；相邻 Flash runtime/Zhipu/structured/thinking
  回归为 `109 passed, 34 subtests passed`，包级导出检查、compileall、`git diff --check` 与治理检查均通过。
  这只是响应边界合同，不等于恢复能力、领域准入或生产成熟度；RQ-180/RQ-181 旧证据不覆盖，Stage 8/8E 仍
  `in_progress`，8F、部署/合规、安全闸门和 `production_media=0` 边界不变。
- 下一步若继续，必须先为候选建立新的 runtime/attempt/预算/Trace 合同，取得 exact-SHA 公共 CI、同 SHA 协议证据，
  再由用户单独授权一次真实诊断；不得直接把候选上限或二次调用带入产品默认。

### 2026-08-31：RQ-183 候选 fresh-recovery runtime/attempt/预算/Trace 合同

- 用户明确继续 RQ-182 的唯一下一项后，本批只建立离线合同；没有 Provider、SDK、Key 或网络调用，
  也没有改前端、Workbench、Auth、默认模型或 `production_media=0`。
- 新增 `ResponseRecoveryRuntimeProfile`，精确绑定未注册的
  `zhipu/glm-5.3-flash` / `glm-5.3-flash-runtime-v2-candidate/2.0.0`；计划最多描述序号 1
  的 `primary` 与序号 2 的 `fresh_recovery`，第二个槽位必须由 RQ-182 候选策略重新判定为白名单形状，
  且计划始终 `execution_allowed=false`。
- `ResponseRecoveryLedger` 把每个底层请求分开预留和结算，严格统计 attempts、input/output token 与墙钟时间；
  失败、Usage 缺失、单次上限或累计预算超限均消耗已发出的槽位并 fail closed，不产生第三次尝试。独立
  `ResponseRecoveryTrace` schema 1.0 只保留脱敏状态、身份和资源数字，不保存 Prompt、正文、reasoning、
  工具参数、Key 或 request ID，也不改写既有 Runtime Trace。
- 聚焦 `tests/test_response_recovery_contract.py` 为 `30 passed`；与响应完成策略、Flash runtime、Runtime models、
  Observed Provider 和领域门相邻回归为 `128 passed`，compileall、`git diff --check` 与 governance 均通过。
- 严格 Flash v1 继续保持 2048 输出上限和零额外调用；候选仍为 `activation_state=candidate`，不进入产品注册表。
  下一唯一闸门是为这批合同取得新的 exact-SHA 公共 CI，并在同一 SHA 重取 G53-3；随后是否执行一次真实诊断，
  仍需用户单独授权并审查成本、延迟、失败和 Trace。G53-7、黄金切片、安全/部署/合规、8F 与 Stage 8/8E
  完成声明均不提前。

### 2026-08-31：RQ-184 候选合同 exact-SHA 公共 CI 与同 SHA G53-3

- 用户明确“继续”，授权完成 RQ-183 候选合同的公共可复现性和同 SHA 协议证据；本批只完成这道证据闸门，
  不执行 fresh-recovery、G53-7 或任何产品默认切换。
- 实现提交 A=`e25c3579e8c37724b76505ad028e066a7e28e654`，Actions run `33405110692` 的 `pytest`、
  `packaging-smoke`、`postgres-migrations` 三 job 全部成功。A 的干净 checkout 严格执行 G53-3 `3/3` 次真实调用：
  A1 结构化合同 `1/1`、A2 Agent 工具往返 `2/2`，`admitted=true`，SDK retries 为 `0`。
- 脱敏结果 `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_rq183_candidate_v1.json`
  的 `code_sha` 为 A；直接子提交 B=`eca01ce1393286dbbe83992c2985f600ea2b30b0` 只新增该结果，Actions run
  `33405881172` 三 job 全部成功。A/B 无 I/O 身份预检通过，结果 canonical-LF SHA-256 为
  `275e3a091a37dc12604143e6890f0ce899fb3d9007cef8c2aa46a51bdb9c8e72`。
- 该证据只证明候选合同的公共可复现性与同 SHA 协议接缝；候选仍 `activation_state=candidate`、
  `execution_allowed=false`，严格 Flash v1 仍为 2048/零额外调用。下一唯一动作是等待用户单独授权一次有界
  候选恢复诊断，并审查成本、延迟、失败与脱敏 Trace；G53-7、黄金切片、安全/部署/合规、8F 和 Stage 8/8E 完成声明不提前。

### 2026-08-31：RQ-185 候选恢复诊断中断

- 用户在 RQ-184 后明确“继续”，授权重开一次候选诊断。隔离诊断代码提交为
  `76de589a128b7a71f1def3316da3f30ebdd3a4c8`，实现基线为候选证据提交
  `eca01ce1393286dbbe83992c2985f600ea2b30b0`；两次启动均只进入 `primary` 首回合，
  SDK `max_retries=0`，没有发送 `fresh_recovery`。
- 首次启动沿用候选合同的 120 秒传输边界，但调用方在约 60 秒无返回时按工具规则中止；
  第二次启动使用全新结果名并把客户端传输上限临时收窄为 20 秒，进程仍未在约 60 秒内结束，
  随后被明确终止。两次都没有收到可观察的响应、Usage、finish reason 或脱敏 Trace，
  也没有生成结果 JSON；不能推断请求是否抵达供应商，费用/计费状态为 `unknown`。
- 候选仍 `activation_state=candidate`、`execution_allowed=false`；严格 Flash v1 仍为
  2048/零额外调用。该中断不改变 G53-3/G53-7、默认模型、AgentLoop、RuntimeTrace、
  Portal、Account、Workbench、Auth、路由或 `production_media=0`。下一项切换为本诊断的
  传输/代理边界复核，需新的用户授权；不自动重试或进入 G53-7。

### 2026-09-01：RQ-187 完整候选窗口诊断

- 用户明确“继续”，授权在 RQ-186 请求级截止修复后执行一次完整候选窗口；未扩大到 G53-7。
- 隔离诊断代码 `94629161c5d3230629210444b5a1a38212799997`、实现基线
  `eca01ce1393286dbbe83992c2985f600ea2b30b0`；请求 `max_tokens=8192`、`timeout_s=90`、SDK retries `0`。
- 唯一 primary 在 90.188 秒以 `transport timeout` 安全结束；无响应、Usage、finish reason、request ID 或
  `fresh_recovery`，`provider_calls_attempted=1`、`candidate_eligible=false`、`terminal_state=fail_closed`、
  费用状态 `unknown`。结果路径为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_response_recovery_diagnostic_rq187_full_window_v1.json`，
  canonical-LF SHA-256=`3d8d4744da3286b921d894684bfffcbf19d56d2c945821703ae1d4282fd80263`，本地提交 `50ce5be`。
- 该结果排除“30 秒过短”，但不能从无响应区分代理/连接/读取与服务端生成延迟，也不构成模型能力失败；候选、
  严格 Flash v1、默认模型、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变。下一项为
  `candidate-transport-generation-split`，需新的明确授权。

### 2026-09-01：RQ-188 传输与生成路径拆分诊断

- 用户新授权后，在隔离工作树中只执行一批固定三路、最多 `3` 次真实调用，SDK `max_retries=0`：合法的
  `thinking=enabled`/`reasoning_effort=low` 最小控制（`max_tokens=16`）、冻结领域上下文的
  `max_tokens=256`/`reasoning_effort=max` 同步请求，以及同一上下文的 `max_tokens=8192`/`reasoning_effort=max`
  流式首块请求。流式探针只读取首个 chunk 后按合同关闭，不重跑 RQ-187，也不打开 recovery。
- 三路均为 `observed`。最小控制与冻结短同步请求均收到完整响应并有有效 Usage，`finish_reason=length`、正文为空、
  reasoning 非空；流式请求在约 `687ms` 观察到首个 `delta_reasoning` chunk，终止原因与 Usage 因探针主动关闭而保持
  `not_observed/missing`。总计 `3` calls、输入 `1993`、输出 `272`、缓存输入 `1920`、总计 `2265` tokens、
  累计观测延迟 `17172ms`。
- 正式脱敏结果为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_final_v1.json`，
  canonical-LF SHA-256=`60073a5f0d0d0324d0fe4deb588d4a49becc607ebfe6b1d008bf04d60a2faf51`，experiment
  `41901515decc6d8768abd56ee3fd49ac1d1a4402f3cc1cef497720995fa80c8e`；诊断代码与运行时 source identity 均为
  `b67b4500ebdbff934e470fd92c1461184aa7c49b`，source identity stable，运行时工作树保持 dirty。首次 disabled-thinking
  控制结果与带代码 SHA 输入笔误的更正结果均保留为不可变审计文件，不进入正式结论。
- `transport_reachable=true`、`minimal_control_observed=true`、`frozen_short_generation_observed=true`、
  `stream_first_chunk_observed=true`，但 `long_window_baseline_observed=false`、`candidate_registered=false`、
  `production_admitted=false`。这确认 endpoint/model 路径可达且已开始生成，并提示当前同步接缝在小额度下会先耗尽
  reasoning；不能区分长请求的代理/读取与服务端延迟，也不能证明完整 provider-neutral streaming、模型一般质量、
  领域采用或生产成熟度。
- 严格 Flash v1 继续 `2048` 输出上限、零额外调用；候选仍为 `activation_state=candidate`、
  `execution_allowed=false`。下一步在同一 evaluation-only 边界内做 `candidate-output-budget-calibration`，先比较
  合法 `reasoning_effort` 与可见正文完成度，不改产品 Provider-neutral 接口、默认模型、Workbench、Portal、Account、
  Auth、路由或 `production_media=0`。

### 2026-09-01：RQ-189 输出额度/推理档位校准

- 在隔离工作树以 evaluation-only 诊断器执行三次相互独立的真实调用；SDK `max_retries=0`，冻结上下文、
  `temperature=1`、`top_p=0.95` 和普通 API endpoint/model 不变。第一路为 `thinking=enabled`、
  `reasoning_effort=low`、`max_tokens=2048`：一次调用约 `28.344s` 返回，`finish_reason=stop`、正文和 reasoning
  均非空，Usage 为输入 `1973`、输出 `724`。第二路 `low+8192` 在 `45.594s` 请求截止内无响应；第三路
  `max+8192` 在 `45.500s` 请求截止内无响应；两路均无 Usage、正文或 request ID，安全记为 transport timeout，费用保持
  `unknown`。
- 三份不可变脱敏结果分别为 `zhipu_glm53_flash_output_budget_calibration_rq189_probe1_v1.json`
  （SHA-256=`1e001b49370f734404bc56896610d73d94057203aebf8de172d54787728e7c32`，诊断 SHA=`b46d5e39e1d44293452b1b893c91feff13f57b02`）、
  `...probe2_v1.json`（SHA-256=`42339af9af71db3e63f2ba8e8773898a7f6b60cd8e5ceab06269ec6aca37f32`）和
  `...probe3_v1.json`（SHA-256=`fc54d9479db60cef585b216d0b11dd36e511180b485ea00c2ebced60d528379f`）；后两份诊断 SHA 为
  `21bc38b211e596f933223aa9a871a5b10f62267f`。第一份在“单路选择”安全修补前生成，但请求形状和脱敏规则相同；三份
  source identity 均稳定，工作树仍明确 dirty，未宣称 public CI。
- 该批只说明在同一冻结长上下文下，低推理档位的 2048 上限可以完成可见正文，而 8192 同步窗口在 45 秒内未完成；
  不能把两次 timeout 归因于模型质量、账号权限或计费，也不能据此把候选注册或放宽生产上限。严格 Flash v1 仍为
  `2048` 输出上限、零额外调用；候选保持 `activation_state=candidate`、`execution_allowed=false`，下一步转为
  `candidate-stream-visible-completion-probe`，验证流式可见正文和 `clear_thinking` 组合。

### 2026-09-01：RQ-190 流式首个可见正文探针

- [completed-local] 隔离工作树冻结 evaluation-only 探针代码/CLI，最终实现与诊断 SHA 均为
  `5ec622c4b651f9aa5e12f54b1e5a4a0dc253a4c7`；聚焦测试 `7 passed`，compileall 与 diff check 通过。
- [completed-bounded-real] 同一冻结上下文、`temperature=1`、`top_p=0.95`、`thinking=enabled`、
  `reasoning_effort=low`、`max_tokens=2048`、SDK `max_retries=0` 下分别执行两次单路流式请求。`clear_thinking=true`
  在 `1813ms` 首块、`2547ms` 首个非空可见正文（18 chunks，17 reasoning chunks）；`clear_thinking=false`
  在 `1500ms` 首块、`3875ms` 首个非空可见正文（50 chunks，49 reasoning chunks）。两路均在首正文后主动关闭，
  未观察终态/Usage，`within_token_budget=null`、费用 `unknown`。
- [evidence] 修正后的不可变结果为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_stream_visible_completion_rq190_clear_true_v2.json`
  （SHA-256=`23e3954c2be65d70b24186a3deba35047e3925b2fc2fde1eb3cfeec82631141a`）和
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_stream_visible_completion_rq190_clear_false_v2.json`
  （SHA-256=`fae64899daaffbd2e9a2a5369ee8d396ea912065f2b7351a782a91eb74a0c77e`）。早期 v1 结果保留为审计，但因曾把
  未观测预算写成布尔值，不作为正式结果；v2 source identity 均 stable，public CI 未宣称。
- [interpretation-boundary] 该批只证明两种单轮请求形状都可打开流并出现首个可见正文；不能证明
  `clear_thinking` 的因果效果、跨轮思考清理/回放、完整 provider-neutral stream、终态 Usage、成本、领域采用或生产成熟度。
  候选仍 `activation_state=candidate`、`execution_allowed=false`，严格 Flash v1 仍 2048/零额外调用；下一项转为
  `candidate-stream-terminal-completion-probe`，不改 Provider-neutral 接口、默认模型、Workbench、Portal、Account、Auth、
  路由或 `production_media=0`。

### 2026-09-01：RQ-191 完整流式终态/Usage 探针

- [completed-local] 隔离工作树冻结 evaluation-only 完整流探针与 CLI，最终实现/诊断 SHA=
  `2a01edf58e9f5b11619553a9eeb4448a4cdb87d0`；聚焦测试 `6 passed`，compileall 与 diff check 通过。
- [completed-bounded-real] 使用当前产品形状 `clear_thinking=false`、`thinking=enabled`、`reasoning_effort=low`、
  `max_tokens=2048`、`stream=true`、SDK `max_retries=0`，只发出 1 条请求。首块 `2203ms`、首个可见正文 `3531ms`，
  完整流 `24140ms` 以 `finish_reason=stop` 结束；642 chunks（30 reasoning、571 visible、41 other），Usage 有效，
  输入 `1973`、输出 `652`、缓存输入 `0`，预算状态可核验为 within。
- [evidence] 脱敏结果为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_stream_terminal_completion_rq191_v1.json`，experiment=
  `dba57e5316058336dbc0e497d01b115e337ce6367acbb967b5e6760e270b3f46`，canonical-LF SHA-256=
  `a57fec105859241ea71e32eb8073b4c33b934262a7793b6a47a7b6e4efb4b3c9`；source identity stable，public CI 未宣称，
  结果不含 Prompt、正文、reasoning、Key 或原始 request ID。
- [interpretation-boundary] 该结果只证明一份冻结上下文的原始完整流可取得可见正文、终态和 Usage；不证明一般模型质量、
  长上下文/高预算延迟、跨轮 `clear_thinking` 语义、工具流、provider-neutral runtime 接入、候选注册、领域采用或生产成熟度。
  严格 Flash v1 仍 2048/零额外调用，候选仍 `candidate`/`execution_allowed=false`；下一项为离线
  `candidate-provider-neutral-stream-adapter-contract`，不改产品接线。

### 2026-09-01：RQ-192 提供商无关流式装配合同（本地候选接缝）

- [completed-local] 新增纯离线 `app/providers/stream_adapter_contract.py`：规范化
  `ProviderStreamEvent`/`StreamToolCallDelta`、独立的 `ProviderStreamAdapter` 协议、单次
  `ProviderStreamAssembler`、`StreamAssemblyResult` 和 body-free `StreamAssemblyTrace`；从
  `app/providers/__init__.py` 导出，但没有改变现有同步 `LLMProvider` 或 Provider 能力声明。
- [completed-boundary] 装配器要求底层迭代器真实 EOF 后显式 `mark_exhausted()`；只有合法终止原因与有效
  Usage 同时出现才交付 `ChatResponse`，终止后最多一个 Usage-only 尾块。序号、model、可选请求 SHA-256、
  正文/reasoning/工具数量与长度、工具连续索引/元数据、重复键、有限数字和 JSON 深度均受校验；任何接收或
  完成错误都会毒化当前实例并 fail closed，不打开隐式重试/恢复。
- [completed-verification] `tests/test_stream_adapter_contract.py` 聚焦 `29 passed`；相邻
  Provider、响应完成策略、候选恢复合同和 Runtime stream 回归 `147 passed, 27 subtests passed`；
  compileall、`git diff --check` 和治理检查在最终文档同步后重跑。Trace 仅保留白名单状态/计数/序号/模型/摘要，
  不保存正文、reasoning、Prompt、工具参数、SDK 对象、Key 或原始 request ID。
- [boundary-next] 本批没有 SDK、网络或真实 API 调用，没有注册候选、没有把 `capabilities.streaming` 改为 true，
  也没有改默认模型、AgentLoop、ToolRuntime、Runtime Trace、预算、Portal、Account、Workbench、Auth、路由或
  `production_media=0`。Stage 8/8E 仍 `in_progress`，8F 尚未开始；下一项是同一新实现 SHA 的公共 CI 与供应商
  适配器一致性测试，完成前不进入候选 runtime/G53-7/黄金切片。

### 2026-09-01：RQ-193 智谱流式适配器一致性接缝（本地与公共 CI 已完成）

- [completed-local] 在提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 中新增测试内的
  `_FixtureZhipuStreamAdapter`，把代表性的 OpenAI-compatible 智谱分块翻译为
  `ProviderStreamEvent`，再与现有 `ZhipuProvider.chat_stream()` 的伪造分块结果逐字段对照；覆盖正文/reasoning、
  工具别名与参数分片、坏分块 fail-closed、模型/终止边界、异常 `abort()`、空 choices 与正文空白保留。
- [completed-local] conformance 聚焦为 `13 passed`（另有历史 capability-result 严格 schema 回归随该提交保留）；
  测试只构造本地 fake client，不读取 Key、不发网络、不改 `ZhipuProvider` 生产实现，也不把
  `capabilities.streaming` 改为 true。Trace 脱敏断言继续确保正文、reasoning、工具参数和内部工具名不外泄。
- [completed-public] `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA 公共 CI run `33489903978` 已
  `completed/success`，pytest、postgres-migrations、packaging-smoke 三 job 均成功且 head_sha 精确匹配；全部 Trace
  脱敏断言均已包含在该提交，主工作树/用户 dirty 改动不参与本条冻结。
- [boundary-next] 候选仍未注册，严格 Flash v1 仍 2048/零额外调用；不接入产品 streaming、不改默认模型、
  AgentLoop、ToolRuntime、Runtime Trace、预算、Portal、Account、Workbench、Auth、路由或 `production_media=0`。
  公共 CI 已通过，下一精确动作是候选接线裁决（是否接入、接入范围及保留的
  runtime/预算/Trace/回退门），而不是自动启用或直接执行 G53-7/黄金切片；Stage 8/8E 仍 `in_progress`，8F 尚未开始。

### 2026-09-01：RQ-194 候选级显式智谱→中立适配接缝（公共闭环完成）

- [completed-local] 早期设计中的占位符已落为实际 `app/providers/zhipu_stream_adapter.py`、
  `ZhipuStreamAdapter` 与 `ZhipuProvider.stream_adapter(*, tool_stream=False)` 显式工厂；适配器实现独立
  `ProviderStreamAdapter` 协议，但不是 `LLMProvider`，调用方必须显式取得实例。
- [completed-public] 提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA Actions run `33496237588`
  中 `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 均 `completed/success`，head_sha 精确匹配；在此提交上
  `tests/test_zhipu_stream_adapter.py` 聚焦 `20 passed`。该公共证据只确认候选接缝可复现，不等于产品 runtime 接线。
- [completed-public] `stream_events(request)` 将一个 Zhipu OpenAI-compatible 原始流翻译为
  `ProviderStreamEvent`；`assemble(request, *, max_output_tokens=None, require_request_identity=True)`
  只打开一次流并交给 `ProviderStreamAssembler`。`_open_stream_for_adapter(...)` 集中请求校验、thinking/runtime
  profile 绑定、工具 alias 编码和 SDK open；工具流形状由实例创建时固定。
- [completed-public] 输出 cap 只接受 `1..8192`；runtime profile cap、显式 cap 与 `ChatRequest.max_tokens` 取最小值，
  同时传给供应商 payload 和 assembler，不能越过 trusted cap。provider 必须为 `zhipu`，event model 必须与绑定 model
  一致；默认要求 request identity，Trace 仅保存 request ID SHA-256，不保存原始 ID。
- [completed-public] 正常 EOF 后才 `mark_exhausted()`/`finalize()`；SDK/迭代器异常、取消、翻译错误或 close 失败会
  `abort("stream_aborted")`、保留 typed provider error 或返回安全 `zhipu_stream_close`，不能误当 EOF、retry 或 recovery。
  iterator/raw stream 均在 `finally` 关闭，Trace/错误/repr 保持 body-free。`tests/test_zhipu_stream_adapter.py`
  fake/local 聚焦 `20 passed`。
- [unchanged] 实现仍未接入默认模型、`capabilities.streaming`（继续 `False`）、严格 Flash v1 2048/零额外调用、
  AgentLoop、ToolRuntime、统一 Runtime Trace、产品预算、Portal、Account、Workbench、Auth、路由或
  `production_media=0`；不注册 recovery，不调用真实 API 或读取 Key，候选未注册。
- [boundary-next] exact-SHA 公共 CI 已完成；当前唯一下一门改为候选 runtime 接线裁决（范围、预算/Trace/回退/失败门）。
  不自动打开 `capabilities.streaming`、注册候选、执行 G53-7/黄金切片或进入生产准入，Stage 8/8E 继续
  `in_progress`，8F 尚未开始。

### 2026-09-01：RQ-195 候选 runtime 接线架构评审

- [completed-review] 评审确认 `ZhipuStreamAdapter.assemble()` 只交付拥有真实 EOF、合法终止和有效 Usage 的完整
  `stop`/`tool_calls` 流；`length`、缺终止、缺 Usage、读取/翻译/关闭异常均 fail-closed，不能从
  `StreamAdapterError` 或私有部分状态推导恢复资格。
- [decision] 不把候选接缝包装成 `LLMProvider`，不改 `AgentRuntimeV1`、`AgentLoop`、Worker、统一 Runtime Trace、
  产品预算、默认 composition root 或 `capabilities.streaming`。未来若获单独授权，先在 `app/evaluation/` 设计隔离的
  `CandidateStreamEvaluationHarness`，由调用方显式持有 adapter 与候选合同，禁止默认注册表发现。
- [boundary-observation] 下一设计门须冻结只输出 field state、finish code、Usage 数字、耗时和安全错误码的
  `BoundaryObservation`（暂定名），复用 adapter 的分块/model/sequence/tool/Usage 校验；不得返回或持久化部分正文、
  reasoning、工具参数，也不得把不完整流包装成 `ChatResponse`。完整流继续走 `assemble()`。
- [identity-budget] 调用前必须精确绑定 `provider_id=zhipu`、`model=glm-5.3-flash`、
  `glm-5.3-flash-runtime-v2-candidate/2.0.0` 与
  `glm-5.3-flash-fresh-recovery-candidate-v1/1.0.0`；候选最多 2 attempts、1 次额外调用、32,000 input、16,384 output、
  180,000ms，当前 `execution_allowed=false`，不得发送 recovery。Trace 需用 allow-list 独立投影，request ID 仅存 SHA-256。
- [unchanged] 严格 Flash v1 仍 2048/零额外调用；候选未注册，默认模型、同步/既有流接口、Workbench、Portal、Account、
  Auth、路由、生产媒体和 `production_media=0` 均不变。RQ-195 只完成评审，下一精确 checkpoint 为
  `candidate-runtime-wiring-design / pending`；8E 仍 `in_progress`，8F 尚未开始。

### 2026-09-01：RQ-196 候选 runtime 接线设计

- [completed-design] 冻结 `CandidateRuntimeBinding` 的 provider/model/runtime-profile/policy/attempt 四元身份，
  以及不可变、body-free 的 `BoundaryObservation`：只允许生命周期、终止码、字段状态、工具计数、有效 Usage 数字、
  单调耗时、model/request SHA-256 和安全错误码；不保存正文、reasoning、工具参数、Prompt、Key、SDK 对象或异常原文。
- [completed-design] 明确完整流继续走 `ProviderStreamAssembler`，不完整流只能进入观察状态；共享 chunk/model/sequence/tool/Usage
  校验核心不得与 RQ-194 漂移。candidate eligibility 必须由既有 policy 从满足 EOF/terminal/close/Usage 的观察重新计算，
  不能由调用方填写。
- [completed-design] 设计隔离的 evaluation-only v2 transport 与 `CandidateStreamEvaluationHarness` 控制流：先校验身份和预算，
  再 reserve→open→observe/assemble→settle；每个槽位恰好结算一次，最多 2 attempts/1 次额外调用/32,000 input/
  16,384 output/180,000ms，unknown Usage 不得按零继续，第三次调用拒绝。candidate `execution_allowed=false` 仍不发送 recovery。
- [completed-design] 未来使用独立 `CandidateStreamTrace` allow-list 投影，不写入 `RuntimeTraceStore`；保留可确定的状态/数字，
  token 总额未知时保持 `None`。新增 ADR-0076、设计计划和学习 walkthrough；本批未改 `app/`、Provider、AgentLoop、Worker、
  默认模型、`capabilities.streaming`、Portal、Account、Workbench、Auth、路由或 `production_media=0`，治理/差异检查在本地通过。
- [boundary-next] 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-boundary-observation-contract-implementation / pending`；
  只允许 fake/local 合同实现和同 SHA 公共 CI，之后再单独裁决候选 harness、fresh-recovery、G53-7、黄金切片与生产准入。

### 2026-09-01：RQ-197 候选边界观察合同本地实现

RQ-197 按当前唯一精确门完成了 fake/local 的候选边界观察实现。新增
`app/evaluation/candidate_stream_contract.py`，提供精确 `CandidateRuntimeBinding`、不可变且
body-free 的 `BoundaryObservation`、状态观察器、候选 v2 注入式 transport port 和独立
`CandidateStreamTrace`；观察器只保留生命周期、字段状态、工具计数、有效 Usage 数字、单调耗时、
model/request SHA-256 与安全错误码。`ProviderStreamEvent` 与智谱翻译现在能区分字段缺失和显式
`null`，assembler 与观察器共用事件级校验核心。

本地矩阵覆盖完整 stop/tool-call、`length` reasoning-only、缺 EOF/terminal/Usage、model/序号/
request identity、工具元数据与参数上限、输出预算、时钟、迭代器/外层资源关闭和 body-free
序列化；聚焦及相邻回归为 `163 passed`，compileall、`git diff --check` 和治理检查通过。观察器
完成闭合后快照不可改写，矛盾的公开状态会被拒绝；用户取消类异常不会被清理代码吞掉。全量本地
pytest 的首个错误仅是 PostgreSQL fixture 缺少 `RIFTCOACH_TEST_DATABASE_URL`，不归因于本批代码。

本批没有真实 API/Key I/O，没有 fresh-recovery、G53-7、黄金切片或候选注册；`execution_allowed=false`、
严格 Flash v1 2048/零额外调用、`capabilities.streaming=False`、默认模型、AgentLoop、Worker、
统一 Trace/预算、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变。
当前状态已达到 `completed-public`：实现提交
`127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run `33507627615` 中，
`pytest`、`postgres-migrations`、`packaging-smoke` 三个 job 均 `completed/success`，且 `head_sha`
精确匹配；公共 pytest 为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。

### 2026-09-01：RQ-198 候选边界观察合同公共 CI 闭环

- [completed-public] RQ-197 的同一干净实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 已取得
  Actions run `33507627615` exact-SHA 公共证据；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 全绿。公共 pytest 摘要为 `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。
- [unchanged] 公共 CI 只验证候选边界合同可复现，不把候选注册为 Provider/Runtime，不打开
  `capabilities.streaming`，不改变严格 Flash v1 2048/零额外调用、默认模型、AgentLoop、Worker、统一
  Trace/预算、Portal、Account、Workbench、Auth、路由或 `production_media=0`；没有真实 API/Key、
  fresh-recovery、G53-7 或黄金切片。
- [boundary-next] 当前唯一下一精确 checkpoint 为：
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`。

### 2026-09-02：RQ-199 隔离候选评估台设计

- `[completed-design]` 本轮按 canonical 唯一下一步完成 ADR-0077、实现计划和学习
  walkthrough。设计冻结 `CandidateEvaluationHarness` 的显式输入/输出、一次性 run
  生命周期、候选专用 staged ledger、单次 normalized event pump、可选但不持久化的
  evaluation consumer，以及独立 `CandidateEvaluationReceipt` body-free envelope。
- `[staged-ledger]` 现有 `ResponseRecoveryLedger` 的“首回合快照已知”离线合同保持兼容；
  未来候选 harness 必须先在 primary I/O 前预留，再用真实 `BoundaryObservation` 映射
  `ResponseBoundarySnapshot` 并重新运行 policy，禁止 sentinel snapshot、首回合结束后
  才 reserve 或 caller-supplied eligibility。每个槽位恰好一次 settle，open/read/取消/
  close 失败也消耗槽位。
- `[event-pump]` 一条 normalized stream 只消费一次；共享事件校验后分别送入
  `CandidateStreamBoundaryObserver`（只保留状态）与 `ProviderStreamAssembler`（仅内存
  暂存完整结果）。只有 EOF、terminal、close 和有效 Usage 全齐时才可向显式 consumer
  交付临时 `ChatResponse`；不完整流永远不构造成产品响应。
- `[receipt-and-budget]` receipt 只允许候选身份、生命周期、finish/error code、字段
  状态、ToolCall 数量、Usage/耗时、调用数和预算确定性；Usage unknown 不得按零当余额。
  候选固定 8192/90/120 秒、`temperature=1`、`top_p=0.95`、retries=0、累计
  32,000/16,384/180,000ms、最多 2 attempts/1 次额外调用；当前 activation 仍关闭，
  命中候选形状只产生 `awaiting_recovery`。
- `[failure-and-non-goal]` 设计覆盖完整 text/tool、候选 shape、缺 EOF/terminal/Usage、
  身份/序号/工具/预算/时钟/取消/关闭、重复结算、第三次调用和 body-free 序列化失败。
  本批没有修改 `app/` 产品运行时代码、ProviderRegistry、AgentLoop、Workbench、Portal、
  Account、Auth、路由、默认模型、统一 Runtime Trace 或 `production_media=0`，没有读取
  Key、真实 API、fresh-recovery、G53-7 或黄金切片。
- `[verification]` 本批为文档设计门，验证范围是状态镜像、ADR/计划/学习材料完整性、
  governance 与 `git diff --check`；未把文档设计误报为实现或生产成熟度。Stage 8/8E
  继续 `in_progress`，8F 尚未开始，`production_media=0`。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-implementation / pending`；
  后续若获明确继续，只允许 fake/local harness/staged ledger 实现与聚焦测试、公共 CI，
  仍需另行授权真实 recovery、G53-7、生产准入和 8F。
  设计门已由 RQ-199 完成；下一轮只在明确继续后实现隔离的候选 evaluation harness 及其 staged
  ledger/Trace 接缝，随后再由用户决定是否执行 fresh-recovery、重跑 G53-7 或进入生产准入。

### 2026-09-02：RQ-200 隔离候选评估台本地实现

- `[completed-local]` 按 RQ-199 冻结的范围新增 `app/evaluation/candidate_evaluation_harness.py` 与
  `tests/test_candidate_evaluation_harness.py`，实现候选专用 staged ledger、primary I/O 前预留、
  单次 normalized event pump、临时内存 assembler、显式 evaluation consumer 和独立
  `CandidateEvaluationReceipt`。`app/evaluation/__init__.py` 仅导出该 evaluation API，不注册 Provider。
- `[fail-closed]` 每个槽位严格 reserve→open→observe/assemble→settle 一次；open/read/clock/close
  异常、缺 EOF/终止/Usage、`length` 不完整、身份/序号/工具/预算冲突均不会构造产品
  `ChatResponse`。完整 stop/tool 流才可短暂交付 consumer；unknown Usage 保持 `None`/`unknown`，
  不执行 ToolRuntime、隐式 retry 或 fresh recovery。
- `[verification-local]` harness 聚焦 `15 passed`，与边界观察、provider-neutral 流装配和旧恢复合同
  相邻回归 `102 passed`；Python 3.11/3.13 编译、`git diff --check` 和治理预检通过。仅使用
  fake/local transport，没有读取 Key、真实 API、G53-3/G53-7 或黄金切片。
- `[unchanged]` activation 仍为不可伪造的 `disabled`，候选仍 `execution_allowed=false`；严格
  Flash v1 2048/零额外调用、`capabilities.streaming=False`、默认模型、产品 Runtime、Portal、
  Account、Workbench、Auth、路由和 `production_media=0` 均不变，8F 尚未开始。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-public-ci / pending`；
  先在同一干净提交上取得 exact-SHA 公共 CI，再另行裁决 recovery 激活、G53-7、黄金切片、生产准入
  与 8F，不把本地测试或候选实现写成公共生产成熟度。

### 2026-09-02：RQ-201 候选评估台 exact-SHA 公共 CI 闭环

- `[completed-public]` RQ-200 实现提交 `f2a80320123d80a6441f3fcac310014a9bd4550e` 的 Actions run
  `33536168224` 已完成且 `head_sha` 精确匹配；`pytest`、`postgres-migrations`、`packaging-smoke`
  三个 job 均 `completed/success`。公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
- `[unchanged]` 该公共证据只证明隔离候选评估台的可复现性，不注册 Provider/Runtime，不打开
  `capabilities.streaming`，不改变严格 Flash v1 2048/零额外调用、默认模型、AgentLoop、统一
  Trace/预算、Portal、Account、Workbench、Auth、路由或 `production_media=0`；没有真实 API/Key、
  recovery、G53-7、黄金切片或 8F 证据。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-review / pending-user-authorization`；
  先复核候选 recovery 的传输、预算、失败和脱敏边界，之后是否建立新的诊断版本仍需单独授权。

### 2026-09-02：RQ-202 候选 recovery 诊断边界复核与最小离线加固

- `[completed-local]` 复核 `CandidateEvaluationHarness` 的回执来源：顶层终态/下一动作、
  安全错误、attempt 决定/原因/装配状态与 budget projection 现在都必须由最后观察和候选
  硬上限推导，`dataclasses.replace()` 伪造会在值对象边界 fail closed；单次 observer elapsed
  上限改为 attempt 的 90 秒与累计 180 秒取小值。
- `[non-reuse]` 检查旧 `glm53_flash_response_recovery_diagnostic.py` 后确认它直接持有 SDK/真实
  I/O、复用未知 Usage 当零的旧账本，且 activation 报告语义不适合新候选控制面；旧脚本与旧
  账本保留不动，不建立新诊断 schema。
- `[verification]` harness 聚焦 `18 passed`；候选流/装配/恢复合同/智谱 adapter/Flash profile
  相邻集合 `127 passed, 1 deselected`；compileall、`git diff --check`、governance 通过。加固提交
  `67031145d3b3e5c864e881576c69e2fda931e950` 的 Actions run `33582049836` 已三 job exact-SHA 全绿，
  公共 pytest 为 `2193 passed, 145 skipped, 1 warning, 127 subtests passed`。
  deselected 与旧诊断测试的本地阻断均来自 Windows 隔离工作树 CRLF fixture 与计划 canonical-LF
  摘要不一致，未修改冻结 fixture/plan。
- `[unchanged]` activation 仍 sealed `disabled`，候选未注册、`execution_allowed=false`，严格
  Flash v1 2048/零额外调用、默认模型、产品 Runtime、Portal、Account、Workbench、Auth、路由、
  `capabilities.streaming=False` 与 `production_media=0` 均不变；没有真实 API/Key、recovery、
  G53-7、黄金切片或 8F 证据。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-design / pending-user-authorization`；
  先设计新版本化诊断协议，再另行决定真实 recovery、G53-7、黄金切片和生产准入。

### 2026-09-02：RQ-203 版本化候选 recovery 诊断协议设计

- `[completed-design]` 冻结独立协议 `glm-5.3-flash-candidate-recovery-diagnostic-v2`、schema `2.0.0` 及四元身份：provider/model、runtime profile、policy、实现/计划/上下文/运行 SHA。请求摘要只保留角色与形状，不保存 Prompt、正文、reasoning、工具参数、Key 或原始 request ID。
- `[lifecycle]` 未来候选流程固定为 `reserve → open → observe/assemble → settle → receipt`；primary 在 I/O 前占用槽位，fresh recovery 是一次完整的新请求，不是 resume、SDK retry、AgentLoop retry 或 ToolRuntime 调用。当前 activation 仍 sealed disabled，设计不产生第二次真实请求。
- `[resource-and-failure]` 明确单次 8192/90s/120s 与累计 32000/16384/180000ms 的分层预算；Usage、预算和费用采用 `within|exceeded|unknown`/`unknown|estimated|actual` 三态，未知值保持 `null`。延迟拆成 open、首事件、首正文、terminal、close、total；失败类别固定并保留第一现场。
- `[storage-boundary]` 诊断回执只允许原子、create-only、canonical UTF-8/LF 的 body-free JSON，不写产品 Runtime Trace、数据库或用户数据；未来实现必须先通过 fake/local 失败矩阵、脱敏序列化、exact-SHA 公共 CI 和 dry-run，真实调用仍需另行一次性授权。
- `[unchanged]` 本门只有 ADR-0079、实施计划和学习材料；没有新增代码、结果 JSON、真实 API/Key、recovery、G53-7 或黄金切片。候选未注册，`execution_allowed=false`、`capabilities.streaming=False`，严格 Flash v1、默认模型、AgentLoop、Workbench、Portal、Account、Auth、路由和 `production_media=0` 均不变；Stage 8/8E 继续 `in_progress`，8F 未开始。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`；只有再次明确授权后才实现 v2 fake/local 协议与聚焦测试，随后再决定真实 recovery、G53-7、黄金切片和生产准入。

### 2026-09-02：RQ-204 版本化候选 recovery 诊断本地实现

- `[completed-local]` 按 RQ-203 协议新增 `candidate_recovery_diagnostic_v2.py`、严格的
  body-free request/receipt allow-list、candidate-only staged ledger、一次 normalized
  event pump、临时 assembler、预算/费用/六段延迟投影与 create-only canonical JSON；
  `app/evaluation/__init__.py` 只导出评估 API，不注册 Provider 或产品 Runtime。
- `[fail-closed]` primary 在 I/O 前 reserve，open/read/close/clock/control/consumer 异常均
  安全 settle；缺 EOF/terminal/Usage、身份/序号/工具/预算冲突、时钟反转、伪造回执和
  forbidden body fields 均拒绝。disabled gate 始终不发送第二次 recovery 请求，unknown
  Usage/未验证价格保持 `null/unknown`。
- `[verification-local]` 新模块聚焦 `22 passed`；候选相关回归 `67 passed`，流式/适配器/
  恢复合同相邻回归 `82 passed`；Python 3.11/3.13 compileall、静态 no-I/O/import 检查、
  `git diff --check` 通过。系统 Python 3.13 用户环境已安装 `pytest 9.1.1`，项目测试仍以
  仓库 `.venv`（含项目依赖）为准。
- `[unchanged]` 严格 Flash v1 继续 2048/零额外调用，候选 `execution_allowed=false`、
  `capabilities.streaming=False`；默认模型、AgentLoop、统一 Trace/预算、Portal、Account、
  Workbench、Auth、路由、媒体采用和 `production_media=0` 不变。没有真实 API/Key、fresh
  recovery、G53-7、黄金切片、生产准入或 8F 证据。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-public-ci / pending`；
  先在同一干净实现提交上取得 exact-SHA 公共 CI 和协议 dry-run，之后仍需另行授权真实
  recovery、G53-7、黄金切片、生产安全/部署与 8F。

### 2026-09-02：RQ-205 版本化候选 recovery 诊断公共闭环

- `[completed-public]` RQ-204 实现提交 `90242822df0e47304700644572bc12f0a3aa88ad` 的 GitHub Actions
  run `33598541029` 已 `completed/success`；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 均成功且 `head_sha` 精确匹配。公共 pytest 为 `2218 passed, 145 skipped, 1 warning,
  127 subtests passed`，PostgreSQL 控制面为 `201 passed, 1 warning`；前端契约、typecheck、unit、build、
  E2E、RAG、治理和打包冒烟均通过。
- `[completed-dry-run]` 在本地 fake transport 上完成一次 primary 协议演练并写入临时 canonical
  body-free 回执：`calls=1`、`body_free=true`、回执 `3900` bytes；没有读取 Key、发送真实 API、
  发起第二次 recovery 或生成持久诊断结果。
- `[unchanged]` 候选仍 `activation_state=disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、默认模型、AgentLoop、统一
  Trace/预算、Portal、Account、Workbench、Auth、路由、媒体采用和 `production_media=0` 不变。
  Stage 8/8E 仍 `in_progress`，8F 未开始；没有 G53-7、黄金切片、生产准入或真实模型质量证据。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`；
  真实 recovery 只能在新的明确一次性授权后执行，不能因公共 CI 通过而自动打开候选或默认模型。

### 2026-09-02：RQ-206 版本化候选 recovery 诊断一次真实主请求观察

- `[completed-public]` 新增的真实调用组合接缝与测试提交为
  `0b2342c240cfdc1801e673e830c9a7f30bed3fbd`；Actions run `33603143606` 三 job
  exact-SHA 全绿。实现基线为 `90242822df0e47304700644572bc12f0a3aa88ad`。
- `[completed-bounded-real]` 在干净隔离工作树、普通智谱 API 官方基址和
  `glm-5.3-flash` 上只发出一次 primary：`thinking=enabled`、`reasoning_effort=max`、
  `clear_thinking=false`、`max_tokens=8192`、请求级 90 秒、传输 120 秒、SDK retries=0。
  流观察到 model/request identity、reasoning、可见正文、`finish_reason=stop` 和 EOF；首事件
  `3078ms`、首个可见正文 `151453ms`、总延迟 `175875ms`。由于 Usage 缺失、close 失败且单次
  90 秒观察门已触发（在晚到事件中发现），回执安全结算为 `fail_closed / elapsed_limit`，`assembled_complete=false`，
  `calls_reserved/settled=1/1`，没有第二次 recovery，费用 `unknown`。
- `[evidence]` 持久回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq206_v1.json`，
  canonical body-free、`4355` bytes，SHA-256=
  `2ead059ea22f035e6201bee6f3638c8e7a113baed3bf51b55fbbd17e42f862e6`；已通过
  `CandidateRecoveryDiagnosticReceipt.from_dict()` 重解析且 canonical bytes 一致。没有正文、
  reasoning、Prompt、Key 或原始 request ID 写入回执。
- `[interpretation-boundary]` 该结果说明这份冻结上下文在 `max+8192` 形状下确实开始生成，
  但没有在候选单次 90 秒窗口内形成完整、可计量、可交付的中立响应；不能解释为 API/Key
  失败、模型一般质量失败或生产成熟度结论。它还暴露 SDK 读超时与总墙钟截止不是一回事：
  流持续有事件时，当前 observer 只能在事件到达时发现超时，实际请求可拖到约 176 秒。
- `[unchanged]` 候选仍 `activation_state=disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、默认模型、产品 Runtime、
  AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和 `production_media=0`
  均不变。没有执行 fresh-recovery、G53-7、黄金切片、生产安全/部署/合规或 8F。
- `[boundary-next]` 当前唯一下一精确 checkpoint 改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  先离线设计并测试硬墙钟取消、流关闭和 Usage/终态尾帧处理，再决定是否另行授权真实重测。

### 2026-09-02：RQ-207 候选流硬墙钟与 Usage 尾帧后续

- `[completed-local]` 在候选评估接缝中新增显式 `CandidateStreamSession` 与
  `CandidateStreamDeadlineSupervisor`。监督从 attempt 起点按绝对单调墙钟计算，watchdog 只调用
  会话承诺的非阻塞 `cancel`；每次读取前后都会拒绝截止后的晚到事件，不使用线程池等待或任意线程强杀。
  没有显式 `session_opener` 时，legacy opener 会在发起 I/O 前以 `hard_deadline_unsupported` fail closed；
  显式 opener 的返回值则在 opener 调用完成后验证。
- `[completed-local]` `ZhipuStreamSession` 只在候选显式路径打开 `stream_options.include_usage`，持有
  SDK 原始流并以 `close`/`__exit__` 回退清理，`cancel`/`close` 幂等且保留安全的关闭失败次级状态。
  terminal+Usage 或 terminal 后一个合法 Usage-only 尾帧才可完整；缺 Usage、重复/提前/终态后内容、
  截止或关闭失败均保持 unknown/fail closed。旧 `stream_events()` 与产品 payload 不变。
- `[verification-local]` 四个候选/适配器测试文件共 `67 passed`；compileall、governance 与 diff check
  在本地验证通过，本轮没有新的真实 API 请求。公共 exact-SHA CI 尚待同一提交验证。
- `[limitation]` 同步 opener 永久阻塞、或供应商 SDK `close()` 阻塞/不能唤醒 `next()` 时，普通 Python
  没有安全强杀路径；这不是硬截止已被证明的证据，真实重测前须取得 provider-level 连接/取消证据。
- `[unchanged]` 候选仍 `activation_state=disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`；严格 Flash v1 仍 2048/零额外调用，默认模型、产品 Runtime、
  AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；
  没有 recovery、G53-7、黄金切片、生产准入或 8F 证据。
- `[boundary-next]` 该本地实现门随后由 RQ-208 公共 CI 闭环取代；当前下一精确 checkpoint 由本文件的
  canonical 唯一下一步行给出，转为等待新的真实观察授权。

### 2026-09-02：RQ-208 候选流硬墙钟与 Usage 尾帧公共闭环

- `[completed-public]` RQ-207 的实现提交 `015b022bfce6d03452f753794ac126a377f8355b` 已取得 GitHub
  Actions run `33613113829` 的 exact-SHA 公共闭环；`pytest`、`postgres-migrations`、`packaging-smoke`
  三 job 均 `completed/success` 且 `head_sha` 精确匹配。公共 pytest 为 `2241 passed, 145 skipped, 1 warning,
  127 subtests passed`，PostgreSQL 控制面为 `201 passed, 1 warning`。
- `[verification]` 同一 run 的网页契约/生产包、媒体审计工具链、治理、RAG v1 与独立 4M holdout、
  Python compile、Harness dry-run 均通过；本地四文件聚焦保持 `67 passed`。RQ-208 没有读取 Key、
  没有新的真实 API、没有重试或第二次请求。
- `[boundary]` 该公共证据只证明候选评估接缝可复现，不证明供应商 SDK `close()` 的非阻塞/唤醒能力，
  也不构成模型一般能力、领域采用或生产成熟度结论。同步 opener 永久阻塞与 SDK close 无法唤醒
  `next()` 的限制继续作为真实供应商验证闸门。
- `[unchanged]` 候选仍 `activation_state=disabled`、`execution_allowed=false`、
  `capabilities.streaming=False`；严格 Flash v1 仍 2048/零额外调用，默认模型、产品 Runtime、
  AgentLoop、统一 Trace/预算、Portal、Account、Workbench、Auth、路由和 `production_media=0` 均不变；
  G53-7、黄金切片、生产安全/部署/合规与 8F 均未开始。
- `[boundary-next]` 当前唯一精确 checkpoint 已推进为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  只有新的明确一次性授权才可执行下一次真实观察，不能因公共 CI 通过而自动发请求或注册候选。

### 2026-09-02：RQ-209 候选流真实硬墙钟与关闭边界观察

- `[completed-bounded-real]` 在隔离工作树 `HEAD=cc5d5c82ddefd4e9932514634d53d1629e563655` 上，
  使用公共闭环树 SHA `015b022bfce6d03452f753794ac126a377f8355b` 作为回执的 implementation/diagnostic identity，
  按用户“继续”只发出 1 次普通智谱 `zhipu/glm-5.3-flash` primary；SDK retries 为 `0`，候选显式请求 Usage。
- `[evidence]` 回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json`，
  `4342` bytes，SHA-256 `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`；该回执由本地
  证据提交 `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存（公共 CI 尚未宣称）；
  `calls_reserved/settled=1/1`、`run_state=fail_closed`、`terminal_reason=elapsed_limit`、`usage=missing`、
  `cost=unknown`、recovery 未执行。首个事件约 `3421ms`，`reasoning_content_state=non_empty`；总时长
  `90015ms` 触发硬墙钟，未见正文、terminal、EOF 或 Usage，组合会话 `close_state=failed`、`eof_observed=false`。
- `[interpretation]` 诊断层已在 attempt 墙钟到点 fail closed；底层 SDK 读取是否被唤醒、物理读取窗口是否继续，
  仍不能由本回执判断；`close_state=failed` 只是组合会话清理结果，不能进一步归因是供应商 SDK response、迭代器或其他资源失败；
  因而也不能证明底层 close 非阻塞或能唤醒挂起的 `next()`，更不能推出模型一般能力、API/Key、领域采用或生产成熟度结论。
  `observation.elapsed_ms=0` 是截止前未结算的初始投影，真实时序以 latency 的 `90015ms` 为准；单次预算
  `exceeded` 与累计 token `unknown` 并不矛盾。
- `[unchanged]` 候选仍为 `activation_gate=disabled`、`activation_state=candidate`、`execution_allowed=false`、
  `capabilities.streaming=False`，且未注册；
  严格 Flash v1 仍 2048/零额外调用，默认模型、产品 Runtime、AgentLoop、统一 Trace/预算、Portal、Account、
  Workbench、Auth、路由和 `production_media=0` 均不变；没有重试、第二请求、G53-7、黄金切片、生产准入或 8F。
- `[boundary-next]` 当前子阶段尚未关闭，唯一下一精确 checkpoint 保持
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  若要继续验证 provider close/wakeup 或重新观察，必须另行取得明确一次性授权。

### 2026-09-03：RQ-210 候选会话分资源关闭报告公共闭环

- `[completed-public]` 在不改 RQ-209 v2 receipt/schema 2.0.0 与 canonical JSON/SHA 的前提下，提交
  `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 为 `ZhipuStreamSession` 增加仅内存、不可变、body-free 的
  `ZhipuStreamCloseReport`；Actions run `33657368435` 三 job 均 `completed/success` 且 `head_sha` 精确匹配。
  公共 pytest 为 `2241 passed, 145 skipped, 1 warning, 127 subtests passed`，PostgreSQL 控制面为
  `201 passed, 1 warning`。
- `[observed]` 报告只区分 session 所拥有的迭代器和外层 SDK stream wrapper 的关闭状态、组合状态及对象别名；
  shared resource 只表示对象相同，不等同于底层 HTTP response。逐资源最多尝试一次，旧 `close_failed` 投影保持兼容。
- `[boundary]` `cancel()` 仍同步经过 SDK close；本报告没有 `cancel_state`、`wakeup_observed` 或 raw-response
  handle，因此不证明 close 非阻塞、能唤醒挂起 `next()` 或物理连接已关闭。候选仍 activation gate `disabled`、未注册、
  `execution_allowed=false`、`capabilities.streaming=False`；严格 Flash v1 2048/零额外调用、默认模型、产品 Runtime、
  AgentLoop、Portal、Account、Workbench、Auth、路由与 `production_media=0` 均不变。
- `[boundary-next]` 当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-provider-close-wakeup-observation / pending-user-authorization`；
  provider-level close/wakeup 观察、持久分资源字段、候选注册、G53-7、黄金切片、生产准入和 8F 均需另行明确授权。

### 2026-09-03：RQ-211 候选 provider close/wakeup 一次真实观察

- `[completed-bounded-real]` 探针实现、诊断与输入计划身份均冻结为
  `c31127b3c780fe4c493966d8b60f942d3b773fd4`；该 SHA 的 GitHub Actions run
  `33661910096` 三 job 均 `completed/success`。在这一干净快照上按用户“继续”只发送 1 次普通智谱
  `zhipu/glm-5.3-flash` 请求，SDK retries=0，父进程硬边界为 30 秒，没有 recovery 或第二次请求。
- `[evidence]` canonical body-free 回执为
  `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq211_v1.json`，
  schema `1.0.0`，`908` bytes，SHA-256
  `9c86b72561b9c9eb40ab083e326b0386b3572e6d4d684a40f66b54908d2613d2`。实现/诊断/输入计划 SHA
  均精确为 `c31127b3c780fe4c493966d8b60f942d3b773fd4`；回执不含 Key、Authorization、request ID、
  正文、reasoning 原文或 provider body。
- `[observed]` `call_count=1`、`session_opened=true`、首段读取 `78ms`，事件类别只记录
  `reasoning_seen` 与 `content_seen`。`observation_state=not_pending`、`pending_reader_observed=false`，
  因此 `cancel_status=not_attempted`、`reader_woke=false`；子进程退出码为 0、未被强制终止。关闭报告为
  iterator/SDK stream/composite 全部 `closed`，`shared_resource=false`。
- `[interpretation]` `not_pending` 只说明这次有限窗口没有进入挂起的第二次读取，不能证明或否定
  provider close 的非阻塞性、取消能否唤醒 pending `next()`、或底层 HTTP response 是否已被取消。
  全部资源投影为 `closed` 也只是拥有资源的 close 报告，不等于生产级网络中断保证。
- `[verification-boundary]` 新探针聚焦测试在后续测试加固后为 `20 passed`；后续提交
  `5b0ce15d9d4a4c3e413d53032b9f529d20e18f6c` 的公共 run `33662730304` 被外部取消，不能记为成功，
  也不改变本次回执绑定的 c311 exact-SHA 公共证据。候选继续 disabled/未注册，
  `execution_allowed=false`、`capabilities.streaming=False`；严格 Flash v1、默认模型、产品 Runtime、
  AgentLoop、Portal、Account、Workbench、Auth、路由与 `production_media=0` 均不变。
- `[boundary-next]` 当前唯一下一精确 checkpoint 改为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`；
  等待用户决定是否设计可稳定制造 pending-read 的新版本观察协议，不自动追加真实请求、注册候选、进入
  G53-7、黄金切片、生产准入或 8F。
