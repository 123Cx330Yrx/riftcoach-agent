# 真实黄金切片实施与恢复计划（RQ-258）

**Goal:** 从真实比赛、静态定义、官方版本与 OP.GG，贯通同源 Evidence、合格 Coach/训练报告、持久化及 live Workbench 消费。

**Architecture:** 复用 Summary Builder、Coach 1.2.0、Evidence 桥和 ADR-0099 A/B/C，不切生产默认。外部获取与产品执行分离；冻结可重放数据后先离线检验，再进行有身份与计数的真实观察。

**Tech Stack:** Python、现有 Riot/HTTP/MCP clients、Pydantic、PostgreSQL、现有 Workbench。

## 当前事实与纠正

### 2026-09-10 位置语义与接入修复（本地，尚未完成黄金切片）

- 用户补充：玩家可主玩一个位置、偶尔玩其他位置，也可主动转位置；不能把异位置局直接判为补位。单局实际位置、长期位置分布、显式训练目标必须分开。目标支持多个位置，显式当前意愿优先于历史倾向，但不能覆盖历史比赛事实。
- 本次先实现黄金切片的接入层：按已纳入分析的每局实际分路分组，每个分路一次 OP.GG 工具查询；完整解析有大小上限的响应后选择目标英雄，不再先截前十条。旧榜单消费者默认仍保留前十条，未改变其合同。
- 分位置统计本次场次与补刀/经济/早期死亡/视野均值，并保留每项有效样本数；缺失不当零。显式 `--training-position` 可重复指定；未明确目标时保持 unspecified，不把五局当长期画像，不宣称识别出补位意图。
- 缺失诊断区分 request_failed、invalid_response、target_not_in_response；最后一项仅指当前响应未对上目标（含潜在命名差异），不等于 OP.GG 全站无数据。不得改用其他位置或无关热门英雄填充缺口。
- 尚待接线：长期历史窗口/偏好 Memory、通过对话确认或更新目标、正式产品请求与 UI 目标编辑。本次只有候选入口可显式传入目标；不能说完整交互已实现。目标位置无样本时只提示缺口，不用旧位置成绩评价新位置。
- 移除了随意截短查询、知识正文及命中数的 `_CappedKnowledge`，恢复完整本地检索器。候选专用 JSON 事实块压缩保留所有值、可信策略、Markdown、外层 canonical 包装和 16000 上限。保存的 v14 五局离线测量为 12286→10576，节省1710，无省略；这不证明多轮预算已足够，新增位置事实还需计入。
- 完整 Training 持久化/live UI 尚未验证，所以入口一律保留 degraded，不能凭 DTO 和报告 digest 标 passed。真实模型报告、静态版本对齐及官方来源 provenance 仍待修复验证。早期草稿之后已有 b0d469f/b910556/31a9806 三个本地提交，下方“尚未提交”为早期历史，不是这三个提交不存在。

### 本次验证与后续顺序

本地测试覆盖目标在第12条、部分/零命中、请求失败/错误位置、跨位置一次查询、目标转位置不重标历史、辅助不套补刀目标、指标缺失与大小写去重、候选应用模拟发布及 JSON 事实等价。已有聚焦与相邻164项通过；最终数量以本次progress记录为准。未新增真实外部调用。

下一步在同一黄金切片内完成：真实形状上下文+完整检索的离线多轮预算验证，定位报告准备失败；修复历史静态版本与官方来源身份；通过公共验证后做有界真实消费，最后验收 Training 持久化和 live Workbench。不重开 A/B/C，不切生产默认。

八维补充：问题/原则是位置事实与意愿分离；实现地图为 `coach_positions.py`、`opgg.py`、黄金切片入口和 `coach_context.py`；流程为实际对局→分位置样本/目标分离→定向资料→同源报告；验证见位置/适配器/上下文测试；运行入口支持重复 `--training-position`；缺口与安全保持未知不推断；可表述为“候选接入层支持混合位置与明确训练目标”，不能表述成“已实现长期画像和对话目标管理”。

### 早期草稿历史

- A/B/C 的公共闭环仍是 `80ed693` / Actions `34324718617`。当前新增代码尚未提交，不属于该 SHA 的公共验证。
- 当前新入口是未验收草稿。旧 v1/v2/v4/v8/v10 回执无条件写 `passed`，只表明函数返回，不能用于黄金切片通过裁决；保留原文件，撤销其通过含义。
- v10 包含 5 局 Riot、Data Dragon、官方版本 feed 的摘要和 OP.GG。比赛 16.17 与静态 16.18 不一致，且部分英雄/位置不能 join；缺口不应抹平。
- 官方 patch 草稿错误地把抓取时刻当发布时间，版本 feed 未核对目标版本即赋值；必须修复 provenance，不能声称取得官方 patch notes。
- Coach v8 的 Agent 因 `context_budget_exceeded` 停止；v10 为 3 次 Provider 请求、Agent final_response，但 Harness `rejected/draft_preparation_failed`。`_CappedKnowledge` 对 dataclass 使用 `model_copy` 是本轮引入的错误，不能归因模型质量。
- 草稿只校验 UI DTO，未做 live UI 消费、训练持久写入或 A/B/C 联调；完整黄金切片仍未完成。
- 真实获取发生于未提交代码，且前几次未预约/计数，不能用 HEAD=`26a65ed` 冒充执行代码身份或声称准确总调用数。停止盲重试，修好离线入口再继续。

## 执行顺序与完成判据

1. 修复入口真实性与资源边界：只读预检，输出/运行身份在网络前预约，持久失败/调用计数，严格来源/结果校验，默认关闭外部 I/O；测试无来源、模型拒绝、重复运行、错误路径时都不能标通过。
2. 保存私有真实 Summary/typed 来源快照供重放；公开只保留摘要与允许字段。读取旧合法工件而非反复获取同一玩家，不能把公开 DTO 校验说成 UI 已运行。
3. 先复用现有完整检索器修复错误；定位上下文超限，以显式事实投影/既有预算合同处理，不能截断知识正文却沿用原摘要或默认降低质量门。
4. 离线用真实形状 Summary + fake Provider 走实际 Coach、报告/引用/评分、同源清单、A/B/C；补齐 4 类来源在建议中的实际消费者。公开 CI 及新鲜协议门满足后再做一次有界真实观察。
5. 将同一产物通过现有 API/Workbench 呈现，验证 Evidence/Trace/Training 可追溯；只在报告质量、四来源 provenance、持久化、UI 全部可复核时认定 golden slice 完成。

## 验证

聚焦：`python -m pytest tests/test_coach_real_data_golden_slice.py tests/test_evidence_fusion_vertical.py tests/test_coach_application_composition.py`。
随后根据实现范围运行 PostgreSQL/前端测试、编译、diff 与 `scripts/check_project_governance.py`。旧 24 项测试仅覆盖预检与 adapter，不能证明执行器安全或完整。

## 八维学习与边界

问题/原理：会回答合成样本不等于真实产品闭环，外部来源、模型、存储和界面必须由同一份事实连接。
设计/实现：复用现有能力，不另造 Runtime；入口负责冻结来源和计数。
代码地图：`app/evaluation/coach_real_data_golden_slice.py`、`scripts/run_coach_real_data_golden_slice.py`、`app/evidence/summary_bridge.py`、`app/product/coach_composition.py`、ADR-0099。
数据/控制流：请求→有界获取→冻结 Summary/来源→Coach/训练→同源发布→事务→API→Workbench。
验证：上述逐层退出条件，开发观察/公共 CI/生产准入分开。
Runbook：默认预检，失败留痕，修好本地证据后才新增运行身份，不重写失败回执。
失败/安全/边界：缺源/未知发布时间/过期/跨版本诚实降级；无报告或无 UI 消费不算完成；不重置 Docker、不删除卷、不切生产默认。
面试表述：当前可说“已打通并公开验证同源事务与恢复，正在补真实黄金切片”；不能说“真实黄金切片和 8E 已完成”。
