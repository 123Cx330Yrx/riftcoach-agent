# 新v2完整原15验证准备（2026-09-30）

## 当前结果和证据

用户在指定起点审查完成后已要求恢复推进。修补提交5fd44a1d的公共CI36670205715
三项成功。新增正式入口复用既有执行器，不改变模型/high、1.5.5政策或全文上下文
验收标准，也不把工程样例或历史1/15拼成新资格。本记录不是付费授权或质量通过。

- 入口：scripts/run_boundary_examples_v2.py；preview不连接宿主、不读取凭据、不发Provider。
- 冻结计划：data/evaluation/results/golden_boundary_examples_independent_v2_preparation_20260930.json。
- canonical SHA：03c80ae504c5e8f7fac4dbe76188f79d503776720bdfdecde8ca7e26c384640e。
- 运行目录：data/runs/role_task_observation/boundary-examples-independent-v2-20260930；尚未创建。
- primary/root：01a0c6c5-01d1-78d0-82fb-e567e0ab7150。独立child：01a0f093-d441-7fe2-9c68-99187920339c。实际原生父子关系已读取核实。
- 全部15个原请求重建并逐一核对摘要；18项执行/审查/计时源码摘要进入plan，执行前再次重建精确比较。
- 47项相关测试通过，含离线完整15执行器回归；独立代码复核accepted=true，十个所读源码摘要回查一致。
- 本机证据目录：C:/Users/33502/Documents/Agent/outputs/riftcoach-v2-preparation-2026-09-30。
  关键文件：v2-entry-tests.xml、independent-entry-review.json、native-lineage-preflight.json、
  prepared-request-manifest.json、budget-reconciliation.json。测试和审查不授模型资格。
- 新入口必须通过包含它的最终提交公共CI三项检查，不能借5fd44a1d的旧检查。

## 新批和累计预算

新批最多35次Provider调用：GLM-5.3审查25次、Flash编辑10次；3,386,880 tokens；
模型/执行活动预算10,500秒。开发宿主审查等待单列最多86,400秒，不增加调用或tokens；
进程重启不能重置时钟。按既有合同未缓存单价保守预留37.167104元，不是账单或硬计费
封顶。产品每任务5调用/401920tokens/900秒不变。

最近三个1.5.5原15尝试合计8次已发/预留请求，其中7完整、1 unknown/incomplete；
known tokens为105614，已知用量未缓存估价1.079228元。新批后该系列最多43次，
known+旧未知保守预留+新tokens上限为3569188；已知费用加新预留38.246332元，
另有旧unknown实际费用待核，不能记为零。这不是全项目历史费用，不包括Codex额度。
原始失败审计和更正均保留；所有旧批次不重开、不补签、不借用旧授权。

## 执行与失败处理

1. 新plan取得具体付费授权且当前干净HEAD公共三项检查成功后才执行。原生父子身份先核实，之后才进入既有执行器和凭据加载。主树现有.env路径存在；准备阶段未读取密钥。
2. 使用一个隐藏且输出持久化的原进程；每例发请求前只写与实际ready-required摘要对应的即时信号，不预写下一例ready。
3. 每个initial/revision/final阶段派发包含实际六字段binding的独立任务。只导入宿主completed最终结果；主Agent自行核对来源与纠错，再正式提交。线程存在不等于审查通过。
4. 无final的429/402、加密或缺失派发、绑定错误不能伪造通过；GLM语义错误与开发协作中断分开。原进程仍活且时限内可继续当前宿主工作；已终止批次不得重开或补签。
5. 首个实质、身份、来源、传输或预算失败即停；不重试、不换提示、模型或评分标准，不暗开新批。封存完整回执、未知用量及最早分歧。
6. 全15通过后才用同一v2事件来源完成严格封存回读和资格判定。之后还有自然Agent生成/工具/纠错及真实Worker/DB/API/Workbench消费，不因此宣告8E完成。

旧真实工程交接不重复。未来宿主可用性无法由本次检查保证，每项真实事件仍重新核验。
四块联动、本人Training、前端审美/必要重做/英雄头像、Memory、身份运维、两树整合和学习仍在原路线内。

## 本轮执行记录的限制

本轮两次本地文档生成命令在解析阶段因嵌套换行失败，没有写入，也未发Provider；
随后改用明确文件补丁和独立数据生成步骤完成。测试筛选范围比原拟定宽，最终实际
完成47项且保留JUnit，不另跑同一长套件。子审查自行启动的重复测试无终态，不计通过数。
