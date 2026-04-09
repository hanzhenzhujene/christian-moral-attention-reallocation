#!/usr/bin/env python3
"""Write a file-hash manifest for the frozen pilot package."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(path_str: str) -> Path:
    return Path(path_str).expanduser().resolve()


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-config", required=True, help="Pilot execution config JSON")
    parser.add_argument("--study-config", required=True, help="Study config JSON")
    parser.add_argument("--benchmark", required=True, help="Frozen pilot benchmark JSON")
    parser.add_argument("--jobs", required=True, help="Frozen pilot jobs JSONL")
    parser.add_argument("--run-schema", required=True, help="Run-record schema JSON")
    parser.add_argument("--response-schema", required=True, help="Model-response schema JSON")
    parser.add_argument("--output", required=True, help="Output manifest path")
    args = parser.parse_args(argv)

    execution_config = resolve(args.execution_config)
    study_config = resolve(args.study_config)
    benchmark = resolve(args.benchmark)
    jobs = resolve(args.jobs)
    run_schema = resolve(args.run_schema)
    response_schema = resolve(args.response_schema)

    exec_payload: Dict[str, Any] = json.loads(execution_config.read_text(encoding="utf-8"))
    prompt_paths = sorted(
        {
            str(resolve(job["prompt_template_path"]))
            for job in (
                json.loads(line)
                for line in jobs.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
    )
    if exec_payload.get("prompt_dir"):
        prompt_dir = resolve(exec_payload["prompt_dir"])
        prompt_paths.extend(
            str(path.resolve())
            for path in sorted(prompt_dir.glob("*.txt"))
        )
        prompt_paths = sorted(set(prompt_paths))
    file_paths = [
        execution_config,
        study_config,
        benchmark,
        jobs,
        run_schema,
        response_schema,
        *[Path(path) for path in prompt_paths],
    ]

    manifest = {
        "name": exec_payload["name"],
        "models": exec_payload["models"],
        "inference": exec_payload["inference"],
        "frozen_files": [
            {"path": str(path), "sha256": sha256(path)}
            for path in file_paths
        ],
    }

    output_path = resolve(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote freeze manifest to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
