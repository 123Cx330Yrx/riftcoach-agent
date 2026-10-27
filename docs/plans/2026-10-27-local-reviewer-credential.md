# 原15评估的本机凭据入口

2026-10-27。用户要求天机阁Key像现有智谱配置一样可重复使用，让执行者能直接续接每一例。智谱原来是显式读取本机.env；天机阁原函数每次getpass，没有后台自动取Key的入口。

- 目标：一次隐藏输入，Windows凭据管理器保存；后续在原发送前检查通过、实际需要Key时才读取，不经过聊天、命令参数、环境变量、Git或运行日志。
- 路径：`scripts/windows_reviewer_credentials.py`使用Windows原生CredWriteW/CredReadW/CredDeleteW，无新依赖。凭据属于当前Windows用户并在本机跨重启保存，不是其他Windows用户通用的配置；同用户运行的程序可以访问它。
- 控制流：原15外部Control/stored_key_operator.py校验固定模块SHA和endpoint/group后，只替换原continuation_credentials回调，调用原operator.main。原费用授权、实际cwd/解释器、CI、来源/作者/原件、逐项审查、预算、stdout根、断点与手动恢复检查全部沿用；不改冻结执行树。原隐藏输入入口也继续保留。
- 绑定：`https://yujianwudi.top/v1`、用户所选GPT-企业专线（0.25×），凭据target为`RiftCoach/Tianjige/yujianwudi.top-v1/GPT-enterprise-0.25`。分组标签不是渠道身份独立验证。
- 失败：凭据缺失或profile不匹配时不回退到其他Key、供应商或交互提示；不发送请求。普通服务错误仍保留成功项，按原规则在同项手动恢复。保存Key不延长费用授权或重置预算。
- 验证：5项针对性检查通过；包括真实Windows假凭据保存→读取→更新→删除→缺失检测、CLI不输出Key、延迟加载、错误profile先拒绝、缺失不回退。假凭据已删除。实际绝对cwd/解释器启动外部adapter通过；准备阶段0真实profile Key读取、0Provider请求。原25回执/432347known和冻结HEAD/clean保持。不重复等待冻结全套CI。
- 当前：实现及本地入口已就绪，真实Key尚待用户一次隐藏保存。原15完成6/15，claim-scope:2只待completion-initial；本工作不授产品或全15资格，automation保持PAUSED。

Control绝对路径：`C:/Users/33502/Documents/Agent/outputs/riftcoach-sol-original15-20261025-control`。

一次配置（用户自己的终端）：

```powershell
& 'C:\Users\33502\Documents\Agent\outputs\riftcoach-sol-original15-20261025-control\configure-tianjige-key.ps1'
```

显示`ok:true`后可由当前执行者非交互续接：

```powershell
& 'C:\Users\33502\Documents\Agent\outputs\riftcoach-sol-original15-20261025-control\start-with-stored-key.ps1' -Case 'claim-scope:2'
```

同配置入口的`-Action status`只输出是否存在，`-Action remove`删除该明确命名的凭据；替换Key再次运行默认配置命令。不在聊天发送Key。当前费用授权北京时间10月28日00:21:46到期，不随保存时间延展。

证据：`data/evaluation/results/sol_original15_stored_credential_ready_20261027.json`，含外部模块/原controller SHA、启动验证与测试结果。保存后仍需按真实运行回执记录进展，不能将这份准备结果称为已成功读取真实Key或已完成下一次评估。
