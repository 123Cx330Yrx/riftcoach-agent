# 8E 学习记录：GLM-5.3 Flash V3 离线实现（RQ-232）

## 1. 问题与原则

RQ-230 的 V2 运行器把修订预算固定为零，导致首稿事实核验失败后只能拒绝；本批把 RQ-231
的设计落成候选专用、离线可验证的 V3 实现。质量门没有降低，V3 也没有进入产品 Runtime。
核心原则是“先预留资源，再 I/O；先完成身份和资产准入，再允许真实调用；任何不完整或不安全
结果都 fail closed”。

## 2. 设计与实现地图

- `provider_domain_production.py`：`max_revisions` 默认仍为 `0`；显式 V3 才传入 `1`，并把
  评测轮次投影为 body-free 的枚举计数。
- `domain_e2e.py` / `coach_report.py`：共享固定的评测类别、严重度、轮次和分数类型；额外字段
  由 `extra="forbid"` 拒绝。
- `glm53_bounded_revision_budget.py`：每案 9 次、全域 27 次调用墙，调用前预留、Usage 结算后
  校验，未知或越界立即关闭。
- `glm53_bounded_revision_budget_reachability.py`：用冻结 Context 和请求包络离线推导每案
  `203000`、全域 `608000` token 上限，并生成可重建报告。
- `glm53_hardened_domain_v3_assets.py`：绑定全新 Dataset、Input Plan、Context、协议、fixture
  和预算报告的 SHA，拒绝 RQ-227/V2 历史污染且不构造 Provider。
- `glm53_hardened_domain_v3_gate.py`：候选专用 V3 入口；缺少同 SHA 公共 CI 或新鲜 G53-3-L
  证据时分别返回 `pending_public_ci` / `pending_protocol_evidence`。

## 3. 控制流

```text
V3 资产准入（零 I/O）
        ↓
每案 Agent 最多 4 次 → 首评/格式修复最多 2 次
        ↓
需要修订且无安全阻断？→ 最多 1 次修订
        ↓
复评/格式修复最多 2 次 → 严格质量与发布门
        ↓
body-free 结果；候选仍未注册
```

阻断性注入或资源失败不会进入修订。真实执行入口还要求显式确认、干净提交、同一实现 SHA
的公共 CI、新鲜 G53-3-L 证据；本批没有走这些真实调用条件。

## 4. 验证与运行手册

预算脚本可离线重建冻结报告：`python scripts/build_glm53_bounded_revision_budget_reachability.py`。
V3 入口预检使用 `python scripts/run_glm53_hardened_domain_v3_gate.py --preflight-only`；修复实现已取得
exact-SHA 公共 CI，因此当前预检停在 `pending_protocol_evidence`，不得加载 Key 或构造 Provider。

初始实现 `730c32d074269fb45e5a5351b1af591ecaa35de1` 的公共运行 `33894351184` 暴露两处版本隔离遗漏：
旧输入计划未默认锁回零修订，V2 加固回执也被总检误分流。修复提交
`f99c142c269df765deb592c463ce6e2555bcc3fe` 让旧调用方继续默认 `max_revisions=0`，只有 V3 显式
使用 `expected_max_revisions=1`，并按 V2 专属 `protocol_id` 严格解析回执。

修复后的相关与相邻回归共 `93 passed`；`compileall`、`git diff --check` 和治理检查均通过。
Actions `33895602378` 三任务 exact-SHA 全绿：公共 pytest `2379 passed, 145 skipped, 2 warnings,
127 subtests passed`，PostgreSQL `201 passed, 2 warnings`，packaging-smoke 通过。该证据只证明实现
可公开复现，不是生产准入或领域质量证据；provider calls=0。

## 5. 失败、安全与边界

诊断只保留 attempt、score、verdict、通过项数量、问题类别和严重度计数，不保存正文、引用、
reasoning、Prompt、工具参数、请求 ID 或凭据。旧 V2 的 `4/12` 与 `24000/72000` 预算和回执
保持不变；GLM-5.2 兼容/应急路径、默认 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均未改。候选仍 `candidate-only/disabled`，领域质量、黄金切片、生产安全/
部署/合规和 8F 仍未完成。

## 6. 面试表达

> 我没有用更低门槛掩盖 V2 的事实核验失败，而是把产品原有的一次修订闭环做成候选专用 V3：
> 保留所有硬门，先用全请求包络证明 9/27 调用和 203000/608000 token 墙，再用 body-free 诊断
> 暴露可行动的枚举计数，同时把真实 Provider 继续挡在公共 CI 和新鲜协议证据之后。

## 7. RQ-235：V3 真实观察与检索归因（2026-09-05）

用户继续后已消费 RQ-234 新鲜协议，在代码 `110f9e8` 上执行一次 V3。首案实际 2 次模型调用、
6936 Token、29344ms；含既有协议累计 5 次/8052 Token。Agent 正常完成，两次 knowledge.search
成功，但共 0 个片段、来源数 0；最后检索诊断 insufficient_evidence，终态 rejected/evidence_required。
因此没有进入首评、修订或复评，后两案按首错停止跳过；admitted=false。

### 已证实的控制流

1. `provider_domain_production.py` 从 `data/rag_docs` 构造本地混合检索器；语料实测 4 文档、
   13 个父片段和 13 个子片段，不是空库。
2. `rag/hybrid.py` 使用 BM25 与默认 local-hashing 检索融合，再交给 `rag/policy.py`。
   insufficient_evidence 表示仍有适用候选，但没有候选同时满足 BM25 支持和查询覆盖条件。
3. 由于证据数为零，最低来源门先拒绝；题目要求至少 3 个归一化响应，而实际 2 个，产生派生码
   provider_response_unavailable。这不是 HTTP 无响应；后两案停止码映射也不能当成执行证据。

原始真实查询/过滤器和模型正文不保留，无法精确判断哪些词或哪一项支持数值导致拒绝。
独立开发查询、默认参数下，“复盘”返回 0，“复盘 事实 相关性 假设”返回 1，
“补刀 经济 发育 训练 目标”返回 2；这些零外部调用对照说明查询具体程度值得修复，
不是重放真实查询，也不是新的领域准入结果。

### 回执与验证

不可覆盖回执为
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_hardened_domain_v3_rq235_v1.json`，
7451 bytes，SHA-256=`2bf87351e38e4b6617604f4728d46047b710c7c11734630f4b364374ed545fcc`。
使用 `V3DomainGateResult.model_validate_json` 与 `canonical_v3_result_bytes` 可无网络复核，
不要再次运行已消费考卷。公开回执只含安全计数/枚举/身份，不保留运行时临时正文。

V3/执行器/预算相关 48 passed。新增真实回执暴露公共结果总检未识别 V3 protocol_id，误用旧
结果模型；只为其增加 V3 严格模型分流和 canonical 比对，修复后总检相邻 22 passed。
该修复不改运行器、模型、查询、阈值、结果结论或历史回执。

下一批只做独立开发用例下的查询/检索/零命中合同与安全诊断加固，先冻结方案，再以聚焦测试
实现；不重跑 V3，不通过伪造引用或降低质量/安全要求取得绿灯，不自动注册候选。

## 8. RQ-236：候选检索合同离线加固

### 问题与原则

RQ-235 的真实 V3 首案调用检索成功但零片段，安全门因此在评分前停止；真实查询正文没有保存，
不能倒推出具体词句。RQ-236 不重跑旧考卷，而是在独立开发语料上验证并修复“过短的单一教练意图”
与本地检索支持之间的接缝。原则是原查询优先、最多一次受控补查、阈值不变、无证据仍拒绝。

### 实现与数据流

- `app/rag/coaching_query.py` 的 `CoachingQueryKnowledgeProvider` 先调用原 KnowledgeProvider；
  只有零命中、`insufficient_evidence` 且能唯一识别安全教练主题时，才追加固定概念词再查一次。
- 补查沿用原 `top_k` 和全部过滤条件，不读取案例答案、账号数据或任意用户文本生成查询；未知、混合、
  注入式、冲突、无适用资料和异常输入不补查。
- `ProductionDomainCaseExecutor` 通过默认关闭的 `retrieval_hardening` 显式装配该包装器；它只能
  与候选 request policy 和 `quality_hardening=True` 同时存在。V2 在 Provider 调用前拒绝该开关，
  V3 候选入口显式开启。
- `EvidenceDiagnostics` 只公开主题、尝试/计数、过滤键名和原因枚举，并分开记录模型工具调用和
  本地补查；历史空字段继续省略，避免改变旧回执。

### 验证、边界与后续

查询恢复、执行器、V2/V3 隔离及完整 Agent→检索→Evidence→评测→发布链路共 `51 passed`；
compileall、`git diff --check` 和治理检查通过，provider calls=0。BM25 `15.0`、查询覆盖率
`0.18`、来源门、事实/引用/注入门与 85 分质量门均未放宽。查询指南常量暂不写入已冻结的 V3
Context snapshot；若要让模型上下文主动生成更具体查询，必须另立 Context/资产版本并重新准入。
候选仍未注册，GLM-5.2 仅为显式兼容/应急路径，默认 Runtime、Portal、Account、Workbench、Auth、
路由和 `production_media=0` 不变；实现提交 `ed62dbbc80506a8bcfae7eefb132348b21e587e0` 的
Actions `33943854904` 三任务 exact-SHA 全部成功。不能据此重跑 RQ-235 或宣称领域/生产准入；
下一步只裁决是否另立新鲜协议/资产。

### 面试表达

> 我把真实检索零命中归因为“查询支持合同不足”，没有靠降低 BM25 或来源门追绿；候选包装器保留
> 原查询和过滤条件，只对已登记的单一教练意图做一次安全补查，并用 body-free 计数区分本地检索
> 与模型工具调用。旧 V2/V3 身份和产品 Runtime 仍通过显式版本边界隔离。
