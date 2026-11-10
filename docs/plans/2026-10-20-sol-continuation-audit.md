# 断续推进审计与工程修复

## 结论与起点

本轮按用户要求核查限流、重启和多次续接后的真实状态。起点为诊断树
`cca038f3ab094977f154c76c756b041a2180aae3`，不是新的付费批。原批五项与单独第六项补测
的语义证据保持；当前尚无混合自然任务的付费执行入口或跨进程恢复完成证明。

该HEAD公共CI `39221139700` 实为failure：web/packaging成功，四pytest分片和Postgres失败，
首个相关偏离是当前profile的组件指纹漂移。不能继续沿用此前“本地测试已过”作为此HEAD全绿证据。

## 发现与处理

1. **遗漏清单更新。** 共享源码变更后role/coarse/correction清单未同步，boundary修复留在工作区。
   本轮仅刷新实际受影响的role/coarse/correction/boundary/natural/sol六份当前清单；
   未更新旧封存结果、原批身份或预期答案。所有profile仍用实际resolver验算。
2. **监督超时可能覆盖硬错误。** worker已写结构/身份拒绝或完整结果，随后挂起，父进程只见deadline。
   现在先核worker code和response_contract；硬拒绝及完整响应均不重发。HTTP200且EOF完成后
   即使SDK解析/关闭卡住、尚无worker-result，也不能误称传输超时再次发送。缺失、空、坏JSON或
   非允许阶段的观测不能作为重试依据；有真实有效观测的明确超时仍保留同阶段一次共享重试。
3. **失败账目与Trace不一致。** 合法失败用量原先可结算预算却不进Trace。新增明确的失败用量事件，
   仍是Failure而非Completed；Trace、费用估价及验收消费一致，旧事件格式保持。验收成功数量只数
   Completed，不能因失败有用量便算一次成功响应。
4. **actual-model归属缺口。** transport先保存usage再拒绝model_identity，receipt的known不足以
   把数字归给Sol。新验证共用于Trace和预算，核原库存、receipt SHA、profile、HTTP/EOF、
   response_received/model_matches及worker/checkpoint一致性。错误模型原receipt数字保留，
   Sol账本维持未知预留；这是通道自报身份的匹配，不认证真实上游厂商或模型。
5. **Windows换行。** 历史golden_coarse_file_handoff结果的工作副本仅CRLF转换，Git原始LF字节
   符合原摘要。恢复原Git字节并设置精确LF属性；原摘要
   `d509d516f40739963ed9ac11679fea757ccd83a902e049cefb5e4110c947b69e`不改。
6. **Docker重启复发。** sailor-ingest.sock残留导致启动失败。停止Desktop后备份两运行目录再重建，
   原容器/卷和15432保留；Docker29.7.2、healthy、只读SELECT1和迁移0014核实。
   这是本机可逆恢复，未证明永久根治。

## 验证与无效检查区分

- 172项清单/资格/检索/候选/失败用量回归通过，838.67秒。源码在该轮运行期间冻结。
- 身份绑定最终25项候选真实子进程回归通过，154.90秒。
- 共享Runtime与实际验收消费130项通过，15.55秒。
- 缺观测修复后，超时/deadline/HTTP/预算17项通过，71.29秒。追加200/EOF边界后，原17项仍通过；
  新SDK反例修正启动时间及ByteStream替身后，五个观测分支最终14.98秒通过。
- 38份profile实际resolver全部通过；最后Sol独有守卫改动后再核该profile通过，其他37份无变更。
- 独立临时Postgres中SQL/Worker/API四组16项通过、无skip，39.73秒；产品DB未迁移或写入。
  临时容器与tmpfs已清理，原容器前后healthy。该检查验证共享Runtime消费，不是Sol新组合DB资格。
- 早先100pass/40fail那轮受到运行中源码修改和CRLF干扰，已由稳定源码回归替代。
  本轮一次清单刷新命令的字符串转义错误引发23项fingerprint失败，刷新成功后25项全过；
  另一次错误测试路径导致0项执行，随后按真实路径130项全过。新SDK反例先因1秒截止早于启动、
  后因content预读替身未走字节观察器失败，改成5秒及真实ByteStream后通过。这些初次失败不算通过。

机器可读证据、原测试报告路径与SHA见
`data/evaluation/results/sol_continuation_audit_20261020.json`。测试均断网替身；
没有新增真实模型请求、没有读取密钥、不延展旧费用授权。

## 已完成与仍未完成

已完成：当前候选同进程有限超时恢复、失败保留/计量、动态请求/逐字修订/同稿fresh离线链路；
本轮补齐上述工程缺陷、当前清单和真实共享数据库消费回归。

仍未完成：候选专用持久执行入口、重启恢复、真实独立审查接线、最终准备包及其精确HEAD全绿CI。
旧runner拒绝existing claim且finally写closure，不能直接冒充恢复入口。

下一实施采用现有Runtime与候选专用持久session：保存真实工具结果、模型原件与请求身份，
从经校验的历史回执纯本地重演到最新边界，只允许后续新调用产生IO。原transport/journal/application
保持只读，派生重演工件单列；历史调用数、known/unknown预留、活动时间和唯一共享重试一并恢复。
完整可信响应落盘但业务阶段未提交时读取旧响应，不重买；application存在只核对复用，不再应用。
不明在途/旧进程未确认退出、身份或SHA漂移、硬错、terminal/seal存在均不重开。
该段是待实现设计，不是恢复功能已完成。

旧封存、同版本15、自然Coach/Training、四块联动、前端头像审美、Memory、身份运维、两树整合、
独立评估与学习要求保持。当前8E、GLM产品采用和五调用产品合同不变，automation仍PAUSED。
