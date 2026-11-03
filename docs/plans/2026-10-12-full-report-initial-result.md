# 三篇完整报告初评诊断关闭结果

## 结论

2026-10-12 本批首次执行在首项 TCP 建连阶段超时，按原规则停止整批；没有模型输出或语义结果，后两篇未发送。没有重试、补发、编辑、fresh 或新资格，自动任务已暂停。

执行冻结 HEAD `6265e14d458f0b060b9f188f97fdee3e56acec17`，同 HEAD CI `38226883176` 全绿后首次启动。plan SHA `66dcb5d0f9a1fe43b8cf38442f34da9e4a13e17213fbd3414c2982eba608ee0a`；授权为最多3次 GLM 初评、Flash0、290304 tokens、1800活动秒/86400 Host秒，保守估价4.288512元并非硬计费封顶。授权原24小时时限及失败停止边界未改。

唯一 runner PID125600 于 UTC09:34:29.624 启动，09:35:00.632 exit1；waiter与runner均已退出。执行期间源码/HEAD保持，未启动第二份。

## 实际计数与最早偏离

| 项目 | 结果 |
|---|---|
| report-V2:initial | 一次客户端请求尝试，TCP建连失败，尚无stream事件 |
| report-H5:initial、report-S8:initial | 未发送，不沿旧余量补发 |
| attempted / HTTP hook | 1 / 1；request hook在TCP连接前计数，不证明服务器收到正文或计费 |
| known / unknown / receiptless | 0 tokens / 1 call / 1 call；实际费用未知，unknown预留96768 tokens |
| completed / native / submit | 0 / 0 / 0；无stage、checkpoint或独立派发 |
| 活动 / Host / wall | 24.875 / 0 / 24.875秒 |
| 新资格 | 0 |

最早可证偏离：`ProviderResponseError`、phase=`transport`；worker `timeout`，最后事件 `connection.connect_tcp.failed`。progress elapsed24297ms、open22610ms、events0、content/reasoning0，无HTTP状态码、usage或模型终答。因此不是600秒审查总时限耗尽，也没有401/429/503、额度不足或语义失败的证据。不能把known0解释成实际免费。

## 路由检查与根因边界

关闭后 UTC09:36:42 做一次不发送HTTP、不带凭据、不调用模型的DNS/TCP/TLS检查：`open.bigmodel.cn` 解析为 `198.18.0.120`，TCP/TLSv1.3在0.187秒内成功。Windows只读路由显示该地址经过 `iKuuuVPN` 虚拟网卡（198.18.0.0/16）。

程序的 `direct` 只清除进程代理环境，不会绕开系统VPN/TUN。用户随后说明曾为连接浏览器扩展启用虚拟网卡，这与观测到的路由相容；仍不能证明它导致了历史超时。事后检查未复现故障，也不证明持续可用；没有修改用户代理配置或据此重发本批。

## 封存与不变性

统一入口严格只读 replay 成功，native_reviews=0（无已审stage），create-only 白名单封存13份公开JSON、核14份run原件SHA，原件未改。

- seal：`data/evaluation/results/document_full_report_initial_result_20261012.json`，SHA `47da76c94f4688e62ff4687bd018abe455139f5dc50723ebc7a6f033ccdbcce3`。
- close audit：`data/evaluation/results/document_full_report_initial_close_audit_20261012.json`，SHA `eceb3b8ee71b85ad7cd49b4eb8475b46541a5fc288dc0804181952a3c1f4b023`。
- 冻结源码摘要与旧修正温度批146份原件SHA保持；旧strict seal缺口不补。授权前execution-target快照不覆盖实际authorization与启动记录。

本次仅补证据与状态，复用准备阶段51项离线检查；收尾核原件/索引字节、治理和diff，不新增模型请求或伪造业务证据。执行CI已全绿，收尾提交CI另算。

## 后续决策

先以不调用模型的网络证据区分TUN接管、分流与连接稳定性，再确定具体后续路径；本批不重开或沿剩余两次补发。没有语义结果，不据此调整教学、温度或600秒时限。任何后续付费范围须另有明确覆盖。

旧历史2/15、3/15、remaining11、完整15分段及教学对照各自保留，不能拼资格；正式同版本15、自然消费、8E以及Coach/Training、四块联动、Worker/DB/API/UI/journal、前端审美头像、Memory、身份运维、两树整合、独立评估和八维学习仍按既有依赖推进。

## 用户切回系统代理后的检查

UTC09:44:31 用户明确已切回系统代理后，再做一次无HTTP、无凭据的连接检查：解析地址变为`8.133.182.104`/`47.102.128.206`，选择首地址一次连接，TCP/TLSv1.3成功（0.125秒）；Windows路由为普通WLAN默认网关，不再经过iKuuuVPN。未修改配置，也未新增模型请求。后续证据另存`data/evaluation/results/document_full_report_route_followup_20261012.json`，不改先前seal或close audit。

当前连接路径已经变化；一次成功不证明持续稳定、鉴权或模型API可用，也不能倒推历史超时的唯一原因。下一步可以据此准备明确范围的后续诊断方案；本批保持关闭，不能当作未执行而重开。
