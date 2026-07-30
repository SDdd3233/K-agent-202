# v0.3.0 - Public Repository Launch

## Included

- Portable `lsdyna-kfile` skill for OpenAI Codex CLI and Claude Code.
- Requirement convergence, unit-aware material lookup, mesh generation, static checking, solver wrapper, and result parsing.
- Drop, crash, penetration, forming, ALE, and SPH templates.
- Search-only academic MCP fallback for literature-backed parameters, boundary conditions, and operating conditions; existing MCP registrations take precedence and are never overwritten.
- Bilingual documentation, publishing safety notes, contribution guidance, and MIT licensing.

## Who should try it

Engineers and researchers who already have a local LS-DYNA installation and want a repeatable, auditable starting point for keyword deck authoring.

## Current limitations

- L1/L2 verification requires a local LS-DYNA installation, license, and a compatible solver path.
- The documented solver baseline is R14.1.1; the bundled manual references are R16.
- Material values are representative and are not a substitute for project calibration or test data.
- Complex CAD meshing is outside the current scope; provide a mesh include instead.

## Suggested repository metadata

Description: `Local-first LS-DYNA agent skill for generating, checking, and solver-verifying auditable .k decks.`

Topics: `ls-dyna`, `finite-element-analysis`, `explicit-dynamics`, `simulation`, `engineering`, `claude-code`, `openai-codex`, `agent-skills`, `keyword-file`
