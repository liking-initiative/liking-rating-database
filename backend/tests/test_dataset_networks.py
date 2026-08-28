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


def test_estimated_networks_declare_their_selection():
    """Items are chosen by bootstrap stability, and that must ship with them."""
    for d in _load_all():
        if not d["estimated"]:
            continue
        sel = d["selection"]
        code = d["dataset_code"]
        assert sel["items_retained"] <= sel["items_tested"] <= sel["items_in_dataset"], code
        assert sel["items_retained"] + sel["items_dropped_unstable"] == sel["items_tested"], code
        # a graphical model over items needs more subjects than items
        assert sel["subjects_complete"] >= 2 * sel["items_retained"], code
        assert len(d["dropped_items"]) == sel["items_dropped_unstable"], code

        method = d["method"]
        assert "bootEGA" in method["algorithm"]
        assert method["iterations"] >= 100
        assert method["seed"] is not None, "results must be reproducible"
        # 0.45 is deliberately below EGAnet's documented 0.70-0.75, chosen to
        # give more datasets a network. The value ships with each result so the
        # page states it rather than implying the stricter default.
        assert 0.4 <= method["stability_cutoff"] <= 0.95


def test_retained_items_were_stable_before_selection():
    """Every kept item cleared the cutoff on the fit that selected it."""
    for d in _load_all():
        if not d["estimated"]:
            continue
        cutoff = d["method"]["stability_cutoff"]
        for n in d["nodes"]:
            before = n.get("stability_before_selection")
            assert before is not None, d["dataset_code"]
            assert before >= cutoff - 1e-9, (
                f"{d['dataset_code']}/{n['label']} kept at {before} below {cutoff}"
            )


def test_dimension_stability_is_reported():
    for d in _load_all():
        if not d["estimated"] or not d.get("dimension_stability"):
            continue
        for dim in d["dimension_stability"]:
            assert 0.0 <= dim["structural_consistency"] <= 1.0, d["dataset_code"]
            if dim["average_item_stability"] is not None:
                assert 0.0 <= dim["average_item_stability"] <= 1.0


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
