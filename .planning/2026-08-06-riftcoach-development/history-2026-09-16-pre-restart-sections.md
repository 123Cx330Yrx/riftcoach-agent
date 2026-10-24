# 重启前 Current Phase / Next Step 原文归档

2026-09-16。以下全部为历史材料，不是当前执行指令；当前看 task_plan.md 与 canonical。

## Current Phase

当前精确 checkpoint：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。

当前仍处于 `8e-productization`。RQ-212 的候选 evaluation-only 离线回放、RQ-213 的一次真实
close/wakeup 观察、RQ-214 的 SDK/HTTP 闸门离线预检和 RQ-215 的一次真实 transport-gated
观察均已完成；这些证据只描述客户端观察合同，不是 8E、领域采用或生产准入完成。RQ-211～214
的历史回执保持不可变。RQ-215 在同 SHA 公共 CI run `33721483490` 三 job 全绿后只发出 1 次
真实请求，随后定位到 `client_wakeup_close_race` 并完成候选适配器的本地关闭顺序修复；实现提交
`3740cdbe2d02b140780ea2b8834793df268e6ac1` 的 Actions `33726209532` 三 job exact-SHA 全绿。
RQ-217 又在 RQ-216 的文档/证据闭环 SHA `3e028b1217f1274152ba161993287f29188a1b73` 上按一次性授权只发出 1 次真实
transport-gated 请求，得到 `client_wakeup_clean`；RQ-218 的 G53-3 在最新实现上 3/3
通过，RQ-219 的候选 8192 单次真实流在 90 秒硬墙钟以 `fail_closed / elapsed_limit`
收口；RQ-220 已完成 9 场景零网络档位—终态—Usage—恢复拆分；RQ-221 又完成显式
`low + 4096` 候选 profile 的 exact-SHA 公共 CI 与一次真实无工具探针，得到
`observed/stop/usage-valid`。当前精确执行指针改为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`。
RQ-222 已完成低思考候选独立领域门的设计裁决；RQ-225 的协议接缝与新鲜资产已取得同一 SHA 的公共 exact-SHA CI；
RQ-226 又在用户“继续”授权后完成低思考 G53-3-L 的一次有界真实协议门。RQ-227 已在实现 SHA
`659757eca7ff1b658dfd164631512d3964c5a2ff` 的 exact-SHA 公共 CI run `33826568517` 三 job 全绿后，
按用户“继续”授权完成一次且仅一次三案例 held-out 领域门：第 1 案 Evaluation=96 且安全通过；
第 2 案 Evaluation=97 但没有 evidence source IDs 且 injection check 失败，触发 `unsafe_publication` 全局停止；
第 3 案按冻结规则跳过。脱敏回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
（7537 bytes，SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`），
累计领域调用 `6/12`、总调用 `9/15`，领域/累计 token 为 `17834/18925`；候选未注册且
`admitted=false`。当前停在独立失败归因与下一版本裁决，不重跑同一考卷。RQ-228 已完成候选专用的
证据来源硬门、可信策略附录、marker 无关的拒绝性脱敏和 body-free 证据诊断；实现
`e2efe8fd75e8cf27cbee7e90484fc90d288ce065` 的 Actions `33832025848` 三个 job 全绿。RQ-229 又完成了
全新加固领域 V2 协议与资产的 no-I/O 准入；实现
`c50cf231957bc54201d0207b99110fcf4b2897b3` 的 Actions `33843064715` 三个任务 exact-SHA
全绿。RQ-230 已在用户“继续”授权后完成 V2 专用真实运行器，并在同一 SHA 公共 CI 通过后完成一次
有界真实观察；首案质量/终态不匹配，后两案按首错停止。RQ-231 已在用户“继续”后完成 V3
有界修订设计：保持 85 分和全部安全/事实硬门，允许最多一次 Harness 修订，并增加 body-free
枚举计数诊断。RQ-232 已完成离线实现、兼容边界修复和 exact-SHA 公共闭环。RQ-233 的新鲜
G53-3-L 尝试在回执延迟校验处失败，修复及 exact-SHA 公共闭环已完成；RQ-234 随后已通过新鲜
协议三次真实调用及 V3 零调用预检；RQ-235 的一次真实领域验收已在首案检索零片段后安全停止，
未进入评测或修订。RQ-236 已完成候选检索合同的离线加固与执行器接线，并取得同一实现 SHA 的公共 CI；RQ-237 已接受全新领域资产设计；当前精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-retrieval-hardened-domain-assets-design / completed-real-observation / pending-retrieval-failure-attribution`。

Phase 20 - `6B-4-conversation-bound-recent-review-identity` is complete at
`d63f908` / Actions `32347834279`. Phase 21 -
`6B-5-memory-candidate-write-gate` is complete at `dd7c9c8` / Actions
`32376405150`. Phase 22 - `6B-6-preferences-profile-review-memory` is complete at
`5531c81` / Actions `32387026797`. RQ-071 authorizes the strict sequential chain
`6B-7 → 6B-8 → 6B-9` without per-step approval. Phase 23 -
`6B-7-training-plan-progress` is complete at `f6d8922` / Actions `32397290175`.
Phase 24 - `6B-8-memory-aware-context-typed-turns` is complete at `aacc11a` /
Actions `32403187972`. Phase 25 - `6B-9-lifecycle-export-exit-review` is complete
at `cbc7cbd` / Actions `32408101770`. Phase 26 -
`stage-7-standard-mcp-dynamic-meta-entry-design` is complete at `e50a546` /
Actions `32436092074`. Phase 27 - `7-1-mcp-client-contract` is complete at
`37f16bc` / Actions `32439753589`. Phase 28 -
`7-2-mcp-transport-and-discovery` is complete at `f121666` / Actions `32441793585`.
Phase 29 - `7-3-opgg-meta-adapter` is complete at `64311a1` / Actions
`32455219404`. Phase 30 - `7-4-riftcoach-mcp-server` is complete at `431c584` /
Actions `32480827952`. RQ-079 authorizes Phase 31 -
`7-5-mcp-interoperability-exit-review`, now complete through implementation
`a88fbc4` / Actions `32483521108` and evidence `fac6fe0` / Actions
`32484257736`. RQ-080 authorized Phase 32 -
`stage-8-multi-agent-reliable-runtime-productization-entry-design`, now complete
at `3431e8b` / Actions `32564500421`. Phase 33 -
`8a-advanced-adoption-gate` is complete at `12ad835` / Actions `32567642315`.
Phase 34 - `8b-conditional-multi-agent-experiment` is complete at `783a329` /
Actions `32572610725`. RQ-083 authorized Phase 35 - `8c-reliable-runtime-core`;
it is complete at `2df5349` / Actions `32587659678` with exact-SHA PostgreSQL/Linux
public closure. RQ-084 authorized Phase 36 -
`8d-riot-opgg-evidence-fusion-core`; it is complete at `a274b7f` / Actions
`32598480400`. Phase 37 - `8e-productization` is the current governance pointer.
The bounded Riot/OP.GG validation and JSON-null Bad Case, Batch B profile/routing,
Batch C Evidence/Product/SSE, Batch D Workbench, live integration, Batch E E1-E5,
production shell/Auth gate and Timeline DTO/UI are publicly closed. The atomic slice
`bilingual-product-surface-foundation` is publicly closed at `6084937/32757872792`;
RQ-163 的 Agent 主线交接与 README 事实版已完成；
 `g53-1-adapter-profile-offline-tdd` 已完成本地实现与回归；`g53-2-exact-sha-ci` 已按精确 SHA
 完成公共三 job 验证；`g53-3-bounded-protocol-gate` 已在新普通 API Key 下通过；
  `g53-4-fresh-domain-gate` 已按一次性授权本地执行并因 `unsupported_parallel_tool_calls` 拒绝，不自动重试；
  `g53-5-fresh-flash-capability-matrix-v1` 已完成本地真实观察（`11/11` calls、`46,151` tokens、`7/8` cases pass），
  但 `production_admitted=false`、`public_ci_confirmed=false`。RQ-176 Flash-only 产品运行时接线已完成本地实现，
  要求精确 Flash Provider 先绑定注册 profile；组合根可从该 concrete profile 自动推断，显式 profile 仍须一致；
  完整产品化仍为 `in_progress`。
Full productization and coverage remain
`in_progress/planned`; RQ-192 的候选装配合同与 RQ-193 的本地 provider conformance 已完成，RQ-194 已完成候选适配器本地实现与公共 CI，未接入产品 streaming；
提交 `8bcbaa5ba467fcaad76193d3790d34a106a47d72` 的同 SHA 公共 CI run `33489903978` 与 RQ-194 提交
`a7580e861cd986c026040c7fcfcc3fa577737961` 的 Actions run `33496237588` 均三 job 全绿且 head_sha 精确匹配。
RQ-197 已完成候选边界观察合同的 fake/local 实现，聚焦与相邻回归 `163 passed`；RQ-198 已记录同一干净提交的
exact-SHA 公共 CI 三 job 全绿；RQ-199 已完成隔离候选评估台设计，RQ-200/RQ-201 已完成实现及公共验证，RQ-202
已完成边界加固，RQ-203 已完成版本化诊断协议设计，RQ-204 已完成 fake/local 版本化诊断实现。当前活动阶段为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-transport-gated-real-observation / completed-clean-client-observation / pending-next-decision`，
RQ-217 的一次真实观察与安全回执已完成，仍不注册候选或改变默认。

## Next Step

当前执行：`8e-productization / candidate-real-golden-slice / in-progress / offline-hardening-and-live-consumption`。用户已授权持续做到黄金切片，A/B/C 不重开；执行 RQ-258 计划，先完成真实入口的离线加固与工件重放，再做报告、事务、live Workbench 消费。本轮真实调用已发生但黄金切片未通过；不切生产默认。

RQ-254公共执行完成：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-summary-evidence-bridge / completed-public / pending-evidence-publication-wiring-design`。下一步为同源Evidence应用/快照发布接线离线设计，明确摘要交付、身份/执行权与发布顺序；以下待CI记录为历史。

RQ-254 当前执行：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-summary-evidence-bridge / completed-local / pending-public-ci`。纯桥本地实现和128项验证已完成，下一步仅本实现同SHA公共CI；不调用真实接口或接生产。以下RQ-253及更早下一步均为历史。

RQ-253 当前执行：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-data-slice-preparation / completed-design / pending-offline-summary-evidence-bridge`。按RQ-253计划第3节离线实现Summary→Evidence纯桥接及真实四段版本格式窄修复；不写数据库、不调用真实接口、不切默认。以下RQ-252及更早下一步均为历史。

RQ-252 当前执行：应用组合实现afda193 / Actions34076953653三任务同SHA公共验证通过。下一步为RQ-251计划第4节真实数据切片接入准备；不再等待本实现CI，不新增真实请求。下方RQ-250与更早执行摘要均为历史。

RQ-250 当前执行：RQ-250工具批量预算修复完成本地、公共和完整真实开发验证。独立组合1.2.0/Skill0.4.0/程序2.2.0将本地工具总量从3调整为8，原报告/质量/9次模型调用预算不变；旧合同摘要及RQ-249失败回执保留。实现772179eba46ca02c99bc7d920e3ab048e39d0468 / Actions34033770356三任务同SHA全绿，新增13项/相邻196项、公共后端2701项通过。新完整四案经济96、整体97、生存96、记忆97，均3来源，事实/引用/注入检查通过，记忆预算偏好确认通过；17次真实调用，输入72595/输出14676 tokens。连同前一批定位问题的4次，本轮合计21调用/101133 tokens。当前开发验证已收口，下一步准备产品采用与真实数据黄金切片的衔接，不重复此开发批、不自动启默认或另立正式考卷。8E仍in_progress、production_media=0；这是已知两局合成demo的开发证据，不是独立领域准入或公共生产成熟度；GLM-5.2、前端与主仓库用户修改均不动。

RQ-249 历史执行：用户明确要求全套测试并以“开始”授权本轮：补齐记忆专项，离线与同SHA公共验证通过后，直接执行经济→整体→生存→记忆四案真实开发批次，无需逐案再授权。四案使用同一实现及high/8192/60秒合同，每案最多9调用/649728 tokens，整批最多36调用/2598912 tokens；质量失败记录后继续独立后案，认证/额度/连接/超时或执行中断等共性故障停止。复用已知两局demo，不是新held-out，不拿旧96/95分拼接；不改默认、前端、GLM-5.2或旧回执，8E in_progress、production_media=0。RQ-248“只做一次经济观察”的下一步被本条取代；本地实现完成：新增18项，聚焦与相邻共180项通过，编译、零网络预检、治理及diff检查通过；当前待本实现公共CI，随后直接执行已授权真实批次，真实请求0。八维学习复用RQ-246计划的RQ-249节。

当前唯一下一步：`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-product-application-composition / completed-public / pending-real-data-slice-preparation`。

RQ-248 已完成修复版产品开发观察入口：显式high组合、实际Runtime、版本/预算绑定、默认零网络、先预约后创建Provider，以及逐调用/检索/评测安全诊断和中断记录。整链测试发现“补刀经济”同主题别名误判，保留原测试输入修复，不降阈值、不增加补查次数；混合主题与未知词仍拒绝。新增53项、相邻共330项及27子测试通过。实现 `02860e271ad595034f80d66f528edee838bebe1f` / Actions `34031421463` 已核对同SHA，pytest、postgres-migrations、packaging-smoke三任务全部成功；唯一下一步为一次有界经济开发观察；本批真实请求0，不新开正式考卷。默认、前端、GLM-5.2、旧资产/回执与production_media=0不变，8E仍in_progress；旧经济真实评测精确原因仍未知。八维学习与操作复用RQ-246计划的RQ-248节。

以下RQ-247及更早动作是历史，不再重复执行。

RQ-247 已完成本地缺陷复现与修复：两种矛盾评测走已有一次纠正、缺引用走原有一次来源驱动修订；安全诊断保留到回执。用户要求适度释放资源，新显式组合使用high/8192/60秒，不改变9调用与事实/引用/85分门。真实协议3调用及产品13调用是修复前结果，经济无有效评分；原始记录不覆盖。实现 `679b203b5dfe65f64bc586e618caaf850cafd2db` / Actions `34030008563` 已核对同 SHA，pytest、postgres-migrations、packaging-smoke 三任务全部成功；下一步仅准备修复版 high 档、带安全诊断的有界开发观察入口（零网络），不重跑旧正式验收或自动另立考卷，本轮不再付费测试。以下 RQ-246 待协议动作均为历史。

RQ-246 公共收口：实现 `3eca1e8995f37050d635451c53667ad7ad404b75` 的 Actions `34028036153` 已核对精确 headSha，pytest、postgres-migrations、packaging-smoke 三任务全部 success。产品版本独立验收准备完成本地与公共闭环，唯一下一步为新鲜产品 G53-3-L；后续协议使用执行时干净 HEAD 及其同 SHA 公共证据，不把纯文档收口 SHA 冒充已核验实现 SHA。上方待本实现 CI 动作已被本条取代。真实 API=0、默认/前端/GLM-5.2/旧回执不变，8E in_progress、production_media=0。

RQ-246 已完成产品版本独立验收准备：全新五局合成输入、四场景冻结资产、实际产品 Runtime 观察入口、严格新鲜证据预检和不可覆盖回执；33项新增、聚焦/相邻共115项通过。下一步本实现同 SHA 公共 CI，之后才新鲜产品 G53-3-L。真实 API=0，默认、GLM-5.2、前端与旧回执不变；本条取代下方 RQ-245 准备待办。详见 `docs/plans/2026-09-06-coach-product-acceptance-preparation.md`。

RQ-245 公共验证已完成：实现 `cecde250e131a0e81585e2e91ec261fad6817700` / Actions `34026629061` 三任务全部成功。下一步准备新产品版本独立真实验收，明确绑定实际产品 Runtime、Skill/程序和预算，不复用旧领域结果；不自动调用真实 API 或打开默认。下方待 CI 动作为历史。

RQ-245 已完成显式新产品组合的离线实现：真实 Runtime→报告/Evidence/Trace、Memory 与 Worker 所有权、九调用预算和假 SDK 智谱适配器均通过；33 项新增、271 项相邻测试通过。唯一下一步为本实现同 SHA 公共 CI；通过后才准备新产品版本独立真实验收，不自动调用 API 或启用默认。详见 `docs/plans/2026-09-06-offline-coach-runtime-wiring.md`。以下 RQ-244 及更早待办是历史。

RQ-244 已完成新报告合同九调用预算证明与产品迁移版本清单，104 项测试通过；实现 `1cd2deb` / CI `34025448118` 三任务全绿，下一步直接推进实际 Runtime 的新执行组合离线接线。真实 API=0，不改默认模型或前端；详细见 `docs/plans/2026-09-06-report-contract-budget-and-runtime-migration.md`，下方旧动作均为历史。

RQ-242 本批：economy_adjustment 实际 4 次调用、3 来源、revision_failed；修订错误类别和中间评测诊断已通过 117 测试与 `a64331b` / CI `34022245397` 三任务公共验证。下一步候选生成/修订合同对齐的离线设计与回归，按当前计划的产品接入差异清单推进；不重复经济观察、不把开发回执算作正式准入。

以下检索加固阶段的下一步均保留为历史记录，不能替代上方当前动作。
RQ-230 已完成一次 V2 真实观察并完成失败归因；RQ-231 接受的全新 V3 最多一次受控修订、
body-free 枚举计数诊断、版本化预算证明和新资产 no-I/O 准入已由 RQ-232 完成；修复提交
`f99c142c269df765deb592c463ce6e2555bcc3fe` 的 Actions `33895602378` 三任务 exact-SHA 全绿。
RQ-233 的新鲜 G53-3-L 尝试因两层延迟口径不一致未能生成回执；修复 `110f9e8` 的公共 CI 已
全绿。RQ-234 协议和 RQ-235 V3 真实验收已完成；下一批只用独立开发用例离线定位并加固
候选查询/检索/零命中合同和安全诊断，先冻结方案再实现，不降门槛、不重跑协议或已消费考卷。
RQ-227 的真实领域门已完成有界观察但拒绝准入：第 1 案通过，第 2 案因证据来源缺失与注入检查失败触发
`unsafe_publication`，第 3 案冻结跳过；回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_domain_gate_rq227_v1.json`
（7537 bytes，SHA-256=`b9fbebacf5c277c6b2cd57f018ff58cfb2646dbad95f6cdc9e90822646a68400`）。
RQ-228 只在候选入口加固上述两条边界，默认产品与 GLM-5.2 兼容路径不变；同一实现 SHA 的
公共 CI 已全绿。RQ-229 已另立全新协议/资产版本并完成 no-I/O 准入；实现
`c50cf231957bc54201d0207b99110fcf4b2897b3` 的 Actions `33843064715` 三个任务 exact-SHA
全绿。用户已授权一次新的 V2 有界真实领域观察；RQ-230 运行器本地完成后，下一动作先取得其
实现 SHA 的公共 CI，再在同一干净 SHA 上执行，不重跑同一 held-out 资产。
RQ-217 的真实回执绑定实现/观察器/输入计划提交
`3e028b1217f1274152ba161993287f29188a1b73`，文件为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_transport_gate_real_rq217_v1.json`，
`1284` bytes、SHA-256=`ad4b920e94f019dae0b08c166e248c12349bdee0d73bf14b8ab2342e6b428ef3`；
Actions run `33727163550` 三 job 全绿。结果为真实流启动后 gate 进入、pending reader 被唤醒，
且 RQ-216 的 reader-owned 关闭顺序让 iterator/SDK/composite 均为 `closed`，结论为
`client_wakeup_clean`；不得自动注册候选、进入 G53-7/黄金切片，也不修改产品 Runtime、Portal、
Account、Workbench、Auth 或路由。

`6B-6-preferences-profile-review-memory` 已由实现/最小测试修复 `5531c81` 与 Actions
`32387026797` 完成 exact-SHA `pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环，
coverage 已 complete。6B-7 又由 `f6d8922` / Actions `32397290175` 完成 exact-SHA 三 job 公共闭环。
RQ-071 授权的 `6B-7→6B-8→6B-9` 已严格依次闭环：6B-8 由 `aacc11a` / Actions
`32403187972` 完成，6B-9 由最小测试修复 `cbc7cbd` / Actions `32408101770` 完成 exact-SHA 三 job。
`7-3-opgg-meta-adapter` 已由 `64311a1` / Actions `32455219404` 完成 exact-SHA
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环，coverage complete。
`7-4-riftcoach-mcp-server` 已由 `431c584` / Actions `32480827952` 完成 exact-SHA
`pytest`、`postgres-migrations`、`packaging-smoke` 三 job 公共闭环，coverage complete。
`7-5-mcp-interoperability-exit-review` 已由实现 `a88fbc4/32483521108`、不可覆盖双向 evidence 与
证据提交 `fac6fe0/32484257736` 完成 exact-SHA 公共闭环，coverage complete，Stage 7 关闭。
`stage-8-multi-agent-reliable-runtime-productization-entry-design` 已由 `3431e8b` / Actions
`32564500421` 完成 exact-SHA 公共闭环，coverage complete；`8a-advanced-adoption-gate` 又由
`12ad835` / Actions `32567642315` 完成。`8b-conditional-multi-agent-experiment` 的 implementation
`180bc8b/32572085065` 与 result/ADR/evidence `783a329/32572610725` 均 exact-SHA 公共闭环，
coverage complete。8C 已由 `2df5349/32587659678` 完成 0010、durable event/replay、lease/fencing、cancel、
checkpoint/recovery、Worker/API/package 纵向与八维材料的 exact-SHA 公共闭环；coverage complete。8D 又由
`a274b7f/32598480400` 完成 exact-SHA 公共三 job 与 coverage 闭环。8E 的真实 preflight、Batch B/C/D、Live integration、E1–E5、production shell/Auth gate、Timeline 与
bilingual/product-journey foundation 已依次公共闭环。当前 canonical checkpoint 是 `8e-productization`，
其中唯一原子项曾为 RQ-108 `portal-motion-polish`，其 design 与 runtime Tasks 1–4
已公共闭环。Task 5 的 RQ-133 v6.1 relay edit 在 task 前 HTTP 400/费用 0；豆包 comparator rejected。official
即梦 Smart Edit 又完成一次有效调用，actual compact prompt 与长版 preflight 已分开；raw SHA
`4d3660b...155b` 的 motion direction promising，但 source `0.889072`、seam `0.046536`、AAC/non-fixed-fps
未过门。历史生成式候选和零费用 proof 均保持 research-only，`production_media=0`。Portal/Account 的 Focus Rail、
handoff、双语文案和响应式 hygiene 已完成本地实现与回归；RQ-161/162 的局部视觉修补也已完成。按 RQ-163，当前文档
交接已收口，`g53-0-no-io-audit` 已完成本地静态审计并停在 `blocked/deferred`；G53-1 离线 profile TDD、
 G53-2 exact-SHA 公共 CI、G53-3 普通 API 协议门已完成，G53-4 新鲜领域门首错拒绝。RQ-171 适配器合同修复与
 RQ-172 G53-5 真实矩阵观察、RQ-173 F7 工具流上限独立诊断与 RQ-174 G53-6 正式领域门（两次首案停止）均已完成，
 用户已明确选定 Flash-only 产品目标，组合阶段要求显式 profile，或仅从已绑定同一注册档案的 concrete Provider 自动推断；
   RQ-180 已在 A/B 证据链上完成一次 G53-7 真实领域尝试，但首例以 `provider_response_invalid/incomplete_chat_response`
   停止，`admitted=false`，领域采用与正式生产成熟度仍未通过。RQ-181 已确认该首例的 `length`/reasoning-only 形状，RQ-182
   已完成版本化响应完成策略与离线 TDD，RQ-183 已完成候选 runtime/attempt/Trace/预算合同；RQ-184 又完成候选合同
   实现 A/B 的 exact-SHA 公共 CI 与同一 SHA G53-3（A=`e25c3579…`、B=`eca01ce…`）。RQ-185–RQ-187 记录候选诊断的
   无响应边界，RQ-188 又以三路固定探针确认合法 Flash endpoint/model 路径可达、同步小额度先耗尽 reasoning，并
   观察到流式首个 reasoning chunk。严格 Flash v1 为 2048/零额外调用，8192/一次 fresh-recovery 仍是未注册候选；
RQ-192 已完成离线 provider-neutral 流式装配合同（29 项聚焦测试），RQ-193 已完成测试内智谱 provider conformance；
RQ-194 已完成 `ZhipuStreamAdapter` 本地实现与 `20 passed` fake 测试。提交 `a7580e861cd986c026040c7fcfcc3fa577737961` 的同 SHA
公共 CI run `33496237588` 已通过，三 job 全绿且 head_sha 精确匹配；RQ-195 已完成候选 runtime 接线架构评审，RQ-196
又完成候选 runtime wiring design，冻结四元身份、BoundaryObservation、共享校验、v2 transport 和独立 Trace 投影；
RQ-197 又完成候选边界观察合同的 fake/local 实现与 `163 passed` 聚焦/相邻回归，RQ-198 已取得同 SHA 公共 CI
三 job 全绿；RQ-199 已完成隔离候选评估台设计（staged ledger、单次事件泵、独立 receipt 和失败矩阵），RQ-200
已完成 fake/local 候选评估台实现与 `102 passed` 相邻回归（harness 聚焦 `15 passed`），RQ-201 已取得实现提交
`f2a80320123d80a6441f3fcac310014a9bd4550e` 的 exact-SHA 公共 CI run `33536168224`（公共 pytest `2193 passed, 145 skipped, 1 warning, 127 subtests passed`）。当前活动阶段为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`，
不注册候选、不接入产品 streaming、不进入 G53-7、
不进入 Workbench、不新增媒体采用、不改变 8E checkpoint；不打开 `capabilities.streaming`，不把候选实现写成生产准入。

- [current-evidence-override] RQ-205 已完成上述公共 CI 待办：`90242822df0e47304700644572bc12f0a3aa88ad` /
  Actions `33598541029` 三 job exact-SHA 全绿并完成协议演练；当前唯一下一项为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-real-call / pending-user-authorization`。

- [current-evidence-override] RQ-206 已覆盖上述真实调用门：`0b2342c240cfdc1801e673e830c9a7f30bed3fbd` /
  Actions `33603143606` exact-SHA 三 job 全绿，并只执行 1 次 primary；观察结果为 `fail_closed / elapsed_limit`，
  未触发 recovery。当前唯一下一精确 checkpoint 为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-real-call-timeout-usage-followup / pending-user-authorization`；
  下一轮先做离线硬墙钟取消、流关闭和 Usage/终态尾帧测试，不自动再次调用。

- [current-evidence-override] RQ-209 已完成上述一次性真实观察：本地证据提交
  `0b276cc1c07ff2cfdb1dfd339e8dc66ab6aff40c` 保存 canonical body-free 回执（`4342` bytes，SHA-256
  `56794fc171c959bbc9f4be6bcb12c5b9300b373dd0a2d270678db81c450c7c6a`）；只发出 1 次 primary，诊断层在
  `90015ms` 的 attempt 墙钟处 `fail_closed / elapsed_limit`，组合 `close_state=failed` 不能归因具体底层资源，
  未执行 recovery/重试。当前唯一下一项仍为
  `8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-provider-close-wakeup-observation / pending-user-authorization`；
  本次离线实现与公共验证授权已消费，不自动发送新的真实请求，不注册候选、不打开 `capabilities.streaming`。

<!-- 历史归档结束；后续执行见当前 task_plan.md。 -->
