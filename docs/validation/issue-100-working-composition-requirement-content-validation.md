# Issue #100 Working Composition requirement-backed content validation

Issue #100 qualifies Guided Working Composition v2 and the semantic distinction
between Placement-backed content, requirement-backed Reflection content, and
non-content Profile requirements.

## Contract under test

```text
vitrine_guided_working_composition_v2
```

The durable Working Composition and Inventory record families remain unchanged.

## Focused acceptance

The focused suite proves:

- exact Reflection revision -> exact canonical record -> exact Profile
  requirement -> exact explicit scope;
- a satisfied Reflection appears in `requirement_contents` without becoming a
  Placement;
- a missing required Reflection remains a visible content obligation;
- section mapping occurs only from explicit `scope_kind` / `scope_reference`;
- portfolio-scoped Reflection remains portfolio-level content;
- current resolution follows the current exact Reflection head;
- historical resolution remains pinned to the exact frozen
  `CurationRevisionRef`;
- multiple independent exact Reflection records are not collapsed heuristically;
- Profile/context mismatch and missing frozen records fail closed;
- Approval and other non-content requirements are not fabricated as Portfolio
  content;
- teacher presentation does not describe a 0/0 Reflection section as empty
  Placement state;
- Technical Details retains exact Placement and Reflection provenance;
- direct `composition prepare` output exposes the same semantic separation;
- Current Portfolio consumes the shared semantic projection while preserving
  exact Reflection materialization and #99 paper-byte behavior.

## Dedicated validators

```text
python scripts/validate_working_composition.py
python scripts/validate_current_portfolio_build_export.py --skip-focused-tests
python scripts/validate_paper_reflection.py --skip-focused-tests
```

The Working Composition validator additionally guards the v2 contract identity,
content-summary fields, shared current/historical resolver, CLI markers, package
files, documentation index, acceptance marker, installed-wheel smoke, and
repository-gate wiring.

The Current Portfolio validator prevents reintroduction of duplicate
Reflection requirement/section semantic resolvers.

## Installed-wheel acceptance

```text
python scripts/smoke_test_working_composition_wheel.py \
  dist/pds_vitrine-<version>-py3-none-any.whl \
  /path/to/pds_core-0.6.3-py3-none-any.whl
```

The isolated smoke installs Core and Vitrine only and proves that v2 can:

1. create an explicit zero-capacity Reflection section and requirement;
2. record one exact canonical Reflection;
3. project that Reflection as requirement-backed content without a Placement;
4. expose the same semantics through `composition prepare`;
5. freeze and exactly replay Composition revision 1;
6. revise the Reflection to revision 2;
7. resolve current content to revision 2 while historical Composition revision 1
   remains pinned to Reflection revision 1;
8. run without ScoreForm, Quillan, Concord, Portia, or Meridian installed.

## Static and package qualification

```text
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
python scripts/check_package.py
python -m pytest -q
python -m build
python -m twine check dist/*
git diff --check
```

`check_package.py` requires both the historical v1 contract documentation and
the v2 / issue #100 documentation in the source distribution.

## Complete repository qualification

Use the exact supported Core wheel:

```text
python scripts/validate_repository.py \
  --core-wheel /path/to/pds_core-0.6.3-py3-none-any.whl \
  --reuse-static-caches
```

Issue #100 is not complete until this command ends with:

```text
PASS complete repository validation
```
