# v0.3.2 - Confirmed Workflow and Complete MCP Deployment

## What's new

- The `lsdyna-kfile` skill pauses after writing `spec.md` until the user explicitly confirms the simulation brief.
- Final delivery requires a persisted `final_delivery_report.md` and an equivalent user-facing delivery summary.
- The compressed skill body is installed as the root skill after static, workflow, and full-suite verification.
- Codex and Claude installers fail closed when `academic-search` MCP setup or post-registration verification fails.
- The bundled MCP setup verifies that a newly registered server is visible through the host CLI; existing registrations remain untouched.
- Added workflow contract tests covering routing, confirmation, baseline evidence, L0/L1/L2 order, repair limits, and final delivery.

## Installation

```bat
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
install-codex.cmd
```

The installer reuses an existing `academic-search` MCP. When none is available, it registers the bundled search-only fallback and verifies that the host can see it before reporting success.

## Validation

- `quick_validate.py`: passed.
- Workflow contract tests: 8 passed.
- Full `lsdyna-kfile` test suite: 31 passed.
- L0/L1/L2 solver runs remain dependent on the user's local LS-DYNA installation and license.
