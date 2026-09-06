# RQ-243：候选生成／修订报告合同对齐

目标：只在显式的新开发候选版本中，使初稿与修订共用既有报告结构要求；不改产品默认或旧考卷。
方案：复用现有 Python、Context 身份校验及 Harness，增加一个具名报告合同，无新依赖。

## 决定与边界

旧生成结构检查允许非空 Markdown，修订却要求固定八个标题；修订提示又只要求保留原标题。
离线已复现该不对称，但 RQ-242 真实经济失败的具体原因仍未知。本批不推断或回填旧失败。
采用明确提示 + 同一验证规则，不自动改写模型正文，不删除标题/70% 长度要求，也不靠新增重试解决。
固定标题仅组织报告，不强迫捏造事实；无对应数据时明确说明未知或样本不足。

## 实施与验证

1. `app/report_validation.py` 提取既有八标题常量；`coach_report.py` 原验证器消费它，旧行为不变。
   新增 `app/evaluation/glm53_report_contract.py`：版本化合同、摘要、生成指引和修订 prompt builder。
   核心接线为 `validate_revised_report(draft.report, draft.report)` 与
   `build_revision_prompt(report, evaluation) + "\n\n" + REPORT_POLICY`，两端使用同一标题表。
2. `glm53_guided_candidate.py` 与 `provider_domain_production.py` 增加默认关闭的显式报告合同参数。
   新合同只准入新的 development plan/case/run/snapshot 命名空间，Context 重建含合同后再核对摘要；
   旧 V4 等入口默认无新合同，给旧计划强塞合同必须在 Provider 调用前拒绝。
   初稿先经过既有安全处理再做同等结构检查；修订继续使用原验证器，事实/引用/注入/85 分及一次修订不变。
3. 开发探针增加显式选择，新计划版本 2.0.0、全新开发身份、回执记录合同 ID/SHA；默认旧身份保持。
   `tests/test_glm53_report_contract.py`：提示/快照一致、旧计划拒绝、三代表场景初稿→修订→重评、
   不合格初稿提前拒绝、缺标题/过短/未知引用仍拒绝，且所有测试断网。重跑相邻预算/旧资产/旧回执回归。
4. 运行聚焦测试、compileall、diff check、governance 并取得实现公共 CI。此批真实 Provider 调用为 0。
   开发请求仍受 9 次/205000 tokens/一次修订约束；新上下文的完整最坏路径预算与独立正式资产后续冻结，
   不声称沿用旧预算证明就已证明新合同的所有真实路径可达。

## 产品迁移清单（不在本批接线）

后续 low/4096 产品档案必须统一 Provider、RuntimePolicy、Trace、Skill/Prompt Program 身份、
检索指引、来源门、工具重试/回退、Worker lease 与总预算；旧 Flash v1 和 GLM-5.2 兼容记录保留。
版本号与数值通过实际候选实现及预算复核后再接受，不能仅改默认模型字符串。
生成/修订合同先完成离线及公共验证，再冻结新合同的完整预算/迁移版本；本批不发新的真实请求、
不启动流式 8192/recovery 实验、不改前端或任何已消费领域资产，production_media=0、8E in_progress 不变。

## 本地结果与学习说明

已实现：合同 `coach-markdown-generation-revision-v1` 从同一八标题常量生成指引；初稿安全处理后
复用旧结构验证器，修订请求携带同一指引且沿用旧长度/引用规则。新入口限定匿名两局 demo，
计划 2.0.0 与 case/run/snapshot 身份独立；默认旧开发计划仍重建出旧真实回执的原摘要。

验证：新合同 13 项，连同相邻回归共 144 项（两组分别 75/80，重复的 11 项仅计一次），
另 16 subtests 全部通过；三代表场景的 70→95 分为脚本输入，只证明修订控制流，不是模型质量分数。
Context 是 JSON 分区消息，测试解析真实请求的 internal_policy 后确认指引，不能拿未转义多行文本直接搜 JSON。
旧正式资产预算重建、旧回执总检、Prompt Program 指纹、Harness、检索和候选资源墙回归通过。

数据/控制流：新具名合同→重建/核对 Context→Agent 检索与初稿→既有安全处理＋同等结构验证→
独立评测→最多一次修订（携带同一合同）→重评→原质量门。身份或结构错误均有可检查的拒绝，不额外发重试。
复现：`python -m pytest tests/test_glm53_report_contract.py -q`，无需 Key、网络或服务器。
代码地图见上方实施清单；开发回执追加合同 ID/SHA，原始报告不会进入公开回执。
可准确表述为“修复了候选生成与修订的格式合同不对称，保持可追溯验证”，不能说已修好 RQ-242 的真实经济失败。
当前只完成本地，下一步本实现公共 CI；之后是新合同完整预算证明与产品迁移版本对齐，不直接重复真实经济场景。
