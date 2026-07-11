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
    assert body["total"] == 2
    study = body["items"][0]
    assert study["doi"] and study["journal"]


async def test_datasets_envelope_and_detail_n_ratings(client):
    r = await client.get(f"{V}/datasets")
    body = r.json()
    assert body["total"] == 3
    detail = (await client.get(f"{V}/datasets/ds-choc1")).json()
    assert detail["n_ratings"] == 15
    assert detail["study"]["name"].startswith("Chocolate")


async def test_items_envelope(client):
    body = (await client.get(f"{V}/items")).json()
    assert body["total"] == 4


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
    assert set(scale["scale_types"]) == {"likert", "continuous"}
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
