# 8E Agent 主线交接与 README 事实对齐实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

> **Goal:** 在 Portal/Account 当前视觉切片收口后，把 8E 的执行指针安全交回 Agent 主线，并让 README 只陈述已有代码与证据能够支持的事实。

**Architecture:** 本批是文档与状态交接，不改变 Agent、Workbench、Auth、路由或媒体运行时。交接记录保留 8A–8D 的完成证据，把 GLM-5.3 采用闸门、受限 Review Coach、Data Dragon/Evidence/Training、OP.GG 黄金切片以及安全部署列为后续独立闸门；README 采用两阶段策略：现在做事实版，8F 再做作品集版。

**Tech Stack:** Markdown、YAML、现有治理脚本；不新增依赖，不读取 Secret，不调用 Riot/OP.GG/LLM，不改变 `production_media`。

---

## 范围与完成标准

1. 记录 RQ-154–162 的 supersession 关系，明确旧的“两地区/第三地区”路线不再是动作。
2. 把 canonical、活动计划、路线镜像和学习索引对齐到 `8e-productization` 下的 Agent 主线交接；8E 仍为 `in_progress`，8F 仍为 `planned`。
3. README 更新当前阶段、已有 Agent 底座、真实缺口、GLM-5.3 闸门和生产边界；不把本地 UI 回归或设计候选写成生产能力。
4. 留下八维学习材料，说明本批解决的问题、原理、代码地图、数据/控制流、验证、运行方式、失败/安全边界和面试表述。
5. 治理脚本、文档链接和差异检查通过；不改 `app/`、`web/` 或 Workbench。

## 后续执行顺序（本批之后）

```text
G53-0 无 I/O 可用性/配置审计
→ G53-1 离线 GLM-5.3 Adapter profile TDD
→ G53-2 exact-SHA 公共 CI
→ G53-3 最多三次真实协议调用
→ G53-4 新鲜领域采用门
→ 受限 Review-grounded Coach
→ Data Dragon / Evidence-Trace / Training 消费闭环
→ OP.GG breadth 与全链路黄金切片
→ 安全、部署、合规与 8E 退出
→ 8F 最终评估与作品集
```

Coach 与 Data Dragon 的相对顺序仍需在对应设计批次正式裁决；本计划只记录建议，不伪造用户已确认的顺序。GLM-5.2 旧结果、DeepSeek 旧结果和 Pi 的拒绝结论保持只读隔离；通过 G53-4 前不改默认模型。

## 本批不做

- 不实现 GLM-5.3、Flash/Pro 分层或任何真实 Provider 调用；
- 不添加开放域聊天框或假造 Coach 交互；
- 不扩展地区、不采用研究媒体、不修改 Portal/Account 运行时；
- 不改变 Workbench、Auth/RSO、Riot routing、`production_media=0` 或 8E/8F 状态；
- 不重跑完整历史阶段审计。

## 验收命令

```powershell
python scripts/check_project_governance.py
git diff --check
```

README 与状态文档的事实检查以 `docs/project_execution_state.md`、`docs/requirements_change_log.md`、`docs/roadmap.md` 和现有 Agent/Runtime/Harness 测试为准。
