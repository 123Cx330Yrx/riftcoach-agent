# 两次远端524后的自然任务续测准备

## 目标与决定

用户要求先准备到单命令/隐藏Key输入，等上游恢复再实测，并明确允许增加必要预算。
两个524都是远端在约128秒返回，早于本地300秒截止；没有业务审查结果，不归为语义失败。
原报告、两次生成与三次检索可复用；保留已封存失败和unknown，不重开旧执行目录。
事实入口：`data/evaluation/results/sol_natural_timeout_observed_20261022.json`。

## 数据与控制流

新Operator递归只读核两层父seal与原stdout信任根，导入五个成功操作，
继承累计5HTTP/52067已知tokens/145824未知预留/重试1/472.672活动秒。
实际应用在同一报告、同一facts-initial请求前暂停，禁止任何新增生成。
后续仍为facts-initial、completion-initial、Host compatibility/edit、唯一逐字应用、双fresh；
双初审pass仍直接结束，不能记作修订成功。完整来源、真实作者和原生final约束保持。

累计预算扩为10次/739840tokens/2400活动秒/重试2；历史已用5次及1重试，
所以新增最多5次Sol/401920tokens，可容四次审查和一次明确已回收的超时重试。
新增估价0.29184元，使用GPT-pro输入0.4/输出2元每百万tokens，非账单硬限。
候选合同版本1.6.2；预算增加不证明远端524已恢复，不改变产品GLM/五调用或资格标准。
任何后续调整根据真实证据和用户现有授权处理，不把传输失败当整稿作废。

## 准备与启动

实现回归通过后冻结新执行树；原两个执行树、封存、授权和截止全部只读。
新树实际prepare和原生行政预检证明路径/作者原件/check-answer/final/导入可用，
不能作为业务质量证明。精确HEAD公共CI必须全绿后才读取Key；查询失败不冒称CI失败。

Control入口只在用户手动运行时激活本次新scope的24小时授权，不提前消耗等待上游的有效期。
已激活grant不自动续期。启动前核源码、父seal、真实native及CI，随后只提示天机阁Key。
默认检查模式不激活授权、不读Key、不发送模型请求；无后台健康探针/automation。
每次启动原stdout和exit摘要create-only保存，恢复仅用这些日志中最初guard与最新checkpoint；
已闭/未完成intent/未审任务由原session拒发或暂停，不删除结果后盲重跑。

最终操作路径、plan/源码/预检SHA、回归结论和命令记录于本轮preparation result及Control。
当前是准备工作；业务质量、同版本15、自然Coach/Training、四块联动/前端/Memory、
身份运维、两树整合、独立评估和学习均未完成。automation保持PAUSED。
