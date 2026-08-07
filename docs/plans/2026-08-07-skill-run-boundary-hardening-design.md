# 5D-1 Skill Run Boundary Hardening 设计

## 1. 结论先行

5D-1 在 Router 与未来的 Context Builder 之间建立一个 fail-closed 的执行入口。只有
当以下四组事实彼此一致时，入口才返回 `ValidatedSkillExecution`：

1. Router 明确返回 `selected`，并锁定 Skill 名称与版本；
2. Catalog 此刻仍能取到同名、同版本的 `LoadedSkill`；
3. 原始 payload 能被这个 Skill 自己的 Pydantic input model 验证；
4. `run_id` 与两份输入内容的 SHA-256 承诺和实际规范字节完全一致。

本检查点不会构造 Prompt、`AgentRunRequest`，不会调用 AgentLoop、Tool、Provider，
也不会创建 Harness run 或发布报告。

## 2. 初学者理解：为什么需要“执行边界”

Router 的工作类似前台分诊：它判断用户应进入“近期复盘”还是“单局复盘”。但分诊
结束到真正执行之间仍可能发生漂移：

- 只保存名字，Catalog 中的 Skill 已升级到另一个版本；
- 调用方提交的输入不属于被选中的 Skill；
- 同一个 `run_id` 被解释成路径，逃出预期运行目录；
- 输入在计算摘要后被改动，执行的已经不是原先承诺的事实。

因此执行前需要一道验票闸机：Router 只能推荐身份，真正权限、预算与模型类型仍要
从当前 Catalog 的已验证 Skill 重新取得。5D-1 先把身份和输入锁住，5D-2/3 才能安全
地用它们构造上下文和 Agent 请求。

## 3. 数据与控制流

```text
RouterDecision(selected name@version)
           +
SkillExecutionRequest
  - safe run_id
  - user_utterance
  - raw input_payload
  - input_artifact_binding
           |
           v
SkillExecutionBoundary.validate(catalog)
  1. selected 检查
  2. Catalog name@version 检查
  3. Skill input_model 校验
  4. 用 Harness 规范字节重新算摘要
  5. 对比 run_id、kind、schema_version、sha256
           |
           v
ValidatedSkillExecution
  - LoadedSkill
  - typed_input
  - safe run_id
  - user_utterance
  - verified input binding
```

任何一步失败都抛出边界错误，不尝试选择“最接近”的 Skill，也不进入模型调用。

## 4. 合同设计

### 4.1 Router 版本绑定

`RouterDecision` 增加 `selected_skill_version`：

- `selected`：名称和版本都必须存在；
- `ambiguous` / `rejected`：二者都不得携带 selected version；
- `DeterministicSkillRouter` 从命中的 `SkillRouteCandidate.version` 原样填入。

版本不是权限来源。执行边界仍必须从 Catalog 重新加载同名 Skill，并验证版本一致；
之后的工具白名单与预算只能来自该 `LoadedSkill.manifest`。

### 4.2 安全 run ID

建立一个共享 `normalize_run_id()`，同时供 `RunManifest.new()`、`FileRunStore` 和
Skill 执行合同使用。V1 规则为：

- 去除首尾空白后长度为 1 到 128；
- 只允许 ASCII 字母、数字、点、下划线和连字符；
- 首字符必须是字母或数字，末字符不能是点；
- 拒绝 Windows 保留设备名，包括带扩展名的形式；
- 因为斜杠、反斜杠、冒号和空格均不在允许集合中，不能形成路径或盘符。

共享校验防止 Manifest 认为合法、Store 却认为非法，或反过来。

### 4.3 输入 Artifact 内容承诺

`SkillInputArtifactBinding` 包含：

- 同一安全 `run_id`；
- Player Summary 的 kind、schema version 与 SHA-256；
- Deterministic Report 的 kind、schema version 与 SHA-256。

摘要必须基于未来 Harness 实际写入的规范字节：

```text
Player Summary:
json.dumps(ensure_ascii=False, indent=2) + newline，UTF-8

Deterministic Report:
验证后的精确字符串，UTF-8
```

这不是新建另一类 Artifact，也不提前写磁盘；它是 5D-5 落盘前的内容承诺。5D-5
仍需把实际 Artifact record 的 `run_id/kind/schema_version/sha256` 与本绑定再次核对。

### 4.4 Skill I/O 文本加固

两个现有 Skill 对相同字段采用一致规则：

- 输入 `deterministic_report` 去除首尾空白并拒绝空白值；
- 输出 `run_id` 使用共享安全 run ID；
- 非空 `report` 去除首尾空白并拒绝空白值；
- `evidence_source_ids` 与 `warnings` 逐项去空白，拒绝空项和重复项；
- 单局 `target_match_id` 继续去空白并拒绝空白值。

`published/degraded` 仍必须有 report，`rejected` 仍不得暴露 report。本轮不增加新的
评分发布规则，以免越过 5D-5 的 terminal output 组合职责。

## 5. 备选方案与取舍

### 只比较 Skill 名称

无法发现路由后 Manifest 升级或替换，拒绝。

### 把 Manifest、权限与预算复制进请求

调用方可以伪造安全控制面，也会形成第二份真相源，拒绝。执行边界只接受业务输入，
权限和预算由后续 Compiler 从经过身份核对的 `LoadedSkill` 读取。

### 5D-1 直接创建 FileRunStore Artifact

这会提前引入 Harness 生命周期、重复运行处理和失败清理，跨入 5D-5。当前只保存与
真实 Artifact 字节一致的内容摘要，并明确记录后续还需落盘复核。

### 直接依赖 LangGraph / Agent SDK 的 run 对象

第三方 run 对象不能替代本项目的 Skill、Artifact 和 Harness 身份合同，且 5F 才做
框架采用实验，当前不采用。

## 6. 测试如何证明行为

### Skill 合同测试

- 两个输入拒绝空白确定性报告并返回去空白文本；
- 两个输出拒绝空白/非法 run ID、空白报告、空白或重复来源/警告；
- 原有 published/degraded/rejected 边界保持不变。

### Router 合同测试

- selected 必须有版本，非 selected 不得有版本；
-真实 Router 返回 Catalog 候选的准确版本；
- 既有选择、拒绝、歧义结果不改变。

### run ID 测试

- Manifest、Store 与执行请求对合法 ID 得到同一规范值；
- 路径穿越、绝对路径、保留名、空格、超长值都被拒绝。

### 执行边界测试

- 两个真实 Skill 都能形成 `ValidatedSkillExecution`；
- rejected/ambiguous 决策不能执行；
- 名称不存在、版本漂移、错误 input model 都在模型调用前失败；
- run ID 不一致、摘要被修改、kind/schema/digest 伪造均失败；
- 修改原 payload 后不能改变已经验证得到的 typed input 快照。

## 7. 本轮完成后仍然缺什么

- 还没有按 Skill 裁剪近期/单局上下文；
- 还没有信任标签和 token 预算；
- 还没有把 Manifest 编译成 `AgentRunRequest`；
- 还没有调用 ToolRuntime、AgentLoop 或真实 Provider；
- 还没有创建 Harness Artifact 或 terminal Skill Output；
- 还没有统一 Trace、Session、Memory、MCP、Multi-Agent 或 Web 部署。
- 当前边界验证 `user_utterance` 非空，但尚未用统一 Runtime event/trace 证明它与最初
  产生 `RouterDecision` 的 `RouterRequest` 是同一条不可变输入；调用方目前必须在
  同一次应用流程中传递二者，5E 再固化完整运行来源链。

因此 5D-1 完成后的准确表述是：

> RiftCoach 已实现受限 Skill 执行前的身份、输入和内容完整性边界；真正的上下文
> 编译、Agent 执行与 Harness 发布组合仍在后续 5D 检查点。
