# 8E Veo refined submit 403 诊断

## 结论

`run-dragon-veo-locked-refined-once.ps1` 在 `POST /v1/videos` 阶段返回 403；body-free status 为
`phase=submitting`、`task_id=""`、`post_attempts=1`。Dragon 通用日志随后给出精确原因：当时余额
`$15.008`，请求需要预扣 `$19.712`，所以预扣失败。该请求没有创建 task、生成视频或产生质量结论，也没有
发生下载或生成扣费。runner 已退出，没有自动重试。

这与早先成功任务的 `/content` 下载 403 不同：早先已有 task 且 query 成功，本次连 task 都没有。

## 证据

- Dragon 模型广场 `Veo3.1-quality-official` 显示 `$2.464 / 请求`，同页描述写“按 1 秒视频计费”；通用日志
  以实际预扣 `$19.712` 证明 8 秒按 `$2.464 × 8` 计费；
- 2026-08-26 16:03:52 的通用日志明确写 `status_code=403, 预扣费额度失败, 用户剩余额度: $15.008000,
  需要预扣费额度: $19.712000`；同一时间的四条 common-log pipeline 记录不是四个 task，runner 状态仍为
  one POST，task log 总数仍为原来的 `4`；
- 用户随后充值 `$50`，钱包权威余额成为 `$65.01`，billing gate 已满足；
- Dragon 错误文档把余额不足列为 402，但实际 relay 返回 403，说明错误码文档与实现仍不一致；
- 同一模型此前的 first+last task 曾成功，不能由本次 403 推导 Veo、prompt、首尾帧或质量失败；
- 没有 task_id，故不能从任务日志获得上游错误详情。

## 当前故障树裁决

| 层 | 状态 |
|---|---|
| local runner / secure prompt | 已执行到提交，Key 非空；无本地异常证据 |
| request construction | 仅能确认请求进入 POST；无法从 403 body 判断价格/权限/字段门 |
| relay billing/access | **已证实故障**：`$15.008 < $19.712` 导致预扣失败；充值后 `$65.01` 已满足 |
| upstream processing | 未进入，无 task_id |
| output quality / motion method | unknown；没有成片 |

## 下一步边界

1. 保留旧 403 status，不覆盖、不把它计为 upstream/model 失败；
2. RQ-130 要求余额以外还必须完成 source、schema、positive/negative、runner 与唯一路径的内容 preflight；
3. v5 spatial-orchestration prompt/negative 与原 runner 通过本地静态门后，先独立提交并取得 exact-SHA 公共 CI；
4. 公共成功后才以 `retry1` output/status 做一次 one POST/no retry；不得自动充值、重抽或切模型归因。

官方参考：

- <https://docs.dragon3api.com/#/errors>
- <https://docs.dragon3api.com/#/model/video-veo3-official-generation>
