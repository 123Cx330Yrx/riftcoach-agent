# RQ-213：候选 close/wakeup 真实观察计划与结果

## 目标

在 RQ-212 离线五场景回放之后，使用一次受控真实 provider 请求检查当前观察器
是否能看到 pending-read；只记录脱敏状态，不把一次观察提升为模型或生产结论。

## 固定边界

- provider/model：`zhipu` / `glm-5.3-flash`
- 请求次数：1；SDK `max_retries=0`；不 retry、不 recovery、不追加第二请求
- 父进程边界：30 秒；输出为新的不可覆盖 provider capability 回执
- 身份：implementation、diagnostic、input-plan 均绑定
  `a396412f7cd0f2e923536cf55f715dd56251aae5`
- 证据：只保留状态、事件类别、计数、时间数字和 close 投影；不保留敏感值或正文

## 执行结果

回执路径：

`data/evaluation/results/provider_capabilities/zhipu_glm53_flash_candidate_close_wakeup_observation_rq213_v1.json`

文件大小 909 bytes，SHA-256 为
`8b2b645bc79785cec6520759d63c530d1b6d6a7d06b192b472334df543706f7b`。
调用成功打开会话并在 172ms 内观察到 reasoning/content 类别，但状态仍是
`not_pending`；没有 pending reader，也没有执行 cancel。子进程退出码为 0，三层
关闭投影均为 `closed`。

## 验证

执行前使用 exact-SHA 公共绿灯提交；执行后重解析 canonical JSON、计算文件 SHA，
并核对回执允许字段与候选身份。后续提交应继续运行聚焦回归、compileall、
`git diff --check`、governance 和同 SHA 公共 CI。

## 结论和下一步

本计划关闭“一次新鲜真实观察”这一有限门，但没有关闭 provider close/wakeup 闸门。
结果不证明 close 非阻塞、不证明 pending `next()` 可唤醒，也不改变候选 gate 或产品
默认。下一步是用户裁决是否另立能稳定制造 pending-read 的协议；在裁决前不自动追加
真实请求、注册候选、进入 G53-7 或黄金切片。
