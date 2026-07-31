# K-agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-skill-412991)](https://github.com/openai/codex)

> Turn a simulation idea into an LS-DYNA `.k` deck that is checked, solver-tested, and documented.

K-agent is a local-first agent skill and Claude Code plugin for engineering teams who need a repeatable way to build LS-DYNA keyword files. It combines requirement convergence, keyword/manual lookup, unit-aware material selection, mesh generation, static checks, solver execution, and result quality gates in one workflow.

[中文说明](README.zh-CN.md)

## What it does

- Converges an underspecified simulation idea into a reviewable simulation brief.
- Builds complete keyword decks for drop, crash, penetration, forming, ALE, and SPH workflows.
- Uses bundled templates and a material library; an R16 keyword-manual index can be fetched and generated locally while targeting the documented R14.1.1 solver baseline.
- Generates simple plate, block, cylinder, sphere, and SPH meshes; accepts user-provided mesh includes for complex geometry.
- Runs L0 static checks, L1 initialization trials, and L2 full runs with energy, hourglass, mass-scaling, and termination checks.
- Searches literature for material parameters, boundary conditions, and operating conditions through `academic-search`, recording paper titles, DOI, and applicability. Existing MCP registrations are reused; the internal fallback is registered only when needed.

## Why this exists

Writing a syntactically valid keyword deck is not the same as producing a useful simulation. The risky work is usually hidden in assumptions, unit conversion, card alignment, contact setup, solver startup errors, and result interpretation. K-agent makes those decisions explicit and keeps a verification trail beside the generated deck.

## Before and after

| Without a repeatable workflow | With K-agent |
| --- | --- |
| A vague request becomes a large deck full of implicit assumptions. | The agent converges a simulation brief and marks assumptions. |
| Units and material values are copied by hand. | Values are selected from a unit-aware material library. |
| A deck is delivered after a visual review. | Static checks and solver runs are part of the delivery gate. |
| Literature values are hard to audit later. | Adopted parameters can carry DOI, page/table, conditions, and confidence. |

## Quick start

### Requirements

- Python 3.8+.
- A local LS-DYNA installation for L1/L2 solver verification. The default configuration targets ANSYS 2024R2 / LS-DYNA R14.1.1.
- `uv` only when K-agent must register its internal literature-search MCP fallback. The core skill and static checker do not require an API key.
- Optional: `pypdf` for rebuilding the keyword-manual index when the manuals are not present.

### Install for OpenAI Codex CLI

```bat
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
install-codex.cmd
```

Then invoke `$lsdyna-kfile`, or describe an LS-DYNA modeling task and let the skill activate.
The installer checks for an existing `academic-search` MCP first. When found,
its command, path, environment, and credentials remain untouched; the internal
fallback is registered only when the server is definitively absent.

For macOS, Linux, or Git Bash:

```bash
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
bash install-codex.sh
```

### Install for Claude Code

Initialize the MCP conditionally once:

```bat
install-claude.cmd
```

On macOS, Linux, or Git Bash, run `bash install-claude.sh`. This reuses an
existing `academic-search` MCP without registering or overwriting another one.
Then load the repository as a local plugin:

```bash
claude --plugin-dir "/path/to/K-agent"
```

You can also add the local marketplace and install `lsdyna-kagent`. Run the
same initialization script from the checkout because a static plugin MCP file
cannot perform a conditional pre-install check.

### Configure the solver

Set `LSDYNA_BIN` and, for MPP runs, `LSDYNA_MPIEXEC`, or create `~/.lsdyna-kagent.json`:

```json
{
  "solver_bin": "C:\\LSDYNA\\bin",
  "mpiexec": "C:\\Program Files\\Microsoft MPI\\Bin\\mpiexec.exe"
}
```

If the official manuals are absent, fetch them and rebuild the index:

```bash
python skills/lsdyna-kfile/scripts/fetch_manuals.py
```

## Example request

> Use the mm-ton-s unit system to simulate a 1 kg steel block dropped from 1 m onto a 2 mm 6061 aluminum plate. Fix the four edges, run for 5 ms, and report deformation and energy curves.

The workflow selects a template, converts material values, generates the simple mesh, writes the deck, and produces a validation report. When literature search is triggered, it automatically reports the paper title, DOI, supported engineering assumption, applicability, and whether the result contains metadata, an abstract, or a full-text location. Literature values are never presented as project measurements.

## Verification workflow

```text
simulation brief -> evidence and template selection -> deck generation
      -> L0 static check -> L1 initialization trial -> L2 solver run
      -> quality gates -> report with assumptions and adjustable parameters
```

Typical commands from a skill directory are:

```bash
python scripts/check_kfile.py model.k
python scripts/run_dyna.py model.k --endcyc 50 --ncpu 4 --timeout 300
python scripts/run_dyna.py model.k --ncpu 4 --timeout 1800
python scripts/parse_results.py . --json report.json
```

Solver verification depends on a locally installed solver and license. Without one, L0 checks and mesh generation can still run, but L1/L2 cannot be honestly claimed.

## Repository layout

```text
.
├── .claude-plugin/              # Claude Code plugin and marketplace manifests
├── agents/                      # Optional modeling sub-agent definition
├── skills/lsdyna-kfile/         # Portable core skill
│   ├── SKILL.md                 # Main workflow and delivery contract
│   ├── references/              # Protocols, formats, routing, quality gates
│   ├── scripts/                 # Mesh, units, checks, solver, parsing
│   ├── knowledge/               # Materials and error patterns
│   ├── templates/               # Drop, crash, penetration, forming, ALE, SPH
│   └── vendor/                  # Search-only academic MCP fallback (not a separate skill)
├── install-codex.cmd            # Windows installer
├── install-codex.sh             # macOS/Linux/Git Bash installer
├── install-claude.cmd           # Windows conditional Claude MCP setup
├── install-claude.sh            # macOS/Linux/Git Bash Claude MCP setup
└── docs/                        # Publishing, release, and contribution notes
```

The official manual PDFs and generated keyword index are intentionally ignored from Git. This keeps the repository lightweight and lets users fetch the manuals locally under their own terms.

## Safety and privacy

K-agent is designed for local engineering work. Before publishing or sharing generated work, remove API keys, tokens, cookies, private paths, raw conversations, unpublished research, customer data, and proprietary geometry. Do not put credentials in the skill package; the scripts read optional service settings from the environment or the user's local configuration.

See [docs/security-and-publishing.md](docs/security-and-publishing.md) for a pre-publication checklist.

## Current status

The current release is v0.3.2. The repository is usable as a portable skill package with fail-closed MCP installation and post-registration verification. The documented solver baseline is LS-DYNA R14.1.1, while the bundled manual references are R16. Material values are representative literature or handbook values and should be replaced or calibrated with project test data for engineering decisions.

## Roadmap

- Add more validated templates for common impact and manufacturing workflows.
- Improve solver-version compatibility checks and result-report portability.
- Expand evidence adapters while keeping credentials and private data local.
- Add small, solver-independent regression fixtures for more keyword cards.

## Contributing

Examples, templates, documentation, and validation improvements are welcome. Please do not submit secrets, proprietary decks, private meshes, raw conversations, or customer data. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request.

## License

Released under the [MIT License](LICENSE).

## One-sentence summary

K-agent is a local-first LS-DYNA authoring skill that turns natural-language simulation requirements into solver-checked, auditable keyword decks.
