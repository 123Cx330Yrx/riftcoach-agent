# Host 作者工作区与提交边界修复

## 工作卡

目标是消除上一批已复现的链路缺口：作者答案误写入证据目录后，提交没有拒绝，下一项请求仍产生费用。
本包只修开发审查流程，不修订业务判词、不购买模型调用、不重开历史批次。

实现选择：在新入口的私有 runner 安装 `scripts/host_review_workspace.py`，复用原始 checkpoint、native 导入、
提交锁与严格 seal。直接修改共享 runner 会改变旧 plan 的源码摘要；给旧白名单增加作者文件又会改写失败判定，
两者均未采用。`scripts/document_full_report_workspace.py` 是接线入口，其付费 `run` 明确关闭；
未来选定业务范围后仍须冻结自己的计划和授权，不能用这份验证入口重买旧报告。

数据流：生成 dispatch 核绝对 cwd/Python 与 run 外作者路径 → 作者 create-only 写自己的 JSON →
原 checkpoint check-answer → 原生 final 导入 → 对照作者文件与原生判断 → 提交锁内再次核库存 →
下一请求前及 transport 接口处再次核库存 → 原只读 replay/create-only seal。
主审不生成独立意见，不改写作者答案。目录跳转及硬链接作者文件拒绝；这不是抵御恶意并发写盘的 OS 沙箱。

## 验证分层

- 软件回归：新增作者真实落盘/CLI 校验与模拟 native 事件来源测试；提交前、native 读取期间、提交后、
  下一 before_send 回调及最终 transport 交接污染均阻断下一请求。另检答案改变、已有答案、Windows junction、
  无付费入口、旧入口隔离与只读/create-only seal。
- 29 项工作区/旧完整报告/旧两稿回归通过；新增完整演练材料预验 1 项通过，共 30 项。
- 真实 native 演练：复用原独立主体，只派一项新短报告；固定模拟响应明确标识，Python 网络调用禁用。
  原生作者/终答是真实来源，transport、用量及回执是离线测试夹具，不是项目 Provider 调用。
  本次范围不包含 V2/H5/S8 旧任务。已完成唯一native审查和提交，严格只读seal成功，26份原件SHA保持。14条原生公开命令均exit0，唯一final与作者文件JSON相同。

本地演练准备曾两次停止：单例600秒总活动预算无法保留完整600秒请求；短报告缺少知识引用导致既有
协议校验拒绝。均未派独立任务，项目 Provider/HTTP 为0；后一项只有显式模拟 transport。两份失败目录及
各自 driver 源码快照保留。修正演练预算为1200秒、正文加入有来源的K5证据分层建议，并先完整跑通离线
observe/作者文件/native替身/submit/seal，再派唯一真实独立任务。未放宽原业务协议或旧付费预算。

## 边界与下一动作

旧47/26/14/146份库存逐字节核验保持；H5错误修法、S8未认证、旧strict seal缺口与TCP unknown1继续保留。
本轮没有新业务资格，完整同版本15、自然消费、8E和下游交付均未完成，自动任务仍PAUSED。

工作区修复只能保证本地流程中的证据边界，不能使错误修法变正确。H5反例中，原policy已要求逐项核对修法，
且已有2.5/0.5的教学反例，因此不能把再添同义提醒当成有效语义修复。下一步沿已有错误/正确全文对照，
检查评审修法到编辑消费的实际合同，决定如何约束新增替换断言；先用离线反例检验表达能力，再决定必要实测。

## 已核证据

公开目录：`data/evaluation/results/host_workspace_repair_20261012/`。`audit.json` SHA
`cd71c137a53f0aa9648c85bf11d5bea34564555134492f27354d2fb76e3d1f58`。
明确命名的 `SYNTHETIC-transport-real-native-seal.json` SHA
`62530865bfbc1c14597d63fb3438f2a7c0812e54aefa1b39864eb0b5f99c5032`。
原生event：`01a12f0c-bb7c-74e3-ad92-775eefbe399a/01a13005-ae8b-7211-9f5e-fe9599ec06ed/msg_0998f8ac4632b025016acccefb195081948ecd72cf0ac59078`。
主审实读原生完整终答后沿真实submit导入；既有FINAL_POLICY接受唯一native final，不假造不可读的dispatch事件。
主审/独立均接受此合成意见。业务提交0、演练提交1、Provider/HTTP/tokens0，新资格0。
