# 8E 学习记录：GLM-5.3 Flash 加固领域 V2 资产（RQ-229）

## 1. 问题与原则

RQ-227 的三道题已经被真实执行过，第二题还直接促成了 RQ-228 的修复。修复后若继续用同一题
重考，得到的提升无法区分是“系统真正泛化”还是“针对旧题优化”。因此新的验证必须同时做到：
题目和数据未被消费、规则先冻结、执行前能证明实际启用了加固合同。

底层原则叫评测污染隔离：测试资产一旦用于调试或修复，就不再是独立验证集。另一个原则是
fail closed：任何身份、预算或安全策略对不上，都在 Provider 创建前停止，而不是边运行边猜。

## 2. 设计与实现

RQ-229 采用一套独立 V2：协议计划固定候选模型、低思考/4096、调用与 token 墙、零重试/修订、
至少一个来源和首个不安全失败即停；Dataset 保存判定要求；Input Plan 保存实际问题和 fixture
身份；Prompt/Context Snapshot 只保存摘要，并明确包含 RQ-228 的可信候选 policy 附录。

`admit_hardened_domain_assets()` 只读这六个文件并重新计算所有关键身份。它不读取 Key、不构造
Provider、不发送网络请求，也不创建真实结果回执。

## 3. 代码地图

- `app/evaluation/glm53_hardened_domain_assets.py`：V2 协议模型与 no-I/O 交叉准入器。
- `app/evaluation/prompt_context_identity.py`：多案例快照新增默认关闭的 `policy_addendum` 输入。
- `data/evaluation/glm53_flash_hardened_domain_protocol_v2.json`：冻结资源与安全规则。
- `data/evaluation/glm53_flash_hardened_domain_heldout_v2.json`：全新三案例判定合同。
- `data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json`：问题、运行 ID、fixture 和上下文承诺。
- `data/evaluation/contracts/glm53_flash_hardened_context_v2.json`：不含正文的上下文摘要。
- `examples/fixtures/*glm53_flash_hardened_v2*`：新的匿名合成对局数据和确定性报告。
- `tests/test_glm53_hardened_domain_assets.py`：身份、冻结确认、历史 marker 隔离与质量版本漂移测试。

## 4. 数据与控制流

```text
V2 protocol + Dataset + Input Plan + Snapshot + 两个 fixture
                          ↓
                 no-I/O admission
                          ↓
  角色/版本 → 历史隔离 → 预算 → 来源门 → policy 摘要
                          ↓
       用当前 Skill + fixture + 三题重新构建 Snapshot
                          ↓
             完全一致才返回公开安全 SHA
```

以后若获授权执行真实观察，运行器只能消费这次准入的身份；准入本身没有这项授权。

## 5. 验证

先写测试并观察到新模块不存在的预期失败；实现后聚焦测试通过。测试还证明：默认 snapshot
不含候选 policy，只有显式传入时才增加可信策略区并改变身份；协议质量版本一旦漂移会被模型拒绝；
新 marker 与包含 RQ-227 在内的历史集合没有交集。新增与相邻回归共 `123 passed`；
no-I/O 准入、compileall、`git diff --check` 和治理检查均通过。

## 6. 运行手册

离线检查只需在仓库根目录调用 `admit_hardened_domain_assets(project_root=..., confirm_rules_frozen=True)`；
成功对象的 `external_provider_calls` 必须恒为 0。若失败，先根据错误定位是文件路径、fixture SHA、
Dataset/Plan/Snapshot 身份、Context 重建、历史污染还是加固/预算合同漂移，不得跳过校验直接运行。

## 7. 失败、安全与边界

Snapshot 不保存用户问题、知识注入正文、报告正文、reasoning、工具参数或凭据；marker 在准入对象中
只保存 SHA。新资产没有删除或覆盖 RQ-227，旧失败事实保持不变。离线通过不说明 GLM-5.3 Flash
已经回答正确，也不注册候选、不改变默认 Runtime，不移除 GLM-5.2 手动应急/兼容路径。
Portal、Account、Workbench、Auth、路由和 `production_media=0` 均未改变。

## 8. 面试表达

> 修复一次 held-out 失败后，我没有原题重考，而是建立了全新的版本化题目、数据和上下文快照。
> 一个零网络准入器在调用模型前交叉验证历史污染、资源墙、证据来源下限和安全策略摘要；只有全部
> 身份一致才允许进入下一阶段，从而把“考卷可用”和“模型通过”清楚分开。
