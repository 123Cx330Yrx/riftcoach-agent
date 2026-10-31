# 原15文件交接故障与修复

## 事实与首次偏离

f1b84486 / CI36254196777公共三项成功后，按冻结原15计划执行。
首例claim-scope:1真实GLM为95/pass，issues/advisories/resolutions全空，正确原稿未改。
主审与独立审查均按全文与完整来源接受；在释放下一例之前，本地校验报
`task_observation_host_binding`，批次停止。不是误报、断流、token耗尽或host超时。

内存候选identity与落盘后读回的identity全值相等，但JSON保存排序了顶层及contract键。
原主审临时工具使用`digest(compact(saved_identity))`得到96ad5b29…ca26b8；
执行器使用原builder序列得到e8ef5843…a33b894。对保存plan验原decision通过，
对执行器内存plan验同一decision失败；这是可离线区分和复现的根因。
原离线整链夹具直接用内存plan生成主审摘要，未覆盖真实文件交接，是验证缺口。

33份原件及公开投影封存`golden_coarse_qualification_result_v1.json`，SHA
8c534f0ec68624517ef71feb081be4cc29cb0beb758579757daa37db28311b6e。
1请求11721输入+1212输出=12933tokens，未知0，含host137秒；未缓存估价0.127704元非账单。
没有task-observation/case-completed；模型单次正确不等于该例取得严格完成资格。
旧目录、错误decision、失败result均不改，不恢复旧时钟，不给它补完成记录。

## 修法、影响与验证

新增共享身份绑定：对保存identity与明确profile的既定builder产物作严格全值/类型比较，
再按builder原顺序求摘要。Observer、StrictObserver、CoarseObserver及live handoff统一消费。
不全局改compact，不接受旧错误摘要为兼容别名，不改变产品候选、请求、模型、提示或业务标准。
task outcome和封存审计已有的当场builder摘要保持一致，历史原摘要不迁移。

主审工具纳入版本库`scripts.write_role_stage_decision`，只消费主审明确写出的判断；
先校候选身份与主审结构，再写primary，最后写decision。运行器收到decision后仍核
完整主审/独立来源、阶段、请求、报告与回执绑定，全部通过才允许下一次Provider。
独立审查不被复制成主审。封存时应使用执行器完整账目，而不是拿基础tokens摘要等同完整账目。

整15夹具改走真实文件writer；另测独立Python进程读保存plan、嵌套键排序、身份/版本篡改、
旧摘要拒绝、独立来源/阶段hash破坏仍停在首请求、关闭批不可重启和历史预览固定。
修复过程曾把要求decision已存在的封存检查提前到writer写decision之前，离线即失败；
已撤销这个循环，完整审查继续由既有运行器在下一请求前完成，不为此发付费探针。

最终相关111项通过（283.72秒），后补独立来源/阶段绑定负例2项通过；治理通过。
独立代码审查确认旧错误摘要仍拒绝、原builder摘要不变，未放松阶段双审。

## 后继执行

修复验证及干净同HEAD公共三项成功后，明确选择`--file-handoff-repair`新批。
冻结`golden_coarse_file_handoff_preparation_v1.json`，摘要
fdec7a2fcc4a5028efd694fb651f8cb89f75799fe8bbb0fc6c62d39c48dcbc6c。
同产品identity、同15原始请求/标签、同35调用/3386880tokens/10500秒预算；
保守全GLM未缓存预留50.03264元，不是账单。旧1请求费用另记，继承完成例数为0。
这次重新验证由已复现并修复的工程故障驱动，不因模型分数变化创建提示变体。
首实质失败仍停批；全15取得资格后才验证自然Agent生成/工具/纠错和真实DB/API/UI消费。
8E仍未完成，Coach/Review/Training/Evidence、审美/头像、Memory等原后续不取消。
