# 剩余十一扫描的付费前 CI 超时修复

用户已明确确认冻结方案d5aa7c914cb9b30d66422a28c83736afc1cc79313fc32be2d4feced1b73429bf。
原准备提交4749c23011f67b7ccedd39d7fa0a25fb3446b34e、CI37809368023的pytest任务
在约83%触及一小时上限取消。GitHub annotation为
`The job has exceeded the maximum execution time of 1h0m0s`；收集5972项。
取消前未观察到断言失败，剩余未执行，不能称CI通过。其他两门成功。
旧等待器因ci_not_passed正常退出，provider_started=false；扫描run未创建，Provider0。

原授权、失败等待器和预检原件保留在本机outputs/riftcoach-document-remaining11-scan-20261009。
恢复配置使用独立ci-recovery子目录，保留原授权并显式记录CI-only后的执行HEAD与CI。
原模型/执行依赖69项、业务identity、input/report/request、方案、预算和停止语义保持；
工程修复不是新增模型实验，也不以旧授权覆盖不同模型计划。

## 执行机制和验证

完整pytest收集清单按原序号均分到四个隔离Ubuntu任务，复用原运行依赖、标记和skip规则。
每片保存同HEAD的完整/选中清单和实际call终态或setup-skip、退出码；原退出码不转换。
汇总pytest门要求四片和web-checks成功，并验证同完整清单、每片精确选中、真实终态恰好
覆盖全部清单一次。缺片、失败、超时、缺测、重复、不同HEAD或清单都不能通过。

web-checks保留原Node/web单元/类型/build/e2e、cinematic、governance、RAG两门、compile、
Harness边界、secrets/run-data和dry-run；Postgres与packaging-smoke保持。
不扩大单任务一小时上限，不删测试、不用仅新增测试代替全套公共CI。

本地真实四子进程8项含skip覆盖，以及六种故障拒绝检查共7项通过。
新扫描21项与分片7项一起运行于四个独立进程，28项全部终态恰好一次，汇总通过；
独立代码复核无阻断。这证明工程分片与覆盖机制，不能证明模型语义质量。

跟进实际消费者时发现既有frontend package contract测试仍要求pytest物理任务直接
包含Node/web步骤，未随汇总任务适配。f6ebae04的CI37819180174主动取消，唯一付费前
等待器47536经命令行身份核实停止，run未创建、Provider0；不把此工程遗漏归咎于模型。
该既有测试现同时核验汇总门对web-checks与全部分片的依赖、失败/skip阻断及覆盖验证，
再核web-checks原完整质量步骤。分片跳过计数也拒绝重复skip记录。CI/前端/DB/打包合同
联合36项本地通过；原失败和恢复记录保留，下一执行HEAD/CI另行记录。

3adaa47b的CI37819992466四分片、web、DB、packaging均成功，汇总因记录器将
pytest 9的unittest.subTest子结果误算为父节点重复执行而失败。原清单5980父节点，
额外129 call事件、无缺失；只读原件未改。现场probe确认SubtestReport带context，
父TestReport仅一次。全部27个相关父节点用修复记录器重放，27通过/129子测试通过，
精确父覆盖验证通过，逐项匹配公共失败清单；不是模型或真实漏跑失败。

记录器version2把有context的子报告单独保留，父终态Counter仍恰好一次，不把父列表
set去重；子报告必须归属选中父节点、结果passed/skipped，失败保持pytest原exitcode
及汇总拒绝。四真实进程覆盖包括setup-skip、通过和跳过的subTest，另有真实失败子测试
不能绿灯及failed/foreign子报告篡改拒绝。联合合同/Provider/MCP/Tool/Zhipu检查115项、
83子测试通过。旧等待器正常ci_not_passed付费前退出，Provider0；新HEAD/CI另行恢复。

## 当前恢复边界

推送本包后记录新执行HEAD/公共CI，恢复单份付费前等待。CI全绿、clean exact HEAD及
真实native主体通过后才首次执行同一11例方案。不得重启已执行批、覆盖原授权或改变
模型边界。11例语义失败收集继续，硬协议/来源/身份/native/transport/预算失败立即停。
历史2/15、旧文档3/15分开保留，第四例分歧和完整15/产品消费/8E仍未完成。
