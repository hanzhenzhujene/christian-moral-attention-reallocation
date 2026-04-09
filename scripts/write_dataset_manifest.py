#!/usr/bin/env python3
"""Write a lightweight manifest with file hashes to freeze dataset versions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_entry(path: Path) -> Dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path),
        "bytes": stat.st_size,
        "sha256": sha256_for_path(path),
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Files to include in the manifest")
    parser.add_argument("--output", required=True, help="Manifest JSON path")
    args = parser.parse_args(argv)

    entries: List[Dict[str, object]] = [manifest_entry(Path(raw_path)) for raw_path in args.paths]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote manifest with {len(entries)} entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
