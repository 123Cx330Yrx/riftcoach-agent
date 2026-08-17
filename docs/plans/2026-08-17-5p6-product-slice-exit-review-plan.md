# 5P-6 Product Slice Evaluation & Exit Review 计划

## 目标

对 5P entry design、5P-1 至 5P-5 做一次独立退出审查，逐条确认产品请求、Prompt Program、
Application Service、文件型查询和 HTTP Adapter 是否形成了职责清楚、可测试、可公开解释的
本地同步产品切片。

退出审查不以“测试数量很多”代替证据，也不把 Fake Provider/no-I/O 误写成真实模型质量或
生产部署。发现属于 5P 合同的缺口时只做最小修补；阶段 6/8 的能力保持 deferred。

## 审查数据流

```text
HTTP product request
→ typed product/compiler
→ verified Prompt Program + composition
→ Domain/Application Service
→ AgentRuntime + ReviewHarness
→ receipt + Trace + manifest + final Artifact
→ RunQueryService
→ HTTP run/report response
```

## 步骤

### Step 1 - 冻结退出标准

- 从 ADR-0032/0033 与 5P 总设计提取功能要求、NFR、测试和明确排除项。
- 输出：exit matrix 的审查维度与证据规则。

### Step 2 - 源码/测试/公开证据审计

- 逐项绑定 5P-1 至 5P-5 的实现、聚焦测试、完整回归与 exact-SHA Actions。
- 检查 HTTP Adapter 是否绕过 Application/Runtime/Query，Prompt identity 是否对应真实组件，
  receipt/query 是否 fail closed，错误响应是否脱敏。

### Step 3 - 比例验证与缺口裁决

- 运行 5P 聚焦和相邻回归、完整 pytest、两套 RAG、compileall、governance、SDK/secret/
  tracked-data boundary、Harness dry-run 和 diff check。
- 仅修复当前 5P exit criteria 的真实缺口；否则记录 deferred/unknown，不堆新技术。

### Step 4 - 退出结论与公共闭环

- 形成 exit matrix、exit review 和面试级表述；同步 canonical/路线/能力矩阵/计划。
- 提交、推送并验证 exact-SHA 公共 CI。
- 5P-6 通过后只把 canonical 交接到 5F，不自动开展 Pi/Claude SDK 实验或阶段 6。

## 完成标准

- 5P 功能要求和 NFR 均有“实现/测试/公开证据/限制/退出影响”的逐条记录；
- 当前范围内没有未处理的结构性缺口，或已完成最小修补；
- 所有本地与公共门禁通过，外部 Provider/Key/Riot/held-out I/O 为 0；
- 关闭结论不宣称真实模型质量、生产 API、Session/Memory、SQL/SSE、鉴权或前端完成。
