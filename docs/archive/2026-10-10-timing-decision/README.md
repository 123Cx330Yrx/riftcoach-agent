# 时间裁决源码归档

源自b00a9eaf父版本，当前共享实现扩展600秒候选前create-only保存。仅为历史
裁决源码证据，不是可执行发送器，不从归档加载或exec源码。

源文件按UTF-8/LF计算SHA，与原公开document_review_timing_decision_20261010.json一致：

| 源码 | SHA256 |
|---|---|
| scripts/audit_document_review_timing.py | 892892c628af3cabffa339bc8c3b6251a267a1dbf04022334f79ca89b65175f3 |
| app/evaluation/golden_stream_bridge.py | 9cae5009df191f10c94808c8512582128641c3523572e908e148333fd46dd345 |

原裁决JSON原字节SHA c90a73efbe4c4282fd18c47d279fe13c0ec03ada3716b03743a0f3cbba95feb5，
旧10例seal SHA76e9a70b808ce297d7d57c8f226a26daaa72f1f932de15f0c39467c582575f30均未改。
当前audit仍运行实际预算反例/旧transport拒绝，只有历史源码摘要从这些固定归档核验，
不能将今天600实现摘要写入旧裁决。其余未变化的源码仍现场重算；归档或原JSON变化拒绝。
