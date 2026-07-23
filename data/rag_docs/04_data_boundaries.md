---
source_id: 04_data_boundaries.md
knowledge_type: data_boundary
version: evergreen
updated_at: 2026-07-23
positions: ALL
---

# 数据边界与安全规则

## 当前可用数据

Riot API 提供玩家公开账号、对局详情和时间线事实。Data Dragon 提供英雄、装备、符文与召唤师技能的静态名称和资源。它们不提供当前版本英雄胜率、登场率、禁用率、主流出装胜率或对位强度。

## Meta 数据边界

版本 Meta 需要来自独立且有来源标识的数据工具，例如后续接入的 OP.GG MCP。未调用 Meta 数据源时，报告不得声称某英雄当前版本强势、某套符文是主流或某件装备胜率更高。

## 公平竞技边界

RiftCoach 只做赛后复盘、公开数据分析与训练建议，不提供实时隐藏信息、敌方冷却追踪、自动操作、脚本或其他可能产生不公平优势的功能。
