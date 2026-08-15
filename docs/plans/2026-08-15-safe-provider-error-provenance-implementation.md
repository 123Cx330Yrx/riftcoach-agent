# 5D-7 安全 Provider 错误 provenance 实现说明

## 1. 为什么现在做这一步

DeepSeek V4 Pro 的真实 V3 Usage calibration 在第一个请求后停止。旧结果只保存了
跨厂商高层分类 `provider_response_invalid`，而 Adapter 当时可能已经产生更具体的
安全错误码。于是我们知道“响应没有进入统一 ChatResponse”，却不能知道是 finish reason、
tool call、model identity 还是 Usage 合同出了问题。

这不是重新测试 DeepSeek，也不是证明模型质量。它是把已经存在的 Adapter 错误信息，
在不泄露 Prompt、response、reasoning、Key、URL/header 或原始 request ID 的前提下，
安全地传到未来实验结果。

## 2. 初学者理解：两层错误是什么意思

把模型接入想成翻译过程：

```text
DeepSeek/Zhipu 原始协议
        ↓ Adapter 翻译
RiftCoach 统一 ChatResponse
```

如果翻译失败，系统需要同时记录：

```text
failure_code = provider_response_invalid
provider_error_code = invalid_finish_reason
```

第一项是所有厂商都能理解的统计分类；第二项是该 Adapter 的有限诊断标签。第二项
只能来自冻结白名单，未知内容必须记录为 `null`，不能把 SDK 异常正文直接写入公开文件。

## 3. 本批实现

- 在 Provider adoption 控制层建立 DeepSeek/Zhipu 的 body-free safe-code allowlist；
- `ExperimentBudgetedProvider` 把允许列表内的细分码传给 Provider stop snapshot；
- 资源 calibration simulation/real result 增加可空 `provider_error_code`；
- adjudication 根据该字段报告 detail available/code；
- 旧 V3 结果没有该字段时仍解析为 `null`，原始 bytes、SHA 和历史裁决不变；
- 未知的任意错误字符串在进入公开结果前变成 `null`；
- 通过离线 Fake Provider 测试允许、拒绝和旧结果兼容性。

## 4. 本批明确不做

- 不读取 API Key；
- 不构造真实 Provider；
- 不调用 DeepSeek、Flash、GLM-5.2 或 GLM-5.3；
- 不重跑或修改 V1/V2/V3 结果；
- 不实现 5E 的统一 Trace、日志系统或多模型路由；
- 不测试 Flash，也不把 Pro 重新打开。

## 5. 数据流

```text
Provider Adapter
  -> ProviderResponseError(provider, safe code)
  -> classify_provider_error()
       -> failure_code (cross-provider)
       -> safe_provider_error_code() (allowlist or null)
  -> public result/adjudication
```

公开结果仍然不包含原始响应。旧结果的 `provider_error_code` 缺省为 `null`，这表示
历史实验没有保存细分码，而不是事后推断出的具体原因。

## 6. 测试如何证明

1. 已知白名单码（例如 `invalid_finish_reason`）会被保留；
2. 任意未登记文本（例如 `arbitrary_sdk_text`）不会被保留；
3. Provider stop snapshot 拒绝未登记码；
4. 旧真实 calibration JSON 仍能通过 Pydantic 合同读取，且 SHA 不变；
5. synthetic offline adjudication 能看到安全细分码，但不会获得原始异常正文；
6. 聚焦 Provider/Calibration/Domain 回归、完整回归、RAG、compile、治理和 CI 全部通过。

## 7. 当前限制

这个改动只解决“下次失败时能安全知道属于哪个有限错误类别”，不能修复本次已丢失的
历史细分信息，也不能证明 DeepSeek 或任何模型的领域质量。只有未来全新的、同任务、
有预算和 held-out 隔离的实验，才能使用这个字段获得更好的失败归因。

## 8. 路线影响

- 当前 DeepSeek Pro V3 尝试仍关闭；不立即切 Flash；
- GLM-5.2 继续作为可用的开发基线，但不宣称已完成最终领域质量准入；
- GLM-5.3 的 G53-0 因普通 API 尚未正式可用而暂缓；
- 本批公开验证完成后，项目等待 API 可用或新的明确模型对照需求，不自动发起模型调用。
