import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch

spec = importlib.util.spec_from_file_location('csp25d_baseline', Path(__file__).parents[1] / 'scripts' / 'csp25d_baseline.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_model_preserves_odd_coronal_shape():
    net = m.CoronalUNet25D(slices=7, width=16)
    with torch.no_grad():
        y = net(torch.randn(1, 7, 73, 55))
    assert tuple(y.shape) == (1, 1, 73, 55)


def test_stack_coronal_center_and_edge_clamping():
    x = np.arange(3 * 4 * 5).reshape(3, 4, 5).astype('float32')
    y = m.extract_coronal_stack(x, j=0, slices=3)
    assert tuple(y.shape) == (3, 5, 3)
    np.testing.assert_array_equal(y[0], y[1])
    np.testing.assert_array_equal(y[1], x[:, 0, :].T)
    np.testing.assert_array_equal(y[2], x[:, 1, :].T)


def test_native_crop_and_affine_offset():
    source = np.zeros((9, 12, 13), dtype=np.uint8)
    source[4, 6, 7] = 1
    affine = np.array([[.7, 0, 0, 14], [0, .7, 0, 31], [0, 0, .7, -7], [0, 0, 0, 1]])
    start = [2, 4, 5]; end = [7, 9, 10]
    cropped_affine = affine.copy()
    cropped_affine[:3, 3] = (affine @ np.r_[start, 1])[:3]
    record = {'source_shape_kji': [13, 12, 9], 'start_ijk': start, 'end_ijk': end,
              'original_affine': affine.tolist(), 'output_affine': cropped_affine.tolist()}
    result = m.crop_native_mask(source, record, affine, (5, 5, 5), cropped_affine)
    assert result.shape == (5, 5, 5)
    assert result.sum() == 1
    with pytest.raises(ValueError):
        m.crop_native_mask(source, record, np.eye(4), (5, 5, 5), cropped_affine)


def test_positive_and_empty_loss_finite():
    for label in [False, True]:
        logits = torch.randn(1, 1, 9, 9, requires_grad=True)
        gt = torch.zeros_like(logits)
        if label:
            gt[0, 0, 4, 4] = 1
        loss = m.bce_dice_loss(logits, gt)
        loss.backward()
        assert torch.isfinite(loss)


def test_annotation_uncertainty_filter():
    assert not m.usable_for_supervision({'presence': 'absent', 'qc': 'needs_review', 'negative_confidence': 'high', 'source_mask': ''})
    assert not m.usable_for_supervision({'presence': 'absent', 'qc': 'provisional', 'negative_confidence': '', 'source_mask': ''})
    assert m.usable_for_supervision({'presence': 'absent', 'qc': 'pass', 'negative_confidence': 'high', 'source_mask': ''})
    assert m.usable_for_supervision({'presence': 'present', 'qc': 'provisional', 'negative_confidence': '', 'source_mask': 'mask.nii'})
