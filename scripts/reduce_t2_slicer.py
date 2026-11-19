r"""Generate conservative, native-voxel CSP search crops from HCP T2 volumes.

Run inside the 3D Slicer Python console; NumPy and VTK ship with Slicer.
This is a REGION-OF-INTEREST generator, not a CSP detector.

Recommended first run (paste ONE line into Slicer's Python console):
exec(open(r'D:\CSP_DEEP_SEG\CSP_DEEP_SEG\scripts\reduce_t2_slicer.py', encoding='utf-8').read()); reduce_active_t2(r'D:\CSP_DEEP_SEG\derived\reduced_t2')

Batch smoke test (first 3 SPC1 scans, from Slicer's Python console):
exec(open(r'D:\CSP_DEEP_SEG\CSP_DEEP_SEG\scripts\reduce_t2_slicer.py', encoding='utf-8').read()); batch_reduce_t2(r'D:\CSP_DEEP_SEG\T2w', r'D:\CSP_DEEP_SEG\derived\reduced_t2', limit=3)

WARNING: The default crop is a starting hypothesis, not validated anatomy.
Do not use it for model training until the native-space reference CSP masks
have been audited for complete containment and sufficient six-face margins.
"""

from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
import csv
import json

import numpy as np


@dataclass(frozen=True)
class CropSettings:
    # Relative to coarse foreground bounds in anatomical RAS coordinates.
    # Keep the LEFT-RIGHT interval around a coarse estimated midline.
    lr_half_width_mm: float = 35.0
    posterior_trim_fraction: float = 0.20
    anterior_trim_fraction: float = 0.05
    inferior_trim_fraction: float = 0.15
    superior_trim_fraction: float = 0.03
    sample_stride: int = 4
    foreground_percentile: float = 30.0
    bound_percentiles: tuple = (1.0, 99.0)
    # These are conservative development defaults; fit/tune on DEV ONLY.


def _validate_settings(cfg):
    if cfg.lr_half_width_mm <= 0 or cfg.sample_stride < 1:
        raise ValueError('LR half-width must be positive; stride must be >=1')
    for value in (cfg.posterior_trim_fraction, cfg.anterior_trim_fraction,
                  cfg.inferior_trim_fraction, cfg.superior_trim_fraction):
        if not (0 <= value < 1):
            raise ValueError('All trim fractions must be in [0, 1)')
    if (cfg.posterior_trim_fraction + cfg.anterior_trim_fraction >= 1 or
            cfg.inferior_trim_fraction + cfg.superior_trim_fraction >= 1):
        raise ValueError('Opposing trim fractions must sum to < 1')
    if not (0 <= cfg.foreground_percentile <= 100):
        raise ValueError('foreground_percentile must be between 0 and 100')
    lo, hi = cfg.bound_percentiles
    if not (0 <= lo < hi <= 100):
        raise ValueError('bound_percentiles must satisfy 0 <= lo < hi <= 100')


def _validate_geometry(ijk_to_ras):
    mat = np.asarray(ijk_to_ras, dtype=np.float64)
    if mat.shape != (4, 4) or not np.isfinite(mat).all():
        raise ValueError('Expected a finite 4x4 IJK-to-RAS matrix')
    if abs(np.linalg.det(mat[:3, :3])) < 1e-8:
        raise ValueError('Image geometry is singular')
    return mat


def _ras_from_ijk(ijk, affine):
    return np.asarray(ijk) @ affine[:3, :3].T + affine[:3, 3]


def foreground_ras_bounds(image_kji, ijk_to_ras, cfg=CropSettings()):
    """Approximate head/foreground RAS bounds using sparse native voxels.

    Does not require skull stripping or an expensive registration. The exact
    estimate is deliberately coarse; mask-containment validation is required.
    """
    _validate_settings(cfg)
    affine = _validate_geometry(ijk_to_ras)
    arr = np.asarray(image_kji)
    if arr.ndim != 3 or min(arr.shape) < 2:
        raise ValueError('Expected a three-dimensional scalar volume')
    s = cfg.sample_stride
    sampled = arr[::s, ::s, ::s]
    positive = sampled[np.isfinite(sampled) & (sampled > 0)]
    if positive.size < 100:
        raise ValueError('Not enough positive sampled voxels; inspect T2/foreground')
    threshold = np.percentile(positive, cfg.foreground_percentile)
    support = np.isfinite(sampled) & (sampled > threshold)
    # A constant-valued synthetic/test image has no values strictly greater
    # than its percentile. Also support quantized real scans gracefully.
    if np.count_nonzero(support) < 100:
        support = np.isfinite(sampled) & (sampled >= threshold) & (sampled > 0)
    if np.count_nonzero(support) < 100:
        raise ValueError('Foreground threshold removed almost all sampled voxels')
    kji = np.argwhere(support).astype(np.float64)
    ijk = kji[:, [2, 1, 0]] * s
    ras = _ras_from_ijk(ijk, affine)
    lo, hi = np.percentile(ras, cfg.bound_percentiles, axis=0)
    if np.any(hi <= lo):
        raise ValueError('Degenerate foreground RAS bounding coordinates')
    return lo, hi, float(threshold)


def desired_ras_roi(fg_lo, fg_hi, cfg=CropSettings()):
    """Construct six RAS faces based on broad foreground anatomical extents.

    RAS: x increases toward right, y increases anteriorly, z increases superiorly.
    """
    _validate_settings(cfg)
    lo = np.asarray(fg_lo, dtype=float)
    hi = np.asarray(fg_hi, dtype=float)
    if lo.shape != (3,) or hi.shape != (3,) or np.any(hi <= lo):
        raise ValueError('Invalid foreground bounds')
    center_x = 0.5 * (lo[0] + hi[0])
    roi_lo = np.array([center_x - cfg.lr_half_width_mm,
                       lo[1] + cfg.posterior_trim_fraction * (hi[1] - lo[1]),
                       lo[2] + cfg.inferior_trim_fraction * (hi[2] - lo[2])])
    roi_hi = np.array([center_x + cfg.lr_half_width_mm,
                       hi[1] - cfg.anterior_trim_fraction * (hi[1] - lo[1]),
                       hi[2] - cfg.superior_trim_fraction * (hi[2] - lo[2])])
    if np.any(roi_hi <= roi_lo):
        raise ValueError('Invalid resulting ROI bounds')
    return roi_lo, roi_hi


def native_ijk_crop_for_ras_box(ras_lo, ras_hi, ijk_to_ras, shape_kji):
    """Conservatively enclose an RAS-aligned box in native IJK array indices.

    Bounding the eight transformed corners can enlarge the actual box for
    oblique images; this is intentional. No MRI interpolation or resampling.
    Returns IJK start (inclusive), end (exclusive) and a clipped-axis flag.
    """
    affine = _validate_geometry(ijk_to_ras)
    ras_lo = np.asarray(ras_lo, dtype=float)
    ras_hi = np.asarray(ras_hi, dtype=float)
    if np.any(ras_hi <= ras_lo):
        raise ValueError('Malformed RAS crop box')
    shape_kji = tuple(int(x) for x in shape_kji)
    if len(shape_kji) != 3:
        raise ValueError('Expected KJI image shape')
    dims_ijk = np.asarray(shape_kji[::-1], dtype=np.int64)
    corners = np.array(list(product(*zip(ras_lo, ras_hi))), dtype=float)
    inverse = np.linalg.inv(affine)
    ijk_corners = _ras_from_ijk(corners, inverse)
    # Include boundary voxels; interval is inclusive start, exclusive end.
    raw_start = np.floor(np.min(ijk_corners, axis=0) - 0.5).astype(int)
    raw_end = np.ceil(np.max(ijk_corners, axis=0) + 1.5).astype(int)
    start = np.maximum(0, raw_start)
    end = np.minimum(dims_ijk, raw_end)
    if np.any(end <= start):
        raise ValueError('Requested ROI does not overlap native image')
    clipped = bool(np.any(start != raw_start) or np.any(end != raw_end))
    return start, end, clipped


def crop_array_native(image_kji, start_ijk, end_ijk):
    i0, j0, k0 = [int(v) for v in start_ijk]
    i1, j1, k1 = [int(v) for v in end_ijk]
    return np.asarray(image_kji)[k0:k1, j0:j1, i0:i1].copy()


def shifted_affine(ijk_to_ras, start_ijk):
    affine = _validate_geometry(ijk_to_ras)
    origin = np.eye(4, dtype=np.float64)
    origin[:3, 3] = np.asarray(start_ijk, dtype=float)
    return affine @ origin


def evaluate_mask_containment(mask_kji, start_ijk, end_ijk, ijk_to_ras):
    """Whole-mask inclusion and signed distance to each native crop face.

    Distances are measured perpendicular to each image-axis face, accounting
    for oblique affines. Empty masks are valid absent cases (not positives).
    """
    mask = np.asarray(mask_kji)
    idx = np.argwhere(mask > 0)
    if idx.size == 0:
        return {'status': 'empty-reference', 'n_mask_voxels': 0,
                'whole_mask_contained': None, 'fraction_inside': None,
                'face_margins_mm': None, 'minimum_margin_mm': None}
    affine = _validate_geometry(ijk_to_ras)
    ijk = idx[:, [2, 1, 0]]
    start = np.asarray(start_ijk, dtype=float)
    end = np.asarray(end_ijk, dtype=float)
    inside = np.all((ijk >= start) & (ijk < end), axis=1)
    # For plane IJK_i = constant, 1 / ||inverse_linear_row_i|| is the mm
    # physical distance between adjacent planes in the original MRI.
    inv_linear = np.linalg.inv(affine[:3, :3])
    plane_mm_per_index = 1 / np.linalg.norm(inv_linear, axis=1)
    min_ijk, max_ijk = ijk.min(axis=0), ijk.max(axis=0)
    margin_low = (min_ijk - (start - 0.5)) * plane_mm_per_index
    margin_high = ((end - 0.5) - max_ijk) * plane_mm_per_index
    margins = dict(zip(['i_low', 'j_low', 'k_low', 'i_high', 'j_high', 'k_high'],
                       [float(x) for x in np.r_[margin_low, margin_high]]))
    return {'status': 'positive-reference', 'n_mask_voxels': int(len(idx)),
            'whole_mask_contained': bool(np.all(inside)),
            'fraction_inside': float(np.mean(inside)),
            'face_margins_mm': margins,
            'minimum_margin_mm': float(min(margins.values()))}


def calculate_crop(image_kji, ijk_to_ras, cfg=CropSettings(), mask_kji=None):
    """Pure NumPy core; safe to unit-test without Slicer or any real HCP files."""
    fg_lo, fg_hi, threshold = foreground_ras_bounds(image_kji, ijk_to_ras, cfg)
    ras_lo, ras_hi = desired_ras_roi(fg_lo, fg_hi, cfg)
    start, end, clipped = native_ijk_crop_for_ras_box(
        ras_lo, ras_hi, ijk_to_ras, np.shape(image_kji))
    original = np.asarray(image_kji)
    cropped = crop_array_native(original, start, end)
    new_affine = shifted_affine(ijk_to_ras, start)
    out = {
        'settings': asdict(cfg),
        'source_shape_kji': list(original.shape),
        'output_shape_kji': list(cropped.shape),
        'start_ijk_inclusive': start.astype(int).tolist(),
        'end_ijk_exclusive': end.astype(int).tolist(),
        'foreground_ras_lo_mm': fg_lo.tolist(),
        'foreground_ras_hi_mm': fg_hi.tolist(),
        'requested_roi_ras_lo_mm': ras_lo.tolist(),
        'requested_roi_ras_hi_mm': ras_hi.tolist(),
        'source_ijk_to_ras': np.asarray(ijk_to_ras).tolist(),
        'output_ijk_to_ras': new_affine.tolist(),
        'foreground_threshold': threshold,
        'requested_roi_exceeds_image': clipped,
        'retained_voxel_fraction': float(cropped.size / original.size),
        'mask_audit': evaluate_mask_containment(mask_kji, start, end, ijk_to_ras)
                      if mask_kji is not None else None,
        'validation_status': 'UNVALIDATED DEFAULT: audit reference masks before training',
    }
    return cropped, new_affine, out


def _slicer_ijk_to_ras(volume_node):
    import vtk
    m = vtk.vtkMatrix4x4()
    volume_node.GetIJKToRASMatrix(m)
    return np.array([[m.GetElement(i, j) for j in range(4)] for i in range(4)])


def reduce_volume_t2(source_node, output_dir, cfg=CropSettings(),
                     segmentation_node=None, segment_id=None, overwrite=False,
                     keep_output_in_scene=True):
    """Crop an already loaded Slicer scalar volume and save native-grid NIfTI.

    Optional segmentation_node / segment_id must refer to a CSP reference.
    Slicer resamples its labelmap onto the source volume for evaluation only.
    The source node and source file are never modified.
    """
    import slicer
    if not source_node or not source_node.IsA('vtkMRMLScalarVolumeNode'):
        raise ValueError('Load a T2 scalar volume first')
    iname = source_node.GetName() or 'T2'
    if '_reduced' in iname.lower():
        raise ValueError('Do not crop an already reduced T2')
    if source_node.GetParentTransformNode() is not None:
        raise ValueError('T2 has a parent transform: harden/validate it before cropping')
    storage = source_node.GetStorageNode()
    source_file = Path(storage.GetFileName()) if storage and storage.GetFileName() else None
    source_base = source_file.name if source_file is not None else iname + '.nii.gz'
    base = source_base[:-7] if source_base.endswith('.nii.gz') else Path(source_base).stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (base + '_reduced.nii.gz')
    meta_path = out_dir / (base + '_reduced.crop.json')
    if out_path.exists() and not overwrite:
        raise FileExistsError('File exists (pass overwrite=True to replace): ' + str(out_path))
    arr = slicer.util.arrayFromVolume(source_node)
    affine = _slicer_ijk_to_ras(source_node)
    mask = None
    if segmentation_node is not None:
        segmentation = segmentation_node.GetSegmentation()
        if segment_id is None:
            if segmentation.GetNumberOfSegments() != 1:
                raise ValueError('Specify segment_id when segmentation has !=1 segment')
            segment_id = segmentation.GetNthSegmentID(0)
        mask = slicer.util.arrayFromSegmentBinaryLabelmap(
            segmentation_node, segment_id, source_node)
    cropped, new_affine, record = calculate_crop(arr, affine, cfg, mask)
    record['source_file'] = str(source_file) if source_file else None
    record['output_file'] = str(out_path)
    # Slicer creates the voxel array AND its native-space affine together.
    temp = slicer.util.addVolumeFromArray(cropped, ijkToRAS=new_affine,
                                         name=base + '_reduced')
    try:
        ok = slicer.util.saveNode(temp, str(out_path))
        if not ok or not out_path.is_file():
            raise IOError('3D Slicer did not save ' + str(out_path))
        meta_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print('[REDUCED T2]', out_path)
        print('  Source KJI:', arr.shape, '-> crop:', cropped.shape,
              'retained voxels:', f"{100*record['retained_voxel_fraction']:.1f}%")
        if record['mask_audit']:
            print('  CSP mask containment:', record['mask_audit'])
        if record['requested_roi_exceeds_image']:
            print('  NOTE: requested ROI extended beyond image bounds; clipped to source')
        return {'volume_node': temp if keep_output_in_scene else None,
                'output_file': str(out_path), 'metadata_file': str(meta_path),
                'record': record}
    finally:
        if not keep_output_in_scene:
            slicer.mrmlScene.RemoveNode(temp)


def reduce_active_t2(output_dir, cfg=CropSettings(), segmentation_node=None,
                     segment_id=None, overwrite=False):
    """One-call crop of the currently selected Slicer background T2 volume."""
    import slicer
    selection = slicer.app.applicationLogic().GetSelectionNode()
    source = slicer.mrmlScene.GetNodeByID(selection.GetReferenceActiveVolumeID())
    if source is None:
        raise ValueError('Select the T2 as the active/background volume in Slicer first')
    return reduce_volume_t2(source, output_dir, cfg=cfg,
                            segmentation_node=segmentation_node,
                            segment_id=segment_id, overwrite=overwrite,
                            keep_output_in_scene=True)


def batch_reduce_t2(input_root, output_dir, limit=3, cfg=CropSettings(),
                    pattern='*_3T_T2w_SPC1.nii.gz', overwrite=False):
    """Sequentially crop native HCP SPC1 files; default limit=3 smoke test.

    Set limit=None only after visual/QC review. Outputs are never added to Git.
    Source files are untouched. Every source is unloaded after processing.
    """
    import slicer
    files = sorted(Path(input_root).rglob(pattern))
    if not files:
        raise FileNotFoundError('No matching T2 files found in ' + str(input_root))
    if limit is not None:
        files = files[:int(limit)]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for source_path in files:
        original = None
        try:
            original = slicer.util.loadVolume(str(source_path), {'show': False})
            if original is None:
                raise IOError('Slicer could not load ' + str(source_path))
            result = reduce_volume_t2(original, out_dir, cfg=cfg,
                                     overwrite=overwrite,
                                     keep_output_in_scene=False)
            rows.append({'input': str(source_path), 'output': result['output_file'],
                         'status': 'GENERATED-UNVALIDATED',
                         'retained_fraction': result['record']['retained_voxel_fraction'],
                         'error': ''})
        except Exception as exc:
            print('[CROP FAILED]', source_path, ':', exc)
            rows.append({'input': str(source_path), 'output': '',
                         'status': 'FAILED', 'retained_fraction': '',
                         'error': str(exc)})
        finally:
            if original is not None:
                slicer.mrmlScene.RemoveNode(original)
    report = out_dir / 'batch_reduced_t2_report.csv'
    with report.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['input', 'output', 'status',
                                               'retained_fraction', 'error'])
        writer.writeheader()
        writer.writerows(rows)
    print('[BATCH SUMMARY]', len(rows), 'processed;',
          sum(row['status'] == 'FAILED' for row in rows), 'failed; report:', report)
    return rows

