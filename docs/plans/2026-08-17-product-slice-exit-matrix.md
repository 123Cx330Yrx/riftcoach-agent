# 5P-6 Product Slice Exit Matrix（本地退出审计）

> 这张矩阵逐项回答“5P 原来承诺了什么、代码在哪里、测试证明了什么、公共证据在哪里、
> 仍有什么限制”。`Public` 表示对应实现已由精确提交 SHA 的 GitHub Actions 验证；
> `Deferred` 表示明确不属于 5P；`Unknown` 表示当前没有足够证据，不能用推测补齐。

## 1. 十项功能要求

| ID | requirement | source/design | implementation | tests | public CI | limitation | exit impact |
|---|---|---|---|---|---|---|---|
| F-01 | 接受严格、有限的近期复盘产品请求 | 5P 总设计 §4/§8；ADR-0033 | `app/product/recent_review.py::RecentReviewProductRequest` | `tests/test_recent_review_product_compiler.py`：默认值、严格类型、额外/服务器字段、Riot ID、count/queue/focus 边界 | `57bd36a` / Actions `31987501935` | 当前只有近期复盘产品入口；没有单局 HTTP、自由对话或 follow-up | Public；满足 5P V1 |
| F-02 | 从 Riot/Data Dragon 形成合法 Summary，并生成确定性报告 | 5P 总设计 §3/§11；5P-3 计划 | `app/lol/player_summary.py`、`app/lol/report_renderer.py`；CLI 改为复用 app-level 逻辑 | `tests/test_recent_review_domain_services.py`、`tests/test_stage1_pipeline.py`：短局/timeline 边界与 CLI 字节一致；Application tests 覆盖坏 Summary/零有效比赛 | `4bd5c83` / Actions `31998739178` | 本轮使用 Fake/fixture，不代表真实 Riot 可用性；局部 detail/timeline 失败会显式保留边界 | Public；满足领域层与确定性 fallback 输入要求 |
| F-03 | 类型化入口可信选择 `recent-form-review`，不重新猜自由文本 | 5P 总设计 §9；ADR-0033 | `RecentReviewRuntimeRequestCompiler` 从 Catalog 读取精确 Skill，以 `entrypoint:reviews.recent` 形成 typed selection | compiler 测试把 `DeterministicSkillRouter.route()` 替换为必失败函数仍能编译；缺 Skill/漂移时 fail closed | `57bd36a` / Actions `31987501935` | 这不是自然语言 Router 泛化能力；产品入口本身已提供任务类型 | Public；避免 HTTP 层二次误路由 |
| F-04 | 从 Catalog/Manifest 同源生成 Skill identity、输入绑定和 Runtime policy | 5P 总设计 §9；5P-1 计划 | `app/product/recent_review.py`；复用 `SkillInputArtifactBinding` 与 `SkillExecutionBoundary` | Manifest 全字段投影、服务器 run ID、真实 bytes/SHA-256、篡改和编译后 Catalog drift 测试 | `57bd36a` / Actions `31987501935` | SHA/合同校验不防有本机写权限者同时改写全部数据和元数据 | Public；满足可信编译与二次验证 |
| F-05 | 加载并校验 recent-form Prompt Program V1 | 5P 总设计 §10；ADR-0032 | `app/prompt_program/*`、`prompt_programs/recent-form-review/manifest.json`、`build_component_fingerprints()` | `tests/test_prompt_program.py`：严格 manifest、自摘要、secure Evaluation 1.1、组件/Skill/Context/Evaluation drift fail closed | `0a9651f` / Actions `31988837293` | component fingerprint 是可重复漂移门，不是程序行为等价证明，也不是 Prompt 质量分 | Public；满足版本化 Prompt/Context provenance |
| F-06 | 通过唯一 `AgentRuntimeV1.run()` 执行，不复制 Agent/Harness | 5P 总设计 §6/§11/§12；ADR-0033 | `app/runtime/composition.py::RuntimeCompositionRoot`、`app/product/recent_review_service.py` | Prompt Program composition、Application 调用顺序、API no-I/O vertical slice；真实 Runtime/Harness/RAG + Fake Provider | `0a9651f` / `4bd5c83` / `6d1e5b0`；对应 Actions 均成功 | Fake Provider 只证明接线与控制流；当前无真实 Provider 领域准入 | Public；满足单一运行与发布控制面 |
| F-07 | 返回 published/degraded/rejected 或安全 Runtime failure | 5P 总设计 §11/§14/§15；5P-3 计划 | `RecentReviewApplicationResult/Error` 与 `app/api/main.py` allowlisted 映射 | Application tests 覆盖三类 publication、typed/untyped Runtime failure、run ID/terminal mismatch；API tests 覆盖稳定 HTTP code/body | `4bd5c83` / Actions `31998739178`；`6d1e5b0` / Actions `32005648179` | degraded 可能是确定性 fallback，不代表模型输出通过；原始异常被有意舍弃 | Public；满足 fail-closed 和安全降级 |
| F-08 | 文件型 receipt/query 安全读取 run 与最终报告 | 5P 总设计 §13；5P-4 计划 | `app/product/run_receipts.py`、`app/product/run_query.py` | receipt 不可覆盖/原子失败清理；receipt/Trace/manifest/final Artifact 交叉校验；篡改、重复报告、rejected 泄漏均 fail closed | `932a863` / Actions `32002994441` | 单进程文件投影，不提供事务、多 worker 一致性、目录扫描或崩溃恢复 | Public；满足本地同步查询切片 |
| F-09 | 提供最小 health endpoint | 5P 总设计 §14；ADR-0033 | `GET /health` in `app/api/main.py` | `tests/test_fastapi_adapter.py::test_health_is_liveness_only`；OpenAPI 只暴露四个冻结路径 | `6d1e5b0` / Actions `32005648179` | 只证明进程 liveness，不探测 Riot/模型/数据库 readiness | Public；满足 5P 最小健康合同 |
| F-10 | 用 Fake Provider 与本地 fixture 完成无外部 I/O HTTP 纵向测试 | 5P 总设计 §17；5P-5 计划 | `create_app(review_service, query_service)` 显式 ports；测试装配真实 Application/Runtime/Harness/RAG/receipt/query | `test_no_io_vertical_slice_uses_real_runtime_harness_rag_and_query`；API 聚焦 24；完整 `884 passed, 1 warning, 110 subtests passed` | `6d1e5b0` / Actions `32005648179`；最终 5P-5 状态 `1ba9355` / Actions `32005901066` | 无 Key/Riot/Provider/网络调用；因此不能据此声称真实 Coach 质量或线上稳定性 | Public；满足本地可重复纵切面 |

## 2. 分层与控制权

| ID | requirement | source/design | implementation | tests | public CI | limitation | exit impact |
|---|---|---|---|---|---|---|---|
| L-01 | HTTP 只适配协议，不拥有业务编排 | ADR-0033；5P 总设计 §2/§6 | `app/api/main.py` 只依赖 `ReviewServicePort` / `RunQueryPort` | Adapter import 审计、严格 OpenAPI、委托行为测试 | `6d1e5b0` / `32005648179` | 尚无正式 composition/启动 CLI 与公网 server 配置 | Public；层次边界成立 |
| L-02 | Application Service 拥有一次产品用例的控制顺序 | 5P 总设计 §11；5P-3 计划 | Summary → validate → report → compile → Runtime → receipt | Application 顺序、前置失败不生成 run、Runtime 后终态投影测试 | `4bd5c83` / `31998739178`；5P-4 接缝 `932a863` / `32002994441` | 当前同步执行；没有后台 job 或幂等请求模型 | Public；用例边界成立 |
| L-03 | Domain 层只做 LoL 数据/报告业务，不读取 HTTP 或 Prompt | 5P 总设计 §3/§11 | `app/lol/player_summary.py`、`report_renderer.py` | Domain/CLI parity 与 Stage 1 回归 | `4bd5c83` / `31998739178` | 上游网络策略仍由既有 client 负责，不等于统一 Tool Runtime | Public；领域逻辑可被 CLI/API/MCP 复用 |
| L-04 | Runtime 负责 Agent 执行与 Trace，Harness 独占发布权 | ADR-0029/0030/0033；5P 总设计 §7/§12 | `AgentRuntimeV1` + secure product execution factory | Prompt Program composition、Runtime/Harness 纵向与 5E 既有回归 | 5E 公共证据链 + 5P-2/5P-5 Actions | 没有真实模型领域准入；Runtime 不是数据库/会话系统 | Public；没有第二套 Agent/Harness |
| L-05 | Query Service 复读证据，不信任 receipt 单一声明 | 5P 总设计 §13；5P-4 计划 | `RunQueryService` 交叉核对 receipt/Trace/manifest/Artifact bytes | `tests/test_run_query_service.py` tampering matrix | `932a863` / `32002994441` | 本地共同写权限攻击不在 V1 威胁模型内 | Public；查询不会绕过完整性链 |

## 3. 非功能、安全与资源要求

| ID | requirement | source/design | implementation | tests | public CI | limitation | exit impact |
|---|---|---|---|---|---|---|---|
| Q-01 | 严格合同与 fail-closed | 5P 总设计 §8/§10/§13/§15 | Pydantic strict/frozen/extra-forbid；Catalog/Program/Query 完整性门 | compiler、prompt program、application、receipt/query、API 负例 | 5P-1 至 5P-5 Actions | 严格 Schema 不等于所有语义都正确 | Public；满足 V1 合同安全 |
| Q-02 | body-free/allowlisted 错误脱敏 | 5P 总设计 §15/§16 | Application/API/Query 只映射固定 code/message/有限 reason 与 Retry-After | 原始 URL、异常、路径、Prompt、Key、损坏正文不进入公开对象 | `4bd5c83`、`932a863`、`6d1e5b0` 对应 Actions | 本地开发日志的未来新增字段仍需复核 | Public；满足当前公开边界 |
| Q-03 | 模块 import/OpenAPI/CI 不读取 Key、不触发网络 | ADR-0033；5P 总设计 §12/§17 | 显式 dependency ports；真实 Provider 不在 import 时构造 | env/http monkeypatch、tracked secret/run-data、SDK boundary、CI | `6d1e5b0` / `32005648179`；最终 `1ba9355` / `32005901066` | 正式启动 composition 尚未实现，因此也未证明真实配置加载 | Public；满足 no-I/O 可重复性 |
| Q-04 | 资源有界 | 5P 总设计 §8/§16 | count 5—20；Manifest-derived context/iteration/tool/deadline policy；同步单次用例 | product bounds、policy projection、Runtime budget/deadline 回归 | 5P-1 + 既有 5D/5E Actions | 没有 HTTP 并发上限、限流、p50/p95 或 SLO | Public for local V1；生产容量 Deferred |
| Q-05 | 文件结果不可覆盖并按真实 bytes 验证 | 5P 总设计 §13/§16 | immutable receipt、Trace/Artifact SHA-256 与严格复读 | store atomicity、duplicate write、tampering tests | `932a863` / `32002994441` | Trace 与 receipt 之间仍有 crash gap | Public；满足本地证据完整性，恢复 Deferred |
| Q-06 | Prompt 变更可追踪且漂移即拒绝 | ADR-0032 | Program manifest/self digest/component fingerprints/verified identity | Prompt Program drift matrix | `0a9651f` / `31988837293` | 尚无 Prompt 效果消融或真实模型质量分 | Public provenance；质量 Unknown |
| Q-07 | 本地回归与知识检索质量门可复现 | 5P 总设计 §17 | pytest、RAG development/independent holdout、compileall、governance、dry-run | 5P 聚焦 `121 passed, 1 warning`；Runtime/Harness 相邻 `166 passed`；完整 `884 passed, 1 warning, 110 subtests passed`；两套 RAG 指标均满足门槛 | 既有 5P-5 Actions；5P-6 exact-SHA 待本退出审查提交验证 | 唯一 warning 是 FastAPI TestClient 的上游 httpx 迁移提示；RAG gate 不是模型报告质量 | Local pass；待 5P-6 公共闭环 |
| Q-08 | 公开开源证据与本地事实对应 | RQ-008/RQ-012/RQ-014 | 每个子阶段独立 commit + exact-SHA CI；状态分四条进度线 | Actions 状态与提交 SHA 复读 | entry `49841ec/31985199623`；5P-1 `57bd36a/31987501935`；5P-2 `0a9651f/31988837293`；5P-3 `4bd5c83/31998739178`；5P-4 `932a863/32002994441`；5P-5 `6d1e5b0/32005648179` | GitHub 公开通过不等于公网产品部署 | Public；5P-6 自身仍待 exact-SHA |

## 4. 明确 deferred / unknown 的能力

| ID | requirement | source/design | implementation | tests | public CI | limitation | exit impact |
|---|---|---|---|---|---|---|---|
| D-01 | 真实 Riot 产品调用 | 5P 总设计 §5/§17 | 未在 5P-6 执行 | 本轮调用数 0 | 不适用 | 真实区域、限流、账号和 Data Dragon 联网链路未由 HTTP 产品入口验证 | Deferred；不阻塞 no-I/O 切片退出 |
| D-02 | 真实模型 Coach 领域质量 | ADR-0032/0033；5D-7/ADR-0028 | 当前没有领域 Provider 准入 | Fake Provider 只验证协议与控制流 | 不适用 | GLM/DeepSeek/Qwen 的事实、引用、建议、成本、延迟仍 unknown | Unknown；不能作为产品效果宣传 |
| D-03 | SQL、事务、多 worker 与崩溃恢复 | 5P 总设计 §13/§16 | 未实现 | crash gap 被显式测试/记录为限制 | 不适用 | file receipt 不是数据库 | 阶段 6/8；不在退出审查偷加 |
| D-04 | Session、Memory、follow-up 与长期训练进度 | 5P 总设计 §5 | 未实现 | 路径在 OpenAPI 中明确不存在 | `6d1e5b0` / `32005648179` | 当前一次请求一次复盘 | 阶段 6 |
| D-05 | 鉴权、限流、CORS、多租户隔离 | 5P 总设计 §16；ADR-0033 | 未实现 | API 只验证当前 allowlisted 错误/路径 | 不适用 | 无这些能力前不得公网绑定 | 阶段 6/部署门；5P 不是生产就绪 |
| D-06 | SSE、后台任务、Token streaming、cancel/resume | 5P 总设计 §5 | 未实现 | deferred endpoints 404 | `6d1e5b0` / `32005648179` | POST 同步阻塞 | 阶段 6/8 |
| D-07 | 正式前端与公网部署 | RQ-008；5P 总设计 §5 | 未实现 | 无部署证据 | 不适用 | 当前只有本地 TestClient/API 切片 | 后续横向交付门；不能称已上线 |
| D-08 | 标准 MCP、Multi-Agent、LangGraph、DAG | 5P 总设计 §5/§19 | 未采用 | 没有 Bad Case 支持采用 | 不适用 | 参考项目只提供方案证据 | 5F/7/8 按各自采用门处理 |
| D-09 | Pi / Claude Agent SDK 采用 | RQ-016；5P 总设计 §19 | 未开始 | 尚未做同切片对照 | 不适用 | 不知道收益能否覆盖迁移/依赖成本 | 5F 独立 entry design；5P 不替其下结论 |
| D-10 | 生产成本、p50/p95、RPS、可用性 SLO | 5P 总设计 §16 | 未测量 | Fake/no-I/O 数字不得代替 | 不适用 | 没有真实业务流量 | 阶段 6/部署后观测 |

## 5. 本地退出裁决

- 十项功能要求均有实现、直接测试和既有 exact-SHA 公共证据；没有发现必须留在 5P
  修复的结构性产品代码缺口。
- 分层、错误脱敏、文件完整性与 no-I/O 边界均有直接负例，不依赖“测试总数很多”作推断。
- 本轮已复跑 5P 聚焦 `121 passed, 1 warning`、Runtime/Harness 相邻 `166 passed`、完整
  `884 passed, 1 warning, 110 subtests passed`，两套 RAG、compileall、Harness boundary、
  tracked secret/run-data、dry-run 与 governance 均通过；真实 Key/Riot/Provider/held-out
  调用为 0。
- 本地结论为 **`close-with-deferred-boundaries`**。在 5P-6 退出提交获得 exact-SHA 公共 CI
  前，5P-6 仍保持 in progress；公共成功后才可正式关闭 5P 并只交接到 5F entry design。
