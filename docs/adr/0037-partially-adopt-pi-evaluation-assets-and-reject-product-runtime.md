# ADR-0037：只保留 Pi 评测资产，拒绝其成为产品 Runtime

- 状态：Accepted
- 日期：2026-08-17
- 范围：`5F-5-adoption-decision-exit-review`
- 最终裁决：`partial-adopt-evaluation-assets-only`

## 背景

RiftCoach 在进入 5F 前已经拥有 Python `AgentRuntimeV1`、受限 AgentLoop、ToolRuntime、
ReviewHarness、Trace/Usage、Prompt Program 和本地 FastAPI 产品切片。5F 不是为了给项目增加一个
SDK 名词，而是要验证官方 Pi Agent Core 能否安全承接其中一部分 Runtime 职责，并减少总维护面。

5F-1 至 5F-3 已得到以下可复现证据：

- 官方 Pi 0.84.2 / MIT / Node 合同可审计，允许进入隔离实验；
- exact lockfile、JSONL sidecar、Python controller、Scripted StreamFn 和真实本地
  `knowledge.search` 可以形成受限 loop；
- Tool 白名单、整批预检、重复、迭代/调用预算、deadline、Usage、坏引用、Tool/进程失败、
  ReviewHarness 唯一发布权、typed output 和成功 Trace 可以由 adapter 保持或安全拒绝；
- 现有 token-unit Context ceiling 与 sidecar JSON 字符门不等价；Pi 扩展失败终态不能无损映射到
  当前 Runtime Agent terminal；sidecar 结束后批量投影的事件没有真实 live timing/stream 语义；
- 安装树为 94 个 npm 包、11,355 个文件、约 62 MB，本机每 run 新进程约 0.4 秒量级；
- 5F-4 因上述强制 Runtime 门失败而未进入，真实模型质量保持 unknown。

这意味着 Pi 可以作为隔离评测对象运行，但没有证明它能以更低的总成本替换产品 Runtime。

## 决策

### 1. 产品 Runtime：拒绝采用 Pi

Python `AgentRuntimeV1` 继续是 RiftCoach 唯一产品 Runtime。Pi 不进入：

- FastAPI 或 `RecentReviewApplicationService`；
- default/secure composition root；
- 产品依赖、部署镜像或运行时选择配置；
- Session、Memory、SSE、SQL、阶段 6 或后续产品控制流。

不存在“Python/Pi 双 Runtime 自动路由”，用户也不能选择 Pi。阶段 6 继续在现有 Python Runtime 上
增加持久任务、Session 与 Memory；5F 的负面结果不阻塞该主线。

### 2. 可执行实验资产：仅作为冻结评测证据局部保留

保留以下 evaluation-only 资产：

- `experiments/pi_runtime/` 中的 exact package/lockfile、sidecar 和官方包身份；
- `app/evaluation/pi_runtime/` 中的严格协议、controller、Harness adapter 和 Signal projector；
- 对应 Pi protocol/sidecar/parity/Harness/Trace 测试；
- 5F ADR、设计、审计、退出矩阵和 Git 历史；
- 当前 GitHub Actions 中的 Node 24、`npm ci --ignore-scripts` 与回归复现能力。

“保留”不表示继续为新产品功能扩展 adapter。该资产进入冻结维护：

1. 不随阶段 6 的业务功能同步扩展；
2. 不自动升级 Pi、Node major 或传递依赖；
3. 只有安全修复、可复现性修复或明确重新采用实验才能改动；
4. 任何重新采用实验必须有新 Bad Case、备选方案、预期收益、预算、评测和新 ADR；
5. 如果高危依赖影响实际导入路径、Node 不再兼容、CI 持续不稳定/成本显著，或实验因产品合同演进
   需要大规模追随维护，优先归档可执行资产，只保留文档与 Git 历史；不得扩展产品合同迁就 Pi。

当前继续在默认 CI 复现，是因为约数秒的隔离安装与有限本地进程开销仍小于公开、持续证明负面实验的
价值。94 个包是开发/研究供应链面，不是生产依赖；`node_modules` 不跟踪，依赖精确锁定，lifecycle
scripts 被禁用。这个决定可由上述归档触发条件重新审查。

### 3. 设计思想：吸收方法，不复制第二套 Runtime

以下方法成为 RiftCoach 的长期工程经验：

- 第三方 Runtime 先经过版本/许可证/合同审计，再做隔离 spike；
- 跨语言协议必须版本化、限长、严格解析并 fail closed；
- 可兼容成功路径不等于完整失败/时序 parity；
- 强制安全/合同门不能被平均分、demo 或框架知名度抵消；
- 真实调用对结构性差异没有信息增益时，应在调用前停止；
- 负面实验要保存可复现证据，并与产品依赖、模型质量和部署成熟度分开表述。

不把 Pi 的 Agent API、事件模型、Session、Provider 抽象或 Coding Agent tools 迁入产品代码。

## 非功能要求与风险

### 安全

- Pi 测试继续使用 allowlisted child environment、限长 JSONL、body-free public result/Trace、
  Python ToolRuntime 和父进程 deadline/terminate/kill；
- 不给 CI 或 sidecar 注入 `.env`、Provider Key 或 Riot Key；
- Node Permission Model 只作为 defense-in-depth，不宣称 OS 网络沙箱；
- 未来安全告警必须判断是否影响实际冻结导入路径，不能因“实验代码”而忽略。

### 性能与成本

- 约 0.4 秒 Windows 新进程测量不是生产 SLO；因为 Pi 不进入产品，不再为它设计生产 p50/p95；
- CI 继续承担 Node setup/npm install/聚焦进程测试成本，但生产部署不承担；
- 若 CI 成本成为明确 Bad Case，按归档触发条件处理，而不是先构建进程池或常驻 sidecar。

### 可靠性与维护

- frozen 不等于“永远不用维护”；它表示只维护安全和复现，不承诺功能追随；
- Pi-only 回归失败时，先判断实验漂移还是产品回归；不得为了让实验变绿而放宽产品合同；
- 当前 exact 0.84.2 证据不能外推到未来 Pi 版本。

## 备选方案

### 完整采用 Pi

拒绝。Context、extended terminal 和 live timing 三项强制门失败，且修复需要复制已有 Runtime 职责；
维护收益没有成立。

### 删除所有 Pi 可执行资产，只留 ADR/Git 历史

当前不选。这样会降低负面实验的可复现性和教学/作品集证据强度；现有隔离 CI 成本仍可控。若触发
安全、兼容、稳定性或显著成本条件，再以新 ADR 归档。

### 保留代码但移出默认 CI

当前不选。没有持续回归时，实验很容易在主 Runtime 合同演进后悄然失效，留下只能阅读不能运行的
资产。默认 CI 失败也不得反向要求产品迁就实验；可以通过未来 ADR 改为手动/归档工作流。

### 继续修 sidecar 直到通过 5F-4

拒绝。重写 Context sizer、扩展终态和在线 event bridge 会先承担迁移成本，再讨论采用，违反既定
技术采用门；真实模型调用不能回答这些结构性问题。

## 后果

### 正面

- 产品保持单一 Python Runtime、单一 Harness 和单一部署语言主线；
- 负面实验可公开复现，能解释“为什么不采用”，而不是主观声称自建更好；
- 阶段 6 不被外部 SDK 迁移阻塞；
- 未来遇到其他框架时已有可复用的采用门方法。

### 负面

- 仓库和 CI 继续承担一套冻结 Node/npm 研究资产；
- 94 个包构成额外开发供应链面；
- `partial-adopt` 容易被误读，必须始终加上 `evaluation-assets-only` 和产品拒绝说明。

### 中性

- 5F-4 没有执行，这是设计中的条件分支，不是遗漏；
- 真实模型质量、Pi 生产性能和未来版本能力继续 unknown，因为它们与当前拒绝原因无关。

## 重新开启条件

只有以下条件之一出现，才允许新 ADR 重新评估 Pi 或其他 Runtime：

1. Python Runtime 出现多个可复现、无法用现有小改动解决的维护/可靠性 Bad Case；
2. 候选提供可验证的 Context/terminal/live event parity，并能减少而非复制维护面；
3. 同一产品切片的质量、延迟、成本、失败恢复和部署对照有明确预期收益；
4. 实验资源、调用上限、停止规则和回滚路径在任何真实 I/O 前冻结。

框架发布新版本、流行度上升或简历价值本身都不是重新开启条件。

## 参考

- ADR-0034、ADR-0035、ADR-0036
- `docs/plans/2026-08-17-5f-pi-only-agent-runtime-adoption-design.md`
- `docs/plans/2026-08-17-5f1-pi-source-license-contract-audit.md`
- `docs/plans/2026-08-17-5f2-offline-protocol-adapter-spike-exit-review.md`
- `docs/plans/2026-08-17-5f3-contract-security-harness-exit-review.md`
- `docs/plans/2026-08-17-5f5-pi-adoption-decision-exit-review-plan.md`
- `docs/plans/2026-08-17-5f-pi-adoption-exit-matrix.md`
- `docs/plans/2026-08-17-5f-pi-adoption-exit-review.md`
