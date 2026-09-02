#!/usr/bin/env python
"""
Publish a release to Zenodo.

The client packages read release assets over plain HTTP with no credentials.
That works against a public host and not against this repository, which is
private: GitHub answers an unauthenticated request for its releases with 404,
so `list_datasets()` fails for everyone including the owner. Zenodo is public,
needs no token to read, and mints a DOI the database can be cited by.

This script creates a *draft* deposition and uploads to it. It does not
publish. Publishing on Zenodo is irreversible -- the DOI is permanent and the
files cannot be removed afterwards -- so that step stays a deliberate click,
or an explicit --publish once the draft has been read.

Versioning: pass --parent to add a new version to an existing Zenodo record
rather than creating an unrelated one. Zenodo then keeps a concept DOI that
always resolves to the newest version, which is what a citation should use.

Usage:
    export ZENODO_TOKEN=...                     # or ZENODO_SANDBOX_TOKEN
    python scripts/publish_to_zenodo.py --version 1.4.0 [--sandbox]
    python scripts/publish_to_zenodo.py --version 1.5.0 --parent 1234567
"""
import argparse
import json
import os
import sys
from pathlib import Path

import time

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE = "https://zenodo.org/api"
SANDBOX = "https://sandbox.zenodo.org/api"


def _request(method, url, tries: int = 5, **kw):
    """A Zenodo call, retried through the gateway errors it hands out.

    Zenodo intermittently answers 502/504 under load, and an upload of seventy
    files hits that often enough that a single failure would otherwise leave a
    half-filled draft behind.
    """
    delay = 3.0
    last = None
    for attempt in range(tries):
        try:
            r = requests.request(method, url, **kw)
        except requests.RequestException as exc:
            last = exc
        else:
            if r.status_code not in (500, 502, 503, 504):
                return r
            last = f"HTTP {r.status_code}"
        if attempt < tries - 1:
            print(f"    {last} — retrying in {delay:.0f}s")
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise SystemExit(f"Zenodo kept failing on {method} {url.split('?')[0]}: {last}")


def metadata(version: str) -> dict:
    return {
        "metadata": {
            "title": "The Liking Initiative: a database of subjective evaluation "
                     "ratings for decision-making research",
            "upload_type": "dataset",
            "version": version,
            "description": (
                "<p>Subjective liking ratings from published decision-making studies, "
                "collected into one database with a common normalized scale so ratings "
                "from different response formats can be compared.</p>"
                "<p>Each release ships the whole corpus as tab-separated files: a "
                "catalogue of every study and dataset, one file per dataset, and one "
                "file holding every rating. <code>codebook.md</code> documents the "
                "columns and the two things most likely to be got wrong &mdash; that "
                "cross-study comparisons must use <code>normalized_rating</code>, and "
                "that subject identifiers are unique only within a dataset.</p>"
                "<p>The <code>likingInitiative</code> packages for R and Python read "
                "these files directly. They are ordinary TSVs and can be used without "
                "either package.</p>"
                "<p>Every correction applied to the data is recorded in "
                "<code>catalog.json</code> as a numbered migration, so any value here "
                "can be traced back to the source file it came from.</p>"
            ),
            "creators": [
                {"name": "Fernandez, Kianté"},
                {"name": "Goyal, Sumedha"},
                {"name": "Krajbich, Ian"},
            ],
            "keywords": ["food preference", "liking ratings", "value-based decision making",
                         "subjective value", "open data", "psychology"],
            "license": "mit",
            "access_right": "open",
            "related_identifiers": [
                {"identifier": "https://github.com/liking-initiative/liking-rating-database",
                 "relation": "isSupplementTo", "scheme": "url"},
            ],
        }
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="release version, e.g. 1.4.0")
    ap.add_argument("--dir", default=str(REPO_ROOT / "release"),
                    help="directory built by scripts/build_release.py")
    ap.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org")
    ap.add_argument("--parent", help="existing Zenodo record id to add a version to")
    ap.add_argument("--deposition", help="resume uploading into an existing draft id")
    ap.add_argument("--publish", action="store_true",
                    help="publish immediately — irreversible, mints a permanent DOI")
    args = ap.parse_args()

    base = SANDBOX if args.sandbox else LIVE
    token = os.environ.get("ZENODO_SANDBOX_TOKEN" if args.sandbox else "ZENODO_TOKEN")
    if not token:
        sys.exit("Set ZENODO_TOKEN (or ZENODO_SANDBOX_TOKEN for --sandbox). "
                 "Create one at zenodo.org/account/settings/applications/tokens/new/ "
                 "with the deposit:write and deposit:actions scopes.")

    src = Path(args.dir)
    files = sorted(p for p in src.rglob("*") if p.is_file())
    if not files:
        sys.exit(f"no files in {src} — run scripts/build_release.py --version {args.version}")
    total = sum(p.stat().st_size for p in files)
    print(f"  {len(files)} files, {total / 1048576:.1f} MB from {src}")

    auth = {"params": {"access_token": token}}

    if args.deposition:
        # Resume: a large upload can be interrupted, and re-uploading 26 MB of
        # files that already landed is pure waste.
        r = _request("GET", f"{base}/deposit/depositions/{args.deposition}", **auth)
        if not r.ok:
            sys.exit(f"could not read draft {args.deposition}: {r.status_code}")
        dep = r.json()
    elif args.parent:
        r = _request("POST", f"{base}/deposit/depositions/{args.parent}/actions/newversion", **auth)
        if not r.ok:
            sys.exit(f"could not draft a new version of {args.parent}: {r.status_code} {r.text[:200]}")
        dep = requests.get(r.json()["links"]["latest_draft"], **auth).json()
        # a new version inherits the previous files; clear them so this upload stands alone
        for f in requests.get(f"{base}/deposit/depositions/{dep['id']}/files", **auth).json():
            requests.delete(f"{base}/deposit/depositions/{dep['id']}/files/{f['id']}", **auth)
    else:
        r = _request("POST", f"{base}/deposit/depositions", json={}, **auth)
        if not r.ok:
            sys.exit(f"could not create a deposition: {r.status_code} {r.text[:200]}")
        dep = r.json()

    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    print(f"  draft deposition {dep_id}")

    r = _request("PUT", f"{base}/deposit/depositions/{dep_id}",
                 json=metadata(args.version),
                 headers={"Content-Type": "application/json"}, **auth)
    if not r.ok:
        sys.exit(f"metadata rejected: {r.status_code} {r.text[:300]}")

    already = {f["filename"] for f in _request(
        "GET", f"{base}/deposit/depositions/{dep_id}/files", **auth).json()}
    if already:
        print(f"  {len(already)} file(s) already uploaded, skipping those")

    for i, path in enumerate(files, 1):
        # Zenodo's file store is flat and reads a slash in the bucket URL as a
        # path, so nested names 404. Flatten with the same separator the client
        # already uses for GitHub, so one naming works against either host.
        name = str(path.relative_to(src)).replace(os.sep, "__")
        if name in already:
            continue
        with open(path, "rb") as fh:
            u = _request("PUT", f"{bucket}/{name}", data=fh, **auth)
        if not u.ok:
            sys.exit(f"upload failed for {name}: {u.status_code} {u.text[:200]}")
        if i % 10 == 0 or i == len(files):
            print(f"    uploaded {i}/{len(files)}")

    link = dep["links"].get("html", f"{base}/deposit/depositions/{dep_id}")
    if args.publish:
        r = _request("POST", f"{base}/deposit/depositions/{dep_id}/actions/publish", **auth)
        if not r.ok:
            sys.exit(f"publish failed: {r.status_code} {r.text[:300]}")
        published = r.json()
        print(f"\n  PUBLISHED  doi: {published.get('doi')}")
        print(f"  record: {published['links'].get('record_html')}")
    else:
        print(f"\n  Draft created but NOT published — publishing mints a permanent DOI.")
        print(f"  Review it at: {link}")
        print(f"  Then publish in the browser, or re-run with --publish.")


if __name__ == "__main__":
    main()
