# 当前组合固定15审查集的资格验证入口

资格入口现已实现，尚无任何真实批次获得新资格。它复用 `FullChainEvidence` 的严格回放，接受一个完整关闭批的原件、独立记录的seal SHA和当前准备指纹；不修改旧资格入口、历史标签或失败记录，不注册产品，不提供付费执行命令。

## 为什么需要这一层

当前whole-text教学、block-keyed editor和time600组合与更早的document-review资格身份不同。旧入口拒绝是正确的身份隔离，不能放宽旧校验器。已有三阶段回放能重建请求、实际修订稿、终评输入、预算、作者文件与真实native；新增入口只汇总同组合完整覆盖，并把离线工程响应与实际模型证据分开。

代码入口：`scripts/qualify_full_chain_controls.py`。准备对象复用上一轮的完整组合指纹，并绑定本验证器源码和指定主审/独立主体；准备状态始终为未授权、未执行、未取得资格。

## 输入、验证和结果

1. 核准备文件及seal的外部SHA，与当前完整准备对象逐项比较。仅接受原15输入和原标签，不从历史批挑成功案例。
2. 核一个完整batch、15 distinct输入、完整顺序及5 accept / 10 reject。accept须initial pass≥85；reject须initial needs_revision、revision、fresh pass≥85，三个阶段双方接受。预期35个阶段，不允许漏编辑、漏fresh、额外调用、未知用量或无回执。
3. 实例化冻结的 `FullChainEvidence`，重建完整plan/request/source/path身份，核run全部原件及run外作者/观测SHA和白名单。关闭锁必须已经存在，避免验证旧目录时新建锁。旧三批和两次离线演练不能进入新资格。
4. 要求actual observed worker的完整parent/采样文件、单次HTTP 2xx、流已关闭、非零响应字节、无观测失败；只写“valid”的synthetic sidecar不够。SHA和观测绑定仍由原严格回放检查，不以形状检查代替原件。
5. 沿用既有公共CI检查：当前checkout须clean、等于run的execution_head，且同HEAD的pytest/postgres-migrations/packaging-smoke成功。只读验证不自动切换checkout。operator显式提供Codex可执行文件，代码自行构造只读原生reader，逐stage重新导入真实唯一final、checkpoint和作者意见。
6. 完整replay必须与pinned seal逐项相同。外部读取结束后再核原件、作者、观测、准备与seal未变。只有全部通过才新建目录外资格结果；不回写seal、run或旧资格。

结果中的 `review_controls_qualified=true` 只覆盖这个固定审查集、这个组合和这个seal。`actual_product_task_qualified`、`production_admitted`、`execution_authorized`仍为false。样本是熟悉来源，不是holdout；自然生成/工具/编辑/终评、Coach/Training及产品消费单独取证。验证期间Provider调用0，不读取模型密钥；CI和原生历史读取不会发起模型回合。

## 操作方式

在后端checkout使用绝对Python路径执行。`prepare`仅创建准备文件，不创建业务run：

```text
python -m scripts.qualify_full_chain_controls prepare --output <new-preparation.json>
python -m scripts.qualify_full_chain_controls validate --preparation <preparation.json> --preparation-sha <SHA256> --directory <closed-full15-run> --seal <sealed-result.json> --seal-sha <SHA256> --codex-executable <operator-verified-codex.exe> --output <new-qualification-result.json>
```

输出须不存在；验证输出不得位于任何run、作者或观测目录。历史run缺新证据路径时直接拒绝，不能让用户拿旧批补字段后尝试。真实验证须在执行HEAD或核准的同一冻结checkout中进行；本入口不为校验而reset/checkout用户工作树。

当前准备文件为 `data/evaluation/results/full_chain_qualification_preparation_20261013.json`。它不是执行许可、不是qualification result，也不意味着应当立即重买原15。

## 本轮证据与剩余决定

`tests/test_full_chain_qualification.py` 共41项通过，16.41秒。覆盖当前plan真实重建、政策/editor/time/source/input/标签/主体漂移、漏例/重复/乱序/缺stage/拒绝/低分、未知用量/无回执/多调用、synthetic观测/重试/HTTP失败、native缺失、seal不一致、原生读取期间污染、错误HEAD和旧CLI路径。

测试的完整通过分支使用明确的synthetic replay后端；它证明新汇总逻辑和调用顺序，不证明真实Host或模型质量。原 `FullChainEvidence` 的实际作者文件/check-answer/native导入/submit/replay接线已有前轮工程测试，本轮未改其冻结源码。机器记录见 `data/evaluation/results/full_chain_qualification_validation_20261013.json`。

实际读取原三批和两次演练seal的新入口均拒绝，旧SHA保持，新增资格0。下一项是形成正式同组合验证的具体执行方案：当前无付费execute入口与新授权，不能直接运行旧full15；须把现有全链入口、当前资格检查、35阶段范围、预算、唯一run/主体、错误停止和真实Host final覆盖方式一次写清并验证。不得用第三次简化报告演练掩盖真实语义缺口，也不得把三处旧语义拒绝/分歧算作已修好。方案还需说明新实测能回答什么，而非以调用本身作为推进。

自动任务保持PAUSED，无新付费、无新Agent或业务Host任务。8E及现有全部产品/学习依赖未改变。
