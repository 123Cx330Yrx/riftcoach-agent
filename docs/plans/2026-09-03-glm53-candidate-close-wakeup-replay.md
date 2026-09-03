# RQ-212：候选 close/wakeup 离线 pending-read 回放计划

> 本计划只处理 8E 的 evaluation-only 候选证据，不启用 GLM-5.3、不改变产品
> Runtime/Workbench/Portal/Account/Auth，也不发真实请求。它对应 RQ-211 暴露的
> “真实样本没有形成 pending-read”问题；离线回执与 provider capability 回执分开存放。

## 要解决的问题

RQ-211 的真实回执是 `not_pending`：会话很快读完，没有一个可供 `cancel()`
唤醒的挂起 `next()`。如果直接重复真实请求，我们仍可能得到同样的结果，而且会
把“没有观察条件”误读成“供应商取消失败”。本计划用内存里的固定闸门重放五种
生命周期，让我们先证明自己的观察器分类、单次打开和脱敏合同是稳定的。

## 软件原则

- **证据来源分层**：fake replay 只能证明本地观察逻辑；它不能替代 provider-level
  网络证据。回执强制 `evidence_origin=offline_fake`、`real_provider_observed=false`
  和 `provider_call_count=0`。
- **资源边界**：每个场景只打开一次 fake session；取消、读线程和清理闸门在场景
  结束时释放，避免测试线程泄漏。真实探针默认值和 RQ-211 回执不改。
- **派生而非手填**：场景期望、观察结果和 `passed` 从固定矩阵与观察器返回值
  派生；不把 fake 的 `observer_call_count=1` 写成供应商调用次数。
- **不可变证据**：离线回执使用 canonical UTF-8/LF JSON 和 create-only writer，
  路径放在 `data/evaluation/results/offline/`，不进入真实能力结果目录的扫描。

## 实现范围与数据流

```text
固定 scenario matrix
        ↓
        ReplaySession（Event 闸门，不读 Key、不创建/调用 SDK client）
        ↓
observe_candidate_session（现有 RQ-211 观察器）
        ↓
期望值 ↔ 实际值的 body-free case
        ↓
OfflineReplayReceipt（provider_call_count=0）
```

覆盖：正常 EOF、取消后 reader 唤醒、取消返回但 reader 未唤醒、取消超时、取消
抛出安全错误。父进程 `child_timeout/child_error` 的真实边界仍由 RQ-211 测试覆盖，
不在本回放中伪造 provider 状态。

## 任务

1. 新增 `app/evaluation/candidate_close_wakeup_replay.py`：固定不可变场景、
   `ReplaySession`、严格 schema、场景 SHA、离线回执和 create-only writer。
2. 新增 `scripts/replay_glm53_flash_candidate_close_wakeup.py`：默认不读取 dotenv
   或凭据、不创建/调用 SDK client、不建立网络连接，不需要确认旗标，只运行离线矩阵
   并输出安全摘要。（既有包导入可能加载依赖模块，但不会实例化供应商客户端。）
3. 新增聚焦测试：五场景全覆盖、每场景只打开一次、重复运行 canonical 内容稳定、
   回执往返解析、禁止正文/Key/headers/request ID、不可覆盖已有文件。
4. 生成一份独立离线回执；它不加入
   `data/evaluation/results/provider_capabilities/`，不参与旧 provider capability
   schema 分派。
5. 运行聚焦回归、相邻候选回归、compileall、diff check、governance 和 exact-SHA
   公共 CI；只在这些证据通过后更新 RQ-212 状态。

## 明确不做

- 不追加 GLM-5.3 真实 API 请求，不重写 RQ-211 回执，不执行 recovery/retry。
- 不把 fake 的 `pending_cancel_returned` 或 `reader_woke=true` 写成供应商能力结论。
- 不注册候选、不修改 `capabilities.streaming`、默认模型、AgentLoop、统一 Trace、
  Portal、Account、Workbench、Auth、路由或 `production_media`。
- 不进入 G53-7、黄金切片、生产安全/部署/合规或 8F。

## 验收与后续闸门

完成后只能得出：“本地 pending-read 观察协议可重复，且脱敏/单次打开合同成立；
provider-level close/wakeup 仍未证实。”下一精确决定是是否授权一次新的、参数明确的
真实 provider 观察；不能由离线回放自动触发。
