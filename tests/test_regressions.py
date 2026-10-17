import importlib.util
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app, parse_sequence
from tardiscreen import coverage, data, evaluate, match_negatives, merge_dataset, model


def test_fasta_and_raw_input():
    sequence = "ACDEFGHIKLMNPQRSTVWY" * 2
    assert parse_sequence("  >record description\n" + sequence.lower()) == sequence
    assert parse_sequence(sequence[:20] + " \n" + sequence[20:]) == sequence


@pytest.mark.parametrize("raw", ["A" * 19, "A" * 10001, ">a\n" + "A" * 20 + "\n>b\n" + "C" * 20,
                                 "A" * 20 + "123", "A" * 20 + "X"])
def test_invalid_input_is_not_silently_changed(raw):
    with pytest.raises(HTTPException) as exc:
        parse_sequence(raw)
    assert exc.value.status_code == 400


def test_api_without_model(tmp_path):
    with patch("app.main.MODELS_PATH", tmp_path / "missing"):
        client = TestClient(app)
        assert client.get("/").status_code == 200
        assert client.get("/health").json()["model_trained"] is False
        assert client.post("/score", json={"sequence": "A" * 40}).status_code == 503
        assert client.post("/score", json={"sequence": "A"}).status_code == 400


def test_disprot_keeps_nuclear_proteins():
    entries = [{"acc": "ordinary", "name": "nuclear cleavage protein", "sequence": "A" * 40},
               {"acc": "protective", "name": "LEA protein", "sequence": "C" * 40}]
    with patch.object(data, "_get", return_value=SimpleNamespace(json=lambda: {"data": entries})):
        assert [r.sequence_id for r in data.fetch_hard_negatives()] == ["ordinary"]


def test_coverage_clips_coordinates_before_merging():
    assert coverage._merge_fraction([(-10, 5), (4, 8), (30, 40)], 20) == 0.4
    assert coverage._merge_fraction([(30, 40)], 20) == 0
    assert coverage._merge_fraction([(1, 50)], 20) == 1


def test_task_population_is_shared_with_diagnostics():
    from tardiscreen.diagnose import _task_frame
    df = pd.DataFrame({"label": ["protective", "protective", "idp_matched", "ordered"],
                       "in_matched_set": [True, False, True, False], "cluster_id": list("abcd")})
    assert evaluate.task_subset(df, "real").index.tolist() == [0, 1]
    assert _task_frame(df, "real")[0]["cluster_id"].tolist() == ["a", "c"]
    assert len(evaluate.task_subset(df, "trivial")) == 3
    with pytest.raises(ValueError, match="in_matched_set"):
        evaluate.task_subset(df.drop(columns="in_matched_set"), "real")


def test_cluster_folds_are_disjoint_and_complete():
    y = np.array([0, 1] * 20)
    groups = np.repeat(np.arange(20), 2)
    folds = list(evaluate.cluster_split_folds(y, groups))
    assert sorted(np.concatenate([te for _, te in folds])) == list(range(len(y)))
    for tr, te in folds:
        assert not set(groups[tr]) & set(groups[te])
        assert set(y[tr]) == set(y[te]) == {0, 1}


@pytest.mark.parametrize("y,groups", [([0, 1], ["a", "b"]), ([0, 0], ["a", "b"]),
                                    ([0, 1, 0, 1], ["a", "", "c", "d"])])
def test_insufficient_clusters_fail_clearly(y, groups):
    with pytest.raises(ValueError):
        list(evaluate.cluster_split_folds(y, groups))


def test_prediction_uses_training_encoder():
    embedding = SimpleNamespace(embed_sequences=Mock(return_value=np.array([[1.0, 2.0]])))
    classifier = Mock()
    classifier.predict_proba.return_value = np.array([[0.2, 0.8]])
    scaler = Mock()
    scaler.transform.return_value = np.ones((1, 9))
    bundle = {"model_name": "training/model", "esm_clf": classifier,
              "bio_clf": SimpleNamespace(named_steps={"standardscaler": scaler,
                           "logisticregression": SimpleNamespace(coef_=np.ones((1, 9)))}),
              "feature_names": model.FEATURE_NAMES, "homolog_ids": []}
    with patch.dict(sys.modules, {"tardiscreen.embed": embedding}), patch.object(model, "load_bundle", return_value=bundle):
        assert model.predict("A" * 40).score == 0.8
    embedding.embed_sequences.assert_called_once_with(["A" * 40], model_name="training/model")


def test_merge_is_repeatable(tmp_path):
    dataset = tmp_path / "dataset.csv"
    rows = [data.Record("p", "A" * 40, "protective", "uniprot", cluster_id="c0"),
            data.Record("n", "C" * 40, "idp_matched", "uniprot", cluster_id="c1")]
    pd.DataFrame([r.__dict__ for r in rows]).to_csv(dataset, index=False)
    pd.DataFrame([{"sequence_id": "n", "sequence": "C" * 40}]).to_csv(tmp_path / "matched_negatives.csv", index=False)
    pd.DataFrame({"sequence_id": ["p"]}).to_csv(tmp_path / "matched_positives.csv", index=False)
    with patch.multiple(merge_dataset, DATA_DIR=tmp_path, DATASET=dataset, BACKUP=tmp_path / "backup.csv"), patch.object(data, "cluster_sequences", side_effect=lambda records, identity: records):
        merge_dataset.main()
        merge_dataset.main()
    assert pd.read_csv(dataset)["sequence_id"].tolist() == ["p", "n"]


def test_zero_variance_balance_is_not_reported_as_balanced():
    assert np.isinf(match_negatives.standardized_mean_difference([1, 1], [2, 2]))
    assert match_negatives.standardized_mean_difference([1, 1], [1, 1]) == 0


def test_single_positive_can_match_exact_candidate():
    frame = pd.DataFrame({"disorder_fraction": [0.5], "length": [100]})
    assert match_negatives.match(frame, frame)[0] == [(0, 0)]


@pytest.fixture
def embed_module():
    # Cache and encoder-selection logic needs no model weights or heavy runtime.
    spec = importlib.util.spec_from_file_location("embed_under_test", model.DATA_DIR.parent / "src/tardiscreen/embed.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"torch": Mock(), "transformers": Mock(), "tqdm": Mock()}):
        spec.loader.exec_module(module)
    return module


def test_explicit_encoder_overrides_environment(embed_module, monkeypatch):
    monkeypatch.setenv("TARDISCREEN_EMBED_MODEL", "different/model")
    assert embed_module._resolve_model() == "different/model"
    assert embed_module._resolve_model(embed_module.DEFAULT_MODEL) == embed_module.DEFAULT_MODEL


def test_cache_invalidates_changed_sequence_and_encoder(embed_module, tmp_path):
    embed_module.CACHE = tmp_path / "embeddings.npz"
    vectors = {"same": np.array([1, 2]), "changed": np.array([3, 4])}
    embed_module._save(vectors, "model", {"same": "AAAA", "changed": "CCCC"})
    assert set(embed_module._load_cache("model", {"same": "AAAA", "changed": "DDDD"})) == {"same"}
    assert embed_module._load_cache("other", {"same": "AAAA"}) == {}
    embed_module._save(vectors, "model")
    assert embed_module._load_cache("model", {"same": "AAAA"}) == {}


def test_training_and_prediction_round_trip(tmp_path):
    import joblib

    ids = ["p1", "p2", "n1", "n2"]
    frame = pd.DataFrame({"sequence_id": ids, "sequence": ["GSK" * 20, "GSE" * 20, "AVL" * 20, "AVF" * 20],
                          "label": ["protective", "protective", "ordered", "ordered"]})
    frame.to_csv(tmp_path / "dataset.csv", index=False)
    vectors = np.array([[1., 2.], [1., 3.], [-1., -2.], [-1., -3.]])
    np.savez(tmp_path / "embeddings.npz", ids=np.array(ids), X=vectors, model="test/encoder")
    model_path = tmp_path / "models.joblib"
    embedding = SimpleNamespace(embed_sequences=Mock(return_value=vectors[:1]))
    with patch.multiple(model, DATA_DIR=tmp_path, MODELS_PATH=model_path):
        model.train()
        assert joblib.load(model_path)["model_name"] == "test/encoder"
        with patch.dict(sys.modules, {"tardiscreen.embed": embedding}):
            prediction = model.predict(frame.iloc[0]["sequence"])
    assert prediction.label == "protective"
    assert prediction.nearest_homolog == "p1"
    assert len(prediction.top_features) == 3


def test_family_holdout_excludes_related_training_rows():
    from tardiscreen.family_holdout import _holdout_train_indices
    assert _holdout_train_indices(["same", "other", "same", "negative"], [0]).tolist() == [1, 3]


def test_page_is_served_from_disk():
    """The page moved out of main.py into a file; a bad path would serve an empty body."""
    from app.main import PAGE_PATH

    page = PAGE_PATH.read_text(encoding="utf-8")
    assert PAGE_PATH.name == "index.html"
    # The page is useless if it cannot reach the API or render the fields the API returns.
    for needed in ('fetch("/score"', 'fetch("/health")', "top_features", "nearest_homolog"):
        assert needed in page, needed
