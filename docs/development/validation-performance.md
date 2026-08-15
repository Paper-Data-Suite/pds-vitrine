# Validation performance and CI qualification

Issue #52 separates runtime compatibility from complete repository qualification
without weakening either proof.

## Authoritative complete gate

The authoritative source-through-installed-wheel qualification command remains:

```powershell
python scripts\validate_repository.py --core-wheel "<path-to-official-core-wheel>"
```

It uses isolated Ruff, Mypy, and pytest caches by default and continues to prove
Core-wheel authenticity/compatibility, all pytest coverage, static analysis,
standalone validators, documentation and fixture audits, package construction,
Twine/package-content policy, all installed-wheel smoke suites, `git diff --check`,
and repository-residue invariants.

For an intentionally dirty development checkout, add `--allow-dirty`.

## Optional reusable local static-analysis caches

Repeated local complete validations may opt into correctness-preserving persistent
Ruff and Mypy caches:

```powershell
python scripts\validate_repository.py `
  --core-wheel "<path-to-official-core-wheel>" `
  --allow-dirty `
  --reuse-static-caches
```

The reusable cache root defaults to:

```text
~/.cache/pds-vitrine/static-analysis/py<major><minor>/
```

Set `PDS_VITRINE_STATIC_CACHE_DIR` to choose another root.

This option changes performance only. Ruff and Mypy still analyze the requested
source tree normally, and deleting the cache must not change pass/fail behavior.
The default complete/CI path deliberately remains isolated.

## CI tiers

GitHub Actions continues to cover the full cross-product:

```text
Ubuntu + Windows
x
Python 3.11 + 3.12 + 3.13 + 3.14
```

Each combination runs the full pytest runtime suite exactly once.

Two reference cells perform complete repository qualification instead of also
running a separate compatibility pytest job:

```text
Ubuntu / Python 3.11
Windows / Python 3.14
```

The other six cells run Core verification, dependency consistency, full pytest,
and whitespace validation. The two reference cells run the authoritative complete
gate, which itself includes full pytest plus static analysis, all standalone
validators, documentation/corpus/foundation checks, package construction, Twine
and package-content validation, and every installed-wheel smoke suite.

This corner pairing covers both supported operating systems and both ends of the
supported Python range with package/install qualification while avoiding a second
pytest execution on those cells.

## Measured evidence

Measurements below were collected on the same Windows development machine during
issue #52. Wall-clock values are diagnostic, not CI thresholds.

| Measurement | Baseline | Current | Reduction |
| --- | ---: | ---: | ---: |
| Full pytest | 1013.399 s | 296.087 s | 70.8% |
| Complete repository validation | 1788.443 s | 586.514 s | 67.2% |

The post-de-duplication intermediate complete gate was 967.599 seconds. The
final cumulative issue #52 gate is 586.514 seconds, a further 39.4% reduction
from that intermediate measurement.

The slowest standalone validators also improved materially:

| Standalone validator | Baseline | Current | Reduction |
| --- | ---: | ---: | ---: |
| Snapshot workflows | 152.253 s | 40.275 s | 73.5% |
| Improvement Portfolio | 80.917 s | 24.782 s | 69.4% |
| Showcase Portfolio | 68.259 s | 22.856 s | 66.5% |

Representative profiled runtime improvements:

| Profiled operation | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Snapshot lifecycle test call | 97.917 s | 34.071 s | 65.2% |
| Snapshot `commit_record_batch()` | 81.876 s | 21.328 s | 74.0% |
| Curation composition test call | 56.277 s | 16.632 s | 70.4% |
| Curation `commit_record_batch()` | 47.454 s | 11.303 s | 76.2% |

The principal causes were:

1. removal of nested complete acceptance-validator executions from pytest;
2. skip modes for focused Candidate/curation tests after full pytest has already
   exercised those focused paths;
3. removal of duplicate improvement-Portfolio validator execution;
4. one-pass canonical-state/history verification within a storage operation,
   including reuse of already verified immutable record bytes and state;
5. CI factoring so platform-independent qualification no longer runs in all eight
   OS/Python cells.

Using the final local timings only as an illustration, not as a hosted-runner
prediction, eight complete 586.514-second gates would total about 78.2 aggregate
minutes. Six 296.087-second compatibility pytest runs plus two complete gates would
total about 49.2 aggregate minutes, approximately 37% less aggregate execution.
