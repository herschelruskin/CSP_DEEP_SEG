"""Synthetic crop geometry tests; do not require Slicer or private HCP scans."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reduce_t2_slicer import (CropSettings, calculate_crop,
                             crop_array_native, evaluate_mask_containment,
                             native_ijk_crop_for_ras_box, shifted_affine)


def make_toy():
    image = np.zeros((100, 120, 140), dtype=np.float32)
    image[10:90, 10:110, 10:130] = 100
    # RAS, anisotropic and left-right flipped axis, with translational offset.
    affine = np.array([[-0.7, 0, 0, 48], [0, 1.1, 0, -60],
                       [0, 0, 0.8, -40], [0, 0, 0, 1]], dtype=float)
    return image, affine


def test_cropped_voxels_and_world_coordinates_unchanged():
    image, affine = make_toy()
    crop, new_affine, meta = calculate_crop(image, affine)
    start = meta['start_ijk_inclusive']
    end = meta['end_ijk_exclusive']
    assert crop.shape == (end[2]-start[2], end[1]-start[1], end[0]-start[0])
    assert np.array_equal(crop, crop_array_native(image, start, end))
    assert 0 < meta['retained_voxel_fraction'] < 1
    for crop_ijk in ([0, 0, 0], [crop.shape[2]-1, crop.shape[1]-1, crop.shape[0]-1]):
        crop_ijk = np.asarray(crop_ijk, dtype=float)
        native_ijk = crop_ijk + np.asarray(start)
        assert np.allclose(new_affine[:3, :3] @ crop_ijk + new_affine[:3, 3],
                           affine[:3, :3] @ native_ijk + affine[:3, 3])


def test_mask_inclusion_reports_real_failure_and_empty_case():
    image, affine = make_toy()
    crop, new_affine, meta = calculate_crop(image, affine)
    start, end = meta['start_ijk_inclusive'], meta['end_ijk_exclusive']
    pos = np.zeros_like(image, dtype='uint8')
    center = (np.asarray(start)+np.asarray(end))//2
    pos[center[2], center[1], center[0]] = 1
    result = evaluate_mask_containment(pos, start, end, affine)
    assert result['whole_mask_contained'] is True
    assert result['fraction_inside'] == 1
    assert result['minimum_margin_mm'] > 0
    pos[0, 0, 0] = 1
    result = evaluate_mask_containment(pos, start, end, affine)
    assert result['whole_mask_contained'] is False
    assert 0 < result['fraction_inside'] < 1
    assert result['minimum_margin_mm'] < 0
    absent = evaluate_mask_containment(np.zeros_like(pos), start, end, affine)
    assert absent['status'] == 'empty-reference'
    assert absent['whole_mask_contained'] is None


def test_oblique_box_conservatively_contains_all_world_corner_voxels():
    theta = np.deg2rad(23)
    affine = np.array([[np.cos(theta), -np.sin(theta), 0, -60],
                       [np.sin(theta), np.cos(theta), 0, -40],
                       [0, 0, 1.2, -50], [0, 0, 0, 1]], float)
    lo, hi = np.array([-15, -10, -5]), np.array([10, 30, 24])
    start, end, _ = native_ijk_crop_for_ras_box(lo, hi, affine, (120, 140, 160))
    assert np.all(end > start)
    for i in range(start[0], end[0]):
        for j in range(start[1], end[1]):
            for k in range(start[2], end[2]):
                ras = affine[:3, :3] @ [i, j, k] + affine[:3, 3]
                if np.all(ras >= lo) and np.all(ras <= hi):
                    assert np.all(np.array([i, j, k]) >= start)
                    assert np.all(np.array([i, j, k]) < end)


def test_settings_and_singularity_checks():
    image, affine = make_toy()
    import pytest
    with pytest.raises(ValueError):
        calculate_crop(image, affine, CropSettings(posterior_trim_fraction=0.8, anterior_trim_fraction=0.3))
    with pytest.raises(ValueError):
        calculate_crop(image, np.zeros((4, 4)))

