# RiftCoach 需求与约束变更账本

本文档保存会影响后续多轮开发的长期要求。采用追加式记录：新要求可以补充或
显式取代旧要求，但不得静默改写历史。产品路线细节仍以 `docs/roadmap.md` 为准。

| ID | 日期 | 状态 | 长期要求 | 对执行方式的影响 |
|---|---|---|---|---|
| RQ-001 | 2026-08-01 | 生效 | 主路线固定为阶段 0-8，共九个阶段 | 未经用户批准和 ADR，不得增删、合并、重排或改名 |
| RQ-002 | 2026-08-01 | 生效 | 开发必须稳扎稳打，一次推进一个可理解、可验证的小子阶段 | “继续”默认只授权当前状态文件中的唯一下一步 |
| RQ-003 | 2026-08-01 | 生效 | 按纯 Agent 初学者水平讲清问题、原理、实现、数据流、测试和边界 | 编码可以由 Codex 完成，但不能只报告文件和测试数字 |
| RQ-004 | 2026-08-01 | 生效 | 用户需要真正理解 Agent 的底层逻辑，以便面试和简历陈述 | 每个子阶段都要留下教学说明和可验证证据，避免无法解释的技术名词 |
| RQ-005 | 2026-08-01 | 生效 | EchoMind、AGI-Saber、Sea/OpenResearch 等是选择性来源，不是必须照搬的底座 | 每项吸收必须对应 RiftCoach 的真实需求、边界和测试 |
| RQ-006 | 2026-08-01 | 生效 | 不盲目堆叠 SDK、LangGraph、Multi-Agent、向量数据库等技术 | 先记录 Bad Case、备选方案、收益与成本，再通过 Eval 和 ADR 决定 |
| RQ-007 | 2026-08-05 | 已完成，当前状态见 RQ-024 | Skill 先建立一个真实样板，稳定后再扩展首批其他 Skill | 实施顺序已完成；当前真实用户 Skill 为 `recent-form-review` 与 `single-match-review`，不用假 Skill 冒充业务完成度 |
| RQ-008 | 2026-07-22 | 生效 | GitHub 开源和部署是横向交付检查点，不替换 0-8 主路线 | MIT、CI、README 等按成熟度维护；Web/API 在对应能力具备后上线 |
| RQ-009 | 2026-08-06 | 生效 | 不得把多个已规划子阶段静默压缩成一个实现批次并宣称完成 | 即使代码提前覆盖后续内容，也必须回到原检查点逐项复核和确认 |
| RQ-010 | 2026-08-06 | 生效 | 必须用仓库文件维持跨上下文连续性 | 每次接受子阶段或长期需求变化后，更新状态、活动计划、进度和冲突文档 |
| RQ-011 | 2026-08-06 | 生效 | Prompt Engineering、Eval、Observability、安全和成本等基础能力不能等用户偶然提到才补 | 每个子阶段开始和结束时交叉检查能力矩阵，不凭对话临时想起 |
| RQ-012 | 2026-08-06 | 生效 | 对当前完成度必须客观，不把小开发集、合成测试或设计意向说成生产能力 | 状态文档必须分别写明实现、证据、限制和未完成项 |
| RQ-013 | 2026-08-01 | 生效 | 用户观点、PDF、网页端 GPT 建议和参考项目都是待分析证据，不是自动需求 | 标注提案、确认、撤回和条件采用；最新明确纠正优先，不能照单全收 |
| RQ-014 | 2026-08-01 | 生效 | 项目必须分开维护代码进度、理解进度、参考资料审计进度和简历/公开交付成熟度 | 不得以测试通过代替用户理解，也不得以本地实现冒充 GitHub 或部署已同步 |
| RQ-015 | 2026-08-04 | 生效 | GLM 是当前唯一真实 Provider 基线；DeepSeek、Qwen 等是未锁定候选 | 显式 Provider 选择、任务级自动模型路由和 Multi-Agent 分开设计；只有同任务同评测后才选第二 Provider |
| RQ-016 | 2026-08-02 | 生效 | Pi、Claude Agent SDK 等属于条件性 Runtime 采用实验，不是项目默认底座 | 阶段 5F 用真实切片、对照、成本和 ADR 决定采用、局部采用或拒绝；它们不能替代 Harness、Tool Runtime 和领域核心 |
| RQ-017 | 2026-08-05 | 生效 | Prompt/Context Engineering 跨阶段演进，并有明确 V1 落点 | 阶段 2 Prompt V0；5B Skill 指令；5D Context Assembly/结构化输出/不可信边界；5E 版本、Trace、Usage、预算；6-8 继续加入 Memory、Meta、Compaction 和隔离上下文 |
| RQ-018 | 2026-08-05 | 由 RQ-024 取代 | 首批业务目标是 `recent-form-review`、`single-match-review`、`report-fact-check`；一个样板先行不等于缩减为一个 | 历史三 Skill 分类经源码审计修正；保留两个领域 Skill，事实审查继续由已有 Harness Evaluator 承担 |
| RQ-019 | 2026-08-05 | 生效 | 后续阶段可以通过稳定契约深化前面的 V1 能力，但不能借“后续完善”掩盖当前未完成 | 每次深化都记录消费者、接口变化、回归证据和能力边界，不整层推翻重写 |
| RQ-020 | 2026-08-04 | 生效 | 3G-4 及后续真实 Provider 工作被延后，不是取消 | 等真实 Skill/Agent 任务形成后，以领域评测重新触发；近期路线不得擅自插回连续 Provider 接入 |
| RQ-021 | 2026-08-06 | 生效 | 1198 页完整 GPT 导出用于定向查漏；后续专项导出和本任务确认记录更适合判定当前路线 | 不按文件更新时间或篇幅判断权威性；完整历史中的旧方案必须结合后续纠正标注状态 |
| RQ-022 | 2026-08-06 | 生效 | 上下文连续性不能只依赖模型记忆或人工自觉读取文档 | 当前执行状态提供机器可读元数据；每轮恢复和子阶段收尾运行治理预检，冲突时停止功能开发 |
| RQ-023 | 2026-08-06 | 由 RQ-024 取代 | 首批三个真实 Skill 均保留，但用户任务与内部质量步骤必须分开调用 | 该方案在功能代码开始前经源码审计修正；事实审查已有完整 Harness Evaluator，不再重复包装为内部 Skill |
| RQ-024 | 2026-08-06 | 生效 | Skill 数量由独立工作流价值决定，不为维持历史数字复制已有 Harness 能力 | 首批 Skill 修正为 `recent-form-review` 与 `single-match-review`；事实审查保留为强制 `EvaluatorStep`，取消未实现的 invocation mode 与 `report-fact-check` Skill；未来只有真实独立用例和 Bad Case 才重新评估内部 Skill |
| RQ-025 | 2026-08-06 | 生效 | Router 评测必须区分历史基线、可校准 development 与规则冻结后的 independent holdout；holdout 失败不得反向调规则 | 数据集强制声明角色、污染记录、案例数量和候选 Skill 版本快照；默认 CLI 拒绝 holdout，污染后必须退休并升级版本 |
| RQ-026 | 2026-08-07 | 生效 | 5C V1 暂缓 LLM Router fallback；一个小型合成语义 Bad Case 不足以引入模型调用 | 保留确定性 Router 与冻结规则；优先类型化入口和澄清。只有新鲜数据出现多个独立失败族、Provider 结构化输出与质量/延迟/成本/故障评测通过后，才用新 ADR 重新评估 |
| RQ-027 | 2026-08-12 | 生效 | 用户授权 5D-6b 内后续有明确实验目的、脚本硬预算和脱敏边界的真实 Provider 测试不必逐次询问，并要求完整验证 | 只覆盖当前已批准检查点内的有界测试，不等于无限调用、盲目重试、扩大厂商数量或越过阶段；每次仍须先离线设计/TDD、设置调用上限、失败即停并记录成本与证据 |
| RQ-028 | 2026-08-13 | 生效 | 保持稳扎稳打，但在不跨检查点和安全边界时可以一次完成更大的连贯能力切片 | 每轮优先交付可运行、可测试、可讲解的完整纵向切片，而不是人为拆成过小函数；扩大批次不得越过 canonical 唯一下一步、跳过 TDD/CI 或混入第二 Provider、领域 Skill 等未授权范围 |
| RQ-029 | 2026-08-14 | 已执行，由 RQ-034 收口 | D5 唯一第二 Provider 候选应选 DeepSeek V4 Pro 正式版，而不是仅因便宜选择 Flash | ADR-0018 取代 ADR-0017 的候选模型与金额停止线；协议门和领域门均绑定 `deepseek-v4-pro`，DeepSeek 停止线为 `$0.10`；Flash 只保留为以后成本/时延分层候选，本次更正不授权真实调用或 held-out |
| RQ-030 | 2026-08-14 | 模型分层归属生效；当前候选由 RQ-034 收口 | DeepSeek V4 Pro 曾作为 5D-7 单候选；当前 V3 已关闭，但 Flash/Pro 分层仍不放入 5F，最早在 5P 后、默认在阶段 6 有真实成本/时延证据后重开 | 5F 继续只负责 Pi / Claude Agent SDK Runtime 采用实验；未来以全新同任务评测比较 Pro-only、Flash-only 与 Flash 默认/Pro 有界升级，证据不足时保持单模型；ADR-0019 的未来归属继续有效，旧 Pro 协议与领域结果保持只读 |
| RQ-031 | 2026-08-15 | 迁移顺序生效；立即下一步由 RQ-035/RQ-036 取代 | GLM-5.3 已有官方模型文档，允许作为新的同厂商模型迁移候选，但不得直接替换 GLM-5.2 | API 可用后仍按 G53-0 可用性/合同审计、G53-1 Zhipu thinking profile 离线 TDD、G53-2 公开 CI、G53-3 最多 3-call 协议门、G53-4 新 Dataset/输入计划领域门推进；旧 GLM-5.2、DeepSeek Adapter、结果和 held-out 只读隔离，不覆盖、不重跑；通过领域门前不改默认模型、不实现自动路由。 |
| RQ-032 | 2026-08-15 | 资源合同原则生效；DeepSeek V3 由 RQ-034 关闭 | 任何新的真实领域 Provider 门在读取 Key 或构造 Provider 前，必须证明资源合同能到达必需的 Agent 工具往返与独立 Evaluation；真实 Usage、tokenizer-free 长度投影和未知值必须分层表达 | DeepSeek V2/V3 结果保持不可变，长度投影不得冒充官方 Token 或继续生成 V3 预算；该原则改由未来全新 Provider 实验继承，并与 RQ-034 的安全错误 provenance 前置条件同时满足。 |
| RQ-033 | 2026-08-15 | 已执行（首错停止） | 用户明确确认执行一次真实 DeepSeek V4 Pro development Usage 校准，固定为 2 profiles × 4 stages、最多 8 calls、每请求 output 64、64000 observed tokens、`$0.10`、零重试和首错停止 | 真实入口先通过 `6aa8c43` / Actions `31868747216`，同 SHA prepare-only 为零调用；正式 replay 在第 1 次请求未形成规范化 `ChatResponse` 后以 `provider_response_invalid` 停止，后 7 次未发送。结果不可覆盖或补跑；实际 Usage/费用 unknown，不创建预算/V3 held-out，不据此判断模型质量。 |
| RQ-034 | 2026-08-15 | 关闭与安全前置条件生效；立即下一步由 RQ-036 取代 | 当前 DeepSeek V3 资源校准与领域采用尝试关闭；保留低层协议事实，但不准入领域质量或产品默认模型 | 不生成 budget/held-out，不补跑 V1/V2/calibration；未来任何真实 Provider 门必须先离线实现跨厂商 `failure_code` 与允许列表安全 `provider_error_code` 双层 provenance，禁止原始响应/异常落盘。G53-0 仍是未来迁移入口，但不再阻塞 5D-7 收尾。 |
| RQ-035 | 2026-08-15 | 生效 | GLM-5.3 普通 API 尚未正式可用；DeepSeek Pro 当前尝试保持关闭，不立即切换 Flash；GLM-5.2 继续作为开发基线 | 将 G53-0 标为 deferred，不读取 Key、不调用未上线模型；先完成 RQ-034 要求的安全错误 provenance 离线合同和公开验证。未来只有明确成本/延迟或同任务对照需求、且基础设施先修复后，才重新设计 Pro/Flash 对照实验。 |
| RQ-036 | 2026-08-15 | 生效 | 用户确认不让 GLM-5.3 外部发布时间阻塞项目，先执行 5D-7 review；模型采用可以诚实地以 reject/unknown 收尾 | ADR-0028 将 5D-7 的退出标准固定为评测、实验控制和采用决策能力，而不是强制一个 Provider 通过。当前无领域 Provider 准入；G53 deferred、Flash/Pro 分层和旧结果边界保持不变。5D-7 review 通过后唯一下一检查点为 `5D-exit-review`，不自动进入 5E。 |
| RQ-037 | 2026-08-17 | 本次顺序授权生效 | 用户明确授权：当前 5E-2 Task D 完成并通过公开验证后，无需再次等待“继续”，直接进入唯一下一检查点 5E-3 | 该授权只跨越当前完成门进入 5E-3，不授权静默合并 5E-3/5E-4、跳入 5P/5F、调用真实 Provider 或改变技术采用门；进入 5E-3 后仍按教学、TDD、持久状态和独立验收执行。 |
| RQ-038 | 2026-08-17 | 本次顺序授权生效 | 用户进一步明确：进入后续唯一子阶段并完成时，同样可以直接继续下一个 canonical 检查点，无需重复询问 | 每次只自动推进一个已完成当前阶段后唯一明确的下一子阶段；仍须先更新持久状态、讲解原理、执行 TDD/门禁和公开验证，绝不跨越未完成的决策门或合并多个子阶段。 |
| RQ-039 | 2026-08-17 | 当前暂停要求生效，覆盖 RQ-038 的自动继续 | 用户要求完成本轮 5E-4 验证与提交后结束 | 完成 5E-4 exact-SHA 公共闭环和必要状态回写后停止；只把 canonical 交接到 `5P-entry-design`，不开展 5P 设计、代码、Provider I/O 或后续子阶段，等待用户再次明确“继续”。 |
| RQ-040 | 2026-08-17 | 生效，解除 RQ-039 的当前暂停 | 用户再次明确“继续下一步”，只恢复 canonical 的 `5P-entry-design` | 先完整审计并设计 5P Prompt Program V1 与早期产品切片；本轮不自动实现 FastAPI、不读取 Key、不调用 Riot/Provider、不进入 5F。设计、治理和 exact-SHA 公共验证完成后，唯一下一步为 5P-1 typed product/compiler。 |
| RQ-041 | 2026-08-17 | 已执行 | 用户再次明确“继续”，只授权 canonical 的 `5P-1-product-contract-compiler` | 完成严格产品 DTO、typed Skill selection、Artifact binding 与 Manifest-derived Runtime policy 的教学、TDD 和公开验证；不实现 Prompt Program/FastAPI、不读取 Key、不调用 Riot/Provider。5P-1 闭环后只交接到 5P-2，等待下一次明确继续。 |
| RQ-042 | 2026-08-17 | 已执行 | 用户再次明确“继续”，授权 canonical 的 `5P-2-prompt-program-runtime-composition` | 只实现版本化 Prompt Program、component fingerprint/drift gate、verified Runtime identity 与薄 composition root；不安装 FastAPI、不实现 Application Service、不读取 Key、不调用 Riot/Provider、不进入 5P-3 或 5F。完成本轮后必须同步持久状态并等待 exact-SHA 公共验证结果。 |
| RQ-043 | 2026-08-17 | 生效 | 用户再次明确“继续下一步”，授权 canonical 的 `5P-3-domain-application-service` | 只提升 Summary/Report domain services、建立 RecentReviewApplicationService 与安全错误映射，并允许首个正式消费者对 5P-2 secure execution factory 做窄幅向后深化；不安装 FastAPI、不实现 receipt/query、不读取 Key、不调用 Riot/Provider、不进入 5P-4 或 5F。 |
| RQ-044 | 2026-08-17 | 已执行 | 用户再次明确“继续”，授权 canonical 的 `5P-4-file-backed-run-receipt-query` | 只实现 body-free immutable receipt、文件 Store、严格 RunQueryService、Trace/manifest/final Artifact 交叉校验与 Application Service receipt 接缝；不安装 FastAPI、不实现 HTTP、SQL/Session/Memory、恢复扫描或 5F。完成本轮后只交接到 5P-5，等待下一次明确继续。 |
| RQ-045 | 2026-08-17 | 生效 | 用户明确“继续5P-5”，授权 canonical 的 `5P-5-thin-fastapi-adapter-no-io-vertical-slice` | 只实现薄 FastAPI HTTP Adapter 与 Fake/fixture 本地无 I/O 纵向切片：POST recent、GET run、GET report、GET health、严格 OpenAPI/错误映射和 TestClient 门禁；不读取 Key、不调用 Riot/Provider，不实现 SQL/Session/Memory/SSE/后台任务/公网部署/5P-6/5F。 |
| RQ-046 | 2026-08-17 | 生效 | 用户再次明确“继续”，授权 canonical 的 `5P-6-product-slice-evaluation-exit-review` | 只审查 5P entry 与 5P-1 至 5P-5 的功能/NFR/安全/资源/公开证据，建立 exit matrix、必要的当前范围内最小修补和退出裁决；不读取 Key、不调用 Riot/Provider，不实现 5F、阶段 6、SQL/Session/Memory/SSE/鉴权/前端。 |

## 新条目格式

后续新增长期要求时，使用新的 `RQ-xxx` 行，并注明日期、状态以及它如何改变
执行方式。若取代旧条目，将旧条目标为“被 RQ-xxx 取代”，不要删除旧记录。
