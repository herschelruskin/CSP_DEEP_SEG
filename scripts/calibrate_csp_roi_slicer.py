"""Calibrate a standardized CSP search ROI from Slicer T2 images and manual masks.

Run from 3D Slicer's Python Console.  This is a geometry/ROI utility, NOT a
CSP segmentation model.  Subject manifests, reports and MRI stay local.

The two rules are calibrated only on development-positive masks:
  fixed_mm     - offsets in millimetres relative to measured foreground bounds
  proportional - offsets as fractions of measured foreground dimensions

Both use a per-subject approximate LR center and deliberately anteriorly placed
AP / SI limits. Neither computes a true intracranial volume or exact midsagittal
plane. Run native mask-geometry and anatomy checks before approving either rule.
"""

import csv
import json
import re
from pathlib import Path
from dataclasses import asdict

import numpy as np

from reduce_t2_slicer import (CropSettings, foreground_ras_bounds,
                              native_ijk_crop_for_ras_box, crop_array_native,
                              shifted_affine, evaluate_mask_containment,
                              _slicer_ijk_to_ras, _validate_geometry)

MODES = ('fixed_mm', 'proportional')
FIELDS = ['subject_id', 'presence', 'qc', 'split', 'source_t2',
          'mask_path', 'segment_id', 'label_value', 'notes']


def _subject_id(path):
    """Prefer the filename; fall back to a subject-named parent directory."""
    p = Path(path)
    for part in [p.name, *reversed(p.parts[:-1])]:
        ids = re.findall(r'(?<!\d)(\d{6})(?!\d)', part)
        if len(ids) == 1:
            return ids[0]
    return None


def _mask_candidate(path):
    name = path.name.lower()
    # Accept .nifti spelling as well as the standard .nii/.nii.gz suffixes.
    # Slicer must still be able to read the file as a real NIfTI label volume.
    return (name.endswith(('.seg.nrrd', '.nii.gz', '.nii', '.nifti', '.nrrd'))
            and not name.endswith(('_reduced.nii.gz', '_t2w.nii.gz')))


def _ids_from_file(path):
    if not path:
        return set()
    text = Path(path).read_text(encoding='utf-8-sig')
    ids = set(re.findall(r'(?<!\d)\d{6}(?!\d)', text))
    return ids


def make_roi_manifest(t2_root, mask_root, output_csv, absent_ids_file=None,
                      review_ids_file=None, status_csv=None):
    """Auto-discover subjects with masks plus explicitly confirmed absences.

    Never infer absence from a missing file. A row with an ambiguous or missing
    mask is marked QC=needs_review; it never enters calibration unexamined.
    The optional status_csv has subject_id,presence,qc,split,notes columns.
    """
    if not Path(t2_root).is_dir() or not Path(mask_root).is_dir():
        raise FileNotFoundError('Expected existing T2w and mask directories')
    t2_files = list(Path(t2_root).rglob('*_3T_T2w_SPC1.nii.gz'))
    t2_by_id = {}
    for p in t2_files:
        sid = _subject_id(p)
        if sid:
            t2_by_id.setdefault(sid, []).append(p)

    masks_by_id = {}
    for p in Path(mask_root).rglob('*'):
        if p.is_file() and _mask_candidate(p):
            sid = _subject_id(p)
            if sid:
                masks_by_id.setdefault(sid, []).append(p)

    absent_ids = _ids_from_file(absent_ids_file)
    review_ids = _ids_from_file(review_ids_file)
    statuses = {}
    if status_csv:
        with open(status_csv, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                sid = str(row.get('subject_id') or row.get('ID') or '').strip()
                if sid:
                    if sid in statuses:
                        raise ValueError('Duplicate subject ID in status CSV: ' + sid)
                    statuses[sid] = row

    recorded_ids = {sid for sid, row in statuses.items()
                    if str(row.get('presence', '')).strip().lower() in
                    ('present', 'absent', 'uncertain')}
    all_ids = sorted(set(masks_by_id) | absent_ids | review_ids | recorded_ids)
    rows = []
    for sid in all_ids:
        images = t2_by_id.get(sid, [])
        masks = masks_by_id.get(sid, [])
        status = statuses.get(sid, {})
        presence = str(status.get('presence', '')).strip().lower()
        if not presence:
            presence = 'absent' if sid in absent_ids else ('uncertain' if sid in review_ids else 'present')
        qc = str(status.get('qc', '')).strip().lower() or 'provisional'
        if sid in review_ids or len(images) != 1 or len(masks) > 1:
            qc = 'needs_review'
        if len(masks) == 0 and presence == 'present':
            qc = 'needs_review'
        if presence not in ('present', 'absent', 'uncertain'):
            qc = 'needs_review'
        if presence == 'uncertain':
            qc = 'needs_review'
        extra_note = []
        if len(images) != 1:
            extra_note.append(f'{len(images)} matching SPC1 T2s')
        if len(masks) > 1:
            extra_note.append(f'{len(masks)} possible masks (choose one manually)')
        if len(masks) == 0 and presence == 'present':
            extra_note.append('missing positive mask')
        rows.append(dict(subject_id=sid, presence=presence, qc=qc,
                         split=str(status.get('split', '')).strip().lower() or 'dev',
                         source_t2=str(images[0]) if len(images) == 1 else '',
                         mask_path=str(masks[0]) if len(masks) == 1 else '',
                         segment_id=str(status.get('segment_id', '')).strip(),
                         label_value=str(status.get('label_value', '')).strip(),
                         notes='; '.join(filter(None, [str(status.get('notes', '')).strip(), *extra_note]))))

    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'[ROI MANIFEST] {len(rows)} subjects: {out}')
    print('  Presence counts:', {kind: sum(r['presence'] == kind for r in rows)
                                  for kind in ('present', 'absent', 'uncertain')})
    print('  Review the qc, split, presence, segment_id and mask_path columns.')
    print('  Missing masks are NEVER automatically classified as CSP absent.')
    return rows


def measure_subject(image_kji, affine, mask_kji=None, presence='present',
                    subject_id='', fg_cfg=CropSettings()):
    """Measure extrema in RAS; positive voxel volume & physical-face bounds."""
    affine = _validate_geometry(affine)
    fg_lo, fg_hi, threshold = foreground_ras_bounds(image_kji, affine, fg_cfg)
    span = fg_hi - fg_lo
    fg_cx = float(0.5 * (fg_lo[0] + fg_hi[0]))
    if presence not in ('present', 'absent'):
        raise ValueError('Presence must be present or absent: ' + presence)
    result = dict(subject_id=str(subject_id), presence=presence,
                  source_shape_kji=list(np.shape(image_kji)),
                  fg_lo=fg_lo.tolist(), fg_hi=fg_hi.tolist(),
                  fg_center_x=fg_cx, fg_threshold=float(threshold),
                  mask_voxels=0, mask_volume_mm3=0.0,
                  mask_ras_lo=None, mask_ras_hi=None,
                  rel_lo=None, rel_hi=None, fixed_lo=None, fixed_hi=None,
                  lr_mm=None, lr_fraction=None)
    if mask_kji is None:
        if presence == 'present':
            raise ValueError('Present case requires a mask')
        return result
    mask = np.asarray(mask_kji)
    if mask.shape != np.shape(image_kji):
        raise ValueError('Reference mask shape differs from original T2')
    kji = np.argwhere(mask > 0)
    if presence == 'absent':
        if len(kji):
            raise ValueError('Confirmed absent case has positive mask voxels')
        return result
    if not len(kji):
        raise ValueError('Present case has an empty reference mask')
    ijk = kji[:, [2, 1, 0]]
    world = ijk @ affine[:3, :3].T + affine[:3, 3]
    # Include the full voxel footprint, not only its center. Conservative
    # for oblique source grids and small one-voxel CSP islands.
    half_extent = 0.5 * np.abs(affine[:3, :3]).sum(axis=1)
    lo = world.min(axis=0) - half_extent
    hi = world.max(axis=0) + half_extent
    result.update(mask_voxels=int(len(kji)),
                  mask_volume_mm3=float(len(kji) * abs(np.linalg.det(affine[:3, :3]))),
                  mask_ras_lo=lo.tolist(), mask_ras_hi=hi.tolist(),
                  rel_lo=((lo - fg_lo) / span).tolist(),
                  rel_hi=((hi - fg_lo) / span).tolist(),
                  fixed_lo=(lo - fg_lo).tolist(),
                  fixed_hi=(hi - fg_lo).tolist(),
                  lr_mm=float(max(fg_cx - lo[0], hi[0] - fg_cx)),
                  lr_fraction=float(max(fg_cx - lo[0], hi[0] - fg_cx) / span[0]))
    return result


def fit_rule(measurements, mode, margin_mm=8.0):
    """Fit common extrema using development positive masks only."""
    if mode not in MODES:
        raise ValueError('Mode must be fixed_mm or proportional')
    if not (np.isfinite(margin_mm) and margin_mm >= 0):
        raise ValueError('Margin must be finite and non-negative')
    positives = [m for m in measurements if m['presence'] == 'present']
    if not positives:
        raise ValueError('Need at least one QC-approved development positive mask')
    if mode == 'fixed_mm':
        lows = np.array([m['fixed_lo'] for m in positives], float)
        highs = np.array([m['fixed_hi'] for m in positives], float)
        half_width = max(m['lr_mm'] for m in positives)
    else:
        lows = np.array([m['rel_lo'] for m in positives], float)
        highs = np.array([m['rel_hi'] for m in positives], float)
        half_width = max(m['lr_fraction'] for m in positives)
    return dict(version=1, mode=mode,
                anchor='robust_head_foreground_not_intracranial_mask',
                coordinate_system='RAS_mm',
                lr_half_width=float(half_width),
                y_lo=float(lows[:, 1].min()), y_hi=float(highs[:, 1].max()),
                z_lo=float(lows[:, 2].min()), z_hi=float(highs[:, 2].max()),
                margin_mm=float(margin_mm),
                training_positive_count=len(positives),
                provenance='development_positive_extrema_only',
                status='UNVALIDATED_CANDIDATE')


def rule_ras_box(fg_lo, fg_hi, rule):
    """Apply one pooled rule to a new subject's anatomy; keep margins in mm."""
    lo = np.asarray(fg_lo, float)
    hi = np.asarray(fg_hi, float)
    span = hi - lo
    if lo.shape != (3,) or hi.shape != (3,) or np.any(span <= 0):
        raise ValueError('Bad foreground anatomy bounds')
    mode = rule['mode']
    if mode not in MODES:
        raise ValueError('Unknown rule mode')
    half_width = float(rule['lr_half_width']) * (1 if mode == 'fixed_mm' else span[0])
    cx = 0.5 * (lo[0] + hi[0])
    margin = float(rule['margin_mm'])
    box_lo = np.array([cx - half_width - margin,
                       lo[1] + rule['y_lo'] * (1 if mode == 'fixed_mm' else span[1]) - margin,
                       lo[2] + rule['z_lo'] * (1 if mode == 'fixed_mm' else span[2]) - margin])
    box_hi = np.array([cx + half_width + margin,
                       lo[1] + rule['y_hi'] * (1 if mode == 'fixed_mm' else span[1]) + margin,
                       lo[2] + rule['z_hi'] * (1 if mode == 'fixed_mm' else span[2]) + margin])
    if np.any(box_hi <= box_lo):
        raise ValueError('Invalid calibrated crop box')
    return box_lo, box_hi


def evaluate_subject_rule(measurement, rule, affine, mask_kji=None, mask_ijk=None):
    """Report per-face containment; does not modify source image data."""
    box_lo, box_hi = rule_ras_box(measurement['fg_lo'], measurement['fg_hi'], rule)
    start, end, clipped = native_ijk_crop_for_ras_box(box_lo, box_hi,
                                                     affine, measurement['source_shape_kji'])
    shape = np.asarray(measurement['source_shape_kji'][::-1], dtype=int)
    result = dict(subject_id=measurement['subject_id'], presence=measurement['presence'],
                  mode=rule['mode'], whole_mask_contained=None, minimum_margin_mm=None,
                  face_margins_mm=None, fraction_inside=None,
                  cropped_fraction=float(np.prod(end-start) / np.prod(shape)),
                  start_ijk=start.tolist(), end_ijk=end.tolist(),
                  requested_ras_lo=box_lo.tolist(), requested_ras_hi=box_hi.tolist(),
                  clipped=bool(clipped))
    if measurement['presence'] == 'present':
        if mask_kji is None and mask_ijk is None:
            raise ValueError('Mask required to evaluate positive containment')
        audit = (_evaluate_sparse_mask(mask_ijk, start, end, affine)
                 if mask_ijk is not None else
                 evaluate_mask_containment(mask_kji, start, end, affine))
        for key in ('whole_mask_contained', 'minimum_margin_mm', 'face_margins_mm', 'fraction_inside'):
            result[key] = audit[key]
    return result



def _evaluate_sparse_mask(ijk, start, end, affine):
    """Exact voxel inclusion without retaining a full 3D binary mask in RAM."""
    idx = np.asarray(ijk, dtype=np.int32).reshape((-1, 3))
    if not len(idx):
        raise ValueError('Positive mask unexpectedly empty')
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    inside = np.all((idx >= start) & (idx < end), axis=1)
    mm_step = 1 / np.linalg.norm(np.linalg.inv(affine[:3, :3]), axis=1)
    min_ijk, max_ijk = idx.min(axis=0), idx.max(axis=0)
    low = (min_ijk - (start - 0.5)) * mm_step
    high = ((end - 0.5) - max_ijk) * mm_step
    margins = dict(zip(('i_low','j_low','k_low','i_high','j_high','k_high'),
                       [float(v) for v in np.r_[low,high]]))
    return dict(whole_mask_contained=bool(np.all(inside)),
                fraction_inside=float(np.mean(inside)),
                minimum_margin_mm=float(min(margins.values())),
                face_margins_mm=margins)

def _report_csv(path, records):
    if not records:
        return
    fields = list(records[0].keys())
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v
                        for k, v in r.items()})


def _load_reference_mask(path, ref_volume, segment_id='', label_value=''):
    """Load Slicer .seg.nrrd or explicit native-grid label volume safely."""
    import slicer
    p = Path(path)
    node = None
    if not p.is_file():
        raise FileNotFoundError('Missing manual mask: ' + str(p))
    try:
        if p.name.lower().endswith('.seg.nrrd'):
            node = slicer.util.loadSegmentation(str(p), {'show': False})
            if node is None:
                raise RuntimeError('Failed to load segmentation: ' + str(p))
            if node.GetParentTransformNode() is not None:
                raise ValueError('Segmentation has an unhardened parent transform')
            seg = node.GetSegmentation()
            if seg.GetNumberOfSegments() == 0:
                return np.zeros_like(slicer.util.arrayFromVolume(ref_volume), dtype=np.uint8)
            if segment_id:
                sid = segment_id
                if seg.GetSegment(sid) is None:
                    sid = seg.GetSegmentIdBySegmentName(segment_id)
                if not sid:
                    raise ValueError('Cannot find segment ID/name ' + segment_id)
            else:
                if seg.GetNumberOfSegments() != 1:
                    raise ValueError('Multiple segments; specify segment_id (triangular CSP only)')
                sid = seg.GetNthSegmentID(0)
            mask = slicer.util.arrayFromSegmentBinaryLabelmap(node, sid, ref_volume)
            if mask.shape != slicer.util.arrayFromVolume(ref_volume).shape:
                raise ValueError('Resampled segment shape does not match original T2')
            return mask
        node = slicer.util.loadLabelVolume(str(p), {'show': False})
        if node is None:
            raise RuntimeError('Failed to load label volume: ' + str(p))
        if node.GetParentTransformNode() is not None:
            raise ValueError('Label volume has an unhardened transform')
        if not np.allclose(_slicer_ijk_to_ras(node), _slicer_ijk_to_ras(ref_volume), atol=1e-3):
            raise ValueError('Labelmap affine does not match original T2 native grid')
        arr = np.asarray(slicer.util.arrayFromVolume(node))
        if arr.shape != slicer.util.arrayFromVolume(ref_volume).shape:
            raise ValueError('Labelmap dimensions do not match original T2')
        nonzero = np.unique(arr[arr != 0])
        if label_value:
            mask = (arr == float(label_value))
            if nonzero.size and float(label_value) not in nonzero:
                raise ValueError('Requested label_value not found in label volume')
        else:
            if len(nonzero) > 1:
                raise ValueError('Multi-label NIfTI: specify label_value for triangular CSP')
            mask = (arr != 0)
        return np.array(mask, dtype=np.uint8, copy=True)
    finally:
        if node is not None:
            slicer.mrmlScene.RemoveNode(node)


def _read_manifest(manifest_csv):
    with open(manifest_csv, newline='', encoding='utf-8-sig') as f:
        records = list(csv.DictReader(f))
    if not records:
        raise ValueError('Manifest has no subjects')
    ids = [str(r.get('subject_id', '')).strip() for r in records]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError('Manifest subject_ids must be unique and non-empty')
    return records


def calibrate_roi_from_manifest(manifest_csv, output_dir, margin_mm=8.0,
                                include_provisional=True, foreground_cfg=CropSettings(),
                                unlock_holdout=False):
    """Calibrate both candidates and evaluate DEV, HOLDOUT, and DEV-LOO.

    IMPORTANT: holdout rows are not opened by default. Set unlock_holdout=True
    once the rule is frozen to assess it independently, without further tuning.
    """
    import slicer
    from collections import Counter

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries = _read_manifest(manifest_csv)
    measures = []
    tests = []
    errors = []
    withheld = []
    cached = []
    for index, row in enumerate(entries, 1):
        sid = row['subject_id'].strip()
        pres = row.get('presence', '').strip().lower()
        qc = row.get('qc', '').strip().lower()
        split = row.get('split', 'dev').strip().lower() or 'dev'
        if split not in ('dev', 'holdout'):
            errors.append(dict(subject_id=sid, error='invalid split '+split))
            continue
        if split == 'holdout' and not unlock_holdout:
            withheld.append(sid)
            continue
        if pres == 'uncertain' or qc in ('needs_review', 'fail', 'exclude', 'excluded'):
            errors.append(dict(subject_id=sid, error='SKIPPED_NEEDS_REVIEW'))
            continue
        if qc != 'pass' and not (include_provisional and qc == 'provisional'):
            errors.append(dict(subject_id=sid, error='SKIPPED_NO_QC_PASS'))
            continue
        if pres not in ('present', 'absent'):
            errors.append(dict(subject_id=sid, error='invalid presence='+pres))
            continue
        src = Path(row.get('source_t2', ''))
        mask_file = row.get('mask_path', '').strip()
        if not src.is_file():
            errors.append(dict(subject_id=sid, error='missing native T2 path: '+str(src)))
            continue
        volume = None
        try:
            volume = slicer.util.loadVolume(str(src), {'show': False})
            if volume is None:
                raise RuntimeError('Could not load T2')
            if volume.GetParentTransformNode() is not None:
                raise ValueError('T2 has parent transform; harden/validate first')
            affine = _slicer_ijk_to_ras(volume)
            img = slicer.util.arrayFromVolume(volume)
            mask = (_load_reference_mask(mask_file, volume, row.get('segment_id', '').strip(),
                                         row.get('label_value', '').strip()) if mask_file else None)
            data = measure_subject(img, affine, mask, pres, sid, foreground_cfg)
            data['qc'] = qc
            data['split'] = split
            data['mask_path'] = mask_file
            data['notes'] = str(row.get('notes', '')).strip()
            measures.append(data)
            # Store only foreground CSP voxel coordinates, not 65 full-sized
            # 3D masks (which could exceed the laptop's available memory).
            coords = (np.argwhere(mask > 0)[:, [2, 1, 0]].astype(np.int32)
                      if mask is not None and pres == 'present' else None)
            cached.append((data, affine.copy(), coords))
            print(f'[ROI {index}/{len(entries)}] {sid} {pres} {data["mask_volume_mm3"]:.1f} mm3')
        except Exception as exc:
            errors.append(dict(subject_id=sid, error=str(exc)))
            print('[ROI ERROR]', sid, exc)
        finally:
            if volume is not None:
                slicer.mrmlScene.RemoveNode(volume)

    dev = [m for m in measures if m['split'] == 'dev']
    holdout = [m for m in measures if m['split'] == 'holdout']
    if not any(m['presence'] == 'present' for m in dev):
        _report_csv(out/'errors.csv', errors)
        raise RuntimeError('No valid development positive masks; see errors.csv')
    rules = {mode: fit_rule(dev, mode, margin_mm) for mode in MODES}
    for mode, rule in rules.items():
        rule['training_subjects'] = len(dev)
        rule['heldout_subjects'] = len(holdout)
        rule['includes_provisional_qc'] = any(x['qc'] != 'pass' for x in dev)
    for data, affine, mask_ijk in cached:
        for rule in rules.values():
            try:
                result = evaluate_subject_rule(data, rule, affine, mask_ijk=mask_ijk)
                result['split'] = data['split']
                result['qc'] = data['qc']
                tests.append(result)
            except Exception as exc:
                errors.append(dict(subject_id=data['subject_id'], error='Rule evaluation: '+str(exc)))

    # Leave-one-subject-out stress test on development positives. Not a substitute
    # for an independent holdout, but reveals how frequently extrema are driven by
    # one unusual individual (such as an unusually large CSP).
    loo = []
    dev_positives = [x for x in cached if x[0]['split'] == 'dev' and x[0]['presence'] == 'present']
    if len(dev_positives) >= 2:
        for data, affine, mask_ijk in dev_positives:
            training = [m for m in dev if m['subject_id'] != data['subject_id']]
            for mode in MODES:
                fitted = fit_rule(training, mode, margin_mm)
                ev = evaluate_subject_rule(data, fitted, affine, mask_ijk=mask_ijk)
                loo.append({k: ev[k] for k in ('subject_id', 'mode', 'whole_mask_contained',
                                               'minimum_margin_mm', 'cropped_fraction')})
    # All individual identifiers remain in local reports; only aggregate
    # descriptions belong in the public repository.
    _report_csv(out/'subject_measurements.csv', measures)
    _report_csv(out/'rule_evaluations.csv', tests)
    _report_csv(out/'leave_one_subject_out.csv', loo)
    _report_csv(out/'errors.csv', errors)
    ranked = sorted((m for m in measures if m['presence'] == 'present'),
                    key=lambda m: m['mask_volume_mm3'], reverse=True)
    _report_csv(out/'largest_csp_ranked.csv', [
        dict(rank=i, subject_id=m['subject_id'], qc=m['qc'], split=m['split'],
             volume_mm3=m['mask_volume_mm3'], voxels=m['mask_voxels'],
             RAS_span_mm=[float(b-a) for a,b in zip(m['mask_ras_lo'], m['mask_ras_hi'])],
             lr_distance_mm=m['lr_mm'], notes=m['notes'])
        for i,m in enumerate(ranked, 1)])
    manifest_summary = dict(n_manifest=len(entries), n_read=len(measures),
                            n_errors=len(errors), n_dev=len(dev), n_holdout_evaluated=len(holdout),
                            n_holdout_reserved=len(withheld),
                            dev_positive=sum(m['presence']=='present' for m in dev),
                            dev_absent=sum(m['presence']=='absent' for m in dev),
                            qc_counter=dict(Counter(m['qc'] for m in measures)),
                            validation='EXPLORATORY only; independent holdout and mask QC required')
    (out/'calibrated_rules.json').write_text(
        json.dumps(dict(rules=rules, summary=manifest_summary,
                        foreground_cfg=asdict(foreground_cfg)), indent=2)+'\n', encoding='utf-8')
    print('[ROI CALIBRATION] Written:', out)
    print('  dev:', len(dev), 'holdout reserved:', len(withheld),
          'holdout evaluated:', len(holdout), 'errors:', len(errors))
    print('  ranked largest positive CSP:', ranked[0]['subject_id'] if ranked else 'none')
    print('  This is not approved for whole-cohort deployment without QC and holdout.')
    return {'rules': rules, 'summary': manifest_summary, 'output_dir': str(out)}


def reduce_t2_with_calibrated_rule(source_node, rules_json, output_dir,
                                   mode='proportional', overwrite=False):
    """Apply fitted geometry to a new ORIGINAL T2 without using its CSP mask."""
    import slicer
    from reduce_t2_slicer import _slicer_ijk_to_ras
    p = Path(rules_json)
    config = json.loads(p.read_text(encoding='utf-8'))
    rule = config['rules'][mode]
    fg_cfg = CropSettings(**config['foreground_cfg'])
    if source_node is None:
        raise ValueError('Select original T2, not an already-reduced T2')
    if source_node.GetParentTransformNode() is not None:
        raise ValueError('Source has parent transform; harden/validate first')
    img = slicer.util.arrayFromVolume(source_node)
    affine = _slicer_ijk_to_ras(source_node)
    fg_lo, fg_hi, _ = foreground_ras_bounds(img, affine, fg_cfg)
    box_lo, box_hi = rule_ras_box(fg_lo, fg_hi, rule)
    start, end, clipped = native_ijk_crop_for_ras_box(box_lo, box_hi, affine, img.shape)
    sub = crop_array_native(img, start, end)
    new_affine = shifted_affine(affine, start)
    source_storage = source_node.GetStorageNode()
    src_path = (Path(source_storage.GetFileName()) if source_storage and
                source_storage.GetFileName() else None)
    base = src_path.name[:-7] if src_path and src_path.name.endswith('.nii.gz') else source_node.GetName()
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / (base + '_' + mode + '_reduced.nii.gz')
    if out.exists() and not overwrite:
        raise FileExistsError('Refusing to overwrite: ' + str(out))
    node = slicer.util.addVolumeFromArray(sub, ijkToRAS=new_affine,
                                         name=base+'_'+mode+'_reduced')
    try:
        if not slicer.util.saveNode(node, str(out)):
            raise IOError('Slicer failed to save ' + str(out))
        record = dict(mode=mode, rule=rule, source_file=str(src_path) if src_path else None,
                      source_shape_kji=img.shape, cropped_shape_kji=sub.shape,
                      start_ijk=start.tolist(), end_ijk=end.tolist(),
                      requested_box_RAS=[box_lo.tolist(),box_hi.tolist()], clipped=clipped,
                      original_affine=affine.tolist(), output_affine=new_affine.tolist(),
                      retained_voxel_fraction=float(sub.size/img.size),
                      status='UNVALIDATED_RULE_UNTIL_INDEPENDENT_TEST')
        (dest/(base+'_'+mode+'_reduced.crop.json')).write_text(
            json.dumps(record, indent=2)+'\n', encoding='utf-8')
        print('[ROI APPLIED]', out, f'{100*sub.size/img.size:.2f}% voxels retained')
        return record
    finally:
        slicer.mrmlScene.RemoveNode(node)


def batch_apply_calibrated_rule(t2_root, rules_json, output_dir, mode='proportional',
                                limit=3, allow_full_cohort=False):
    """Small batch smoke test; explicit opt-in required for all 1,113 images."""
    import slicer
    if limit is None and not allow_full_cohort:
        raise ValueError('Full-cohort processing requires allow_full_cohort=True after holdout validation')
    scans = sorted(Path(t2_root).rglob('*_3T_T2w_SPC1.nii.gz'))
    if limit is not None:
        scans = scans[:int(limit)]
    if not scans:
        raise FileNotFoundError('No HCP SPC1 scans found')
    results = []
    for scan in scans:
        node = None
        try:
            node = slicer.util.loadVolume(str(scan), {'show': False})
            if node is None:
                raise RuntimeError('Slicer failed to load original T2')
            record = reduce_t2_with_calibrated_rule(node, rules_json, output_dir, mode)
            results.append(dict(source_file=str(scan), status='SAVED_UNVALIDATED',
                                retained_fraction=record['retained_voxel_fraction'], error=''))
        except Exception as err:
            print('[ROI CROP FAILED]', scan, err)
            results.append(dict(source_file=str(scan), status='FAILED',
                                retained_fraction='', error=str(err)))
        finally:
            if node is not None:
                slicer.mrmlScene.RemoveNode(node)
    _report_csv(Path(output_dir)/'batch_calibrated_crop_report.csv', results)
    print('[ROI BATCH]', len(results), 'processed;',
          sum(r['status']=='FAILED' for r in results), 'failed')
    return results

