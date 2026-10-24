# 8E 学习 walkthrough：为什么要先设计 recovery 诊断 v2

## 先说结论

现在不是把 GLM-5.3 的第二次请求接进产品，而是先把“如果将来允许一次候选 recovery，
我们要留下什么证据”定义清楚。RQ-202 已证明旧同步诊断器带着真实 SDK、旧账本和
未知 Usage 的零值投影，不能直接复用。v2 因此是一份独立的、只保存脱敏事实的诊断协议。

## 1. 为什么旧脚本不能加开关继续用

旧脚本把三件事放在一起：调用供应商、决定是否再请求、写入诊断结果。这样很容易把
“请求没有响应”“Usage 没回来”“模型输出被截断”和“没有权限”混成同一种失败，也容易
在重构时漏记一次已经发出的调用。v2 将它们拆开：

```text
显式授权/身份
      ↓
reserve（先记账）
      ↓
一次 normalized 流
      ├─ BoundaryObservation（只留状态）
      └─ 临时 assembler（完整结果只在内存）
      ↓
policy 重算 → settle → body-free receipt
```

这条顺序保证即使 transport 在打开后立刻失败，也不会出现“账本显示没有调用”的假象。

## 2. recovery 到底是什么

它不是把原请求接着写，也不是 SDK 自动重试。它是第二次、完整提交的请求，attempt kind
明确写成 `fresh_recovery`，继续使用同一份消息语义摘要，但拥有自己的 timeout、Usage、
失败和费用记录。只有首回合严格符合 `length + 空正文 + 非空 reasoning + 无工具 + 有效
Usage + 初始 Agent 阶段`，并且未来有独立 permit，才有资格考虑第二次。当前 activation
仍然关闭，所以设计不会产生第二个真实请求。

## 3. 为什么 unknown 不能写成 0

假设请求已经抵达服务端，但连接在 Usage 返回前断开。此时我们知道“至少发生了一次
尝试”和一些耗时，却不知道准确 token 或费用。把 input/output 写成 0 会让人误以为
没有消耗，还可能错误地放行下一次请求。v2 采用三态：

```text
within   已知资源齐全且没有超限
exceeded 已知资源明确超限
unknown  仍有资源未知，不能证明 within
```

金额也一样：没有可靠的公开单价快照时保持 `unknown`；有快照只能叫 `estimated`，只有
可核验的本次账单凭证才能叫 `actual`。这比给出一个看似精确但无法追溯的数字更诚实。

## 4. 延迟为什么要分段

“总耗时 24 秒”无法回答问题出在哪一段。v2 分别记录打开流、首事件、首个可见正文、
终止、关闭和总耗时；每个值都是单调时钟的整数毫秒，没有观察到的阶段为 `null`。因此
可以区分“很快收到 reasoning 但迟迟没有终止”“根本没有首事件”和“终止后关闭失败”，
却不会把这些客户端现象夸大成供应商内部质量结论。

## 5. 失败聚合如何避免掩盖第一现场

每次尝试只允许安全的失败类别（transport、protocol、identity、usage、budget、
completion、consumer、control）和规范化 code/stage。顶层记录保留第一条失败、最后
终态和明确的 recovery skip reason。后续异常不能覆盖第一条，异常正文也不进入日志或
JSON。这样“没有响应”不会被改写成“模型拒绝”，`Usage missing` 也不会被改写成“零费用”。

## 6. 记录和产品 Trace 的边界

v2 记录是 evaluation evidence，不是产品 `RuntimeTrace`。它只在可选的、原子、不可覆盖
的 JSON 文件中保存身份、状态、计数、哈希、资源数字和安全码；正文、reasoning、Prompt、
工具参数、Key、原始 request ID 和 SDK 对象永远不落盘。完整 `ChatResponse` 如果要做
质量标注，只能交给显式的内存 consumer，随后立即释放。

## 7. 下一步怎样实施

设计门完成后，下一批才实现 fake/local v2 值对象和测试。测试要证明身份/版本不能伪造、
reserve/settle 顺序不能绕过、unknown Usage/费用不会被归零、分段时钟不会倒退、二次
请求没有隐式 retry，以及所有 receipt/日志/repr 都不含正文。实现通过 exact-SHA 公共 CI
后，真实调用仍需另一次明确授权；它也不能自动改变产品默认模型、打开 streaming、重跑
G53-7 或跳过 8F 闸门。

## 当前检查点

本门只完成协议设计，Stage 8/8E 仍为 `in_progress`，候选未注册，
`production_media=0` 不变。下一项是：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-recovery-diagnostic-version-implementation / pending-user-authorization`
