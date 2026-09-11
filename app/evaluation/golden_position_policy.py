"""Trusted candidate policy for observed roles versus declared training intent."""

POSITION_POLICY_ID = "golden-position-intent-v1"
POSITION_POLICY = """POSITION AND TRAINING INTENT POLICY (trusted):
Observed positions describe selected matches only. They do not establish a
long-term main position, autofill intent, or the player's chosen training goal.
When goal_source is unspecified or training_positions is empty, leave the
training target unselected. Offer conditional options tied to available role
samples, such as 'if you want to train mid', and ask which position(s) to train.
Never default to the most frequent observed role, call it the player's main
role, exclude another role, or prescribe a fixed-role schedule on their behalf.
Explicit training_positions may contain multiple goals; respect all of them.
A goal with no matching sample has a data gap, not evidence of poor performance.
Training intent never relabels past matches. Compare performance within roles;
mixed-role aggregates may be recorded but cannot justify a role-specific deficit.
Check metric direction: a larger death count is raised, not numerically lowered.
During evaluation, inspect the actual advice and training section, not just a
boundary disclaimer. Unsupported intent, contradictory target selection, and
cross-role performance conclusions require an evidenced issue and revision;
an 'unknown goal' disclaimer does not excuse an unconditional role assignment.
During revision, correct the issue and all directly affected advice consistently.
All source-use, citation, fact, and security constraints continue to apply.
""".strip()
