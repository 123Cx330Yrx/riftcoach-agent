# 3G-3：Provider Registry 与配置选择

## 1. 为什么有 Provider 接口还需要 Registry

`LLMProvider` 解决的是：

> 不同厂商适配器怎样用同一个 `chat()` 接口工作。

`ProviderCapabilities` 解决的是：

> 某个适配器当前真正实现了哪些能力。

但系统仍然需要回答：

```text
当前配置了哪些 Provider 实例？
每个实例使用什么模型？
默认使用哪个实例？
显式指定的实例是否存在？
哪些实例满足当前请求？
```

如果没有 Registry，上层代码容易直接创建：

```python
ZhipuProvider(...)
```

这样 Harness、Skill 或 API 就重新依赖具体厂商。3G-3 用 `ProviderRegistry` 把“实例目录与选择”从业务层分离出来。

## 2. Provider 类型、模型和注册 ID 的区别

三个名称承担不同职责：

| 名称 | 示例 | 含义 |
|---|---|---|
| `provider_name` | `zhipu` | 厂商适配器类型 |
| `model_name` | `glm-5.2` | 该实例实际调用的模型 |
| `provider_id` | `zhipu-quality` | RiftCoach 配置中的稳定实例 ID |

同一家厂商可以登记多个实例：

```text
zhipu-fast    → zhipu / glm-flash
zhipu-quality → zhipu / glm-5.2
```

因此不能只用 `provider_name` 当 Registry 主键。

`provider_id` 只允许小写字母、数字、点、下划线和连字符，避免环境变量、日志、URL 和数据库中出现多种不一致写法。

## 3. Registry 的五项职责

### `register(provider_id, provider)`

登记一个已经完成配置的 Provider 实例。

它会拒绝：

- 重复 ID；
- 非法 ID；
- 不符合 `LLMProvider` 契约的对象。

### `set_default(provider_id)`

显式设置默认实例。Registry 不会因为“只注册了一个”就自动把它设为默认，避免启动配置缺失被悄悄掩盖。

### `resolve(provider_id=None)`

- 有显式 ID：解析该实例；
- 没有显式 ID：解析默认实例；
- 不存在或没有默认项：返回安全、结构化错误。

### `select(request, provider_id=None)`

先解析实例，再运行 3G-2 能力协商。成功结果包含：

```text
provider_id
provider
CapabilityNegotiation
```

### `compatible_provider_ids(request)`

列出满足请求能力的候选 ID。它只提供事实，不替 Harness 做最终选择。

## 4. 为什么不自动 Fallback

假设：

```text
默认 Provider：text-only
另一个 Provider：tool-ready
当前请求：需要 Tool Calling
```

3G-3 的行为是：

```text
select(request)
→ 默认实例能力不足
→ ProviderCapabilityError
```

它不会自动切到 `tool-ready`。调用方可以先查询：

```python
registry.compatible_provider_ids(request)
```

再由后续明确的路由策略决定是否切换。

这是为了保留可解释性。真正的自动路由还需要同时考虑：

- Skill 是否允许该 Provider；
- 成本和延迟预算；
- 模型健康状态；
- 数据合规和地域要求；
- 同一业务评测是否通过；
- Fallback 是否会改变语义。

这些不属于一个简单目录的职责。

## 5. 配置加载

新增配置：

```env
LLM_PROVIDER=zhipu
LLM_DEFAULT_PROVIDER=zhipu
```

当前两者相同，但语义不同：

- `LLM_PROVIDER` 是旧配置中的厂商类型，也作为兼容性回退；
- `LLM_DEFAULT_PROVIDER` 是 Registry 的默认实例 ID。

加载优先级：

```text
LLM_DEFAULT_PROVIDER
→ LLM_PROVIDER（兼容旧环境）
→ zhipu（当前开发默认值）
```

`create_provider_registry()` 接受已经构造好的 Provider Mapping，然后应用默认项。这样 Registry 本身不依赖环境变量，也不负责创建 SDK Client。

## 6. 完整启动关系

```text
环境变量
   │
   ├── load_zhipu_settings()
   │        │
   │        ▼
   │   create_zhipu_provider()
   │
   └── load_provider_registry_settings()
            │
            ▼
create_provider_registry({"zhipu": provider}, settings)
            │
            ▼
      ProviderRegistry
```

这里有三层分工：

1. 厂商 Settings 验证密钥、Base URL、模型和超时；
2. Provider Factory 创建 SDK Client 与适配器；
3. Registry 登记实例并管理显式选择。

## 7. 安全边界

`ProviderDescriptor` 只暴露：

```text
provider_id
provider_name
model_name
capabilities
is_default
```

它不暴露 API Key、Client、Base URL 或 Prompt。以后 API 展示可用模型时，应使用 Descriptor，不应序列化 Provider 对象。

## 8. 当前尚未实现什么

3G-3 不能声称已经实现：

- 第二 Provider；
- 智谱 Tool Calling SDK 映射；
- 基于价格、延迟或质量的路由；
- Provider 健康检查；
- 自动 Fallback；
- 动态热注册；
- 多租户 Provider 配置；
- Agent Loop。

下一步 3G-4 会完成智谱 Tool Calling 映射，让当前 `ZhipuProvider` 的 `tool_calling` 从“未实现”变成经过测试的真实能力。

## 9. 测试证明什么

测试覆盖：

- 显式和默认 Provider 解析；
- 重复、未知和非法 ID 拒绝；
- Provider Protocol 运行时校验；
- 没有默认项时拒绝隐式解析；
- 能力不足时不静默切换；
- 兼容候选发现；
- Descriptor 排序和敏感字段隔离；
- 新默认配置优先级与旧配置兼容；
- 默认 ID 未登记时启动失败。

## 10. 面试中的准确说法

可以说：

> 我将厂商适配、能力协商和实例选择拆成三层。Provider Registry 使用稳定实例 ID 管理同厂商多模型，显式解析默认或指定 Provider，并在选择时执行 capability negotiation；候选发现与最终路由分离，避免能力不足时发生不可解释的静默切换。

暂时不能说：

> 系统已经可以根据成本、质量和健康状态在多家模型之间自动路由。
