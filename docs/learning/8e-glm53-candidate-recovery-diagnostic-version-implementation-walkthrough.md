# RQ-204：版本化 GLM-5.3 候选 recovery 诊断实现 walkthrough

## 先说这次解决什么问题

RQ-203 已经冻结了一个新的、版本化的候选 recovery 诊断协议，但协议文档本身还
不能执行测试。RQ-204 把它落成一个只供 fake/local 评估使用的 Python 接缝，目的是
回答“这一轮候选流到底发生了什么”，而不是把候选偷偷接入产品。

旧的同步诊断器把供应商 SDK、网络 I/O、恢复决定、Usage 投影和落盘混在一起。这样
一旦打开、读取、关闭或时钟本身出错，就可能没有完整账本；未知 Usage 也容易被误当成
零；更危险的是，测试代码可能把正文、reasoning、工具参数或 Key 写进诊断文件。

## Agent/软件原理

这批实现用四个简单原则拆开风险：

1. **先记账，再 I/O。** 每一次可能发生的调用先 `reserve`，因此 open、read、timeout、
   cancel 和 close 失败也有结算槽位。
2. **一次事件泵，多种观察。** 一条已经规范化的事件流只遍历一次，同时送给只保存
   状态的 observer 和只在本次评估内存中暂存结果的 assembler，避免两个消费者各自解释
   出不同事实。
3. **结果由事实推导。** attempt 的完成决定、失败类别、预算状态和顶层 receipt 都由
   观察结果与冻结 profile/policy 重新计算，调用方不能传入一个“eligible=true”就改变结论。
4. **未知就明确写未知。** 缺 Usage、价格未验证或时钟不可用时保留 `null/unknown`，
   不用零值、历史价格或猜测补齐。

## 这次实现了什么、没有实现什么

实现位置：

- `app/evaluation/candidate_recovery_diagnostic_v2.py`：协议值对象、请求形状摘要、
  staged ledger、执行器、预算/费用/延迟投影、严格回执解析和原子写入。
- `app/evaluation/__init__.py`：只把评估 API 导出，便于测试和学习；没有把它注册进
  `ProviderRegistry` 或产品组合根。
- `tests/test_candidate_recovery_diagnostic_v2.py`：完全本地的 normalized fake transport
  和失败矩阵。

明确没有做：真实 GLM API、读取 Key、网络请求、第二次 fresh-recovery、AgentLoop 或
ToolRuntime 接线、Provider 注册、默认模型切换、`capabilities.streaming` 开启、统一
Runtime Trace、Portal/Account/Workbench/Auth/路由修改、G53-7、黄金切片或生产准入。
候选 activation 仍是不可伪造的 `disabled`。

## 代码地图

从外到内可以按下面顺序阅读：

1. `CandidateRecoveryRunSpec` 绑定协议、候选 runtime profile、completion policy 和
   disabled gate；`CandidateRecoveryDiagnosticIdentity` 绑定实现、诊断代码、输入计划、
   context shape 和随机 run nonce 的 SHA。
2. `RequestShapeSummary` 与 `MessageShape` 只保留角色、字段是否存在、字符数、工具
   数量、response-contract 标志和候选身份。它们不会保存消息正文。
3. `CandidateRecoveryDiagnosticLedger` 提供 candidate-only 的 `reserve`/`settle`，
   让 primary 在 I/O 前就占用槽位，并保证每个槽位只能结算一次。
4. `CandidateRecoveryDiagnostic._execute_attempt()` 建立 observer、assembler 和
   `_LatencyBuilder`，把同一组 `ProviderStreamEvent` 依次交给它们；正常 EOF、终止、
   关闭和有效 Usage 都满足时才短暂产生 `StreamAssemblyResult`。
5. `CandidateRecoveryAttemptDiagnostic` 和
   `CandidateRecoveryDiagnosticReceipt` 从 observation 重新计算 disposition、
   failure class、budget 与 first failure，不接受调用方伪造的派生字段。
6. `canonical_receipt_bytes()` 与 `write_candidate_recovery_receipt()` 执行递归
   body-free 检查、canonical UTF-8/LF JSON 和 create-only 原子落盘；已有目标文件永远
   不会被覆盖。

## 数据和控制流

一次本地评估的控制流是：

```text
可信 RunSpec + ChatRequest
        │
        ├─ 规范化候选 cap / timeout / sampling，生成 body-free request shape
        │
        ├─ ledger.reserve(primary)       ← 任何 transport I/O 之前
        │
        ├─ transport.open_stream(fake/local)
        │       │
        │       └─ normalized event pump
        │              ├─ BoundaryObserver：只记字段状态/计数/安全码
        │              └─ ProviderStreamAssembler：只在本次运行内存装配
        │
        ├─ EOF + terminal + close + valid Usage 才允许临时 consumer 接收
        │
        ├─ observation → policy / budget / cost / latency / failure 推导
        │
        ├─ ledger.settle(一次)
        │
        └─ body-free receipt；disabled gate 阻止第二次调用
```

单次候选上限为 output `8192`、agent `90s`、transport `120s`；累计 input `32000`、
output `16384`、elapsed `180000ms`，最多两个槽位但当前只执行 primary。SDK retries
固定为 `0`。费用只有带 `verified=True` 的价格快照才能估算，否则保持 unknown。

## 失败、安全和边界

测试锁住了以下行为：

- 缺 EOF、终止或 Usage，`length`、非法工具片段、序号/model/request identity 冲突，
  以及超出输出/时间预算时 fail closed，不构造产品 `ChatResponse`。
- transport、protocol、identity、usage、budget、completion、consumer、control 八类
  失败只保存安全 code/stage；异常原文不会进入 receipt。
- `KeyboardInterrupt`、`GeneratorExit`、`SystemExit` 和关闭异常先完成安全结算，再把
  控制异常继续抛出，调用方不会误以为成功。
- canonical 序列化会递归拒绝 `prompt`、`body`、`content`、`reasoning`、工具参数、
  Key、request ID 和 SDK 对象等字段；解析器对每一层实行 allow-list。
- 时钟反转或不可用时，延迟字段保持 `null`，但已预留的槽位仍然 settle。

## 验证和运行说明

仓库项目验证使用 `.venv`（Python 3.11.9，已含项目依赖）：

```text
.venv\Scripts\python.exe -m pytest -q tests/test_candidate_recovery_diagnostic_v2.py
22 passed

.venv\Scripts\python.exe -m pytest -q \
  tests/test_candidate_recovery_diagnostic_v2.py \
  tests/test_candidate_evaluation_harness.py \
  tests/test_candidate_stream_contract.py
67 passed

.venv\Scripts\python.exe -m pytest -q \
  tests/test_stream_adapter_contract.py \
  tests/test_zhipu_stream_adapter.py \
  tests/test_response_recovery_contract.py
82 passed
```

另外已用 Python 3.11/3.13 做编译检查，静态扫描确认新模块不导入 SDK、网络客户端、
Key loader、产品 Runtime 或 Provider 实现。系统 Python 3.13 的 `pytest 9.1.1` 也已
安装到用户环境；它没有仓库的 `pydantic` 等项目依赖，所以不作为项目测试解释器。

## 面试/复盘时怎么准确表述

可以说：

> 我实现了一个版本化、候选专用、只保存脱敏状态的 recovery 诊断接缝。它在真实 I/O
> 前记账，用一次规范化事件泵同时做 O(1) 边界观察和临时结果装配，再从观察事实推导
> 预算、失败与回执。当前只通过 fake/local 测试，activation 仍 disabled，因此不能把
> 这批结果说成 GLM-5.3 已进入产品或通过生产准入。

不要说“已接入 streaming”“已自动 recovery”或“本地测试绿所以生产可用”。下一道
明确门是同一实现提交的 exact-SHA 公共 CI 和协议 dry-run；真实 recovery、G53-7、黄金
切片、生产安全/部署和 8F 仍要单独裁决。
