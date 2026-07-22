# Player Summary Schema v1.0

`player_summary_*.json` 是 RiftCoach 领域核心向 Harness、报告、评测和未来 Skills 提供的稳定数据契约。

## 顶层字段

| 字段 | 说明 |
|---|---|
| `schema_version` | 当前固定为 `1.0` |
| `metadata` | 生成时间、来源和处理数量 |
| `player` | Riot ID 与脱敏 PUUID 前缀 |
| `request` | 请求场次、队列、短局阈值和 Data Dragon 版本 |
| `recent_summary` | 只基于有效聚合样本生成的近期汇总 |
| `matches` | 成功解析的全部对局，包括被排除的短局 |
| `failed_matches` | Match Detail 阶段无法解析的对局与错误原因 |
| `excluded_matches` | 保留明细但不计入聚合的对局与排除原因 |

## 单局状态

每条 `matches` 记录必须包含：

- `included_in_aggregate`：是否进入近期统计；
- `is_short_game`：是否低于配置的最短时长；
- `exclusion_reason`：未进入统计时的结构化原因；
- `timeline_status`：`available` 或 `unavailable`；
- `timeline_error`：Timeline 缺失或解析失败时的原因。

Timeline 不可用时，Match Detail 指标仍可进入聚合，但死亡时间、装备购买事件等 Timeline 指标必须为 `null` 或空集合，不能伪造为 0。

## 短局策略

默认将少于 300 秒的对局视为短局：

- 对局仍保留在 `matches`，便于审计；
- 不进入胜率、补刀/分钟、经济/分钟等近期汇总；
- 阈值可以通过 `--min-duration-seconds` 调整。

## 兼容规则

下游消费者必须验证 `schema_version`。不带版本的旧 Summary 不再被静默接受，需要重新运行数据构建脚本或显式迁移。
