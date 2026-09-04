# 8E 学习记录：GLM-5.3 Flash V3 离线实现（RQ-232）

## 1. 问题与原则

RQ-230 的 V2 运行器把修订预算固定为零，导致首稿事实核验失败后只能拒绝；本批把 RQ-231
的设计落成候选专用、离线可验证的 V3 实现。质量门没有降低，V3 也没有进入产品 Runtime。
核心原则是“先预留资源，再 I/O；先完成身份和资产准入，再允许真实调用；任何不完整或不安全
结果都 fail closed”。

## 2. 设计与实现地图

- `provider_domain_production.py`：`max_revisions` 默认仍为 `0`；显式 V3 才传入 `1`，并把
  评测轮次投影为 body-free 的枚举计数。
- `domain_e2e.py` / `coach_report.py`：共享固定的评测类别、严重度、轮次和分数类型；额外字段
  由 `extra="forbid"` 拒绝。
- `glm53_bounded_revision_budget.py`：每案 9 次、全域 27 次调用墙，调用前预留、Usage 结算后
  校验，未知或越界立即关闭。
- `glm53_bounded_revision_budget_reachability.py`：用冻结 Context 和请求包络离线推导每案
  `203000`、全域 `608000` token 上限，并生成可重建报告。
- `glm53_hardened_domain_v3_assets.py`：绑定全新 Dataset、Input Plan、Context、协议、fixture
  和预算报告的 SHA，拒绝 RQ-227/V2 历史污染且不构造 Provider。
- `glm53_hardened_domain_v3_gate.py`：候选专用 V3 入口；缺少同 SHA 公共 CI 或新鲜 G53-3-L
  证据时分别返回 `pending_public_ci` / `pending_protocol_evidence`。

## 3. 控制流

```text
V3 资产准入（零 I/O）
        ↓
每案 Agent 最多 4 次 → 首评/格式修复最多 2 次
        ↓
需要修订且无安全阻断？→ 最多 1 次修订
        ↓
复评/格式修复最多 2 次 → 严格质量与发布门
        ↓
body-free 结果；候选仍未注册
```

阻断性注入或资源失败不会进入修订。真实执行入口还要求显式确认、干净提交、同一实现 SHA
的公共 CI、新鲜 G53-3-L 证据；本批没有走这些真实调用条件。

## 4. 验证与运行手册

预算脚本可离线重建冻结报告：`python scripts/build_glm53_bounded_revision_budget_reachability.py`。
V3 入口预检使用 `python scripts/run_glm53_hardened_domain_v3_gate.py --preflight-only`；当前实现
尚无公共 CI 声明，因此应停在 `pending_public_ci`，不得加载 Key 或构造 Provider。

本地聚焦与相邻回归共 `54 passed`；`compileall`、`git diff --check` 和治理检查均通过，
provider calls=0、network=false。实现冻结在提交
`730c32d074269fb45e5a5351b1af591ecaa35de1`；这只是离线实现身份，不是公共 CI 或生产准入证据。

## 5. 失败、安全与边界

诊断只保留 attempt、score、verdict、通过项数量、问题类别和严重度计数，不保存正文、引用、
reasoning、Prompt、工具参数、请求 ID 或凭据。旧 V2 的 `4/12` 与 `24000/72000` 预算和回执
保持不变；GLM-5.2 兼容/应急路径、默认 Runtime、Portal、Account、Workbench、Auth、路由和
`production_media=0` 均未改。候选仍 `candidate-only/disabled`，领域质量、黄金切片、生产安全/
部署/合规和 8F 仍未完成。

## 6. 面试表达

> 我没有用更低门槛掩盖 V2 的事实核验失败，而是把产品原有的一次修订闭环做成候选专用 V3：
> 保留所有硬门，先用全请求包络证明 9/27 调用和 203000/608000 token 墙，再用 body-free 诊断
> 暴露可行动的枚举计数，同时把真实 Provider 继续挡在公共 CI 和新鲜协议证据之后。
