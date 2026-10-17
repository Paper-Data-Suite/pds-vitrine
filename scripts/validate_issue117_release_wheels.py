"""Issue #117: verify exact published input-wheel identities for Vitrine v0.4.0.

Default mode checks a *static* qualification inventory, not downloaded bytes.
--wheel-dir independently authenticates local official GitHub Release wheel bytes.
Neither mode changes Vitrine's runtime producer compatibility policy.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path

from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACTS,
    ReleasedCoreAudit,
    ReleasedProducerContractAudit,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CORE_REQUIREMENT = "pds-core>=0.6.6,<0.7"

# Qualified Core #232 release record. The original Core 0.6.5 audit remains
# immutable in vitrine.released_producer_contracts and Slice 6 baseline evidence.
CORE_0_6_6_AUDIT = ReleasedCoreAudit(
    distribution_name="pds-core",
    release_version="0.6.6",
    release_tag="v0.6.6",
    wheel_filename="pds_core-0.6.6-py3-none-any.whl",
    wheel_sha256=(
        "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301"
    ),
    requires_python=">=3.11",
)


@dataclass(frozen=True, slots=True)
class QualifiedWheel:
    distribution: str
    version: str
    repository: str
    filename: str
    sha256: str

    @property
    def url(self) -> str:
        return (
            f"https://github.com/Paper-Data-Suite/{self.repository}/releases/"
            f"download/v{self.version}/{self.filename}"
        )


# The values below are exact qualification inputs, NEVER runtime allowlists.
# Core 0.6.6 is newly authenticated; producer identities retain #103 audits.
EXPECTED_WHEELS: tuple[QualifiedWheel, ...] = (
    QualifiedWheel(
        "pds-core",
        "0.6.6",
        "pds-core",
        "pds_core-0.6.6-py3-none-any.whl",
        "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301",
    ),
    QualifiedWheel(
        "scoreform",
        "0.13.0",
        "pds-scoreform",
        "scoreform-0.13.0-py3-none-any.whl",
        "4a4d158fda6e899f1835f3312ca8291622e2b1c7da219b349adf5e88b9b7c9b7",
    ),
    QualifiedWheel(
        "quillan",
        "0.10.6",
        "pds-quillan",
        "quillan-0.10.6-py3-none-any.whl",
        "7dbe975c969e60cfda9a8489154450f95c4dc58a8d75afcfad92e7a3c026afbb",
    ),
    QualifiedWheel(
        "pds-concord",
        "0.3.2",
        "pds-concord",
        "pds_concord-0.3.2-py3-none-any.whl",
        "825b27bc6142cc8bce8c3b9381a3337c4a55e983f6f3f2e7e4b1a10f980e83ce",
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_inventory(
    specs: tuple[QualifiedWheel, ...] = EXPECTED_WHEELS,
    *,
    root: Path = ROOT,
) -> tuple[str, ...]:
    """Reject stale or inconsistent source/docs qualification anchors."""
    findings: list[str] = []
    audits: tuple[ReleasedCoreAudit | ReleasedProducerContractAudit, ...] = (
        CORE_0_6_6_AUDIT,
        *RELEASED_PRODUCER_CONTRACTS,
    )
    by_distribution = {audit.distribution_name: audit for audit in audits}
    if len(specs) != 4 or len(by_distribution) != 4:
        findings.append(
            "current producer/Core qualification set must contain four wheels"
        )
    if len({spec.distribution for spec in specs}) != len(specs):
        findings.append("duplicate distribution in release wheel inventory")
    if {spec.distribution for spec in specs} != set(by_distribution):
        findings.append("release wheel inventory diverged from #103 active audits")
    for spec in specs:
        audit = by_distribution.get(spec.distribution)
        if audit is None:
            continue
        if (spec.version, spec.filename, spec.sha256) != (
            audit.release_version,
            audit.wheel_filename,
            audit.wheel_sha256,
        ):
            findings.append(f"release wheel audit drift: {spec.distribution}")
        if re.fullmatch(r"[0-9a-f]{64}", spec.sha256) is None:
            findings.append(f"invalid expected SHA-256: {spec.distribution}")
        if spec.repository not in {
            "pds-core",
            "pds-scoreform",
            "pds-quillan",
            "pds-concord",
        }:
            findings.append(f"unexpected release repository: {spec.distribution}")
        if audit.release_tag != f"v{spec.version}":
            findings.append(f"release tag/version drift: {spec.distribution}")
        if spec.filename != (
            spec.distribution.replace("-", "_")
            + f"-{spec.version}-py3-none-any.whl"
        ):
            findings.append(
                f"release wheel filename/version drift: {spec.distribution}"
            )
    try:
        source_version = (root / "vitrine/_version.py").read_text(encoding="utf-8")
        if '__version__ = "0.4.0"' not in source_version:
            findings.append("Vitrine candidate version is not 0.4.0")
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        if f'"{EXPECTED_CORE_REQUIREMENT}"' not in pyproject:
            findings.append("Vitrine Core-only requirement changed")
        matrix = (root / "docs/v0.4.0-release-compatibility.md").read_text(
            encoding="utf-8"
        )
        for spec in specs:
            if spec.filename not in matrix or spec.sha256 not in matrix:
                findings.append(
                    f"v0.4.0 matrix missing expected {spec.distribution} wheel"
                )
        if "Pending authentication" not in matrix:
            findings.append("current matrix prematurely removed pending verification")
    except OSError as exc:
        findings.append(f"cannot inspect release identity/matrix: {exc}")
    return tuple(findings)


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def authenticate_wheel(path: Path, spec: QualifiedWheel) -> str:
    """Verify local wheel bytes, ZIP integrity and embedded distribution identity."""
    if path.name != spec.filename:
        raise RuntimeError(
            f"wrong wheel filename for {spec.distribution}: {path.name}"
        )
    if not path.is_file():
        raise RuntimeError(f"missing official release wheel: {path}")
    actual = _sha256(path)
    if actual != spec.sha256:
        raise RuntimeError(
            f"SHA-256 mismatch for {spec.filename}: "
            f"expected {spec.sha256}; got {actual}"
        )
    try:
        with zipfile.ZipFile(path) as wheel:
            bad_member = wheel.testzip()
            if bad_member is not None:
                raise RuntimeError(f"corrupt wheel member: {bad_member}")
            metadata_paths = [
                name
                for name in wheel.namelist()
                if len(name.split("/")) == 2
                and name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_paths) != 1:
                raise RuntimeError(
                    f"expected exactly one dist-info METADATA in {spec.filename}"
                )
            metadata = BytesParser().parsebytes(wheel.read(metadata_paths[0]))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"not a readable wheel: {spec.filename}") from exc
    name = metadata.get("Name", "")
    if _canonical_name(name) != _canonical_name(spec.distribution):
        raise RuntimeError(
            f"wheel distribution mismatch: {name!r} != {spec.distribution!r}"
        )
    if metadata.get("Version") != spec.version:
        raise RuntimeError(
            f"wheel metadata version mismatch: {metadata.get('Version')!r}"
        )
    if metadata.get("Requires-Python") != ">=3.11":
        raise RuntimeError(
            f"wheel Python requirement mismatch: {metadata.get('Requires-Python')!r}"
        )
    return actual


def authenticate_wheelhouse(
    wheel_dir: Path,
    specs: tuple[QualifiedWheel, ...] = EXPECTED_WHEELS,
) -> tuple[str, ...]:
    """Authenticate four official input wheels, without fetching or installing."""
    verified: list[str] = []
    for spec in specs:
        path = wheel_dir / spec.filename
        actual = authenticate_wheel(path, spec)
        verified.append(f"{spec.distribution}=={spec.version}: {actual}")
    return tuple(verified)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel-dir",
        type=Path,
        help="directory holding the four official GitHub Release input wheels",
    )
    args = parser.parse_args(argv)
    findings = validate_inventory()
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS issue #117 static release input-wheel identity inventory")
    if args.wheel_dir is None:
        print("NOTE downloaded wheel bytes NOT authenticated (supply --wheel-dir)")
        return 0
    try:
        for verified in authenticate_wheelhouse(args.wheel_dir.expanduser().resolve()):
            print("PASS authenticated", verified)
    except (OSError, RuntimeError) as exc:
        print(f"Issue #117 wheel authentication failed: {exc}", file=sys.stderr)
        return 1
    print("PASS issue #117 exact official input-wheel authentication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
