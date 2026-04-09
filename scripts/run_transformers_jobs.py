#!/usr/bin/env python3
"""Run prompt jobs against a local Hugging Face causal LM via transformers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import evaluate_runs


MODEL_RESPONSE_FIELDS = (
    "task_a_more_morally_problematic",
    "task_b_written_motive_relation",
    "task_b_worse_inward_orientation",
    "task_c_primary_reason",
    "brief_explanation",
)
OPTIONAL_RESPONSE_FIELDS = {"task_b_written_motive_relation"}
REASON_SYNONYMS = {
    "motive": "motive",
    "written_motive": "motive",
    "inward_motivation": "motive",
    "inward motivation": "motive",
    "inward motive": "motive",
    "inward_orientation": "motive",
    "inward orientation": "motive",
    "worse inward orientation": "motive",
    "worse_inward_orientation": "motive",
    "inwardly worse": "motive",
    "worse motive": "motive",
    "intention": "motive",
    "intent": "motive",
    "inner_orientation": "motive",
    "inward_orientation": "motive",
    "inward_act": "motive",
    "heart": "motive",
    "outward_act": "outward_act",
    "act": "outward_act",
    "action": "outward_act",
    "behavior": "outward_act",
    "consequence": "consequence",
    "outcome": "consequence",
    "rule": "rule",
    "rules": "rule",
    "norm": "rule",
    "outlawed_action": "rule",
}
RELATION_SYNONYMS = {
    "same": "same",
    "same_written_motive": "same",
    "same_written_intention": "same",
    "same_intention": "same",
    "same_motive": "same",
    "different": "different",
    "different_written_motive": "different",
    "different_written_intention": "different",
    "different_intention": "different",
    "different_motive": "different",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each row must decode to an object")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def choose_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def choose_dtype(requested: str, device: str) -> torch.dtype:
    if requested == "float32":
        return torch.float32
    if requested == "float16":
        return torch.float16
    if requested == "bfloat16":
        return torch.bfloat16
    if device in {"cuda", "mps"}:
        return torch.float16
    return torch.float32


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def find_json_object(text: str) -> str | None:
    stripped = strip_code_fences(text)
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]
    return None


def parse_response_text(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    candidate = find_json_object(text)
    if candidate is None:
        return None, "no_json_object_found"
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error:{exc}"
    if not isinstance(parsed, dict):
        return None, "decoded_json_not_object"
    cleaned = {
        field: parsed.get(field)
        for field in MODEL_RESPONSE_FIELDS
        if parsed.get(field) is not None or field not in OPTIONAL_RESPONSE_FIELDS
    }
    for field in ("task_a_more_morally_problematic", "task_b_worse_inward_orientation"):
        value = cleaned.get(field)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.lower() == "same":
                cleaned[field] = "Same"
            elif normalized.lower() in {"a", "b"}:
                cleaned[field] = normalized.upper()
    relation = cleaned.get("task_b_written_motive_relation")
    if isinstance(relation, str):
        normalized_relation = RELATION_SYNONYMS.get(relation.strip().lower())
        if normalized_relation is None:
            cleaned.pop("task_b_written_motive_relation", None)
        else:
            cleaned["task_b_written_motive_relation"] = normalized_relation
    reason = cleaned.get("task_c_primary_reason")
    if isinstance(reason, str):
        cleaned["task_c_primary_reason"] = REASON_SYNONYMS.get(reason.strip().lower(), reason.strip().lower())
    explanation = cleaned.get("brief_explanation")
    if isinstance(explanation, str):
        cleaned["brief_explanation"] = explanation.strip()
    if not evaluate_runs.validate_response(cleaned):
        return None, "response_failed_schema_validation"
    return cleaned, None


def render_chat_prompt(tokenizer: AutoTokenizer, prompt: str) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return prompt


def prepare_inputs(tokenizer: AutoTokenizer, prompt: str, device: str) -> Dict[str, torch.Tensor]:
    encoded = tokenizer(prompt, return_tensors="pt")
    return {key: value.to(device) for key, value in encoded.items()}


def generate_once(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    job: Dict[str, Any],
    device: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    prompt_mode: str,
) -> str:
    prompt = job["prompt"]
    if prompt_mode == "chat":
        prompt = render_chat_prompt(tokenizer, prompt)
    inputs = prepare_inputs(tokenizer, prompt, device)
    prompt_length = inputs["input_ids"].shape[1]
    do_sample = temperature > 0.0
    generation_kwargs: Dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.pad_token_id,
    }
    if tokenizer.eos_token_id is not None:
        generation_kwargs["eos_token_id"] = tokenizer.eos_token_id
    if do_sample:
        generation_kwargs["temperature"] = temperature
        generation_kwargs["top_p"] = top_p

    with torch.no_grad():
        output_ids = model.generate(**inputs, **generation_kwargs)
    generated_ids = output_ids[0, prompt_length:]
    text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    if device == "mps":
        torch.mps.empty_cache()
    return text.strip()


def load_completed_job_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {row["job_id"] for row in load_jsonl(path)}


def select_jobs(jobs: Sequence[Dict[str, Any]], limit: int | None) -> List[Dict[str, Any]]:
    if limit is None:
        return list(jobs)
    return list(jobs[:limit])


def model_aliases(config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    return {entry["alias"]: entry for entry in config["models"]}


def default_output_path(config: Dict[str, Any], model_alias: str) -> Path:
    run_dir = Path(config["outputs"]["run_dir"])
    filename = model_alias.lower().replace(".", "_").replace("/", "_").replace("-", "_")
    return run_dir / f"{filename}_pilot_runs_v1.jsonl"


def default_failure_path(config: Dict[str, Any], model_alias: str) -> Path:
    run_dir = Path(config["outputs"]["run_dir"])
    filename = model_alias.lower().replace(".", "_").replace("/", "_").replace("-", "_")
    return run_dir / f"{filename}_pilot_failures_v1.jsonl"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Pilot execution config JSON")
    parser.add_argument("--model-alias", required=True, help="Configured model alias to run")
    parser.add_argument("--jobs", help="Override jobs JSONL path")
    parser.add_argument("--output", help="Run-record JSONL output path")
    parser.add_argument("--failures-output", help="Failure JSONL output path")
    parser.add_argument("--limit", type=int, help="Only run the first N jobs")
    parser.add_argument("--resume", action="store_true", help="Skip job ids already present in the output file")
    parser.add_argument("--device", help="Override device: auto, cpu, cuda, or mps")
    parser.add_argument("--dtype", help="Override dtype: auto, float32, float16, or bfloat16")
    return parser


def main(argv: Sequence[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = load_json(Path(args.config))
    aliases = model_aliases(config)
    if args.model_alias not in aliases:
        raise SystemExit(f"Unknown model alias '{args.model_alias}'. Allowed: {sorted(aliases)}")

    model_entry = aliases[args.model_alias]
    jobs_path = Path(args.jobs) if args.jobs else Path(config["jobs_path"])
    output_path = Path(args.output) if args.output else default_output_path(config, args.model_alias)
    failure_path = (
        Path(args.failures_output) if args.failures_output else default_failure_path(config, args.model_alias)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.parent.mkdir(parents=True, exist_ok=True)

    jobs = select_jobs(load_jsonl(jobs_path), args.limit)
    existing_job_ids = load_completed_job_ids(output_path) if args.resume else set()
    jobs = [job for job in jobs if job["job_id"] not in existing_job_ids]

    if not jobs:
        print("No jobs to run.")
        return 0

    inference = config["inference"]
    device = choose_device(args.device or inference.get("device", "auto"))
    dtype = choose_dtype(args.dtype or inference.get("dtype", "auto"), device)
    hf_model_id = model_entry["hf_model_id"]

    print(f"Loading {args.model_alias} from {hf_model_id} on {device} with dtype={dtype}")
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(hf_model_id, dtype=dtype)
    model.to(device)
    model.eval()

    max_attempts = int(inference.get("max_attempts", 2))
    prompt_mode = inference.get("prompt_mode", "chat")
    max_new_tokens = int(inference["max_new_tokens"])
    temperature = float(inference["temperature"])
    top_p = float(inference["top_p"])

    if not args.resume:
        output_path.write_text("", encoding="utf-8")
        failure_path.write_text("", encoding="utf-8")

    success_count = len(existing_job_ids) if args.resume else 0
    failure_count = 0

    for index, job in enumerate(jobs, start=1):
        raw_outputs: List[str] = []
        parsed_response: Dict[str, Any] | None = None
        last_error: str | None = None
        print(f"[{index}/{len(jobs)}] {job['job_id']}")
        for attempt in range(1, max_attempts + 1):
            raw_text = generate_once(
                model=model,
                tokenizer=tokenizer,
                job=job,
                device=device,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                prompt_mode=prompt_mode,
            )
            raw_outputs.append(raw_text)
            parsed_response, last_error = parse_response_text(raw_text)
            if parsed_response is not None:
                break
            print(f"  attempt {attempt} failed: {last_error}")

        if parsed_response is None:
            append_jsonl(
                failure_path,
                {
                    "job_id": job["job_id"],
                    "item_id": job["item_id"],
                    "model": args.model_alias,
                    "condition": job["condition"],
                    "error": last_error,
                    "raw_outputs": raw_outputs,
                },
            )
            failure_count += 1
            continue

        append_jsonl(
            output_path,
            {
                "job_id": job["job_id"],
                "item_id": job["item_id"],
                "model": args.model_alias,
                "condition": job["condition"],
                "benchmark_source": job["benchmark_source"],
                "pair_type": job["pair_type"],
                "primary_diagnostic_dimension": job["primary_diagnostic_dimension"],
                "swapped": job["swapped"],
                "gold": job["gold"],
                "response": parsed_response,
            },
        )
        success_count += 1

    print(f"Wrote {success_count} successful run records to {output_path}")
    print(f"Wrote {failure_count} failures to {failure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
