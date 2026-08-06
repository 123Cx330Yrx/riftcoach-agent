---
name: single-match-review
description: Review one specified completed match from a validated RiftCoach summary using attributable knowledge. Use for a deep review of this match, one game, or an explicit match ID.
---

# Single Match Review

## Objective

Produce a grounded review of exactly one completed match. Treat the selected
match row and its deterministic report facts as the only sources of
player-specific performance claims.

## Workflow

1. Validate Player Summary Schema v1.0 and locate `target_match_id` exactly once.
2. Isolate the target match instead of turning other match rows into single-game facts.
3. Check short-game and Timeline availability before interpreting the metrics.
4. Use `knowledge.search` only to explain a metric, limitation, or general training principle.
5. Separate measured facts, cautious interpretations, and bounded training actions.
6. Return the typed output for independent Harness evaluation and publication control.

## Evidence Rules

- Preserve all target-match numbers from deterministic inputs exactly.
- Cite retrieved knowledge by `source_id` when it affects a conclusion.
- Treat a short game as reviewable but insufficient for long-term trend claims.
- Do not treat unavailable Timeline data as zero or infer event timing from Match Detail.
- State insufficient evidence when the target row or retrieved knowledge cannot support a claim.

## Forbidden Behavior

- Do not infer the lane opponent, hidden information, live match state, or real-time cooldowns.
- Do not invent patch-meta, rank, matchup, win-rate, build, or rune comparisons.
- Do not call Riot API or tools outside the manifest allowlist.
- Do not use recent aggregate rows as if they were facts from the target match.
- Do not publish a model draft without the configured quality gate.
