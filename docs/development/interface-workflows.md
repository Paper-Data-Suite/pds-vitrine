# Teacher-facing and direct workflows

Vitrine exposes one application layer through two terminal interfaces. Bare
`vitrine` (or `vitrine menu`) starts the low-density teacher menu. Complete
commands are noninteractive and never prompt for omitted values.

The teacher path selects a current Subject by label and exact ID, then progresses
through Portfolio creation, exact Profile Binding, configured Candidate discovery
and provenance review, explicit Selection, Placement and Arrangement, Working
Composition, exact Audience Context, Snapshot Request and Plan preparation, Build
Attempt, sealed Edition, and exact verification. Screens are intentionally compact.
`B`, `M`, `Q`, and `H` retain the shared PDS navigation meanings.

Representative direct reads use synthetic identifiers:

```text
vitrine portfolio list --workspace-root C:\PDS
vitrine portfolio show portfolio-syn-001 --workspace-root C:\PDS
vitrine candidate list portfolio-syn-001 --workspace-root C:\PDS
vitrine arrangement show portfolio-syn-001 --section-id baseline --workspace-root C:\PDS
vitrine composition show portfolio-syn-001 --workspace-root C:\PDS
vitrine audience list portfolio-syn-001 --workspace-root C:\PDS
vitrine snapshot series list portfolio-syn-001 --workspace-root C:\PDS
vitrine snapshot plan-show snapshot-plan-syn-001 --workspace-root C:\PDS
vitrine snapshot verify snapshot-series-syn-001 --edition 1 --workspace-root C:\PDS
```

Mutations require exact IDs and actor attribution. They accept
`--expected-state-revision`; when it is omitted, the shared wrapper observes the
state once immediately before the operation. Pointer-sensitive operations also
accept their exact expected pointer revision. A conflict is reported and is not
silently retried.

```text
vitrine portfolio create --subject-id subject-syn-001 --title "Writing Portfolio" --actor-id teacher-syn-001
vitrine selection add portfolio-syn-001 candidate-syn-001 --section-id baseline --actor-id teacher-syn-001
vitrine arrangement place portfolio-syn-001 selection-syn-001 --section-id baseline --actor-id teacher-syn-001
vitrine composition build portfolio-syn-001 --actor-id teacher-syn-001
vitrine audience create portfolio-syn-001 --audience-rule-id student-review --actor-id teacher-syn-001
```

`ActorAttribution` records who requested an action. It is not source-read,
curation, or Snapshot-build authorization. Those decisions come from separately
configured gates. The ordinary runtime supplies no live producer integrations
and fails closed when a gate or provider is unresolved.

Development fixture adapters and authority/providers may be supplied only by an
explicitly injected `VitrineWorkflowDependencies` test or development context.
They are Vitrine-owned ScoreForm-, Quillan-, and Concord-shaped fixtures, not
live readers. Merely running from a source checkout never enables them.

Snapshot preparation uses an injected planning provider or an explicit direct
CLI plan-specification JSON object containing `entry_plans`, `export_plans`, and
optional policy and acknowledgement fields. It does not require a fabricated
complete canonical `SnapshotBuildPlan` record. The ordinary planning provider
is unconfigured and fails closed. Preparation persists Request and Plan as
separate records; building later executes one exact immutable Plan.

The semantic boundaries remain visible:

```text
Candidate != Selection
Working Composition != Snapshot
Audience Context != disclosure authorization
Build Request != Build Plan != Build Attempt != Edition
Edition verification != Export verification
sealed Edition != current-Edition pointer
```

Candidate review shows decision-relevant provenance, relationship assertions,
availability, conditions, exact IDs, and eligible sections without displaying
raw producer bodies. Condition acknowledgement is explicit and is not described
as satisfying an independent Profile review requirement. Historical Edition
verification uses canonical Vitrine state and sealed Vitrine-owned bytes; it
does not reread the producer source.
