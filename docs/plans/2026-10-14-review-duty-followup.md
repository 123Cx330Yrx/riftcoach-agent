# 充值后的五次职责对照准备

2026-10-14。用户确认“GLM没钱了，现在充了”，随后要求继续。账户侧余额耗尽/充值已由用户确认；
旧429回执没有业务错误码，不能回填为1113或声称已核实账单。旧批永久保持关闭与原件不变。
本文件把新的付费范围明确为五次；执行须单独绑定新授权、提交和公共CI，旧六次授权不重用。

## 目标、范围与决定

继续检验事实正确性/任务完成度职责分离，核心语义问题尚未解决。已取得有效回答的第一组full
不再购买；新批只发送第一组facts和第二/三组full、facts，共五次，均为新initial、report_assessment=null。
报告、完整来源、system政策、Schema及采样参数逐字保持原准备包的对应请求；不改提示词。

| 顺序 | 新请求 | 证据用途 |
|---|---|---|
| 1 | duty-1-facts:initial | 检验候选对全称真错及全文限定的判断；本批没有对应full，旧full仅历史参考，不能作同批改善证据 |
| 2—3 | duty-2-full:initial / duty-2-facts:initial | 两项完整新初评；旧终稿只作输入快照，核泛指与实质误报 |
| 4—5 | duty-3-full:initial / duty-3-facts:initial | 两项完整新初评；核错组诊断、摘要依赖及完整修法 |

任一facts实质错误则否定当前候选；语义拒绝/分歧仍按既定规则记录并完成下一独立项。
两臂均正确或新full未复现旧失败，无改善证据；不能把不同批次成功拼成修复或资格。
正向差异只支持互补职责/真实编辑消费的开发验证，熟悉来源非holdout，不重启15。
任一身份/来源/native/checkpoint/协议/传输/预算硬故障停全批，不重试或补发。

## 新批执行合同

最多5次GLM-5.3/high、Flash0；temperature=1、top_p=.95，每次600秒/32768输出，
总483840 tokens、3000模型活动秒、86400 Host秒；每请求至多1次HTTP，SDK重试0。
沿现有合同价格输入8/输出28元每百万token计算，保守未缓存估价上界7.14752元，非账单硬封顶。
这是新五次的单独预算，旧批已知部分0.223940元及未知用量继续单列，不能相减伪装成剩余额度。

- 入口：`python -m scripts.document_review_duty_followup_diagnostic`
- 包：`data/evaluation/fixtures/document_review_duty_followup_20261014`（11件）
- 唯一run：`data/runs/model_comparison/document-review-duty-followup-20261014`
- Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-review-duty-followup-20261014`
- 授权版本：`document-review-duty-followup-authorization-v1`，另行签发24小时有效期，不延展旧授权。
- cwd：`D:/riftcoach-agent-rq192-pr`；Python：该目录`.venv/Scripts/python.exe`。

独立worker及diagnostic隔离新run、授权、observations和author-answers；继续使用完全相同的模型请求身份，
不修改旧代码/执行包。复用原主审与`/root/host_scope_calibration`，不新建Agent；
执行前核实即时真实native、绝对cwd/Python启动、clean exact HEAD及同HEAD公共CI全绿。
完整原样dispatch、checkpoint路径/SHA、run外作者路径；每stage唯一NEW_TASK，同task恢复仅MESSAGE。
独立全文实审、自写JSON/check-answer及唯一native final；主审真实读取后submit，不能代写/补签。
Host库存与无正文观测贯穿submit/下一发送/严格replay及create-only seal。
网络沿用模型内部direct与NO_PROXY，GitHub仅进程代理，不修改用户网络。

## 准备证据与后续门

新入口17项离线检查通过：完整请求字节保持、旧授权拒绝、包污染拒绝、真实loopback SDK
完整/静默/心跳/EOF、原件观测绑定、作者文件/check-answer/native替身/submit/只读封存及硬失败停止。
最初金额字符串多写一位尾零导致测试失败，已纠正测试预期并单项通过；金额数值及运行代码未因此修改。
离线native替身不是实际审查证据。旧批43原件、冻结源码/包和readiness重新核对保持。
旧收尾提交7efa0e9d的公共CI38442621895已全绿；这不替代新入口提交的公共CI。

此时没有新授权文件、业务run或模型发送，旧automation继续PAUSED。
新五次范围获确认后绑定该包SHA、新HEAD/CI并执行唯一批次；不另买探活。
产品5到7调用预算、互补职责/编辑消费、正式同版本15及全部8E产品依赖继续保留。
