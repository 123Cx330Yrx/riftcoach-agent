# 8E Timeline DTO/UI 设计

## 初学者先理解

Timeline 在这里不是“把所有数据画成曲线”。它是把一场比赛中带时间戳的事实放到同一条尺子上：
死亡、购买和目标事件发生在第几分钟，属于 early/mid/late 哪一段。DTO 是后端给前端的严格数据合同；
exact decoder 则是前端的海关，字段多、少、类型错或 run identity 不一致都会拒绝。

`partial` 也不是报错：例如五场比赛中四场拿到 Timeline、一场 Riot 源暂不可用，页面必须展示四场真实
事件并明确一场缺失，不能把缺失填成 0，也不能让整个工作台消失。

## 数据合同

- run binding：`run_id`、固定 Skill、version、terminal/publication status；
- posture：overall `available | partial | unavailable`；
- bounds：total/projected match count、per-match total/projected event count、truncated flag；
- match：safe match id、champion、role、win、duration、aggregate inclusion、availability、安全原因；
- event：`death | item_purchase | objective`、真实秒数、`early | mid | late`、安全 label、可选 item id；
- source：固定 `riot_match_v5_timeline`，不把 OP.GG 或推理混入比赛事实。

## UI 结构

Desktop 为 match strip → focused phase rail → chronological detail list；mobile 把 match strip 横向滚动，
轨道和列表纵向堆叠。轨道的 marker 位置由 `atSeconds / durationSeconds` 计算，不写死百分比。列表始终存在，
所以颜色、hover 或动效都不是获取信息的唯一方式。

## 状态与失败

- available：展示真实 marker；无事件时明确“没有投影事件”，不画平线；
- partial：顶部说明缺失场次；可用场继续可选；
- unavailable：展示固定原因和 match detail fallback，不渲染空轨道冒充零事件；
- identity/integrity failure：沿用 body-free `run_integrity_failed`，不泄露 Artifact 路径、玩家身份或异常正文。

## 视觉合同

内容密度高、spectacle 低：青色用于选择与方向，金色只用于阶段/关键目标，红色只用于死亡；面板不增加
新的齿轮、仪表或常驻旋转。进入动效短且只发生一次，focus-visible、reduced-motion、320px overflow 都是
交付门。
