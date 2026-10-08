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

## 当前恢复边界

推送本包后记录新执行HEAD/公共CI，恢复单份付费前等待。CI全绿、clean exact HEAD及
真实native主体通过后才首次执行同一11例方案。不得重启已执行批、覆盖原授权或改变
模型边界。11例语义失败收集继续，硬协议/来源/身份/native/transport/预算失败立即停。
历史2/15、旧文档3/15分开保留，第四例分歧和完整15/产品消费/8E仍未完成。
