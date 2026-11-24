"""Manual HCP CSP prediction QC helper, run *inside 3D Slicer Python Console*.

Run once after extracting the private QC ZIP at home:
    exec(open(r'D:\CSP_DEEP_SEG\derived\csp25d_spatial_qc\slicer_csp25d_qc_loader.py', encoding='utf-8').read()); load_csp25d_qc()

Choose the cases/<subject ID> directory in the file picker.

This loads native cropped T2 and an error labelmap (GREEN true positive,
RED false positive, BLUE false negative), plus hidden manual and predicted
segmentation nodes that can be toggled independently in Segmentations.
No automatic editing, interpolation, smoothing, resampling or network calls.
This script intentionally clears the *current Slicer scene* when switching
to a new case: save unsaved manual work before running.
"""


def load_csp25d_qc(case_dir=None):
    from pathlib import Path

    import numpy as np
    import qt
    import slicer
    import vtk

    if case_dir is None:
        case_dir = qt.QFileDialog.getExistingDirectory(
            slicer.util.mainWindow(),
            "Select a folder from csp25d_spatial_qc/cases/<subject>",
            "")
    if not case_dir:
        print("[CSP QC] No case selected; existing Slicer scene not changed.")
        return
    folder = Path(str(case_dir))
    required = {
        "t2": folder / "T2_crop.nii.gz",
        "manual": folder / "manual_CSP.nii.gz",
        "pred": folder / "predicted_CSP.nii.gz",
        "error": folder / "error_TP1_FP2_FN3.nii.gz",
        "prob": folder / "probability_CSP.nii.gz",
    }
    missing = [str(x) for x in required.values() if not x.is_file()]
    if missing:
        raise FileNotFoundError("Missing QC files:\n" + "\n".join(missing))

    # Warn explicitly: switching cases deletes unsaved in-scene changes.
    if qt.QMessageBox.question(
        slicer.util.mainWindow(), "Load CSP QC subject " + folder.name,
        "This clears the current Slicer scene, including unsaved edits.\n"
        "Continue loading " + folder.name + "?",
        qt.QMessageBox.Yes | qt.QMessageBox.No,
        qt.QMessageBox.No,
    ) != qt.QMessageBox.Yes:
        return

    slicer.mrmlScene.Clear(0)
    name = folder.name
    t2 = slicer.util.loadVolume(str(required["t2"]), {"name": name + " T2 crop"})
    error = slicer.util.loadLabelVolume(
        str(required["error"]), {"name": name + " TP=green FP=red FN=blue"})

    # Explicit per-label colors, not dependency on Slicer's default label palette.
    palette = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLColorTableNode", name + " CSP error colors")
    palette.SetTypeToUser()
    palette.SetNumberOfColors(4)
    palette.SetColor(0, "Background", 0.0, 0.0, 0.0, 0.0)
    palette.SetColor(1, "True positive", 0.0, 0.95, 0.1, 1.0)
    palette.SetColor(2, "False positive", 1.0, 0.15, 0.15, 1.0)
    palette.SetColor(3, "False negative", 0.1, 0.5, 1.0, 1.0)
    error.GetDisplayNode().SetAndObserveColorNodeID(palette.GetID())

    def make_segmentation(mask_path, title, rgb):
        labelmap = slicer.util.loadLabelVolume(str(mask_path),
                                                {"name": title + " imported"})
        seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", title)
        seg.CreateDefaultDisplayNodes()
        seg.SetReferenceImageGeometryParameterFromVolumeNode(t2)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelmap, seg)
        segmentation = seg.GetSegmentation()
        for index in range(segmentation.GetNumberOfSegments()):
            part = segmentation.GetSegment(segmentation.GetNthSegmentID(index))
            part.SetColor(*rgb)
            part.SetName(title)
        seg.GetDisplayNode().SetVisibility(False)  # Error overlay is shown first.
        slicer.mrmlScene.RemoveNode(labelmap)
        return seg

    reference = make_segmentation(required["manual"], name + " Manual CSP",
                                  (0.1, 0.85, 0.2))
    predicted = make_segmentation(required["pred"], name + " Predicted CSP",
                                  (1.0, 0.85, 0.1))

    # The probability map can be loaded later via Add Data if desired.
    # Always show color-coded error, not one of the two segmentation overlays.
    slicer.app.layoutManager().setLayout(
        slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    slicer.util.setSliceViewerLayers(background=t2, label=error, labelOpacity=0.70)
    slicer.util.resetSliceViews()

    # Center on any predicted-or-reference CSP voxel (label values 1/2/3).
    mask_kji = slicer.util.arrayFromVolume(error)
    coords = np.argwhere(mask_kji > 0)
    if coords.size:
        kji = coords.mean(axis=0)
        matrix = vtk.vtkMatrix4x4()
        error.GetIJKToRASMatrix(matrix)
        x, y, z, w = matrix.MultiplyPoint(
            (float(kji[2]), float(kji[1]), float(kji[0]), 1.0))
        if w:
            slicer.util.jumpSlicesToLocation(x / w, y / w, z / w, centered=True)

    print("[CSP QC] " + name + " loaded on native T2 grid.")
    print("[CSP QC] GREEN=true positives, RED=extra predicted, BLUE=missed manual.")
    print("[CSP QC] Manual CSP and Predicted CSP segmentation nodes are loaded, hidden.")
    print("[CSP QC] Toggle their visibility in Data/Segmentations to compare.")
    print("[CSP QC] Review CORONAL, AXIAL and SAGITTAL around the CSP, and note "
          "isolated islands vs contiguous ventricular leakage.")
    return {"t2": t2, "error": error, "manual": reference, "predicted": predicted,
            "folder": str(folder)}
