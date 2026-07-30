# Existing Deck Repair Protocol

Use this reference only when the user supplies an existing LS-DYNA `.k`, `.key`, or `.dyn`
deck and wants it modified, debugged, checked, or run to diagnose solver output.

## Routing

Existing deck mode skips:

- Requirement brainstorming and convergence.
- Mandatory `spec.md` confirmation.
- Template applicability checks.
- Baseline official/academic search gates for new models.
- New deck generation from scratch.

It retains:

- Solver environment check.
- `knowledge/errors.md` precheck before edits.
- L0 static validation, L1 initialization trial, L2 full-run quality gates.
- Maximum 8 repair iterations.
- Final report and experience append when a new solver/debugging lesson was learned.

Without `spec.md`, preserve the original deck's physical intent as the working contract.

## Workspace Setup

Never modify the user's original deck directly. First run:

```bash
python "SKILL_DIR/scripts/prepare_existing_deck.py" user_model.k --objective "short user goal"
```

The script creates:

```text
repair_<deck-name>/
  source/
  working/
  iterations/
    001/
  deck-manifest.json
  repair-history.json
```

Treat `source/` as read-only evidence. Edit only `working/` and per-iteration copies.
`deck-manifest.json` records the main deck, recursive include graph, hashes, copied files,
missing includes, and the user objective.

If an include path points outside the main deck directory, inspect the manifest before solving.
The copier preserves files for evidence, but the repaired working deck may still need an explicit
include-path rewrite inside `working/` so LS-DYNA can resolve it from the isolated run directory.

## Repair Loop

For each iteration:

1. Copy the current working deck/include closure into `iterations/<NNN>/` or run with
   `run_dyna.py --rundir iterations/<NNN>`.
2. Run L0:
   ```bash
   python "SKILL_DIR/scripts/check_kfile.py" repair_x/working/model.k --json repair_x/iterations/NNN/l0.json
   ```
3. If L0 fails, diagnose from `l0.json`, edit the smallest relevant card/include, and record the change.
4. Run L1:
   ```bash
   python "SKILL_DIR/scripts/run_dyna.py" repair_x/working/model.k --rundir repair_x/iterations/NNN --endcyc 50 --ncpu 4 --timeout 300
   python "SKILL_DIR/scripts/parse_results.py" repair_x/iterations/NNN --json repair_x/iterations/NNN/report.json
   ```
5. Use `diagnostics[]`, `errors[]`, warnings, `d3hsp`, `messag`, and `mes*` evidence to decide the next edit.
6. Stop after PASS at L1, then run L2 full calculation and parse against `references/quality-gates.md`.
7. If not repaired within 8 iterations, stop and report current symptoms and attempted fixes.

Append each attempt to `repair-history.json`:

```json
{
  "iteration": 1,
  "stage": "L0|L1|L2",
  "verdict": "PASS|WARN|FAIL",
  "evidence": ["source file and lines or solver diagnostics"],
  "diagnosis": "probable cause",
  "change": "exact card/file changed",
  "permission_class": "safe|stabilization|physical",
  "result": "what changed after rerun"
}
```

## Modification Permissions

Allowed without asking:

- Formatting and fixed-field alignment.
- Broken relative include paths inside the repair workspace.
- Missing or inconsistent ID references when the intended target is obvious.
- Missing output cards required for quality gates, such as `*DATABASE_GLSTAT`.
- Trial-only `ENDCYC=50` or temporary L1 termination overrides.

Allowed automatically but report clearly:

- Conservative control/stabilization edits tied to solver diagnostics, such as timestep scale,
  contact stiffness scale, hourglass control, or adding recommended contact output.

Ask the user before changing:

- Material model, material constants, EOS, failure strain, erosion criteria.
- Loads, initial velocity, constraints, contact pair definitions, friction, geometry, mesh topology.
- Production `ENDTIM`, part deletion, material replacement, or physical simplification.

Never silently delete parts, replace material models, shorten the production run, or reinterpret the
simulation purpose.

## Final Report Additions

For existing deck mode, include:

- Original deck path and repaired working deck path.
- Manifest path and repair history path.
- Whether the original files were left untouched.
- Iteration table: L0/L1/L2 verdict, main evidence, edit made.
- Permission-gated edits, including any user-approved physical changes.
