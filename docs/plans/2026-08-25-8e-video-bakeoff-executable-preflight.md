# 8E Video Bake-off 可执行 Preflight（Task 5）

## 1. 范围与当前裁决

- 检查点：`8e-productization / portal-motion-polish / runtime Task 5 media bake-off`；
- 本记录只冻结可执行身份、Key presence、prompt digest、素材、调用顺序、预算和停止线；不保存 Key、prompt
  正文、cookie、账号标识、账单正文或原始 API 响应；
- 用户已明确：正规 DragonAPI 中转可以实际试用，不能把 official-first 误解成 relay 不调用。授权覆盖当前
  Task 5 中必要的有界单样本横评，无需逐候选再次询问；不授权充值、订阅、批量生成或无限重抽；
- 当前尚未上传 Portal 母图，也没有创建任何视频任务。

## 2. 可执行 transport

### A1：千问AI平台 / DashScope（第一方）

- identity：千问AI平台由通义云启（杭州）信息技术有限公司提供，使用阿里云账号体系；请求 endpoint 为
  `https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`；
- available models：`wan3.0-video` 与 `wan3.0-video-prime`；Prime 声明能力对齐标准版、只优化端到端速度；
- access：用户已提供标准版官方模型市场 UI 并确认邀测通过；当前登录页又显示 Prime API 参考、体验能力和
  可用免费视频秒数；
- Key presence：API Keys 管理页存在现成 Key；只核对 existence，不读取/复制值；
- first sample：优先使用已登录第一方体验 surface；若体验 surface 无法明确 first+last/1080p/audio-off，停止并
  改为用户在本机安全注入 `DASHSCOPE_API_KEY` 后调用，不读取浏览器 Key；
- request：8s、16:9、1080p、audio false、watermark false、first=last=同一 source derivative；优先消耗免费
  额度，不充值；只生成 1 个结果。

### A2：DragonAPI / Veo 3.1 Quality relay

- endpoint：`https://newapi.dragon3api.com/v1/videos`；model `Veo3.1-quality-official`；
- access：账号登录；Key 管理页存在 1 条现成 masked Key；只核对 existence，不读取/复制值；
- execution surface：优先使用 DragonAPI 自有在线体验/任务日志，避免导出 Key；若 surface 不能表达首尾帧和
  lossless/pad，停止并改为用户在本机安全注入 Key；
- request：8s、16:9、1080p、generateAudio false、`compressionQuality=lossless`、`resizeMode=pad`、
  first=last=同一 source derivative；只生成 1 个结果；
- 不新充值；使用现有余额。价格页/模型广场币种符号冲突，提交前 UI 必须显示本次实际费用且不超过既有
  单次上限；失败不自动重复提交。

## 3. 固定 source 与 motion brief

- source path：`docs/assets/8e-portal/portal-mother-image-source-v2.png`；
- source SHA-256：`8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`；
- source bytes/dimensions：`2,268,033` / `1672×941`；v1 SHA `552a874...aada` 只作 archival parent；
- prompt body：仅存在本地 research scratch，不入 Git；UTF-8 bytes `1662`；
- prompt SHA-256：`f324264150a729daad5e7be71d5e762e8fec496d98e94ffebd2fdddcbd2f36fc`；
- 核心 motion language（prompt body/digest 不变，但输入身份已迁移到 v2）：
  1. 左 Rift 漩涡、云雾、远景空间持续闭环；
  2. 整条能量道路、前景平台和反射贯穿循环；
  3. 原水晶只做内部折射/呼吸且轮廓位置不变；塔体金缝/平台同步；
  4. 右星图整体极慢运动，连线、节点、紫色核心、粒子与环境光持续变化；
  5. 所有主要层都动，不以局部粒子冒充全局；镜头 locked，无 zoom/reframe/crop；
  6. 第 8 秒回到与第 0 秒相同的位置、相位、曝光和速度；无黑场、无音频。

同一 semantic prompt body 用于 Wan/Veo；只允许字段名、模型专有负面参数和语言包装差异，不改变 motion brief。

## 4. 调用与审计顺序

1. A1 official Wan 单样本；创建后只轮询同一 task，不因客户端超时重复提交；
2. 下载到 research scratch，立刻记录 body-free task/model/transport/timestamp、output SHA/bytes、ffprobe；
3. 执行 source→first SSIM、manual anchors、locked camera/geometry/full-frame motion/seam；任一硬门失败标 rejected；
4. A2 Dragon/Veo 使用相同 source/prompt/scorecard；
5. 两项结果并列比较。若都失败，才按已冻结替补池 `Vidu Q3 Pro → Kling v3 → MiniMax H3 → Seedance/Grok`
   逐一进入新的单样本槽位；用户已授权必要试用，但每项仍是一候选一调用、首错停止、无充值；
6. 只有通过 source/geometry/full-frame/seam 的结果才进入 C 线分层/HyperFrames 结构合成；任何 raw 结果不直接
   接入 RiftCoach runtime。

执行结果：A1 已由 `2026-08-26-8e-video-bakeoff-wan3-sample-audit.md` 以单次有效调用完成并 rejected；不重抽。
当前 handoff 严格进入 A2 Dragon/Veo。

## 5. Account 不得丢失的同 Task 5 后半段

本 Portal bake-off 只是在已确认 source 上选择制片方法，不把 Task 5 缩减成 Portal-only。两个首轮 Portal 样本
完成审计后，canonical 必须在 RQ-108 内按以下顺序继续，不能跳到 Task 6、Coach、RQ-103 或 8F：

1. 回到 Account source gate：以官方 map11/near-final reference 制作 annotated topology overlay；
2. 无英雄峡谷内殿底座同时通过“三路/河道/双野区/双坑/基地/左下蓝右上红”和 intentional-abstraction /
   no-fake-precision 人工门；当前 v3 仍是未签收 preview，不能自动晋级；
3. Camille、Kindred、Ahri、Jinx、Thresh 逐位场景化重塑，逐个检查解剖、武器、尾巴/面具/羊狼双体、
   路线接触、遮挡、投影和反射；禁止群像一次生成或 splash 抠图；
4. 分层合成 adopted Account source，补官方参考/provenance/Riot 合规/免责声明/移除路径；
5. 用本轮胜出的生成式/确定性/混合式制片方法制作 Account 10 秒 desktop/mobile 全帧 loop，并走同一 Task 4
   媒体审计；
6. Portal 与 Account 的 production manifest/renditions 全部通过后，才进入 runtime Task 6 双幕产品组合。

因此 Account 母图当前状态准确表述为 `preview / blocking / not adopted`，不是“已完成”，也不是“后面再说”。

## 6. 数据与费用边界

- 上传内容仅为无玩家数据、无账号、无 Riot/OP.GG/日志的原创 Portal 概念母图；
- 不上传 Account 英雄素材或任何用户数据；
- 浏览器调用前若出现实际扣费/购买确认，必须确认显示费用落在已有单次上限；不购买 credits、不订阅；
- Key 始终留在用户账号/本机秘密环境；不进入 prompt、日志、repo、聊天或任务记录；
- 结果远程 URL 立即下载后不作长期热链；有删除/清理能力时在本地证据固定后清理远程任务/临时素材。
