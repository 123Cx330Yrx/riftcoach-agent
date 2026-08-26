# 8E Seedance 2.5 Portal sample audit

## 执行与恢复事实

- ratio fix preflight `c6143c196e3251af53c5bd2e697206df92a8b04b` / Actions `32960467379` 三 job 全绿；
- Studio readback：同一 v2 first+last 两张、Seedance 2.5、8s、720p、`adaptive`、no audio、enhancement off；
- prompt 1,776 B/SHA `91ca48b714d7aa7c7263416e8371205e2d0b78a26aeefaeb442a4d080853b322`；
- task `task_w6ggXo15mMMw5Y3KMu9CfLK1QLevULvW`，137 秒、100%、NewAPI terminal `成功`；
- 实际费用 `$11.9566`；没有退款。external video calls `9`，production media `0`；
- Studio 在任务完成后访问结果内容时返回 403，将成功 task 错投影为“生成失败”；
- 用已有 Dragon Key 的 GET-only recovery 查询同一 task，从 `task.result.data[0].url` / `files.toapis.com` 下载；
  `post_attempts=0`，没有新生成或额外费用。

## 原片身份

- local file：research scratch `dragon-seedance25-portal-v5-first-last-adaptive-720p-8s.mp4`；
- SHA-256：`acf68ba63a3382f4c79bee090ca9c89ff39727e35af26685aba1c9cc1add56c4`；
- 5,429,356 B；1280×720；H.264 High；yuv420p；24fps；193 frames；8.041667s；无音轨；
- 原片与抽帧留在 repo 外，不进入 production manifest。

## 视觉与数值初审

- 人工抽帧：camera/architecture/composition 基本锁定，无 global push、HUD overlay 或显著 melting；
- left Rift、center crystal/platform 与 right tactical field 从首帧到 4s 均有明显变化；中央水晶中段亮度增强；
- source scaled→first SSIM `0.864923`，低于 source fidelity hard gate `0.95`；
- first→4s SSIM `0.852572`；left/center/right 分别 `0.823370 / 0.892302 / 0.840886`，证明三大区均参与；
- last→first SSIM `0.939557`，raw seam difference `1-SSIM = 0.060443 > 0.03`；left/center/right seam SSIM
  `0.939835 / 0.947600 / 0.930683`，右区最弱；
- codec/pix_fmt/fps/bytes/no-audio 可用，但 720p 低于原计划 1080p production target。

## 当前裁决

`candidate_requires_user_visual_review_and_postprocess_proof`：

- 不按 Studio 403 误判生成失败；
- 不按三大区有运动直接 adopted；
- 该样本是目前最接近 locked-camera/full-scene organic motion 的候选，但 raw source identity、seam 与 resolution
  仍不过门；
- 用户已观看并认可三主体方向，指出静区像雾层覆盖；因此下一动作改为 RQ-133 的文档化 video edit，而非
  no-generation 后处理或重抽。原片仍不 adopted；编辑结果需重新过人工静区运动、source/seam/codec 门。
