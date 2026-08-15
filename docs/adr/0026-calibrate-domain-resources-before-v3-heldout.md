# ADR-0026：先用 development 请求校准资源，再创建 V3 held-out

- 状态：Accepted
- 日期：2026-08-15
- 阶段：5D-7

## 背景

DeepSeek V4 Pro V2 在首个响应后使用 3440 observed tokens，下一调用因单例 4000-token
上限不可达而在 I/O 前停止。ADR-0025 已证明这是资源合同 Bad Case，但只得到首轮真实
Usage，无法给出完整四调用路径的精确预算。

代码审计和本地生产路径又确认：正常路径为两次 Agent 调用和一次 Evaluation；严格
Evaluation 非法时允许一次同合同 repair，因此领域单例必须容纳最多四次 Provider 调用。

## 决策

1. V2 结果保持不可变，不修改或重跑；
2. 新建两个公开、合成且不复用 V2 内容的 development 校准 profile：baseline 和
   ceiling；
3. 用现有生产组装与本地受控 Provider 生成四阶段 `ChatRequest`，不另写 Prompt 拼接器；
4. 在未来单独获批后，最多使用 8 个 DeepSeek V4 Pro 请求做独立 Usage replay；
5. 校准输出上限为每请求 64，零重试，首错停止，总 observed token 上限 64000，金额
   停止线 `$0.10`；
6. V3 单例预算按两个 profile 的逐阶段最大真实 input Usage、25% 工程余量、四次 1024
   output ceiling 和固定向上舍入推导；
7. 推导总成本超过 `$0.10`、四阶段不完整、Skill 30 秒 Agent deadline 不可达或任一安全
   合同失败时，不创建 V3 held-out，回到人工采用决策；
8. 只有 development 校准结果、预算裁决、代码和 exact-SHA public CI 都冻结后，才允许
   创建新 V3 held-out；held-out 不得反向调节本轮资源合同；
9. 本设计批不创建 Provider、不读取 Key、不调用模型，也不创建或运行 V3 held-out。

## 备选方案

- 直接提高 V2 预算：污染已消费考卷且没有完整 Usage 依据，拒绝；
- 用一次真实 development 端到端运行校准：阶段是否可见取决于模型行为，不能保证观察
  repair，拒绝作为唯一资源依据；
- 立即关闭候选：当前证据只否定旧实验合同，尚未否定模型领域质量，暂缓；
- 使用 tokenizer-free 长度直接定预算：长度只适合 preflight 和 envelope guard，不能
  冒充 Provider Usage，拒绝。

## 后果

正面后果：

- 资源合同在新 held-out 出现前冻结，避免考后调预算；
- 四阶段都能获得真实 input Usage，资源测量与模型质量解耦；
- 正常 3-call 与可选 4th repair 都真实可达；
- V3 请求变大、Usage 越界或成本过高时有明确停止行为。

代价：

- 在 V3 前增加最多 8 次 development 校准调用；
- 25% 是工程余量而非统计保证，Prompt/Context 版本变化需要重新校准；
- 推导预算若超过既有 `$0.10`，需要新的人工决策而不能自动继续。
