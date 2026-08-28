# ADR-0069：采用本地地区壁纸作为 Portal 动效回退

- 状态：Accepted for 8E Portal motion fallback design
- 日期：2026-08-28
- 范围：`8e-productization / portal-motion-polish`

## 背景

连续的 Wan/Seedance/Veo/Kling 与局部分层实验都暴露了同一问题：复杂的 Portal 母图没有可靠的区域和时间
控制，模型或分层贴材质会产生漂移、重影、蓝雾、硬环或局部静止。用户提供的 `animated-demacia.webm` 已经
是完整的高质量动态场景，证明“成品场景媒体”比继续生成整幕更接近目标。

## 决策

1. Portal 的动效回退采用“地区选择 → 本地动态壁纸 → 语义激活 → Account”的结构；Account 使用独立静态壁纸。
2. 壁纸只作为 presentation layer，React/DOM 继续拥有选择、焦点、按钮、URL、Auth 和 Player Link 控制流；壁纸
   不能承载产品文案、数据或交互语义。
3. 候选文件必须是本地 content-hashed 资产，并有 WebM/MP4、poster、loop、尺寸、体积、来源/许可和移除路径记录。
4. Riot League Displays、用户自有素材或明确允许再分发的素材优先；Steam Workshop/Wallpaper Engine 下载作品
   默认只作研究或本地预览，未获得作者许可前不得进入公开仓库或 runtime。
5. 每个候选必须通过 source/rights、编码/浏览器、移动端、reduced-motion、poster-first、loop 和人工视觉门；未
   通过的文件不构成 production media。

## 为什么不直接采用 Wallpaper Engine 场景

Wallpaper Engine 的 scene/web 壁纸更像运行时项目而不是一个可直接交付的 MP4；官方文档说明不能直接导出成
GIF/视频，下载作品重新发布还可能需要原作者许可。因此我们可以使用用户已经拥有的独立 WebM，或对自制/获准
素材做受控录制和转码，但不把 Workshop 场景包当作网站依赖。

## 后果

正面：运动来自经过创作的完整场景，减少模型重绘和贴层重影；地区选择让 Portal 有产品叙事，Account 可以保持
清晰可读。代价：需要维护多份视频、poster 和许可证证据，WebM/MP4 双格式增加体积，移动端必须保留静态降级，
动态素材的版权不再是可忽略事项。

本 ADR 只批准 fallback 的设计和研究预览，不批准任何具体第三方文件进入公开 runtime；`animated-demacia.webm`
仍是 `research-candidate`。
