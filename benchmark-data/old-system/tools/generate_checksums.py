#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for a dataset directory."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


IGNORED_PARTS = {".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", ".venv", "venv"}
MUTABLE_TOP_LEVEL = {"old-system", "ocr-results", "benchmark-results", "predictions"}


def included(path: Path, root: Path, output: Path) -> bool:
    relative = path.relative_to(root)
    return (
        path.is_file()
        and path.resolve() != output.resolve()
        and not any(part in IGNORED_PARTS for part in path.parts)
        and (not relative.parts or relative.parts[0] not in MUTABLE_TOP_LEVEL)
        and path.suffix not in {".pyc", ".pyo"}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("checksums.sha256"))
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    paths = sorted(path for path in root.rglob("*") if included(path, root, output))
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}" for path in paths]
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Wrote {len(lines)} checksums to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
