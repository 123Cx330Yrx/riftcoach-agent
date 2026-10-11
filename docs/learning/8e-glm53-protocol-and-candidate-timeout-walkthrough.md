# 8E 学习材料：Flash 基础协议与候选 8192 超时的证据拆分

## 要解决的问题

“API 能返回一次结构化结果”与“最大思考档能在 Agent/工具链中完整结束”是两个不同
问题。前者只需要固定协议门，后者还涉及输出预算、思考内容、流终态、Usage 尾帧和
取消边界。把它们合并会让一次小样本成功或失败被误读成产品成熟度。

## 关键原则

评测必须绑定实现 SHA、请求档案和不可变回执；每一次真实调用先过精确预算，失败只保留
安全机器码。候选 profile 可以扩大实验上限，但 `activation_state=candidate` 与
`execution_allowed=false` 必须继续阻止它通过元数据悄悄进入产品 Runtime。

## 本批数据流

G53-3 读取普通 API 配置，按 A1 结构化合同、A2 Agent 工具往返顺序运行 3 次，输出
body-free 协议回执。候选诊断读取冻结的单案例 Context，开启显式中立流适配器，最多
观察一个 8192/90 秒 primary；诊断层在墙钟到点时先关闭会话并结算安全的
`elapsed_limit`，不创建第二个请求。两条路径的正文和 reasoning 只在进程内短暂存在。

## 证据与验证

最新实现的 G53-3 为 3/3 通过；候选 8192 观察为 1/1、90 秒超时、无 recovery。回执
分别绑定 `aa22cea…/4b6cd58…` 和 `4b6cd58…/3f35d15…`，均没有 Key、Prompt、正文
或 request ID。应把“协议可达”记录为已证实，把“完整长思考终态”记录为未证实。

## 后续工程动作

先在本地 fake/fixture 中把思考档位、流终态与 Usage 缺失分开，再决定是否需要新的候选
域门。产品默认、Workbench、Portal、Account、Auth、`capabilities.streaming` 和
`production_media=0` 不因本批变化。面试表述可以说：我用独立身份和预算把 transport、
协议、生成完成度分层，避免把一个 timeout 误报成账号不可用或模型整体不可用。
