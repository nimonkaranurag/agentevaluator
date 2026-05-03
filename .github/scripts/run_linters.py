#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6"]
# ///
"""
Run every linter declared in config/linter.yaml against every declared target and aggregate the exit codes; exits 0 on a clean run, 1 when any linter fails, 2 on a missing or malformed config.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class _LinterSpec:
    name: str
    check_command: tuple[str, ...]


@dataclass(frozen=True)
class _LinterPolicy:
    linters: tuple[_LinterSpec, ...]
    targets: tuple[Path, ...]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_linters",
        description=(
            "Execute every linter declared in the "
            "policy YAML against every declared target."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/linter.yaml"),
        help=(
            "Path to the linter policy YAML "
            "(default: config/linter.yaml)."
        ),
    )
    return parser.parse_args(argv)


def _load_policy(config_path: Path) -> _LinterPolicy:
    if not config_path.is_file():
        raise FileNotFoundError(
            f"linter config not found at "
            f"{config_path}; either pass --config or "
            f"create the file."
        )
    raw: Any = yaml.safe_load(
        config_path.read_text(encoding="utf-8")
    )
    if not isinstance(raw, dict):
        raise ValueError(
            f"{config_path}: expected a YAML mapping at "
            f"the top level."
        )
    linters_raw = raw.get("linters")
    targets_raw = raw.get("targets")
    if not isinstance(linters_raw, list) or not linters_raw:
        raise ValueError(
            f"{config_path}: 'linters' must be a "
            f"non-empty list."
        )
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ValueError(
            f"{config_path}: 'targets' must be a "
            f"non-empty list."
        )
    linters: list[_LinterSpec] = []
    for index, entry in enumerate(linters_raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"{config_path}: linters[{index}] must "
                f"be a mapping."
            )
        name = entry.get("name")
        check_command = entry.get("check_command")
        if not isinstance(name, str) or not name:
            raise ValueError(
                f"{config_path}: linters[{index}].name "
                f"must be a non-empty string."
            )
        if not isinstance(check_command, list) or not all(
            isinstance(item, str) and item
            for item in check_command
        ):
            raise ValueError(
                f"{config_path}: "
                f"linters[{index}].check_command must be "
                f"a non-empty list of non-empty strings."
            )
        linters.append(
            _LinterSpec(
                name=name,
                check_command=tuple(check_command),
            )
        )
    targets: list[Path] = []
    for index, entry in enumerate(targets_raw):
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{config_path}: targets[{index}] must "
                f"be a non-empty string."
            )
        path = Path(entry)
        if not path.exists():
            raise ValueError(
                f"{config_path}: targets[{index}]="
                f"{entry!r} does not exist on disk; "
                f"either remove the entry or create the "
                f"path."
            )
        targets.append(path)
    return _LinterPolicy(
        linters=tuple(linters),
        targets=tuple(targets),
    )


def _run_linter(
    spec: _LinterSpec, targets: tuple[Path, ...]
) -> int:
    print(f"\n::group::{spec.name}", flush=True)
    print(
        f"$ {' '.join(spec.check_command)} "
        f"{' '.join(str(t) for t in targets)}",
        flush=True,
    )
    completed = subprocess.run(
        [*spec.check_command, *(str(t) for t in targets)],
        check=False,
    )
    print("::endgroup::", flush=True)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        policy = _load_policy(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for spec in policy.linters:
        exit_code = _run_linter(spec, policy.targets)
        if exit_code != 0:
            failures.append(spec.name)

    print("\n=== linter summary ===")
    for spec in policy.linters:
        status = "FAIL" if spec.name in failures else "PASS"
        print(f"  {status}  {spec.name}")
    if failures:
        print(
            f"\n::error::{len(failures)} linter(s) "
            f"failed: {', '.join(failures)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
