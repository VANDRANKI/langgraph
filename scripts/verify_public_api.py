#!/usr/bin/env python3
"""Verify that public packages in each library can be imported.

Walks every libs/<library>/src directory, finds Python packages
(directories with __init__.py), imports each one, and reports failures.

Usage:
    python scripts/verify_public_api.py
    python scripts/verify_public_api.py libs/langgraph
    python scripts/verify_public_api.py --fail-fast
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

LIBS_ROOT = Path("libs")


def collect_packages(src_dir: Path) -> list[str]:
    """Return importable package names found under src_dir."""
    packages: list[str] = []
    for init in sorted(src_dir.rglob("__init__.py")):
        parts = init.parent.relative_to(src_dir).parts
        # Skip private, test, and generated packages.
        if any(p.startswith(("_", "test")) for p in parts):
            continue
        module = ".".join(parts)
        if module:
            packages.append(module)
    return packages


def verify_library(lib_dir: Path, fail_fast: bool = False) -> dict[str, str]:
    """Import all public packages in lib_dir and return {module: error} for failures."""
    src_dir = lib_dir / "src"
    if not src_dir.exists():
        return {}

    sys.path.insert(0, str(src_dir))
    errors: dict[str, str] = {}
    try:
        for package in collect_packages(src_dir):
            try:
                importlib.import_module(package)
            except Exception as exc:  # noqa: BLE001
                errors[package] = str(exc)
                if fail_fast:
                    return errors
    finally:
        sys.path.remove(str(src_dir))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "libraries", nargs="*", type=Path,
        help="Library paths to check (default: all under libs/)",
    )
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Stop after first import error per library",
    )
    args = parser.parse_args(argv)

    if args.libraries:
        lib_dirs = [Path(p) for p in args.libraries]
    else:
        if not LIBS_ROOT.exists():
            print(f"ERROR: {LIBS_ROOT} not found.", file=sys.stderr)
            return 1
        lib_dirs = sorted(d for d in LIBS_ROOT.iterdir() if d.is_dir())

    total_errors: dict[str, dict[str, str]] = {}
    for lib_dir in lib_dirs:
        errors = verify_library(lib_dir, fail_fast=args.fail_fast)
        if errors:
            total_errors[lib_dir.name] = errors

    if total_errors:
        for lib_name, errors in total_errors.items():
            for module, err in errors.items():
                print(f"FAIL  {lib_name}/{module}: {err}")
        return 1

    checked = len(lib_dirs)
    print(f"All public packages in {checked} librar{'y' if checked == 1 else 'ies'} import successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
