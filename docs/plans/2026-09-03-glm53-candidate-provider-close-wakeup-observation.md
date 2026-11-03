# GLM-5.3 Candidate Provider Close/Wakeup Observation Implementation Plan

> 本计划是 RiftCoach 的候选验证记录，不是外部代理或工具的执行指令。按本仓库的 Code 工作流逐项实施；任何真实请求都必须等实现提交取得 exact-SHA 公共 CI 通过并获得用户明确授权。

**Goal:** Run one bounded, candidate-only observation that measures whether the explicit Zhipu session's cancel/close returns and wakes a pending `next()` without persisting provider body data.

**Architecture:** A parent runner owns the hard process boundary and writes an immutable body-free observation receipt. A short-lived child opens exactly one explicit `ZhipuStreamSession`, records only allow-listed event categories, starts a reader for a potentially pending `next()`, and reports cancel/reader timing. The observation defines a finite grace window after `cancel()` returns; `reader_woke=false` means only that the reader did not finish within that window, not that the provider definitively failed to wake. If the child exceeds the parent deadline, the parent terminates and reaps that child and records `child_timeout`; no thread is force-killed in-process and no raw SDK response is exposed.

**Tech Stack:** Python 3.13, existing `ZhipuStreamAdapter`/`ZhipuStreamSession`, standard-library `subprocess`/`threading`/`json`, pytest, existing ordinary Zhipu API configuration loader.

---

### Task 1: Freeze the body-free observation contract

**Files:**
- Create: `app/evaluation/candidate_provider_close_wakeup_observation.py`
- Test: `tests/test_candidate_provider_close_wakeup_observation.py`
- Modify: `app/evaluation/__init__.py` only if an explicit export is required (prefer no export)

**Step 1: Write the failing tests**

Cover schema validation and allow-list behavior before any provider client is constructed:

- valid `not_pending`, `pending_cancel_returned`, `pending_cancel_timeout`, and `child_timeout` projections;
- reject body text, exception text, headers, raw request IDs, negative durations, invalid state codes, and extra keys;
- prove `repr()` and `as_dict()` contain only safe categories, booleans, bounded integers, and timing values;
- prove an immutable output path cannot be overwritten.

**Step 2: Run the focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_candidate_provider_close_wakeup_observation.py -q`

Expected: FAIL because the observation value objects and writer do not exist.

**Step 3: Implement the minimal contract**

Define frozen/slots value objects with an explicit schema version (separate from RQ-209 v2), safe state literals, bounded millisecond fields, call count, child exit/termination flags, session close-report projection, and a canonical JSON writer that refuses an existing path. Keep all provider payload and exception text out of the object graph.

**Step 4: Re-run the focused tests**

Run the same command; expected: PASS.

### Task 2: Add an isolated child probe and deterministic fake seams

**Files:**
- Modify: `app/evaluation/candidate_provider_close_wakeup_observation.py`
- Test: `tests/test_candidate_provider_close_wakeup_observation.py`

**Step 1: Write failing fake-seam tests**

Use injected client/provider/session factories to prove:

- exactly one `stream_session(..., include_usage_tail=True)` open;
- event summaries never retain content/reasoning/tool arguments;
- a reader that is pending when `cancel()` returns is classified as `reader_woke=false`;
- a fake whose cancel wakes its reader is classified as `reader_woke=true`;
- cancel exceptions map to a safe code and still attempt `close_report` capture;
- no second request, retry, recovery, or product Provider call is possible.

**Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_candidate_provider_close_wakeup_observation.py -q`

Expected: FAIL on the missing child-probe orchestration.

**Step 3: Implement the child probe**

Use a reader thread only inside the child. Emit one flushed `probe_started` marker before the potentially blocking operation, then return a final line containing only safe event categories (`reasoning_seen`, `content_seen`, `terminal_seen`, `usage_seen`, `tool_seen`), elapsed milliseconds, cancel return status, reader wake status, and `ZhipuStreamCloseReport.as_dict()`. The post-cancel reader result is sampled only during the finite grace window defined by the contract. Never access or serialize `raw_stream.response`; the report names only the outer SDK wrapper. Keep the explicit candidate profile and `max_retries=0` checks. Bound and discard child stderr; provider exception text, headers, request IDs, and response bodies must never reach the receipt.

**Step 4: Re-run the fake tests**

Run the same command; expected: PASS.

### Task 3: Add the parent hard process boundary and CLI

**Files:**
- Modify: `app/evaluation/candidate_provider_close_wakeup_observation.py`
- Create: `scripts/diagnose_glm53_flash_candidate_close_wakeup.py`
- Test: `tests/test_candidate_provider_close_wakeup_observation.py`

**Step 1: Write failing parent tests**

Verify the parent kills a child that never reports completion within the hard process deadline, writes a safe `child_timeout` receipt, refuses to overwrite an existing receipt, requires an explicit confirmation flag, and rejects endpoint/model mismatches before constructing a client.

**Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_candidate_provider_close_wakeup_observation.py -q`

Expected: FAIL on the parent runner/CLI.

**Step 3: Implement the parent runner**

Launch the child with `subprocess.Popen`, capture only bounded stdout/stderr, wait no longer than the configured process deadline, terminate and reap it on timeout, and write one canonical body-free receipt. On Windows, keep the child as the only spawned process and close/reap its pipes after termination; do not expose unbounded SDK output. Require `--confirm-real-call` before loading the dotenv file or creating a client. Keep the default probe to one primary call, no retry/recovery, and a bounded process deadline shorter than the transport timeout.

**Step 4: Run the parent tests**

Run the same command; expected: PASS.

### Task 4: Local verification and public closure

**Files:**
- No additional product files; update RQ-211 records only after verification.

**Step 1: Run proportional local checks**

Run:

```text
.venv\Scripts\python.exe -m pytest tests/test_candidate_provider_close_wakeup_observation.py tests/test_zhipu_stream_adapter.py tests/test_candidate_stream_deadline.py tests/test_candidate_recovery_diagnostic_v2.py tests/test_candidate_recovery_diagnostic_real.py -q
.venv\Scripts\python.exe -m compileall -q app tests scripts
python scripts/check_project_governance.py
git diff --check
```

Expected: all focused tests pass, compilation/governance/diff checks pass, and no real API is used during this task.

**Step 2: Commit and obtain exact-SHA public CI**

Commit only the new candidate observation files/tests/docs, push the isolated branch, and wait for the three required jobs to finish with `head_sha` equal to the implementation commit. Do not run the real probe before this closure.

**Step 3: Run exactly one authorized real probe**

After exact-SHA CI, run the CLI once with `--confirm-real-call`, the ordinary API endpoint, the frozen candidate input, and an immutable new receipt path. Stop at the process deadline; do not retry or launch recovery. Record only the resulting body-free receipt SHA and whether cancel returned and the pending reader woke.

**Step 4: Update durable state and stop**

Append RQ-211, update the single canonical next action, and explicitly preserve the boundary: candidate remains disabled/unregistered, `capabilities.streaming=False`, strict Flash v1 remains 2048/zero extra calls, and no product Runtime/Workbench/Portal/Account/Auth/routing or `production_media` changes.
