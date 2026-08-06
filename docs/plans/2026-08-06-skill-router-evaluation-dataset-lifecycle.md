# 5C-5 Router Evaluation：数据集生命周期

## 1. 这一步解决什么问题

Router 的任务是把用户表达映射为一个 Skill，或明确返回拒绝/歧义。旧评测虽然得到
`1.0`，但它只有一个真实候选，15 条案例还参与过触发词和排除词校准。这个结果可以
证明当时的规则能记住开发案例，不能证明当前两个 Skill 的路由泛化。

本检查点先修复证据链，再计算新成绩。否则测试数字越漂亮，结论反而越不可信。

## 2. 底层原理：开发集与保留集为什么必须分开

开发集允许被反复运行。看到错误后，可以修改触发信号、排除信号或案例标签，因此
它适合调试和防回归，但已经被开发过程“看过”。

独立保留集在规则冻结后才建立并封存。第一次正式运行后，失败必须原样保留；如果
拿失败案例去修改规则，该版本就不再独立，必须退休并创建新的未参与校准的版本。

```text
历史单 Skill 数据与结果
        |
        v
只读归档 + 哈希 + 重建来源说明

双 Skill development --允许调试--> 冻结 Router 与 Skill 版本
                                      |
                                      v
                         independent holdout 单次验收
                                      |
                           记录结果，不反向调规则
```

这与机器学习中的 train/dev/test 分离是同一个原则，也适用于纯规则 Router。算法
没有训练参数，不代表开发者没有通过案例人工“训练”触发词。

## 3. 三类数据的职责

| 数据 | 角色 | 能否调规则 | 当前用途 |
|---|---|---:|---|
| 旧 15 条单 Skill 案例/结果 | historical baseline | 否 | 保存项目演进证据，不再作为当前 CLI 默认输入 |
| 双 Skill development v2 | development/calibration | 是 | 覆盖近期、单局、歧义、拒绝与无候选，记录每条污染来源 |
| 双 Skill holdout v1 | held_out | 否 | 规则冻结后的一次独立验收 |

## 4. 历史基线如何冻结

旧文件被原样移动到 `data/evaluation/history/` 和
`data/evaluation/results/history/`，字节 SHA-256 未改变。旁路 Manifest 记录：

- 候选只有 `recent-form-review`；
- 兼容的 Skill 版本为 `0.1.0`；
- 可对应到公开提交 `02528db` 的 Manifest Blob；
- 精确的未提交运行 SHA 无法恢复，因此 provenance 标为 reconstructed，而不是
  伪装成精确复现。

## 5. 新数据契约与控制流

新数据集必须声明：

```text
dataset_id + dataset_version + role + calibration_excluded
+ created_at + case_count
+ candidate_snapshot(name, version)
+ contamination_notes
+ cases(expected outcome/reason/skill/candidates)
```

控制流为：

```text
JSON 数据集
  -> Schema/生命周期校验
  -> CLI mode 与 role 校验
  -> Catalog name/version 与 candidate_snapshot 校验
  -> Router 精确决策比较
  -> 指标与逐案例结果
```

任何 Skill 版本变化都会让快照校验失败，防止用旧题库静默测新候选。默认
`development` 模式不能加载 `held_out`；保留集运行还必须显式确认规则已冻结。

## 6. 本批实现与不实现

本批实现：

- 冻结旧单 Skill 基线和来源证据；
- 建立双 Skill development v2 与 synthetic holdout v1；
- 记录开发污染和 holdout 退休规则；
- 增加数据角色、候选版本快照、案例数量和歧义准确率；
- 增加 CLI 误用门禁及对应测试。

本批不实现：

- 不运行新的 development 正式成绩；
- 不运行 holdout，也不读取其 Router 结果；
- 不修改任何 Skill 触发词；
- 不执行 Skill、Tool、Harness 或模型；
- 不决定 5C-6 是否需要模型兜底；
- 不进入 5D。

## 7. 测试如何证明边界

- 哈希测试证明历史案例和结果移动后没有被改写；
- Loader 测试证明 development/held_out 元数据和案例数量有效；
- 快照测试证明 Skill 版本漂移会被拒绝；
- CLI 负例证明 development 模式读取 holdout 时在写结果前失败；
- 显式确认测试证明 holdout 不能被默认运行；
- 小型合成测试证明歧义准确率指标本身可计算。

这些测试只证明评测基础设施和生命周期门禁工作，不证明 Router 已通过新数据集。

## 8. 局限与面试安全表述

当前 holdout 只有 12 条维护者编写的合成案例，不是用户流量抽样，也不是第三方盲测。
它可以提供比开发集更可信的小规模证据，但不能支持“自然语言路由已充分泛化”。

面试可准确表述为：

> 我把参与规则校准的开发集与规则冻结后的保留集分离，并用候选 Skill 版本快照、
> 污染记录和 CLI 角色门禁防止评测泄漏；历史单 Skill `1.0` 只作为演进基线，
> 不再冒充当前双 Skill 的泛化成绩。

## 9. 下一小步

下一批只运行双 Skill development v2，逐条分析误路由并决定开发门禁是否接受。
只有开发规则和候选版本再次明确冻结后，才进入 holdout 的单次正式运行。
