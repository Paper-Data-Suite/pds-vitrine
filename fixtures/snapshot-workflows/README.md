# Snapshot workflow development fixtures

These synthetic bytes exercise issue #35 only. They are Vitrine-owned
development fixtures, not live ScoreForm or Quillan integration and not a
producer-private storage contract.

`source-root/artifacts/` mirrors only the three explicitly approved Quillan-shaped
fixture locators used by the Snapshot source-provider boundary. `structured/`
contains one bounded ScoreForm-shaped structured attempt input used by an
explicit deterministic fixture renderer. `expected/` contains deterministic
renderer outputs checked by the Snapshot workflow validator.

`fixture-index.json` records the exact SHA-256 and byte size of every committed
fixture payload. No student names, private teacher notes, answer keys, scans,
detector data, credentials, or recipient authorization data are present.
