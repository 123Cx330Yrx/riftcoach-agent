# Host dispatch CI portability repair (pre-migration record)

Closed update: the user explicitly confirmed rebinding to `1039fb50` / CI `38258297688`; all jobs passed, the authorized fast-forward preserved source/package bytes, and the same batch ran without extending its expiry. See [closed results](2026-10-12-relation-initial-result.md). The remainder is the original pre-migration snapshot.

The four-request relation comparison remains unexecuted. Its frozen HEAD is
`549220ab1b8c7a4edcd93dd74ab6c366c9c2a733`, with CI `38254464870` and plan
`8b93463e04a5d4321727ba06188914047d12215d097a12fc0091eabb2e3d0dda`.
The user authorized that bounded comparison; this repair does not expand it.

## Failure and repair

Linux job `114828831807` failed in
`test_author_file_through_submit_next_request_and_strict_seal[None]` because
`assert 'python -m ' not in text` rejects the valid absolute interpreter
`/opt/hostedtoolcache/Python/3.11.17/x64/bin/python -m ...`.
The job reported 1 failed, 846 passed and 13 skipped. The same assertion also
occurs in `test_document_full_report_remaining_initial.py`.

Both tests now check every module command's prefix against the exact absolute
interpreter, including shell quoting and the expected command count. The
regression covers the observed Linux path, paths containing spaces, Windows,
and rejection of bare, relative, wrong, prefixed or missing commands. Production
code, prepared requests and historical evidence are unchanged.

The repair is isolated at `D:/riftcoach-agent-ci-portability-20261012`, branch
`codex/host-dispatch-ci-portability`. The original checkout remains frozen.
The new checkout initially converted unpinned text to CRLF, causing dataset
hash rejection before the affected assertions. Only pristine files whose bytes
equaled their Git blobs after CRLF-to-LF conversion were restored to exact blob
bytes; no expected digest or dataset content was changed. Git commands for this
repair use `-c core.autocrlf=false`.

## Execution boundary and next action

The sole pre-execution waiter PID 22200 was stopped after identifying the CI
failure. Operator records are in
`C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-initial-20261012`,
including `authorization.json`, `ci-shard0.log` and `waiter-operator-stop.json`.
There is no business run or execution directory and no Provider/HTTP request,
business submission or new qualification. Automation remains PAUSED.

The original authorization binds the original HEAD/CI. A repaired HEAD and its
green CI must be explicitly rebound before the first paid run; the original
authorization must not be overwritten or silently extended. Its expiry remains
2026-10-13T13:18:08.784319Z. Keep the four-request scope, plan, cost and no-retry
rules unchanged; do not restart the old waiter or purchase a new batch.

Validation results and byte comparisons are recorded in
`data/evaluation/results/host_dispatch_ci_portability_20261012.json`. Public CI
must be checked for the actual repair HEAD; local checks are not public CI or
model quality evidence. This infrastructure repair does not settle candidate
semantics, formal same-version 15, natural consumption or the remaining stage 8E
and product dependencies.
