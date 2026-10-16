# 自然互补审查：已确认的六次候选接线

2026-10-14。用户对具体“5改6，其他预算和模型保持，先零付费设计接线”回复“确认”。
实施目录 `D:/riftcoach-natural-duty-six`，分支 `codex/natural-duty-six`，基于 `1e0e48af`。
原后端 `D:/riftcoach-agent-rq192-pr` 保留冻结源码和封存回放；主树前端不动。
决策见 ADR0118。当前 8E checkpoint 不变。

## 解决的问题与设计

Agent 先调用模型选择知识工具，工具在本机执行，再调用模型读取结果成稿。这两次都是
同一个任务账本中的生成请求。双初审直接通过共4次；如果需要补丁和双fresh，最少6次。
候选把调用上限显式改为6，保留401920总tokens、900秒整任务、实际单请求300秒、
64000输入/32768输出、零重试及现有high模型分工。没有额外Flash编辑请求。

预算检查发生在真实发送前：已用和未知预留都占tokens；剩余时间裁切下一请求timeout。
双初审需要修订而不足两个调用slot时，在应用前停止。追加工具轮次仍可能失败，不承诺
任意自然任务都能在6次内完成。内部既有调度330/transport360配置不覆盖实际300秒发送门。

实际路径：RecentReview输入编译 → Runtime/唯一共享预算 → AgentLoop选工具 → 本地RAG
→ 成稿 → facts/completion完整初审 → 严格补丁预览 → 唯一应用 → 同一新稿双fresh
→ candidate journal与Trace/receipt。DispatchAwareRuntime在下一真实发送前检查取消。

## 代码位置与身份

| 文件 | 职责 |
|---|---|
| app/evaluation/natural_duty_contract.py | 独立1.6.0合同、请求time300身份、角色路由和源码指纹 |
| app/evaluation/natural_duty_workflow.py | 初审/预览/唯一应用/fresh状态机、原件绑定与内部结果 |
| app/product/natural_duty_candidate.py | 显式依赖注入的真实应用组装；不读取Key或注册默认入口 |
| examples/runtime_profiles/natural_duty_v1 | Skill0.7.0和Program4.0.0独立资产 |
| scripts/refresh_natural_duty_manifest.py | 审阅源码改动后显式刷新新候选指纹 |
| tests/test_natural_duty_candidate.py | 阻断socket的实际Runtime/本地工具/预算/Trace集成验证 |

共享合同白名单、request policy、Program resolver和混合模型Trace加入精确新身份；旧合同
仍为5次。新候选不接受开发time600请求、旧transport标签或伪造snapshot。每次审查核对
prepared与实际issued（仅允许预算字段和timeout裁切）、response身份及原回执SHA。

每个run的 natural-duty-journal 以create-only方式保存完整公开意见、实际预览、应用与结果，
不保存private reasoning。终态不能重开；同一结果文件不覆盖。日志失败不掩盖原执行异常。
这些业务原件不是脱敏监控日志，后续接API前仍需按既有owner与保存期限合同处理。

## 发布语义与未证项

程序确认block_N、唯一锚点、无重叠及逐字应用，复用已有补丁校验；完全相同的重叠也拒绝。
它不能自动证明意见正确、无语义冲突、四项ReportAssessment或正确内容的语义保留。
没有伪造Host意见，也没有把开发人工Host放进生产免费步骤。

因此，即使候选双初审或双fresh都pass，Harness也收到FAIL，receipt报告不可用；内部journal
分别记录 candidate_initial_pass_unqualified / candidate_repaired_pass_unqualified。
该FAIL表示候选不允许发布，不等同于已经判定报告语义错误。测试中故意对已知错误原稿
返回pass，仍只能得到内部未认证结果。没有默认Worker/API入口、可用付费transport或生产准入。

这次交付完成的是工程候选接线。自动语义策略仍需以完整原15、正确稿、错误修法和冲突例
评估；两fresh的模型同意不替代独立质量标准，也不证明自然生成/工具组合的真实成功率。
正式同版本15、自然Coach/Training、四块联动/journal、前端头像审美、Memory、身份运维、
两树整合、独立评估与学习继续保留。Owner理解未验收，8E未完成。

## 验证与运行方法

在新worktree，使用 `D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`：

```powershell
python -m scripts.refresh_natural_duty_manifest
python -m pytest tests/test_natural_duty_candidate.py tests/test_role_coach_application.py tests/test_role_budget_failures.py tests/test_role_runtime_trace.py tests/test_prompt_program.py tests/test_review_duty_direct_patch.py -q --tb=short --show-capture=no
python scripts/check_project_governance.py
git diff --check
```

模型响应是手写替身，真实运行AgentLoop、ToolRuntime、本地RAG、共享预算和Trace落盘；
不联网、不产生模型费用。覆盖4/6调用、额外检索、坏锚点/fresh拒绝、结构合法但语义错误的补丁仍拒发布、transport/receipt/model
故障、1/4/5次后取消、第7次拒发、900秒/剩50秒/tokens/未知预留、旧身份隔离、指纹漂移、
终态重入、revision来源和原稿篡改、实际fresh稿被替换、伪造Trace。旧补丁测试覆盖重复和重叠。
结果记录见 `data/evaluation/results/natural_duty_six_offline_20261014.json`。

原目录854源码配置、3包、103原件与seal已只读复核；新工作树共享源码及四个受影响旧runtime
manifest有新SHA，这不替旧封存重新签名。canonical历史尾段保持原字节。automation保持PAUSED。

## 下一动作

在新分支继续零付费整理自动语义裁决的反例与同版本资格设计，明确错误意见、坏修法、语义
冲突、双审漏判如何被实际拒绝。保持发布门关闭；先用既有原例决定方案，避免按每个字段
补丁后另购一批。新付费验证另列可审查输入、完整停止条件和成本，不挪用任何旧授权。

## 2026-10-15 离线语义边界

新增 `docs/plans/2026-10-15-natural-duty-semantic-qualification.md`，把错数字、错范围、错因果、
空来源、错目标段、补丁删除知识引用和未认证的 `conflict_status='clear'` 固定为结构边界反例。
空来源/无引用不自动判语义失败，跨段可修真实直接影响；具体缺口须按完整任务/来源判断。
新增三项预览见证及三项真实应用对象整链见证，连同已有错数字用例，共同验证六次替身调用、
双fresh pass仍拒发布、原样意见/实际新稿/Trace/receipt绑定。职责/补丁/候选84项和清单4项通过。
新清单核真实Program资产并构造原15的30个完整time300初审请求，原标签仅留评估端；fresh SHA
待实际改稿后再计算。结果natural_duty_qualification_inventory_20261015.json不授资格，不是执行准备。

下一步按六项开发Host义务的缺口选择可检验的自动策略，再确定最小必要开发验证；不直接重买15。
可独立零付费工程继续，生产准入与未授权付费保持关闭。

## 2026-10-15 公共CI恢复

8d06f442的CI38590893161：web、packaging和postgres通过，四pytest分片均在历史remaining4
快照setup提前停止。124项本机结果保持，但没有公共全库通过。历史test-only archive缺少本次
变更的model_runtime、coach_contract、reviewer_roles旧源码，materialize回退读取当前文件。
补齐固定51923f4b提交的3份原LF文本，分别匹配remaining4和remaining8既有摘要；原归档条目、
摘要清单、生产prior拒绝逻辑及原封存均不改。检查记录见natural_duty_ci_recovery_20261015.json。

同一公共回归随后暴露旧 timing 快照还引用 `app/runtime/coach_contract.py` 的历史指纹；该共享文件
在候选中新增1.6.0合同入口，不能用当前文件重算旧裁决。已从固定提交51923f4b提取原LF字节，
加入 timing 源码归档并纳入 `FROZEN_SOURCES`；旧 timing JSON、seal、原件与生产拒绝逻辑均未改。
本机候选加历史回归140项、治理检查和 timing 审计通过；b79d2c83对应公共CI38601405819全绿。
该CI证据只属于b79d2c83，后继语义边界工作提交另核。
