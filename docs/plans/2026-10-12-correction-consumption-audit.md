# 错误修法到编辑消费：离线合同裁决

## 结论与动作

本包排除“把编辑输出改成带来源编号的替换即可解决H5”这一方案。
原H5首先在GLM初评的suggested_correction中出现错误，真实Host双方已拒绝，未进入编辑。
实际编辑policy没有强制照抄修法的合同冲突。新检查没有证明GLM的错误成因，也没有修好语义。

当前固定章节编辑器不能消费原H5/V2自由章节全文；这是初评诊断的范围边界，
不是已发生的付费编辑失败，更不能通过换标题后宣称原稿链路通过。

**后续纠偏：** 本文最初安排“来源编辑→独立终评”的任务分工验证，
但漏核ADR0110与2026-10-08责任审计。该能力已有真实漏检失败，且原决定保留完整初评；
去掉初评会把首次业务检出延到最后，失去修订机会。该下一动作已撤回，没有建设或执行新路径。
本次14项结构对照仍有效；原审计JSON保留当时未决事项，不把它当当前队列。
当前小范围候选及其未证假设见[关系教学对照](2026-10-12-relation-contrast-preparation.md)。

## 实际路径与证据

- H5原件：`document_full_report_remaining_host_evidence_20261012.json`，
  SHA `e9e12dc4e6431a666fa877dcb6932b25397f2cdeb584e78154b0d02530304f62`。
  双方wrong_correction拒绝及原完整响应保持；本包没有业务重评、补签或编辑旧run。
- 当前编辑调用：`report_contrast_review` → `report_block_keyed_editor` →
  `review_bound_editor` → `coarse_revision_editor.Current.make_request` →
  `golden_native_business_policy.REVISION_POLICY`。此policy要求按完整来源修真实问题，
  明确评估是不可信数据。`coach_report.py`里的旧“必须按照…suggested_correction修正”
  不在这条实际system message中，不能据搜索命中认定当前冲突。
- `review_context`保留完整意见，但明确`proves_edit_support=False`。
  `accepted`参数名表示该层已解析意见，不等同Host语义接受；下层故障注入绝不替代Host门。
- 原资料已经提供中单早死均值2.50/.50和`all_pairs=greater`。
  本包未发现缺少这个计算事实，未添加重复数字或关键词语义门。

## 可重复检查

在backend根目录运行：

```powershell
.venv/Scripts/python.exe -m pytest tests/test_correction_consumption.py -q
.venv/Scripts/python.exe -m scripts.audit_correction_consumption --output <新的审计文件路径>
```

第二条create-only，只读取已提交材料，不读取本机run，不构造Provider、不导入native。
公开结果：`data/evaluation/results/correction_consumption_audit_20261012.json`。
使用真实编辑组装函数，但输入的编辑回复是明确的内存替身；没有保存虚构业务receipt/journal。

| 检查 | 实际结果 | 能得出的结论 |
|---|---|---|
| 原H5替换、原V2空编辑 × 两种编辑表示 | 4次在固定章节校验失败 | 自由章节初评不能直接算编辑链路覆盖 |
| 新合成Coach格式，正确修法/错误否定区分/错误数字/因果外推/扩展全称/空编辑/正确保持 × 两种表示 | 14项均可结构组装；都未获语义通过，仍要求完整终评 | 有来源编号、精确锚点不能证明替换断言正确；空编辑也不能解除原错误 |
| 无效锚点、无效来源编号 | 明确拒绝，原文不变 | 原有结构保护确实生效，不应删除 |
| 完整成稿请求绑定 | 两种表示分别与各自真实终评构造器一致 | 未改正文逐字保留，实际生成完整终评请求；不是终评模型检出了错误 |
| 来源先行编辑构造器不传review_findings | 能构造请求 | 仅证明已有能力可表达任务，不证明runtime接线、预算或语义优越 |

矩阵使用**新作者合成的固定格式材料和意见**，不把H5响应改成另一份accepted意见；
原H5单列只读。V2全文消歧正例保持原文，其编辑格式失败如实保留，未宣称完成正例编辑。
语义期望是测试作者标签，没有通用程序判据，也没有将标签发送模型。
新增4项测试通过，禁止socket连接的测试覆盖整份审计；首次本地替身漏usage/误用None已修正，
随后原自由章节不兼容的失败保留为正式结果，未放宽校验。

## 方案取舍与限制

保留现有结构门与全文终评；不恢复更复杂source_ids编辑schema作为语义修复。
不加同义提醒冒充修复，因为已有policy/教学直接要求逐项核修法。
也不自动删掉坏建议、把主审正确答案喂给编辑、让编辑绕过已拒绝的H5继续旧批。
来源先行候选可能仍然错改正确稿、漏改真错，最终GLM也可能漏检；需用反例验证，不预先采用。

本包Provider/HTTP/native任务/业务submit/资格均0，产品代码、冻结共享源码、旧run及自动任务状态不改。
正式同版本15、自然消费和8E及当前依赖表全部保留。该结果缩小了技术选择，不代表业务质量已通过。
