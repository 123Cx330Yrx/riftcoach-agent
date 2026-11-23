# Training与Coach记忆的同对象消费修复

2026-10-09；基线7f97d21c。目标是在已有self Training采用/版本/进度合同内修复可复现的
跨消费者不一致，不改变语义资格或前端产品设计。

## 两个实际反例与修法

1. 同一指标的两个active进度事件observed_at、created_at完全相同。Training查询按
   progress_id降序选第一条，Memory读取原来按升序选第一条。独立真库反例中页面选UUID
   尾号2/值1.0，Coach记忆却选尾号1/值2.0；插入顺序与编号顺序相反，不能用插入先后解释。
2. Memory读取先选择active Plan A并投影，再重新选择active Plan给Progress查询。
   READ COMMITTED允许另一真实Candidate事务在两次SELECT间提交Plan B与B的进度；
   原实现返回A的计划和B的进度。真库红灯确实落在plan_id配对断言，不是迁移或连接失败。

app/persistence/memory_context_repository.py现在一次选择active Plan，Plan投影及Progress
查询共用该对象/plan_id；无Plan时两者都为空。事件排序统一为observed_at DESC、created_at
DESC、progress_id DESC，与Training查询一致。仍只读，不加锁、不增加隔离级别、写入口或Provider。
owner/relationship/subject/self/可见性约束保留，observed仍无self Plan/Progress。

保证的是本次训练投影的计划与进度绑定一致。读取期间换计划后，本次可以返回一致的A，
后续读取返回B；不保证整个Memory在READ COMMITTED下具备同一时点快照，不称为最新实时数据。
UUID仅是时间并列时的既有稳定裁决，不能赋予它测量先后或效果因果含义。

## 验证与开发复核

新增公共测试复用实际Candidate/materializer/终态Task夹具与真实PostgreSQL，未读本机旧run。
Task/Artifact数值与摘要是公共合成夹具，不是用户比赛或模型质量证据。

- 修前两新增案例：2 failed，4.17秒；分别在UUID选择和Plan/Progress绑定断言失败。
- 修后Memory/Training真库：8 passed，9.17秒。再补“初次无Plan、读取中激活”参数边界后，
  最终9 passed，9.99秒，含3新增案例及6既有查询/写入/纠错/版本/身份检查。
- 修后Memory-aware context/models/runtime-binding/manifest：13 passed，1.70秒。
- 修前Training/models/materializers/service/API及Memory/models/runtime-binding基线47 passed；
  独立审查另实测34项纯/Runtime检查，存在重叠，不相加为唯一测试数。
- 新测试仍在tests/test_memory_context_repository_postgres.py，既有公共Postgres job明确执行此文件。

现有Sol主体独立精确SHA复核无阻断缺陷；实读completed/error=null/唯一native final，
不是业务StageAssessment、旧意见重签或模型质量认证。事件：
01a11fea-dc3d-72d0-a07e-90fde8f04f92/01a1207e-e597-7871-9aed-e0695356e8ac/msg_03d7b027593b6423016ac8d4e4d3cc81958c7e633699cd6f44。
源码SHA a308af0ff4c2c1812c9a25e96146e8399cd2d76eaf3f65e75e8f978e953e71c3，测试SHA
e9400d00f01f127ca20642ee11d318e02559abe44f16d42b017556cdd51a4987。
审查实读红灯并核两处修法及边界，只跑纯检查，没有独立重跑真库绿灯。

只读开发证据保存在operator outputs/riftcoach-training-context-20261009：

| 文件 | SHA256 |
|---|---|
| red.log | b33ed68500ca3c561b28b19029bac25684989848d2ae16c67662b77f5e703077 |
| green-final.log | 14d6305adaa6b4ad4a09b51828287ff94df0c3f9d884904a5e828a513d5d9e5e |
| independent-memory-context-review.native.json | 8e5136c6559091dc026d32bd9d3bd1b8a74f2dd8ca064a77e7952633b6165e89 |

复现使用独立、可销毁test DB的RIFTCOACH_TEST_DATABASE_URL，运行上述两份Postgres测试。
现有迁移helper会downgrade base/upgrade head，不可指向业务数据库。

## 本机数据库恢复与清理

Docker启动实际遇到sailor-ingest.sock及docker-secrets-engine/engine.sock残留错误。
沿已有恢复方法官方stop --force，验证进程退出和绝对目录、非链接/备份不存在后，原目录
移动留存并新建运行目录。备份在AppData/Local下：Docker/run.backup-training-context-20261009、
Docker/run.backup-training-context-20261009-final及
docker-secrets-engine.backup-training-context-20261009-final；没有删除原文件或数据卷。
用既有本地override启动仅postgres服务，仍127.0.0.1:15432，复用原命名卷。
新建专用riftcoach_training_context_20261009_7f97d21c，仅其承受测试迁移；结束后已删除。
原riftcoach库只读核迁移head仍0014_message_projection_status。未启动API/模型Worker或改共享.env。

## 保留的业务缺口与下一动作

已有Plan是用户结构化Candidate→明确accept→同事务物化/版本替换；不是模型建议自动落库。
Progress是服务器deterministic_run_fact Candidate，终态task/run/final Artifact与metric allowlist
由writer核验；公开POST固定user_structured_input，不能由客户端补deterministic来源。
查询/记忆路径的修复不证明服务器已自动生产真实Progress或自然反馈闭环。

下一免费动作追踪实际Progress创建者和已批准指标映射，确定从完整复盘到Candidate的生产
路径与缺口；已有缺陷直接修，不擅自加写路由、将主观反馈当测量或替observed创建self。
四块Review/Coach/Training/Evidence交互与视觉仍按后续设计核，不修改主树前端。
本轮Provider0、新资格0；原两处分歧、正式同版本15/当前组合自然消费/8E，以及身份运维、
Memory、前端审美/头像、两树整合和八维学习保留。修复不绕过这些依赖或重开关闭批。
