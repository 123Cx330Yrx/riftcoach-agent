# 8E 学习材料：候选 close/wakeup 真实观察（RQ-213）

## 1. 问题与原则

流式模型调用里，“已经收到第一批事件”“读取器正在等待下一块”“取消已经返回”
和“底层连接确实被取消”是四件不同的事。RQ-211 的 `not_pending` 说明当时没有
第二次挂起读取，RQ-212 又用 fake 闸门验证了观察器的分类。RQ-213 的原则是只补一
个新鲜真实样本，并保持这些状态分离，避免把 `closed` 误报成 wakeup 成功。

## 2. 设计与代码地图

父进程由 `scripts/diagnose_glm53_flash_candidate_close_wakeup.py` 负责硬边界和一次性
回执；子进程才在确认门之后加载配置并创建显式 `ZhipuStreamSession`。
`app/evaluation/candidate_provider_close_wakeup_observation.py` 负责读取器、取消窗口、
事件类别和 close 投影。RQ-212 的
`app/evaluation/candidate_close_wakeup_replay.py` 仍只服务离线 fake，不与真实回执混写。

## 3. 数据与控制流

1. 父进程校验当前提交身份、输出路径和一次性确认。
2. 子进程打开唯一会话，先记录安全事件类别，再判断是否出现 pending reader。
3. 只有出现 pending reader 才会进入 cancel/wakeup 观察；本次没有进入该分支。
4. 退出前分别投影 iterator、SDK stream wrapper 和 composite 状态。
5. 父进程只写 canonical、body-free JSON；回执路径和 SHA 单独保存，不能覆盖旧证据。

## 4. 这次观察到什么

实现、诊断和输入计划均绑定 `a396412f7cd0f2e923536cf55f715dd56251aae5`；该提交的
Actions `33708492921` 三个 job 全绿。RQ-213 回执为 909 bytes，SHA-256 为
`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`。一次调用在
172ms 内打开并产生 `reasoning_seen/content_seen`，状态为 `not_pending`；cancel 未尝试，
reader 未被报告为唤醒，子进程正常退出，三层 close 投影为 `closed`。

## 5. 如何验证

验证重点是回执 schema、canonical 字节、身份 SHA、允许字段、调用数和退出状态；同时
运行真实观察器的聚焦测试、compileall、差异检查和治理检查。公共 CI 的绿色只证明
精确提交可复现，不把这一次外部观察变成公共生产能力。

## 6. 失败、安全与边界

回执不含 Key、Authorization、request ID、正文、reasoning 原文或 provider body；没有
retry、recovery 或第二请求。`not_pending` 不是唤醒成功，也不是唤醒失败；`closed` 只是
本层资源投影，不等于 HTTP response 已取消。候选保持 disabled/未注册，产品 Runtime、
默认模型、Workbench、Portal、Account、Auth、路由和 `production_media=0` 不变。

## 7. 运行手册

真实观察只能在明确的一次性授权和精确的新输出路径下运行；同一回执存在时必须失败，
不能覆盖。若没有稳定的 pending-read，下一步应先设计新版协议，不应靠重复请求消耗预算。
离线复核使用 RQ-212 的 replay CLI，不能把 fake 结果放进 provider capability 目录。

## 8. 面试式表述

“我把流式关闭拆成读取状态、取消状态和资源关闭状态，并用无正文回执保存一次真实
观察。该样本没有进入 pending-read，所以我不会声称供应商 close 能唤醒 `next()`；
这体现的是 fail-closed 的证据边界，而不是把一个 `closed` 字段当成网络事实。”

## 9. 当前状态

RQ-213 属于 8E 的 8-Advanced candidate-only 证据，不新增 8-Core capability。Stage 8/8E
仍为 `in_progress`，8F 尚未开始；下一精确 checkpoint 为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-close-wakeup-follow-up-decision / pending-user-decision`。
