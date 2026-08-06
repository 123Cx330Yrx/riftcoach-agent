# Skill Contract V1 Design

## Scope

Stage 5B defines how RiftCoach describes and validates one reusable workflow. It does not yet choose a Skill from natural language, run a Skill through AgentLoop, or add another model provider.

## Three Sources Of Truth

Each project-local Skill package has three distinct responsibilities:

- `manifest.yaml`: machine-readable identity, trigger examples, model references, tool permissions, budgets, and quality policy;
- `SKILL.md`: concise procedural instructions, evidence rules, and forbidden behavior loaded only after the Skill is selected;
- Pydantic models in `app/skills/`: authoritative input and output data validation.

The same field must not be independently redefined in several places. The loader rejects name and description drift between `manifest.yaml` and `SKILL.md`.

## First Vertical Contract

`recent-form-review` receives an already validated Player Summary Schema v1.0 document plus its deterministic report. It does not grant the model raw Riot API access or ask the model to calculate match facts. Its only allowed tool is `knowledge.search`, because player facts and Data Dragon name mapping are upstream deterministic responsibilities.

This preserves the project boundary:

```text
deterministic facts
→ Skill input validation
→ attributable knowledge retrieval
→ bounded Agent work
→ quality-gated output
```

## Loading And Validation

The loader must reject:

- malformed or unknown manifest fields;
- mismatched folder, manifest, or frontmatter names;
- invalid semantic versions and model references;
- missing or non-Pydantic input/output classes;
- tools that are not present in the active ToolRegistry;
- invalid budgets, duplicated examples, or overlapping positive/negative examples.

Loading a Skill grants no execution authority. Stage 5C will select a Skill; Stage 5D will translate its permissions and budgets into an `AgentRunRequest`.
