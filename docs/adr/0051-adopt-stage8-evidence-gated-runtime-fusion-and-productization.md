# ADR-0051：采用证据门控的 Stage 8 可靠运行时、证据融合与产品化路线
- 状态：Accepted for Stage 8 entry design（2026-08-22，用户明确“那开始吧”）
- 范围：只冻结 Stage 8 入口设计、8A–8F 顺序、Core/Advanced 双轨和采用门；不表示
  Multi-Agent、DAG、cancel/resume、SSE、正式 Auth、前端或公网部署已经实现。

## 初学者解释

Stage 7 解决的是“系统能不能用标准 MCP 与外部工具互操作”。Stage 8 要解决的是两个更
具体的问题：第一，一次分析任务在排队、执行、取消、进程中断或恢复后，怎样仍然保持正确；
第二，用户能不能在一个真正的 Web 产品里看到建议来自哪些比赛事实、版本静态数据、Meta
快照和质量门。

Multi-Agent 不是 Stage 8 的必然答案。只有当两个职责拥有独立上下文、工具权限和失败边界，
并行后又能在质量、延迟或隔离性上测出收益，才允许进入产品。否则保留单 Runtime 是正确的
工程结论。

## 背景与当前事实

- Stage 7 已由 `a88fbc4` 与 `fac6fe0` 完成 exact-SHA 公共闭环；OP.GG 已通过标准
  Streamable HTTP 接入，但仍是 partial provenance，不能声称精确 patch 或上游 freshness。
- 6A 已有 PostgreSQL task、原子 claim、Application/Artifact terminal、保守
  `recovery-required` 与人工 recovery CAS，但没有 lease/heartbeat/fencing、自动 reclaim、
  cancel/resume 或 checkpoint。
- 5E 已有进程内 `run/stream`、Runtime Trace、Usage、Artifact 引用和终态提交，但没有 durable
  event log、跨进程 replay 或恢复协议。
- 6B-8 已有 owner-scoped data-only Context、body-free manifest 与 terminal-only assistant/Candidate
  writer；6B-9 已有 owner export、删除、retention 和补偿语义。
- 现有仓库没有正式 React/Next/Vite 前端脚手架；FastAPI、Memory/Training、Run Query、Riot、
  Data Dragon、OP.GG MCP 与 MCP Server 接缝已经存在。

## 决策

### 1. 固定 Stage 8 机器顺序

```text
entry design
  → 8A advanced-adoption-gate
  → 8B conditional-multi-agent-experiment
  → 8C reliable-runtime-core
  → 8D riot-opgg-evidence-fusion-core
  → 8E productization
  → 8F final-evaluation-and-portfolio
```

每个 checkpoint 独立完成初学者教学、TDD、实现或实验、八维证据、本地门禁、独立提交和
exact-SHA 公共 CI。前一项未正式关闭，不进入后一项。

### 2. 8-Core 与 8-Advanced 双轨

`8-Core` 必须完成：可靠任务语义、Riot+OP.GG 分层证据融合、正式 Web 产品纵向、安全/隐私/
备份恢复、完整回归与作品集交付。

`8-Advanced` 至少完成一个证据驱动的高级能力实验。实验可以得到 adopt、partial-adopt 或
reject；reject 仍是合格结论，只要 Bad Case、对照、消融、成本和 ADR 完整。Advanced 默认
候选是 Multi-Agent，DAG、Agentic Retrieval、第三方 Runtime 只能作为候选，不能预先承诺。

### 3. 8A/8B 的采用门

8A 只审计候选，不改产品 Runtime。每个候选必须提供：

1. RiftCoach 可复现的真实 Bad Case 或收益假设；
2. 与当前单 Runtime 的同输入、同工具、同 Harness 对照；
3. 独立上下文、权限和失败边界的证明；
4. 质量、延迟、成本、复杂度、维护和安全指标；
5. 明确的停止条件与不可覆盖实验身份。

8B 只允许一个有界实验切片。先比较单 Agent 串行、条件并行和候选 Multi-Agent；没有独立
收益就拒绝采用。DAG 只有在并行/恢复需求已经被实验证明后，才可进入 8C 的实现范围。

### 4. 8C 先做可靠性，不把复杂编排偷渡成必选

8C 的可靠 Runtime Core 先围绕现有 PostgreSQL task、Runtime Trace、Artifact 和 Harness 建立：

- durable lifecycle event、幂等 event identity 与 replay-safe projection；
- lease/heartbeat/fencing、cancel request、checkpoint 和安全恢复；
- 迟到结果拒绝、重复终态保护、owner/global 背压和 observability；
- 单 Worker/单 Runtime 作为兼容基线；只有 8B 通过才接入多 Agent/DAG executor。

不采用 Redis/Celery/Kafka/Kubernetes 作为默认前提；若真实 Bad Case 证明 PostgreSQL 不足，
必须另立 ADR。

### 5. 8D 的 Riot + OP.GG Evidence Fusion

融合不是把两边 JSON 拼在一起，而是建立 typed、可追溯、可降级的 `EvidenceBundle`：

```text
Riot account/rank/match/timeline facts
 + Riot/Data Dragon versioned static definitions
 + official patch/update facts
 + OP.GG admitted partial MetaEvidence
 → typed EvidenceBundle
 → bounded Coach recommendation
 → UI evidence projection
```

Riot 官方事实优先，Data Dragon 负责版本化静态定义，OP.GG 只提供声明允许范围内的当前快照
Meta。join 必须显式声明键（champion、position、region、queue、patch 等）和 provenance；
OP.GG 缺 patch 时不能继承同日 Riot patch。冲突、不一致或过期时保留来源并降级，不静默覆盖。

### 6. 8E 的 Web 产品与 MotionSites 资源门

采用自主 React 设计系统，外部资源只作为候选参考/局部 Prompt/资产来源：

- Radix/shadcn：可访问的交互底座；
- Motion：常规布局和状态动画；
- ECharts：趋势、对照和 Rift Timeline；
- React Bits/Aceternity/Uiverse：逐项审查后精选少量效果；
- Anime.js：只有复杂 SVG 序列确有收益时才加入；
- MotionSites：公开目录和预览用于筛选，付费 Prompt/资产按单项获取，不作为生产组件库；
- Image2/Photoshop：分别用于生成/编辑和精修素材，均不替代 React 实现。

MotionSites 的采用门固定为：公开 URL/预览、适配页面、技术栈、许可证/购买权限、移动端
替代、性能预算、可访问性、依赖数量和退出方案。用户提供的 Excel 只作离线候选库，不进入
产品运行时，也不能取代官网当前目录核验。

8E 的五个产品模块是：电影感 Riot ID 入口、近期复盘工作台、Rift Timeline、Evidence/Agent
Trace 抽屉、Training Plan/Progress。首页动效预算最高；工作台动效服务于状态理解；所有页面
必须有 loading/empty/error/degraded/no-evidence 状态、键盘焦点和 reduced-motion 方案。

RQ-094 后续补齐本入口 ADR 未持久化的视觉职责：`Rift Awakening` 入口与 `Esports Intelligence`
工作台组成 `Cinematic Portal → Broadcast Workbench`，`Void Holographic Lab` 只作受限 Hero 实验。
同一纠偏要求 8F 前另设 OP.GG useful-breadth gate，并完成一次实际覆盖 Riot match、Data Dragon、
official patch、OP.GG、训练建议和 UI Evidence 的 body-free golden slice；8D pure kernel 与当前
`degraded/unjoined` replay 不单独满足这项完整纵向验收。

### 7. 安全与隐私边界

- 前端只收到 owner-scoped、allowlisted DTO；不返回 PUUID、Key、路径、Prompt、原始 MCP body、
  原始 Provider 错误或 chain-of-thought；
- Evidence 抽屉展示来源、版本、digest、状态和安全工具事件，不展示隐藏推理；
- SSE 只发送可重放的 body-free lifecycle/evidence events；断线以后通过 cursor/replay 恢复，
  不能把浏览器连接当作任务真相；
- Auth/RSO、CORS、HTTPS、限流、备份副本擦除和公开隐私说明是 8E/8F 的硬门，不在入口设计中
  假设已完成。

## 备选方案

### A. 直接采用 Multi-Agent/DAG 框架

拒绝。它把并行、权限、恢复和第三方依赖一次引入，无法知道收益来自哪里，也违背现有技术
采用门。

### B. 先做一个普通 Dashboard，再以后补可靠运行时

拒绝。前端会被迫围绕不稳定的 task/event 语义重写，且无法从第一天展示真实 evidence boundary。

### C. 可靠 Runtime Core + 条件 Advanced + 证据融合 + 设计系统（采用）

采用。它保留当前 Python/PostgreSQL/Harness 资产，让高级能力用实验取得资格，同时把用户真正
能看到的前端和证据链放入同一产品化顺序。代价是入口设计较重，且 8A/8B 可能以 reject 收尾。

## 验收与影响

- Entry design 完成后，canonical 只交接 `8A-advanced-adoption-gate`，不自动进入实验实现；
- 每个 checkpoint 的代码、理解、参考资料和公开部署四条进度线分别记录；
- Stage 8 关闭前必须有：可靠恢复测试、Riot/OP.GG provenance 测试、桌面/移动截图、键盘与
  reduced-motion 证据、失败态截图、部署/备份/安全说明和 final eval；
- 本 ADR 不授权读取 Riot/Provider Key、真实模型调用、付费资源购买或公网部署。
