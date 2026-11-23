# Compute Canada / Alliance GPU pilot (2026-11-23)

**Default:** Train on a Digital Research Alliance of Canada (formerly Compute Canada) GPU because the RTX 2060 Super is at home, not at the office. **Fallback:** home 2060 only if Alliance access, allocation, software environment or queue makes a pilot impractical. No cluster login, GPU allocation or job submission has been independently verified.

Retain the unshifted proportional ~1% crop, native 0.7 mm SPC1 T2, seven consecutive coronal input slices, subject-level validation, and 16-channel 2.5D U-Net. The small supervised pilot requires one GPU, not distributed training.

**IMPORTANT 2026-11-23 UPDATE:** A completed office batch has been reported. Do not recrop the cohort based on the older instructions below; first follow the inventory addendum at the end of this document.

## 1. Local Windows and Slicer gate

Keep using the exact private calibrated rules file under:
    D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json

Use the existing one-line Slicer command from docs/CSP_25D_BASELINE.md with limit=3 before cropping the remaining manifest rows. Verify the script versions are current. Three-scan reports are not a substitute for independent validation.

Generate a **private** 2.5D manifest from PowerShell at repo root:

    python scripts\csp25d_baseline.py build-manifest --cohort "D:\CSP_DEEP_SEG\derived\roi_calibration\cohort_manifest.csv" --crop-dir "D:\CSP_DEEP_SEG\derived\roi_calibration\model_25d_crops" --output "D:\CSP_DEEP_SEG\derived\model_25d_manifest.csv"

Audit only subjects whose new proportional crop actually exists; for example, replace ACTUAL_ID below with a cropped subject and run:

    python scripts\audit_csp25d_manifest.py --manifest "D:\CSP_DEEP_SEG\derived\model_25d_manifest.csv" --report "D:\CSP_DEEP_SEG\derived\model_25d_audit.csv" --rule-json "D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json" --verify-original --subject-id ACTUAL_ID

This requires nibabel, numpy and torch on Windows Python. The script checks the frozen rule, exact Slicer integer crop mapping, saved/reloaded NIfTI affine, binary native mask and complete CSP coverage; with --verify-original it also checks the original unaltered T2 voxel values against the stored cropped image. The CSV contains subject IDs and must remain private.

Inspect/QC the available 70 development labels and explicit train/val/test and family_group fields. Some absent cases are operational or unresolvable, NOT automatically confidently negative. After the three-scan gate, crop only the cohort-manifest subjects with limit=None and audit the eligible train/val records with --split train --split val --verify-original. Existing 108828 extreme is known not to fit the standard crop; do not waive this failure.

## 2. Alliance access and Python

The exact cluster and Slurm billing account are UNKNOWN. On Windows PowerShell use SSH to an Alliance GPU cluster that the user is entitled to use; for example:

    ssh YOUR_ALLIANCE_USERNAME@nibi.alliancecan.ca

After login (not on a GPU node), inspect:

    module spider python
    sacctmgr show assoc where user=$USER format=Account,Cluster%20
    echo "$HOME" "$SCRATCH"

Find the actual supported Python module and establish a virtual environment on the login node, for example:

    module load python/3.11.5
    python -m venv "$HOME/venvs/csp25d"
    source "$HOME/venvs/csp25d/bin/activate"
    python -m pip install --no-index torch numpy nibabel pytest

The module version is EXAMPLE ONLY, not verified for the target cluster. Some installations may need different modules or PyTorch builds; consult that cluster's Python/PyTorch documentation and check CUDA inside the GPU allocation. No training work belongs on login nodes.

Clone the actual feature branch:

    git clone --branch feature/native-coronal-25d-baseline-20261120 https://github.com/herschelruskin/CSP_DEEP_SEG.git "$HOME/CSP_DEEP_SEG"

## 3. Transfer only needed private inputs

Confirm HCP data-transfer permission and local institutional storage rules before uploading any scans. Transfer reduced NIfTIs and adjacent crop JSON files, matching original-grid native binary masks for positive subjects, the frozen corrected calibrated_rules.json and the private model manifest. The **full 1,689 T2 acquisitions are unnecessary** for the pilot. Use Globus/Globus Connect Personal from the office workstation or the Alliance-recommended data-transfer host. Do not put HCP files or private manifests in public GitHub.

Suggested directories:
    $SCRATCH/csp25d_private/crops
    $SCRATCH/csp25d_private/masks
    $SCRATCH/csp25d_private/calibrated_rules.json

Raw full-resolution T2 images are unnecessary on the GPU after passing the Windows original-voxel crop audit. Private Windows-path manifest entries must be rewritten for Linux; copying the CSV alone is not enough. From the Alliance login node, after transferring the CSV:

    python "$HOME/CSP_DEEP_SEG/scripts/relocate_csp25d_manifest.py" --manifest "$SCRATCH/csp25d_private/model_25d_manifest_windows.csv" --crop-dir "$SCRATCH/csp25d_private/crops" --mask-dir "$SCRATCH/csp25d_private/masks" --output "$SCRATCH/csp25d_private/model_25d_manifest_linux.csv"

Inspect the generated CSV privately: paths, split and QC are retained; the script copies no data files.

## 4. Launch one short GPU pilot

On the cluster shell (replace YOUR_ALLOCATION and verify the Python module name):

    export CSP_REPO="$HOME/CSP_DEEP_SEG"
    export CSP_VENV="$HOME/venvs/csp25d"
    export CSP_MANIFEST="$SCRATCH/csp25d_private/model_25d_manifest_linux.csv"
    export CSP_RULE_JSON="$SCRATCH/csp25d_private/calibrated_rules.json"
    export CSP_OUT="$SCRATCH/csp25d_runs/pilot_001"
    export CSP_PY_MODULE="python/3.11.5"
    export CSP_EPOCHS=2
    sbatch --export=ALL --account=YOUR_ALLOCATION "$CSP_REPO/scripts/hpc/train_csp25d.sbatch"

The script requests one GPU, 4 CPUs, 16 GB of RAM and 1 hour as a **provisional request**, not a benchmark or guarantee. Verify GPU Slurm flags and cluster policies first. It refuses a CPU-only Torch installation, audits eligible train/val rows with the exact frozen rule, and starts only if the audit passes. It logs GPU device, CUDA runtime, training times, PyTorch peak allocated memory, train/val split sizes and checkpoint selection. It does NOT make cropped-label validation independent of the original crop-calibration set.

After submission:

    squeue -u "$USER"
    sacct -j JOB_ID --format=JobID,State,Elapsed,MaxRSS,ReqMem

Compare actual Slurm time/RAM, job logs and run-local history.csv; only then consider 20 epochs. There are no actual GPU runtime, VRAM or segmentation Dice results as of this document.

## 5. RTX 2060 Super fallback

If Alliance access is blocked, use exactly the same code, corrected crop/manifest and CUDA installation on the home PC:

    python scripts\csp25d_baseline.py train --manifest PRIVATE_MANIFEST.csv --out PRIVATE_RUN_DIR --epochs 2 --require-cuda

The home GPU is a fallback, not the preferred location for development.


## Implementation verification

GitHub Actions run 45210799717 on 2026-11-23: **13/13 synthetic CPU tests passed**, including native mask reconstruction, pixel-equality audit and tiny-mask optimizer overfit. Slurm shell syntax checked. **No Alliance GPU job launched or tested**, no HCP images read by CI, no real-data segmentation accuracy claim. First pending external step is the three-subject Windows Slicer crop/manifest/original voxel audit.


## 2026-11-23: reuse the completed existing 1% batch (supersedes the old recropping instruction)

**USER-REPORTED:** the office batch selected 1,113 unique SPC1 scans; 1,082 were newly verified, 30 were resumed, zero were counted failed, and one was reported as an exception. This implies **1,112 claimed completed crops**, NOT 1,113 independently audited model inputs. The exception identity and whether it was an intentional exclusion must be read from the PRIVATE batch log. Do not presume it was 108828. The user has visually checked a separate 30-crop sample with no reported ROI coverage failures; this was not blinded mask validation.

Before creating new ROI files, run the new inventory on the EXISTING final batch directory from a PowerShell window in the checked-out feature-branch repository:

```powershell
python scripts\inventory_csp25d_crops.py --crop-dir "D:\CSP_DEEP_SEG\derived\roi_batch\cohort" --source-root "D:\CSP_DEEP_SEG\T2w" --rule-json "D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json" --report "D:\CSP_DEEP_SEG\derived\roi_batch\csp25d_crop_inventory.csv"
```

This inventories the source SPC1 set, detects missing paired final crop NIfTI/JSON, refuses duplicate finished outputs, checks exact frozen rule/provenance and native NIfTI affine geometry, and reports the failures without overwriting anything. It intentionally excludes temporary `.roi_staging*` files. **An exit status 1 is EXPECTED if the one exception is actually missing; read the report and determine its identity rather than disguising it as PASS.** The report and its IDs/paths are private.

Then verify actual original-source voxel equality for three representative known-complete IDs (replace example tokens with actual subject IDs), and then the eligible labeled training set:

```powershell
python scripts\inventory_csp25d_crops.py --crop-dir "D:\CSP_DEEP_SEG\derived\roi_batch\cohort" --source-root "D:\CSP_DEEP_SEG\T2w" --rule-json "D:\CSP_DEEP_SEG\derived\roi_calibration\results_corrected_112112\calibrated_rules.json" --report "D:\CSP_DEEP_SEG\derived\roi_batch\csp25d_sample_voxel_audit.csv" --verify-original --subject-id REPLACE_ID_1 --subject-id REPLACE_ID_2 --subject-id REPLACE_ID_3
```

Actual source voxel equality across every original scan is more I/O-intensive; do it only if justified after systematic header/provenance QC and a representative sample. The inventory does not inspect CSP masks, so **after** marking reliable supervised subjects in the private cohort manifest, use the existing `audit_csp25d_manifest.py` with `--verify-original` to check full native CSP mask containment, binary labeling and source geometry.

The training manifest must point to the actual successful cropped-output directory. If the inventory shows files in nested final directories, adjust each private `crop_t2`/`crop_json` path from the report rather than assuming the previous `model_25d_crops` directory. Never copy private CSVs or HCP T2/masks into this public repository.

After trusted positive train subjects and their binary 0/1 native-grid masks are present on Alliance, run a deliberate TRAIN-only overfit check BEFORE the existing two-epoch Slurm pilot:

```bash
python "$CSP_REPO/scripts/overfit_csp25d_real.py" --manifest "$CSP_MANIFEST" --subject-id ACTUAL_TRAIN_ID --out "$SCRATCH/csp25d_runs/overfit_001" --steps 150
```

Run this command **inside a requested GPU compute allocation**, not on a login node. The diagnostic logs optimization loss and Dice on the EXACT training center slice used for updates; it is not subject-disjoint validation and cannot be cited as generalization performance. If it cannot memorize a trusted small mask, diagnose image/mask alignment, normalization and sampling before launching longer runs. The Slurm pilot remains in `scripts/hpc/train_csp25d.sbatch` and should follow only after basic integration succeeds.

**Actual cluster and project permissions remain user-specific and unverified.** Start by inspecting accessible association/account, modules and GPU partitions, and checking applicable HCP data-use/Alliance policies before any transfer. Nibi (`nibi.alliancecan.ca`) is a candidate login host, not a confirmed allocation for this account. The Python module version shown in the earlier example is NOT verified.
