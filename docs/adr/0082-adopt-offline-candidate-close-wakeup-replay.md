# ADR-0082：采用候选 close/wakeup 离线回放协议

- 状态：已采用（8E evaluation-only）
- 日期：2026-09-03
- 依据：ADR-0079、ADR-0080、ADR-0081；RQ-207、RQ-210、RQ-211、RQ-212

## 背景

RQ-211 的一次真实 `glm-5.3-flash` 观察在有限窗口内很快结束，结果是
`not_pending`，没有可以交给 `cancel()` 唤醒的挂起读取。直接重复真实请求既不能
保证改变这个条件，也会让“观察条件未成立”和“供应商取消失败”混在一起。

## 决策

新增独立的 evaluation-only 回放协议
`glm-5.3-flash-candidate-close-wakeup-replay` / schema `1.0.0`：

1. 用固定的内存 `ReplaySession` 和 Event 闸门重放五个生命周期：正常 EOF、取消
   后 reader 唤醒、取消返回但 reader 未唤醒、取消超时、取消抛出安全错误。
2. 复用 RQ-211 的 `observe_candidate_session()`，由观察器返回值派生每个 case 的
   `passed`；场景表有稳定 SHA，回放回执不记录运行时耗时。
3. 回执强制标记 `evidence_origin=offline_fake`、`real_provider_observed=false`、
   `provider_call_count=0`、`network_used=false`；观察器内部的
   `observer_call_count=1` 与 fake session 的 `fake_session_open_count=1` 不等同于
   供应商调用。
4. 回执放在 `data/evaluation/results/offline/`，使用 canonical UTF-8/LF、原子
   create-only writer；不复用 RQ-211 provider receipt 的 schema 或路径。

回放入口不读取 dotenv/凭据、不创建或调用供应商 SDK client，也不建立网络连接；由于
现有 Python 包的导入副作用，依赖模块可能出现在进程内，但这不等于供应商调用。

## 被否决的替代方案

- **重复同一真实请求**：不能保证形成 pending-read，且会增加无必要的外部调用；
  留给后续有明确参数的一次真实观察门。
- **把 fake 回执放进 provider capability 目录**：会被真实能力扫描误认，违反
  证据来源分层。
- **修改产品 Provider/Runtime 或默认模型**：RQ-212 只验证观察协议，不是候选
  注册或生产接线门。
- **在进程内强杀阻塞线程**：普通 Python 无安全语义；父进程硬边界仍沿用 RQ-211
  的子进程合同。

## 影响与边界

该协议让本地 pending-read 分类、单次打开、脱敏和回放稳定性可被公共 CI 复核，
但不能证明供应商 SDK 的 close 非阻塞、底层 HTTP response 可取消或真实 pending
`next()` 能被唤醒。候选继续 `disabled`/未注册，`capabilities.streaming=False`；
严格 Flash v1、默认模型、AgentLoop、统一 Trace、Portal、Account、Workbench、
Auth、路由、`production_media=0`、G53-7、黄金切片、生产准入和 8F 均不变。

## 后续门

只有在这份离线回放和公共验证闭环后，才可另行决定是否授权一次参数明确的真实
provider close/wakeup 观察；离线回放不会自动触发真实请求。
