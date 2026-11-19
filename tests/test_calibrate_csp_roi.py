"""Synthetic CSP crop calibration tests; no HCP data or Slicer needed."""
import csv
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import calibrate_csp_roi_slicer as calibration
from reduce_t2_slicer import CropSettings


def toy(shift=0, scale=1.0):
    img = np.zeros((70, 90, 110), np.float32)
    img[6:65, 8:84, 9:102] = 100
    affine = np.array([[0.85*scale, 0.03, 0.0, -50 + shift],
                       [0.0, 0.85*scale, 0.02, -35],
                       [0.0, 0.0, 0.85*scale, -30],
                       [0.0, 0.0, 0.0, 1.0]])
    return img, affine


def positive_roi(shape, k0=25, k1=31, j0=55, j1=60, i0=50, i1=58):
    m = np.zeros(shape, np.uint8)
    m[k0:k1, j0:j1, i0:i1] = 1
    return m


def test_measure_absent_is_zero_not_missing():
    im, aff = toy()
    result = calibration.measure_subject(im, aff, presence='absent', subject_id='100206')
    assert result['mask_voxels'] == 0
    assert result['mask_volume_mm3'] == 0
    assert result['mask_ras_lo'] is None
    with pytest.raises(ValueError, match='requires a mask'):
        calibration.measure_subject(im, aff, presence='present')
    with pytest.raises(ValueError, match='positive mask voxels'):
        calibration.measure_subject(im, aff, positive_roi(im.shape), 'absent')
    with pytest.raises(ValueError, match='empty reference'):
        calibration.measure_subject(im, aff, np.zeros_like(im), 'present')


def test_fixed_and_proportional_rules_contain_development_extremes():
    cases = []
    for number, (k0, j0, i0, scale) in enumerate([(25, 55, 50, 1.0),
                                                   (13, 35, 45, 1.2),
                                                   (35, 65, 55, 0.85)]):
        im, aff = toy(shift=20*number, scale=scale)
        mask = positive_roi(im.shape, k0=k0, k1=k0+8, j0=j0, j1=j0+6,
                            i0=i0, i1=i0+10)
        meas = calibration.measure_subject(im, aff, mask, 'present', str(100206+number))
        cases.append((meas, aff, mask))
    for mode in calibration.MODES:
        fitted = calibration.fit_rule([c[0] for c in cases], mode, margin_mm=5)
        assert fitted['training_positive_count'] == 3
        for meas, aff, mask in cases:
            audit = calibration.evaluate_subject_rule(meas, fitted, aff, mask)
            assert audit['whole_mask_contained']
            assert audit['minimum_margin_mm'] > 0
            assert audit['fraction_inside'] == 1
            assert 0 < audit['cropped_fraction'] <= 1


def test_proportional_box_responds_to_subject_size_while_fixed_mm_does_not():
    rule = dict(mode='proportional', lr_half_width=0.10, y_lo=0.4, y_hi=0.65,
                z_lo=0.3, z_hi=0.5, margin_mm=8)
    lo = np.array([-50, -100, -80])
    small = np.array([50, 100, 80])
    large = np.array([75, 200, 150])
    a0, a1 = calibration.rule_ras_box(lo, small, rule)
    b0, b1 = calibration.rule_ras_box(lo, large, rule)
    assert np.all((b1-b0) > (a1-a0))
    rule['mode'] = 'fixed_mm'
    c0, c1 = calibration.rule_ras_box(lo, small, rule)
    d0, d1 = calibration.rule_ras_box(lo, large, rule)
    assert np.allclose(d1-d0, c1-c0)


def test_sparse_mask_audit_equals_dense_mask_audit_and_can_detect_exclusion():
    im, aff = toy()
    mask = positive_roi(im.shape)
    m = calibration.measure_subject(im, aff, mask, 'present')
    rule = calibration.fit_rule([m], 'fixed_mm', margin_mm=5)
    voxels = np.argwhere(mask>0)[:, [2,1,0]]
    dense = calibration.evaluate_subject_rule(m, rule, aff, mask_kji=mask)
    sparse = calibration.evaluate_subject_rule(m, rule, aff, mask_ijk=voxels)
    for key in ['whole_mask_contained','minimum_margin_mm','fraction_inside']:
        assert sparse[key] == dense[key]
    assert sparse['face_margins_mm'] == dense['face_margins_mm']
    # Shrink far beyond positive extent: must report a miss, not succeed silently.
    rule.update(lr_half_width=0.01, y_lo=1., y_hi=2., z_lo=1., z_hi=2., margin_mm=0)
    shrunk = calibration.evaluate_subject_rule(m, rule, aff, mask_ijk=voxels)
    assert shrunk['whole_mask_contained'] is False
    assert shrunk['minimum_margin_mm'] < 0


def test_manifest_never_interprets_missing_positive_as_absent(tmp_path):
    t2 = tmp_path/'T2w'
    for sid in ('100206','100307','100408'):
        path=t2/sid/f'{sid}_3T_T2w_SPC1.nii.gz'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.touch()
    mask_root=tmp_path/'masks'
    for p in (mask_root/'100206'/'csp.seg.nrrd',
              mask_root/'100408'/'csp.seg.nrrd'):
        p.parent.mkdir(parents=True,exist_ok=True)
        p.touch()
    absents=tmp_path/'absent.txt'
    absents.write_text('100307\n')
    rows=calibration.make_roi_manifest(t2,mask_root,tmp_path/'cohort.csv',
                                       absent_ids_file=absents)
    assert len(rows) == 3
    assert {r['subject_id']:r['presence'] for r in rows} == {
        '100206':'present','100307':'absent','100408':'present'}
    assert rows[1]['mask_path']==''
    assert rows[1]['qc']=='provisional'
    assert all(r['split']=='dev' for r in rows)
    # Explicit status asking for present but missing mask -> manual QC blocker.
    status=tmp_path/'status.csv'
    status.write_text('subject_id,presence\n100307,present\n')
    rows=calibration.make_roi_manifest(t2,mask_root,tmp_path/'revised.csv',
                                       status_csv=status)
    assert next(r for r in rows if r['subject_id']=='100307')['qc']=='needs_review'


def test_ambiguous_masks_cannot_be_included_by_automatic_manifest(tmp_path):
    t2=tmp_path/'T2w'/'100206'
    t2.mkdir(parents=True)
    (t2/'100206_3T_T2w_SPC1.nii.gz').touch()
    m=tmp_path/'masks'/'100206'
    m.mkdir(parents=True)
    (m/'first.seg.nrrd').touch()
    (m/'second.seg.nrrd').touch()
    rows=calibration.make_roi_manifest(tmp_path/'T2w',tmp_path/'masks',tmp_path/'out.csv')
    assert rows[0]['qc']=='needs_review'
    assert rows[0]['mask_path']==''


def test_loo_maximum_extreme_is_not_guaranteed_generalization():
    im, aff = toy()
    a = calibration.measure_subject(im, aff, positive_roi(im.shape), 'present', 'one')
    b = calibration.measure_subject(im, aff, positive_roi(im.shape, k0=10,k1=15,
                                   j0=24,j1=30,i0=43,i1=48), 'present', 'two')
    loo = calibration.fit_rule([a], 'fixed_mm', margin_mm=0)
    mask_b = positive_roi(im.shape,k0=10,k1=15,j0=24,j1=30,i0=43,i1=48)
    measured = calibration.evaluate_subject_rule(b,loo,aff,mask_kji=mask_b)
    assert measured['whole_mask_contained'] is False


def test_cohort_runner_dev_holdout_and_local_outputs(tmp_path, monkeypatch):
    im, aff = toy()
    masks = {'100206':positive_roi(im.shape),
             '100307':positive_roi(im.shape, k0=13,k1=22),
             '100509':positive_roi(im.shape, j0=65,j1=70)}
    manifest=tmp_path/'manifest.csv'
    ids = [('100206','present','dev'),('100307','present','dev'),
           ('100408','absent','dev'),('100509','present','holdout')]
    with manifest.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=calibration.FIELDS)
        w.writeheader()
        for sid,pres,split in ids:
            fake_source=tmp_path/f'{sid}_3T_T2w_SPC1.nii.gz'
            fake_source.touch()
            w.writerow(dict(subject_id=sid,presence=pres,qc='pass',split=split,
                            source_t2=str(fake_source), mask_path=(f'{sid}.nii.gz' if sid in masks else '')))
    class Node:
        def GetParentTransformNode(self): return None
    util=types.SimpleNamespace(loadVolume=lambda *a,**kw: Node(),
                               arrayFromVolume=lambda volume: im)
    mock=types.SimpleNamespace(util=util, mrmlScene=types.SimpleNamespace(RemoveNode=lambda node: None))
    monkeypatch.setitem(sys.modules,'slicer',mock)
    monkeypatch.setattr(calibration,'_slicer_ijk_to_ras',lambda volume: aff)
    monkeypatch.setattr(calibration,'_load_reference_mask',
                        lambda path, volume, segment_id, label_value: masks[Path(path).stem.split('.')[0]])
    result=calibration.calibrate_roi_from_manifest(manifest,tmp_path/'out',margin_mm=4)
    assert result['summary']['n_dev']==3
    assert result['summary']['n_holdout_evaluated']==0
    assert result['summary']['n_holdout_reserved']==1
    assert result['summary']['dev_positive']==2
    assert result['summary']['dev_absent']==1
    data=json.loads((tmp_path/'out'/'calibrated_rules.json').read_text())
    assert data['rules']['fixed_mm']['training_positive_count']==2
    with (tmp_path/'out'/'rule_evaluations.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==6  # only 3 DEV subjects times two crop candidates
    assert all(r['whole_mask_contained']=='True' for r in rows
               if r['split']=='dev' and r['presence']=='present')
    assert len(list(csv.DictReader((tmp_path/'out'/'leave_one_subject_out.csv').open())))==4


def test_holdout_cannot_be_inspected_without_unlock(tmp_path, monkeypatch):
    # The default cohort run must not load an untouched holdout MRI or mask.
    manifest = tmp_path/'manifest.csv'
    with manifest.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=calibration.FIELDS); w.writeheader()
        w.writerow(dict(subject_id='100206', presence='present', qc='pass',
                        split='holdout', source_t2='NEVER_OPENED'))
    with pytest.raises(RuntimeError, match='No valid development positive'):
        calibration.calibrate_roi_from_manifest(manifest,tmp_path/'out')
    assert not (tmp_path/'out'/'subject_measurements.csv').exists()


def test_review_flag_is_qc_not_presence(tmp_path):
    """A review flag on a saved CSP must not erase its positive status."""
    for sid in ('100206', '100307'):
        t2 = tmp_path / 'T2w' / sid
        t2.mkdir(parents=True)
        (t2 / f'{sid}_3T_T2w_SPC1.nii.gz').touch()
    masks = tmp_path / 'CSP_Seg'
    masks.mkdir()
    (masks / '100206.nii').touch()
    (masks / '100307.nii').touch()
    review = tmp_path / 'needs_review_ids.txt'
    review.write_text('100206\n')
    rows = calibration.make_roi_manifest(tmp_path/'T2w', masks, tmp_path/'manifest.csv',
                                         review_ids_file=review)
    entry = next(row for row in rows if row['subject_id'] == '100206')
    assert entry['presence'] == 'present'
    assert entry['qc'] == 'needs_review'


def test_review_flagged_large_positive_contributes_to_envelope(tmp_path, monkeypatch):
    """An unusual large positive expands the main rule and keeps the QC label."""
    im, aff = toy()
    normal = positive_roi(im.shape)
    unusual = positive_roi(im.shape, k0=7, k1=48, j0=20, j1=78,
                           i0=27, i1=86)
    masks = {'100206': normal, '100307': unusual}
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=calibration.FIELDS)
        writer.writeheader()
        for sid, qc in (('100206', 'pass'), ('100307', 'needs_review')):
            source = tmp_path / f'{sid}_3T_T2w_SPC1.nii.gz'
            source.touch()
            writer.writerow(dict(subject_id=sid, presence='present', qc=qc,
                                 split='dev', source_t2=str(source),
                                 mask_path=f'{sid}.nii'))
    class Volume:
        def GetParentTransformNode(self): return None
    fake_slicer = types.SimpleNamespace(
        util=types.SimpleNamespace(loadVolume=lambda *a, **kw: Volume(),
                                   arrayFromVolume=lambda volume: im),
        mrmlScene=types.SimpleNamespace(RemoveNode=lambda node: None))
    monkeypatch.setitem(sys.modules, 'slicer', fake_slicer)
    monkeypatch.setattr(calibration, '_slicer_ijk_to_ras', lambda volume: aff)
    monkeypatch.setattr(calibration, '_load_reference_mask',
                        lambda path, volume, segment_id, label_value: masks[Path(path).stem])
    result = calibration.calibrate_roi_from_manifest(manifest, tmp_path/'result', margin_mm=5)
    assert result['summary']['dev_positive'] == 2
    assert result['summary']['dev_positive_needs_review'] == 1
    assert result['rules']['fixed_mm']['training_positive_count'] == 2
    rules_file = json.loads((tmp_path/'result'/'calibrated_rules.json').read_text())
    assert rules_file['rules']['fixed_mm']['includes_needs_review_positive_masks']
    assert rules_file['sensitivity_excluding_review']['fixed_mm']['training_positive_count'] == 1
    assert rules_file['rules']['fixed_mm']['lr_half_width'] > rules_file['sensitivity_excluding_review']['fixed_mm']['lr_half_width']
    ranked = list(csv.DictReader((tmp_path/'result'/'largest_csp_ranked.csv').open()))
    assert ranked[0]['subject_id'] == '100307'
    assert ranked[0]['qc'] == 'needs_review'
    audits = list(csv.DictReader((tmp_path/'result'/'rule_evaluations.csv').open()))
    assert len(audits) == 4
    assert all(row['whole_mask_contained'] == 'True' for row in audits)


def test_fit_excludes_outlier_but_keeps_its_measurement_ranking_and_audit(tmp_path, monkeypatch):
    """Post-hoc outlier exclusion cannot hide a real mask from auditing."""
    im, aff = toy()
    masks = {
        '100206': positive_roi(im.shape, k0=24, k1=32, j0=54, j1=60, i0=49, i1=59),
        '100307': positive_roi(im.shape, k0=23, k1=31, j0=52, j1=62, i0=48, i1=60),
        '108828': positive_roi(im.shape, k0=7, k1=48, j0=20, j1=78, i0=27, i1=86),
    }
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=calibration.FIELDS)
        writer.writeheader()
        for sid, qc in [('100206', 'pass'), ('100307', 'pass'),
                        ('108828', 'needs_review')]:
            src = tmp_path / f'{sid}_3T_T2w_SPC1.nii.gz'
            src.touch()
            writer.writerow(dict(subject_id=sid, presence='present', qc=qc, split='dev',
                                 source_t2=str(src), mask_path=f'{sid}.nii'))
    class Volume:
        def GetParentTransformNode(self): return None
    fake_slicer = types.SimpleNamespace(
        util=types.SimpleNamespace(loadVolume=lambda *a, **kw: Volume(),
                                   arrayFromVolume=lambda volume: im),
        mrmlScene=types.SimpleNamespace(RemoveNode=lambda node: None))
    monkeypatch.setitem(sys.modules, 'slicer', fake_slicer)
    monkeypatch.setattr(calibration, '_slicer_ijk_to_ras', lambda volume: aff)
    monkeypatch.setattr(calibration, '_load_reference_mask',
                        lambda path, volume, segment_id, label_value: masks[Path(path).stem])
    out = tmp_path / 'outlier_excluded'
    r = calibration.calibrate_roi_from_manifest(
        manifest, out, margin_mm=5, excluded_from_fit_ids=('108828',))
    assert r['summary']['n_read'] == 3
    assert r['summary']['n_dev'] == 2
    assert r['summary']['n_excluded_from_fit'] == 1
    assert r['summary']['all_positive_read'] == 3
    assert r['summary']['dev_positive'] == 2
    for rule in r['rules'].values():
        assert rule['training_positive_count'] == 2
        assert rule['excluded_from_fit_ids'] == ['108828']
    ranked = list(csv.DictReader((out / 'largest_csp_ranked.csv').open()))
    assert ranked[0]['subject_id'] == '108828'
    assert ranked[0]['excluded_from_fit'] == 'True'
    evaluations = list(csv.DictReader((out / 'rule_evaluations.csv').open(encoding='utf-8-sig')))
    assert len(evaluations) == 6
    assert len([x for x in evaluations if x['subject_id'] == '108828']) == 2
    assert all(x['excluded_from_fit'] == 'True'
               for x in evaluations if x['subject_id'] == '108828')
    loo = list(csv.DictReader((out / 'leave_one_subject_out.csv').open(encoding='utf-8-sig')))
    assert len(loo) == 4
    assert set(x['subject_id'] for x in loo) == {'100206', '100307'}


def test_unknown_fit_exclusion_cannot_silently_do_nothing(tmp_path):
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=calibration.FIELDS)
        w.writeheader()
        w.writerow(dict(subject_id='100206', presence='present', qc='pass', split='dev',
                        source_t2='unused'))
    with pytest.raises(ValueError, match='Unknown excluded_from_fit_ids'):
        calibration.calibrate_roi_from_manifest(
            manifest, tmp_path / 'out', excluded_from_fit_ids=('NOT_A_SUBJECT',))
