# Producer Adapter Development Fixtures

These files are synthetic Vitrine development inputs for issue #32.

They are **not** ScoreForm, Quillan, or Concord publications and do not establish
installed producer integration. Their contract identities are Vitrine fixture
identities, and execution requires explicit use of the development fixture
registry.

The fixture readers accept the exact canonical bytes of these JSON files. They do
not receive paths, discover workspaces, import sibling packages, or open producer
native records.
