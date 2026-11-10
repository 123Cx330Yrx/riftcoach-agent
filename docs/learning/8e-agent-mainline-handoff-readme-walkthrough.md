# 8E Agent 主线交接与 README 事实版 walkthrough

这份材料记录 Portal/Account 视觉切片收口后，为什么要把执行重心交回 Agent，以及这次交接为什么不等于 8E 或生产发布完成。

## 1. 问题与原则

前端入口已经能展示地区选择、Account 交接和工作台骨架，但如果继续只做视觉扩展，容易把 Agent 的模型准入、用户可用交互、证据闭环和部署边界往后遗忘。本批解决的是“路线交接和事实表达”问题，不是新增运行时能力。

核心原则仍是：程序计算事实，检索提供依据，模型组织表达，独立 Harness 决定是否发布；所有长期记忆和训练计划写入都必须经过来源、权限、确认和版本控制。

## 2. 设计与实现

交接保持现有组合：`Cinematic Portal → Broadcast Workbench`。Portal/Account 当前切片继续是 research-only presentation，Agent 主线从既有 `AgentLoop`、`ContextBuilder`、`ToolRuntime`、`ReviewHarness`、Conversation/Memory/Training 合同继续推进，不另造一套 Agent。

README 的事实版只补充当前阶段、完成证据和开放闸门；8F 再做广泛样本研究、架构图、截图、演示和作品集编排。

## 3. 代码地图

- `app/agent/`：请求编译、上下文构建、循环和 Memory-aware context；
- `app/runtime/`：可靠运行时、预算、取消、事件和恢复；
- `app/harness/`：唯一发布权威与事实评测；
- `app/conversations/turns.py`：受约束的 terminal assistant turn；
- `app/tasks/recent_review_executor.py`：Conversation-bound Recent Review 执行；
- `app/api/main.py`：会话、Review、任务、证据、时间线和训练 API；
- `web/src/components/CoachBrief.tsx` 与 `web/src/api/liveWorkbenchApi.ts`：当前主要是报告/证据展示，尚没有受限追问 Coach 的提交合同。

## 4. 数据与控制流

现有 Recent Review 链路是：Riot ID/绑定玩家 → 对局与时间线 → 确定性指标 → Data Dragon 与本地 RAG → Agent 草稿 → 独立评测/Harness → final Artifact。Conversation 追加 user message 不会自动触发 Agent；terminal assistant 只能由可信任务和发布结果内部写入。

后续 Coach 必须绑定 owner、Conversation、source run 和玩家身份，只允许 Review-grounded 的有限 Skill；Training Candidate 先由用户编辑和确认，再物化为长期计划。

## 5. 本批验证

本批只修改 Markdown/YAML 状态和 README，不读取 Secret、不调用外部 Provider/Riot/OP.GG，不触碰 `app/` 或 `web/`。完成后运行治理脚本和 `git diff --check`；RQ-161/162 的前端测试证据继续按原记录引用，不能被重新表述为生产成熟度。

## 6. 运行方式

阅读顺序固定为：

1. `docs/project_execution_state.md`；
2. `.planning/.active_plan` 指向的活动计划；
3. `docs/requirements_change_log.md` 的 RQ-163 及 RQ-154–162；
4. 本计划与本 walkthrough；
5. `README.md` 的当前定位和 Stage 8 待办。

## 7. 失败、安全与边界

- GLM-5.3 不是改一个模型名；必须通过 G53-0 至 G53-4，默认模型保持不变；
- Coach 被 Harness 拒绝时不能写 assistant 消息，不能开放任意聊天；
- 未通过来源/许可/格式/部署门的媒体继续保持 research-only，`production_media=0`；
- 本地 unit、E2E、typecheck 和 build 不能代替正式 OIDC/RSO、HTTPS、密钥生命周期、备份擦除、公网部署和 8F 评估；
- 旧的两地区试验和“决定第三地区”文字只保留为历史，不是当前动作。

## 8. 面试准确表述

可以说：项目已经完成 Agent Loop、可靠运行时、Memory/typed turns、MCP 和 typed EvidenceBundle，并正在 8E 把这些能力接成产品。不能说：GLM-5.3 已上线、Coach 已有开放对话、Portal 媒体已进入生产，或 Stage 8 已经完成。
