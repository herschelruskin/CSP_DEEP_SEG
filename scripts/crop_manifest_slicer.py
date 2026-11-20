"""Crop *only* explicitly listed original SPC1 scans with the frozen rule.

Run inside 3D Slicer Python console (module must be on sys.path). This uses
calibrate_csp_roi_slicer.py and reduce_t2_slicer.py from the existing repo.
Manual CSP masks are never opened to decide an individual subject's crop.
"""
import csv
from pathlib import Path


def crop_manifest(manifest_csv, rules_json, out_dir, limit=3, overwrite=False):
    import slicer
    from calibrate_csp_roi_slicer import reduce_t2_with_calibrated_rule

    with open(manifest_csv, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows or not {'subject_id', 'source_t2'}.issubset(rows[0]):
        raise ValueError('Requires cohort_manifest.csv with subject_id and source_t2')
    if limit is None:
        print('WARNING: cropping every explicitly listed subject in the manifest:', len(rows))
    else:
        rows = rows[:limit]
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    status = []
    for row in rows:
        source_file = Path(row['source_t2'])
        base = source_file.name[:-7] if source_file.name.endswith('.nii.gz') else source_file.stem
        result_path = output / (base + '_proportional_reduced.nii.gz')
        record_path = output / (base + '_proportional_reduced.crop.json')
        node = None
        try:
            if not source_file.is_file():
                raise FileNotFoundError(source_file)
            if not overwrite and result_path.exists() and record_path.exists():
                state = 'EXISTS_NOT_REWRITTEN'
            else:
                node = slicer.util.loadVolume(str(source_file), {'show': False})
                if node is None:
                    raise RuntimeError('Could not load ' + str(source_file))
                reduce_t2_with_calibrated_rule(node, rules_json, str(output), mode='proportional', overwrite=overwrite)
                state = 'SAVED'
            status.append({'subject_id': row['subject_id'], 'status': state, 'error': ''})
        except Exception as exc:
            status.append({'subject_id': row['subject_id'], 'status': 'FAILED', 'error': str(exc)})
            print('[CROP FAILED]', row['subject_id'], exc)
        finally:
            if node is not None:
                slicer.mrmlScene.RemoveNode(node)
    with (output / 'manifest_crop_report.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['subject_id', 'status', 'error'])
        writer.writeheader()
        writer.writerows(status)
    print('[MANIFEST CROP]', len(status), 'scans;', sum(x['status']=='FAILED' for x in status), 'failures')
    return status
