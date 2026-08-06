# Security and Student Data

Vitrine is pre-1.0 local-first educational software. It is not a hosted service,
a legal-compliance certification, or a production authorization system.

## Student data

Do not commit, publish, or attach real student names, identifiers, work, scores,
feedback, signatures, disability information, disciplinary information, or other
education records to this repository. Tests and examples must use synthetic data.

The package baseline only manages the shared Core workspace. It does not open
producer manifests or student work. Later features must enforce authorization
before accessing protected records and must preserve the no-leakage boundaries in
accepted Vitrine ADRs 0005 and 0008.

## Reporting concerns

Report suspected vulnerabilities privately to the repository maintainer. Do not
include real records, credentials, access tokens, local configuration files, or
absolute workstation paths in a public report.
