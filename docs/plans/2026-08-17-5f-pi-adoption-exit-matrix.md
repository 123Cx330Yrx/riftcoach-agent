# 5F Pi Runtime 采用与退出矩阵

## 1. 裁决摘要

```text
产品 Runtime：reject Pi
评测资产：partial-adopt as frozen evaluation evidence only
设计方法：adopt selected engineering lessons
5F-4：not entered because hard Runtime gate failed
```

本矩阵把“产品是否使用”“仓库是否保留实验”和“是否学习设计方法”分开，避免把
`partial-adopt` 误写成线上双 Runtime。

## 2. 功能与合同矩阵

| 维度 | Python 产品基线 | Pi 实验证据 | 裁决 | 依据 |
|---|---|---|---|---|
| 产品入口 | FastAPI → Application → composition | 未接入且禁止接入 | 保持 Python | ADR-0033/0037 |
| Skill/Prompt identity | Catalog、Compiler、Program drift gate | 复用 Compiler 后映射 | 可作为实验输入 | 5F-3 adapter tests |
| Tool 白名单 | Manifest + Python ToolRuntime | exact pass | 保留测试证据 | unauthorized/schema/batch tests |
| batch/duplicate | 整批 I/O 前预检 | exact pass | 保留测试证据 | 5F-2 parity |
| 迭代/调用预算 | Python AgentLoop | exact pass | 保留测试证据 | last-iteration/failure-count tests |
| 总 deadline | 协作式 Python deadline | adapter-covered + child kill | 仅实验可接受 | Tool handler 仍须合作 |
| Context ceiling | deterministic token-unit | 编译前 token-unit + sidecar char guard，两者不等价 | 产品拒绝 | hard gap |
| 草稿与发布 | CoachDraft → ReviewHarness | exact pass | 保留评测资产 | Pi 直接 final producer 为 0 |
| 知识证据 | 实际 ToolExecutionRecord | process-local exact pass | 保留评测资产 | public result 仍 body-free |
| typed output/Artifact | terminal Manifest + SHA Artifact | exact pass | 保留评测资产 | Harness vertical test |
| Usage | completeness-aware per-call/aggregate | 成功 exact；missing fail closed | 保留评测资产 | projector/Recorder tests |
| 常见终态 | 受限稳定 vocabulary | final/budget/timeout/provider error 可映射 | 部分兼容 | 5F-3 matrix |
| 扩展失败终态 | 当前生产枚举 | provider_aborted/protocol/process 等无法无损映射 | 产品拒绝 | hard gap |
| live event/stream | 运行中交付、真实 sequence/time、parity | child 完成后批量投影 | 产品拒绝 | hard gap |
| deterministic fallback | Harness degraded/rejected | exact pass | 保留评测资产 | bad citation/tool/process/usage tests |
| Session/Memory/SSE | 阶段 6 在 Python V2 深化 | 未评估 | 不跟随扩展 | 不属于 5F |

## 3. 安全矩阵

| 风险 | 当前控制 | 结果 | 长期处理 |
|---|---|---|---|
| 未授权 Tool | Manifest/Registry/整批预检 | pass | 冻结测试继续回归 |
| Tool 参数/结果泄漏 | public event/result/Trace body-free | pass | detailed record 只存在单次进程内 |
| secret 进入 child | allowlisted environment | pass | CI/实验不得读取 `.env` 或 Key |
| 非法/超长 IPC | versioned strict 256 KiB JSONL | pass | 解码错误 fail closed |
| child hang/crash/stderr | parent deadline、terminate/kill、限长 stderr | pass/partial | 不是 OS 沙箱；不用于真实 Provider |
| 依赖生命周期脚本 | `npm ci --ignore-scripts` | pass | exact lock、official registry |
| 供应链面 | 94 个 npm 包 | unfavorable | 仅开发/研究；高危实际路径触发归档/新 ADR |
| unsafe publication | ReviewHarness 唯一 publisher | pass | 任何绕过均为直接拒绝 |

## 4. 非功能与运维矩阵

| 维度 | 观测 | 判断 | 退出影响 |
|---|---|---|---|
| 安装体积 | 11,355 files / 约 62 MB `node_modules` | 不利；不进 Git/生产镜像 | 反对产品采用 |
| 依赖数量 | 94 packages | 额外研究供应链面 | exact lock + ignore scripts + 归档门 |
| 安装耗时 | Windows 本地约 5-6 秒量级 | 当前 CI 可接受，不是 SLO | 暂保持续复现 |
| 单 run 进程 | Windows 本地约 0.4 秒量级 | 对产品不利；不是生产 p50/p95 | 不做进程池优化，因产品拒绝 |
| 部署 | Python + Node 24 sidecar | 增加镜像/日志/故障面 | 不进入部署 |
| 调试 | Python↔JSONL↔Node 多边界 | 比单 Python 更复杂 | 维护收益未成立 |
| 代码收益 | Pi loop 可运行，但 adapter 重建 Compiler/transcript/evidence/terminal/Trace | 没减少总维护面 | 反对产品采用 |
| CI 复现 | exact lock + public Actions 已通过 | 作品集/防漂移价值明确 | 冻结保留 |
| 真实质量 | 未调用真实模型 | unknown | 不影响结构性拒绝，不补 5F-4 |

## 5. 生命周期矩阵

| 资产 | 是否保留 | 允许变更 | 禁止变更/用途 |
|---|---|---|---|
| Python `AgentRuntimeV1` | 是，产品唯一默认 | 阶段 6/8 按自身路线演进 | 不为 Pi parity 扩枚举或复制语义 |
| Pi package/lockfile/sidecar | 是，冻结评测 | 安全/可复现性或新 ADR 实验 | 不进入产品依赖或部署 |
| evaluation adapter/projector | 是，冻结评测 | 最小安全/复现修复 | 不随业务功能追随扩展 |
| Pi tests | 是 | 防回归、安全和归档验证 | 不冒充模型质量测试 |
| 默认 CI Node/npm step | 暂保 | 若成本/风险触发可用新 ADR 分离或归档 | 不证明生产使用 Pi |
| 5F ADR/exit docs/Git history | 永久保留 | 勘误需保留历史 | 不删除负面结果或改写为成功采用 |
| Pi 真实 Provider slice | 不创建 | 只有新采用门重新授权 | 不补做 5F-4 |

## 6. 教学与作品集矩阵

| 可以陈述 | 不可以陈述 |
|---|---|
| 对官方 Pi 0.84.2 做源码/许可证/协议审计 | “RiftCoach 基于 Pi 构建” |
| 实现隔离 JSONL sidecar 和严格 fail-closed adapter | “Pi 已进入产品或部署” |
| 用同一 Harness/Trace 合同发现三项 hard gap | “Scripted 测试证明 Pi/模型质量” |
| 因无信息增益在真实调用前停止 | “调用真实 Pi Provider 后比较质量” |
| 负面实验促成产品继续采用 Python Runtime | “自建 Runtime 普遍优于所有框架” |
| 保留可复现评测资产并冻结生命周期 | “项目有双 Runtime/自动 Runtime 路由” |

## 7. 退出判定

5F 的问题已得到足够答案：

1. 候选身份、许可、低层协议和安全边界已审计；
2. 隔离 loop 与 Harness/Trace 成功路径已真实执行；
3. 三项强制 Runtime gap 与跨语言成本已由测试和测量固定；
4. 既定采用门正确阻止无信息增益的真实调用；
5. 产品、实验资产和设计思想的生命周期已分别裁决；
6. 未完成的真实模型质量、Session/Memory/SSE/部署不是 5F 的退出阻塞项。

因此 5F 可以在本地与 exact-SHA 公共门禁成功后关闭，并交接既有路线的
`6A-entry-design`；交接不自动实现阶段 6。
