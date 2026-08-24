# 8E Timeline DTO/UI 实施计划

1. 先为 `RunQueryService.get_timeline()` 写红灯：真实事件排序/phase、partial/unavailable、安全错误码、
   bounds 和 Artifact 篡改 fail-closed。
2. 为 FastAPI route 写红灯：latest link、owner scope、task terminal/publication gate、identity mismatch 和
   body-free errors。
3. 实现 strict Pydantic view、verified projection、composition proxy 与 HTTP response。
4. 为 TypeScript wire/decoder/adapter/controller 写红灯：exact keys、run binding、terminal load、generation/
   abort 不变。
5. 实现 Timeline panel、真实几何 marker、可见事件列表、partial/unavailable、keyboard、responsive 与
   reduced-motion。
6. 扩展 fake live server/fixture，任何合成内容继续由现有 fixture disclosure 明示。
7. 运行 focused Python/frontend、全量回归、typecheck/build、Playwright/axe/overflow/visual QA、PostgreSQL、
   package、RAG/Harness/security/governance；记录八维证据。
8. 创建独立 implementation/evidence commit，push，并等待同一 SHA 的 `pytest`、
   `postgres-migrations`、`packaging-smoke` 全绿后才进入下一产品模块。

本批不调用 Riot/OP.GG/Provider/LLM，不演进上游 Summary producer，不实现连续曲线、Evidence/Trace 深页、
Training full page、OP.GG breadth/golden slice 或 8F。
