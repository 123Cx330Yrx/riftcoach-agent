# 2026-10-11 有界温度筛查结果

## 结论

本批没有完成候选温度筛查，也没有产生新资格。唯一真实 Provider 请求是 `sample-1:baseline`（温度 `1.0`）；它完成了传输和主/独立全文双审，但原报告得到 `score=74`、`verdict=needs_revision`，与该样本预期 `accept` 不匹配，因此 `semantic_accepted=false`。候选温度 `0.2` 没有发送。

## 绑定与边界

- checkout：`D:/riftcoach-agent-rq192-pr`
- HEAD：`8adcc24a88b0e9de1c8e3c898771716b21910dfd`
- CI：`38133097207`
- plan SHA：`fcfb726a326085119f52246486eac21dd0c426d185c0bb44492a5de97c8087b3`
- run：`data/runs/model_comparison/document-sampling-screening-20261011`
- 授权：最多 10 次 `glm-5.3`，未缓存估价 14.29504 元且不是硬计费封顶；本批实际调用 1 次。

## 真实证据

`sample-1:baseline` 的请求、响应和 receipt 完整，独立主体原生 final 事件已按同一 checkpoint 导入，主审与独立审查均接受该 Provider 意见，`host_disagreement=false`。实际账目为 1 个 HTTP 请求、16341 个已知 token、unknown=0、receiptless=0。

第二个样本发送前，runner 在 `before_send` 发现 `role_development_checkout_changed_after_ci`，按硬边界停止整批。核对后确认原因是审查答案承接时临时写入 backend checkout 的辅助 JSON；这些文件已删除，`git status --short` 为空，HEAD 恢复并保持上述冻结值。该停止属于 operator 侧执行边界，不能归因于 429、401、503、Provider 语义或额度，也不允许通过重试、重开或补发来修复。

未执行项为：`sample-1:temperature-02`、`sample-2` 至 `sample-5` 的 baseline 和 temperature-02，共 9 项。剩余预算不构成继续执行授权。

## 收尾

严格只读 replay 已核验 `native_reviews=1`；create-only 封存位于 `C:/Users/33502/Documents/Agent/outputs/riftcoach-bounded-sampling-screening-20261011/sealed`，seal SHA 为 `16ba99da8419f48acccbb897bca8f0aa108cbfde02d7dfd402b5050925980838`。原 run、请求、响应、审查、失败和未执行边界均保留，未修改历史批次或生产入口；本批 `new_qualification=0`。

后续应从已清理且 CI 后不再改动的 checkout 重新准备新的有界方案，并重新取得明确授权；不得把本批的单个 baseline 结果外推为低温效果或完整 15 例资格。
