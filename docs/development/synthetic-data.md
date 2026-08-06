# Synthetic Data Policy

All Vitrine tests, examples, smoke tests, and fixtures must use synthetic data.

Do not commit:

- real student names or identifiers;
- real student work, scores, feedback, or signatures;
- real class rosters;
- disability, disciplinary, counseling, or intervention information;
- credentials, tokens, private configuration, or absolute developer paths;
- restricted agency forms or real regulated submissions.

The representative Portfolio corpus is intentionally synthetic. Package tests may
copy or inspect those committed synthetic bytes only when the tested issue owns
that behavior. This package-baseline issue does not open producer data.

Diagnostics should report bounded structural information and must not print
arbitrary file contents or environment secrets.
