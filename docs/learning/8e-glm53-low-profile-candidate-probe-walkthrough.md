# 8E 学习材料：GLM-5.3 Flash 低思考候选探针

## 先说问题

前一轮 `max + 8192` 的真实候选观察超出 90 秒，并不说明账号、适配器或模型整体
不可用。它只说明那组思考档位、输出预算和终态要求没有在限定时间内交付。为了不把
多个变量混在一起，本轮只改变思考档位和输出上限，其他身份与冻结上下文保持不变。

## 软件原则

候选实验必须和产品运行时隔离。正常产品构造器只接受已经登记的运行档案；低思考档
通过显式 `from_candidate_profile` 才能使用，并且身份上写死 `execution_allowed=false`。
这样“实验可以发请求”与“产品可以自动采用”是两个独立开关，避免一次成功探针悄悄改变
默认行为。

## 数据与控制流

1. 读取已经冻结的无工具上下文和输入计划摘要。
2. 构造 `low + 4096` 候选请求，覆盖调用者可能伪造的 profile 元数据。
3. 创建一次、retries=0 的智谱客户端并调用显式候选 Provider。
4. 只把终态、Usage 状态、计数、延迟和哈希写入回执；正文和推理内容在回执边界被拒绝。
5. 回执采用 create-only 写入，已有文件时直接失败，保证旧证据不可覆盖。

## 结果如何读

这次观察只发出 1 次真实请求，得到 `observed`、`finish=stop`、有效 Usage，输入/输出
token 为 `1973/498`，约 `20.7s` 完成。它证明低思考候选在这个冻结无工具问题上能形成
完整规范化响应；它没有证明工具调用顺序、多轮恢复、领域任务质量或生产 streaming。

## 如何验证

候选 profile 与探针测试共 25 个通过，本次相关候选/流/智谱回归共 357 个通过；公共 Actions
`33746833148` 在实现提交 `c3de5555d0b00d77f402c41a842d00df53f46865` 上三 job 全绿。
回执提交后再检查 canonical JSON、body-free 字段、文件不可覆盖、compileall、差异检查
和治理脚本。真实回执 SHA-256 为
`c2946954181b10da2dcb726e186a2800d4381da24d04395b7baef4eecebd1957`。

## 失败与安全边界

客户端异常、Provider 错误和无响应必须落到安全错误码，不能把未知 Usage 当成零，也不能
把 `stop` 单独当作完整产品答案。探针不保存 Key、Authorization、headers、Prompt、
正文、reasoning、工具参数或完整 request ID；候选不进入产品 Runtime，不执行 recovery，
不触碰 Portal、Account、Workbench、Auth、路由和 `production_media=0`。

## 下一步与面试表达

下一步不是立刻扩大调用，而是为低思考候选单独设计 held-out 领域门，重新绑定 G53-3、
预算和终态/Usage 判定。可以这样概括：

> 我把一次长响应失败拆成“思考预算假设”和“产品准入”两个问题，用显式 candidate-only
> profile 做一笔无工具真实探针。探针成功只关闭了一个窄观察问题；由于没有领域、多轮和
> 成本证据，我保留 activation gate，避免把实验结果误当成生产模型资格。

当前精确指针：

`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / candidate-low-profile-probe / completed-real-observation / pending-next-decision`
