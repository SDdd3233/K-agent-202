# LS-DYNA Literature Search Routing

Read this reference only after the literature-search rule in `SKILL.md` fires.
This is an LS-DYNA engineering search workflow, not a general academic-writing
or reference-management workflow.

## Trigger Boundary

Use this route in either of two cases:

1. **Baseline branch**: once the engineering context is sufficient to form queries,
   an inapplicable or missing local template requires an official LS-DYNA search
   and an academic search in parallel. Do not wait for the official search to fail.
2. **Evidence-fallback branch**: local templates, `knowledge/materials.json`,
   manuals, and official LS-DYNA sources do not support a literature-type input,
   including material parameters, boundary conditions, loads, operating conditions,
   or validation cases.

An explicit request for papers, literature, DOI, or literature-backed engineering
inputs triggers this route regardless of template status. The baseline branch is
owned by `brainstorm-protocol.md` §4.4; this file owns the academic search details.

Mandatory baseline triggers include high-uncertainty mechanisms for which a
local template cannot be shown applicable, for example:

- explosive welding, flyer-plate welding, impact welding, or collision welding
- interface wave, wavy interface, jetting, bonding window, or collision angle
- blast-structure coupling, explosive loading of a deformable workpiece, or
  detonation-driven forming when no same-mechanism template exists
- coupled thermal-plastic-failure inputs used to justify bonding, melting, or
  interface morphology

In scope:

- material, constitutive, failure, erosion, EOS, strain-rate, and thermal data
- friction, interface, adhesion, contact, and calibration data
- boundary conditions, load curves, impact velocity, temperature, pressure,
  duration, and other operating conditions
- experimental setups, validation cases, benchmark conditions, and reusable
  baseline schemes for drop, crash, penetration, forming, ALE, SPH, blast,
  and impact models

Out of scope:

- keyword layout, field order, defaults, flags, version support, and solver
  behavior; use official manuals
- LS-DYNA errors, FAQ entries, and solver-specific examples; use local history
  and official LS-DYNA sites
- citation verification, MeSH strategy, citation-file conversion, BibTeX/RIS
  management, related-article management, and general literature reviews

## MCP Contract

Use an existing `academic-search` MCP when the environment provides one. Never
replace or re-register an existing server. The K-Agent fallback runtime is at
`SKILL_DIR/vendor/academic-search-mcp/` and is registered by the installation
scripts only when no compatible existing configuration is found.

The required search capability is `search_papers`. Source-specific search tools
may be used when exposed by the current MCP, but do not depend on citation,
verification, MeSH, or file-conversion tools. By default search CrossRef,
PubMed, and arXiv. Add Scopus or ScienceDirect only when the user already has
local Elsevier/pybliometrics access and the additional source is useful.

If `academic-search` is configured but `search_papers` is unavailable, report
the capability mismatch. Do not install a second MCP or overwrite the existing
configuration. If no academic MCP is configured, run:

```bash
python "SKILL_DIR/scripts/setup_academic_mcp.py" ensure --client auto \
  --server-dir "SKILL_DIR/vendor/academic-search-mcp"
```

A newly registered MCP becomes available after the host restarts or reloads its
MCP configuration. Do not silently replace the requested literature search with
ordinary web search in the same run.

## Search Procedure

### Common Search Steps

1. Build one or more queries from the engineering context:
   use the baseline or parameter form below.
2. Search the relevant default sources concurrently through `search_papers`.
3. If results are empty, broaden one constraint at a time using the order specified
   for the selected search type.
4. Merge and deduplicate by DOI first, then normalized title plus year.
5. Record `evidence_scope` as metadata only, abstract supported, or full-text
   location provided; do not imply that this search workflow independently verified
   the paper.

### Baseline Scheme Search

1. Query form: `<event/phenomenon> <object/material> <loading mode> LS-DYNA validation`.
2. Broaden in this order: event or load, object or geometry, material family, then
   validation mode.
3. Classify usable results as `direct-reuse`, `similar-adaptation`,
   `official-literature-combination`, or `no-similar-case`.
4. Select only results that support an actual baseline decision.

### Parameter and Condition Search

1. Query form: `<material/grade> <parameter or condition> <test/loading mode> <temperature/strain rate> <model>`.
2. Broaden in this order: model name, test mode, material state, then material family.
3. Rank by material state, loading mode, temperature, strain rate, and test setup;
   citation count is secondary.
4. Select only results that support a concrete model decision.

Example queries:

- `Ti-6Al-4V Johnson-Cook parameters high strain rate`
- `6061-T6 aluminum friction coefficient impact contact`
- `composite plate drop test boundary conditions impact velocity`
- `concrete HJC EOS parameters penetration experiment`

## Evidence Output

Write adopted search results to `research/literature-evidence.json` and mirror
the essential fields in `spec.md` under `文献依据`. If the baseline branch was
triggered by an inapplicable or missing template, also mirror the template
applicability result and the official-search result in `spec.md` under
`基准仿真方案与改造映射`.

Each evidence item must contain:

- `title`
- `doi`, using `unavailable` when no DOI is returned
- `year`, `source`, and available authors or other identifier
- `baseline_role`: `direct-reuse`, `similar-adaptation`,
  `official-literature-combination`, `parameter-support`,
  `boundary-condition`, `operating-condition`, `validation-case`, or
  `no-similar-case`
- `supports`: the material parameter, boundary condition, operating condition,
  validation case, or baseline scheme informed by the paper
- `template_applicability`: `applicable`, `inapplicable`, or `not-available`
  for baseline evidence, with a short reason when not applicable
- `official_basis`: manual keyword, official example, or official support page
  used alongside the paper; use `pending` only before task-book confirmation
- original value and unit when a numeric value is used
- converted deck value, deck unit, and conversion method
- matching material grade/state, temperature, strain rate, test method, and
  loading condition when available
- applicability, limitations, and `evidence_scope`: `metadata-only`,
  `abstract-supported`, or `full-text-location-provided`
- `reuse_items`, `modified_items`, and `unsupported_gaps` when the evidence is
  used to define a baseline scheme
- `search_queries` when the result is `no-similar-case`

The final report must list every selected paper title and DOI automatically,
grouped by baseline schemes, material parameters, boundary conditions, operating
conditions, or validation cases. State that literature values are representative
values rather than project measurements. Report `no-similar-case` explicitly when
no comparable case is found; never fill the gap with ordinary web results.
