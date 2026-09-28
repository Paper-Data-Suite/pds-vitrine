# Issue #99 paper-native Reflection validation

This record defines focused and physical acceptance for paper-native student
Reflection.

## Automated acceptance

`python scripts/validate_paper_reflection.py` verifies the #99 contract markers,
runtime surfaces, package/repository wiring, docs, and focused tests. When the
complete repository suite already ran, use `--skip-focused-tests`.

The isolated wheel smoke is:

```text
python scripts/smoke_test_paper_reflection_wheel.py <vitrine-wheel> <core-wheel>
```

It requires only Core + Vitrine wheels, discovers Vitrine through Core's
`paper_data_suite.modules` contract, verifies active PDS2 routing compatibility,
checks the declared Core/qrcode/ReportLab dependencies, and confirms no sibling
PDS producer package is required for routing/profile discovery.

Focused automated coverage includes immutable issuance, exact class-link
selection, PDS2 route validation, route persistence/replay, returned evidence,
rescan preservation, explicit student-authorship confirmation, student/recorder
separation, typed fallback, Current Portfolio paper materialization, printable
packet generation/reprint, Portfolio workflow status, returned-paper preview,
and non-mutating cancellation paths.

## Physical acceptance procedure

For each release candidate, record:

```text
Vitrine wheel filename and digest
Core wheel filename and digest
OS and Python
printer make/model
scanner make/model
paper size
print scaling
scan DPI
color mode
simplex/duplex
retained source format
test date
tester
```

Exercise this exact path:

```text
1. Open one Portfolio's Student Reflection workflow.
2. Review the exact curated comparison targets.
3. Supply/select the exact prompt identity and prompt text.
4. Verify the exact student/class link.
5. Generate the response PDF and print at the recorded scaling.
6. Write a representative handwritten response.
7. Scan the actual page through normal Core intake.
8. Confirm Core resolves the PDS2 route to Vitrine.
9. Confirm Vitrine persists returned-paper evidence without creating a Reflection.
10. Open the exact returned paper from Student Reflection review.
11. Confirm the viewed bytes correspond to the physical response.
12. Type CONFIRM STUDENT AUTHOR.
13. Verify canonical PortfolioReflection author is the exact core_student.
14. Verify teacher is confirmation/recording actor, not Reflection author.
15. Verify exact prompt, targets, Subject link, student reference, and evidence IDs.
16. Verify no PortfolioPlacement was created for Reflection.
17. Verify the exact Reflection requirement is satisfied.
18. Verify Current Portfolio preparation can materialize the retained paper bytes.
19. Verify the original Core-retained source remains digest-valid.
```

For multi-page acceptance, scan at least one response where page ordering matters.
For rescan acceptance, route a second scan of one page and verify both
occurrences remain preserved and the UI requires an explicit occurrence choice.

## Failure expectations

Acceptance must fail closed for wrong issuance, missing page, mismatched class
identity, state conflict, authority denial, tampered retained bytes, unsafe
retained path, wrong confirmation phrase, and an invalid/ambiguous rescan
selection.

OCR is not part of acceptance.

## Installed end-to-end wheel acceptance

The final automated installed acceptance is:

```text
python scripts/smoke_test_paper_reflection_end_to_end_wheel.py <vitrine-wheel> <core-wheel>
```

The harness copies only synthetic test support and fixture data into a temporary directory. It does not copy the Vitrine or Core source packages. With `PYTHONPATH` removed and the working directory outside the repository, all `vitrine` and `pds_core` imports therefore resolve from the supplied wheels.

The acceptance proves one exact one-page paper lifecycle: issuance, exact Core route registration, retained PNG source, installed module-profile discovery, Core dispatch to Vitrine, returned-paper evidence, explicit adult authorship confirmation, canonical student-authored Reflection, paper finalization, and exact retained bytes through the Current Portfolio Reflection renderer.

It asserts no `PortfolioPlacement` is created for the Reflection, the student remains the canonical author, the adult remains confirmation/recording actor, the prompt and targets are unchanged from issuance, the retained digest is preserved, the Reflection requirement reaches `recorded`, and no sibling PDS producer package is installed.

General repository wheel smokes preserve the historical Core-only base installation and use `--no-deps`. Printable PDF support is declared under the `paper` extra (`pds-vitrine[paper]`). The #99 routing and end-to-end isolation smokes deliberately exercise only surfaces that remain available without that extra.
