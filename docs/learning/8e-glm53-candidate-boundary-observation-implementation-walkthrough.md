# 8E 学习记录：GLM-5.3 候选边界观察合同实现（RQ-197）

## 1. 这批解决什么问题

RQ-194 已能把一条智谱流装配成完整 `ChatResponse`，但完整装配器不能用来判断“为什么
没有交付”：真实截断、网络半流、模型错配和 Usage 缺失需要不同的处理。RQ-197 将
RQ-196 冻结的边界落成一个只观察外形的离线合同。它回答的是“这一次流在合同上走到了哪
一步”，不是“模型回答得好不好”，也不执行第二次请求。

这仍是 8E 的受控高级实验接缝。GLM-5.3-Flash 是当前唯一主力候选目标，但候选仍未注册，
`execution_allowed=false`；严格 Flash v1 的 2048 输出上限和零额外调用不变。

## 2. 代码地图与数据流

```text
fake/local normalized events
        │
        ├─ validate_provider_stream_event（共享事件级校验）
        │
        └─ CandidateStreamBoundaryObserver
             ├─ 只累积状态、计数、SHA-256 和有界时间
             ├─ EOF + terminal + close + valid Usage
             │      ├─ complete_text / tool_calls_ready
             │      └─ candidate_shape（由 policy 再分类）
             └─ 任何边界错误 → fail_closed
```

- `app/evaluation/candidate_stream_contract.py`：精确候选绑定、不可变
  `BoundaryObservation`、状态观察器、fake/local transport port 和独立 Trace 投影。
- `app/providers/stream_adapter_contract.py`：`ProviderStreamEvent` 的显式 null presence
  标记，以及 assembler 与观察器共用的事件级校验核心。
- `app/providers/zhipu_stream_adapter.py`：智谱 delta 翻译时保留“字段缺失”和“字段显式
  null”的区别；仍然只提供显式 adapter，不打开产品 streaming。
- `tests/test_candidate_stream_contract.py`：候选边界、预算、脱敏、状态机和资源清理矩阵。

## 3. 关键合同

`CandidateRuntimeBinding` 只接受精确的 `zhipu / glm-5.3-flash`、candidate v2 profile
`2.0.0`、fresh-recovery policy `1.0.0`，并要求 `primary=1`、`fresh_recovery=2` 的
连续尝试身份。候选 transport 固定 8192 单次上限、90 秒执行窗口、120 秒传输窗口、
`temperature=1`、`top_p=0.95` 和 `max_retries=0`；它只接受注入的 opener，不导入 SDK，
也不进入 registry、composition root、AgentLoop 或 Worker。

`BoundaryObservation` 是冻结的 allow-list 值对象。它只保留生命周期、finish code、
content/reasoning 字段状态、工具调用数、有效 Usage 数字、单调耗时、解析后的候选 model、
request ID 的 SHA-256 和安全错误码。正文、reasoning、工具参数、Prompt、Key、SDK 对象、
原始 request ID 和异常原文都不会进入 observer、`repr`、JSON 或 Trace。Usage 缺失/非法时
三个 token 字段保持 `None`，绝不把未知当作零。

完整结论必须同时满足真实 EOF、合法 terminal、成功 close 和 valid Usage；缺任一项都不能
构造 `ChatResponse`。`length + 空正文 + 非空 reasoning + 有效 Usage` 只能形成
`candidate_shape`，再交给既有 policy 计算资格；调用方不能写入 `candidate_eligible`。

观察状态和下一动作由 observer 推导，值对象会拒绝直接构造的矛盾组合（例如把已关闭的
完整流伪装成 `not_started`）。观察器一旦失败会保持原始安全错误，完成后快照也不可再改写。
清理只吞普通 `Exception`；`KeyboardInterrupt`、`SystemExit` 和 `GeneratorExit` 继续向上
传播，避免把用户取消伪装成普通 provider 失败。

## 4. 验证证据

- 候选合同、共享 assembler、智谱 adapter、响应完成策略和恢复合同聚焦回归：
  `163 passed`（本地 Python 3.11）。
- `compileall`、`git diff --check` 和治理检查已通过。
- 测试覆盖正常 text、tool-call shape、reasoning-only length、缺 EOF/terminal/Usage、
  model/request identity conflict、重复 terminal/Usage、工具索引/元数据/参数上限、输出
  预算、时钟异常、迭代器与外层资源关闭，以及 body-free JSON/repr。
- 全量本地 pytest 的首个错误来自未配置 `RIFTCOACH_TEST_DATABASE_URL` 的 PostgreSQL
  fixture（`DATABASE_URL is required`），不是本批代码路径。
- 同一干净实现提交 `127e6da43ef1b71b284a7e8d4198547b04c556d8` 的 Actions run `33507627615`
  已由 RQ-198 完成 exact-SHA 公共验证：三个 job 全绿，公共 pytest 为
  `2178 passed, 145 skipped, 1 warning, 127 subtests passed`。

## 5. 明确没有做的事

本批没有真实 API/Key I/O，没有 fresh-recovery，没有 G53-7 或黄金切片，没有注册候选、
打开 `capabilities.streaming` 或改全局默认模型；Portal、Account、Workbench、Auth、
路由、统一 Runtime Trace、生产预算和 `production_media=0` 均未改。它也没有实现未来的
`CandidateStreamEvaluationHarness` 或累计 ledger；那是公共 CI 之后的独立设计/实现门。

## 6. 当前门与下一步

当前状态为 `completed-public / candidate-only`。下一精确 checkpoint 是：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-evaluation-harness-design / pending`

下一轮只设计隔离 harness/ledger/Trace 接缝；fresh-recovery、G53-7、候选注册和生产准入仍需单独裁决。
公共 CI 通过不等于领域准入或公共生产成熟度，本轮到此暂停。
