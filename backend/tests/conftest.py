"""
Test fixtures: a small synthetic database seeded through the app's own models,
served through the real FastAPI app via httpx's ASGI transport.

DATABASE_URL must be set before backend modules import settings, so it is
configured at module import time here.
"""
import asyncio
import os
import tempfile
import uuid
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp(prefix="lrd_test_")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"  # keep the limiter out of tests
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.models import database
from backend.models.database import Dataset, Item, Rating, Study, init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _seed():
    async with database.async_session() as s:
        studies = [
            Study(id="study-choc", name="Chocolate preferences across contexts",
                  authors=["Doe, J.", "Roe, R."], year=2020,
                  doi="10.1000/choc", journal="Journal of Testing",
                  publication_title="Doe & Roe (2020). Chocolate preferences. J Testing."),
            Study(id="study-veg", name="Vegetable liking in adults",
                  authors=["Poe, E."], year=2022, doi="10.1000/veg",
                  journal="Annals of Fixtures"),
            # year 2020 keeps the metadata year-range and the 2021-2023 search
            # filter assertions unchanged
            Study(id="study-repeat", name="Repeated liking phases",
                  authors=["Moe, M."], year=2020, doi="10.1000/repeat",
                  journal="Annals of Fixtures"),
        ]
        datasets = [
            Dataset(id="ds-choc1", study_id="study-choc", name="choc1 Dataset",
                    n_subjects=5, n_items=4, rating_scale_min=0, rating_scale_max=10,
                    rating_scale_type="likert", data_completeness=100.0),
            Dataset(id="ds-choc2", study_id="study-choc", name="choc2 Dataset",
                    n_subjects=3, n_items=4, rating_scale_min=-10, rating_scale_max=10,
                    rating_scale_type="continuous", data_completeness=100.0),
            Dataset(id="ds-veg", study_id="study-veg", name="veg Dataset",
                    n_subjects=4, n_items=3, rating_scale_min=1, rating_scale_max=5,
                    rating_scale_type="likert", data_completeness=100.0),
            # repeated-phase dataset: the same subjects rate the same item twice
            Dataset(id="ds-repeat", study_id="study-repeat", name="repeat Dataset",
                    n_subjects=3, n_items=1, rating_scale_min=1, rating_scale_max=7,
                    rating_scale_type="likert", data_completeness=100.0),
            # wide enough to clear the preference-similarity item floor
            Dataset(id="ds-pref", study_id="study-repeat", name="pref Dataset",
                    n_subjects=12, n_items=24, rating_scale_min=0, rating_scale_max=100,
                    rating_scale_type="slider", data_completeness=100.0),
        ]
        items = [
            Item(id="it-choc", name="chocolate", standardized_name="chocolate",
                 category="sweets", frequency=2),
            Item(id="it-apple", name="apple", standardized_name="apple",
                 category="fruits", frequency=2),
            Item(id="it-kale", name="kale", standardized_name="kale",
                 category="vegetables", frequency=2),
            Item(id="it-chip", name="tortillachips", standardized_name="tortillachips",
                 category="chips", frequency=1),
            Item(id="it-rep", name="repeatsnack", standardized_name="repeatsnack",
                 category="snacks", frequency=1),
        ]
        s.add_all(studies + datasets + items)

        def spread(ds, item, values, lo, hi, timepoint=1):
            for subj, v in enumerate(values, start=1):
                s.add(Rating(id=str(uuid.uuid4()), dataset_id=ds, item_id=item,
                             subject_id=str(subj), timepoint=timepoint, rating=float(v),
                             normalized_rating=(v - lo) / (hi - lo)))

        # ds-choc1: 0..10 likert, incl. a genuine 0 rating (falsy-zero regression)
        spread("ds-choc1", "it-choc", [0, 2, 5, 8, 10], 0, 10)
        spread("ds-choc1", "it-apple", [1, 3, 5, 7, 9], 0, 10)
        spread("ds-choc1", "it-chip", [2, 4, 6, 8, 10], 0, 10)
        # ds-choc2: -10..10 continuous
        spread("ds-choc2", "it-choc", [-10, 0, 10], -10, 10)
        spread("ds-choc2", "it-kale", [-5, 0, 5], -10, 10)
        # ds-veg: 1..5 likert
        spread("ds-veg", "it-kale", [1, 2, 3, 4], 1, 5)
        spread("ds-veg", "it-apple", [2, 3, 4, 5], 1, 5)
        # ds-repeat: the same (subject, item) pairs at two timepoints, different values
        for tp, vals in ((1, [1, 3, 5]), (2, [2, 4, 6])):
            spread("ds-repeat", "it-rep", vals, 1, 7, timepoint=tp)

        # ds-pref exercises preference similarity. Two latent tastes: subjects
        # split into a "sweet" half and a "savoury" half. pref-sweet-* track
        # each other, pref-savoury-* track each other, and the two groups move
        # opposite. A per-subject offset is layered on so that WITHOUT
        # person-centring every pair would look positively correlated -- the
        # response-style artifact the centring exists to remove.
        pref_items = []
        for group in ("sweet", "savoury"):
            for k in range(12):
                iid = f"it-pref-{group}-{k}"
                pref_items.append(
                    Item(id=iid, name=f"pref{group}{k}", standardized_name=f"pref{group}{k}",
                         category="sweets" if group == "sweet" else "vegetables",
                         frequency=1)
                )
        s.add_all(pref_items)

        # The generosity offset (span 66) deliberately dwarfs the taste
        # difference (10), reproducing foljac2's shape: uncentred, even
        # opposite-taste items correlate at +0.97; centred, they sit at -1.0.
        for subj in range(1, 13):
            likes_sweet = subj <= 6
            generosity = subj * 6.0          # the response-style offset
            for group in ("sweet", "savoury"):
                high = (group == "sweet") == likes_sweet
                for k in range(12):
                    base = 20.0 if high else 10.0
                    v = base + generosity + (0.1 * k)
                    s.add(Rating(id=str(uuid.uuid4()), dataset_id="ds-pref",
                                 item_id=f"it-pref-{group}-{k}", subject_id=str(subj),
                                 timepoint=1, rating=float(v),
                                 normalized_rating=min(max(v / 100.0, 0.0), 1.0)))
        await s.commit()


@pytest_asyncio.fixture(scope="session")
async def client():
    await init_db()
    await _seed()
    from backend.app import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
