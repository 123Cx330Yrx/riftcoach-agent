# 8E：GLM-5.3 候选会话关闭报告计划（RQ-210）

## 目标

为 RQ-209 暴露的组合关闭未知增加一个可审计、body-free、只存在于会话内存的分资源观察，
同时保持旧回执和产品边界不变。

## 方案

1. 让 `ZhipuStreamSession` 持有的迭代器与外层 SDK stream wrapper 各自返回安全关闭状态。
2. 对同一对象去重，对不同对象分别最多调用一次；清理过程中继续尝试其他资源。
3. 用不可变 `ZhipuStreamCloseReport` 汇总资源状态、组合状态和别名关系。
4. 保留旧 `close_failed` 和 v2 receipt/schema，不把报告序列化或写入真实诊断回执。

## 验证

- shared/distinct 资源各自关闭一次；
- 迭代器、SDK wrapper、两者同时失败时均映射为安全状态，不保留或暴露异常原文；
- `GeneratorExit` 等控制异常在其他资源尝试后重抛；
- 无 hook 与仅 `__exit__` 资源保持保守状态；
- adapter/deadline/v2/real 聚焦 `73 passed`，相邻集合 `182 passed, 27 subtests passed`，再跑 compileall、diff check、治理和 exact-SHA 公共 CI。

## 不在本计划内

不修改 `CandidateStreamReceipt` schema，不改 `cancel()` 为异步，不声称 raw HTTP response 可取消或
唤醒 pending `next()`，不发新的真实 API，不注册候选，不接入产品 Runtime/Workbench/Portal/Account/Auth，
不改变严格 Flash v1 的 2048/零额外调用或 `production_media=0`。

## 收口条件

同一实现提交 `15026a8abeeb2f343fbf893e55e2d94c512a86f6` 的公共 Actions run `33657368435` 已
exact-SHA 成功（三 job 全绿）；公共证据已写入状态。后续 provider-level 观察或新的 schema 仍需单独授权。
