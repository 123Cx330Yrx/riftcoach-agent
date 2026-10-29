# 自然任务候选的协调与恢复入口

适用入口：`python -m scripts.sol_natural_launch`。这是显式开发候选，仍拒绝发布；不注册默认Worker/API，不授模型或产品资格。

## 当前候选

`prepare --candidate dual-necessity`选择`sol_review_contract`，使用同一Application、Runtime、持久化session及原生双审gate。它支持动态自然任务，和固定报告评估使用同一审查政策；准备不读取Key或发送请求。

原`baseline`和`necessity`选择不变。计划固定实际HEAD、源码、合同、请求、分组和预算；原历史计划/冻结目录不在新源码下改签。新入口不自动导入其他合同的封存任务。

## 观摩标题与内容边界

第6节支持`## 6. 训练计划`及`## 6. 观摩练习计划`，按同一结构身份消费，不改写模型原补丁或报告字节。实际Markdown标题、必需章节、顺序/重复、围栏/行内伪装、来源与保留校验仍有效。来源插槽原型与Memory探针复用章节识别；实际自然任务不经过该插槽原型。

该兼容只解决本地标题误拒绝，不能裁定用户用途、个人训练基线或语义质量。2026-10-29真实原补丁strict preview通过，18段及来源节保持；后续单独的同稿双fresh已完成、双审接受并封存，见`data/evaluation/results/retained_report_fresh_completed_20261029.json`。原完成度漏检、拒绝及原正式application缺口仍保留；单独fresh不是原任务的正式应用。不为标题兼容重测旧15或重买生成/事实初审。

## 保留事实初审的显式诊断续接

新增的是独立计划模式，不是重开旧seal或普通`--manual-retry`。先运行零发送的`python -m scripts.prepare_natural_completion_frontier`，提供原Operator、seal SHA及已保存的拒绝结果。它用原冻结Runtime和当前Runtime回放，重新读取原事实作者/native，停在完全相同的completion请求前；只在scratch里给最后成功的事实响应携带全部后续费用，不改变早先524与手动恢复的账目。

新计划使用现有`python -m scripts.sol_natural_launch prepare --candidate dual-necessity`，增加`--completion-proof <frozen-prefix-proof.json> --completion-proof-sha <SHA>`；run-id和双审主体必须与原任务相同，Operator必须独立且新建。实际plan/guard/checkpoint、绝对cwd/Python和封存库存仍是唯一运行依据；本机最终引用见`C:/Users/33502/Documents/Agent/outputs/riftcoach-natural-completion-continuation-20261029-control/readiness.json`。

后半段仍走原Application、SessionBudget和SessionWorkflow：复用生成/工具/已接受facts → 新completion-initial → 必要时原补丁协调 → compatibility/edit双审 → 唯一application → 同稿双fresh。不会导入被拒completion意见；原事实handle只允许原作者/native回放，禁止重提交。新初审被语义拒绝即停止，不自动再建一轮直到通过。这是验证正式修订尾段的有界诊断，不是修好模型漏检的证明。

正常路径只需3个新逻辑请求，既有合同可留2次手动恢复：新增最多5次实际请求、401920 tokens，父链累计3600活动秒（继承约342秒），企业专线0.25×、gpt-6.1-sol/high，每次300秒/16384输出；保守包络估价0.36480元，非账单硬限。专门新授权还必须固定`new_logical_reviews=3`和`semantic_retry_not_quality_repair=true`；旧授权不覆盖新计划。已完成的独立同稿双fresh及其2HTTP/38271known另行保留，不能从总账中消失或冒充新application后的复审。

费用授权、冻结提交公共CI全绿及真实作者预检均满足后才可发送；准备和Host-only不读取Key。发送使用现有Windows Credential Manager企业凭据，不需要再次填写，不读取生成模型Key。524/可恢复格式故障只暂停同项；普通resume不发补测，手动补测保留所有成功项和未知费用。

## 初审漏检的待修暂停（本地接线，尚未完成恢复批准入口）

新计划可在prepare时显式固定`--initial-review-rejection-policy pause-initial-review-v1`。
默认仍为旧stop行为，旧冻结计划不改。该选项进入review_plan及plan/guard摘要，run不能覆盖。
仅facts-initial/completion-initial的opinion、且两份Host意见中所有缺陷均为missed_error时，
导入真实拒绝后保留原submission及作者/native，记录review_repair_pending，不直接写terminal。
恢复回放返回session_review_repair_required，仍阻止新模型请求、重复提交和绕过未解决问题。
fresh、其他缺陷及来源/native完整性错误沿用原拒绝行为。本阶段没有“继续”或跳过门的开关。

下一步接入绑定同稿/原意见/补丁的独立联合覆盖审查，确认修法可靠后才允许原工作流继续。
因此本阶段只证明可保留待修前缀，不证明已恢复正式application，也不授权重开已封存批。

## 重叠意见

1. 两项初审分别返回并完成完整来源双审，原意见逐字保留。
2. 组装如发现重叠，返回`session_awaiting_patch_coordination`，保留成功前缀及`execution/journal/patch-conflicts.json`。此时没有application或新模型请求。
3. Operator依据完整来源形成协调选择，固定选择文件SHA。只能从原补丁中选择，并覆盖两项审查的全部修订义务；选择文件不能自行添加改写文本。
4. 续接同一`run`及原guard/checkpoint，增加`--host-only --patch-coordination-file <FILE> --patch-coordination-sha <SHA>`。文件/SHA使用既有严格读取器；缺原冲突库存、丢失义务、未知选择或仍然重叠均拒绝。
5. 依次完成`patch-coordination`、`compatibility`、`edit`原生双审。提交与检查点交接沿用原命令和作者原件规则；后续续接不再传选择文件，程序回放已提交的选择。
6. `run --host-only`执行唯一实际application，到下一新模型请求边界返回`session_model_boundary`。之后移除`--host-only`，按有效费用授权发送facts-fresh和completion-fresh；两项审查须绑定同一实际新稿。

任一原生双审拒绝仍保留最早拒绝并停止该任务；不以补测越过语义拒绝。协调只解决原补丁组装，不能代替完整新稿检查。

## 本地续接与模型发送

Host-only仅允许已有session及精确原guard/checkpoint，不接受`--manual-retry`。它核对原授权字节、冻结源码、原控制和真实native，但不查询CI、不读取Key。其`max_new_models=0`在任何新model intent前暂停，已有结果照常回放。因此费用授权过期也可完成本地审查/收尾；不能据此发送新请求或延长授权。命令仍须携带原授权、preflight及CI参数；CI参数不在本地片段中查询。

需要新发送时，现有精确HEAD公共CI、有效授权及来源/native核验照常执行。524及已知格式故障仅暂停当前项；普通续接不读Key、不重发。明确手动补测使用原`--manual-retry`，累计用量和unknown预留保持，不自动循环。

关闭后使用原`replay`/`seal`，不传选择文件。回放从原session恢复已接受选择；seal只创建一次。成功项、原意见、作者原件、历史失败与费用均不得改写。

## 验证边界

`tests/test_sol_natural_coordination.py`通过实际自然Application/Runtime及owned worker验证以上流程，HTTP和native事件为禁止联网的模拟资料。该检查不能证明真实模型语义质量或产品可用。

自然候选为6个逻辑模型调用，和原产品5调用的差异仍未解除。旧15案例已分版本封存，不为这次接线重跑；后续真实自然消费需要明确范围和费用授权。
