# 5D-7 Batch B 初学者复核：Prompt/Context 实验身份

## 1. 我们刚才到底搭建了什么

这一批没有让 Agent “更聪明”，而是给后续实验安装了可验证的控制变量。

把模型对照想象成一次考试。如果同学 A 和同学 B 使用的题目、评分标准、允许查阅的
资料都不一样，那么比较总分没有意义。RiftCoach 的“题目和规则”不只是一段 Prompt，
还包括 Skill、Context、工具说明和 Evaluation。

现在系统会先生成一份安全的 Prompt/Context 快照：

```text
Skill Manifest + SKILL.md
        |
Context Policy + 实际 section/messages
        |
knowledge.search 工具合同
        |
Evaluation Schema + Prompt 行为探针
        v
分层 SHA-256 快照
        |
Dataset 声明 --------精确匹配-------- 当前重新计算值
        |
        v
离线实验入场券（0 次 Provider 调用）
```

只有这些身份全部一致，后续运行才有资格被称为“同一实验条件下的候选”。

## 2. Prompt、Context 和 Tool 不是一回事

- **Prompt**：告诉模型任务、规则和输出要求的文本。
- **Context**：本次请求实际交给模型的全部上下文，包括指令、事实、用户请求和知识。
- **Tool contract**：模型看到的工具名称、说明和参数 Schema。它会影响模型是否以及怎样
  调用工具，因此也是输入条件。
- **Evaluation contract**：评分模型看到的事实投影、审查规则和必须返回的 JSON Schema。

`ContextBuilderV1` 已经负责把这些内容按信任级别组装成 system/user 消息。Batch B 没有
重写它，只读取其真实结果并生成指纹。

## 3. 为什么需要两层指纹

组件层回答“规则有没有变化”：

```text
skill_manifest
skill_instructions
context_contract
knowledge_tool_contract
evaluation_schema / fact_pack / prompts
```

案例层回答“这一条题实际喂了什么”：

```text
Summary Artifact 摘要
确定性报告摘要
用户表达和 focus 摘要
选中/省略的 section
每个 section 内容摘要
最终 system/user 消息摘要
Context 预算
```

如果只存一个总摘要，发现变化后无法定位；如果只存组件，又无法证明具体案例的事实和
消息没有变化。两层一起才能兼顾可定位性和可重复性。

## 4. SHA-256 在这里做什么，不做什么

它做的是内容承诺：同样的规范内容会得到同一 64 位十六进制摘要；有效内容改变，摘要
也会改变。它不是加密，不能让一个已知短文本保密。因此我们的公开快照根本不保存完整
Prompt 或事实，只保存摘要和必要的安全元数据。

代码还避免了两类假漂移：

- 不哈希整个 Python 文件，注释或 import 排序不会影响实验身份；
- 对实际会被 `.strip()` 的 Skill 指令也先规范化，末尾空行和 CRLF/LF 不会冒充语义变化。

Dataset 文件身份同样来自规范化 Pydantic JSON，而不是操作系统原始换行字节。

## 5. 数据流与控制流分别是什么

数据流：

```text
fixture -> typed Skill input -> Artifact commitments
       -> Context sections -> rendered messages -> digests
```

控制流：

```text
严格加载 Dataset
-> 严格加载冻结快照并验证其自摘要
-> 从当前代码和 fixture 重新构建快照
-> 当前值 == 冻结值
-> Dataset 声明 == 快照身份
-> admitted=true
```

任一环不一致都会在 Provider 之前失败，不会生成一份看似正式但条件已经变化的实验结果。

## 6. 测试证明了什么

- 两次构建得到完全相同的模型和 JSON；
- 修改 `SKILL.md` 的有效内容会改变对应组件和总摘要；
- 修改 Summary 事实只改变案例 Context，不改变组件合同；
- 伪造快照自摘要或塞入 `raw_prompt` 会被严格 Schema 拒绝；
- Dataset 1.1 与 Candidate/Result 强绑定快照 ID 和摘要；
- CLI 临时输出和仓库冻结 admission 完全一致；
- Dataset 与冻结快照必须位于项目内，项目外输入会在读取前被拒绝；测试输出允许写入
  临时目录，便于逐字节复现而不污染仓库；
- 外部 Provider 调用固定为 0。

这些证据不证明 Prompt 好、模型强、注入攻击已防住。它只证明后续做这些实验时，测试
条件不会悄悄变化。

## 7. 当前限制与下一步

- 当前快照只冻结 `recent-form-review` 的 demo 案例；Batch C 才扩展为多案例。
- Evaluation 行为探针覆盖当前实际入口，但不是对任意 Python 分支的形式化证明。
- 当前没有运行模型级恶意用户/RAG/Tool Observation 注入。
- 当前 admission 不是 5E Trace；它不记录某次真实运行的事件、耗时和调用链。
- 当前没有第二 Provider，也没有模型排名。

下一批应使用这张入场券建立多个可执行 development 案例，分别验证工具选择、事实、
引用和模型级注入边界；仍要先离线控制器和 Fake Provider，再决定有限真实调用。

## 8. 面试时怎样准确描述

可以说：

> 为避免 Prompt 或 Context 静默漂移污染模型对照，我设计了实验前置身份层：从实际
> Skill、Context Builder、工具合同和 Evaluation 合同生成组件级与案例级 SHA-256
> 快照，Dataset 和 Candidate 必须强绑定该快照，且在 Provider 调用前重新计算并失败
> 关闭。公开快照只保存摘要与安全元数据。

不能说：

- “已经完成 Prompt 自动优化”；
- “已经证明 GLM/DeepSeek/Qwen 哪个更好”；
- “已经彻底防住 Prompt Injection”；
- “已经实现完整 Agent Trace”；
- “admitted=true 表示真实模型领域能力通过”。
