# ADR-0002：选择性参考 EchoMind 与 AGI-Saber

- 状态：接受
- 日期：2026-07-16

## 背景

EchoMind 更接近垂直应用所需的用户、会话、工具、Memory 和评测结构；AGI-Saber 更擅长通用 Planner、DAG、复杂检索和运行时控制。

## 决策

- 阶段 3 和阶段 6 优先参考 EchoMind 的 Tool、Session、Memory、Monitor 与 Evaluation；
- 阶段 4 参考 AGI-Saber 的父子块、混合检索和重排思想；
- 阶段 8 才正式引入 AGI-Saber 式 DAG、并行、取消、快照和恢复；
- 不复制完整运行时，不引入与实际需求无关的重型基础设施。

## 影响

项目能够获得两类架构的优点，同时避免提前承担 PostgreSQL、Elasticsearch、Milvus、Neo4j 和 Kafka 的完整运维成本。
