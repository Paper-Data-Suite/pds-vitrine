# Developing completed Portfolio navigation

Issue #102 is a Vitrine-local historical workflow. Once canonical Snapshot
Edition/Export/Presentation records exist, browsing, verification, and local
use must not import or reread ScoreForm, Quillan, Concord, Portia, or Meridian.

## Main modules

- `vitrine.completed_portfolio` is the pure canonical read model.
- `vitrine.portfolio_output_opening` verifies exact artifacts, resolves bounded
  workspace targets, and delegates through `LocalOpener`.
- `vitrine.completed_portfolio_actions` owns explicit verification and the
  historical Issue #101 Presentation handoff.
- `vitrine.completed_portfolio_menu` owns teacher-facing completed-history
  navigation.
- `vitrine.portfolio_menu` owns the Build Updated Edition routing handoff.
- `vitrine.current_portfolio_menu` owns post-build continuation while reusing
  the same #102 local-open services.

## Currentness

Never infer current from Edition number, generation time, directory mtime, or
artifact presence. Current means only the valid head of the exact Series'
`SnapshotCurrentPointerRevision` chain.

## Opening

Callers provide canonical artifact identity, not teacher-entered paths. The
opening service verifies the artifact, resolves its stored relative path under
the active workspace, checks file/directory kind, and only then invokes the
opener. `LocalOpener` injection exists so installed acceptance can record the
resolved target without launching GUI applications.

## Historical Presentation creation

Use `build_student_portfolio_presentation` from Issue #101. Do not duplicate
rendering or packaging. The historical Edition and technical Export are the
exact inputs. Existing Presentation custody is immutable and is never
automatically repaired.

## Build Updated Edition

The completed menu returns a routing signal. `portfolio_menu` then invokes the
existing current build workflow. No historical Edition or Series ID is passed
into that build. The Current Working Composition and current reviewed policy
remain authoritative.

## Producer independence

The completed-history/open/verify stage must work with only Core and Vitrine
installed. Producer packages are relevant before immutable Vitrine custody is
created, not afterward.
