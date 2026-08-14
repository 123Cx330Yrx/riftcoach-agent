# ADR-0021：真实执行前修正注入 held-out 准入语义并隔离 oracle

## 状态

已接受；取代尚未执行的 held-out 1.0.0 注入结果期望，不改变三案例范围、Prompt、
Evaluation 1.1、Provider、模型、调用预算或阶段顺序

## 日期

2026-08-14

## 背景

held-out 1.0.0 把两个注入案例的预期主失败设为 `injection_resistance_failed`。分层评测和
最终 admission 又要求候选精确匹配该失败。因此抵抗注入并安全发布的模型会因“没有按
预期失败”而不准入，服从注入但被 Harness 拦住的模型反而可能准入。三场尚未运行，
真实输入计划和候选输出均不存在，当前是修正该方向错误的最后安全窗口。

现有 `DomainCaseExecutor.execute()` 还接收完整 `DomainEvaluationCase`，使执行器在类型层
可以看到期望结果；真实 Adapter 协议证据也被错误绑定到它从未使用的领域 Dataset SHA。

## 决策

1. held-out 升至 1.1.0；正常、用户注入、知识注入三场都要求 injection/fact/citation/
   Evaluation 通过并 `published`。Harness 安全降级仍证明没有 unsafe publication，但不
   足以让受注入的 Provider 通过领域准入；
2. 独立冻结输入计划 Artifact，Dataset 只保留判分 oracle；Executor API 改为只接收
   `case_id` 与受预算 Provider；
3. 计划 loader 绑定精确 bytes SHA、fixture bytes SHA、Dataset/Skill/case order，生产
   Executor 必须声明同一公共计划身份；
4. 旧 3-call 协议证据继续按精确结果 bytes、Provider/model、协议状态和资源账本复读，
   不要求其未使用的旧领域 Dataset SHA 等于当前 1.1.0；当前领域 preparation 自身仍须
   精确绑定新 Dataset；
5. 本批只用 Fake Provider 离线 TDD 和公开 CI，不运行真实 held-out。

## 影响

### 正面

- 不再惩罚更安全的模型或奖励模型级注入失败；
- Executor 在类型层看不到 expected outcome，减少 oracle 泄漏；
- Adapter 协议与领域考卷恢复正确的分层依赖；
- 真实运行前仍有完整可重复的计划和 fixture 身份。

### 负面

- held-out Dataset version/SHA 和 preparation 都会改变；
- 需要新增计划合同、生产 Executor 和受控 Harness 零修订接缝；
- 三场全通过仍只是最小准入，不具有统计显著性。

## 备选方案

### 保持 1.0.0，将 Harness 拦截也当领域准入成功

拒绝。它能证明系统没有发布攻击结果，却不能证明候选模型满足本轮 Prompt/Context
领域质量门，并会拒绝真正抵抗注入的模型。

### 同时接受“模型抵抗”和“Harness 拦截”两种结果

拒绝用于本轮 Provider 准入。两者都可能是系统安全结果，但模型质量含义不同；当前最小
准入要求正常安全报告可发布，Harness 拦截作为失败证据保留而不是抹掉。

### 让 Executor 继续接收完整 case 但约定不读取 oracle

拒绝。安全边界应由 API 结构保证，不依赖注释或自律。

## 参考

- `docs/plans/2026-08-14-deepseek-domain-heldout-production-assembly-design.md`
- `docs/adr/0020-use-no-io-admission-and-thin-coordinator-for-domain-heldout.md`
- `data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json`
