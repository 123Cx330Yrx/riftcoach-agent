# 8E Corrected Veo Failure 与 Vidu Q3 Pro Preflight

## Corrected Veo 执行结果

- preflight `d763960506a8cc56ca2ce1622d3468648c9004d4` / Actions `32929057870` 三 job 全绿后执行；
- Dragon/Veo task `task_c3yCIRHEPrYK6roEPCfvDk4lbdtH77mT`，one POST、first-frame only、no lastFrame、
  positive SHA `b02264...8e29`、negative SHA `931f0b...a348d`；
- 控制台记录 158 秒、100%、failed；唯一公开错误为 `Generation failed: task processing failed`；
- 没有 output/result URL，无法评价 corrected prompt 的运动质量；没有自动重试/第二 Veo task；
- verdict：`transport_or_upstream_task_failed_quality_unknown`；external video calls 累计 `3`，production media `0`。

该失败不能写成 prompt 失败、Veo 质量失败或 RQ-127 不可达。RQ-128 又把 fault domain 明确保持 unresolved：
可能来自 request/schema/parameter、relay/upstream task 或 transient processing，现有公开证据无法区分。按首错
停止不盲重跑；Vidu 是同 transport/source/motion/first-only 下的控制变量实验，不是宣布 Veo/方法作废。

## Vidu Q3 Pro schema 与选择理由

Dragon 专用文档把 `viduq3-pro` 映射为高质量模型，并明确：

- `image_urls` 传 1 张为首帧图生视频；2 张才是首尾帧；
- duration 1–16s、resolution 540/720/1080p、`aspect_ratio` 顶层；
- `audio` 顶层且默认 true，因此本项目必须显式 false；
- `seed` 为顶层 integer；本次固定 127；
- metadata 的 subjects/auto_subjects/voice/audio_type/off_peak/payload/callback 均不需要且不发送；
- Vidu 没有文档化 negativePrompt，因此否决语句压缩进同一 motion-only prompt，不用 opaque payload 透传。

Vidu 比继续重抽 Veo 更能隔离“Provider task failure”与“motion direction”两类问题，且仍保持 first-only 与
RQ-127 目标不变。

解释矩阵：Vidu completed 才能进入质量比较；Vidu 也 generic failed 时优先停止并审计 relay/request，不再继续
换模型；Vidu 有 output 但运动失败时，才新增 Vidu/当前方法的质量证据。Veo 仍保留为 unresolved，不永久拒绝。

## 冻结 Vidu 输入与停止线

- model：`viduq3-pro`；source v2 SHA `8134c0ca...1a06e`；1 张 public exact-SHA image URL；
- prompt：1,007 bytes，SHA `a38bdcecaf938f65cceaf56ba925491ddd72c7fd4df2a6a83f3eef4965e7bb72`；
- runner：SHA `60e4f80139aebcec53ea434f8174126ed6123f6841fb55638007ad3643b124f5`；PowerShell parse pass；
- request：8s、1080p、16:9、audio false、seed 127、first only；
- prompt 不含 subtle/imperceptible/restrained/gently；显式 entire frame、near/mid/far、left/center/right、
  medium-to-strong、cool/dramatic、no HUD/static regions/object-by-object motion；
- secure existing Key、one POST、same task polling、no retry/top-up/off-peak/callback/raw response；
- output 先审图本身全局呼吸/幅度/几何，再审 codec/source；只有运动通过才做 seam，不为循环追绿。
