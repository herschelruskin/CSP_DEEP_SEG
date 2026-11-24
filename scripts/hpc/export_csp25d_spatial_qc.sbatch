#!/usr/bin/env bash
#SBATCH --job-name=csp25d-spatial-qc
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00

# Fixed checkpoint only: write native T2/correct reference/prediction and TP-FP-FN NIfTIs.
# Add connected component measurements, checksum inventory and private transfer ZIP.
# No training or modifications of the original model/reference data.
set -euo pipefail
: "${CSP_REPO:?Set project checkout}"
: "${CSP_VENV:?Set CUDA virtualenv}"
: "${CSP_MANIFEST:?Set private Linux 44/11 manifest}"
: "${CSP_CHECKPOINT:?Set original best.pt from pilot_2epoch}"
: "${CSP_PRIOR_METRICS:?Set private per_case_metrics.csv from frozen evaluator}"
: "${CSP_SPATIAL_OUT:?Set new private spatial QC output directory}"

if [[ -n "${CSP_PY_MODULE:-}" ]]; then
  module load "$CSP_PY_MODULE"
fi
source "$CSP_VENV/bin/activate"
cd "$CSP_REPO"
echo "[SPATIAL QC] Start $(date -Is) job=${SLURM_JOB_ID:-unknown} compute=$(hostname)"
git rev-parse HEAD
nvidia-smi

python scripts/export_csp25d_spatial_qc.py \
  --manifest "$CSP_MANIFEST" \
  --checkpoint "$CSP_CHECKPOINT" \
  --prior-metrics "$CSP_PRIOR_METRICS" \
  --out "$CSP_SPATIAL_OUT" \
  --expected-subjects 11 \
  --threshold 0.5 \
  --require-cuda

echo "[SPATIAL QC] Complete $(date -Is)"
