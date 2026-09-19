---
name: recent-form-review
description: Review a validated recent-match summary and deterministic report using attributable RiftCoach knowledge. Use for recent form, recent match trends, recurring weaknesses, or short training-priority requests.
---

# Recent Form Review

## Objective

Produce a grounded review of trends across multiple completed matches. Treat the supplied player summary and deterministic report as the only sources of player-specific facts.

## Workflow

1. Validate that the input contains Player Summary Schema v1.0 data.
2. Identify repeated patterns across the aggregate and match rows.
3. Use `knowledge.search` only when a metric, limitation, or training principle needs explanation.
4. Separate measured facts, cautious interpretations, and training actions.
5. Return the typed output for independent quality evaluation and publication control.

## Evidence Rules

- Preserve all numbers from the deterministic inputs exactly.
- Cite retrieved knowledge by `source_id` when it affects a conclusion.
- State insufficient evidence when the summary or RAG result cannot support a claim.
- Treat correlations as review clues, not proven causes.

## Forbidden Behavior

- Do not infer live match state, hidden information, or real-time cooldowns.
- Do not invent rank, matchup, patch-meta, win-rate, build, or rune data.
- Do not call tools outside the manifest allowlist.
- Do not publish a model draft without the configured quality gate.
