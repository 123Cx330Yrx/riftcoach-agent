# 切回系统代理后的三稿初评后续方案

## 问题与选择

主线仍是正确全文概括不误报、真实范围错误和伪造来源能检出。
前批在首项TCP建连时停止，没有任何模型输出；不能据此改变教学、温度、来源或评审时限。
用户切回系统代理后，DNS从TUN地址变为公网地址，路由改走WLAN，单次TCP/TLS成功。
这提供了改变连接路径后再观察的理由，不证明历史根因或模型API已可用。

本方案复用原三稿和现有执行器，仅添加独立run身份及固定失败/路由证据。
不重开旧批、不继承余量；原批unknown1、费用未知和原件全部保留。
不为API通不通另买空白模型探针：若获本具体范围授权，首次实际初评本身提供该证据；
若仍有transport硬失败，立即停整批，不自动重试。

## 固定范围

- 入口：`python -m scripts.document_full_report_network_followup`。
- 准备包：`data/evaluation/fixtures/document_full_report_network_followup_20261012`。
- 新run：`data/runs/model_comparison/document-full-report-network-followup-20261012`。
- Operator：`C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-network-followup-20261012`。
- plan SHA：`fb573b77b24b882ef917569781a7bb0c5d616cceb2a10c28da6eda4453758c6a`。
- 顺序：`report-V2:initial`、`report-H5:initial`、`report-S8:initial`，各一次。
- GLM-5.3/high、temperature1.0/top_p0.95，单次600秒、输出32768、SDK retries0。
- 最多3GLM、Flash0、290304 tokens、1800活动秒/86400 Host秒；保守估价
  **4.288512元**，不是实际账单或硬计费封顶。无编辑、fresh、重评、重试或新增资格。

报告、完整来源、policy、request和material与旧准备包逐字节一致；
16个校准逻辑段仍按现有解析器产生18个实际请求段号。预期标签和网络诊断证据
只留Host计划，不能进入Provider载荷或独立审查任务。

## 执行和判据

沿用[原三稿方案](2026-10-12-full-report-initial-diagnostic.md)的完整审查与收尾合同，
其中旧run/授权身份由本方案替换；新授权类型为`document-full-report-network-authorization-v1`。
必须覆盖本批范围与成本、绑定本plan和同HEAD全绿CI，clean exact HEAD、run不存在、
即时真实native预检通过后，唯一runner首次启动。准备包本身不是授权；旧授权不能用于新包。
授权最长24小时，不因故障延长。程序direct不保证绕过系统TUN，不自动改用户代理配置。

主审`01a1248f-e18c-7282-92bf-7ceb2eb5dce4`，复用独立`/root/host_scope_calibration`
（`01a12f0c-bb7c-74e3-ad92-775eefbe399a`）；不新建Agent。实际响应出现后，主审
从material完整读实际stage/报告/来源/policy/request/response；只向独立派精确dispatch
checkpoint路径/SHA，每stage一次NEW_TASK，同task恢复仅MESSAGE，不泄漏主审或预期标签。
独立恢复和final前重读同checkpoint，自己check-answer后唯一多行JSON原生final；主审实读
真实native事件后submit，必须event-id、checkpoint路径/SHA及指定Codex0.153.4读取程序。
三项均initial，report_assessment=null，不把原稿当修订稿；逐项核事实、范围、引用、解释、
修法与保留内容，不能将泛指强补全称或把措辞偏好升级为事实错。

有效语义拒绝记录后继续下一独立案；身份/来源/native/checkpoint/协议/transport/预算/
主体硬故障停整批，不补发未执行项。关闭后严格只读replay、create-only白名单seal，
核实际调用、HTTP、known/unknown/receiptless、未发和最早偏离；不修改原件或造回执。

三项意见和解释均正确才考虑更广同版本业务回归；若有误报/漏检或Host分歧，按实际命题与
完整来源决定修法。网络失败不算语义结果。熟悉来源开发组三项不是稳定率、盲测或正式15资格。
历史库存、旧strict seal缺口、正式同版本15、自然消费、8E及既有产品/前端/学习依赖保留。

## 准备证据

公开准备审计：`data/evaluation/results/document_full_report_network_preparation_20261012.json`。
最小入口复用旧builder/runner/transport/native门，不修改冻结旧源码。旧请求和材料一致性、
新身份/旧授权拒绝、证据篡改拒绝、包重建与原有离线执行/停止/封存验证一并检查。
准备阶段只读native预检通过；current_input_readable=false、current_route_and_final_available=true
如实保留，不保证将来可用，不替代执行前预检及实际唯一原生final。当前Provider0、业务submit0。

准备验证结果：18项相关离线检查通过（54.57秒）；三稿request/material字节一致，14+146旧原件及旧冻结源码SHA保持。准备审计SHA `dc875f75c9d0c10c580782267ab17d321ef53e2149403425e52855b130840428`。同HEAD公共CI在提交后确认，当前不启动。
