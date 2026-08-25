# HyperFrames Task 5 安全、许可与隔离准入报告

## SKILL VETTING REPORT

- Skill：`general-video`（HyperFrames agent skill）
- Source：GitHub `heygen-com/hyperframes`
- Author：HeyGen；审计 checkout HEAD
  `6eaa2cb64b280c51cadb3843ce190f6f0b7493cc`
- Version：CLI/package `0.8.14`
- Repository metrics（2026-08-25 读取）：42,555 stars、4,081 forks、240 open issues；未 archived
- License：Apache-2.0；Copyright 2026 HeyGen, Inc.
- Files reviewed：所选 `skills/general-video` 全部 4 个文件；另定向审计 root/CLI/core/engine/producer package、
  telemetry/auth/update/registry/render/download 接缝和安装脚本

## 1. Red flags 与边界

### 不接受原样安装/执行 `general-video` skill

- skill 第一动作要求 `npx hyperframes skills update general-video`，会访问网络并改写 agent skill 安装目录；
- media 路由要求 `npx hyperframes auth status`，可进入 HyperFrames/HeyGen provider 登录与凭据路径；
- CLI production 默认 `telemetryEnabled: true`，带内置 PostHog ingest key、稳定匿名 ID、系统/命令/渲染事件；
  登录后 telemetry identity 还可能使用账号 email/username；
- CLI 会写 `~/.hyperframes/config.json` 和 `install-state.json`，默认做 npm update check；registry、字体、Whisper、
  remote media、cloud/Lambda/GCP/HeyGen paths 都具有额外网络或凭据能力；
- 根仓库 `prepare` 会安装 lefthook；CLI/engine 可以启动 Chrome/FFmpeg 子进程并下载远程媒体；这些能力对当前
  单一 Portal 结构层 preview 过宽；
- skill 自带并行 frame-worker 合同，但 RiftCoach 当前 Task 5 不需要多 agent，也没有用户授权把该 skill 的
  sub-agent 编排带入产品工作流。

这些都是可解释的正式产品能力，不证明项目恶意；但按最小权限原则，原样 skill 对本任务属于高风险/过宽。

## 2. Permission scope

原始 skill/CLI 可能需要：

- Files：项目目录、`~/.hyperframes`、全局/项目 agent skill 目录、浏览器/FFmpeg 路径、缓存和输出目录；
- Network：npm registry、GitHub registry、PostHog、HeyGen auth/cloud、远程媒体/CDN/字体及可选 provider；
- Commands：Node/npm/npx、Chrome/Puppeteer、FFmpeg/ffprobe，并可进入 Docker/AWS/GCP cloud 子命令；
- Credentials：HyperFrames/HeyGen auth、云部署和可选媒体 provider；本任务均不允许。

## 3. Risk classification 与 verdict

- `general-video` agent skill as-is：**HIGH / DO NOT INSTALL FOR TASK 5**；
- HyperFrames HTML/frame renderer as an isolated offline build tool：**MEDIUM / INSTALL WITH CAUTION**；
- 允许的用途仅为研究区内一次确定性 preview，不能成为 RiftCoach browser runtime 依赖，也不能访问产品数据。

## 4. 隔离 spike 允许条件

1. 只从官方 npm registry 安装 exact `hyperframes@0.8.14`；固定 integrity：
   `sha512-PT6KSNo6t8l/I8De3l20Aw0VS1wp3qu1HNf0r0/yB3wNj6fllUmmOK75rSkdJ2bjG4ocNVJZYOIeCHeYLBtnEA==`；
2. 使用独立 research scratch 和临时 HOME；不写用户真实 `~/.hyperframes`；
3. 安装使用 `--ignore-scripts`，不运行根仓库 `prepare`，不运行 `skills update/add`；
4. 运行环境固定 `HYPERFRAMES_NO_TELEMETRY=1`、`DO_NOT_TRACK=1`，并验证 `telemetry status` 是 disabled；
5. 不运行 `auth`、cloud、lambda、gcp、feedback、registry add、media-use、Whisper 或任何 provider 命令；
6. install 后渲染阶段禁用外网；HTML 不含 CDN、远程字体、远程图片/视频、fetch、WebSocket、analytics 或
   未 seeded randomness；只引用 scratch 内母图副本；
7. 不使用正在运行的桌面 Chrome；显式使用本机已缓存的 `chrome-headless-shell 152.0.7977.42` 与已安装 FFmpeg/ffprobe；
8. spike 只输出本地 preview、命令/版本/body-free digest 和失败原因；不把 node_modules、缓存或 raw log 写入
   产品仓库；
9. spike 通过也只证明 B/C 制片候选可运行。采用 HyperFrames 作为长期制片依赖仍需独立 ADR；失败则保留
   Remotion/plain FFmpeg 作为确定性对照。

## 5. 为什么引擎仍值得试

HyperFrames 的核心是普通 HTML/CSS/SVG 加 seek-safe timeline，由 headless Chrome 逐帧捕获并由 FFmpeg 编码。
它可以锁定母图、镜头、建筑、水晶、道路和 loop 时钟，而生成模型只负责有机运动 plate。Apache-2.0 没有
Remotion 的组织规模许可证门，且它不需要进入 RiftCoach 的 React bundle。

本次只需要证明：固定 source SHA 的本地图片能否在无网络、无遥测、无登录下按确定性 8 秒时轴渲染；不需要
借用 skill 的创意扩写、provider、云渲染、catalog 或并行 worker。

## 6. 隔离 spike 实际结果

- research scratch：`C:\Users\33502\Documents\Agent\tmp\riftcoach-task5-hyperframes-spike`；不在产品仓库；
- exact install：官方 npm registry `hyperframes@0.8.14`，`--ignore-scripts --no-audit --no-fund`；135 packages；
- source copy SHA-256：`552a87453daae53762f56f0cb5f7c7c2fee18256ef6d193c00575283e9b7aada`，与 archival source 完全一致；
- telemetry：`disabled / HYPERFRAMES_NO_TELEMETRY`；HOME 与 npm cache 均在 scratch；未登录、未运行 cloud/skills/
  provider 命令；
- first lint Bad Case：纯 CSS composition 缺 `data-no-timeline`，lint 正确拒绝；补显式声明后 0 error/0 warning；
- Windows browser Bad Case：用系统完整 Chrome 时，两次 `check` 均因 Puppeteer 临时 profile singleton 冲突失败；
  没有关闭用户 Chrome。改用本机已缓存、无网络下载的 `chrome-headless-shell 152.0.7977.42` 后，lint/runtime/
  motion 0 errors，layout 9 samples 0 issues；
- render：8.000s、1920×1080、24fps、192 frames、H.264 yuv420p、BT.709、无音轨；单 software worker，
  约 48.7s；v2 SHA-256 `64d234f306e4c5da8464d92977dfdf3c3f8b0111165d84ff28fc9219caf224b5`；
- determinism：frame 0 两次 PNG SHA 均
  `1f248379f9fe7a7ddd6fabb1470c19508541a63794ac070404faf2b80db1ffc5`；frame 191 两次均
  `26db619bf241ed9eac59d8d6c86e427cb7314b63b83d700ecde87fffead35056`；
- raw seam：frame 0→191 SSIM `0.999600`，证明 seek/frame renderer 闭合；
- default MP4 reject：5,650,074 B 超过 5.5 MB H.264 门；decoded seam SSIM `0.960673`，DSSIM `0.039327`；
  全片 adjacent DSSIM p95 `0.001868`，Task 4 threshold `max(1.5×p95,0.03)=0.03`，因此 encoded seam 不通过。

裁决为 `renderer-conditional-pass / default-encoder-reject`。HyperFrames 可以继续作为 C 线结构层帧生成器；正式
资产必须输出无损帧/高质量 intermediate，再由 RiftCoach 固定 FFmpeg VP9/H.264 pipeline 编码并走 Task 4 审计。
本 smoke 的 CSS 微动极弱，仅证明工具链，不满足 RQ-112 全帧视觉目标，不得成为候选 loop、poster 或 runtime。
