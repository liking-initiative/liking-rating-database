#!/usr/bin/env python
"""
Check every stored DOI against CrossRef and against doi.org.

Reports three kinds of problem:

* **unregistered** — doi.org does not resolve it at all. The citation is broken.
* **title mismatch** — the DOI resolves, but to a paper whose title does not
  match the study we filed it under. Usually means the DOI is simply wrong.
* **superseded** — the DOI points at a preprint of a paper that has since
  been published, or at a version-pinned DOI when a later version exists. The
  link works but sends a reader to a draft.

  Two ways of detecting this, because one is not enough. CrossRef `relation`
  fields are only present when a publisher deposits them: Frömer et al. was
  published in Open Mind with no `is-preprint-of` recorded on the preprint,
  and relation-following missed it entirely. So every preprint DOI is *also*
  searched for by title and author among journal articles.

A publisher returning 403 to this script is not a problem: APA, SAGE, PNAS
and J Neurosci block automated requests. What matters is that doi.org issues
a redirect, which is what the registration check tests.

Usage:
    python scripts/verify_dois.py [--db data/liking_rating_db.db] [--json out.json]
"""
import argparse
import difflib
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "liking-rating-database-doi-check/1.0 (mailto:kiantefernan@gmail.com)"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "liking_rating_db.db"
TITLE_THRESHOLD = 0.85


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)["message"]


def find_published_version(title, authors):
    """Search CrossRef for a journal article matching a preprint's title.

    Relations catch the easy cases; this catches the ones where the publisher
    never deposited a link back to the preprint.
    """
    query = {"query.bibliographic": title, "rows": 5, "filter": "type:journal-article"}
    if authors:
        query["query.author"] = authors
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            items = json.load(r)["message"]["items"]
    except Exception:
        return None
    for item in items:
        found = (item.get("title") or [""])[0]
        if difflib.SequenceMatcher(None, _norm(title), _norm(found)).ratio() >= 0.85:
            return {
                "doi": item.get("DOI"),
                "title": found,
                "journal": (item.get("container-title") or [""])[0],
                "year": (item.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0],
            }
    return None


def registered(doi):
    """True if doi.org resolves the DOI, regardless of what the publisher does."""
    opener = urllib.request.build_opener(_NoRedirect())
    req = urllib.request.Request("https://doi.org/" + doi, headers={"User-Agent": UA})
    try:
        r = opener.open(req, timeout=45)
        code, loc = r.status, r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        code, loc = e.code, e.headers.get("Location", "")
    except Exception:
        return False, ""
    return (code in (301, 302, 303, 307, 308) and bool(loc)), loc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    studies = con.execute(
        "SELECT name, year, doi, journal FROM studies "
        "WHERE doi IS NOT NULL AND doi != '' ORDER BY year"
    ).fetchall()

    rows, problems = [], []
    for s in studies:
        doi = s["doi"].strip()
        rec = {"name": s["name"], "doi": doi, "our_year": s["year"]}

        ok, dest = registered(doi)
        rec["registered"] = ok
        rec["resolves_to"] = dest
        if not ok:
            rec["problem"] = "unregistered"
            problems.append(rec)
            rows.append(rec)
            continue

        try:
            m = crossref(doi)
        except Exception as e:
            rec["problem"] = f"crossref lookup failed: {type(e).__name__}"
            problems.append(rec)
            rows.append(rec)
            time.sleep(0.4)
            continue

        title = (m.get("title") or [""])[0]
        rec["crossref_title"] = title
        rec["type"] = m.get("type")
        rec["similarity"] = round(
            difflib.SequenceMatcher(None, _norm(s["name"]), _norm(title)).ratio(), 3
        )
        if rec["similarity"] < TITLE_THRESHOLD:
            rec["problem"] = "title mismatch"
            problems.append(rec)

        # A preprint DOI: check by search as well as by relation.
        if m.get("type") == "posted-content":
            first_author = ((m.get("author") or [{}])[0].get("family") or "")
            published = find_published_version(title or s["name"], first_author)
            if published:
                rec["published_version"] = published["doi"]
                rec["published_in"] = f"{published['journal']} ({published['year']})"
                rec["problem"] = "preprint of a published article"
                problems.append(rec)
                rows.append(rec)
                time.sleep(0.6)
                continue

        relations = m.get("relation") or {}
        if "is-preprint-of" in relations:
            rec["published_version"] = relations["is-preprint-of"][0].get("id")
            rec["problem"] = "superseded by a published version"
            problems.append(rec)
        elif "has-version" in relations:
            rec["newer_version"] = relations["has-version"][0].get("id")
            rec["problem"] = "a newer version of this record exists"
            problems.append(rec)

        rows.append(rec)
        time.sleep(0.4)

    print(f"checked {len(rows)} DOIs — {len(rows) - len(problems)} clean, "
          f"{len(problems)} to look at")
    for p in problems:
        print(f"\n  {p['problem']}")
        print(f"    {p['doi']}  {p['name'][:64]}")
        if p.get("crossref_title"):
            print(f"    crossref: {p['crossref_title'][:64]}")
        for k in ("published_version", "published_in", "newer_version"):
            if p.get(k):
                print(f"    {k}: {p[k]}")

    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2))
        print(f"\nfull report -> {args.json}")

    return 1 if any(p.get("problem") == "unregistered" for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
