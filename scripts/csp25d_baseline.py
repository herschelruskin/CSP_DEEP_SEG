"""December baseline: native-resolution coronal 7-slice T2 -> central CSP mask.

Requires torch, numpy, nibabel. Does not use Slicer at training time.
Input crops MUST be generated with calibrate_csp_roi_slicer.py using the
frozen proportional rule and accompanied by the original .crop.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler


class Block(nn.Module):
    def __init__(self, incoming: int, outgoing: int):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(incoming, outgoing, 3, padding=1), nn.GroupNorm(4, outgoing), nn.ReLU(inplace=True),
            nn.Conv2d(outgoing, outgoing, 3, padding=1), nn.GroupNorm(4, outgoing), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.layers(x)


class CoronalUNet25D(nn.Module):
    """2D U-Net with consecutive coronal slices as input channels; one output plane."""
    def __init__(self, slices: int = 7, width: int = 16):
        super().__init__()
        if slices < 1 or slices % 2 != 1:
            raise ValueError('slices must be a positive odd number')
        if width % 4:
            raise ValueError('width must be divisible by four')
        self.enc1 = Block(slices, width)
        self.enc2 = Block(width, width * 2)
        self.enc3 = Block(width * 2, width * 4)
        self.center = Block(width * 4, width * 8)
        self.pool = nn.MaxPool2d(2)
        self.dec3 = Block(width * 8 + width * 4, width * 4)
        self.dec2 = Block(width * 4 + width * 2, width * 2)
        self.dec1 = Block(width * 2 + width, width)
        self.head = nn.Conv2d(width, 1, kernel_size=1)

    def forward(self, x):
        from torch.nn.functional import interpolate
        a = self.enc1(x)
        b = self.enc2(self.pool(a))
        c = self.enc3(self.pool(b))
        z = self.center(self.pool(c))
        for block, skip in ((self.dec3, c), (self.dec2, b), (self.dec1, a)):
            z = block(torch.cat((interpolate(z, size=skip.shape[-2:], mode='bilinear', align_corners=False), skip), dim=1))
        return self.head(z)


def extract_coronal_stack(img_ijk: np.ndarray, j: int, slices: int = 7):
    """Nibabel image axes are I,J,K: coronal J, output C,K,I (no resampling)."""
    if slices < 1 or slices % 2 != 1:
        raise ValueError('slices must be positive and odd')
    if not 0 <= j < img_ijk.shape[1]:
        raise IndexError(j)
    half = slices // 2
    indices = [min(max(j + d, 0), img_ijk.shape[1] - 1) for d in range(-half, half + 1)]
    return np.stack([img_ijk[:, idx, :].T for idx in indices], axis=0).astype(np.float32)


def crop_native_mask(mask_ijk: np.ndarray, meta: dict, mask_affine: np.ndarray,
                     crop_shape_ijk: tuple[int, int, int], crop_affine: np.ndarray):
    """Extract label voxels by integer offsets; abort on shape/geometry mismatch."""
    orig = tuple(int(x) for x in meta['source_shape_kji'][::-1])
    start = np.asarray(meta['start_ijk'], dtype=int)
    end = np.asarray(meta['end_ijk'], dtype=int)
    if mask_ijk.shape != orig or (start < 0).any() or (end > orig).any() or (end <= start).any():
        raise ValueError('Native mask shape/crop coordinates mismatch')
    if tuple(end - start) != tuple(crop_shape_ijk):
        raise ValueError('Crop dimensions differ from .crop.json')
    if not np.allclose(mask_affine, meta['original_affine'], atol=1e-3, rtol=0):
        raise ValueError('Native mask affine does not match original T2')
    if not np.allclose(crop_affine, meta['output_affine'], atol=1e-3, rtol=0):
        raise ValueError('Cropped T2 affine does not match .crop.json')
    expected = np.asarray(meta['original_affine'], dtype=float).copy()
    expected[:3, 3] = (expected @ np.r_[start, 1.0])[:3]
    if not np.allclose(expected, crop_affine, atol=1e-3, rtol=0):
        raise ValueError('Crop-to-native affine translation mismatch')
    i0, j0, k0 = start
    i1, j1, k1 = end
    return mask_ijk[i0:i1, j0:j1, k0:k1]


def normalize_t2(img: np.ndarray):
    """Per-volume robust clipping; preserves bright CSF signal and voxel size."""
    good = img[np.isfinite(img) & (img > 0)]
    if good.size < 10:
        raise ValueError('Too few finite positive T2 intensities')
    lo, hi = np.percentile(good, (1, 99))
    if hi <= lo:
        raise ValueError('Constant or degenerate T2 intensities')
    scaled = np.clip((np.nan_to_num(img.astype(np.float32)) - lo) / (hi - lo), 0, 1)
    scaled[img <= 0] = 0
    return scaled.astype(np.float32)


def read_manifest(filename):
    with open(filename, newline='', encoding='utf-8-sig') as fp:
        rows = list(csv.DictReader(fp))
    required = {'subject_id', 'split', 'crop_t2', 'crop_json', 'source_mask', 'presence', 'qc', 'negative_confidence'}
    if not rows or not required.issubset(rows[0]):
        raise ValueError('Manifest missing required columns or rows: ' + ', '.join(sorted(required)))
    ids = [r['subject_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated subject ID: only one SPC1 row per subject allowed')
    groups = {}
    for r in rows:
        if r['split'] not in ('train', 'val', 'test', 'unassigned'):
            raise ValueError('Use explicit train/val/test/unassigned split, never dev as training')
        family = r.get('family_group', '').strip()
        if family:
            groups.setdefault(family, set()).add(r['split'])
    for fam, splits in groups.items():
        if len(splits - {'unassigned'}) > 1:
            raise ValueError('Family split leakage: ' + fam)
    if any(not r.get('family_group', '').strip() for r in rows):
        print('WARNING: family-disjoint partition NOT VERIFIED (missing family_group)')
    return rows


def usable_for_supervision(row):
    presence = row['presence'].strip().lower()
    qc = row['qc'].strip().lower()
    if presence == 'present':
        return qc in ('pass', 'provisional') and bool(row['source_mask'].strip())
    # Operational 'absent' isn't proof of anatomical zero. Require explicit adjudication.
    return presence == 'absent' and qc == 'pass' and row['negative_confidence'].strip().lower() == 'high'


@lru_cache(maxsize=128)
def load_case(subject_id, crop_path, json_path, mask_path, presence):
    import nibabel as nib
    nii = nib.load(crop_path)
    image = np.asarray(nii.dataobj, dtype=np.float32)
    meta = json.loads(Path(json_path).read_text(encoding='utf-8'))
    # In these native HCP volumes the second IJK axis must be predominantly AP.
    # Fail instead of silently using a sagittal/axial dimension as 'coronal'.
    axis_dominance = np.argmax(np.abs(nii.affine[:3, :3]), axis=0).tolist()
    if axis_dominance != [0, 1, 2]:
        raise ValueError('Non-coronal native axis order for '+subject_id+': '+str(axis_dominance)+'; do not resample silently')
    original_shape = tuple(int(x) for x in meta['source_shape_kji'][::-1])
    if original_shape == image.shape:
        raise ValueError('Expected a reduced T2 crop, got original-sized image')
    # Also validate the crop affine and offset when the reference is empty.
    start = np.asarray(meta['start_ijk'], dtype=int)
    end = np.asarray(meta['end_ijk'], dtype=int)
    orig_aff = np.asarray(meta['original_affine'])
    exp_aff = orig_aff.copy()
    exp_aff[:3, 3] = (orig_aff @ np.r_[start, 1.0])[:3]
    if tuple(end - start) != image.shape or not np.allclose(nii.affine, exp_aff, atol=1e-3, rtol=0):
        raise ValueError('Crop and metadata geometry disagree for ' + subject_id)
    if presence == 'absent':
        mask = np.zeros(image.shape, dtype=np.uint8)
    else:
        if not mask_path:
            raise ValueError('Positive subject lacks native mask: ' + subject_id)
        ref = nib.load(mask_path)
        native = np.asarray(ref.dataobj)
        values = np.unique(native)
        if not np.isin(values, (0, 1)).all():
            raise ValueError('Nonbinary mask: explicitly export triangular-only 0/1 labelmap for ' + subject_id)
        mask = crop_native_mask(native, meta, ref.affine, image.shape, nii.affine).astype(np.uint8)
        if not np.any(mask):
            raise ValueError('Positive CSP completely outside crop: ' + subject_id)
        if int(np.count_nonzero(mask)) != int(np.count_nonzero(native)):
            raise ValueError('CSP incompletely contained in crop: ' + subject_id)
    # Return native unnormalized crop for simple inference/diagnostics too.
    return normalize_t2(image), mask, nii.affine.copy(), meta


class CoronalDataset(Dataset):
    def __init__(self, rows, slices=7, boundary_ignore=1):
        self.rows = {r['subject_id']: r for r in rows}
        self.slices = slices
        self.index = []
        for r in rows:
            img, mask, _, _ = load_case(r['subject_id'], r['crop_t2'], r['crop_json'], r['source_mask'], r['presence'])
            positive = np.any(mask, axis=(0, 2))
            if positive.any():
                lo, hi = np.flatnonzero(positive)[[0, -1]]
            else:
                lo, hi = -100, -100
            for j in range(img.shape[1]):
                if not positive[j] and (lo - boundary_ignore <= j < lo or hi < j <= hi + boundary_ignore):
                    continue  # Do not force uncertain immediate end-slices to background.
                self.index.append((r['subject_id'], j, bool(positive[j])))
        if not self.index:
            raise ValueError('No eligible slices')

    def __len__(self):
        return len(self.index)

    def __getitem__(self, index):
        sid, j, _ = self.index[index]
        r = self.rows[sid]
        img, mask, _, _ = load_case(sid, r['crop_t2'], r['crop_json'], r['source_mask'], r['presence'])
        x = extract_coronal_stack(img, j, self.slices)
        y = mask[:, j, :].T.astype(np.float32)[None, :, :]
        return torch.from_numpy(x.copy()), torch.from_numpy(y.copy())


def bce_dice_loss(logits, target):
    bce = nn.functional.binary_cross_entropy_with_logits(logits, target)
    # Dice only on positive-center slices; empty slices still contribute BCE.
    mask = target.flatten(1).sum(1) > 0
    if not torch.any(mask):
        return bce
    p = torch.sigmoid(logits[mask]).flatten(1)
    t = target[mask].flatten(1)
    dice_loss = 1 - ((2 * (p * t).sum(1) + 1) / (p.sum(1) + t.sum(1) + 1)).mean()
    return bce + dice_loss


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


@torch.no_grad()
def predict_case(model, row, device, slices):
    img, _, affine, meta = load_case(row['subject_id'], row['crop_t2'], row['crop_json'], '', 'absent')
    prob = np.zeros_like(img, dtype=np.float32)
    model.eval()
    for j in range(img.shape[1]):
        x = torch.from_numpy(extract_coronal_stack(img, j, slices)[None]).to(device)
        prob[:, j, :] = torch.sigmoid(model(x))[0, 0].cpu().numpy().T
    return prob, affine, meta


def evaluate(model, rows, device, slices, threshold=0.5):
    """Subject-level metrics: Dice only for annotated positives; empty-case FP volume separately."""
    dices, empty_fp = [], []
    for row in rows:
        prob, _, meta = predict_case(model, row, device, slices)
        _, ref, _, _ = load_case(row['subject_id'], row['crop_t2'], row['crop_json'], row['source_mask'], row['presence'])
        pred = prob >= threshold
        spacing_volume = abs(np.linalg.det(np.asarray(meta['original_affine'])[:3, :3]))
        if np.any(ref):
            dices.append(2 * int(np.logical_and(pred, ref).sum()) / max(1, int(pred.sum()) + int(ref.sum())))
        else:
            empty_fp.append(float(pred.sum()) * spacing_volume)
    return {'positive_case_mean_dice': float(np.mean(dices)) if dices else None,
            'n_positive': len(dices), 'empty_case_mean_fp_mm3': float(np.mean(empty_fp)) if empty_fp else None,
            'n_empty': len(empty_fp)}


def train(args):
    rows = read_manifest(args.manifest)
    train_rows = [r for r in rows if r['split'] == 'train' and usable_for_supervision(r)]
    val_rows = [r for r in rows if r['split'] == 'val' and usable_for_supervision(r)]
    if not train_rows or not val_rows:
        raise ValueError('Need eligible explicit train and val subjects; see annotation-confidence policy')
    seed_all(args.seed)
    train_ds = CoronalDataset(train_rows, args.slices, args.boundary_ignore)
    positive = [b for _, _, b in train_ds.index]
    p, n = sum(positive), len(positive) - sum(positive)
    if not p or not n:
        raise ValueError('Both positive and negative center slices required for training')
    weights = torch.tensor([0.5 / p if b else 0.5 / n for b in positive], dtype=torch.double)
    sampler = WeightedRandomSampler(weights, num_samples=len(train_ds), replacement=True)
    loader = DataLoader(train_ds, batch_size=1, sampler=sampler, num_workers=0)
    model = CoronalUNet25D(slices=args.slices, width=args.width)
    device = torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    manifest_hash = hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()
    try:
        git_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        git_head = 'unavailable'
    record = {'slices': args.slices, 'width': args.width, 'seed': args.seed, 'lr': args.lr,
              'boundary_ignore': args.boundary_ignore, 'device': str(device), 'torch': torch.__version__,
              'manifest_sha256': manifest_hash, 'git_head': git_head,
              'train_subjects': len(train_rows), 'val_subjects': len(val_rows),
              'positive_training_slices': p, 'negative_training_slices': n,
              'checkpoint_selection': 'positive_case_mean_dice; validation requires positive cases'}
    (out/'config.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    best = -float('inf')
    with (out/'history.csv').open('w', newline='', encoding='utf-8') as fp:
        writer = csv.DictWriter(fp, fieldnames=['epoch', 'train_loss', 'val_positive_case_mean_dice', 'val_empty_mean_fp_mm3'])
        writer.writeheader()
        for epoch in range(1, args.epochs + 1):
            model.train(); losses = []
            for x, y in loader:
                x = x.to(device); y = y.to(device)
                optimizer.zero_grad(set_to_none=True)
                loss = bce_dice_loss(model(x), y)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                losses.append(float(loss.item()))
            metrics = evaluate(model, val_rows, device, args.slices)
            dice = metrics['positive_case_mean_dice']
            # A validation set with no positives is inadequate for selecting a Dice model.
            if dice is None:
                raise ValueError('Validation split must contain at least one CSP-positive subject')
            writer.writerow({'epoch': epoch, 'train_loss': np.mean(losses),
                             'val_positive_case_mean_dice': dice,
                             'val_empty_mean_fp_mm3': metrics['empty_case_mean_fp_mm3']})
            fp.flush()
            print(f'Epoch {epoch}: train_loss={np.mean(losses):.4f}, val_positive_Dice={dice:.4f}, val_empty_fp_mm3={metrics["empty_case_mean_fp_mm3"]}')
            if dice > best:
                best = dice
                torch.save({'state_dict': model.state_dict(), 'config': record, 'epoch': epoch, 'val_metrics': metrics}, out/'best.pt')
    print('Saved model and run record:', out)


def infer(args):
    import nibabel as nib
    rows = read_manifest(args.manifest)
    found = [r for r in rows if r['subject_id'] == args.subject_id]
    if len(found) != 1:
        raise ValueError('Unknown subject in manifest')
    row = found[0]
    device = torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    state = torch.load(args.checkpoint, map_location=device, weights_only=False)
    cfg = state['config']
    model = CoronalUNet25D(cfg['slices'], cfg['width']).to(device)
    model.load_state_dict(state['state_dict'])
    prob, crop_affine, meta = predict_case(model, row, device, cfg['slices'])
    pred = (prob >= args.threshold).astype(np.uint8)
    full = np.zeros(tuple(meta['source_shape_kji'][::-1]), dtype=np.uint8)
    i0, j0, k0 = meta['start_ijk']; i1, j1, k1 = meta['end_ijk']
    full[i0:i1, j0:j1, k0:k1] = pred
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(prob, crop_affine), str(out/(row['subject_id']+'_crop_prob.nii.gz')))
    nib.save(nib.Nifti1Image(full, np.asarray(meta['original_affine'])), str(out/(row['subject_id']+'_native_pred.nii.gz')))
    print('Saved native-space mask and crop probability map:', out)


def build_manifest(args):
    """Create an editable PRIVATE manifest; never invent train/val/test assignment."""
    with open(args.cohort, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    fields = ['subject_id', 'split', 'family_group', 'crop_t2', 'crop_json', 'source_mask',
              'presence', 'qc', 'negative_confidence']
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            source = Path(r['source_t2'])
            base = source.name[:-7] if source.name.endswith('.nii.gz') else source.stem
            cropped = base + '_proportional_reduced'
            split = r.get('split', '')
            if split not in ('train', 'val', 'test'):
                split = 'unassigned'
            w.writerow({'subject_id': r['subject_id'], 'split': split,
                        'family_group': r.get('family_group', ''),
                        'crop_t2': str(Path(args.crop_dir)/(cropped+'.nii.gz')),
                        'crop_json': str(Path(args.crop_dir)/(cropped+'.crop.json')),
                        'source_mask': r.get('mask_path', ''), 'presence': r.get('presence', ''),
                        'qc': r.get('qc', ''), 'negative_confidence': ''})
    print('Wrote PRIVATE draft manifest; edit splits and QC before training:', output)


def smoke(args):
    net = CoronalUNet25D(slices=7, width=16)
    x = torch.rand(1, 7, 73, 55)
    output = net(x)
    assert output.shape == (1, 1, 73, 55)
    print('CPU forward smoke passed; parameters:', sum(x.numel() for x in net.parameters()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('smoke')
    m = sub.add_parser('build-manifest'); m.add_argument('--cohort', required=True); m.add_argument('--crop-dir', required=True); m.add_argument('--output', required=True)
    t = sub.add_parser('train'); t.add_argument('--manifest', required=True); t.add_argument('--out', required=True)
    t.add_argument('--slices', type=int, default=7); t.add_argument('--width', type=int, default=16)
    t.add_argument('--epochs', type=int, default=20); t.add_argument('--lr', type=float, default=3e-4)
    t.add_argument('--seed', type=int, default=843); t.add_argument('--boundary-ignore', type=int, default=1); t.add_argument('--cpu', action='store_true')
    i = sub.add_parser('infer'); i.add_argument('--manifest', required=True); i.add_argument('--checkpoint', required=True)
    i.add_argument('--subject-id', required=True); i.add_argument('--out', required=True)
    i.add_argument('--threshold', type=float, default=0.5); i.add_argument('--cpu', action='store_true')
    args = parser.parse_args()
    {'smoke': smoke, 'build-manifest': build_manifest, 'train': train, 'infer': infer}[args.action](args)


if __name__ == '__main__':
    main()
