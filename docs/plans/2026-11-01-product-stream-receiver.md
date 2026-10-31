# 产品审查流式接收适配

目标：在现有opt-in Recent Review产品路径接收完整Sol流式审查，继续使用原业务政策、补丁应用、双fresh和持久恢复；不重发生成、不回写旧失败或诊断结果。

依据：2026-11-01完整输入只改stream后，1.516秒首字节、147.344秒完整completed/usage/EOF，无524。诊断接收器因重复created、身份/序号及done字段拒收。仅有聚合计数，不能声称已知道真实事件序列或追认该次严格验收。

实现：增加独立产品流式codec，复用当前非流式wire，仅stream=true；16,384输出、high和强制工具不变。复用owned-process 300秒截止、取消、回执及费用保留。产品合同快照升级到1.7.1并显式标记流式transport/thinking identity；其他历史候选及默认产品入口不变。旧任务迁移另核当前检查点和合同差异，当前不自动发送。

兼容范围：输出开始前最多一次替换空created前导；序号保持单调，记录间隙，只在该空前导替换边界允许重置；done.name缺失时仅从已绑定工具item补足校验。工具id/call_id/name/增量/最终arguments仍须一致；输出后的身份切换、冲突、缺少终态拒收。逐事件只记录白名单类型、序号、字段存在性和SHA，禁止保存reasoning正文或凭据。保留known usage，即使随后结构拒绝。

验证：真实SDK+Mock SSE覆盖标准/兼容正例、身份/工具反例、终态、断流/关闭、usage/凭据不泄；产品Runtime真实owned worker运行pass/修订/恢复/失败预算；发送前取消与在途超时/取消复用进程监管。更新当前manifest库存，检查原15当前清单差异与所有Runtime入口，不重跑付费15例。合成兼容事件不是上次真实SSE回放。

终点：离线接线和必要检查通过、留下具体未验证事项；新真实发送须沿实际剩余授权/预算，不把本轮“继续”扩成新付费批。Stage8E与默认发布准入不自动改变。

## 已完成与接续边界

2026-11-01 00:36北京时间，按用户“继续吧那就”完成现有opt-in产品审查的流式接收适配。产品合同1.7.1、transport natural-sol-product-stream-v1；完整业务messages/tools、high、强制submit_report_review及16384输出保持，仅wire.stream=true。默认legacy入口不切换，旧非流式合同与封存原件不改。

接收器允许输出前最多一次空created前导替换、该边界序号重置及单调序号间隙；done.name缺失时只从已绑定item取得名称。增量、done、item_done和terminal工具参数仍逐字一致，输出后身份切换/明确字段冲突/终态缺失/EOF失败均拒收。保存有界白名单事件字段与哈希，不保存私有reasoning；拒收、取消和关闭故障仍保留known usage。普通resume不自动重试格式故障。

验证共235项通过：SDK接收/旧协议/进程监管197，产品完整链17，产品流式格式/取消6，真实临时Postgres与浏览器10，原15库存及旧候选回归5。修正诊断工具wire指纹后，相关25项再次通过（不重复计数）。外部模型与来源使用替身，真实SQL/API/Worker/Chromium按现有产品路径运行；临时容器已清理。本轮新付费请求0。11个当前Runtime入口一致，原15离线新库存仅component_fingerprints/program_sha256变化，其余字段和15例业务请求/政策/标签/预算完整保持；原15完成不撤销。

上次真实流式拒收仍是拒收：未捕获原逐事件字段，不能把本轮合成SSE兼容测试说成该次真实回放通过。新接收器尚未经新的真实上游流式验收。旧产品累计8HTTP/29323known/366910unknown预留/4retry及3次成功生成保持，未迁移旧DB/checkpoint、未发布新报告；Stage8E和默认准入不变。

下一行动：准备同一旧任务从1.7.0到1.7.1的受控继承与零发送预检，明确保留成功生成、失败回执和累计费用的映射，并形成具体追加token/活动时间方案后再续真实首审；原包只余5687tokens/75.719活动秒，不足本次审查。用户放开手动重试次数不等于清零或扩大旧预算。当前不启动付费请求或waiter。工作卡docs/plans/2026-11-01-product-stream-receiver.md，结果data/evaluation/results/sol_product_stream_receiver_20261101.json。
