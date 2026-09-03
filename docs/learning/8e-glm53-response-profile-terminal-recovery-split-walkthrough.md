# 8E 学习材料：如何拆开 Flash 的档位、终态、Usage 与恢复

## 问题

一次长响应超时可能来自思考档位消耗、输出预算、流没有到达 terminal、Usage 尾帧缺失，
也可能来自传输截止。若只看一个 `fail_closed`，就会误把客户端控制问题当成模型质量问题。

## 方法

先用请求 profile 描述 `reasoning_effort`、`clear_thinking`、输出上限和 Agent 窗口；再用
normalized event fixture 让候选观察器判断 terminal/EOF/Usage 生命周期；只有完整闭合的
边界才交给严格或候选 policy。候选 policy 命中白名单时只返回 `candidate_eligible`，
当前 activation gate 仍把恢复动作锁为 `blocked_activation`。

## 结果

固定 9 场景全部通过。2048/low 的完整 stop 与工具回合能明确交付；8192 的
reasoning-only `length` 可被识别但不能静默重试；缺 Usage 和 elapsed timeout 不补零、
不伪造 EOF。回执只含状态和安全码，provider calls=0，不能证明真实供应商能力。

## 迁移边界

这套拆分是评测工具，不是产品 Runtime 改造。下一步若要做真实候选域门，必须另立版本、
绑定 exact SHA、重新审查预算/成本/Trace，并保持严格 Flash v1、Workbench 和前端边界不变。
