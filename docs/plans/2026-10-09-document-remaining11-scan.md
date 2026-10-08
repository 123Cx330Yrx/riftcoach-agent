# 剩余十一例集中初评扫描：实现与执行边界

用户要求把诊断提速落地，并推进到下一次完整十五例验证的准备位置。本包完成独立初评
扫描工程准备；还没有修好第四例语义分歧，也不能宣称下一次完整十五例已具有质量依据。
新Provider调用0，旧批关闭、自动接续保持暂停。

## 为什么只测十一例

上一批封存`d225f75e39e850e62c7af2cefab1ec823d837e6c46fd65606e93da373d2ed4c5`
已有前三例整链与第四例真实初评/审查分歧。新批仅购买未执行的十一例，不重复这些观察。
原15业务identity、原input/report、schema/catalog与完整initial request逐项等于旧冻结；
六十九项执行/验证依赖另行冻结。诊断历史分开显示，不拼成同期通过率或资格。

顺序：scope:4、scope:3、claim-scope:2、claim-scope:5、claim-scope:6、claim-scope:7、
observed:1至5。原15正确控制及明确真错控制原样保留；期望标签不发给Provider，Host仍
按完整上下文核所有issues、解释、修法、来源及advisories，不机械比较段号集合。

## 数据与停止路径

`run_document_review_scan.py`复用旧document route、真实role transport、预算和native
双审。每例独立transport目录、序号1；全批仍共用一个calls/tokens/unknown reservation
预算对象和Host clock。旧传输器单任务最大九序号、旧资格首失败停止均保持。

语义拒绝、真实双审分歧、错误verdict/score记入各例失败集合，再发下一独立初评。
任何协议/来源/身份/native/transport/预算/可用性异常立即关闭；无重试、编辑、fresh、
重评、批次重开或资格注册。`scan_completed`与`diagnostic_accepted`分开，失败集合不能
因为整批走完而被涂成通过。调用前仍要求本提交公共CI全绿、clean exact HEAD和真实
主体预检；关闭result和Host提交共用OS lock、create-only与atomic publication。

`document_review_scan_handoff.py`实际重建source、完整stage与原始transport request/
response，精确绑定task及真实作者final。主审notes和独立native事件分别输入；不代写
独立意见。`report_assessment=null`只认证初评质量，不认证带错原稿已修好。

预算后的实际`issued-request.json`在进入transport前落盘。route/role/native identity
前置失败若没有transport receipt，明确记`local_pre_transport_attempt_only`及未知用量，
不是伪造receipt或认定免费。已知/未知、未审尾部和未执行案例分别记录。

`seal_document_review_scan.py`只读重放真实回执、各阶段和native事件，再白名单公开。
硬失败尾部的dispatch绑定重建；未验证Host材料不公开JSON，只保留路径与原件摘要。
所有原件留存摘要，stream/private reasoning/凭据不在公开内容；已有关闭文件不能覆盖。
原件腐损导致严格读回失败时不能伪称验证成功；保持原件，调查并记录未证范围。

## 实际验证与复核

- 新入口21项离线行为检查通过：十一例完整receipt/handoff/关闭回放、语义拒绝后继续、
  错verdict收集、协议/身份/不可用/传输/预算立即停、未知用量、零发送失败、缺receipt
  本地尝试、晚提交、篡改拒绝及未验证Host内容不公开。
- 相邻旧document/scope diagnostic入口30项通过，旧语义首失败停止保持；旧业务源码未改。
- 独立真实代码复核发现并修复pre-transport封账与pending Host公开问题，末次无阻断。
- 当前真实主体预检通过，沿`native-final-attestation-v1`；不保证未来可用性，每阶段仍需
  当时真实final与取证。替身测试和CI不构成新模型语义证据。

## 冻结与预算

准备文件：`data/evaluation/results/golden_document_remaining11_scan_preparation_20261009.json`。
方案SHA：`d5aa7c914cb9b30d66422a28c83736afc1cc79313fc32be2d4feced1b73429bf`。
新增最多11次GLM-5.3/high，Flash0；1064448tokens、3300活动秒、86400Host秒；
每请求最大64000input ceiling、32768output、300秒。保守未缓存估价15.724544元，
不是实际账单保证。原授权已关闭，不借其余量；需要本方案具体新增付费授权。

准备器和执行器：`python -m scripts.run_document_review_scan`。执行时显式提供本准备文件、
完整plan SHA、同提交CI run、真实root/independent IDs、env-file及codex-executable。
先不带`--execute`精确重建；执行只允许首次创建对应run。待审用
`python -m scripts.document_review_scan_handoff task --key KEY`，读取完整材料并真双审后
用`submit --key KEY --notes PRIMARY_JSON --event-id NATIVE_EVENT --codex-executable PATH`。
结束用`python -m scripts.seal_document_review_scan --codex-executable PATH`只读回放；
确认后加`--output PUBLIC_JSON`create-only封存。自动任务不能在未获新授权时发送。

## 结果怎样改变下一步

收到十一例质量观察后，和分开保留的旧四例一起归类实际主张/范围/方向/量级/建议分流，
集中修复共同机制；复核原反例、正确对照、明确真错及混合样本。若不能选出有效修法，
就不原样重跑完整15，也不继续堆近义提示、额外重评或人工删issue。

只有修法与失败集合回归提供充分依据后，才冻结一份新版本完整15；保留原初评→必要
编辑→fresh、真实全文双审、预算及首失败停止，不导入扫描通过数。历史严格2/15、
新文档旧批3/15各自保留，完整review-controls、自然产品消费和8E仍未完成。
自然Coach/四块联动、本人Training、Worker/DB/API/UI/journal、前端审美/必要重做/头像、
Memory、身份运维、两树整合及学习继续沿活动计划依赖。
