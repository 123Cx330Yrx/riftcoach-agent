# 六次候选的Worker、数据库与用量消费验证

2026-10-15。7个真实Postgres/Worker/FastAPI场景通过（26.69秒），模型与Riot来源为替身。
本次补齐当前1.6.0组合的工程证据；未发现需要修改生产代码的缺陷，不作模型质量或自然消费验收。

## 用户可见行为与实际路径

停止任务不抹掉停止前的消耗；未认证完成不允许阅读正文。之前的数据库回归用旧五次
correction-scope应用，不能证明六次候选实际接线也保持这两个边界。

新测试`tests/test_natural_duty_worker_postgres.py`走真实入口：API入队 → Postgres领取 →
ReviewWorker → RecentReviewTaskExecutor → build_natural_duty_candidate → AgentLoop/本地RAG/
共享预算/补丁与fresh → Trace及receipt → SQL终态 → owner用量API。Provider提供固定响应，
网络限制为loopback。候选已内置DispatchAwareRuntime，无需旧with_dispatch_trace适配器。

| 场景 | 调用数 | SQL终态 | 发布与用量 |
|---|---:|---|---|
| 双初审通过 | 4 | succeeded | publication=rejected；用量可见、正文409 |
| 补丁应用及双fresh通过 | 6 | succeeded | 内部unqualified；用量可见、正文409 |
| owner在第1/4/5次响应后取消 | 1/4/5 | cancelled | 下一发送被拦；已知tokens完整保留 |
| owner在第6次响应后取消 | 6 | cancelled | 本地可有completed/rejected凭据；SQL继续拦正文 |
| 外人在第4次响应后请求取消 | 6 | succeeded | 取消404，正常流程继续，仍未认证且不发布 |

每次替身响应已知输入/输出各10tokens；实际Trace和HTTP白名单投影保持对应次数，不增添
尚未发送调用，不误填未知或0。所有场景外人读取任务、用量和正文均404；本地无final_report，
终态不再领取，重复取消不增加事件。`succeeded`只表示执行终态，与报告获得资格是两层含义。

测试已加入`.github/workflows/tests.yml`的Postgres job，公共测试使用提交内资料；普通pytest
没有独立测试库配置时会跳过，不能把skip当数据库通过。本次本地7项均实际执行，无skip。
FastAPI/Starlette现有httpx弃用提示不影响结果，未为此修改无关依赖。

## 本机Docker恢复及复现

本次启动失败首先发生在`Docker/run/sailor-ingest.sock`，然后在
`docker-secrets-engine/engine.sock`：Windows无法把残留socket重命名为`.stale`，引擎未创建。
仅重建其中一个目录后，失败会在另一目录出现；失败启动还留下新socket。因此最终在官方
`docker desktop stop --force --timeout 30`且进程退出后，同时备份并重建两个运行目录。
恢复后Docker服务端29.7.2可用。没有重置Docker、删除镜像/业务卷、改网络或升级安装。
这是已验证的本次恢复；不能保证上游socket残留问题永久消失。

原容器`ebffdb0a8f3e`按原配置启动，原卷`riftcoach-agent-rq192-pr_riftcoach-postgres-data`
保持，映射仍为127.0.0.1:15432；health=healthy，容器内SELECT1及迁移
`0014_message_projection_status`通过。详细本机恢复与备份路径保存在
`C:/Users/33502/Documents/Agent/outputs/riftcoach-docker-recovery-20261015/`。

测试另建`riftcoach-natural-duty-test-20261015`、postgres:17-alpine，独立数据库映射
127.0.0.1:10803，使用本次专属标签和`--rm`。测试前核标签和端口，未指向产品库；
结束后再次核标签并stop，自动删除已确认，原产品库仍healthy。

仅对新建可丢弃数据库设置`RIFTCOACH_TEST_DATABASE_URL`后运行：

```text
python -m pytest tests/test_natural_duty_worker_postgres.py -q --tb=short --show-capture=no
```

该fixture会downgrade/upgrade自己的测试schema；现有产品库不能作为测试库。
结果见`data/evaluation/results/natural_duty_worker_postgres_20261015.json`。

## 剩余边界

没有默认Worker/API候选注册、真实模型请求、新资格、部署或Owner理解验收。
原稿保留提案已零调用关闭；本项工程通过不能补足其材料前提或自动语义质量。
下一步核本提交公共CI；仍须按原标准完成同版本15、自然Coach/Training、四块联动/journal、
前端审美头像、Memory、身份运维、两树整合、独立评估与学习，automation保持PAUSED。
