# 5E-4 Runtime V1 Exit Matrix（最终审计结果）

> 这张表是 5E-4 的工作底稿，不是“全部完成”的宣传清单。`Public` 表示代码、测试和
> 精确 SHA 的 GitHub Actions 都有证据；`Local` 表示只有本地证据；`Deferred` 表示明确
> 不属于 5E V1，并记录未来阶段；`Pending` 表示本轮仍需补证据。

| ID | 验收承诺 | 主要源码/ADR | 直接测试/证据 | 状态 | 限制与退出影响 |
|---|---|---|---|---|---|
| C-01 | Runtime request 只接受 selected Skill | `app/runtime/models.py`, `app/skills/execution.py` | `tests/test_agent_runtime.py`；5E-2 commit `d49508e` / Actions `31959646589` | Public | Router 仍在 Runtime 外；rejected/ambiguous 不伪装成 Agent run |
| C-02 | Event/Trace 1.1 严格合同并兼容合法 1.0 读取 | `app/runtime/models.py`, `signals.py`, ADR-0030 | `tests/test_runtime_models.py`, `test_runtime_contract_v11.py`；Actions `31942483874` | Public | 没有生产旧 Trace 迁移需求 |
| C-03 | Recorder 顺序、配对、lifecycle 和 terminal 不变量 | `app/runtime/recorder.py`, `lifecycle.py` | `tests/test_runtime_recorder.py` | Public | 单进程、单 Recorder；不等于 durable log |
| C-04 | Usage 区分 complete/partial/unknown/not_applicable | `app/runtime/recorder.py`, `models.py` | `tests/test_runtime_recorder.py`, `test_runtime_models.py` | Public | 未配置价格时 cost 为 null；不提供厂商真实账单 |
| C-05 | Trace 原子写入、不可覆盖、SHA 复读 | `app/runtime/store.py`, ADR-0029/0030 | `tests/test_runtime_store.py` | Public | 只是最终快照；崩溃前中间事件不可恢复 |
| F-01 | Agent 与 Harness 共用一个 observed Provider | `app/runtime/runtime.py`, `observed_provider.py` | `tests/test_agent_runtime.py`, `test_runtime_observed_provider.py` | Public | 当前纵向证据使用 Fake Provider，不代表模型质量 |
| F-02 | Agent 只观察 Manifest 允许的业务 Tool | `app/agent/loop.py`, `app/runtime/observed_provider.py` | `tests/test_agent_loop_observation.py` | Public | Harness 内部 `llm.chat` 不计为业务 Tool |
| F-03 | Harness 保持唯一评测、修订、发布权 | `app/harness/runtime.py`, `app/skills/review_executor.py` | `tests/test_harness_observation.py`, `test_skill_review_executor.py` | Public | Runtime 不复制质量门逻辑 |
| F-04 | 两个真实 Skill 通过同一同步 `run()` | `app/runtime/runtime.py` | `tests/test_agent_runtime.py`；Actions `31959646589` | Public | 真实 Skill 指真实项目合同 + 本地执行，不等于真实模型质量 |
| F-05 | typed output 从终态 Artifact 重建 | `app/skills/review_executor.py`, `app/runtime/artifacts.py` | `tests/test_skill_review_executor.py`, `test_agent_runtime.py` | Public | rejected 不暴露报告 |
| E-01 | Boundary/Context 失败安全映射 | `app/runtime/runtime.py` | `tests/test_agent_runtime.py` | Public | 预期错误为安全 reason code；原始异常不进 Trace |
| E-02 | Agent/Evaluation Provider failure 可降级 | `app/runtime/observed_provider.py`, `app/harness/runtime.py` | `tests/test_agent_runtime.py`, `test_agent_runtime_stream.py` | Public | Fake Provider 只证明控制流与 fallback |
| E-03 | Trace persistence failure 不先公开 completed | `app/runtime/runtime.py`, `recorder.py` | `tests/test_agent_runtime.py`, `test_agent_runtime_stream.py` | Public | 失败时可能没有 durable Trace reference |
| E-04 | Observation failure 与业务失败分离 | `app/runtime/observer.py`, `runtime.py` | `tests/test_agent_loop_observation.py`, `test_agent_runtime.py` | Public | 内部 Recorder fail-fast；外部订阅关闭不取消执行 |
| S-01 | Stream item 只有 Event 或 Result | `app/runtime/models.py` | `tests/test_agent_runtime_stream.py` | Public | 仅进程内 Python iterator，不是 API/SSE |
| S-02 | `run()`/`stream()` 共用 `_execute()` 且事件实时交付 | `app/runtime/runtime.py`, ADR-0031 | `tests/test_agent_runtime_stream.py`；Actions `31960987333` | Public | 不是 Token streaming；不提供模型逐 token 输出 |
| S-03 | terminal 只在 Trace commit 后交付 | `app/runtime/runtime.py` | stream Trace failure/parity tests | Public | 仍是最终 Trace 快照，不是事件溯源 |
| S-04 | queue 背压保持顺序，不丢已订阅事件 | `app/runtime/runtime.py` | tiny `queue_size=1` test | Public | 慢消费者会阻塞业务；V1 不做丢弃策略 |
| S-05 | 订阅者关闭不取消 Runtime、不让 worker 永久阻塞 | `app/runtime/runtime.py` | closed-stream test | Public | 后续 stream-only item 可丢弃；无 cancel/resume |
| R-01 | 最坏 event budget 在副作用前拒绝 | `AgentRuntimeV1._required_event_budget` | `tests/test_agent_runtime.py` | Public | V1 预算公式需随新 Signal 显式更新 |
| R-02 | Artifact SHA 指向真实 bytes | `app/runtime/artifacts.py`, `harness/store.py` | `tests/test_agent_runtime.py`, `test_runtime_store.py` | Public | Trace 不保存正文 |
| Q-01 | Trace 不保存 Prompt、正文、Tool data、request ID、异常正文 | `app/runtime/models.py`, `runtime.py` | tracked-data boundary、runtime security tests；Actions `31960987333` | Public | 只覆盖当前字段/路径；未来新增字段必须复核 |
| Q-02 | 两套 RAG gate、治理、compileall、dry-run 可复现 | `.github/workflows/tests.yml`, scripts | Actions `31960987333` | Public | RAG quality gate 与模型领域质量是两件事 |
| D-01 | 真实厂商领域质量已准入 | 5D/5E adoption boundary | 5D-7/ADR-0028 | Deferred/Unknown | 当前无 Provider 领域准入；不阻塞厂商无关 Runtime V1 |
| D-02 | API/SSE/Web UI 对外服务 | 后续 5P/6 | 当前未实现 | Deferred | `stream()` 是内部运行时接口，不是部署 API |
| D-03 | durable event log、崩溃恢复、cancel/resume | 后续阶段 6/8 | 当前未实现 | Deferred | ADR-0031 明确排除 |
| D-04 | Memory、MCP、Multi-Agent、LangGraph/SDK 采用 | 后续阶段/5F | 当前未实现 | Deferred | 必须由 Bad Case、对照和 ADR 重新触发 |
| D-05 | 生产 p50/p95、真实成本和 SLO | 后续阶段 6/8 | 当前未测量 | Deferred | Fake Provider 运行时间不能冒充生产数据 |

## 最终本地审计结论

- `C-*`、`F-*`、`E-*`、`S-*`、`R-*`、`Q-*` 的当前 V1 合同均有本地代码、测试和公开 CI
  路径；5E-3 的精确 SHA 为 `80b76a182f38d31d862f32ffa1dc0f14ebd1c971`，Actions 为
  `31960987333`。
- `D-*` 不是当前实现缺陷，而是明确的后续边界；它们不能被“5E 通过”掩盖，也不应在本轮
  偷偷实现。
- 5E-4 已用 Runtime 聚焦 `128 passed`、完整 `762 passed, 110 subtests passed`、compileall、
  RAG、治理和差异检查复读本矩阵，没有发现当前 V1 必须补的结构性代码缺口。
- 最终退出决策为 `close-with-deferred-boundaries`；本退出审查提交
  `3d3656195a66adfd4595cffa145c978d24c33628` 已由 GitHub Actions run `31962252231`
  完成 exact-SHA 公共验证，因此 5E-4 与整个 5E 已完成。
- canonical 只交接到 `5P-entry-design`；按 RQ-039 暂停，没有开始 5P 设计或实现。
