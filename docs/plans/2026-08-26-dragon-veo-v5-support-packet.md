# DragonAPI Veo 3.1 task failure support packet

请协助查询下列异步视频任务的上游失败原因；希望确认是上游临时故障、relay 参数映射，还是具体字段不被当前
通道支持。请尽量提供实际 upstream error/status，而不仅是 `task processing failed`。

- task ID：`task_I5iJQDEiEOpZtsQCSOi3qELNTMFAk9Mw`
- model：`Veo3.1-quality-official`
- endpoint：`POST /v1/videos`
- 提交时间：2026-08-26 17:16:10（Asia/Shanghai）
- 终态时间：2026-08-26 17:18:49（159 秒）
- 终态：failed / 100%
- 页面错误：`Generation failed: task processing failed`
- billing：预扣 `$19.712`，失败后已全额异步退款；提交前余额充足
- input：一张公开 PNG 作为 first frame，同一张图作为 `metadata.lastFrame`
- source：HTTP 200、`image/png`、2,268,033 bytes；SHA-256
  `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`
- request：8 秒、1080p、16:9、`generateAudio=false`、`personGeneration=dont_allow`、
  `compressionQuality=lossless`、`resizeMode=pad`，包含 `negativePrompt`
- prompt SHA-256：`99cce1b934b13e0908b933fba0062dd4b20317c8baa83e3c477efcebc15e72a6`
- negative prompt SHA-256：`310b2813df3b37e8c77760947ba7ec27c0497e07b71ca0d17ae385050711b8ab`
- client retry：0；只创建了这一个 task

对照信息：同账号同模型的 first+last 任务 `task_UaNhoqYyuwc5J72zsqfQSH6vnQrKEQSX` 曾于同日成功；另一个
first-only task `task_c3yCIRHEPrYK6roEPCfvDk4lbdtH77mT` 也在约 158 秒后返回同样 generic failure。

请重点确认：

1. 当前 `Veo3.1-quality-official` 通道是否稳定支持 first frame + same-image lastFrame；
2. `negativePrompt`、`generateAudio=false`、`compressionQuality=lossless`、`resizeMode=pad` 是否都映射到上游；
3. 此 task 的实际 upstream error/code；
4. 若是字段问题，请告知需要删除或修改的精确字段；若是临时故障，请说明是否建议原请求重试。

本说明不包含 API Key、Authorization header、prompt 正文或用户隐私数据。
