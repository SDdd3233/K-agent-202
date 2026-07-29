# Contributing to K-agent

Thanks for helping improve the skill package.

## Good contributions

- Reproducible keyword-card fixes with a small example or regression fixture.
- New templates with clear assumptions, units, adjustable parameters, and validation notes.
- Documentation improvements, translations, and installation fixes.
- Improvements to static checking, evidence recording, or solver-version diagnostics.

## Before opening a pull request

- Run the relevant Python checks and `git diff --check`.
- Explain the solver version, unit system, and environment used for validation.
- Keep changes focused and update the relevant README or reference when behavior changes.
- Remove secrets, private paths, raw conversations, proprietary geometry, and customer data.

## Scope

This project favors small, reviewable improvements. Do not silently change solver-version assumptions, quality thresholds, material provenance, or the meaning of an existing template. If a change affects those contracts, describe the tradeoff in the pull request.
