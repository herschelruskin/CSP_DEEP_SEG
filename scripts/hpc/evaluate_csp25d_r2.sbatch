#!/usr/bin/env bash
#SBATCH --job-name=csp25d-r2-eval
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:20:00

# Inference ONLY: freeze the model weights, R2 stage, manifest and threshold.
# Never train on the 20 repeat-annotation subjects in this job.
set -euo pipefail
: "${CSP_REPO:?Set CSP_REPO to existing source checkout}"
: "${CSP_VENV:?Set CSP_VENV to original CUDA venv}"
: "${CSP_PY_MODULE:?Set Python module version}"
: "${CSP_MANIFEST:?Set frozen original 44/11 private manifest}"
: "${CSP_R2_STAGE:?Set PRIVATE transferred R1/R2 stage}"
: "${CSP_CHECKPOINT:?Set original best.pt checkpoint}"
: "${CSP_EVAL_OUT:?Set new private output directory}"

[[ -f "$CSP_R2_STAGE/READY.json" ]] || { echo "R2 stage not complete" >&2; exit 2; }
[[ -f "$CSP_R2_STAGE/r2_eval_manifest.csv" ]] || { echo "R2 manifest missing" >&2; exit 2; }
[[ -s "$CSP_CHECKPOINT" ]] || { echo "Checkpoint missing" >&2; exit 2; }
[[ ! -e "$CSP_EVAL_OUT" ]] || { echo "R2 evaluation already exists; refusing overwrite" >&2; exit 2; }
module load "$CSP_PY_MODULE"
source "$CSP_VENV/bin/activate"
cd "$CSP_REPO"
echo "[R2 GPU] job=${SLURM_JOB_ID:-unknown} node=$(hostname) at $(date -Is)"
git rev-parse HEAD
nvidia-smi
python scripts/evaluate_csp25d_r2.py \
  --stage "$CSP_R2_STAGE" \
  --checkpoint "$CSP_CHECKPOINT" \
  --original-manifest "$CSP_MANIFEST" \
  --out "$CSP_EVAL_OUT" \
  --threshold 0.5 \
  --require-cuda
echo "[R2 GPU COMPLETE] $(date -Is)"
