"""Deterministic HCP test selector tests on fabricated inventory IDs only."""
import importlib.util
from pathlib import Path

import pytest


def load_selector():
    module_path = Path(__file__).parents[1] / "scripts" / "select_blinded_hcp_test_cohort.py"
    spec = importlib.util.spec_from_file_location("select_blinded_hcp_test_cohort", module_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fake_inputs():
    inventory = [
        {
            "subject_id": str(100000 + i),
            "status": "FAIL" if i == 20 else "PASS",
            "crop_t2": f"crop_{i}.nii.gz",
            "crop_json": f"crop_{i}.json",
            "original_t2": f"source_{i}.nii.gz",
        }
        for i in range(50)
    ]
    cohort = [{"subject_id": str(100000 + i)} for i in range(10)]
    return inventory, cohort


def test_blind_reproducible_selection_and_exclusions():
    m = load_selector()
    inventory, cohort = fake_inputs()
    a, meta = m.select(inventory, cohort, 12, 4, seed=843)
    b, _ = m.select(list(reversed(inventory)), list(reversed(cohort)), 12, 4, seed=843)
    assert [x["subject_id"] for x in a] == [x["subject_id"] for x in b]
    assert len(a) == len({x["subject_id"] for x in a}) == 16
    assert not {x["subject_id"] for x in a} & {x["subject_id"] for x in cohort}
    assert all(x["subject_id"] != "100020" for x in a)
    assert [x["assignment"] for x in a] == ["test"] * 12 + ["reserve"] * 4
    assert all(x["annotation_status"] == "" and x["annotation_mask"] == "" for x in a)
    assert meta["family_grouping_verified"] is False
    assert meta["unseen_pass_candidates"] == 39


def test_verified_family_groups_exclude_annotated_relatives():
    m = load_selector()
    inventory, cohort = fake_inputs()
    families = {r["subject_id"]: "fam_" + r["subject_id"] for r in inventory}
    families["100010"] = families["100000"]  # relation to annotated subject
    families["100011"] = families["100012"]  # two unseen siblings, only one allowed
    selected, meta = m.select(inventory, cohort, 12, 4, seed=843, family_map=families)
    ids = {x["subject_id"] for x in selected}
    assert "100010" not in ids
    assert not {"100011", "100012"}.issubset(ids)
    assert len({x["family_group"] for x in selected}) == 16
    assert meta["family_grouping_verified"] is True


def test_fails_closed_on_missing_cohort_ids_or_candidate_shortage():
    m = load_selector()
    inventory, cohort = fake_inputs()
    with pytest.raises(ValueError, match="absent from full HCP inventory"):
        m.select(inventory, cohort + [{"subject_id": "999999"}], 20, 10, seed=1)
    with pytest.raises(ValueError, match="Not enough unseen PASS candidates"):
        m.select(inventory, cohort, 40, 10, seed=1)
    with pytest.raises(ValueError, match="Family map lacks"):
        m.select(inventory, cohort, 10, 0, seed=1, family_map={"100001": "f1"})
    inv = [dict(row) for row in inventory]
    inv[11]["crop_json"] = ""
    with pytest.raises(ValueError, match="lacks expected crop"):
        m.select(inv, cohort, 5, 0, seed=1)
