# 8E Video Bake-off：DragonAPI 与官方候选准入记录

## 1. 结论

本记录把用户已登录并打开的 DragonAPI 模型广场、通用 API 文档和图片/视频专用文档，与上游官方资料交叉核对。
它不保存 Key、cookie、prompt 正文、任务响应或母图 URL，也没有创建任务、上传文件或产生费用。

当前结论不是“只选三款”，而是先广筛，再把实际付费 A 线限制为最多两个调用槽位：

1. `wan3.0-video` 官方阿里云百炼优先进入槽位 A1；DragonAPI 当前未启用该 slug 只影响 transport，不否定
   官方候选。用户已提供官方模型市场截图并确认邀测申请通过，页面可见 `立即体验` 与 `调用 API`；A1 的
   账号准入已满足，只剩地域 endpoint 与 Key 的安全接线；
2. `Veo3.1-quality-official` 通过 DragonAPI 或官方 `veo-3.1-generate-001` 进入槽位 A2；实际 transport 只选一条；
3. Kling v3、Vidu Q3、MiniMax H3 是已核验的有效替补；Seedance 2.x 与 Grok 保留在研究池，但当前不占首轮
   两个调用槽位；
4. B/C 线只准入固定 commit 的 HyperFrames 引擎隔离 preview，不安装或运行其 `general-video` agent skill。

每个槽位首轮最多一次 8 秒、16:9、无音频生成；任一失败不自动重试。两个槽位合计最多两次模型调用。

## 2. DragonAPI transport 合同

### 2.1 已由可见文档证明

- API base：`https://newapi.dragon3api.com/v1`；Bearer API Key，仅服务端使用；
- 创建：`POST /v1/videos`；查询：`GET /v1/videos/{task_id}`；下载：
  `GET /v1/videos/{task_id}/content`；
- 状态：`queued → in_progress → completed | failed`；视频建议 8–15 秒轮询，不因客户端 timeout 重复提交；
- 通用字段包括 model、prompt、duration、aspect ratio、resolution、单图/多图、显式
  `first_frame | last_frame | reference_image`、音频开关与 seed；具体模型仍以各自页面为准；
- DragonAPI 不提供通用文件托管；输入只接收公网 HTTPS URL，不接本地路径或 base64；公开 task ID 不暴露
  上游 task ID；
- HTTP 400/401/402/404/429/500/502 具有文档化语义，429 遵循 `Retry-After`；本项目仍采用首错停止；
- 模型广场当前可见 96 个模型；Veo 3.1、Seedance 2/2.5、Kling v3、Vidu Q3、Grok、Wan 2.6、
  MiniMax H3/Hailuo 均有条目。

### 2.2 文档一致性 Bad Cases

- 专用导航写 28 个视频模型、价格页写 34 个、模型广场标签写 30 个；三者不是同一个版本化目录；
- 通用 `/v1/videos` 的响应示例把 model 写成图片模型 `doubao-seedream-4-0`；该示例不能作为响应映射证据；
- 模型广场为 `grok-video-3` 生成了 `/v1/chat/completions` 文本参数示例，明显不适用于视频；Grok 3 必须等
  专用视频 schema，而不能照广场 API 页调用；
- 专用价格页使用人民币符号，模型广场对相同数值使用美元符号；执行前必须以账户账单/任务日志确认实际
  计价币种，不能把符号冲突写成确定成本；
- 可见文档没有给出 DragonAPI 自身的输入训练用途、任务记录保留期、删除接口、处理地域或 subprocessor
  清单。该缺口不否定站点的可用性，但阻止把它表述成“隐私政策已验证”。

## 3. 广筛候选矩阵

| 候选 | 官方 identity / transport | 关键控制 | 当前裁决 |
|---|---|---|---|
| Wan 3.0 | 官方 `wan3.0-video`；阿里云百炼，北京/新加坡等地域；DragonAPI 文档存在但模型广场当前未启用 | first/last、2–30s、1080p、30fps、audio/watermark off；官方异步 | A1；用户官方 UI 证明邀测已通过，relay 缺席不是拒绝理由 |
| Veo 3.1 Quality | 官方 `veo-3.1-generate-001`；DragonAPI alias `Veo3.1-quality-official` 声称 Vertex AI 直连 | first/last、4/6/8s、16:9、1080p、24fps；relay 有 lossless/pad 和 24h result URL | A2；上游能力高度吻合，transport/账单币种调用前确认 |
| Vidu Q3 Pro | 官方和 relay 均为 `viduq3-pro` | first/last、1–16s、1080p、24fps、audio off | A1 fallback；映射最清楚，适合作为 relay 可用性对照 |
| Kling v3 | 官方 Kling 3.0；relay `kling-v3` | 显式 first/last、3–15s、1080p、audio off、watermark false | 有效替补；控制强，但不挤占首轮两个槽位 |
| MiniMax H3 | 官方 `MiniMax-H3`，开源权重与官方 API；relay 同名 | first/last/reference、4–15s、768p/2K | 有效替补；relay media 价格页缺项、广场未标视频，先不付费 |
| Seedance 2 | 官方 Seedance 2.0 API 存在；relay `seedance-2` | first/last/reference、4–15s、最高 1080p/4K（relay 声称） | research-ready；relay 未给 exact upstream model ID/region |
| Seedance 2.5 | relay `seedance-2-5` 声称映射 `doubao-seedance-2-5-260628` | first/last/edit/extend/reference、4–30s、720p | catalog-only；本轮未在上游官方索引中独立确认该 exact ID |
| Grok Imagine Video 1.5 | 官方名 `grok-imagine-video-1.5`；relay 为 `grok-video-1.5` | 首帧 I2V、1–15s、最高 720p；无尾帧 | 保留研究；不满足首轮 loop 控制与 1080p 目标 |
| Grok Video 3 | relay `grok-video-3` 第三代条目已由模型广场与价格页证明；上游 exact mapping 尚未独立证明 | 通用 `/videos` 示例直接使用该 model；站内全文搜索确认当前无专用视频参数/首尾帧页 | 第三代存在且可售，不回退成 1.5；补齐 schema 后重新参与首轮评分 |
| Wan 2.6 | relay 当前启用，官方可核对 | 价格清楚，但本轮 relay 页面未证明 first/last | 低于 Wan 3.0/2.7，不占首轮槽位 |
| Hailuo 2.3 | 官方/relay 均存在 | I2V 强，first/last 主要由 Hailuo-02 官方接口证明 | 备选；当前控制/规格不优于 H3/Vidu/Kling |

## 4. 首轮调用冻结

### 槽位 A1：Wan 3.0 官方

- model：`wan3.0-video`；不使用未启用的 relay slug；
- region：调用前从实际官方账号选择与 Key/endpoint 同地域；不跨地域；
- request：8 秒、16:9、1080p、audio false、watermark false、首帧=尾帧=获准 Portal source derivative；
- 官方原价上限：北京 `1.2 元/秒`，8 秒 `9.6 元`；新加坡约 `1.49884 元/秒`，8 秒约 `11.99 元`；
  单次 cap 固定 `12 元`，不自动重试；
- access：用户提供的官方模型市场截图显示 `wan3.0-video`、`立即体验` 与 `调用 API`，并确认邀测已通过；
  账号权限已证明。当前本机尚无 `DASHSCOPE_API_KEY` 等可用凭据名称，只需完成地域 endpoint/Key 的安全接线。

### 槽位 A2：Veo 3.1 Quality

- upstream model：`veo-3.1-generate-001`；relay alias：`Veo3.1-quality-official`；
- request：8 秒、16:9、1080p、generateAudio false、首帧和尾帧均来自同一固定 source；relay 用
  `compressionQuality=lossless`、`resizeMode=pad`，不得 crop；
- relay 专用价格页显示约 `2.46/秒`，8 秒约 `19.68`，但价格页与模型广场币种符号冲突；实际调用前以账户
  账单币种为准并记录 body-free cost estimate；
- 同一槽位只选择官方 Vertex 或 relay 之一，不做两个 transport 的重复生成。

### A1 fallback：Vidu Q3 Pro

只有 Wan 官方 access preflight 失败时才启用；model `viduq3-pro`，8 秒、1080p、audio false、首尾帧；首轮仍
算 A1 的一次调用，不把总调用数增加到三次。

## 5. 隐私与素材边界

- 输入只允许 Portal 生成母图的获准 derivative；不得包含玩家、比赛、Riot API、OP.GG、账号、Key 或日志数据；
- relay 要求公网 HTTPS URL，因此必须使用独立临时对象、随机路径、最短可行有效期和调用后删除；不得把仓库
  或长期公开 URL 暴露为素材源；
- DragonAPI 自身的训练/保留/删除/地域仍 unknown。在用户明确接受这项低敏生成艺术素材的 residual risk 前，
  relay 只能完成 API/capability admission，不能上传母图；官方 transport 则按各自地域和数据条款执行；
- 结果立即下载到研究区，记录 SHA/bytes/ffprobe/body-free task identity；远程 URL、raw response、prompt、Key 和
  账单正文不进入 Git；
- 任一候选首帧身份、构图、几何、locked camera 或全帧运动失败即 rejected，不进行“再抽一次看看”。

## 6. 证据来源

DragonAPI 可见页：

- `https://docs.dragon3api.com/#/videos`
- `https://docs.dragon3api.com/#/tasks`
- `https://docs.dragon3api.com/#/pricing`
- `https://docs.dragon3api.com/#/model/video-veo3-official-generation`
- `https://docs.dragon3api.com/#/model/video-seedance-2-generation`
- `https://docs.dragon3api.com/#/model/video-seedance-2-5-generation`
- `https://docs.dragon3api.com/#/model/video-kling-v3-generation`
- `https://docs.dragon3api.com/#/model/video-viduq3-generation`
- `https://docs.dragon3api.com/#/model/video-grok-video-1.5-generation`
- `https://docs.dragon3api.com/#/model/video-grok-video-generation`
- `https://docs.dragon3api.com/#/model/video-wan3.0-generation`
- `https://docs.dragon3api.com/#/model/video-minimax-h3-generation`
- `https://newapi.dragon3api.com/pricing`

上游官方：

- Google Veo first/last：<https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames>
- Alibaba Wan 3.0：<https://help.aliyun.com/zh/model-studio/wan3-video-generation-api-reference>
- Alibaba Wan 3.0 official landing/API entry：<https://modelstudio.console.alibabacloud.com/model-releases/wan3.0-video>
- Vidu model map / start-end：<https://platform.vidu.com/docs/model-map>、
  <https://platform.vidu.com/docs/start-end-to-video>
- Kling 3.0：<https://kling.ai/document-api/apiReference/model/textToVideo>
- xAI video：<https://docs.x.ai/developers/model-capabilities/video/generation>
- MiniMax H3：<https://www.minimax.io/blog/minimax-h3>、
  <https://www.minimax.io/news/minimax-h3-open-source>
- Seedance 2.0 API：<https://api.volcengine.com/api-docs/view?action=CreateContentsGenerationsTasks&serviceCode=ark&version=2024-01-01>
