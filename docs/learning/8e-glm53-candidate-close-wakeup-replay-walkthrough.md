# RQ-212：候选 close/wakeup 离线回放 walkthrough

## 问题

RQ-211 的真实样本是 `not_pending`，因为第二次读取没有停在等待状态。
这不是取消成功或失败。为了不靠重复付费请求“碰运气”，我们需要一个能稳定制造
等待状态的本地夹具，先验证观察器本身是否按合同分类。

## 核心原则

回放证据和供应商证据必须分层。`CandidateCloseWakeReplayReceipt` 明确写入
`evidence_origin=offline_fake`、`real_provider_observed=false`、
`provider_call_count=0`、`network_used=false`。每个 fake session 可以被观察器打开
一次（`fake_session_open_count=1`），但这不代表发生了供应商调用。

## 代码地图

| 部分 | 作用 |
| --- | --- |
| `app/evaluation/candidate_close_wakeup_replay.py` | 固定场景、闸门式 `ReplaySession`、严格回执与 create-only writer |
| `app/evaluation/candidate_provider_close_wakeup_observation.py` | 被复用的真实观察器；本批不改其真实路径 |
| `scripts/replay_glm53_flash_candidate_close_wakeup.py` | 不读 dotenv/凭据、不创建或调用 SDK client、不建立网络连接的回放入口（包导入可能加载依赖模块） |
| `tests/test_candidate_close_wakeup_replay.py` | 状态矩阵、稳定 digest、脱敏、往返解析与不可覆盖验证 |
| `data/evaluation/results/offline/` | 与 provider capability 结果隔离的离线回执目录 |

## 数据与控制流

```text
REPLAY_SCENARIOS（固定期望）
        ↓
ReplaySession 的 read/cancel Event 闸门
        ↓
observe_candidate_session（一次 fake session）
        ↓
期望/实际状态比较
        ↓
OfflineReplayReceipt（不含正文，provider_call_count=0）
```

五个场景是：正常 EOF、取消后唤醒、取消返回但未唤醒、取消超时、取消抛出。
回执只保存状态和计数，不保存等待时长，因此同一版本重复运行会得到相同 canonical
内容和场景 SHA。取消抛出时观察器的 `cancel_returned=true` 只表示控制线程已结束，
不表示取消成功；回执同时保留 `observed_cancel_status=raised`。

## 验证与运行手册

```powershell
& .\.venv\Scripts\python.exe scripts\replay_glm53_flash_candidate_close_wakeup.py `
  --output data\evaluation\results\offline\zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_local.json
```

该命令不需要确认旗标，不读取 `.env` 或凭据，不创建/调用 SDK client，也不建立网络连接。
既有回执使用 create-only 写入，重复运行必须改用新的输出路径或只读校验已有文件，不能覆盖。
测试应验证五场景全部通过、每个场景只
打开一次 fake session、重复回放内容稳定、非法正文/Key/headers/request ID 被拒绝，
以及已有回执不能被覆盖。

## 失败、安全与边界

回放失败只代表本地观察合同或夹具回归失败；它不能推导 GLM-5.3 的网络行为、模型
能力、API/Key 有效性或生产成熟度。父进程超时/错误仍由 RQ-211 的真实探针合同和
既有测试覆盖。候选继续未注册、`execution_allowed=false`、
`capabilities.streaming=False`，产品 Runtime、Workbench、Portal、Account、Auth
与默认模型不变。

## 面试表述

> 我先用固定 Event 闸门做了五种 close/wakeup 生命周期的离线回放。回执明确标记
> `offline_fake` 且供应商调用数为零，所以它证明的是我们自己的分类和脱敏合同可
> 重复复核，不冒充供应商 close/wakeup 证据；真实 provider 观察仍是独立闸门。

## 本批验证结果（2026-09-03）

实现提交 `1a32012d9dc6424aa012f160d48c8847e21b00ec` 的公共 Actions `33707313651` 三 job exact-SHA 全绿；
本地 RQ-212/RQ-211 聚焦回归 `37 passed`。最终 v2 回执为
`data/evaluation/results/offline/zhipu_glm53_flash_candidate_close_wakeup_replay_rq212_v2.json`（`2220` bytes，
SHA-256=`a4477258735c5f217f1c328830e8453e4c686a9b386e1e04e0f37b6d777876f2`），三身份 SHA 绑定该实现提交。
这关闭的是离线回放合同；真实 provider close/wakeup 仍未证实，下一精确门是一次性真实观察授权。
