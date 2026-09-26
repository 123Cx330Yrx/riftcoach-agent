# RQ-218/RQ-219：Flash 协议复核与候选 8192 响应完成度计划/结果

## 目标

在 RQ-217 的客户端唤醒修复之后，分别确认最新实现的基础协议身份，以及放宽到
8192 输出后完整候选流能否在固定窗口内形成终态。两项都属于 8E 的
candidate-only 评测，不改变产品接线。

## 固定范围

- 普通 API：`https://open.bigmodel.cn/api/paas/v4/`、`zhipu/glm-5.3-flash`；
- G53-3：精确 3 次调用，SDK retries=0，脱敏 JSON 回执；
- 候选流：`glm-5.3-flash-runtime-v2-candidate/2.0.0`，8192 单次上限、90 秒
  attempt、120 秒 transport、最多一个 recovery 槽位但本批 activation 仍 disabled；
- 不改 `.env`、默认模型、Portal、Account、Workbench、Auth、路由或生产媒体；不保存正文。

## 执行结果

### RQ-218：最新实现的 G53-3

实现身份为 `aa22cea0daeb443b635706144ccbfa66185670c4`，证据提交为
`4b6cd5807f40f6a8dd469f21c688be861261d20c`；Actions `33735039437` 的 pytest、
postgres-migrations、packaging-smoke 均成功。3/3 调用通过，A1 用时 20234ms、A2
用时 14938ms；回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_adapter_protocol_aa22cea.json`
大小 2145 bytes，SHA-256=`feeb7fd7eec2643ca692bd6182fd94a04abed354b17b892029402c0217641e99`。

### RQ-219：候选 8192 单次真实流

在 `4b6cd5807f40f6a8dd469f21c688be861261d20c` 上只发送 1 次 primary。90 秒时
诊断硬墙钟收口为 `fail_closed / elapsed_limit`，`calls_reserved=1`、
`calls_settled=1`，没有 recovery 或 retry。回执
`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq218_v1.json`
大小 4341 bytes，SHA-256=`21350d7883b4d2eea30e0467a7b8c23eed3a3ad5a9deeb309c44f8ded5cf3f84`。
它仍是 candidate/disabled，不能解释为模型质量失败或生产 streaming 失败。

## 验收与下一步

- RQ-218 的 exact-SHA 公共 CI 已完成；RQ-219 的证据提交公共 CI 需单独确认，
  在确认前不标记为公共闭环。
- 下一批先做零网络离线拆分：比较 `reasoning_effort`、`clear_thinking`、流终态/Usage
  尾帧和恢复决策的独立观测，补齐可解释的 body-free receipt；不自动增加真实调用。
- 只有离线合同和 exact-SHA 公共 CI 清楚后，才考虑新的候选域评测；候选注册、G53-7、
  黄金切片、生产安全/部署合规和 8F 仍是后续独立闸门。
