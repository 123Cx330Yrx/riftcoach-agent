# 5D-6b Production Zhipu Adapter Mapping 教学复核

## 1. 这一步解决了什么

在本检查点开始前，RiftCoach 已经有统一的 `ChatRequest`、`ChatResponse`、
`ToolSpec`、`ToolCall` 和 `StructuredResponseContract`，真实 GLM-5.2 微探针也已经证明
文本、JSON mode、Function Calling 与 Tool Observation 协议在 disabled-thinking 下
可用。但生产 `ZhipuProvider` 仍只会发送 role/content 并读取纯文本。

本步补上的不是新的 Agent Loop，而是 Provider Adapter 的双向翻译：

```text
Provider-neutral ChatRequest
→ Zhipu 请求编码
→ OpenAI-compatible SDK
→ Zhipu 响应解码与安全校验
→ Provider-neutral ChatResponse
```

上层 Skill、AgentLoop、ToolRuntime 和 Harness 不需要知道智谱字段格式。

## 2. 请求如何映射

| 统一合同 | 智谱请求 | 关键边界 |
|---|---|---|
| system/user | role + content | 保持原角色与文本 |
| assistant ToolCall | assistant + `tool_calls` | 参数规范序列化为 JSON object 字符串 |
| tool observation | tool + `tool_call_id` + content | 保持与原调用 ID 的关联 |
| ToolSpec | function tool | 名称、描述和 object parameters |
| AUTO | `tool_choice=auto` | 允许模型自行决定是否调用 |
| NONE | 不发送 tools/tool_choice | 这一轮明确禁用工具 |
| REQUIRED | 调用前拒绝 | 官方合同未准入，不能偷偷降为 AUTO |
| response contract | `response_format=json_object` | 严格 Schema 仍由 5D-6a 本地 Pydantic 掌握 |

结构化输出和 Tool Calling 的单项能力都已映射，但两者同一请求组合尚无真实准入证据，
因此 Adapter 会在 SDK 调用前拒绝该组合，而不是从两个 true 的 capability flag 推导出
未经验证的组合能力。

所有生产请求显式发送 `thinking.type=disabled`。原因不是禁止模型推理，而是当前统一
Runtime 不保存或回传厂商 reasoning state；工具多轮若依赖隐藏状态，就无法做到无损、
可审计的协议回放。

## 3. 为什么需要工具名称别名

RiftCoach 的内部工具名是有领域层级的，例如：

```text
knowledge.search
```

智谱函数名只接受字母、数字、下划线和连字符，所以 Adapter 为每个请求建立可逆表：

```text
knowledge.search  ↔  knowledge_search
```

编码 ToolSpec 和历史 assistant ToolCall 时使用厂商别名，解码响应时恢复内部名称。
Manifest、ToolRegistry 和 AgentLoop 始终只认识 `knowledge.search`。若两个内部名称映射
到同一别名，Adapter 在 SDK 调用前 fail closed，避免把结果路由给错误工具。

## 4. 响应为什么必须严格解码

厂商返回的 ToolCall 不是可信代码输入。Adapter 只接受：

- 非空且规范化后唯一的调用 ID；
- `type=function`；
- 本请求别名表中存在的函数名；
- 可以解析为 JSON object 的 arguments；
- 当前已准入的单个 ToolCall，且 `finish_reason=tool_calls` 与调用存在性一致。

非 JSON、JSON array、未知别名、空名称、重复 ID、多个并行调用和非字符串 content
都会转换为脱敏的 `ProviderResponseError`。参数是否满足具体工具 Schema 仍由
ToolRuntime 校验，Adapter 不复制它的职责。

## 5. 测试证明了什么

本步采用测试先行：旧实现首先得到 `11 failed, 11 passed`，失败点对应工具、结构化
输出、Thinking 和坏响应边界；实现后：

- Zhipu/Provider/Structured/AgentLoop 聚焦回归：`73 passed, 50 subtests passed`；
- 完整本地回归：`405 passed, 103 subtests passed`；
- compileall、`git diff --check` 与项目治理预检通过。

这些是离线 Fake SDK 和跨模块回归证据，证明翻译规则与失败边界成立。它们还没有证明
生产 Adapter 对真实 GLM 请求能完整往返，也没有证明真实 RiftCoach 报告质量。

## 6. 当前边界与下一步

当前 Adapter 可以为下一次有界真实协议切片临时声明：

```text
text_chat = true
tool_calling = true
structured_output = true
parallel_tool_calls = false
```

下一步仍属于 5D-6b：用同一生产 Adapter 真实执行一个 Provider-neutral structured
request，以及 `AgentLoop + fixed read-only tool` 的工具往返。它不会立即进入真实
recent-form 领域报告、第二 Provider 或 5D-7 Prompt E2E Evaluation。

GLM 是首个基准实现，不是永久厂商选择。DeepSeek、Qwen 等候选只有在既定模型选择门
打开后，才能用同一任务、Prompt、工具合同和评价器比较质量、延迟、成本与稳定性。

## 7. 面试中的准确表述

可以说：

> 我实现了 Provider-neutral 模型合同与智谱生产 Adapter 的双向映射。Adapter 将统一
> 消息、JSON mode 和 Tool Calling 翻译为厂商协议，并用请求级可逆别名隔离函数名
> 约束；未知别名、坏参数、重复或并行调用会 fail closed。上层 AgentLoop 和 Skill
> 不依赖智谱 SDK，因此后续 Provider 可在相同合同和评测下替换。

暂时不能说：

> GLM 已经通过 RiftCoach 真实领域报告准入，或者系统已经自动选出所有厂商中的最佳模型。
