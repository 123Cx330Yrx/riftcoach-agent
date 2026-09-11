# ADR-0101: User-authored notes for observed players

Status: Accepted for the bounded observation-note slice, 2026-09-11.

Problem: the archive workbench can display ShowMaker but loses a viewer's notes.
Existing Review Memory already stores observation_note under an owner-player
relationship, but its public structured-input gate rejects this use case.

Decision: reuse Conversation → Memory Candidate → user accept → Review Memory
and the existing owner-scoped review-memory GET. Admit only observed/append/
observation_note for structured user input, with a distinct gate-policy version.
Do not add a table, generic archive upload endpoint, or another persistence stack.
The save button expresses the user's write intent and performs candidate creation
and acceptance. A retry retains operation identity and any returned candidate ID.

An optional user_attached_archive reference carries source_run_id, bundle digest,
report SHA and original observation time. These are user-attached metadata, not
server-verified task provenance. No source_task_id or authenticated run binding is
invented. Old text-only notes remain valid; the 4 KiB typed payload limit remains.

The browser connects only on explicit action, selects an existing matching observed
profile from the authenticated owner's list, and reads notes back. Importing an
archive alone remains local and performs no API calls. No Riot self account is
required. Creating a missing observed profile remains the existing Account flow.

Training, model-generated memory gates and non-observation keys remain unchanged.
The archive report itself stays in the local file; this slice persists user notes,
not report publication, exercise completion, or the entire golden-slice pipeline.

Verification: gate/payload counterexamples, API owner isolation and readback tests
with real PostgreSQL, existing session/CSRF enforcement tests, browser CSRF header
and save/reload/filter/failure tests, and existing regressions.
No external Provider/Riot/OP.GG calls are necessary. Workbench redesign remains
deferred per the four-surface design follow-up.

## Engineering and learning evidence

Code map: memory/gate.py admits the narrow user-observation case;
memory/typed_models.py validates the optional archive reference while preserving
old payload fingerprints. Existing materializers and owner-scoped query services
write/read review_memories. ObservationNotesApi handles existing API contracts;
ObservationNotes implements explicit connect, save, retained retry and readback.
No new database migration or dependency is needed.

Runbook: import an observation JSON at /?view=observation; connect an authenticated
RiftCoach session with a matching observed profile (use the Account page if absent);
write a note and save. Reload, import the same archive, connect and read it again.
An uncertain response keeps the operation on the current page. Reconnect refreshes
the session before retry. Closing the page loses the pending retry identity; saved
notes remain server-side. Reads currently inspect at most 100 recent records.

Failure boundaries: an unavailable session/profile cannot write; owner isolation
is enforced server-side. An accept response lost after commit can be retried without
another candidate or memory row. The UI only claims success after readback. Archive
references are user assertions, not proof of a trusted run. Source identifiers on
the server candidate are not populated from these assertions. Text is rendered
inertly and payload size remains 4 KiB. No Training or source API writes occur.

Verification evidence: 47 focused backend/session tests passed; 280 frontend unit
tests passed; two browser scenarios passed, including uncertain acceptance retry,
reload, no-API local import and mobile overflow. Typecheck/build passed. The new
PostgreSQL round-trip test is explicitly included in the public database job.
Local execution failed connecting to the stopped database at localhost:54329;
this is not counted as a pass or silently skipped. Browser routes use fixtures;
this does not establish an actual user-owned ShowMaker record was written.

Interview wording: implemented owner-scoped observation notes by reusing a
candidate-confirmation-memory pipeline, and tested retry/readback contracts.
Do not claim the entire product or a deployed authenticated golden slice is done.
The parent learning checkpoint stays in progress; this ADR supplies the bounded
slice's design, flow, verification, operations and boundary evidence.
