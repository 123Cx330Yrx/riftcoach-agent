# 5D-7 Batch B 实施计划

## 状态

已完成。Task 1 至 Task 5 均已有实现、测试、冻结证据和教学复核。

## 目标

在零外部调用下，为 current recent-form development 实验建立可重复的 Prompt/Context
语义快照、Dataset/Candidate 强绑定和实验 admission 入口。

## Task 1：合同红灯

- 输出：`tests/test_prompt_context_identity.py` 与 Domain E2E 1.1 预期。
- 测试：缺少模块、快照字段和 admission CLI 时必须失败。

## Task 2：快照核心

- 输出：`app/evaluation/prompt_context_identity.py`，以及集中但不改文案的 Evaluation
  system prompt 常量。
- 测试：同输入稳定；Skill/fixture 漂移可定位；自摘要和公开 Schema 严格。

## Task 3：Domain E2E 强绑定

- 输出：Domain Dataset/Candidate/Result Schema 1.1 与快照 ID/SHA 字段。
- 测试：Dataset/Candidate 快照漂移在分层案例求值前失败。

## Task 4：可重复入口与冻结证据

- 输出：`scripts/prepare_domain_e2e_experiment.py`、冻结 Prompt/Context 快照和离线
  admission；重新生成 1.1 development 基线。
- 测试：临时输出与冻结 JSON 完全一致，`external_provider_calls=0`。

## Task 5：收尾

- 输出：教学说明、canonical state、活动计划、路线历史与能力矩阵同步。
- 测试：聚焦/相邻/全量 pytest、两套 RAG、compileall、Harness dry-run、安全、治理、
  diff check；随后提交、推送并核验精确 SHA 的 GitHub Actions。

## 唯一下一步

继续 5D-7 Batch C 入口设计与离线 TDD：所有可执行 development 候选必须先通过
Batch B admission，再逐类验证工具选择、事实、引用与模型级注入；不直接运行真实
Provider、不创建或运行 held-out、不接第二 Provider，也不进入 5D exit review 或 5E。
