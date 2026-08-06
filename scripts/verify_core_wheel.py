"""Authenticate the exact released pds-core v0.6.0 wheel and installation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

CORE_DISTRIBUTION_NAME = "pds-core"
CORE_IMPORT_NAME = "pds_core"
EXPECTED_CORE_VERSION = "0.6.0"
EXPECTED_CORE_WHEEL_FILENAME = "pds_core-0.6.0-py3-none-any.whl"
EXPECTED_CORE_WHEEL_SHA256 = (
    "be28c061b38463ef59ebc328ed1aa443767fe7f2c626babb769c2d8e5932f308"
)


class CoreVerificationError(ValueError):
    """Raised when a Core artifact or installation is not authoritative."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_core_wheel(path: str | Path) -> None:
    """Verify the exact filename, bytes, ZIP structure, and wheel metadata."""
    wheel = Path(path)
    if wheel.name != EXPECTED_CORE_WHEEL_FILENAME:
        raise CoreVerificationError(
            f"Expected {EXPECTED_CORE_WHEEL_FILENAME!r}, got {wheel.name!r}."
        )
    if not wheel.is_file():
        raise CoreVerificationError(f"Core wheel does not exist: {wheel}")
    actual_digest = _sha256(wheel)
    if actual_digest != EXPECTED_CORE_WHEEL_SHA256:
        raise CoreVerificationError(
            f"Core wheel SHA-256 mismatch: expected {EXPECTED_CORE_WHEEL_SHA256}, "
            f"got {actual_digest}."
        )
    try:
        with zipfile.ZipFile(wheel) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise CoreVerificationError(
                    f"Core wheel has a corrupt ZIP member: {corrupt_member}"
                )
            metadata_names = [
                name
                for name in archive.namelist()
                if len(Path(name).parts) == 2
                and Path(name).parts[0].endswith(".dist-info")
                and Path(name).name == "METADATA"
            ]
            if len(metadata_names) != 1:
                raise CoreVerificationError(
                    "Core wheel must contain exactly one top-level METADATA file."
                )
            metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
    except zipfile.BadZipFile as error:
        raise CoreVerificationError(
            "Core wheel is not a readable ZIP archive."
        ) from error
    if metadata["Name"] != CORE_DISTRIBUTION_NAME:
        raise CoreVerificationError("Core wheel distribution name is not pds-core.")
    if metadata["Version"] != EXPECTED_CORE_VERSION:
        raise CoreVerificationError("Core wheel version is not exactly 0.6.0.")


def verify_installed_core() -> None:
    """Verify installed metadata and the imported package in this environment."""
    version = importlib.metadata.version(CORE_DISTRIBUTION_NAME)
    if version != EXPECTED_CORE_VERSION:
        raise CoreVerificationError(
            f"Installed pds-core must be exactly 0.6.0; found {version}."
        )
    import pds_core

    missing_version = object()
    imported_version = getattr(pds_core, "__version__", missing_version)
    if imported_version is missing_version:
        raise CoreVerificationError("Imported pds_core.__version__ is missing.")
    if not isinstance(imported_version, str):
        raise CoreVerificationError("Imported pds_core.__version__ must be a string.")
    if imported_version != version:
        raise CoreVerificationError(
            "Imported pds_core.__version__ disagrees with installed distribution "
            f"metadata: {imported_version!r} != {version!r}."
        )
    if pds_core.__file__ is None:
        raise CoreVerificationError("pds_core does not resolve to a package file.")
    imported = Path(pds_core.__file__).resolve()
    environment = Path(sys.prefix).resolve()
    if not imported.is_relative_to(environment):
        raise CoreVerificationError(
            f"pds_core is shadowed outside the active environment: {imported}"
        )
    distribution = importlib.metadata.distribution(CORE_DISTRIBUTION_NAME)
    metadata_package = Path(str(distribution.locate_file(CORE_IMPORT_NAME))).resolve()
    if imported.parent != metadata_package:
        raise CoreVerificationError(
            "Installed pds-core metadata and imported pds_core package disagree."
        )


def main(argv: list[str] | None = None) -> int:
    """Run artifact verification or installed-distribution verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args(argv)
    if args.wheel is None and not args.installed:
        parser.error("provide a wheel path, --installed, or both")
    try:
        if args.wheel is not None:
            verify_core_wheel(args.wheel)
        if args.installed:
            verify_installed_core()
    except (
        CoreVerificationError,
        OSError,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        print(f"Core verification failed: {exc}", file=sys.stderr)
        return 1
    print("PASS Core v0.6.0 verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
