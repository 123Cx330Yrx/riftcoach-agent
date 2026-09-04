# RQ-225：低思考 G53-3-L 协议与新鲜资产离线实现

## 目标

在 RQ-223 的公共可复现性闭环之上，把低思考候选的三次协议门和全新
oracle-blind 三案例资产做成可验证、可重复的离线控制面。此批不读取 Key、
不发真实请求，也不把候选接入产品 Runtime。

## 实现范围

- `AdapterProtocolSliceRunner` 增加显式 `request_policy` 入口；仍兼容已登记的
  产品 `runtime_profile`，二者互斥。
- 新增 `glm53_low_profile_protocol`：绑定私有低思考策略，复用结构化响应 +
  `knowledge.search` 两回合（总计 3 次请求），输出 body-free、create-only 报告。
  真实来源必须显式确认；默认运行是 Fake Provider 离线来源。
- 新增 `glm53_low_profile_assets`：只读校验新 Dataset、V1.1 Input Plan、
  Prompt/Context Snapshot、fixture SHA、case/marker 唯一性和历史隔离；不构造
  Provider、不读取环境变量。
- 新增三案例 held-out 资产：正常复盘、用户数据边界、检索知识边界。案例 ID、
  措辞和 marker 均不复用历史门；资产创建不等于资产执行。

## 固定合同

| 项目 | 合同 |
|---|---|
| profile | `glm-5.3-flash-candidate-low-4096`，`reasoning_effort=low` |
| 请求 | `max_tokens=4096`、`temperature=1`、`top_p=0.95`、Agent/工具 90 秒、传输 120 秒 |
| 协议 | 结构化 1 次 + 工具往返 2 次，最多 3 次；零重试、无回退 |
| 资产 | schema 1.1、3 个 held-out case、`calibration_excluded=true` |
| 领域资源 | 每案 4 次/24,000 tokens，全域 12 次/72,000 tokens（后续运行合同） |

## 验收

- 低思考协议聚焦测试覆盖策略传播、固定请求参数、body-free 报告、create-only
  写入、真实来源确认和伪造策略拒绝。
- 新资产通过 Dataset/Plan/Snapshot 交叉校验，且准入返回 `external_provider_calls=0`。
- 相关协议/策略/资产回归、`compileall`、`git diff --check`、治理和公共 exact-SHA
  CI 全部通过后，才进入一次性真实 G53-3-L 协议门。

## 边界

本批不执行真实 G53-3-L、不运行 held-out 领域案例、不生成领域结果、不修改默认模型、
Portal、Account、Workbench、Auth、路由或 `production_media=0`。候选仍为
`candidate-only/disabled`，不能据此宣称领域质量、黄金切片、生产准入或 8F。

## 当前指针

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-g53-3l-and-fresh-assets / completed-public / pending-user-authorization`

实现提交 `411753c1d4b89fe0c4ce9098caf380c45e10fa0f` 的 Actions run `33787508488` 已通过
exact-SHA 三 job；公共 pytest 为 `2332 passed, 145 skipped, 2 warnings, 127 subtests passed`。

## RQ-226 真实协议门结果（2026-09-04）

RQ-225 的公共闭环完成后，用户“继续”授权一次最多 3 次的真实 G53-3-L 协议。使用同一候选
`low + 4096` 策略、SDK retries=0，在实现/协议 SHA
`ac63bf4ee70d61fca78813b200cf7775e5ca61d8` 上完成 A1 结构化合同 `1/1` 与 A2 工具往返
`2/2`，协议 `admitted=true`。总计 `3/3` provider calls，输入/输出/总 token `1007/84/1091`，
累计延迟 `12062ms`。

回执使用原有 create-only 路径并以新文件名保存：
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_low_4096_g53_3l_rq225_v1.json`，
`2511` bytes、SHA-256=`a3077ce6d4729e676d0c0ce0d9a6429153075ca59e0850529dee4e29c0376e35`。
它只含安全身份、计数、终态和摘要哈希，不含正文、reasoning、工具参数、Key 或完整请求标识。

本结果只关闭固定三调用协议的真实可达性，不等于 held-out 领域质量、streaming 生产能力、
黄金切片、生产准入或 8F；候选仍 `candidate-only/disabled`，未注册，产品 Runtime、默认模型、
Portal、Account、Workbench、Auth、路由和 `production_media=0` 保持不变。下一步如需继续，
必须另行授权独立三案例 held-out 领域门。
