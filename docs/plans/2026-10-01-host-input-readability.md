# 续批停止：宿主派发不可读

日期：2026-10-01。此文记录来源故障和预检修补，不改变模型、high、1.5.5、产品标准或原15资格。

## 结果与费用

执行前提交8ac9cab1a2acc29d4f628d4b6574fb3169d57110，CI36735390662三项成功；
pytest5462通过/163跳过/129子测试，耗时43:04。一次监控EOF不是CI失败。
执行冻结435affe0828827d56e84f2c811567aca84fa16d530f30c8473d4859db9fdffa2，
运行目录data/runs/role_task_observation/boundary-examples-independent-v2-continuation-20260930。

claim-scope:4仅完成GLM初评78/needs_revision，正确指出辅助局抬高视野和早期死亡均值，
故“每一个指标均值都被拉低”错误。一次完整调用，输入12243、输出7216，总19459tokens；
无未知用量，未缓存估价0.299992元，非账单。未Flash编辑、未全新终评、未正式提交独立审查。
原15仍1/15；本批0新增完整资格，生产未准入。v2父子合计2调用35034tokens/0.491412元。

停止证据在data/evaluation/results/golden_boundary_examples_independent_v2_continuation_host_failure_20261001.json，
文件SHA256为d080f9e5ecfb9927a00aa1d4e94478f6dc04b4dfaa02366d0bd69b01898e1660。
32份原件逐一核验；公开投影不含私有推理，不替代原始响应。executor_result_available=false、
qualified=false、strict_completed_cases=[]。停止的是PID95496的原等待进程，没有伪造result.json。
父封存984d66ca597de2d655bbed62504b9e25dbb8ef02c39ac04143011c34cf61dc61保持只读。

## 首次偏离及排除

1. 摘要错将冻结主体映射为/root/coarse_live_reviewer。原生thread.source确认真正主体是
   /root/recovery_patch_check，线程01a0f093-d441-7fe2-9c68-99187920339c。错派意见未导入。
2. 正确主体收到实际任务并完成审查。turn为01a0f318-a370-7080-83dd-543b64e29b1c，
   dispatch为amsg_01a0f318-a38d-7431-84ac-419ed1eabdc7；final可读且绑定字段正确。
3. 该派发只有路由头明文，正文在encrypted_content。父工具参数同样密文。
   thread/turns/list(itemsView=full)、thread/read(includeTurns=true)、Codex read_thread
   均没有派发明文。正式取证拒绝codex_review_host_rollout_dispatch_encrypted。
4. 因此换回正确别名没有解除阻断；不是GLM本例检错失败，也不是402/429、预算耗尽或自然退出。
   final和本地task不能替代合同要求的原生派发。未解密、修改宿主日志或追认已停批。

## 修补及验证范围

scripts/codex_review_event_source.py复用原生路径/主体校验，新增check_latest_input。
只检查最新一个已完成turn；缺失、重复、错主体、密文或未完成即拒绝，不搜索旧成功事件。
可读性探针支持普通工程任务文本；正式fetch仍要求六字段绑定和真实独立final。
scripts/run_boundary_examples_v2.py的verify_native_principals在核对身份后调用该检查，
原续批入口复用，因此两入口在凭据加载、目录创建和Provider请求之前发现此类已知故障。
返回的原生agent_path用于核对路由，不信任摘要别名。

相关三测试文件首次90通过1失败；失败为新增续批fixture漏experiment，补齐后该文件14通过，
最终覆盖91例通过，不能说一次91全绿。compileall、diff检查通过。独立补丁复核无阻断，
在fixture单字段修正前完成。真实只读预检拒绝当前密文：credentials_loaded=false、
provider_requests=0、run_created=false。这证明提前拦截有效，不证明宿主已恢复。
新补丁公共CI需按新提交另查，不能借执行前CI授予通过。

本机辅助证据位于C:/Users/33502/Documents/Agent/outputs/riftcoach-v2-preparation-2026-09-30：
continuation-review-routing-correction.json、continuation-execution/operator-stop.json、
host-preflight-real-result.json、host-preflight-tests.xml、host-preflight-continuation-tests.xml。
这些本机文件不是公共测试依赖；正式失败封存随提交保存。

## 恢复条件与方案边界

预检只能拦截当前不可读，不能保证下一次派发仍可读。现有读取渠道已没有满足合同的来源，
不能把此补丁说成“通路恢复”后再跑模型。下一项必须先证明真实宿主派发可读且与真实final
同源绑定，用离线/零GLM的真实往返检查；同时从原生source核对路由。成功后才考虑新批资格、
历史消费扣回及授权适用范围。当前固定续批入口不可重开，旧停止结果不可补签。

若宿主继续只提供密文，应先比较可提供真实完整派发证据的受支持宿主入口，或提出替代证据
合同，列出独立性、不可替换绑定、恢复/封存语义及兼容影响，再作决定。不能把主Agent自写
task文件、独立final自述或可读性布尔值直接作为派发证明，也不创建另一套协议绕过现门。

整体顺序保留：完整原15→自然Coach生成/工具/纠错→当前组合真实Worker/DB/API/Workbench。
四块联动、个人Training、前端审美/必要重做/英雄头像、Memory、身份运维、两树整合、学习
沿活动计划与既有需求追踪推进；本包工程修补不计为这些产品目标完成。
