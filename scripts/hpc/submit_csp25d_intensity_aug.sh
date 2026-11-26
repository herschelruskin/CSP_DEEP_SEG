#!/usr/bin/env bash
# Submit controlled CSP25D augmentation jobs from Narval login using sbatch.
# Original checkpoints and private MRI labels are not modified.
set -euo pipefail

REPO="$HOME/CSP_DEEP_SEG"
ROOT="${SCRATCH:?Set SCRATCH on Narval}/csp25d_private/baseline_seed843"
MANIFEST="$ROOT/manifests/model_25d_trainval_seed843_linux.csv"
EXPECTED_SHA="3498caf14cddb7fa56e50b26333a2374d49ac472170231a92a2886b977291229"

cd "$REPO"
test -f "$MANIFEST" || { echo "[STOP] Frozen manifest missing: $MANIFEST" >&2; exit 2; }
test -f "$HOME/venvs/csp25d/bin/activate" || { echo "[STOP] Python venv missing" >&2; exit 2; }
bash -n scripts/hpc/train_csp25d.sbatch

ACTUAL_SHA="$(sha256sum "$MANIFEST" | awk '{print $1}')"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
    echo "[STOP] Frozen 44/11 manifest SHA256 changed: $ACTUAL_SHA" >&2
    exit 2
fi

# If multiple rule versions exist, require explicit caller selection.
if [[ -n "${CSP_RULE_JSON:-}" ]]; then
    test -f "$CSP_RULE_JSON" || { echo "[STOP] Calibrated rules file missing" >&2; exit 2; }
else
    mapfile -t RULES < <(find "$ROOT" -type f -name calibrated_rules.json)
    if [[ ${#RULES[@]} -ne 1 ]]; then
        echo "[STOP] Found ${#RULES[@]} calibrated_rules.json files; need exactly one." >&2
        printf '%s\n' "${RULES[@]}" >&2
        echo "Set CSP_RULE_JSON to original corrected-112112 path and retry." >&2
        exit 2
    fi
    CSP_RULE_JSON="${RULES[0]}"
fi
export CSP_RULE_JSON
echo "[RULES] $CSP_RULE_JSON"
sha256sum "$MANIFEST" "$CSP_RULE_JSON"

export CSP_REPO="$REPO"
export CSP_VENV="$HOME/venvs/csp25d"
export CSP_PY_MODULE="python/3.11.5"
export CSP_MANIFEST="$MANIFEST"
export CSP_EXPECT_MANIFEST_SHA256="$EXPECTED_SHA"
export CSP_EPOCHS=20
export CSP_INTENSITY_AUGMENT=1
mkdir -p "$ROOT/logs"

for SEED in 843 844 845; do
    OUT="$ROOT/runs/baseline_20epoch_augint_seed${SEED}"
    NAME="csp25d-ai${SEED}"
    if [[ -e "$OUT" ]]; then
        echo "[SKIP] Existing output directory for seed $SEED"
        continue
    fi
    if squeue -u "$USER" -h -o '%j' | grep -Fx "$NAME" >/dev/null; then
        echo "[SKIP] Existing queued/running job for seed $SEED"
        continue
    fi
    echo "[SUBMIT] seed=$SEED, fixed-split 44/11, 20 epochs, train-only intensity augmentation"
    CSP_SEED="$SEED" CSP_OUT="$OUT" sbatch --account=def-nwc_gpu --gres=gpu:a100_3g.20gb:1 --cpus-per-task=4 --mem=16G --time=01:00:00 --job-name="$NAME" --output="$ROOT/logs/augint-${SEED}-%j.out" --export=ALL scripts/hpc/train_csp25d.sbatch
done

echo "=== JOB STATUS ==="
squeue -u "$USER"
