# ADR 0122：任务创建时固定生成版本

Status: Implemented for explicit opt-in; SQL/CI verification and live wording acceptance are separate gates.

## 问题与选择

离线玩家口吻版本已能编译完整材料，但旧 Worker 到首次领取任务才固定执行合同。任务排队期间切换配置可能改变将要消费的生成规则，离线 context builder 也不能绕过 Runtime 对实际合同的校验。

采用任务创建事务中的私有 `generation_binding`，以及独立 Worker 合同 1.7.11。复用既有 Chat 双审、预算、Runtime、续接和发布流程；不新增模型调用或生成后的展示润色。仅改共享默认提示不能解决排队身份问题；复制整个审查协议则没有必要。

## 数据与控制流

API 的服务端 `RIFTCOACH_TASK_GENERATION_PROFILE=sol-dual-product-wording-v2` 显式选择新任务版本。Worker 使用对应的 `RIFTCOACH_WORKER_EXECUTION_PROFILE`。两项均不默认打开，客户端不能提交版本字段。服务组合固定合同快照及组件摘要，普通和 conversation 创建在各自原有事务中保存，重放原幂等键返回原任务与原绑定。

Worker 在读来源和发模型请求之前核对绑定，并在 `PostgresTaskContinuations.begin` 持有行锁和有效租约时复核，覆盖领取后到执行前的数据变化。每段续接继续绑定相同身份。旧 NULL 行保持旧 profile 行为；新 Worker 拒绝接管 NULL 行。版本/组件不匹配留下 `recovery_required` 与明确原因；首次拒绝没有虚构 session/checkpoint，不可拿它调用普通 checkpoint resume，恢复正确配置或处置任务需按其实际状态操作。已经建立 session 的任务继续走现有 owner resume，成功前缀不重发。

`0016_task_generation_binding` 为旧行添加 nullable JSONB，不迁移封存任务。downgrade 持表锁并拒绝丢弃任一非空绑定，在线与离线 SQL 使用相同保护。该迁移本轮没有应用到真实任务库。

## 生成与审查边界

`player_wording_worker.CONTRACT` 的 snapshot 版本为 1.7.11，Worker profile 独立；Chat 的请求业务身份与审查序列化仍复用 1.7.10。实际生成上下文使用新规则，原四审请求可逐字节比较。新 profile 的 Skill/Program 清单、Runtime 校验、trace 解析、budget 和 session 路由均显式登记。共享接线改变的当前组件清单同步刷新；原 15 个业务输入、报告和请求摘要不变。

## 验证与限制

`tests/test_generation_binding.py` 验证显式配置、精确绑定、可信上下文，以及实际 Runtime 的 pass/repair 暂停续接（模型和 HTTP 是替身）。`tests/test_generation_binding_postgres.py` 覆盖事务保存、幂等重放、owner 隔离、缺失/错误/漂移绑定、领取后竞态、普通 Worker 续接和迁移保护；`test_sol_product_entry_postgres.py` 增加普通与 conversation 的真实组合入口，新用例已加入 PostgreSQL CI 收集清单。

完整封存五场输入经正式 Worker 编译，与离线候选完全一致：32948 / 42388 / 46754。第三轮沿用历史前缀的预算总额 401892/401920，余 28；不推导新任务实际用量，不提高上限或删来源。原 Chat 四审字节摘要一致。真实新模型请求、真实 Key 读取、新对局来源和封存任务写入均为 0。

本机 Docker 本次正常启动后仍未响应引擎 API，SQL 执行不得以 collection 或旧 CI 代替。最终执行结果以本包结果记录及同提交 CI 为准。P3_not_accepted、Stage8E、默认准入及自然度待验状态保持。
