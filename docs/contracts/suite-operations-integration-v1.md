# Vitrine Suite Operations Integration v1

## Status and scope

Issue #70 defines the Vitrine side of the shared Paper Data Suite module-operations
boundary. It does not define a new Core wire protocol. Vitrine implements the released
Core contract:

```text
paper_data_suite.module_operations
contract version = 1
module_id = vitrine
```

The installed provider exposes two distinct capabilities:

```text
readiness
attention
```

The governing ownership rule is:

```text
suite orchestrates
Core defines neutral interoperability
Vitrine owns Vitrine meaning and state
```

The suite may consume Vitrine's bounded results. It must not inspect or mutate Vitrine
private records to recreate them.

## Release baseline

This integration is developed and qualified against:

| Component | Baseline | Relationship |
| --- | --- | --- |
| PDS Core | 0.6.3 | required runtime and module-operations contract |
| ScoreForm | 0.11.0 | existing producer compatibility anchor only |
| Quillan | 0.10.0 | existing producer compatibility anchor only |
| Concord | 0.3.0 | existing producer compatibility anchor only |
| Meridian | 0.2.0 | sibling module-operations precedent only |
| Paper Data Suite shell | 0.1.0 release line | downstream consumer; no runtime dependency |
| Portia | no required published baseline | no runtime dependency |

Vitrine retains exactly this runtime requirement:

```text
pds-core>=0.6.3,<0.7
```

No ScoreForm, Quillan, Concord, Meridian, Portia, or Paper Data Suite shell runtime
dependency is added by issue #70.

## Provider registration and discovery

The installed distribution registers exactly one module-operations entry point:

```toml
[project.entry-points."paper_data_suite.module_operations"]
vitrine = "vitrine.pds_operations:get_module_operations_profile"
```

The profile identity is exactly:

```text
module_id = vitrine
supported Core operations versions = {1}
```

The existing console script remains:

```text
vitrine = vitrine.cli:main
```

These are separate capabilities. Module-operations provider presence does not establish
launcher membership, suite qualification, or application launchability.

Importing the provider module or asking Core to inspect provider metadata must not:

- resolve or create a workspace;
- initialize Vitrine storage;
- read Portfolio records;
- evaluate attention;
- inspect Snapshot custody;
- read producer artifacts; or
- mutate any state.

Capability evaluation occurs only when Core invokes the selected readiness or attention
provider with an explicit request.

## Readiness contract

Readiness answers one bounded question:

> Can Vitrine safely operate against its own current state in this workspace?

Readiness is workspace-level. It is not a claim about a class, school year, Portfolio,
producer, teacher workload, or Snapshot buildability.

The following distinctions are contractual:

```text
readiness != attention
readiness != launchability
readiness != installation compatibility
readiness != Portfolio existence
readiness != class membership
```

A supplied `class_id` or `active_school_year` is ambient Core context only. Vitrine v1
does not reinterpret either as a readiness filter.

### Missing workspace

When `request.workspace_root is None`, Vitrine returns:

```text
evaluation = unavailable
ready = None
```

The provider does not resolve a saved/default workspace implicitly.

### Empty shared workspace

A valid writable shared workspace with no Vitrine namespace or Portfolio activity is a
normal start state:

```text
evaluation = evaluated
ready = True
```

Readiness does not initialize Vitrine state merely to prove that conclusion.

### Existing Vitrine state

When Vitrine canonical state exists, readiness uses Vitrine-owned storage invariants.
Healthy inspectable state returns `ready=True`.

A positively diagnosed Vitrine-owned blocking condition may return:

```text
evaluation = evaluated
ready = False
```

An inability to evaluate safely remains:

```text
evaluation = unavailable
ready = None
```

A generic read failure must never be converted into `ready=False`.

Readiness is observational. It must not repair, initialize, rewrite, migrate, unlock,
advance, rebuild, or re-export state.

## Attention contract

The Core-facing attention capability is an adapter over the existing issue #69 service:

```text
vitrine_attention_next_actions_v1
```

The semantic authority remains `evaluate_vitrine_attention(...)`. The Core adapter does
not duplicate Candidate currentness, Selection state, Curation Review interpretation,
Working Composition requirements, Snapshot recovery logic, omission logic, or Export
verification.

The mapping preserves native attention:

```text
native code  -> Core summary code unchanged
native label -> Core label unchanged
native count -> Core count when representable
native notice -> Core notice
```

Successful evaluated-empty attention remains distinct from unavailable attention.
Partial native attention remains evaluated and preserves the valid summaries supplied by
issue #69.

## Exact class-scope decision

This decision is frozen for Vitrine/Core operations v1.

When:

```text
request.class_id is None
```

Vitrine evaluates normal workspace-wide attention through issue #69.

When:

```text
request.class_id is not None
```

Vitrine returns:

```text
evaluation = unavailable
summaries = ()
notice = vitrine_attention_class_scope_unsupported
```

The teacher-facing meaning is that Portfolio attention may span classes and cannot be
safely reduced to one requested class. The caller should use unfiltered suite/Vitrine
attention or Vitrine's own Attention / Next Actions view.

The adapter must not run the full workspace attention projection merely to discard it
afterward.

This rule exists because:

```text
Portfolio linked to class != Portfolio attention belongs to class
source work belongs to class != Portfolio-wide obligation belongs to class
```

Portfolio-wide Selection, Curation Review, Working Composition, Snapshot recovery,
omission, and Export facts may not belong to any single linked class.

The following strategies are forbidden:

- ignore the supplied class and return workspace-wide results;
- treat every Portfolio linked to the class as class-owned attention;
- duplicate one Portfolio-wide attention item into every linked class;
- infer attention ownership from one Candidate or source item's class;
- infer class ownership from Portfolio Subject identity; or
- invent a `ModuleWorkRef` merely to satisfy the filter.

`active_school_year` likewise does not fabricate a school-year Portfolio filter.

## Owner-action mapping

Issue #69 actions are Vitrine-local references with:

```text
action_id
portfolio_id
```

Core v1 owner actions contain only:

```text
module_id
action_id
```

Therefore a native action such as:

```text
action_id = open_candidate_review
portfolio_id = portfolio-example
```

maps to:

```text
module_id = vitrine
action_id = open_candidate_review
```

The local `portfolio_id` is deliberately dropped at the Core boundary.

The adapter must not encode Portfolio identity into the action string and must not put
commands, URLs, filesystem paths, imports, menu numbers, credentials, or arbitrary
arguments into `action_id`.

Owner-action references are opaque routing hints. They are not executable commands and
do not confer authorization.

## Doctor and launcher boundary

Vitrine exposes readiness facts. It does not define suite doctor presentation policy.
The shell may later translate neutral Core outcomes into its own PASS/WARN/FAIL/SKIP
presentation, but that translation is not a Vitrine contract.

Likewise, issue #70 does not change launcher membership or routing. The existing
`vitrine` console entry point remains the application launch surface. A valid
module-operations profile does not make an application suite-qualified or launchable by
itself.

## Backup and restore boundary

Issue #70 adds no Vitrine-specific backup hook.

The integration invariant is:

```text
backup copy != Vitrine export
Snapshot Export != suite backup
suite restore != Vitrine repair
byte-for-byte restored workspace != migration or reinterpretation
```

The suite owns opaque whole-workspace byte custody. Vitrine owns all Vitrine canonical
records, copied artifact bytes, Snapshot custody, and Snapshot Export bytes beneath that
workspace.

A byte-for-byte copied workspace must remain usable from a different root. A valid
relocation preserves:

- the complete relative file inventory;
- exact file bytes and SHA-256 digests;
- current and historical canonical Vitrine state;
- Snapshot Edition custody;
- existing Export artifacts;
- readiness semantics;
- issue #69 attention semantics; and
- unresolved Snapshot recovery state.

After relocation, existing sealed Editions and Exports that were verifiable before must
remain verifiable without consulting the old workspace or producer source bytes.

Restore is not repair. It must not clear locks, abandon Attempts, rebuild a Snapshot,
recreate an Export, advance a pointer, clear attention, rewrite canonical records, or
reinterpret recovery state.

## Privacy and failure isolation

Core-facing reports are deliberately low density. They do not expose:

- student names or identifiers;
- student writing;
- Scores, percentages, Grades, or proficiency;
- producer feedback bodies;
- source filenames or private paths;
- Snapshot manifests or Artifact bytes;
- raw exceptions or tracebacks;
- credentials or tokens; or
- recipient information.

A shared failure is represented by bounded Core/Vitrine codes and summaries. Raw domain
records stay behind the Vitrine owner boundary.

## Explicit non-goals

V1 does not implement:

- a suite dashboard;
- suite attention aggregation;
- class-aware Portfolio attention attribution;
- suite doctor PASS/WARN/FAIL/SKIP policy;
- launcher registration or command routing;
- a Vitrine backup API;
- backup repair/migration;
- executable remote actions;
- Grade/proficiency/risk interpretation; or
- new producer support versions.

Those capabilities require their own authority and contracts.
