# v0.3.3 - K-file Template Authoring and One-click Deployment

## What's new

- Added a dedicated workflow for turning an uploaded `.k`/`.key`/`.dyn` deck into a reusable template.
- Added source isolation, structured deck analysis, a maximum-five-question clarification gate, template contracts, and representative-variant validation.
- Added `references/template-authoring-protocol.md` and regression tests for template routing and safety gates.
- Claude Code installation now registers the local marketplace and installs `lsdyna-kagent` in one command, alongside the existing Codex installer.
- Bumped the plugin and repository release metadata to `0.3.3`.

## One-click installation

### OpenAI Codex CLI

```bat
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
install-codex.cmd
```

### Claude Code

```bat
git clone https://github.com/LLK-LL/K-agent.git
cd K-agent
install-claude.cmd
```

On macOS, Linux, or Git Bash, use `bash install-codex.sh` or
`bash install-claude.sh`. Claude installation requires the Claude Code CLI;
both installers reuse an existing `academic-search` MCP and fail closed if
MCP or plugin setup cannot be verified.

## Validation

- Full Python regression suite passes.
- `git diff --check` passes.
- LS-DYNA L1/L2 runs remain dependent on the user's local solver and license.
