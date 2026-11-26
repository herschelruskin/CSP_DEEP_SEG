"""Recover original NIfTI voxels for Slicer's integer-index ROI without resampling.

Slicer may flip or permute NIfTI voxel axes on import while preserving RAS
physical coordinates. Verify that its recorded source affine can be obtained
from the original NIfTI affine by an exact signed axis permutation. Reject
geometry that would require interpolation or arbitrary registration.
"""
from itertools import permutations, product

import numpy as np


def extract_original_native_crop(original, metadata):
    """Return original voxel values in the Slicer crop's native IJK order.

    original: nibabel 3D image, with its original disk-order array and affine.
    metadata: Slicer .crop.json, including original_affine and start/end_ijk.
    Raises ValueError if geometry is not a unique integer reindexing.
    """
    original_shape = tuple(int(v) for v in original.shape)
    slicer_shape = tuple(int(v) for v in metadata["source_shape_kji"][::-1])
    original_affine = np.asarray(original.affine, dtype=np.float64)
    slicer_affine = np.asarray(metadata["original_affine"], dtype=np.float64)
    if len(original_shape) != 3 or len(slicer_shape) != 3 or any(v <= 0 for v in slicer_shape):
        raise ValueError("Expected positive 3D original/Slicer source dimensions")
    if original_affine.shape != (4, 4) or slicer_affine.shape != (4, 4):
        raise ValueError("Original/Slicer affine is not a 4x4 matrix")
    if not (np.isfinite(original_affine).all() and np.isfinite(slicer_affine).all()):
        raise ValueError("Original/Slicer affine contains nonfinite coordinates")

    matches = []
    for axes in permutations(range(3)):
        if tuple(original_shape[axis] for axis in axes) != slicer_shape:
            continue
        for flips in product((False, True), repeat=3):
            transform = np.eye(4, dtype=np.float64)
            transform[:3, :3] = 0.0
            for slicer_axis, original_axis in enumerate(axes):
                transform[original_axis, slicer_axis] = -1.0 if flips[slicer_axis] else 1.0
                if flips[slicer_axis]:
                    transform[original_axis, 3] = original_shape[original_axis] - 1
            if np.allclose(original_affine @ transform, slicer_affine, atol=1e-3, rtol=0):
                matches.append((axes, flips))
    if len(matches) != 1:
        raise ValueError(
            "Original image affine/shape cannot be uniquely matched to Slicer "
            "by signed voxel-axis reindexing (matches=%d)" % len(matches)
        )

    axes, flips = matches[0]
    start = np.asarray(metadata["start_ijk"], dtype=int)
    end = np.asarray(metadata["end_ijk"], dtype=int)
    if (start.shape != (3,) or end.shape != (3,)
            or np.any(start < 0) or np.any(end <= start)
            or np.any(end > np.asarray(slicer_shape))):
        raise ValueError("Invalid crop indices in Slicer .crop.json")

    original_slices = [None] * 3
    for slicer_axis, original_axis in enumerate(axes):
        lo, hi = int(start[slicer_axis]), int(end[slicer_axis])
        if flips[slicer_axis]:
            length = original_shape[original_axis]
            original_slices[original_axis] = slice(length - hi, length - lo)
        else:
            original_slices[original_axis] = slice(lo, hi)
    roi = np.asarray(original.dataobj[tuple(original_slices)])
    roi = np.transpose(roi, axes)
    for slicer_axis, is_flipped in enumerate(flips):
        if is_flipped:
            roi = np.flip(roi, axis=slicer_axis)
    if roi.shape != tuple(end - start):
        raise ValueError("Reindexed native source crop shape differs from .crop.json")
    return roi
