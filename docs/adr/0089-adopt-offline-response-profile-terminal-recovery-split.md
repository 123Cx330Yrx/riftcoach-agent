# ADR-0089：采用 Flash 响应档位—终态—恢复离线拆分

- 日期：2026-09-03
- 状态：`implementation-complete-local / candidate-only / public-ci-pending`
- 范围：Stage 8 / 8E；RQ-220

## 背景

RQ-218 证明普通 API 与基础工具协议可达，RQ-219 却在候选 8192、90 秒窗口内以
`elapsed_limit` 收口。两者不能合并成“模型可用/不可用”的结论；还必须把请求档位、
流是否到达终态、Usage 尾帧是否有效，以及候选恢复策略分别观察。

## 决策

新增 `app/evaluation/glm53_flash_response_profile_split.py`，使用固定、零网络的
normalized-event 与 policy snapshot fixtures，复用已有 `CandidateStreamBoundaryObserver`
和两个版本化 `ResponseCompletionPolicy`。每个结果只保存 profile 元数据、终态/Usage
状态、策略安全码和恢复动作，不保存 Prompt、正文、reasoning、工具参数、凭据或请求标识。

固定矩阵覆盖 low/max、2048/8192、`clear_thinking` 两种形状，以及完整 stop、工具回合、
`length` 候选形状、部分正文、缺 Usage、非法 Usage 和 elapsed timeout。候选形状可以被
识别为 `candidate_eligible`，但由于 `activation_state=candidate`，恢复动作仍为
`blocked_activation`，不会发起第二请求。

## 不做的事

本 ADR 不注册候选、不打开 `capabilities.streaming`、不修改严格 Flash v1 的 2048/零额外
调用、不接入 AgentLoop/产品 Runtime/Workbench/Portal/Account/Auth，也不把 fake 结果
当作 provider-native streaming、模型质量、G53-7、黄金切片、生产准入或 8F 证据。

## 验证与下一步

本地矩阵 9/9 场景通过，相关策略/恢复/候选流聚焦回归通过；脚本只能写入
`data/evaluation/results/offline/`，且回执为 `offline_fixture`、provider calls=0。
实现提交的 exact-SHA 公共 CI 完成后，才可把本批标为公共闭环；下一步再审查是否需要
新的候选真实域门，不自动追加真实请求。
