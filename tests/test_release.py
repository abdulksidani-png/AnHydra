from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app, parse_sequence
from tardiscreen import evaluate, model
from tardiscreen.artifacts import atomic_destination, load_embeddings, sequence_hash
from tardiscreen.cnn import _split_val
from tardiscreen.explain import _offline_readout, _timeout


@pytest.fixture
def cache(tmp_path):
    frame = pd.DataFrame({"sequence_id": ["p", "n"], "sequence": ["A" * 40, "C" * 40],
                          "label": ["protective", "ordered"]})
    frame.to_csv(tmp_path / "dataset.csv", index=False)
    content = dict(ids=np.array(["p", "n"]), X=np.array([[1., 2.], [-1., -2.]]),
                   model=np.array("test/encoder"),
                   sequence_hashes=np.array([sequence_hash(s) for s in frame.sequence]))
    return tmp_path, frame, content


@pytest.mark.parametrize("failure", ["stale", "missing", "legacy", "duplicate", "nan", "encoder"])
def test_training_and_evaluation_reject_bad_cache(cache, failure):
    root, frame, content = cache
    if failure == "stale":
        content["sequence_hashes"][0] = sequence_hash("changed")
    elif failure == "missing":
        content["ids"][0] = "x"
    elif failure == "legacy":
        del content["sequence_hashes"]
    elif failure == "duplicate":
        content["ids"][1] = "p"
    elif failure == "nan":
        content["X"][0, 0] = np.nan
    else:
        content["model"] = np.array("")
    np.savez(root / "embeddings.npz", **content)
    with patch.object(evaluate, "DATA_DIR", root), pytest.raises(ValueError):
        evaluate._load()
    with patch.multiple(model, DATA_DIR=root, MODELS_PATH=root / "models.joblib"), pytest.raises(ValueError):
        model.train()
    assert not (root / "models.joblib").exists()


def test_valid_cache_aligns_by_id(cache):
    root, frame, content = cache
    np.savez(root / "embeddings.npz", **content)
    vectors, encoder = load_embeddings(root / "embeddings.npz", frame.iloc[::-1])
    assert encoder == "test/encoder"
    np.testing.assert_equal(vectors["p"], [1., 2.])


def test_atomic_write_preserves_previous_artifact_on_failure(tmp_path):
    target = tmp_path / "cache.npz"
    target.write_bytes(b"previous")
    with pytest.raises(RuntimeError):
        with atomic_destination(target) as temporary:
            temporary.write_bytes(b"partial")
            raise RuntimeError("interrupted")
    assert target.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_success_preserves_service_readability(tmp_path):
    import os
    import stat

    target = tmp_path / "models.joblib"
    target.write_bytes(b"previous")
    if os.name != "nt":
        target.chmod(0o640)
    with atomic_destination(target) as temporary:
        temporary.write_bytes(b"complete")
    assert target.read_bytes() == b"complete"
    if os.name != "nt":
        assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_inner_cnn_split_is_disjoint_and_has_both_classes():
    groups = np.repeat(np.arange(12), 2)
    y = np.repeat([0, 1] * 6, 2)
    train, val = _split_val(np.arange(len(y)), groups, np.random.default_rng(42), y)
    assert set(y[train]) == set(y[val]) == {0, 1}
    assert not set(groups[train]) & set(groups[val])
    with pytest.raises(ValueError):
        _split_val(np.arange(2), np.array(["a", "b"]), np.random.default_rng(42), np.array([0, 1]))


def test_api_rejects_silent_encoder_truncation():
    assert len(parse_sequence("A" * 1022)) == 1022
    response = TestClient(app).post("/score", json={"sequence": "A" * 1023})
    assert response.status_code == 400
    assert "1022" in response.json()["detail"]


def test_unusable_model_returns_actionable_503(tmp_path):
    artifact = tmp_path / "models.joblib"
    artifact.write_bytes(b"invalid")
    with patch("app.main.MODELS_PATH", artifact), patch("app.main.predict", side_effect=ValueError("private detail")):
        response = TestClient(app).post("/score", json={"sequence": "A" * 40})
    assert response.status_code == 503
    assert "private detail" not in response.text


def test_readiness_rejects_broken_bundle():
    with patch("app.main.load_bundle", side_effect=ValueError("broken")):
        assert TestClient(app).get("/ready").status_code == 503


def test_offline_explanation_preserves_opposing_auxiliary_signal():
    text = _offline_readout(.9, "protective", [("low_complexity", -4.)])
    assert "opposes, -4.00" in text
    assert "do not explain the ESM-2 score" in text
    assert "driven mainly" not in text


@pytest.mark.parametrize("value", ["bad", "nan", "inf", "-1", "0", ""])
def test_invalid_timeout_does_not_break_app(monkeypatch, value):
    monkeypatch.setenv("GEMINI_TIMEOUT_S", value)
    assert _timeout() == 12.


def test_coverage_refreshes_both_current_classes_without_disprot(tmp_path):
    from tardiscreen import coverage

    pd.DataFrame({"sequence_id": ["p", "n"], "label": ["protective", "idp_matched"]}).to_csv(
        tmp_path / "dataset.csv", index=False)
    rows = [dict(sequence_id=sid, disorder_fraction=.5, n_regions=1, length=40) for sid in ["p", "n"]]
    output = tmp_path / "disorder_coverage.csv"
    with patch.multiple(coverage, DATA_DIR=tmp_path, OUT_PATH=output), patch.object(
            coverage, "fetch_uniprot_coverage", return_value=rows), patch("tardiscreen.data._get") as get:
        coverage.main()
    get.assert_not_called()
    assert set(pd.read_csv(output).label) == {"protective", "idp_matched"}


def test_incomplete_coverage_preserves_previous_file(tmp_path):
    from tardiscreen import coverage

    pd.DataFrame({"sequence_id": ["p", "n"], "label": ["protective", "idp_matched"]}).to_csv(
        tmp_path / "dataset.csv", index=False)
    output = tmp_path / "disorder_coverage.csv"
    output.write_text("previous", encoding="utf-8")
    with patch.multiple(coverage, DATA_DIR=tmp_path, OUT_PATH=output), patch.object(
            coverage, "fetch_uniprot_coverage", return_value=[]), pytest.raises(ValueError):
        coverage.main()
    assert output.read_text(encoding="utf-8") == "previous"


def test_merge_does_not_keep_an_orphaned_matched_negative(tmp_path):
    from tardiscreen import data, merge_dataset

    records = [data.Record("p1", "A" * 40, "protective", "uniprot"),
               data.Record("p2", "G" * 40, "protective", "uniprot")]
    pd.DataFrame([r.__dict__ for r in records]).to_csv(tmp_path / "dataset.csv", index=False)
    pd.DataFrame({"sequence_id": ["n1", "n2"], "sequence": ["C" * 40, "D" * 40],
                  "matched_positive_id": ["p1", "p2"]}).to_csv(tmp_path / "matched_negatives.csv", index=False)
    pd.DataFrame({"sequence_id": ["p1", "p2"]}).to_csv(tmp_path / "matched_positives.csv", index=False)
    # Simulate cross-label clustering removing p2 but retaining its negative partner.
    def cluster(rows, identity):
        return [row for row in rows if row.sequence_id != "p2"]
    with patch.multiple(merge_dataset, DATA_DIR=tmp_path, DATASET=tmp_path / "dataset.csv",
                        BACKUP=tmp_path / "backup.csv"), patch.object(data, "cluster_sequences", side_effect=cluster):
        merge_dataset.main()
    result = pd.read_csv(tmp_path / "dataset.csv")
    assert set(result.sequence_id) == {"p1", "n1"}
    assert set(result.matched_pair_id) == {"p1"}


def test_all_experiment_entrypoints_require_matched_population():
    from tardiscreen import blast_baseline, cnn, family_holdout, motifs, remote_homology

    frame = pd.DataFrame({"sequence_id": ["p", "n"], "sequence": ["A" * 40, "C" * 40],
                          "label": ["protective", "idp_matched"], "cluster_id": ["a", "b"]})
    for module in (blast_baseline, cnn, family_holdout, motifs, remote_homology):
        with patch.object(module, "_load", return_value=(frame, {})), patch.object(
                module, "_require_blast", create=True), pytest.raises(ValueError, match="in_matched_set"):
            if module is remote_homology:
                module.collect(frame, {})
            else:
                module.main()
