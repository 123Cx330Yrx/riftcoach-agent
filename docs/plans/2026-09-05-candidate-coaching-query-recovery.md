# Candidate Coaching Query Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复候选自然语言查询与本地教练检索的衔接，并保留无正文诊断，不降低证据门。

**Architecture:** 一个显式 KnowledgeProvider 包装器，原查询优先、精确教练别名最多补查一次。
共享领域执行器默认关闭；新策略以固定版本和脱敏计数投影，旧领域入口拒绝新行为。

**Tech Stack:** 现有 Python / Pydantic / pytest / LocalHybridKnowledgeProvider，无新依赖。

---

### Task 1：先复现查询和安全边界

**Files:** Create `tests/test_coaching_query_recovery.py`；Create `app/rag/coaching_query.py`。

- [ ] 测试“复盘”原路径零命中、新路径可返回真实来源；双语别名、未知/恶意字符串、过滤、
  冲突、已有命中、异常、最多两次本地检索和严格计数诊断。
- [ ] 运行新测试，确认红灯；实现最小包装器后转绿，原支持阈值保持不变。
- [ ] 不把整个案例上下文或预期答案加入查询，不额外调用模型。

### Task 2：显式接线与完整离线链路

**Files:** Modify `app/evaluation/provider_domain_production.py`、`app/evaluation/domain_e2e.py`；
Test `tests/test_provider_domain_production.py`、`tests/test_domain_e2e_evaluation.py`。

- [ ] 新增默认 false 的 retrieval_hardening；要求候选请求策略+质量加固。
- [ ] 候选上下文加入通用查询指南，知识库外层包装原检索器；原有工具输入/输出合同不变。
- [ ] EvidenceDiagnostics 增加默认省略的严格检索计数；额外自由文本字段必须拒绝。
- [ ] 独立开发 Fake Provider 验证三次模型调用内检索来源→引用→评分→发布，以及仍无证据拒绝。

### Task 3：版本隔离与收口

**Files:** Modify `app/evaluation/glm53_hardened_domain_gate.py`、
`app/evaluation/glm53_hardened_domain_v3_gate.py` 及相应测试；更新 canonical/活动计划/路线/学习。

- [ ] 旧 V2/V3 在任何 Provider 调用前拒绝显式开启新检索策略的执行器。
- [ ] 运行新查询、领域执行器、RAG、旧回执、V2/V3、上下文与预算的比例回归。
- [ ] compileall、diff check、governance，通过后提交推送并核验公共 CI；真实 Provider calls=0。

## Runbook / limits

聚焦：`.\.venv\Scripts\python.exe -m pytest tests/test_coaching_query_recovery.py tests/test_provider_domain_production.py -q`。
诊断只允许固定枚举/数字/过滤键名，禁止 query/filters 的值、正文、提示词、推理和凭据。
旧真实回执保持不可变，开发结果不等于新鲜领域准入；未知复杂查询仍可能不命中，下一版本必须
验证真实交互，而不能用本地测试数冒充生产成熟度。
