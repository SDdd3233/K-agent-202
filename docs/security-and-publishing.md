# Security and Publishing

K-agent can process engineering inputs, local paths, solver logs, and literature configuration. Treat generated decks and reports as potentially sensitive until reviewed.

Before pushing a public repository or sharing an example, check that it contains none of the following:

- API keys, access tokens, passwords, cookies, private certificates, or credential files.
- Private Windows paths, usernames, internal hostnames, license-server details, or local configuration files.
- Raw conversations, unpublished papers, customer information, proprietary CAD, or unreleased test data.
- Solver output that exposes confidential geometry, material data, or project identifiers.

Use environment variables or a user-local configuration file for optional services. Never replace a placeholder with a real credential in a script, README, MCP config, or example.

The repository intentionally ignores official manual PDFs and generated keyword indexes. Fetch them locally when needed instead of committing copies without checking redistribution rights.

For a final pre-push check, review `git status`, `git diff --cached`, and the complete list of staged files. A clean static check does not prove that a deck is safe to publish.
