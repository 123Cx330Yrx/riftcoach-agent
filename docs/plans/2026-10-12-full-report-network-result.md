# 系统代理切换后三稿诊断关闭结果

## 结论

2026-10-12本批首项模型请求正常完成，但独立主体在读取checkpoint前使用了不存在的
`D:/riftcoach-agent-rq192-pr/backend`工作目录，命令启动失败（OS error267），随后发出
唯一原生`routing_failed`终答。按已授权硬故障规则停整批；没有再次派审或补签。
这次是Host交接执行失败，不是网络、模型质量、401/429/503或额度问题。

冻结HEAD `11d1f9e0a1bc6eccfb370e2029db0cd8e7849758`，同HEAD CI `38232745159`全绿；
plan SHA `fb573b77b24b882ef917569781a7bb0c5d616cceb2a10c28da6eda4453758c6a`。
唯一runner117012于UTC10:29:16.289启动，10:33:11.599 exit1，waiter及runner均已退出。
运行期间源码/HEAD保持，未启动第二份。

## 实际结果与费用边界

| 项目 | 实际证据 |
|---|---|
| V2初评 | 模型97/pass，issues空，advisory仅block4；有完整response/receipt |
| Host | 独立派发1；checkpoint未读、未完成全文审查、check-answer未执行；业务submit0 |
| H5、S8 | 未发送，未执行 |
| 调用/HTTP | 1/1 |
| 用量 | input13284/output2643/cached0，共15927 known tokens；unknown0/receiptless0 |
| 按合同价估算 | 0.180276元；不是账户账单，实际收费未核 |
| 活动/Host/wall | 42.735/185.437/228.172秒（展示到毫秒，原始值保留） |
| 新资格 | 0；V2未获双审认证，不计为通过案例 |

请求约6.781秒收到首事件，约40.141秒流结束。原先TCP连接失败没有在本次请求复现，
但一次正常模型响应不证明网络持续稳定，也不能追认上一批超时的根因。
前批unknown1、费用未知仍单列，不能用本批known计数覆盖。

主审在独立失败前已开始读取完整报告、policy、来源及实际输出；尚未完成全部审查，
未制作或提交合格主审意见。97/pass只是Provider原始结果，不作为事后补签。

## 原生失败与交接缺口

实际原生事件：
`01a12f0c-bb7c-74e3-ad92-775eefbe399a/01a12fab-8a7c-7a43-b4e4-01c8ed1af9f7/msg_0998f8ac4632b025016accb742556c8194891a1f56b5eb75d6`。
只读原生full turn核到一条commandExecution（错误cwd、processId=null、exitCode=-1、duration0）
及唯一失败final。没有读取或公开私有推理，不将失败JSON当作审查attestation导入。

交接给出了精确checkpoint与SHA，但仅用“backend repository”描述执行目录，未明确列出
绝对cwd和Python；独立主体由此作出了未经验证的`/backend`假设。责任属于开发交接与执行，
不能让用户再次改代理或把它归因模型API。

关闭后主审只做路径检查：使用`D:/riftcoach-agent-rq192-pr`和
`D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`读取同一checkpoint成功，SHA保持。
这是主审侧路径可用证据，不是独立主体恢复、全文审查或新业务提交。
项目AGENTS已补未来交接要求：明确验证后的绝对cwd/Python，原样转交dispatch，
禁止自行附加backend；身份预检不替代命令启动验证。未修改冻结helper或旧任务。

## 封存与后续

严格只读replay通过、native_reviews=0，create-only封存24份公开JSON/26份原件。

- seal：`data/evaluation/results/document_full_report_network_result_20261012.json`，
  SHA `746ae66a490fe211bb4fca3a305e329bcf9b94a70cc709c452ba1956a58ed086`。
- close audit：`data/evaluation/results/document_full_report_network_close_audit_20261012.json`，
  SHA `c29139af631580bc9be87610bfc6a74c85324b86fc0af947a82c2dd333403a10`。

26份本批、14份前批和146份旧温度批原件SHA不变，冻结源码摘要保持；旧strict seal缺口不补。
自动任务已暂停，无重试、补发、重评或新资格。本次收尾仅证据/规则/状态更新，使用相称的
原件/索引字节核验、治理和diff检查；准备阶段18项离线检查不冒充真实主体路径验证。

后续另做一次全新的中性routing-probe，未派回旧审查；结果如下。
下一动作是依据已证当前启动通路确定后续语义诊断范围；不再仅凭身份预检就开始付费；不派回这个
已终答的任务，不重开本批。保持原报告、来源、policy、教学和温度，不能据此改语义机制。
正式同版本15、自然消费、8E及既有产品/前端/Memory/身份/两树整合和学习依赖均未解除。

## 后续无项目模型调用的真实独立路径验证

明确目录后的真实独立中性探针已完成：同一主体以正确根目录/绝对Python执行5条公开命令（两次读同checkpoint、帮助、写自己的答案、check-answer），全部exit0；唯一native final与作者文件相同。新中性任务不含报告，Provider0/业务submit0/资格0，未派回旧审查。证据`data/evaluation/results/host_explicit_cwd_probe_20261012.json`，SHA `cf23819bb3add8c37c84eb4d6c3f2aba43b1f212841c832b0c2f5586fa4f994b`。这是当前启动通路证据，不保证未来可用或语义正确。
