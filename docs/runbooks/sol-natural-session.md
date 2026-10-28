# 自然任务候选的协调与恢复入口

适用入口：`python -m scripts.sol_natural_launch`。这是显式开发候选，仍拒绝发布；不注册默认Worker/API，不授模型或产品资格。

## 当前候选

`prepare --candidate dual-necessity`选择`sol_review_contract`，使用同一Application、Runtime、持久化session及原生双审gate。它支持动态自然任务，和固定报告评估使用同一审查政策；准备不读取Key或发送请求。

原`baseline`和`necessity`选择不变。计划固定实际HEAD、源码、合同、请求、分组和预算；原历史计划/冻结目录不在新源码下改签。新入口不自动导入其他合同的封存任务。

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
