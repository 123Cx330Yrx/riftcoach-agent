# 8E Corrected Veo A Comparator 可执行 Preflight

## 范围与目的

该单样本不是重抽上一条 Veo。它隔离测试 RQ-125/126/127 指出的两个关键变量：去掉相同 lastFrame，并把
过长、保守、重述画面的 prompt 改为 short motion-only direction。模型/transport/source/8s/1080p 保持一致，
以判断上一样本的轻微/局部运动是否主要受输入策略限制。

## 固定输入

- transport/model：DragonAPI / `Veo3.1-quality-official`；
- source v2 SHA：`8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`；
- first frame：v2 exact-SHA public URL；last frame：`absent`；
- positive prompt：819 bytes，SHA
  `b02264cf1ff442cad7f2b6968c27369dec67f3e59a0a72e46bc8e066513b8e29`；
- negative prompt：357 bytes，SHA
  `931f0b052d08ec12805c3da0e02d28dc059f7566f080ee7e0ba7d468551a348d`；
- runner：7,136 bytes，SHA
  `cee5ac21b88180afe734470b8c3b49fc26046443b6f613e93e7172c0deeba850`；PowerShell parse pass；
- request：8s、16:9、1080p、audio false、lossless、pad、personGeneration `dont_allow`；
- positive prompt 不含 subtle/imperceptible/restrained/gently；显式 entire frame、left/center/right、foreground/
  midground/background、medium-to-strong、cool/dramatic 与一轮 breathing cycle。

## 执行边界

- 只在用户可见 secure prompt 读取 existing Key；不回显、不写盘，finally 清零；
- 一次 POST、同 task 12s 轮询、无自动重试/第二 task/充值；
- 只从 completed query 的 result URL 下载；不依赖已证实 403 的 `/content`；
- status 只保存 body-free identity/digest/progress/error/host，不保存 prompt、Key、signed URL 或 raw response；
- 成片先审 source、全幕 breathing/强度/几何与大区静止；只有运动通过才进入 deterministic seam，不能反过来
  用 crossfade 掩盖生成失败。

## 视觉硬门

- 图和环境本身运动，禁止 HUD/line/ring/node overlay；
- near/mid/far 与 left/center/right 从第一秒同时持续参与；
- 体积空气、大尺度蓝金光影、建筑/地面/反射、全道路能量、Rift、水晶与整片星空共同呼吸；
- camera 可做构图锚定小幅 float/parallax，禁止突发 zoom/reframe/shake/crop；
- motion 必须 medium-to-strong、clearly perceptible、cool/immersive；三主体轮流或大区静止即 rejected。
