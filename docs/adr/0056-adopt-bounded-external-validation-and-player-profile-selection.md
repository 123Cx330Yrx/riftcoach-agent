# ADR-0056：8E 采用有界真实验证与用户选择的玩家档案

- 状态：Accepted for `8e-productization` preflight（2026-08-23）
- 关联：ADR-0051、ADR-0055、RQ-086

## 背景

8D 的 `EvidenceBundle` 是纯函数、no-I/O 的融合内核。它已经证明来源、版本、
join、freshness、conflict、gap 和 public projection 的规则，但不能证明当前
Riot 网络、账号路由、OP.GG MCP schema 或两者在同一条真实链路中的可用性。

Stage 7 曾经做过一次真实 OP.GG MCP smoke；8E 需要补一次新的、有预算和隐私
边界的真实验证。与此同时，产品不能把某个职业选手或测试账号写成默认玩家，
也不能让旧的 `RIOT_REGION=asia` 部署默认掩盖用户选择的外服地区。

## 决策

### 1. 真实验证是 8E preflight 的独立门

验证门与 8D 公共 exact-SHA CI 分离。一次授权只允许：

1. Riot Account-V1 账号解析；
2. 最近对局 ID 查询，最多 1–3 局；
3. 一局 Match Detail，Timeline 只有在验证需要时才调用；
4. OP.GG MCP `initialize`、`tools/list` 和一个已准入的只读 lane-meta `tools/call`。

不调用 LLM、不发布 Coach、不批量抓取、不无限重试、不重跑 8B holdout。

持久结果只包含次数、状态/安全错误码、延迟、catalog/schema digest、证据 digest、
版本、freshness/provenance 和 fact 数量。禁止保存 API Key、PUUID、原始 Riot/MCP
body、私人比赛正文、Prompt 或异常正文。

真实失败按 `endpoint`、`authentication`、`rate_limit`、`schema`、`network`、
`privacy` 分类；失败不修改 8D 融合规则，也不被解释成产品逻辑失败。

### 2. 玩家是用户选择的档案，不是硬编码账号

产品输入使用 `Riot ID = gameName#tagLine` 和显式 `routing_region`。当前支持
`americas`、`asia`、`europe`、`sea` 四个 Riot regional routing；CN 不在当前
官方公开 LoL routing 列表中，不能通过静默 fallback 假装支持。

每个 owner 可以保存多个玩家档案：

- `self + unverified_claim`：用户声明这是自己的账号；可形成自己的训练目标，
  但必须显示“未验证”，直到未来 RSO/OIDC 完成精确 PUUID 绑定；
- `observed + not_applicable`：公开观察对象，例如职业选手或高分段玩家；只允许
  公开比赛分析和 owner-local 观察备注，不生成对方的私人偏好或训练完成度。

Conversation 创建时固定一个 player subject。相同 PUUID 的 Riot ID 改名可继续；
不同 PUUID 必须创建新 Conversation。前端以后提供 owner-scoped 档案列表与选择，
不会把 ShowMaker、任何职业选手或某个测试 fixture 作为默认账号。

### 3. 旧兼容入口不作为最终玩家选择 UX

现有 `/player-links` 合同已经接受 `riot_id`、`routing_region` 和 `relationship_role`，
可作为新档案接缝。旧 `/reviews/recent` 仍直接接受 Riot ID，且执行组合默认从
环境读取 `RIOT_REGION`；它继续作为兼容路径，但 8E 的最终 UI 必须改为选择已绑定
的 player subject，或补齐显式地区/档案引用，避免把 `asia` 当作隐式用户地区。

## 取舍

| 方案 | 结果 | 原因 |
|---|---|---|
| 继续只用 fixture | 拒绝 | 不能发现真实 endpoint、权限、字段或网络问题 |
| 把真实调用放入公共 CI | 拒绝 | 不可复现、消耗额度、依赖 Key/网络并带来隐私风险 |
| 硬编码 ShowMaker 作为默认 | 拒绝 | 不可扩展、身份语义错误、容易过期 |
| 每次复盘直接用 Riot ID + 环境地区 | 拒绝为最终 UX | 容易查错服，且无法稳定绑定 Conversation/Memory |
| 自动遍历所有地区重试 | 拒绝 | 额外调用、限流和隐私暴露不可接受 |

## 后果与待办

- 8E preflight 必须先取得一个明确的测试 `Riot ID + routing_region`，然后执行一次
  body-free Riot 验证并与新鲜 OP.GG evidence 做离线 replay/fusion。
- 需要一个 owner-scoped player profile list/selection DTO；不急于增加新的运行时框架。
- OP.GG 本次结果仍只能用于 `current_snapshot_recommendation`；没有 patch、source time
  或 upstream TTL 就不能产生 exact-patch claim。
- 真实网络证据是一次观察窗口，不是 SLA、容量或长期 freshness 保证。
- 前端实现继续拆成小批次，先做合同、状态和可访问性，再做高质量动效。
