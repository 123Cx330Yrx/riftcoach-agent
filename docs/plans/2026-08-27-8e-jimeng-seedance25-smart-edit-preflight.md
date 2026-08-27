# 8E 即梦 Seedance 2.5 智能编辑 preflight

## 目标与为什么改走这一条

Dragon relay 的 v6.1 `video_operation=edit` 在 task 创建前 HTTP 400，原 runner 又丢失 response body；豆包工作
标准套餐虽成功调用 Seedance 2.5，但 Skill 实际把 Video1 抽成首尾帧再做 image-to-video，输出按 source、seam、
水印、音轨和视觉门拒绝。即梦官方 UI 的 `智能编辑` 是当前唯一已观察到的专用单视频 edit 入口，因此只在这里
继续一次真正的 Video1 编辑，不再用首尾帧重抽冒充 edit。

## 素材裁决

第一轮只用两个互补素材，不因“支持多参考”而堆叠图片：

1. `编辑视频`：repo 外成功 Seedance MP4，SHA `acf68ba63a3382f4c79bee090ca9c89ff39727e35af26685aba1c9cc1add56c4`，
   负责原有运动、时长、镜头、构图和连续性；
2. `参考内容`：immutable v2 PNG，SHA `8134c0ca00223e1ff180630be9d21f4c21da0e97e952fbc09e6713209e81a06e`，
   负责几何、材质、线稿与色彩身份。

不追加其他审美概念图：新增图会引入不同构图/材质/光照，增加平均化和重绘风险。用户截图已确认 `高级编辑`
上传后可用，提供矩形、画笔、箭头、文字、橡皮、定位点与说明输入；因此优先使用区域框选/标记表达左 Rift、
中央水晶、右能量场和整体环境，而不是第三张图。只有后续证明纯文本/标注无法让
右侧/静区被模型识别，才另行设计一张不含新审美元素的功能性 motion mask，并先过独立采用门。

用户纠正后，旧“在单一帧放五标注”方案作废。可验证教程与 ByteDance 官方时间戳能力说明确认：高级编辑应先
播放/拖动到具体时间并暂停，再在该帧框选/箭头/定位、填写该时间点说明并点“添加至输入框”；添加后形成 `00:xx`
帧标注，可重复创建多个时间点。当前 8 秒循环采用三个时间戳，避免逐秒过约束：

- `00:00`：红/黄/绿矩形分别覆盖完整左 Rift、中央水晶/平台、完整右场；蓝箭头沿道路指向 Rift；白定位点放在
  上中建筑。说明要求三主体和全局环境从第一帧同时启动；
- `00:04`：同样三个主体矩形；定位点/画笔只补建筑接缝、地面反射和空气层。说明要求左/中/右同级达到运动峰值，
  尤其右场不能落后；
- `00:07`：三个主体矩形即可，说明要求所有系统保持运动并在 8 秒末回到接近 0 秒的相位、曝光和速度。

不用文字工具，避免画面生成文字。三份说明位于 repo 外：`portal-motion-v7-jimeng-frame-00-{00,04,07}.txt`；每个
时间点都必须单独“添加至输入框”，主页面最终应出现三个帧标注。旧单帧 note SHA `5e69688...9a419` 不得再用。

## RQ-134 动效编排

prompt v7 同时冻结两个硬门：

- 三主体增强：左 Rift、中央水晶/平台、右星图/能量场均全程运动，右侧单列不可遗漏；
- 全局增强：建筑、道路、地面焦散/反射、多层云/空气和星空纵深同步运动。

豆包样本只保留“光流沿真实道路和结构接缝运动”的动作语言；主色改为冷蓝/青蓝/电弧蓝，暖金仅作低占比节点和
金属边缘强调。光轨只是 motion stack 一层，不能替代三主体内部运动或全局 breathing。

设计阶段长版 prompt 文件位于 repo 外：`portal-motion-v7-jimeng-smart-edit.txt`，1,439 chars / 4,115 bytes /
SHA-256 `edbc0d39f778b2002bd2ca48300d83d176255e4dd07838854b7505e04be6f388`。它冻结 motion intent；实际 UI
又把主 prompt、三个 frame reference 和三段说明共同计入 2,000 字上限，所以执行时使用压缩等价版。实际主
prompt 为 534 chars / SHA `d003f047...cff10`，稳定 frame-placeholder projection 为 822 chars / SHA
`6dcd29d4...9d411`；各帧说明 digest 与原文见 result audit。历史长版不得冒充实际提交。

生成前核对页面仍为 `Seedance 2.5 / 智能编辑`、正确 MP4、正确 v2 PNG、自动时长/比例、720P、音频行为、
实际积分和高级编辑状态。

## 调用与停止线

- 文件选择由用户手动完成；Codex 不再自动操作系统 file picker。
- 上传本身不等于生成授权。页面 readback 和 prompt 审核完成后只执行一次，不自动重试、不追加参考图抽卡。
- 输出为 sibling candidate，绝不覆盖原视频。先人工检查 source/镜头、三主体、尤其右场和整体环境，再审
  codec/audio/watermark/source-first/region motion/seam；任一核心维度劣化即拒绝。
- 当前 Chrome 扩展能连接，但即梦页面本身的 DOM/截图读取持续超时。无法可靠读取页面时，不由 Codex盲点；
  用户上传后通过可见截图/明确页面读数完成 preflight。

## 执行后状态（2026-08-27）

用户在本 preflight 尚未取得 exact-SHA 公共闭环时手动完成一次 official Smart Edit。该顺序偏差原样披露，不能
重写成 public-gate-first。raw SHA `4d3660...155b`；三大区和九宫格有运动、镜头/建筑初审稳定，但 v2→first
`0.889072 < 0.95`、seam DSSIM `0.046536 > 0.03`，另有 AAC 与非 fixed-24fps。零费用 FFmpeg 仅成功修复
codec delivery contract，最佳 J seam `0.042684` 仍 fail 且 source identity 降至 `0.849216`。结果状态为
`revise-candidate / not-adopted`，有效 calls `11`、production media `0`；完整证据见
`2026-08-27-8e-jimeng-seedance25-smart-edit-result-audit.md`。
