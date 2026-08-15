# 5D-7 V2 预算可达性实现计划

## Task 1：先写失败测试

文件：

- `tests/test_provider_budget_reachability.py`

覆盖精确 V2 复读、下一调用不可达、三阶段 envelope、长度校准投影、证据漂移和敏感
字段边界。

## Task 2：实现最小合同与裁决器

文件：

- `app/evaluation/provider_budget_reachability.py`

实现严格 Pydantic 模型、请求 envelope 测量和 V2 专用裁决函数。模块不得接受 Provider、
API Key、网络客户端或原始 Prompt 输出字段。

## Task 3：聚焦验证并修正

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_budget_reachability.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_provider_adoption_control.py tests/test_provider_domain_production.py tests/test_deepseek_fresh_domain_assets.py -q
```

## Task 4：形成离线裁决与持久状态

记录精确结果与投影的不同证据等级，更新项目执行状态、路线历史、能力矩阵、需求和活跃
计划。不得创建或执行 V3。

## Task 5：全量门禁与公开同步

运行完整 pytest、compileall、RAG development/held-out、Harness 边界与 dry-run、治理、
`git diff --check`；随后提交、推送并核验 exact-SHA GitHub Actions。
