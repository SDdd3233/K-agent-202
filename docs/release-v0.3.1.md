# v0.3.1 - Easier Install and Safer Literature Search

## What's new

- Installation is simpler for both OpenAI Codex CLI and Claude Code: clone this repository, run the matching installer, and start using `$lsdyna-kfile`.
- The installers now check for an existing `academic-search` MCP first. If you already have one, K-agent reuses it and leaves its command, paths, environment variables, and credentials untouched.
- If no `academic-search` MCP exists, K-agent can register its bundled search-only fallback so the skill, scripts, and MCP literature path work together.
- The portable release zip includes clear `README_INSTALL.md` and `DEPENDENCIES.md` files so users can see required Python, `uv`, solver, manual, and optional literature-search setup in one place.
- Public documentation now explains what the new MCP behavior means in plain language: existing setups are preserved, the fallback is only used when needed, and secrets stay on the user's machine.

## Why it is better

This release makes K-agent easier to share and safer to install. A user can send the GitHub repository link to Codex or Claude Code, follow the repository instructions, and install the LS-DYNA skill without manually wiring the full MCP chain. Teams that already have an academic-search server keep their existing configuration; new users still get a complete fallback path.

## Included

- Portable `lsdyna-kfile` skill for OpenAI Codex CLI and Claude Code.
- Requirement convergence, unit-aware material lookup, mesh generation, static checking, solver wrapper, and result parsing.
- Drop, crash, penetration, forming, ALE, and SPH templates.
- Search-only academic MCP fallback for literature-backed material parameters, boundary conditions, and operating conditions.
- Bilingual repository documentation, publishing safety notes, install scripts, and dependency notes.

## Notes

- L1/L2 solver verification still requires a local LS-DYNA installation, license, and compatible solver path.
- Official LS-DYNA manual PDFs are not included in the public repository or the lightweight release zip. Fetch and index them locally with `python skills/lsdyna-kfile/scripts/fetch_manuals.py`.
- Material values are representative references, not project calibration data.
