# 8E 学习 walkthrough：怎样复核候选 recovery 的边界

## 这次门解决什么问题

候选评估台已经能在本地观察一条规范化流，但“能观察”不等于“可以恢复”。复核时要
分别回答四个问题：回执字段是否来自真实观察、一次调用是否受自己的截止约束、未知
Usage 是否被误算成零，以及旧的真实诊断入口是否会把候选悄悄带进产品路径。

## 1. frozen dataclass 不是事实来源

`frozen=True` 只阻止原对象就地赋值，`dataclasses.replace()` 仍能构造一个新对象。
因此回执值对象必须在 `__post_init__` 中重新推导：最后一个 attempt 决定顶层终态，
观察状态决定 disposition/assembly，观察到的资源决定 budget projection。测试先构造
一个完整 stop 流，再替换这些字段；如果替换没有被拒绝，就说明控制面仍有伪造入口。

## 2. 两种时间预算不能混为一谈

候选 profile 同时有“每次 attempt 的 90 秒”和“整个候选运行的 180 秒”。前者由
observer 在流内强制，后者由 ledger 在结算时累计。正确关系是：

```text
一次流的 observer 截止 = min(单次 attempt 90s, 累计剩余窗口)
账本累计截止       = 所有已结算 attempt 的 elapsed 总和 ≤ 180s
```

如果直接把 180 秒传给 observer，单次请求就能越过自己的合同；如果把两者混成一个
字段，失败原因和下一步动作会失真。本轮只修正前者，未打开第二次请求。

## 3. unknown 不是零

流没有可靠 Usage 时，输入/输出总量应保持 `None`，资源确定性为 `unknown`，而不是用
`or 0` 伪造余额。旧的同步 `ResponseRecoveryLedger` 仍有这种历史投影，所以它不能
直接承载新的候选 recovery 诊断；新版本必须重新定义自己的 schema 和失败聚合。

## 4. 为什么不复用旧诊断脚本

旧脚本导入 SDK、dotenv 和生产 Provider，并在显式确认后拥有真实 I/O。它适合记录历史
有界尝试，但不适合作为 disabled candidate harness 的控制面。把它复制过来会同时带入
真实调用入口、旧账本和模糊的 activation 语义。本轮选择不改旧脚本，只在隔离 harness
里加固值对象和截止边界。

## 5. 验证与下一步

本轮 harness 聚焦 `18 passed`，相邻候选集合 `127 passed, 1 deselected`，编译、差异和
治理检查通过。一个旧诊断测试集合因 Windows CRLF fixture 与 canonical-LF 计划摘要不一致
而未作为证据；这是环境差异，不是把失败改写成通过。

下一门是“版本化候选 recovery 诊断设计”，仍需单独授权。设计前不发真实 recovery，
不把候选写成默认模型或 8-Core 生产能力。
