# RQ-220：Flash 响应档位—终态—恢复离线拆分计划/结果

## 目标

把 RQ-219 的 8192 超时拆成可独立归因的四个维度：请求思考档位、流终态、Usage 尾帧、
恢复策略。使用固定 fake/fixture，不消耗 Key、不联网、不改变产品默认。

## 实施范围

- 新增 `app/evaluation/glm53_flash_response_profile_split.py` 与离线 CLI；
- 复用候选流观察器和严格/候选响应策略，不复制 Provider 解码逻辑；
- 产出 9 个固定场景及 body-free、create-only 的 offline receipt；
- 新增聚焦测试，覆盖矩阵完整性、策略差异、激活阻断、错误分类、回执篡改和路径边界；
- 不修改 Portal、Account、Workbench、Auth、路由、产品 Runtime 或 `production_media`。

## 本地结果

9/9 场景通过：正常 stop 与 tool_calls 可交付；`length` 的 reasoning-only 形状在候选
策略下可识别但恢复被 activation gate 阻断；部分正文、缺/非法 Usage 和 elapsed timeout
均保持 fail-closed。聚焦集合为 `133 passed`，compileall、`git diff --check` 和治理
检查通过。矩阵 provider calls=0、network=false。

## 退出条件与下一步

实现提交 `14254048f6ad2faea5c7b15801e5c7c11e0ceba4` 的 Actions `33738050233`，以及回执提交
`ebb09a525b3340f31ba71821b894b4a142dfb4e7` 的 Actions `33738673832` 均三 job
exact-SHA `completed/success`。回执为 `6209` bytes、SHA-256=`32965cbe06fc122c8ed436dbab0e4100fdf9b6f51510e2a69849b3cc4c2c8f8a`。
当前状态为
`8e-productization / candidate-explicit-zhipu-neutral-stream-adapter-seam / response-profile-terminal-recovery-offline-split / completed-public / pending-next-decision`。
公共闭环只关闭本地实现的可复现性；下一步再决定是否建立新的真实候选域门，不得因为离线矩阵通过而注册候选或切换默认模型。
