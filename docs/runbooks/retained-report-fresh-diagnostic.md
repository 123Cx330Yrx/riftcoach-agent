# 保留修订稿的两项复审诊断

目的：仅检查既有修订稿在事实与完成度新审查中的表现。原completion初审漏检、原seal及原费用不改写；此入口不生成、不执行旧初审、不声称原正式application已经完成，也不授产品资格。

入口为`scripts/retained_report_fresh_launch.py`。复用CandidateSession、SessionBudget、SolReviewProvider、SessionReviewGate及原严格transport审计；没有新的HTTP实现。每次`run`最多一个新Provider请求，等待Host时不读Key、不查CI。凭据使用Windows Credential Manager里用户已保存的企业分组Key。

## 准备与凭证

1. 在精确提交的干净独立目录运行`prepare`，指定新的Operator、已固定的fresh-materials及现有主审/独立作者ID。
2. 新plan在派发前固定`native-final-attestation-v1`。它核实际父子身份、单次派发route、唯一completed final、任务binding与作者原件逐字相等；不能证明宿主加密输入正文等价。旧dispatch-and-final失败不改写或追认。
3. `preflight`发布唯一行政任务。`task --administrative`输出原留完整dispatch；作者在run外自写答案，check-answer后唯一native final；主审实读后`submit --administrative`。原stdout保存guard/checkpoint，随后只读replay核验。行政结果不算业务判断。
4. 费用授权必须绑定新plan SHA、精确HEAD、企业分组、2逻辑项、初始最多6实际请求/482304 tokens/3600活动秒、每次300秒及4个手动恢复预留。初始两项估价0.14592元，含全部预留估价0.43776元；均非账单硬上限。授权从用户明确同意时起最多24小时，程序不会续期。

## 执行与恢复

`run`参数包含Operator/plan SHA、原授权路径/SHA、行政预检stdout根、精确HEAD的CI run，以及恢复时原stdout中的guard/checkpoint SHA。只在新的发送边界核当前授权、源码/材料/原件库存、全部CI和原生路由，然后读Key。CI查询错误不等于CI失败，均不触发模型请求。

每个正常输出保留原始回执、HTTP计数、known/unknown用量和观测，再发布事实或完成度完整来源Host任务。主审和独立作者审查实际全文、完整来源、完整请求政策与原意见，接受后才进入下一项。不得传Host答案、旧分数标签或原初审意见给Provider。

超时/已有可恢复格式错误仅暂停本项。普通resume零重发；`--manual-retry`只消费一次恢复意图并重发同项，已成功项从原会话回放。任何中断未决intent须先用已有receipt reconciliation核对，不以重跑补写。身份、来源、语义拒绝等原则性问题停止发送，保留原件供诊断。

`--host-only`允许不发模型地推进现有Host边界，授权过期仍可做本地审查；过期只能阻止新的付费请求。余量不足暂停在边界，追加范围需单独记录，不清零旧账。

两项均通过后，`replay`只读验证实际新稿/原生作者/回执/用量，`seal`唯一create-only固定外层库存及stdout根。两个pass仅是这份修订稿的新审查证据；不能抹掉原漏检、拼同版本15资格或称产品准入。

## 验证

`tests/test_retained_report_fresh_launch.py`用真实owned worker、SDK解析与本地MockTransport检验：成功分段续接、Host等待无Key/CI、前项保留、524手动同项恢复、过期禁止新发送而允许Host-only、语义拒绝阻止后项、严格只读回放和唯一seal。模拟native/HTTP均不当真实模型质量证据。实际Operator的作者原件→check-answer→native final→导入预检另行留证。
