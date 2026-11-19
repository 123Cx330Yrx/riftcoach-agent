# 当前组合15例完整链路：执行准备与决策

> **2026-10-13后续裁决：本次37.167104元付费提议已撤回，不是当前执行队列。**
> 三个旧失败的完整请求与当前重建请求相同，没有语义修复证据；见
> [修复就绪审计](2026-10-13-full15-repair-readiness.md)。以下范围、预算、CLI与准备原件
> 保留为未执行的工程准备及原提议记录，不能据此申请/生成授权或启动批次。

本包接通可执行入口，尚未授权或执行模型请求。复用现有完整报告初评、必要编辑和独立完整终评的状态机；新代码只负责冻结35次范围、首次执行条件和新资格入口的配置接线。旧三批、两次Host演练和J1/J2均不重开，不改历史标签或审查意见。

## 决策价值与结束条件

目标是判断当前组合能否在**一个完整批次**中通过既定15例固定审查集，补齐实际编辑、终评与每阶段真实Host记录。原15已全部发送，旧10通过不能拼成当前组合资格，2项认证缺口不能补签；新批不是继续发送旧批未发项。三个旧语义拒绝/分歧仍是反证，没有因工程修复而消失。

不再购买另一组关系教学成对初评：J1/J2两臂皆过，没有改善证据。也不再用第三次简化Host演练冲通过：完整链路将在业务stage中检查，只有真实存在的final才计覆盖。此批若成功，只能授予当前版本熟悉固定审查集资格，不能证明提示改善、稳定成功率、独立holdout、自然Coach/Training或产品准入。任一必要stage缺失/语义失败就不能授予该资格；保存失败矩阵后重新裁决方案，不自动再跑同一批。

## 冻结范围与实际预算

| 项目 | 执行约束 |
|---|---|
| 入口 | `python -m scripts.full_chain_execution` |
| 配置 | `full-chain-controls-execution-v1`，仅full15/time600 |
| 唯一run | `D:/riftcoach-agent-rq192-pr/data/runs/model_comparison/document-full-chain-controls-20261013-v1` |
| Operator | `C:/Users/33502/Documents/Agent/outputs/riftcoach-full-chain-controls-20261013` |
| 模型次数 | 最多25次GLM-5.3/high、10次GLM-5.3-flash；共35次 |
| 实际阶段 | 5份正确稿各initial；10份错误稿各initial/revision/final。依赖失败后不为凑数发送 |
| Token | 批次known+unknown reservation最高3,386,880；单case沿用401,920共享预算 |
| 时间 | 单case共享900活动秒；review最多600秒、edit最多300秒，受case剩余额度约束；批次13,500活动秒/86,400 Host秒 |
| 输出 | 每请求最高32,768 tokens；SDK重试0；禁止重评、补发和重开 |
| 估价 | 按每次64,000输入+32,768输出及现有合同价格估算37.167104元，非硬账单封顶 |
| 主体 | 主审 `01a1248f-e18c-7282-92bf-7ceb2eb5dce4`；独立 `01a12f0c-bb7c-74e3-ad92-775eefbe399a` |

旧full15准备保留45次宽预算。本配置把真实runner使用的batch budget收紧到35次，不修改冻结的旧runner或case900秒合同。合法状态转换自然限制为25次review/10次edit；总次数及token reservation在实际发送前检查，不只列在文档。固定15的顺序、全文、来源、标签和请求SHA沿用原15对齐记录；模型输入不加入标签或本方案。

新plan保持`full-chain-evidence-v1`的回放格式，另有明确execution_profile；53份业务源码包括新executor和资格验证器。资格准备另绑定alignment producer及完整组合。旧准备原件保留为当时的快照，不能冒充本配置准备；本配置使用两个新文件：

- `data/evaluation/results/full_chain_execution_preparation_20261013.json`：实际plan、路径、预算及嵌入资格准备。
- `data/evaluation/results/full_chain_execution_qualification_20261013.json`：供资格CLI独立核SHA的准备文件。

## 数据和控制流

准备/授权原件SHA → 当前同HEAD clean/public CI → native主从身份与读取能力 → 绝对cwd/Python真实启动 → 重建全部准备 → create-only执行占位 → 读取模型配置 → create-only run → observed worker → 真实Host每stage审查 → 原件关闭 → 只读replay/seal → 新资格检查。

新代码继承`FullChainEvidence`，让它的私有runner.prepare及replay自动重建相同配置；没有复制三阶段业务状态机。资格入口按显式配置选择同一个类，拒绝旧配置冒充35次配置。

首次执行前拒绝存在的run（包括空目录）、作者目录、观测目录或`operator/execution.json`。Operator路径也在准备SHA内，不允许换目录绕过失败占位。占位用排他创建，读取密钥失败也不删除重试。授权原件在后续send、Host等待、库存复查及子进程IO前重新核SHA/期限；同HEAD clean在每次发送前复核。源码、来源、作者、观测及白名单库存沿用完整链路门。

完整返回但有效语义拒绝/分歧：结束该case依赖，继续下一独立case，批次资格失败。身份、来源、native、checkpoint、协议、传输、预算、主体不可用或授权失效：停止全批，适用时写abort，无自动重试。CI查询错误只表示查询未知，不宣称CI失败。启动后的错误保留占位；诊断输出不写SDK异常正文或环境变量。

## 授权与首次启动

目前**无新付费授权**；旧J1/J2授权已关闭。授权只能在用户确认本方案后创建，字段必须恰为`kind, authorized, preparation_sha256, execution_head, ci_run, issued_at, expires_at`；kind为`full-chain-controls-execution-v1-authorization`、authorized=true，绑定准备文件原始SHA、精确提交及该HEAD CI。授权最长24小时，原issued_at和截止不延展，原件SHA作为独立启动参数。准备不会生成授权，CLI不提供签发或重试命令。

首次启动采用绝对Python `D:/riftcoach-agent-rq192-pr/.venv/Scripts/python.exe`，workdir严格为`D:/riftcoach-agent-rq192-pr`；独立审查继续复用既有主体，不新建Agent。所有参数都在实际准备/授权形成后填入，不能把下面占位字符串直接运行：

```text
python -m scripts.full_chain_execution execute --preparation <preparation.json> --preparation-sha <原始SHA> --authorization <operator/authorization.json> --authorization-sha <原始SHA> --operator <上述Operator绝对路径> --env-file <既有模型配置路径> --codex-executable C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe
```

只启动一份进程，stdout/stderr和进程/退出信息写Operator外部记录；不因会话中断重启。GitHub查询的父进程代理`http://127.0.0.1:12000`；模型发送的进程环境由现有direct上下文清代理、设置`NO_PROXY=open.bigmodel.cn`并恢复，不修改用户网络。只在批准后启用对应监控，等待不变保持安静，关闭或确定不能继续后暂停；目前automation继续PAUSED。

## 每阶段人工执行与关闭

每次新`review-required.json`只生成一次checkpoint/dispatch。操作员实读完整stage/report/source/policy/request/response与编辑journal；初评`report_assessment=null`，revision/final要求真实成稿的四项标志。范围语义、来源、解释、修法与正确保留都要核，不把泛指补全称或措辞建议升级成事实错。

向原独立主体发送完整原样dispatch，每业务stage仅一个NEW_TASK；恢复同task只MESSAGE。dispatch已经包含准确checkpoint路径/SHA、绝对cwd/Python和run外作者答案路径，不追加backend，不附主审判断、标签或本批代码。作者在恢复及final前重读同checkpoint，自己写create-only JSON并check-answer，唯一多行native final。主审读取真实event后才调用本入口submit，指定event-id/checkpoint-sha/原主审notes/本机codex-executable；不代写、剪裁或补造。

`task/submit/abort/replay/seal`使用相同入口与prepare里的五个路径参数（directory/answers/observations/cwd/python），其余参数沿用full-chain证据入口。完整关闭后即使付费授权到期，也可继续**只读**审计；不重新安装发送权限。先seal到run/作者/观测外的全新文件，独立记录SHA，再执行：

```text
python -m scripts.qualify_full_chain_controls validate --preparation data/evaluation/results/full_chain_execution_qualification_20261013.json --preparation-sha <资格准备原始SHA> --directory <上述唯一run> --seal <新seal路径> --seal-sha <seal原始SHA> --codex-executable C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe --output <全新资格结果路径>
```

冻结HEAD保持到严格回放和资格判定结束，再提交结果/状态。实际HTTP观测、每阶段真实native、作者原件、完整35stage和同HEAD公共CI缺一不可；通过才输出固定审查集资格，产品/自然任务/付费权限仍false。失败批仍如实关闭、核actual/HTTP/known/unknown/receiptless/未发/最早偏离，保留所有原件；原件损坏时不得通过移除文件让seal通过。

## 离线验证与限制

验证记录见`data/evaluation/results/full_chain_execution_validation_20261013.json`。测试覆盖授权期限/错绑/改字节、旧授权拒绝、唯一run与占位、密钥前门控、35次预算配置与真实发送拦截、新配置的作者文件/check-answer/native导入/submit/replay，以及资格回放的正确入口和缺失/变更拒绝。业务响应和native为替身，不是真实质量或真实Host final成功证据。实际native只读预检仅说明当前可读取，不能保证未来35阶段主体始终可用。

本包不改变模型政策、编辑schema、产品默认或9个主阶段；8E、自然消费、Worker阶段间取消、Coach/Training、四块联动、DB/API/UI/journal、前端审美头像、Memory、身份运维、两树整合、独立评估与学习继续保留。
