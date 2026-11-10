# Domain Docs

How the engineering skills and autonomous agents consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root: defines canonical endurance physiology concepts, mathematical formulas, and coaching terms.
- **`docs/adr/`**: read Architecture Decision Records that touch the area you are about to modify.

If any of these files do not exist, proceed silently. The `domain-modeling` skill creates them lazily when terms or decisions get resolved.

## File structure

Single-context repo:

```text
/
├── GLOSSARY.md                                       # Canonical physiology and coaching terminology
├── docs/adr/                                         # Architecture Decision Records
│   └── 0001-deterministic-sports-engine-and-offline-store.md
├── docs/agents/                                      # Agent coordination configs
│   ├── issue-tracker.md
│   ├── triage-labels.md
│   └── domain.md
├── app/                                              # FastAPI backend & physiology engine
└── public/                                           # Frontend assets & GPX files
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, or a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids (e.g. use "Calculator Pace" instead of "Pace Calculator", use "VDOT" instead of "running score").

## Flag ADR conflicts

If your proposal contradicts an existing ADR, surface it explicitly rather than silently overriding.
