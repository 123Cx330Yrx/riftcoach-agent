# 5F-5 Pi Adoption Decision / Exit Review 计划

## 1. 要解决的问题

5F-1 至 5F-3 已经回答了“Pi 能不能在隔离实验里跑起来”和“它能否经过现有 Harness”。
5F-5 不再写第二套 Runtime，也不再调用真实模型；它只把这些证据转成一个长期可维护的技术决策：

```text
产品 Runtime 是否使用 Pi
+ 实验代码是否继续保留
+ 哪些设计经验进入 RiftCoach
→ adopt / partial-adopt / reject
```

这三层必须分别裁决。否则一句“局部采用”可能被误解为线上产品已经依赖 Pi。

## 2. 底层原理

第三方框架的采用不是看 demo 能否运行，而是看它能否在既有产品约束下减少总维护成本：

```text
候选带来的能力收益
- 语义适配成本
- 依赖与部署成本
- 调试和故障恢复成本
- 安全与长期升级成本
```

如果候选能运行，但为了保持 Context、终态和实时 Trace 又要重写已有能力，那么“接入成功”仍可能是
负收益。负面实验同样有价值，但必须与产品依赖分开保存。

## 3. 本检查点会做什么

1. 建立最终比较矩阵，覆盖职责、合同、安全、性能、依赖、运维、教学和作品集价值；
2. 用 ADR-0037 分别裁决产品 Runtime、隔离实验资产和可吸收设计思想；
3. 冻结实验资产生命周期、默认 CI 复现边界和重新开启条件；
4. 形成 5F 总退出审查，核对 5F-entry 至 5F-5 的证据和限制；
5. 同步 canonical、需求账本、路线、能力矩阵、项目决策和活动计划；
6. 运行聚焦/完整回归和全部本地门禁，再提交、推送并核验 exact-SHA 公共 CI。

## 4. 本检查点不会做什么

- 不补做 5F-4，不读取 Key，不调用真实 Provider、Riot 或 held-out；
- 不把 Pi 接入 `AgentRuntimeV1`、FastAPI、Application Service 或默认 composition；
- 不扩展生产 Runtime 的 Context、terminal 或 stream 合同来迁就实验；
- 不升级 Pi/Node 包，不引入 Claude Agent SDK、LangGraph、Multi-Agent、MCP 或模型路由；
- 不展开阶段 6 的实现，只在 5F 公共闭环后交接到既有路线中的 `6A-entry-design`。

## 5. 决策候选与判定规则

| 候选 | 成立条件 | 当前证据方向 |
|---|---|---|
| `adopt` | 强制 Runtime 合同全部通过，且维护收益明确 | 已被三项 hard gap 排除 |
| `partial-adopt` | 产品不依赖 Pi，但隔离资产或设计思想具有明确、受控的长期价值 | 需要在本轮裁决生命周期 |
| `reject` | 产品和当前仓库均不再保留 Pi 可执行资产，只保留 ADR/Git 历史 | 若持续 CI/供应链成本大于复现价值则选择 |

硬安全或合同失败不能被测试数量、框架流行度或作品集价值抵消。

## 6. 建议裁决

建议采用精确定义的：

```text
partial-adopt for frozen evaluation evidence only
+
reject Pi as product Runtime
```

含义如下：

- 产品唯一默认底座继续是 Python `AgentRuntimeV1`；
- 保留 `experiments/pi_runtime/`、`app/evaluation/pi_runtime/`、对应测试、exact lockfile 和 CI
  复现能力，作为冻结的架构评测资产；
- 不为新产品功能持续扩展 adapter；依赖升级或功能重开必须有新的 Bad Case、ADR 和对照计划；
- 若出现高危依赖、Node 不兼容、持续 CI 不稳定/成本显著或实验长期漂移，则优先归档可执行资产，
  不得反向迫使产品 Runtime 迁就它；
- 可吸收的思想仅包括版本化严格协议、fail-closed projection、采用硬门和负面实验记录方法。

## 7. 数据流与控制流

保留后的产品控制流不变：

```text
FastAPI / Application Service
→ Python AgentRuntimeV1
→ Python AgentLoop + ToolRuntime
→ ReviewHarness
→ Trace / Artifact / receipt
```

Pi 只存在于测试/研究控制流：

```text
Scripted test case
→ evaluation-only Python adapter
→ isolated Node/Pi sidecar
→ Python ToolRuntime
→ existing Harness / strict projector
→ parity result
```

两条路径没有运行时选择开关；用户和产品请求不能选择 Pi。

## 8. 验证计划

### 聚焦证据

- Pi protocol/sidecar/parity/Harness/Trace 测试；
- governance 对 canonical、唯一下一步和连续 RQ 编号的检查；
- Node syntax、exact dependency tree 和 `npm ci --ignore-scripts`。

### 回归证据

- 完整 pytest；
- development 与 independent RAG 门；
- compileall；
- Harness SDK boundary、tracked secret/run-data boundary、Harness dry-run；
- `git diff --check`。

### 公共闭环

- 提交并推送当前决策；
- 等待 exact commit SHA 的 GitHub Actions 成功；
- 只有成功后才把 5F 标为完成并交接 `6A-entry-design`，不自动实施阶段 6。

## 9. 当前限制

- Scripted/Fake 证据不评价任何真实模型质量；
- Windows 约 0.4 秒进程开销不是生产 p50/p95；
- 保留 CI 复现能力意味着继续承担 94 个 npm 包的开发/研究供应链面；
- `partial-adopt` 只描述评测资产和方法，不是产品功能、部署或 Runtime 双轨。
