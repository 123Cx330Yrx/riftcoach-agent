# 8E 学习 walkthrough：低思考候选领域门的离线控制面（RQ-223）

## 先说清楚问题

RQ-221 只证明一条没有工具的短请求可以完成。它没有证明模型能在 RiftCoach 的 Agent、知识
检索、评测和 Harness 链路里安全完成领域任务。若直接把 `low + 4096` 写进产品 Runtime，
一次窄探针就会意外改变全局默认模型，所以 RQ-222 先决定使用评测专用作用域。

## 核心原则

这里有两个容易混淆的概念：

- 产品运行档案是已登记、可被正常 Runtime 解析的 `ModelRuntimeProfile`；
- 候选请求策略是只在评测入口可用的能力令牌，不能冒充产品档案。

共享执行链不需要复制一套 Agent。它只接收一个窄的 `request_policy`，在编译、工具和最终
Provider 边界重复施加同一组上限。这样模型返回的参数不能把 4096、采样或超时升高。

## 代码地图

- `app/model_runtime.py`：候选策略类型、私有签发工厂、精确对象身份校验；
- `app/evaluation/glm53_flash_candidate_profile.py`：RQ-221 profile plan 与唯一候选策略；
- `app/agent/compiler.py`、`app/agent/draft.py`：把策略带入 Agent 请求；
- `app/tools/adapters/llm.py`：固定 LLM 请求参数、一次尝试、无工具回退；
- `app/evaluation/provider_domain_production.py`：让既有领域执行器通过显式入口消费策略；
- `app/evaluation/glm53_low_profile_budget.py`：reserve-before-I/O 的调用/token 墙；
- `app/skills/review_executor.py`：候选执行时关闭 deterministic fallback。

## 一次请求怎样流动

1. 评测模块拿到私有工厂签发的唯一策略；普通构造器和 `dataclasses.replace` 克隆都不能
   通过身份检查。
2. 编译器把 Agent 总时限、输出上限、temperature/top-p 和安全元数据写进
   `AgentRunRequest`。
3. `llm.chat` 再把调用方参数压回策略上限，并把重试设为 1 次尝试；候选失败不能由工具
   fallback 伪装成成功。
4. 最后的预算包装器在 Provider I/O 前占用调用槽，在响应后结算 Usage。单案或全域超限、
   响应身份不对、Provider 异常都会把整个候选运行置为停止状态。

## 测试怎样证明它

所有测试使用内存 Fake Provider，调用数和请求对象都可观察：

- 私有作用域和克隆拒绝证明候选不能伪装成产品档案；
- 编译器/LLM 断言证明请求方传入更大预算也只得到 4096/90 秒/固定采样；
- 包装器先记账再调用，第四次之后的第五次不会触碰 Provider；
- 超过 token 墙后立即 fail-closed，且只保留安全计数，不保存正文。

## 现在还没有证明什么

这批没有新真实 API、没有新 held-out Dataset、没有 G53-3-L 回执，也没有改变产品默认档案。
实现提交 `d823cc40c3fcafb7167edccded87e185be4cae8a` 的 Actions `33781369322` 已完成
exact-SHA 三 job 公共 CI，pytest 为 `2326 passed, 145 skipped, 2 warnings, 127 subtests passed`。
该绿灯只证明离线控制面的可复现性；候选仍属于 8-Advanced，不能算 8-Core、黄金切片、
生产成熟度或 8F。下一精确 checkpoint 是新的 G53-3-L 与全新 held-out 资产前置，且需明确授权。

## 面试式表述

“我把实验档案和产品档案分成两种类型，用私有能力令牌和最终 Provider 预算墙防止候选
越权；共享 Agent 链只消费显式请求策略，因此能复用控制面而不把一次实验悄悄变成默认模型。”
