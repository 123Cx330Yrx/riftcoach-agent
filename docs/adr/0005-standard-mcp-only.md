# ADR-0005：只将标准协议实现称为 MCP

- 状态：接受
- 日期：2026-07-16

## 背景

EchoMind 和 AGI-Saber 中存在以 MCP 命名的本地工具管理或普通 HTTP 适配逻辑，但不具备完整的协议初始化、工具发现、工具调用和会话管理。

## 决策

RiftCoach 的内部工具系统称为 Tool Runtime。只有通过标准 MCP 互操作验证的 Client/Server 才称为 MCP，并在阶段 7 实现。

## 影响

项目描述更加准确，也为后续 OP.GG 动态工具发现和 RiftCoach 能力对外暴露建立清晰边界。
