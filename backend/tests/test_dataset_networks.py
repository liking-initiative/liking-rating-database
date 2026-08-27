"""
The precomputed per-dataset preference networks.

These are estimated offline by scripts/estimate_networks.R, so the tests check
the shipped artefacts and the endpoint that serves them, not the estimation.
"""
import json
from pathlib import Path

import pytest

NETWORK_DIR = Path(__file__).resolve().parents[2] / "data-release" / "networks"

pytestmark = pytest.mark.skipif(
    not NETWORK_DIR.exists(), reason="networks not estimated"
)


def _load_all():
    return [json.loads(p.read_text()) for p in sorted(NETWORK_DIR.glob("*.json"))]


def test_every_dataset_has_a_file():
    """A dataset with no network still gets a file saying why."""
    files = _load_all()
    assert len(files) >= 50
    for d in files:
        assert d.get("dataset_code")
        assert "estimated" in d
        if not d["estimated"]:
            # never a silent absence
            assert d.get("reason"), f"{d['dataset_code']} has no reason recorded"


def test_estimated_networks_declare_their_restriction():
    """The item selection is part of what the figure means, so it must ship."""
    for d in _load_all():
        if not d["estimated"]:
            continue
        sel = d["selection"]
        assert sel["items_estimated"] <= sel["items_in_dataset"]
        # a graphical model over items needs more subjects than items
        assert sel["subjects_complete"] >= 2 * sel["items_estimated"], d["dataset_code"]
        assert sel["min_item_frequency"] >= 1
        method = d["method"]
        assert method["algorithm"].startswith("bootEGA")
        assert method["iterations"] >= 100
        assert method["seed"] is not None, "results must be reproducible"


def test_edges_reference_real_nodes():
    for d in _load_all():
        if not d["estimated"]:
            continue
        labels = {n["label"] for n in d["nodes"]}
        for e in d["edges"]:
            assert e["source"] in labels, d["dataset_code"]
            assert e["target"] in labels, d["dataset_code"]
            assert e["source"] != e["target"]


def test_edges_are_partial_correlations():
    """Weights are signed and bounded; the UI draws sign as colour."""
    for d in _load_all():
        if not d["estimated"]:
            continue
        for e in d["edges"]:
            assert -1.0 <= e["weight"] <= 1.0, d["dataset_code"]
            assert e["weight"] != 0


def test_node_fields_are_present_and_sane():
    for d in _load_all():
        if not d["estimated"]:
            continue
        for n in d["nodes"]:
            assert n["label"] and n["id"]
            assert n["community"] is None or n["community"] >= 0
            if n["stability"] is not None:
                assert 0.0 <= n["stability"] <= 1.0, d["dataset_code"]
            if n["mean_rating"] is not None:
                # ratings are normalized before estimation
                assert 0.0 <= n["mean_rating"] <= 1.0, d["dataset_code"]


async def test_network_endpoint_serves_and_404s(client):
    listing = (await client.get("/api/v1/analytics/dataset-networks")).json()
    assert isinstance(listing, list)
    r = await client.get("/api/v1/analytics/dataset-network/definitely-not-a-dataset")
    assert r.status_code == 404
