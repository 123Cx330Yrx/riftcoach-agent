# GLM-5.3 Flash 加固领域 V3 有界修订设计

## 1. 目标

RQ-230 的 V2 首案不是 Provider 或工具失败，而是首稿事实核验失败、评分 80 未达到 85，且零修订预算
立即耗尽。V3 要验证的是：保持全部质量与安全门不变时，产品原本已有的“评测后最多修订一次”是否能
让候选完成领域发布闭环；同时让失败在不保存正文的前提下可分类。

## 2. 已选方案

采用 ADR-0094 的“最多一次修订 + 安全诊断投影”。不采用继续零修订的纯诊断方案，也不通过降低
85 分门槛、弱化事实/引用/注入/来源要求或临时提高思考档来追求通过。

V3 仍是 candidate-only 评测，不是产品默认模型切换。RQ-227 和 RQ-230 的考卷与回执保持不可变；
V3 使用全新协议、问题、数据、Context 和结果身份。

## 3. 组件与职责

### 3.1 生产领域执行器的显式修订参数

`ProductionDomainCaseExecutor` 增加显式、默认仍为 0 的 `max_revisions` 参数。所有旧调用不传参数时
字节与行为保持不变；V3 专用入口必须传入 1。参数只能落到 `SkillReviewExecutor`，不得在运行器外
模拟第二次回答或绕过 Harness 状态机。

### 3.2 安全评测诊断

为每次实际落盘且通过 `EvaluationResponseModelV11` 校验的评测生成公开投影：

- `attempt_id`、`score`、`verdict`、`passed_check_count`；
- `issue_category_counts`：只允许评测 Schema 中的固定类别；
- `severity_counts`：只允许 `high/medium/low`；
- 整个案例的 `revision_count` 和 `revision_attempted`。

投影从 Harness 工件读取并重新做严格 Schema 校验。任何未知类别、计数不一致、轮次重复或私有字段
进入公开模型都 fail closed。V3 不保存或哈希正文，也不把自由文本换个字段带出去。

### 3.3 版本化资源墙

调用上界是控制流可证明的 9 次/案、27 次/域：AgentLoop 4 次 + 首评/格式修复 2 次 + 修订 1 次 +
复评/格式修复 2 次。该上界允许正常的一次工具往返与一次修订，也覆盖评测格式修复，但不引入 SDK
retry 或 recovery。

Token 上界在实现阶段通过离线包络报告确定：对全新冻结 Context、Agent 各轮、首评、格式修复、修订
和复评分别计算输入估算，并为每个允许调用预留最多 4096 输出；按案例求和后冻结有限上限和三案例
总上限。准入器必须核对报告 SHA、协议数值和运行时预算对象完全一致。设计阶段不伪造一个未经证明的
Token 数字。

### 3.4 全新 V3 资产与证据链

V3 创建新的三案例 Dataset、V1.1 Input Plan、Prompt/Context Snapshot 和匿名合成 fixture，禁止复用
RQ-227/RQ-230 的问题、case/run ID、数据或 marker。真实运行前按顺序取得：离线测试与 no-I/O 准入、
实现 SHA 的公共 CI、新鲜 G53-3-L 脱敏证据、另行授权的 V3 真实观察。任何一步不能由前一步自动授权。

## 4. 数据与控制流

```text
V3 assets ─┐
budget proof ├─> no-I/O admission ─> exact-SHA CI ─> fresh G53-3-L
policy v1 ──┘                                      ↓
                       initial draft → evaluation attempt 0
                            │ pass/fail        │ needs_revision
                            ↓                  ↓
                         terminal      one revision → evaluation attempt 1
                                                    ↓
                                             strict terminal decision
                                                    ↓
                         body-free result + enum/count diagnostics
```

阻断性安全问题仍立即停止，不能进入修订；资源墙在每次 Provider I/O 前预留；缺失或非法 Usage、未知
评测 Schema、预算耗尽和身份漂移均失败关闭。

## 5. 验证策略

离线测试必须覆盖：默认零修订兼容、V3 一次修订后通过、一次修订后仍拒绝、阻断性安全问题不修订、
首评或复评格式修复的调用计数、9/27 调用墙、Token 包络可达与越界停止、诊断计数正确、所有自由文本
字段无法进入回执，以及旧 V2 schema/序列化/结果身份保持不变。

比例回归至少覆盖 Provider domain production、Harness runtime/adapters、低思考预算、V2 runner、
Prompt/Context identity 和 body-free 扫描。随后运行 compileall、`git diff --check` 与治理检查。

## 6. 当前完成与下一步

本批只完成设计与详细实施计划，provider calls=0。下一精确检查点是 V3 离线实现：先写失败测试、
完成版本化预算证明和安全诊断，再创建全新资产并做 no-I/O 准入；不得直接调用真实模型。
