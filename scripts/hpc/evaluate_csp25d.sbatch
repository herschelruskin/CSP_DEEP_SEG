#!/usr/bin/env bash
#SBATCH --job-name=csp25d-case-eval
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00

# Evaluate an existing frozen BEST checkpoint on the fixed 11-subject split.
# No training, gradient descent, threshold tuning or split modification.
# Account and Narval GPU MIG type are passed at submission time.
set -euo pipefail

: "${CSP_REPO:?Set CSP_REPO to the checked-out project}"
: "${CSP_VENV:?Set CSP_VENV to the CUDA-enabled Python venv}"
: "${CSP_MANIFEST:?Set CSP_MANIFEST to private 44/11 Linux-path manifest}"
: "${CSP_CHECKPOINT:?Set CSP_CHECKPOINT to pilot_2epoch/best.pt}"
: "${CSP_EVAL_OUT:?Set CSP_EVAL_OUT to new private evaluation output directory}"

if [[ -n "${CSP_PY_MODULE:-}" ]]; then
  module load "$CSP_PY_MODULE"
fi
source "$CSP_VENV/bin/activate"
cd "$CSP_REPO"
echo "[EVAL] Start: $(date -Is) job=${SLURM_JOB_ID:-unknown} node=$(hostname)"
git rev-parse HEAD
nvidia-smi

python scripts/evaluate_csp25d_checkpoint.py \
  --manifest "$CSP_MANIFEST" \
  --checkpoint "$CSP_CHECKPOINT" \
  --out "$CSP_EVAL_OUT" \
  --split val \
  --expected-subjects 11 \
  --threshold 0.5 \
  --require-cuda

echo "[EVAL] Complete: $(date -Is)"
