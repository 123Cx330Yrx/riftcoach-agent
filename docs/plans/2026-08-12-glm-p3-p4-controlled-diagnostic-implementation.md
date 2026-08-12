# GLM P3/P4 Controlled Diagnostic Implementation Plan

**Goal:** 在不扩大 5D-6b 范围的前提下，修正 Thinking 与工具参数验收边界，并用最多
一次、最多 5 calls 的真实探针复核 P1-P5。

### Task 1: Freeze request-policy and argument-contract tests

**Files:** `tests/test_zhipu_capability_probe.py`

1. 写红灯：P1-P5 必须显式关闭 Thinking。
2. 写红灯：Schema 合法但 query 措辞不同的 arguments 应通过并进入 P5。
3. 写红灯：额外键、非法类型/范围与 disabled 后非空 reasoning 必须 fail closed。
4. 运行目标测试并确认失败来自旧实现，而不是测试夹具错误。

### Task 2: Implement the controlled probe

**Files:** `app/providers/zhipu_probe.py`

1. 为结构化和工具请求加入智谱官方 disabled-thinking request body。
2. 使用冻结 Tool JSON Schema 验证解析后的 arguments object。
3. 在 P4 到 P5 的边界拒绝非空 reasoning，不保存正文。
4. 更新官方文档快照日期，保持 5-call、无重试和历史输出兼容。
5. 运行目标测试、Provider/structured 比例回归、compileall、diff check 和治理预检。

### Task 3: Execute one authorized controlled P1-P5 run

**Files:** 新增唯一结果 JSON；更新活动计划事实与进度。

1. 确认 Key 只存在而不显示；记录代码 SHA 和独立输出路径。
2. 用 `--confirm-real-call --scope p1_p5 --max-calls 5` 运行一次，不自动重试。
3. 校验结果合同和脱敏白名单；不读取或保存原始模型正文/reasoning。
4. 若 P1/P4 依赖失败，按控制流停止，不补跑单项。

### Task 4: Evidence closeout

**Files:** canonical state、requirements、活动计划、路线历史、能力矩阵、项目决策。

1. 分开记录第一轮与受控轮的证据，不覆盖失败历史。
2. 根据 mandatory 结果决定继续 Task 4 Adapter TDD，还是留在诊断边界。
3. 运行完整 pytest、RAG 门禁、compileall、安全检查、Harness dry-run 和治理门禁。
4. 提交、推送并核对精确 SHA 的公开 CI；不自动进入 5D-7。
