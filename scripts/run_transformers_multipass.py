#!/usr/bin/env python3
"""Run a multi-pass Task B diagnostic against a local Hugging Face causal LM."""

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
import run_transformers_jobs as single_pass


TASK_AC_FILENAMES = {
    "baseline": "task_ac_baseline_prompt.txt",
    "christian_heart": "task_ac_christian_heart_prompt.txt",
    "secular_matched": "task_ac_secular_matched_prompt.txt",
}
TASK_B_FILENAMES = {
    "baseline": "task_b_baseline_prompt.txt",
    "christian_heart": "task_b_christian_heart_prompt.txt",
    "secular_matched": "task_b_secular_matched_prompt.txt",
}
COPY_FILENAME = "copy_intentions_prompt.txt"
RELATION_FILENAME = "relation_prompt.txt"
AB_ONLY = {"A", "B"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def rewrite_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_benchmark_items(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON list")
    return {item["item_id"]: item for item in payload}


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_template(template: str, replacements: Dict[str, str]) -> str:
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def normalize_ab_same(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.lower() == "same":
        return "Same"
    if value.lower() in {"a", "b"}:
        return value.upper()
    return None


def normalize_reason(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return single_pass.REASON_SYNONYMS.get(value.strip().lower(), value.strip().lower())


def normalize_relation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return single_pass.RELATION_SYNONYMS.get(value.strip().lower())


def parse_json_object(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    stripped = single_pass.strip_code_fences(text)
    start = stripped.find("{")
    if start == -1:
        return None, "no_json_object_found"
    candidate = None
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
                candidate = stripped[start : index + 1]
                break
    if candidate is None:
        return None, "no_json_object_found"
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"json_decode_error:{exc}"
    if not isinstance(parsed, dict):
        return None, "decoded_json_not_object"
    return parsed, None


def parse_task_ac_response(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    parsed, error = parse_json_object(text)
    if parsed is None:
        return None, error
    response = {
        "task_a_more_morally_problematic": normalize_ab_same(parsed.get("task_a_more_morally_problematic")),
        "task_c_primary_reason": normalize_reason(parsed.get("task_c_primary_reason")),
        "brief_explanation": (parsed.get("brief_explanation") or parsed.get("brief explanation") or "").strip(),
    }
    if response["task_a_more_morally_problematic"] not in evaluate_runs.AB_SAME:
        return None, "invalid_task_a_label"
    if response["task_c_primary_reason"] not in evaluate_runs.REASON_LABELS:
        return None, "invalid_task_c_label"
    if not response["brief_explanation"]:
        return None, "empty_brief_explanation"
    return response, None


def parse_copy_response(text: str) -> Tuple[Dict[str, str] | None, str | None]:
    parsed, error = parse_json_object(text)
    if parsed is None:
        return None, error
    copy_a = parsed.get("case_a_written_intention_copy")
    copy_b = parsed.get("case_b_written_intention_copy")
    if not isinstance(copy_a, str) or not copy_a.strip():
        return None, "invalid_case_a_written_intention_copy"
    if not isinstance(copy_b, str) or not copy_b.strip():
        return None, "invalid_case_b_written_intention_copy"
    return {
        "case_a_written_intention_copy": copy_a.strip(),
        "case_b_written_intention_copy": copy_b.strip(),
    }, None


def parse_relation_response(text: str) -> Tuple[str | None, str | None]:
    parsed, error = parse_json_object(text)
    if parsed is None:
        return None, error
    relation = normalize_relation(parsed.get("task_b_written_motive_relation"))
    if relation not in {"same", "different"}:
        return None, "invalid_task_b_written_motive_relation"
    return relation, None


def parse_task_b_response(text: str) -> Tuple[str | None, str | None]:
    parsed, error = parse_json_object(text)
    if parsed is None:
        return None, error
    label = normalize_ab_same(parsed.get("task_b_worse_inward_orientation"))
    if label not in AB_ONLY:
        return None, "invalid_task_b_worse_inward_orientation"
    return label, None


def normalize_intention_copy(text: str) -> str:
    text = text.strip().strip("\"'`")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def pass_expected_relation(job: Dict[str, Any]) -> str:
    return "same" if job["gold"]["task_b_worse_inward_orientation"] == "Same" else "different"


def presented_cases(job: Dict[str, Any], item: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    source_a = job.get("presented_case_a_source") or ("case_b" if job.get("swapped") else "case_a")
    source_b = job.get("presented_case_b_source") or ("case_a" if job.get("swapped") else "case_b")
    return item[source_a], item[source_b]


def prompt_replacements(case_a: Dict[str, Any], case_b: Dict[str, Any]) -> Dict[str, str]:
    return {
        "{{case_a}}": case_a["text"],
        "{{case_b}}": case_b["text"],
        "{{case_a_motive_summary}}": case_a["motive_summary"],
        "{{case_b_motive_summary}}": case_b["motive_summary"],
        "{{case_a_outward_act_summary}}": case_a["outward_act_summary"],
        "{{case_b_outward_act_summary}}": case_b["outward_act_summary"],
        "{{case_a_consequence_summary}}": case_a["consequence_summary"],
        "{{case_b_consequence_summary}}": case_b["consequence_summary"],
        "{{case_a_rule_summary}}": case_a["rule_summary"],
        "{{case_b_rule_summary}}": case_b["rule_summary"],
        "{{case_a_written_intention_copy}}": "",
        "{{case_b_written_intention_copy}}": "",
    }


def generate_prompt_text(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    device: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    prompt_mode: str,
) -> str:
    if prompt_mode == "chat":
        prompt = single_pass.render_chat_prompt(tokenizer, prompt)
    inputs = single_pass.prepare_inputs(tokenizer, prompt, device)
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
    text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    if device == "mps":
        torch.mps.empty_cache()
    return text


def generate_and_parse(
    prompt: str,
    parser_fn,
    *,
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    device: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    prompt_mode: str,
    max_attempts: int,
) -> Tuple[Any | None, List[str], str | None]:
    raw_outputs: List[str] = []
    parsed_value: Any | None = None
    last_error: str | None = None
    for _ in range(max_attempts):
        raw_text = generate_prompt_text(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            device=device,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            prompt_mode=prompt_mode,
        )
        raw_outputs.append(raw_text)
        parsed_value, last_error = parser_fn(raw_text)
        if parsed_value is not None:
            break
    return parsed_value, raw_outputs, last_error


def default_output_path(config: Dict[str, Any], model_alias: str) -> Path:
    run_dir = Path(config["outputs"]["run_dir"])
    filename = model_alias.lower().replace(".", "_").replace("/", "_").replace("-", "_")
    return run_dir / f"{filename}_{config_name_suffix(config)}_runs.jsonl"


def default_failure_path(config: Dict[str, Any], model_alias: str) -> Path:
    run_dir = Path(config["outputs"]["run_dir"])
    filename = model_alias.lower().replace(".", "_").replace("/", "_").replace("-", "_")
    return run_dir / f"{filename}_{config_name_suffix(config)}_failures.jsonl"


def default_trace_path(config: Dict[str, Any], model_alias: str) -> Path:
    run_dir = Path(config["outputs"]["run_dir"])
    filename = model_alias.lower().replace(".", "_").replace("/", "_").replace("-", "_")
    return run_dir / f"{filename}_{config_name_suffix(config)}_trace.jsonl"


def config_name_suffix(config: Dict[str, Any]) -> str:
    raw_name = str(config.get("name", "multipass"))
    match = re.search(r"(v\d+)$", raw_name)
    if match:
        return f"pilot_{match.group(1)}"
    normalized = re.sub(r"[^a-z0-9]+", "_", raw_name.lower()).strip("_")
    return normalized or "multipass"


def cleanup_failure_file(output_path: Path, failure_path: Path) -> None:
    if not output_path.exists() or not failure_path.exists():
        return
    successful_job_ids = {row["job_id"] for row in single_pass.load_jsonl(output_path)}
    cleaned_rows: List[Dict[str, Any]] = []
    seen_keys: set[Tuple[str, str]] = set()
    for row in single_pass.load_jsonl(failure_path):
        job_id = row.get("job_id")
        error = row.get("error", "")
        if job_id in successful_job_ids:
            continue
        key = (str(job_id), str(error))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        cleaned_rows.append(row)
    rewrite_jsonl(failure_path, cleaned_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Pilot execution config JSON")
    parser.add_argument("--model-alias", required=True, help="Configured model alias to run")
    parser.add_argument("--jobs", help="Override jobs JSONL path")
    parser.add_argument("--output", help="Run-record JSONL output path")
    parser.add_argument("--failures-output", help="Failure JSONL output path")
    parser.add_argument("--trace-output", help="Trace JSONL output path")
    parser.add_argument("--limit", type=int, help="Only run the first N jobs")
    parser.add_argument("--resume", action="store_true", help="Skip job ids already present in the output file")
    parser.add_argument("--device", help="Override device: auto, cpu, cuda, or mps")
    parser.add_argument("--dtype", help="Override dtype: auto, float32, float16, or bfloat16")
    return parser


def main(argv: Sequence[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = load_json(Path(args.config))
    aliases = single_pass.model_aliases(config)
    if args.model_alias not in aliases:
        raise SystemExit(f"Unknown model alias '{args.model_alias}'. Allowed: {sorted(aliases)}")

    prompt_dir = Path(config["prompt_dir"])
    benchmark_items = load_benchmark_items(Path(config["benchmark_path"]))
    jobs_path = Path(args.jobs) if args.jobs else Path(config["jobs_path"])
    output_path = Path(args.output) if args.output else default_output_path(config, args.model_alias)
    failure_path = Path(args.failures_output) if args.failures_output else default_failure_path(config, args.model_alias)
    trace_path = Path(args.trace_output) if args.trace_output else default_trace_path(config, args.model_alias)
    for path in (output_path, failure_path, trace_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    jobs = single_pass.select_jobs(single_pass.load_jsonl(jobs_path), args.limit)
    existing_job_ids = single_pass.load_completed_job_ids(output_path) if args.resume else set()
    jobs = [job for job in jobs if job["job_id"] not in existing_job_ids]
    if not jobs:
        cleanup_failure_file(output_path, failure_path)
        print("No jobs to run.")
        return 0

    inference = config["inference"]
    device = single_pass.choose_device(args.device or inference.get("device", "auto"))
    dtype = single_pass.choose_dtype(args.dtype or inference.get("dtype", "auto"), device)
    model_entry = aliases[args.model_alias]

    print(f"Loading {args.model_alias} from {model_entry['hf_model_id']} on {device} with dtype={dtype}")
    tokenizer = AutoTokenizer.from_pretrained(model_entry["hf_model_id"])
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(model_entry["hf_model_id"], dtype=dtype)
    model.to(device)
    model.eval()

    task_ac_templates = {condition: load_prompt(prompt_dir / filename) for condition, filename in TASK_AC_FILENAMES.items()}
    task_b_templates = {condition: load_prompt(prompt_dir / filename) for condition, filename in TASK_B_FILENAMES.items()}
    copy_template = load_prompt(prompt_dir / COPY_FILENAME)
    relation_template = load_prompt(prompt_dir / RELATION_FILENAME)
    copy_mode = config.get("task_b_copy_mode", "model_copy")
    if copy_mode not in {"model_copy", "benchmark_summary"}:
        raise SystemExit(f"Unsupported task_b_copy_mode '{copy_mode}'")

    max_attempts = int(inference.get("max_attempts", 2))
    prompt_mode = inference.get("prompt_mode", "chat")
    max_new_tokens = int(inference["max_new_tokens"])
    temperature = float(inference["temperature"])
    top_p = float(inference["top_p"])

    if not args.resume:
        output_path.write_text("", encoding="utf-8")
        failure_path.write_text("", encoding="utf-8")
        trace_path.write_text("", encoding="utf-8")

    success_count = len(existing_job_ids) if args.resume else 0
    failure_count = 0

    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] {job['job_id']}")
        item = benchmark_items[job["item_id"]]
        case_a, case_b = presented_cases(job, item)
        replacements = prompt_replacements(case_a, case_b)

        task_ac_prompt = render_template(task_ac_templates[job["condition"]], replacements)
        task_ac_response, task_ac_raw, task_ac_error = generate_and_parse(
            task_ac_prompt,
            parse_task_ac_response,
            model=model,
            tokenizer=tokenizer,
            device=device,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            prompt_mode=prompt_mode,
            max_attempts=max_attempts,
        )
        if task_ac_response is None:
            append_jsonl(
                failure_path,
                {
                    "job_id": job["job_id"],
                    "item_id": job["item_id"],
                    "model": args.model_alias,
                    "condition": job["condition"],
                    "error": f"task_ac:{task_ac_error}",
                    "raw_outputs": task_ac_raw,
                },
            )
            failure_count += 1
            continue

        if copy_mode == "benchmark_summary":
            copy_response = {
                "case_a_written_intention_copy": case_a["motive_summary"],
                "case_b_written_intention_copy": case_b["motive_summary"],
            }
            copy_raw: List[str] = []
            copy_error = None
        else:
            copy_prompt = render_template(copy_template, replacements)
            copy_response, copy_raw, copy_error = generate_and_parse(
                copy_prompt,
                parse_copy_response,
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                prompt_mode=prompt_mode,
                max_attempts=max_attempts,
            )
            if copy_response is None:
                append_jsonl(
                    failure_path,
                    {
                        "job_id": job["job_id"],
                        "item_id": job["item_id"],
                        "model": args.model_alias,
                        "condition": job["condition"],
                        "error": f"copy_intentions:{copy_error}",
                        "raw_outputs": copy_raw,
                    },
                )
                failure_count += 1
                continue

        copy_a_normalized = normalize_intention_copy(copy_response["case_a_written_intention_copy"])
        copy_b_normalized = normalize_intention_copy(copy_response["case_b_written_intention_copy"])
        copy_exact_match = bool(copy_a_normalized and copy_a_normalized == copy_b_normalized)

        relation_response: str | None = None
        relation_raw: List[str] = []
        relation_error: str | None = None
        task_b_response: str | None = None
        task_b_raw: List[str] = []
        task_b_error: str | None = None
        gate_source = "exact_copy_match" if copy_exact_match else None

        if copy_exact_match:
            task_b_label = "Same"
        else:
            relation_replacements = {
                **replacements,
                "{{case_a_written_intention_copy}}": copy_response["case_a_written_intention_copy"],
                "{{case_b_written_intention_copy}}": copy_response["case_b_written_intention_copy"],
            }
            relation_prompt = render_template(relation_template, relation_replacements)
            relation_response, relation_raw, relation_error = generate_and_parse(
                relation_prompt,
                parse_relation_response,
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                prompt_mode=prompt_mode,
                max_attempts=max_attempts,
            )
            if relation_response is None:
                append_jsonl(
                    failure_path,
                    {
                        "job_id": job["job_id"],
                        "item_id": job["item_id"],
                        "model": args.model_alias,
                        "condition": job["condition"],
                        "error": f"relation:{relation_error}",
                        "raw_outputs": relation_raw,
                    },
                )
                failure_count += 1
                continue

            if relation_response == "same":
                task_b_label = "Same"
                gate_source = "relation_same"
            else:
                task_b_prompt = render_template(task_b_templates[job["condition"]], relation_replacements)
                task_b_response, task_b_raw, task_b_error = generate_and_parse(
                    task_b_prompt,
                    parse_task_b_response,
                    model=model,
                    tokenizer=tokenizer,
                    device=device,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    prompt_mode=prompt_mode,
                    max_attempts=max_attempts,
                )
                if task_b_response is None:
                    append_jsonl(
                        failure_path,
                        {
                            "job_id": job["job_id"],
                            "item_id": job["item_id"],
                            "model": args.model_alias,
                            "condition": job["condition"],
                            "error": f"task_b_worse:{task_b_error}",
                            "raw_outputs": task_b_raw,
                        },
                    )
                    failure_count += 1
                    continue
                task_b_label = task_b_response
                gate_source = "inward_worse_pass"

        response = {
            "task_a_more_morally_problematic": task_ac_response["task_a_more_morally_problematic"],
            "task_b_worse_inward_orientation": task_b_label,
            "task_c_primary_reason": task_ac_response["task_c_primary_reason"],
            "brief_explanation": task_ac_response["brief_explanation"],
        }
        if not evaluate_runs.validate_response(response):
            append_jsonl(
                failure_path,
                {
                    "job_id": job["job_id"],
                    "item_id": job["item_id"],
                    "model": args.model_alias,
                    "condition": job["condition"],
                    "error": "final_response_failed_schema_validation",
                    "raw_outputs": [],
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
                "response": response,
            },
        )
        append_jsonl(
            trace_path,
            {
                "job_id": job["job_id"],
                "item_id": job["item_id"],
                "model": args.model_alias,
                "condition": job["condition"],
                "benchmark_source": job["benchmark_source"],
                "pair_type": job["pair_type"],
                "primary_diagnostic_dimension": job["primary_diagnostic_dimension"],
                "gold": job["gold"],
                "expected_relation": pass_expected_relation(job),
                "copy_mode": copy_mode,
                "gate_source": gate_source,
                "copy_exact_match": copy_exact_match,
                "case_a_written_intention_copy": copy_response["case_a_written_intention_copy"],
                "case_b_written_intention_copy": copy_response["case_b_written_intention_copy"],
                "case_a_written_intention_copy_normalized": copy_a_normalized,
                "case_b_written_intention_copy_normalized": copy_b_normalized,
                "relation_response": relation_response,
                "task_b_pass_response": task_b_response,
                "final_response": response,
                "pass_outputs": {
                    "task_ac": task_ac_response,
                    "copy_intentions": copy_response,
                    "relation": relation_response,
                    "task_b_worse": task_b_response,
                },
                "raw_outputs": {
                    "task_ac": task_ac_raw,
                    "copy_intentions": copy_raw,
                    "relation": relation_raw,
                    "task_b_worse": task_b_raw,
                },
            },
        )
        success_count += 1

    cleanup_failure_file(output_path, failure_path)
    print(f"Wrote {success_count} successful run records to {output_path}")
    print(f"Wrote {failure_count} failures to {failure_path}")
    print(f"Wrote traces to {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
