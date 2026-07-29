# Literature Parameter Routing

Use this reference when an LS-DYNA task needs physical, empirical, or material
parameters that are not already trusted in local templates or
`knowledge/materials.json`.

## Scope

Route these lookups through the bundled `academic-search` MCP:

- Material constants not present in the local database: density, modulus,
  Poisson ratio, yield stress, hardening, thermal properties, heat capacity,
  conductivity, melting temperature, and similar measured properties.
- Constitutive and failure model parameters: Johnson-Cook A/B/n/C/m,
  Cowper-Symonds constants, EOS coefficients, damage/failure strain
  parameters, strain-rate curves, fracture energy, erosion thresholds, and
  comparable empirical model data.
- Contact and interface parameters when they are material/test dependent:
  friction coefficients, adhesion/cohesion, interface strength, thermal contact
  conductance, or impact/contact calibration data.
- Experimental conditions that control applicability: material grade, heat
  treatment, porosity, temperature, strain rate, specimen geometry, loading
  mode, test method, and unit system.

Keep these lookups on the original LS-DYNA path:

- Keyword names, card layouts, field order, defaults, flags, version support,
  and solver behavior: use the official manuals first.
- LS-DYNA examples, error messages, FAQ entries, and solver-specific modeling
  practices: use local knowledge, `dynasupport.com`, `dynaexamples.com`, and
  `lsdyna.ansys.com` as before.
- General non-literature web facts: use the existing ordinary web fallback.

## MCP Source Policy

Use the vendored `nature-academic-search` package at:

`SKILL_DIR/vendor/nature-academic-search/`

The guaranteed MCP server is `academic-search`. Its guaranteed core tools are:

- `search_papers`
- `get_paper_by_id`
- `get_citation`
- `lookup_mesh`

By default, `search_papers` searches CrossRef, PubMed, and arXiv. Scopus and
ScienceDirect are optional: use them only when the user has configured local
Elsevier/pybliometrics credentials and explicitly needs those sources.

Do not treat `paper-search MCP` tools as bundled or guaranteed. If an
environment happens to provide them, they may be used only as an optional
fallback after the guaranteed `academic-search` path.

## Evidence Rules

For every parameter adopted from literature, record evidence in
`research/parameter-evidence.json` and summarize it in
`research/literature-notes.md`.

Each evidence item must include:

- parameter name and LS-DYNA card/field where it is used
- adopted value, original units, converted deck units, and conversion method
- material grade/state, temperature, strain rate, test method, and specimen or
  loading condition when available
- source title, authors, year, DOI/PMID/arXiv ID, and retrieval source
- full-text provenance: page, table, figure, or equation number whenever a
  numeric value is adopted
- applicability note and confidence: `high`, `medium`, or `low`

Abstract-only search results may identify candidate papers, but numeric values
from abstract-only metadata are unverified. Mark them `unverified` and do not
silently use them as final deck parameters unless the user explicitly accepts
that risk or no verified alternative exists.

Also write `research/references.bib` for papers that support adopted parameter
values. Use `get_citation` when DOI/PMID/arXiv IDs are available; otherwise
generate BibTeX from MCP-returned metadata and mark it as generated.

## Query Pattern

Build queries from all available engineering context:

`<material grade> <parameter/model> <test mode> <temperature/strain rate> LS-DYNA`

Examples:

- `Ti-6Al-4V Johnson-Cook parameters high strain rate`
- `6061-T6 aluminum Johnson Cook failure strain compression`
- `concrete Holmquist Johnson Cook EOS parameters impact`

Prefer papers that report complete parameter sets under matching material state
and loading conditions. If values conflict, prefer better provenance and closer
test conditions over citation count alone.
