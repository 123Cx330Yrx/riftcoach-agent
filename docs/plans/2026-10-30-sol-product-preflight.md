# 产品通路零付费预检与三次CI修复

2026-10-30，基线a000443d；用户要求核实最近三个CI并继续推进。沿用planning-with-files的canonical/活动计划/progress/findings，不启动新付费批。

## 目标与当前结果

修复CI实际失败，继续查普通观摩入口到持久Worker/Evidence的真实接缝。工程修复及API/真库预检完成；远端新HEAD全套结果和浏览器预检尚待完成。

40996162649现已结束：shard1/2分别在两份OpenAPI精确路径集合漏登记continuation、resume，其余实际jobs通过；汇总job随失败分片失败。40998305806已见同一shard2错误，其他分片在最近查询仍运行。41000871576的Postgres为249通过6失败：correction-scope构造在模型发送前发现4个共享源码指纹漂移；它的分片最近查询仍运行。不是三个全套都停止不动，也不是本机挪动造成。

## 实施

- 保留两份精确API集合并补齐真实接口。四个当前role/coarse/correction/boundary清单只刷新组件/程序SHA，其他字段与政策保持；旧封存清单不改。真实11个默认/命名Runtime消费入口可零Provider启动，CI提前执行同一检查。
- PostgreSQL job纳入上一包遗漏的8个续接、7个产品合同检查及本包2个普通入口检查。原job10分钟包括安装和迁移；扩展覆盖后调度上限20分钟，业务预算/请求超时不变。所有pytest使用短trace且不输出捕获正文。
- API配置新增`RIFTCOACH_TASK_PUBLICATION_MODE=legacy|evidence_bound_v1`，默认legacy。两条创建接口写入所选模式；客户端不能在body覆盖它。模型选择仍独立由Worker显式`sol-dual-product-v1`控制，不切默认。
- 普通观摩会话预检发现Evidence重建使用新当前时间，bundle摘要漂移改变模型输入，因而恢复拒绝。现在首次完整projection随session保存并重放，保留原时间和真实材料；逐字节验证恢复前后deterministic input一致。Evidence adapter为2，旧adapter-1续接不被静默重解释；legacy adapter保持1，本轮没有迁移真实旧任务。

## 验证与证据

- 11个默认/当前Runtime消费入口启动校验通过，无Provider构造。
- 36项Runtime/原API定向检查、61项API/组合/会话检查通过，两组重叠1项。
- 原6个取消围栏加8个续接与7个产品检查，共21项临时Postgres通过（239.70秒）。修复Evidence投影后，原Evidence提交项1次复核通过。
- 2个新普通HTTP入口真库检查通过（41.67秒），覆盖服务端模式、观摩身份/Memory、暂停重启、成功前缀不重发、owner/非owner读取、报告/Evidence/累计用量和唯一会话回复，观摩不写本人训练进度。
- 新入口首轮1通过1失败；原因证据保留。补充诊断后修复投影，随后一次测试代码误用messages而非既有items分页字段，已改正并通过。一次临时容器同名保护在创建前阻止并行冲突，无数据库操作；等待原容器移除后使用新临时库。
- 外部模型/Riot均为替身，真实模型请求/真实凭据读取0；产品库未迁移。容器均删除，Docker恢复停止。旧15不重跑。
- 机器结果：`data/evaluation/results/sol_product_preflight_ci_repair_20261030.json`。原日志和诊断：`C:/Users/33502/Documents/Agent/outputs/riftcoach-product-preflight-20261030`。其中早期runtime-manifest-source-drift.json使用repo根解析profile Skill路径，产生非权威误报；以真实组件函数及resolver通过为准，未按该粗略清单批量刷新历史profile。

## 下一步与边界

跟进修复提交的新CI；继续本地浏览器零付费预检、实际观摩账号/近期来源准备，再冻结一条代表性通路的执行清单。此次不把API TestClient/临时真库检查称为浏览器整链或真实模型质量，不复用旧批次授权、不扩大付费批、不改产品默认或主树前端。Stage8E仍in_progress，automation保持PAUSED。

## 0add355f远端结果与快照补修

CI41003259222的web、packaging、Postgres和shard2已通过；shard3为1911通过/1失败/55跳过，其他两分片仍在运行。失败为natural_duty当前离线库存测试仍指向20261029快照；上轮未覆盖这层检查。

新增natural_duty_qualification_inventory_product_contract_20261030.json，旧快照不改；仅组件/程序摘要变化，20个其他字段、15例、30份原始请求保持。源码差异来自已实现产品合同涉及的4个共享文件。本轮仅维护当前快照/引用和CI早期检查，不再改产品实现。6项GLM库存、当前Sol库存、两份API路径集合统一提前执行，完整分片仍保留。

本次9项禁网检查全部通过（36.30秒）；不重跑已通过且输入未变的数据库/前端检查。新提交CI仍须读真实结果。
