# 8E Seedance 2.5 视频编辑提交 400 诊断

## 已发生事实

- 已公共关闭的 v6.1 runner 只执行了一次 POST；source task GET 成功后，POST 在
  `submitting` 阶段返回 HTTP 400；本地状态更新时间为
  `2026-08-26T12:28:05.5643980Z`。
- `task_id` 为空，output 不存在。Dragon 任务日志仍只有此前 8 个视频任务，没有
  新的隐藏 edit task；通用日志也没有新增本次扣费行。因此本次费用为 `$0`，有效
  external video task/call 账本继续为 `9`，production media 继续为 `0`。
- 这不是模型生成失败，也没有任何输出质量证据。当前只可分类为
  `request_or_schema_rejected_before_task_creation`。

## 为什么还不能断言具体字段

原 runner 的异常处理只保存 HTTP status，没有读取 `ErrorDetails`/response content，
因此本次响应正文已经丢失。登录态 Dragon 通用日志只显示 18:49 的旧 ratio 400，
不能拿它冒充 20:28 左右的新 edit 400。

Dragon 专用文档仍把当前各单项列为合法：`seedance-2-5`、`video_operation=edit`、
`video_with_roles(reference_video)`、`duration=-1`、`aspect_ratio=adaptive`、720p、
`image_with_roles(reference_image)` 与多模态参考。故在缺失本次 error body 时，不能
猜测是 Video1+Image1 组合、duration、ratio、reference URL 或其他字段。

## 本地诊断缺口修复

- 新增 `scripts/sanitize_dragon_video_error.py`：只接受严格的 outer/nested error
  形状并投影 `code/param/type` 与经过 request-id/敏感标记过滤的 bounded message；
  未知形状、额外字段、URL、Bearer/API Key/签名参数只留下 UTF-8 byte length 与
  SHA-256，不保存 raw response。
- `tests/test_dragon_video_error.py` 先以缺模块红灯，再以三项测试覆盖已知 ratio
  形状、未知敏感正文和带额外字段的拒绝路径。
- repo 外 revised runner：
  `run-dragon-seedance25-video-edit-diagnostic-v2.ps1`，SHA-256
  `e7eb8c91c2ba6422fcc56fc1d2553b7c7fb1541a4b73c37843cbf46397c0807f`；
  PowerShell 7 `-SelfTest` 通过且无网络；静态审计仍恰好 1 POST / 2 GET；其唯一
  output/status 路径均不存在，尚未执行。
- sanitizer SHA-256 为
  `f5c4f6797cd71a00c417d2ad029119f6ffb45dbe08d3c941d3967c5397158f5a`，
  revised runner 在 Key prompt 前核对该 digest，防止诊断逻辑漂移。

## 裁决与停止线

本批只修复“下次不再丢 error body”的本地可观测性，不修复尚未知的远端拒绝原因。
在获得本次精确 error body 或另一个可证伪的字段修正前，不重发同一 POST、不删
Image1 或 Video1 试错、不换模型。原成功 Seedance 视频继续保留；失败 v6.1 status
继续只读保存。

## 即梦官方 UI 的只读替代预检

用户打开的即梦官方创作端已只读核对，未上传、未生成、未购买积分或会员：

- `全能参考`：Seedance 2.5，可组合最多 50 个图片/视频/音频参考；当前显示 720P，
  属于从多参考重新生成，保留现有成片的约束弱于专用编辑。
- `首尾帧`：Seedance 2.5，首帧+尾帧、720P；适合控制开闭相位，但会重新生成中间
  运动，不能替代“保留现有三主体动效”的编辑目标。
- `智能多帧`：当前 UI 自动切到 Seedance 1.0 Fast，用逐镜头/关键帧编排；不是本轮
  Seedance 2.5 成片增强的首选。
- `智能编辑`：Seedance 2.5，有独立 `编辑视频` 槽，只接受单个 MP4/MOV；另有可多选
  的图片/视频/音频 `参考内容` 槽。比例/时长显示 `自动`、输出 720P；上传后才解锁
  `高级编辑`。该合同与 Video1 成片 + Image1 母图双锚点最吻合。
- `超长视频`：Seedance 2.5、30 秒、720P，面向长叙事，不适合当前 8 秒 loop，漂移、
  成本和 seam 风险都更高。

页面显示 Free 当前计划且支持直接购买积分；API 服务购买出现在超级会员权益中。
因此若改走官方路径，先用官方 UI `智能编辑`，不先购买高价会员或 API 套餐。只有
上传两项素材并看到本任务实际积分后，才决定是否购买最小所需积分并执行一次；该
上传/付费/生成尚未授权或发生。

## 豆包工作 30 天标准套餐候选

- 2026-08-25 的首发 30 天订阅活动已由豆包工作客户端搜索、豆包公关负责人公开
  表述及多家发布报道交叉支持；当前本机客户端左下角已显示 `标准套餐`。具体到期日
  和剩余额度尚未从账户页读回。
- 豆包工作客户端检索结果称标准套餐可用月度额度调用 Seedance 2.5；字节官方账号
  也已公开宣布 Seedance 2.5 上线豆包专业版。
- 豆包与即梦的产品合同不同：豆包没有即梦五个显式模式按钮，而是通过上传两张图、
  上传多模态参考、或上传视频并在 prompt 写“编辑视频”来触发首尾帧、全能参考和
  智能编辑；独立高清度/运镜控件也更少。
- 因此豆包工作是“同一官方模型、零新增现金”的条件 comparator，不是已经证明与
  即梦智能编辑逐字段等价。只有在运行前读回 Seedance 2.5、素材角色、额度和停止线，
  才允许一次对话式 edit；当前没有上传或任务调用。
