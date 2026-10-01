# GLM-5.3 Flash Hardened Domain V2 Real Observation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 RQ-229 已公共闭环的 V2 新考卷增加专用、可审计的真实运行入口，并在新的 exact-SHA 公共绿灯后执行用户授权的一次有界领域观察。

**Architecture:** 新入口复用 RQ-227 已验证的串行预算、领域评测和 body-free 回执结构，但使用独立的 V2 协议/准入类型，避免把新结果误标成旧协议。运行器强制 `quality_hardening=True`，只接受 RQ-229 六文件准入、低思考/4096 请求策略、既有真实 G53-3-L 证据和与当前实现 SHA 一致的公共 CI；任何身份、安全或资源漂移都在 Provider 创建前失败关闭。

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, OpenAI-compatible Zhipu client, versioned JSON evidence.

---

### Task 1: 写出 V2 真实入口红灯合同

**Status:** completed-local

**Files:**
- Create: `tests/test_glm53_hardened_domain_gate.py`

1. 断言预检绑定新协议、三案例、质量加固、exact-SHA 公共证据且外部调用为零。
2. 用 Fake Provider 断言三案例串行执行、低思考/4096 预算和新结果身份。
3. 断言没有开启质量加固的执行器被拒绝，真实调用确认和 create-only 回执边界保持 fail closed。
4. 运行聚焦测试，确认新模块不存在时失败。

### Task 2: 实现专用预检、执行和 CLI

**Status:** completed-local

**Files:**
- Create: `app/evaluation/glm53_hardened_domain_gate.py`
- Create: `scripts/run_glm53_hardened_domain_gate.py`
- Modify: `app/evaluation/glm53_hardened_domain_assets.py`

1. 为六文件准入对象增加只读的命名 SHA 投影，不改变序列化身份。
2. 建立 V2 Admission/Result，绑定 RQ-229 资产、质量版本、G53-3-L 真实证据和当前 exact-SHA CI。
3. 复用已有串行领域执行器与预算墙，但额外强制 `quality_hardening=True`。
4. 提供 preflight-only 与显式 `--confirm-real-call` CLI，输出仅含安全计数和状态。
5. 运行聚焦与相邻回归、compileall、diff check 和治理检查。

### Task 3: exact-SHA 公共闭环与一次真实观察

**Status:** implementation-ready; pending-public-ci

**Files:**
- Create: `data/evaluation/results/provider_capabilities/zhipu_glm53_flash_hardened_domain_v2_rq230_v1.json`

1. 独立提交并推送运行器实现，等待同一 SHA 的 pytest、PostgreSQL 和 packaging-smoke 全绿。
2. 在干净同 SHA 上执行 no-I/O preflight，核对 Provider 调用为零。
3. 使用用户本轮授权执行一次且仅一次 V2 三案例观察；最多 12 次领域调用，24,000/72,000 token 墙，首个不安全失败即停。
4. 只保存 create-only、body-free 脱敏回执，不保存 Prompt、正文、reasoning、工具参数、Key 或请求 ID。

### Task 4: 持久化 RQ-230 结论

**Status:** in-progress; pre-real-call checkpoint persisted

**Files:**
- Modify: `docs/requirements_change_log.md`
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/roadmap_v1_3_amendment.md`
- Modify: `docs/architecture_capability_matrix.md`
- Modify: `docs/project_decisions.md`
- Modify: `docs/learning/README.md`
- Modify: `docs/learning/coverage.yaml`
- Create: `docs/learning/8e-glm53-hardened-domain-v2-real-observation-walkthrough.md`

1. 按真实结果记录通过、拒绝或资源停止，不预设结论、不改写 RQ-227。
2. 明确候选注册、生产准入、黄金切片、安全/部署/合规与 8F 边界。
3. 运行回执 schema/body-free、聚焦回归、diff check 和治理检查后单独提交证据与文档。
