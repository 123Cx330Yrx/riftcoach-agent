# GLM-5.3-Flash 专属运行时预算实施计划

> 历史说明：本计划对应 RQ-175 的离线适配批次；随后 RQ-176 已明确把同一 Flash 档案推进为产品正常运行目标，
> 因而下方“非目标”只约束 RQ-175 当时的批次，不再覆盖当前路线。当前公共 CI、同 SHA 协议、领域门与生产准入仍须
> 按 RQ-176 独立完成。

> **For Claude:** REQUIRED SUB-SKILL: Use the execution workflow in `C:\Users\33502\.agents\skills\code-1.0.4\SKILL.md` when carrying out this plan.

**目标：** 为精确模型 `glm-5.3-flash` 建立一个受信、版本化、可回放的运行时预算档案，
让 Flash 思考与工具回合拥有独立的 90 秒执行窗和 2048 输出上限，同时不改变
GLM-5.2、其他 Provider、默认模型或生产准入结论。旧 held-out 数据集的 30 秒资源质量门
仍保留；若要取消该质量门，必须另建版本化 Dataset/Plan，不能改写旧结果。

**架构：** 共享的不可变 `ModelRuntimeProfile` 只承载模型专属的 Agent 截止、Harness 工具窗口、传输超时、输出上限和采样默认值。G53 领域执行器显式注入该档案；AgentLoop、`llm.chat` 工具适配器和 Flash Provider 构造共同消费它。Manifest 的调用次数、工具白名单、上下文上限、质量/安全规则继续保持原值；旧 G53-4/G53-6 结果只读。真实新结果使用新的档案/输出身份，不能覆盖历史结果。

**技术栈：** Python 3.11、不可变 dataclass、现有 AgentLoop/ToolRuntime/Zhipu 适配器、pytest、治理检查。

---

## 实施任务

1. **先写离线红灯测试**
   - 锁定 Flash 档案字段、精确模型匹配、预算上限和 GLM-5.2/未知模型不受影响。
   - 验证 AgentRunRequest/AgentLoop 收到显式 `max_tokens`、`temperature`、`top_p` 和 90 秒剩余截止。
   - 验证 `llm.chat` 的 Flash 默认值、工具窗口和超大请求被档案上限截断；普通 Provider 保持旧值。
   - 验证 G53 领域预算身份只能使用新 profile，旧结果仍可读取。

2. **实现受信 Flash 档案与传递接缝**
   - 新增 `ModelRuntimeProfile` 及精确 `glm-5.3-flash` 档案；不从用户输入或环境变量升权。
   - 扩展 AgentRunRequest/Compiler/Loop 的请求级预算字段，并在领域执行器中显式注入。
   - 让 Harness `llm.chat` 和客户端超时消费同一档案；所有调用继续单次、首错停止。

3. **更新 G53-7 专属实验边界**
   - 将 Flash profile 的 per-request 上限从 1024 提升到有证据的 2048，保留每例 4000、总计
     12000、12 calls 和旧数据集的 30 秒质量检查（它是质量阈值，不是 Provider 执行截止）。
   - 新档案 ID/实验输出路径与 RQ-174 分离；历史 JSON、数据集和协议证据不可改写。
     默认输出为 `data/evaluation/results/provider_capabilities/`
     `zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json`，运行目录也单独命名。
   - 真实 G53-7 还必须在新实现的 exact-SHA 上重新取得 G53-3 协议证据；当前
     `zhipu_glm53_flash_adapter_protocol_retry2.json` 绑定旧 SHA，只能作为历史基线，不能被新 SHA 冒用。
   - 在真实调用前执行 no-I/O 身份、dirty-worktree 和输出路径检查；结果只标记本地观察，不冒充公共 CI/生产成熟度。

4. **验证与收口**
   - 运行新增/相关聚焦 pytest、compileall、`git diff --check` 和 governance。
   - 若聚焦门全绿，且新实现取得 exact-SHA 公共 CI，再做一次有界真实 G53-7 领域尝试；
     dirty worktree 只允许 no-I/O preflight，不能把本地实现冒充公共 CI。单个外部工具异常立即停止；
     外层监控按不超过 60 秒回报，不静默延长等待，并保留不可变结果。
   - 更新 RQ-175、canonical/活动计划与 findings/progress，明确下一步仍需独立领域/公共 CI/生产决策。

## 非目标

- 不修改 Portal、Account、Workbench、Auth、Riot 路由或 `production_media`。
- 不把 Flash 设为默认生产模型，不修改 GLM-5.2/DeepSeek 的旧预算和结果。
- 不把官方 128K 输出/1M 上下文上限直接照搬到产品；2048/90 秒只是首个受控、可校准档案。
