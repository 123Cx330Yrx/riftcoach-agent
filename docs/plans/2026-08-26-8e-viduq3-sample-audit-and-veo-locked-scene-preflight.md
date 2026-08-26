# 8E Vidu Q3 样本审计与 Veo Locked-Scene Preflight

## 1. Vidu Studio-contract 调用事实

- predecessor `22e3ad4db02bc1a2486d46eacd29cfd10f2ad7a4` / Actions `32942367833` 三 job 全绿；
- `viduq3-pro`、1 张 first frame、8s、1080p、16:9、audio true、no seed；
- task `task_SpHkjXvRBtzdsHhVwwRlm2gr8z7mIkEU`，one POST，completed/downloaded；
- output SHA `6e1ce903eb1fdb5db3914f9e73192a1b276184f04073d089f5cb86100eb6251a`，12,616,484 B；
- 1920×1080、24fps、193 frames、8.041667s、H.264 High/yuvj420p/full-range/BT.709、AAC stereo；
- metadata AIGC ProduceID 含 `720p`，与 container 1920×1080 冲突，不能证明 native 1080p；
- audio-remux preview SHA `7a371309...a2003`；research-only，不入 repo/runtime；
- external video calls 累计 `5`，production media `0`。

成功证明 DragonAPI、public image URL、Vidu first-only 与 motion-only prompt 可工作；此前 generic failures 至少
与 API 参数/relay mapping 有关，不能归因模型或方法。

## 2. Vidu 视觉裁决

- source→first SSIM `0.790736`；first→last `0.574903`，seam DSSIM `0.425097`；
- adjacent DSSIM p95 `0.083309`，allowed `0.124963`，raw output 不能 loop；
- 3×3 first→mid SSIM `0.378175–0.813710`，整幅画明显变化；
- 人工/用户审查：变化主要来自持续相机推进/整体漂移/重新取景；原场景被平滑化，景内动效仍粗糙，不是
  fixed-composition living matte painting；
- verdict：`rejected_sample_for_global_camera_drift_source_fidelity_motion_language_seam_and_resolution_provenance`；
- 只拒绝该 sample，不拒绝 Vidu 或 first-only。

## 3. RQ-129 唯一运动目标

1. frame/lens/scale/composition/architecture/object positions locked；
2. near/mid/far 与 left/center/right 的景物内部同时持续运动；
3. 体积雾/空气、大尺度蓝金光影、建筑/地面/反射、全道路能量、Rift 内层、水晶折射和整片星空体积场形成
   medium、clearly visible、intricate/cool motion；
4. 雾有遮挡与深度，光沿真实材质/表面传播；能量/反射/水晶/金缝相位协调；不是独立效果槽；
5. 所有系统同时运行，8 秒末 phase/exposure/velocity 回到起点；
6. no camera drift/pan/zoom/dolly/orbit/reframe/Ken Burns、no whole-frame exposure pulse、HUD/cheap bloom/melt/boil。

## 4. 为什么下一样本仍选 Veo

- 已有 Veo first+last 成功样本构图较稳，运动发生在场景内部，是最接近目标的现有证据；
- 旧 prompt 使用多个 subtle/slow/restrained 词，且运动是四个粗效果槽；新 storyboard 同时修强度与精细度；
- same model/transport/source/first+last 只改 storyboard，最能检验 prompt/art direction 是否主因；
- Seedance official `camera_fixed` 对 reference-image 场景/2.0 支持有限且效果不保证；
- xAI Grok I2V 无 first+last/fixed-camera contract，Dragon `grok-video-3` exact mapping/schema 未独立确认。

Veo locked-scene 仍不合格时，下一对照进入 Seedance 2.5；不是在当前样本前同时双发。

## 5. Veo locked-scene refined preflight

- `Veo3.1-quality-official`、same v2 first=last、8s/1080p/16:9、audio false、lossless/pad；
- positive 1,277 B，SHA `4dbdf0d3ab84b365da8b8d72dbcd57d6ab9a4608ca55d166154b3a689ea841f9`；
- negative 435 B，SHA `b6d7b49ff4f86a022d4f3fb80d3c57139e285f86984e44575921443c10149cbd`；
- runner 6,804 B，SHA `70332e28ad324f9537a3395530fb6dae178c009e7eaede535512d738bc488406`；parse pass；
- positive：locked-off camera + multi-depth fog/occlusion + surface-following caustics + multi-layer Rift + soft route
  currents/reflections + crystal subsurface/refraction + warm tower seams + volumetric star field，全部同时 medium/evident；
- negative：camera/global drift、whole-frame exposure pulse、static regions/local spotlights、HUD/cheap glow/clipped
  bloom、strobe/flicker/boil/melt/geometry/new objects；
- one POST/same task/no retry/top-up；Key/body/raw response 不落盘；
- 人工 camera-lock/motion-craft gate 优先；只有通过才进入 seam/encoding，不拿指标绕过视觉失败。
