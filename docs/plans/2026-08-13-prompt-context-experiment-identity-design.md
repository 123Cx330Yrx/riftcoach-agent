# 5D-7 Batch B：Prompt/Context 实验身份设计

## 1. 这一批解决什么问题

Batch A 已经规定“评什么”：一个领域案例必须分别观察 Provider/Agent、Tool、
Evidence、Evaluation、Terminal 和 Resources。但它还没有充分规定“拿什么去评”。

当前 Dataset 只保存三个手写标识：

```text
recent-form-review@0.2.0
context-builder-v1
coach_evaluation@1.0.0
```

如果维护者修改了 `SKILL.md`、内部 Context Policy、上下文渲染，或 Evaluation
Prompt/Schema，却忘记升级版本字符串，两个实际不同的实验仍会被当成同一候选比较。
模型分数变化时，我们就无法判断到底是模型变了，还是输入规则变了。

Batch B 要为后续开发集、保留集和 Provider 对照建立一个离线、可复读、在外部调用前
失败关闭的实验入场门。它不改善报告质量，也不调用模型。

## 2. 底层原理

可重复实验必须控制变量。对 RiftCoach 来说，Provider 只是一个变量，实际输入还包括：

- Skill Manifest 中的权限、预算和质量门禁；
- `SKILL.md` 的任务指令；
- Context Policy、事实投影、section 选择和 system/user 渲染；
- Evaluation 的系统指令、结构化 Schema、评测/修复/修订模板；
- 当前案例的 Summary、确定性报告、用户请求和选项。

SHA-256 在这里不是加密 Prompt，而是内容指纹：同样的规范字节必然得到同样的摘要；
任意一个有效字符改变，摘要极大概率改变。公开快照只保存摘要和安全元数据，不保存完整
Prompt、事实内容、模型正文、思维链、异常、request ID 或密钥。

## 3. 三种方案比较

### 方案 A：只使用人工版本号

优点是实现最简单。缺点是版本号与正文没有机器绑定；忘记升版本就会产生静默漂移。
拒绝。

### 方案 B：只哈希最终 system/user 消息

它能发现差异，但不能定位差异来自 Skill、Policy、事实输入还是 Evaluation；不同案例的
事实本来就不同，也不应被误判为组件合同变化。拒绝作为唯一身份。

### 方案 C：组件身份 + 案例 Context 身份

采用。组件层分别记录 Skill、Context Policy 和 Evaluation 的语义指纹；案例层记录
输入 Artifact commitment、实际选中/省略 section、section 内容摘要、最终消息摘要和
Context 预算。这样既能发现漂移，也能说明漂移发生在哪一层。

不哈希整个 Python 文件。注释、import 排序等无行为改动不应让实验失效；指纹只覆盖
实际生效的合同产物。

## 4. 组件与合同

### 4.1 `PromptContextSnapshot`

一个快照包含：

```text
snapshot identity
  snapshot_id / schema_version / self_sha256

declared contracts
  Skill name/version
  Context contract ID
  Evaluation contract ID

component fingerprints
  Skill manifest
  Skill instructions
  Context internal policy
  knowledge.search version/description/schema/policy
  Evaluation response schema
  Evaluation fact-pack projection probe
  Evaluator system prompt
  Evaluation prompt probe
  Evaluation repair prompt probe
  Reviser system prompt
  Revision prompt probe

case context fingerprints
  input Artifact digests
  user utterance / typed option digests
  selected and omitted sections
  section metadata + content digests
  rendered system/user message digests
  estimated and maximum context tokens
```

Evaluation template不能直接对 Python 源码做哈希，所以使用固定、安全的哨兵事实和报告
调用真实 builder，再哈希其输出。模板中任何有效规则或 Schema 变化都会改变探针摘要。

### 4.2 Domain E2E 合同升级

Batch A 的 Dataset/Candidate/Result 从 Schema `1.0` 升到 `1.1`，development Dataset
版本从 `1.0.0` 升到 `1.1.0`。案例和标签不变；变化仅是 `ContractSnapshot` 新增：

```text
prompt_context_snapshot_id
prompt_context_snapshot_sha256
```

Candidate 必须与 Dataset 的完整快照相等，否则分层评测在读取观测前失败。旧 Batch A
证据仍在 Git 历史中；当前 development 基线会在零外部调用下重新生成。

### 4.3 `DomainExperimentAdmission`

可重复入口同时核对：

- Dataset ID、版本和规范 Pydantic JSON SHA-256；
- 已提交 Prompt/Context 快照的内部自校验；
- 从当前 Skill、fixture 和 builder 重新计算的快照是否逐字段相等；
- Dataset 声明的 Skill/Context/Evaluation 和快照是否一致。

全部通过才产生 `admitted=true` 的离线 admission。它记录 `external_provider_calls=0`。
后续 Batch C 的候选运行必须先取得这张入场券。

## 5. 数据流与控制流

```text
validated Skill package --------+
example Summary / report -------+--> SkillExecutionBoundary
synthetic request / focus -------+             |
                                                v
                                      ContextBuilderV1
                                                |
                                                v
                                   component + case digests
                                                |
frozen snapshot JSON ---------------------------+--> exact comparison
domain Dataset JSON --> strict load + SHA ------+        |
                                                         v
                                             offline admission
                                             external calls = 0
```

数据流回答“哪些内容被变成摘要”；控制流回答“哪些检查通过后才能进入下一步”。
任何不匹配都在 Provider 创建或调用之前抛出安全错误，不写部分正式 admission。

## 6. 本批实现与不实现

实现：

- 严格 Pydantic 快照与 admission 合同；
- 规范 JSON/text SHA-256；
- 真实 Catalog、Router、ExecutionBoundary 和 ContextBuilder 的离线快照构建；
- Evaluation Schema 和模板行为探针；
- Dataset/Candidate/Result 1.1 的强绑定；
- 可重复 CLI、冻结快照和离线 admission 基线；
- 漂移、路径、Schema、Prompt 泄漏和零外部调用测试。

不实现：

- 不调整任何 Prompt 内容或 Context 选择策略；
- 不运行真实 Provider、Tool 或 Judge；
- 不创建 held-out，不比较 GLM/DeepSeek/Qwen；
- 不实现模型级注入案例；该工作属于 Batch C；
- 不实现 5E 的统一 Trace、Usage 或生产日志；
- 不进入 5D exit review。

## 7. 非功能要求与失败模式

- **可重复性**：相同仓库合同和 fixture 生成逐字节相同 JSON。
- **可定位性**：组件和 section 分开摘要，不能只返回一个总哈希。
- **安全性**：公开文件不包含 Prompt/事实正文、模型输出、异常、request ID 或 Key。
- **失败关闭**：快照、Dataset 或声明合同任一漂移时，不产生 admitted 结果。
- **路径安全**：CLI 读取的 Skill、fixture、Dataset 和快照必须位于项目根目录内。
- **成本**：整个 Batch B 外部 Provider 调用数固定为 0。
- **维护性**：有效 Prompt/Context 变化必须显式升级合同和 development Dataset；不能
  通过重写冻结文件掩盖差异。

## 8. 测试怎样证明它工作

1. 先写红灯测试，证明当前不存在快照模块和强绑定字段。
2. 重复构建两次，断言完整模型和 JSON 字节一致。
3. 复制 Skill 包并只改 `SKILL.md` 一个有效字符，断言组件和总摘要改变，入场失败。
4. 改 fixture 事实，断言 Artifact、section 和 message 摘要改变，但组件合同不变。
5. 改 Dataset 或伪造快照自摘要，断言在 admission 输出前失败。
6. 把 `raw_prompt`、异常或 request ID 塞进公开 Schema，断言 Pydantic 拒绝。
7. CLI 生成临时结果并与冻结 admission 比较，断言输出完全一致且外部调用为 0。
8. 最后运行全量 pytest、两套 RAG 门禁、compileall、Harness dry-run、安全和治理门禁。

这些测试证明实验身份和入口可重复，不证明 Prompt 质量、真实模型能力或未知攻击已经
通过。后者需要 Batch C/D 的新案例与受控运行。

## 9. 面试安全表述

> 我把 Prompt/Context 当作实验依赖而不是散落字符串。系统在 Provider 调用前，从实际
> Skill、Context Builder 和 Evaluation 合同生成分层 SHA-256 快照，并与 Dataset 的
> 冻结身份核对；快照只保存摘要和安全元数据。这样同一评测集比较模型时，可以证明
> Skill、上下文和评测规则没有静默变化，同时避免把完整 Prompt 或运行原文写入公开结果。
