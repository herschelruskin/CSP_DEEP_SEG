#!/usr/bin/env bash
#SBATCH --job-name=csp25d-pilot
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
# Pass --account=... to sbatch; never hardcode the user's allocation.
set -euo pipefail

: "${CSP_REPO:?Set CSP_REPO to the checked-out CSP_DEEP_SEG directory}"
: "${CSP_VENV:?Set CSP_VENV to a CUDA-enabled Python virtual environment}"
: "${CSP_MANIFEST:?Set CSP_MANIFEST to the PRIVATE Linux-path manifest}"
: "${CSP_RULE_JSON:?Set CSP_RULE_JSON to the PRIVATE calibrated_rules.json}"
: "${CSP_OUT:?Set CSP_OUT to a writable output directory}"

# Must match module used to create the virtualenv on this particular cluster.
if [[ -n "${CSP_PY_MODULE:-}" ]]; then
    module load "$CSP_PY_MODULE"
fi
source "$CSP_VENV/bin/activate"
cd "$CSP_REPO"
mkdir -p "$CSP_OUT"
echo "[CSP25D] Start: $(date -Is) SLURM_JOB_ID=${SLURM_JOB_ID:-unknown}"
git rev-parse HEAD
nvidia-smi || true

python - <<'PY'
import nibabel, numpy, torch
print("Torch:", torch.__version__, "CUDA runtime:", torch.version.cuda)
print("Nibabel:", nibabel.__version__, "NumPy:", numpy.__version__)
if not torch.cuda.is_available():
    raise SystemExit("FAIL: CUDA unavailable; refusing silent CPU training")
print("GPU:", torch.cuda.get_device_name(0))
PY

# Real original-T2 voxel equality must already have passed on the Windows PC.
python scripts/audit_csp25d_manifest.py \
    --manifest "$CSP_MANIFEST" \
    --rule-json "$CSP_RULE_JSON" \
    --split train --split val --eligible-only \
    --report "$CSP_OUT/preflight.csv"

# Short pilot; increase only after run and validation metrics are inspected.
srun python scripts/csp25d_baseline.py train \
    --manifest "$CSP_MANIFEST" \
    --out "$CSP_OUT" \
    --epochs "${CSP_EPOCHS:-2}" \
    --slices 7 --width 16 --seed 843 --require-cuda

echo "[CSP25D] Complete: $(date -Is)"
