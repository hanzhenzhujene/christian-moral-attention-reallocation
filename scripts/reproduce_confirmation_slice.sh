#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-${ROOT_DIR}/results/reproduction_confirmation}"

mkdir -p "${OUTPUT_DIR}"

python3 "${ROOT_DIR}/scripts/run_transformers_multipass.py" \
  --config "${ROOT_DIR}/configs/preview_execution_v12_main_partial_mps.json" \
  --model-alias Qwen-1.5B-Instruct \
  --jobs "${ROOT_DIR}/results/paper_first_main_same_act_confirmation_jobs_v1.jsonl" \
  --output "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --failures-output "${OUTPUT_DIR}/qwen_1_5b_confirmation_failures.jsonl" \
  --trace-output "${OUTPUT_DIR}/qwen_1_5b_confirmation_trace.jsonl"

python3 "${ROOT_DIR}/scripts/run_diagnostics.py" \
  --input "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --output "${OUTPUT_DIR}/confirmation_run_diagnostics.json"

python3 "${ROOT_DIR}/scripts/evaluate_runs.py" \
  --input "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --bootstrap-samples 1000 \
  --contrasts baseline:christian_heart \
  --output "${OUTPUT_DIR}/confirmation_summary.json"

if ! python3 "${ROOT_DIR}/scripts/evaluate_pilot_health.py" \
  --config "${ROOT_DIR}/configs/paper_first_study_v1.json" \
  --jobs "${ROOT_DIR}/results/paper_first_main_same_act_confirmation_jobs_v1.jsonl" \
  --runs "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --models Qwen-1.5B-Instruct \
  --output "${OUTPUT_DIR}/confirmation_health.json"; then
  echo "Health thresholds were not fully met for this pre-freeze artifact; confirmation outputs were still written." >&2
fi

python3 "${ROOT_DIR}/scripts/evaluate_robustness_report.py" \
  --bootstrap-samples 400 \
  --contrasts baseline:christian_heart \
  --input "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --output-json "${OUTPUT_DIR}/confirmation_robustness.json" \
  --output-md "${OUTPUT_DIR}/confirmation_robustness.md"

python3 "${ROOT_DIR}/scripts/analyze_task_b_swap_gap.py" \
  --input "${OUTPUT_DIR}/qwen_1_5b_confirmation_runs.jsonl" \
  --bucket-mode pair_type \
  --output-json "${OUTPUT_DIR}/confirmation_swap_gap_by_pair_type.json" \
  --output-md "${OUTPUT_DIR}/confirmation_swap_gap_by_pair_type.md"

python3 "${ROOT_DIR}/scripts/render_confirmation_overview.py" \
  --summary "${OUTPUT_DIR}/confirmation_summary.json" \
  --health "${OUTPUT_DIR}/confirmation_health.json" \
  --robustness "${OUTPUT_DIR}/confirmation_robustness.json" \
  --output "${OUTPUT_DIR}/confirmation_overview.svg"

echo "Wrote confirmation artifact to ${OUTPUT_DIR}"
