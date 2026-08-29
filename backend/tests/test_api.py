"""
API contract tests. Each test pins a behavior that was once broken
(ISSUES.md ids in comments) or a contract the frontend depends on.
"""
import io
import zipfile

import pytest

pytestmark = pytest.mark.asyncio

V = "/api/v1"


# --- envelopes (B13) ---------------------------------------------------------

async def test_studies_envelope(client):
    r = await client.get(f"{V}/studies")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"items", "total", "page", "page_size", "pages"}
    assert body["total"] == 3
    study = body["items"][0]
    assert study["doi"] and study["journal"]


async def test_datasets_envelope_and_detail_n_ratings(client):
    r = await client.get(f"{V}/datasets")
    body = r.json()
    assert body["total"] == 5
    detail = (await client.get(f"{V}/datasets/ds-choc1")).json()
    assert detail["n_ratings"] == 15
    assert detail["study"]["name"].startswith("Chocolate")


async def test_items_envelope(client):
    body = (await client.get(f"{V}/items")).json()
    assert body["total"] == 29


# --- search (B6 field names, item-matching, sort join) -----------------------

async def test_search_matches_items(client):
    r = await client.post(f"{V}/search", json={"query": "chocolate"})
    assert r.status_code == 200
    assert r.json()["total"] == 2  # both datasets containing the chocolate item


async def test_search_year_filters(client):
    r = await client.post(f"{V}/search", json={"filters": {"year_min": 2021, "year_max": 2023}})
    assert r.json()["total"] == 1  # only the 2022 veg study's dataset


async def test_search_sort_by_year_no_cartesian(client):
    plain = (await client.post(f"{V}/search", json={"query": "chocolate"})).json()
    sorted_ = (await client.post(f"{V}/search", json={"query": "chocolate", "sort_by": "year"})).json()
    assert sorted_["total"] == plain["total"]


async def test_search_suggestions_route_exists(client):  # B7
    r = await client.get(f"{V}/search/suggestions", params={"query": "choc"})
    assert r.status_code == 200
    assert "chocolate" in str(r.json()).lower()


# --- aggregations (B4 falsy zero, B5 limit/offset) ----------------------------

async def test_aggregate_preserves_zero_min(client):
    rows = (await client.get(f"{V}/ratings/aggregate", params={"min_ratings": 1})).json()
    choc = next(x for x in rows if x["item_id"] == "it-choc")
    assert choc["min_rating"] == 0.0  # was null before B4
    assert choc["max_rating"] == 1.0
    assert choc["n_ratings"] == 8
    assert choc["datasets_count"] == 2
    assert choc["category"] == "sweets"  # category rides along for the frontend


async def test_aggregate_limit_offset_stable(client):
    full = (await client.get(f"{V}/ratings/aggregate", params={"min_ratings": 1})).json()
    page = (await client.get(f"{V}/ratings/aggregate",
                             params={"min_ratings": 1, "limit": 2, "offset": 1})).json()
    assert [x["item_id"] for x in page] == [x["item_id"] for x in full[1:3]]


# --- downloads (B1 zip, B3 ids, B9 404) ---------------------------------------

async def test_multi_dataset_csv_zip(client):
    r = await client.post(f"{V}/download",
                          json={"dataset_ids": ["ds-choc1", "ds-veg"], "format": "csv"})
    assert r.status_code == 200
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    zf = zipfile.ZipFile(io.BytesIO(blob.content))
    names = zf.namelist()
    assert len([n for n in names if n.endswith(".csv")]) == 2
    assert "metadata.json" in names


async def test_same_second_downloads_get_distinct_ids(client):
    a = await client.post(f"{V}/download", json={"dataset_ids": ["ds-choc1"], "format": "csv"})
    b = await client.post(f"{V}/download", json={"dataset_ids": ["ds-choc1"], "format": "csv"})
    assert a.status_code == b.status_code == 200
    assert a.json()["download_id"] != b.json()["download_id"]


async def test_unknown_dataset_id_is_404(client):
    r = await client.post(f"{V}/download", json={"dataset_ids": ["nope"], "format": "csv"})
    assert r.status_code == 404


async def test_xlsx_download(client):
    r = await client.post(f"{V}/download", json={"dataset_ids": ["ds-veg"], "format": "xlsx"})
    assert r.status_code == 200
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    assert blob.content[:2] == b"PK"  # xlsx is a zip container


async def test_spss_download(client):
    pytest.importorskip("pyreadstat")
    r = await client.post(f"{V}/download", json={"dataset_ids": ["ds-choc2"], "format": "spss"})
    assert r.status_code == 200
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    assert blob.content[:4] == b"$FL2"  # SAV magic


# --- repeated phases must survive export --------------------------------------

async def test_csv_export_carries_timepoint(client):
    """Repeated phases are indistinguishable in an export that drops `timepoint`."""
    import csv, io, collections
    r = await client.post(f"{V}/download",
                          json={"dataset_ids": ["ds-repeat"], "format": "csv"})
    assert r.status_code == 200
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    rows = list(csv.DictReader(io.StringIO(blob.content.decode())))

    assert "timepoint" in rows[0], "export dropped the timepoint column"
    assert {row["timepoint"] for row in rows} == {"1", "2"}
    # 3 subjects x 1 item x 2 timepoints, every observation uniquely keyed
    assert len(rows) == 6
    keys = collections.Counter(
        (row["subject_id"], row["item_id"], row["timepoint"]) for row in rows
    )
    assert not [k for k, n in keys.items() if n > 1]


async def test_json_and_xlsx_exports_carry_timepoint(client):
    import json as _json
    r = await client.post(f"{V}/download",
                          json={"dataset_ids": ["ds-repeat"], "format": "json"})
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    payload = _json.loads(blob.content.decode())
    ratings = payload["datasets"][0]["ratings"]
    assert all("timepoint" in row for row in ratings)
    assert {row["timepoint"] for row in ratings} == {1, 2}

    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    r = await client.post(f"{V}/download",
                          json={"dataset_ids": ["ds-repeat"], "format": "xlsx"})
    blob = await client.get(f"{V}/download/{r.json()['download_id']}")
    df = pd.read_excel(io.BytesIO(blob.content))
    assert "timepoint" in df.columns
    assert set(df["timepoint"]) == {1, 2}


async def test_ratings_expose_subject_id(client):
    """The API, the exports, and the archive must all name this field the same."""
    body = (await client.get(f"{V}/ratings", params={"dataset_id": "ds-choc1"})).json()
    row = body["items"][0]
    assert "subject_id" in row
    assert "participant_id" not in row


# --- descriptives --------------------------------------------------------------

async def test_descriptives_index_lists_datasets_and_timepoints(client):
    rows = (await client.get(f"{V}/descriptives/index")).json()
    by_id = {r["dataset_id"]: r for r in rows}
    # only datasets that actually carry ratings are offered
    assert set(by_id) == {"ds-choc1", "ds-choc2", "ds-veg", "ds-repeat", "ds-pref"}
    assert by_id["ds-repeat"]["timepoints"] == [1, 2]
    assert by_id["ds-veg"]["timepoints"] == [1]
    assert by_id["ds-choc1"]["label"].startswith("Doe")


async def test_descriptives_dataset_items(client):
    items = (await client.get(f"{V}/descriptives/datasets/ds-choc1/items")).json()
    assert {i["item_name"] for i in items} == {"chocolate", "apple", "tortillachips"}
    missing = await client.get(f"{V}/descriptives/datasets/nope/items")
    assert missing.status_code == 404


async def test_descriptives_dataset_item_stats(client):
    r = await client.get(f"{V}/descriptives/dataset-item",
                         params={"dataset_id": "ds-choc1", "item_id": "it-choc"})
    body = r.json()
    # ds-choc1 it-choc ratings are 0,2,5,8,10 on a 0-10 scale
    assert body["n_subjects"] == 5
    assert body["stats"]["mean"] == pytest.approx(5.0)
    assert body["stats"]["median"] == pytest.approx(5.0)
    assert body["stats"]["prop_floor"] == pytest.approx(0.2)   # the single 0
    assert body["stats"]["prop_ceil"] == pytest.approx(0.2)    # the single 10
    assert body["distribution"]["dots"] == [0.0, 2.0, 5.0, 8.0, 10.0]
    assert len(body["distribution"]["kde"]) > 3


async def test_descriptives_timepoint_selection(client):
    """The phase selector must actually change which ratings are summarised."""
    base = {"dataset_id": "ds-repeat", "item_id": "it-rep"}
    first = (await client.get(f"{V}/descriptives/dataset-item", params=base)).json()
    second = (await client.get(f"{V}/descriptives/dataset-item",
                               params={**base, "timepoint": 2})).json()
    assert first["timepoint"] == 1 and second["timepoint"] == 2
    assert first["available_timepoints"] == [1, 2]
    assert first["stats"]["mean"] == pytest.approx(3.0)   # 1,3,5
    assert second["stats"]["mean"] == pytest.approx(4.0)  # 2,4,6

    # an out-of-range phase falls back to the first rather than 404ing
    fallback = (await client.get(f"{V}/descriptives/dataset-item",
                                 params={**base, "timepoint": 9})).json()
    assert fallback["timepoint"] == 1


async def test_descriptives_dataset_item_404(client):
    r = await client.get(f"{V}/descriptives/dataset-item",
                         params={"dataset_id": "ds-veg", "item_id": "it-choc"})
    assert r.status_code == 404  # kale/apple only in ds-veg


async def test_descriptives_item_across_datasets(client):
    """Cross-study panels summarise each dataset on the normalised 0-1 axis."""
    body = (await client.get(f"{V}/descriptives/items/it-choc")).json()
    assert body["n_datasets"] == 2          # it-choc appears in choc1 and choc2
    assert set(body["stats"]) == {"mean", "sd", "skewness", "prop_floor", "prop_ceil"}

    by_ds = {d["dataset_id"]: d for d in body["datasets"]}
    # ds-choc1: 0,2,5,8,10 on 0-10 -> normalised mean 0.5
    assert by_ds["ds-choc1"]["mean"] == pytest.approx(0.5)
    # ds-choc2: -10,0,10 on -10..10 -> normalised mean 0.5, both ends hit once
    assert by_ds["ds-choc2"]["mean"] == pytest.approx(0.5)
    assert by_ds["ds-choc2"]["prop_floor"] == pytest.approx(1 / 3)
    assert by_ds["ds-choc2"]["prop_ceil"] == pytest.approx(1 / 3)
    # every dot has a matching dataset label for the hover text
    assert len(body["stats"]["mean"]["dots"]) == len(body["stats"]["mean"]["dots_detail"])


async def test_descriptives_item_uses_first_phase_only(client):
    """Repeated phases must not double-count a dataset in the cross-study view."""
    body = (await client.get(f"{V}/descriptives/items/it-rep")).json()
    assert body["n_datasets"] == 1
    row = body["datasets"][0]
    assert row["timepoint"] == 1
    assert row["n"] == 3                       # not 6
    assert row["mean_raw"] == pytest.approx(3.0)  # phase 1 values 1,3,5


async def test_descriptives_item_404(client):
    assert (await client.get(f"{V}/descriptives/items/nope")).status_code == 404


# --- preference similarity -----------------------------------------------------

async def test_similar_items_are_ranked_by_shared_preference(client):
    """Items liked by the same people rank together; opposite tastes rank apart."""
    r = await client.get(f"{V}/descriptives/items/it-pref-sweet-0/similar",
                         params={"min_shared_subjects": 5, "limit": 30})
    assert r.status_code == 200
    body = r.json()

    top = body["most_similar"]
    assert all(n["item_name"].startswith("prefsweet") for n in top[:5]), \
        [n["item_name"] for n in top[:5]]
    assert top[0]["r"] > 0.9

    bottom = body["most_dissimilar"]
    assert all(n["item_name"].startswith("prefsavoury") for n in bottom[:5]), \
        [n["item_name"] for n in bottom[:5]]
    assert bottom[0]["r"] < -0.9

    # the target itself is never its own neighbour
    assert all(n["item_id"] != "it-pref-sweet-0"
               for n in top + bottom)


async def test_similarity_is_person_centred(client):
    """Without centring, a response-style offset makes everything correlate.

    ds-pref gives each subject a generosity offset far larger than the taste
    difference. Uncentred, even opposite-taste items correlate at about +0.97;
    the centred result must instead be strongly negative.
    """
    body = (await client.get(f"{V}/descriptives/items/it-pref-sweet-0/similar",
                             params={"min_shared_subjects": 5, "limit": 30})).json()
    by_name = {n["item_name"]: n["r"] for n in
               body["most_similar"] + body["most_dissimilar"]}
    assert by_name["prefsavoury0"] < -0.9, by_name["prefsavoury0"]


async def test_similarity_skips_narrow_datasets(client):
    """A 2-item dataset yields r = -1 mechanically once centred, so it is skipped."""
    body = (await client.get(f"{V}/descriptives/items/it-pref-sweet-0/similar",
                             params={"min_shared_subjects": 5})).json()
    assert body["min_items_per_dataset"] >= 20
    # ds-choc1 (3 items) and ds-repeat (1 item) must contribute nothing
    names = {n["item_name"] for n in body["most_similar"] + body["most_dissimilar"]}
    assert not names & {"chocolate", "apple", "kale", "tortillachips", "repeatsnack"}


async def test_similar_items_404_for_unknown_item(client):
    r = await client.get(f"{V}/descriptives/items/nope/similar")
    assert r.status_code == 404


# --- read-only API (B8) --------------------------------------------------------

async def test_mutation_endpoints_removed(client):
    assert (await client.post(f"{V}/studies", json={})).status_code == 405
    assert (await client.put(f"{V}/studies/study-choc", json={})).status_code == 405
    assert (await client.delete(f"{V}/studies/study-choc")).status_code == 405
    assert (await client.post(f"{V}/datasets", json={})).status_code == 405


# --- misc ------------------------------------------------------------------------

async def test_health(client):
    assert (await client.get("/health")).status_code == 200


async def test_metadata_endpoints(client):
    scale = (await client.get(f"{V}/metadata/scale-types")).json()
    assert set(scale["scale_types"]) == {"likert", "continuous", "slider"}
    years = (await client.get(f"{V}/metadata/years")).json()
    assert years == {"min_year": 2020, "max_year": 2022}


# --- item network -------------------------------------------------------------

async def test_item_network_triangle(client):
    net = (await client.get(f"{V}/analytics/item-network",
                            params={"min_shared": 1, "min_frequency": 2})).json()
    labels = {n["label"] for n in net["nodes"]}
    assert labels == {"chocolate", "apple", "kale"}  # tortillachips: 1 dataset only
    assert net["meta"]["edge_count"] == 3            # triangle via shared datasets
    assert net["meta"]["components"] == 1
    node = net["nodes"][0]
    assert {"id", "label", "category", "frequency", "mean_rating", "x", "y"} <= set(node)


async def test_item_network_threshold_empties(client):
    net = (await client.get(f"{V}/analytics/item-network",
                            params={"min_shared": 2, "min_frequency": 2})).json()
    assert net["meta"]["edge_count"] == 0 and net["meta"]["node_count"] == 0


async def test_item_network_category_filter(client):
    net = (await client.get(f"{V}/analytics/item-network",
                            params={"min_shared": 1, "min_frequency": 2,
                                    "categories": ["fruits", "vegetables"]})).json()
    assert {n["label"] for n in net["nodes"]} == {"apple", "kale"}
    assert net["meta"]["edge_count"] == 1


async def test_item_network_backbone(client):
    # top-1 edge per node over the equal-weight triangle -> a 2-edge path,
    # still one component (backbone must not disconnect the graph here)
    net = (await client.get(f"{V}/analytics/item-network",
                            params={"min_shared": 1, "min_frequency": 2,
                                    "max_edges_per_node": 1})).json()
    assert net["meta"]["edge_count"] == 2
    assert net["meta"]["components"] == 1
    assert net["meta"]["node_count"] == 3


async def test_ratings_include_normalized(client):
    rows = (await client.get(f"{V}/ratings", params={"page_size": 5})).json()["items"]
    assert all(r["normalized_rating"] is not None for r in rows)
    assert all(0 <= r["normalized_rating"] <= 1 for r in rows)


async def test_aggregate_statistics_are_coherent(client):
    """The aggregate is computed in SQL; check it still describes the ratings.

    A broken rewrite of that query would most likely show up as a median
    outside the range, a negative spread, or a dataset count that exceeds the
    number of ratings — none of which the shape assertions above would catch.
    """
    rows = (await client.get(f"{V}/ratings/aggregate", params={"min_ratings": 1})).json()
    assert rows, "expected at least one aggregated item"
    for r in rows:
        assert r["n_ratings"] >= 1
        assert r["min_rating"] <= r["median_rating"] <= r["max_rating"], r["item_id"]
        assert r["min_rating"] <= r["mean_rating"] <= r["max_rating"], r["item_id"]
        assert r["std_rating"] >= 0.0, r["item_id"]
        # a single rating has no spread, and every rating belongs to a dataset
        if r["n_ratings"] == 1:
            assert r["std_rating"] == 0.0, r["item_id"]
        assert 1 <= r["datasets_count"] <= r["n_ratings"], r["item_id"]
    # most-rated first, item id breaking ties, so pages stay stable
    keys = [(-r["n_ratings"], r["item_id"]) for r in rows]
    assert keys == sorted(keys)
