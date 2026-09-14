# 十二条范围对照真实验证

2026-09-15独立对照入口：原ShowMaker报告闭环已于1.3.25有效96/pass验收，本次沿用该候选与修订稿SHA a1cef8b4af58b6e241ba9bb683bb814c7a603d3d4ce9e56b61ad9a8af6e07088，不改模型提示/schema或重跑原报告修订。新增scripts/run_golden_scope_controls.py，将冻结golden-stability-calibration-v1十二条人工开发标签（accept/reject/clarify各4）逐条嵌入已验证完整报告，标签/rationale不送模型。六组每组两例顺序执行，共最多24次、每例至多一次纠正、零修订/SDK重试；每组共享现有high/32768/300秒/401920tokens/900秒预算且另限4调用，全套预约上限2411520tokens/5400秒模型执行预算，不是单报告预算增加。结构无效单列invalid后继续独立案例，传输/认证/额度/其他运行错误停止后续全套；有效漏检/误报/澄清遗漏与invalid分母分开，目标原句绑定避免其他问题冒充检出。28项聚焦及容量回归通过；十二份完整初评输入55378–55436<64000，真实纠正仍逐请求重检，预检零I/O。下一步本实现同SHA公共三项通过后直接执行全套十二例，逐条人工核对目标判定并保存完整结果，不能当独立held-out/生产准入。Stage8E仍in_progress；Workbench四块设计后置且人工稿不替换。

## 问题与原理

原报告修好只证明一个已知案例；用已冻结的不同说法检查评估器是否既漏检又误杀。沿用开发集，绝不称held-out。完整报告每次只嵌入一条案例，完整证据和新候选不变，expected/rationale仅用于返回后的本地判分。

## 执行与验收

入口默认预检无外部I/O；execute检查干净checkout与同SHA三项CI后创建不可覆盖run目录，才加载本地配置。每组复用一个CoachBudgetedProvider，Counted在I/O前预约并私有保存raw。每例保存输入摘要/有效evaluation或invalid结果/调用区间；组与整套均保存回执，中途故障也保留已完成例。整套必须分别报告计划12、实际尝试、有效数和无效数；accept误报、reject漏检、clarify遗漏仅在有效响应中统计，不可用“没输出”当正确拒绝。12/12有效且每类4/4匹配才可声称此开发集通过；仍需人工逐项审查，且不是生产准入。

## 数据与控制流

已验证修订报告+一条待测陈述+原五局/RAG→原1.3.25评估器→必要时一次纠正→canonical校验→绑定目标原句判分→私有原始/有效结果和公共摘要。运行不调用修订器、不改报告或产品默认。结构无效继续独立例，任何其他运行失败停止全套，未知usage保留未知。

## 测试与操作

28项聚焦验证原句匹配、含混other绑定、invalid分母、标签隔离、独立例继续、传输停止、十二例覆盖及原高档容量墙。预检：python -m scripts.run_golden_scope_controls --source-run data/runs/golden_slice/golden_20260910_compact_1cd694d --base-report data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md。实际使用全新scope-controls-*身份、execute/env-file/ci-run。可显式选择pair用于后续有依据的局部验证，不允许覆盖旧结果或选择性合并为同批全通过。

## 边界与讲述

代码地图：scripts/run_golden_scope_controls.py（组预算/评估/判分/回执）、app/evaluation/golden_evidence_runtime_v7.py（不变评估路径）、tests/test_golden_scope_controls.py（入口行为）。能够准确表述为“设计有真实返回证据、把结构失败和语义错误分开统计的开发对照”；不能说模型因此从此不会犯错。下一步按完整真实结果决定质量修复或可信报告产品接入。
