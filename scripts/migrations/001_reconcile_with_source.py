#!/usr/bin/env python
"""
Migration 001 — reconcile the database with its authoritative sources.

Sources of truth, in order:
  1. `Liking Rating Database/final_database.csv` (RA's compiled ratings; values verified
     against the DB import 2026-07-09 — the import used the MEAN for repeated
     (subject, item) ratings, which this migration preserves)
  2. `Liking Rating Database/Liking Rating Database.xlsx` (per-dataset scales, citations)
  3. `reference-papers/0_Fernandez-Liking-Database-updated.docx` Table 1 (per-study scales)

What this migration does and the evidence for each step:

  A. Consolidate duplicate study rows (35 rows -> 24 publications). Datasets are
     repointed to one canonical row per publication; the orphaned "High-value
     decisions" row (parent of the deleted shevsmith2) is merged into its twin.
  B. Enrich every study with its full citation, DOI, journal, and corrected year
     (e.g. "Spacing of cue-approach training" is Bakkour et al. 2018 PLOS ONE,
     not 2021).
  C. Re-ingest romfred from the source CSV. The original import stored
     (rating+10)/2, mapping the true -10..10 range onto 0..10, corrupting every
     value. Re-ingest takes the mean per (subject, item) — the same policy the
     original import used for toyam — giving the expected 27,108 rows.
  D. libain1/libain2: declared 0..99 but the source holds integers 0..100
     (101 distinct values). Scale becomes 0..100.
  E. deskrab2: the source itself contains slider overshoot (971 values in
     (10, 10.1]) on a -10..10 continuous scale. Clamp to 10.0.
  F. foljac2: the source stores values already normalized to 0..1 (the paper's
     scale is WTP 0..3; original units are not recoverable from the CSV).
     Scale metadata becomes 0..1 with a provenance note in the description.
  G. Set rating_scale_type per dataset from the source data + papers
     (taxonomy: likert / continuous / vas / slider / wtp) — previously every
     dataset was labelled 'likert'.
  H. Recompute normalized_rating = (rating - min) / (max - min) for ALL datasets.
  I. Recompute n_subjects / n_items from actual ratings.
  J. Replace the fabricated data_completeness (constant 95.0) with the real
     value: n_ratings / (n_subjects * n_items) * 100.
  K. Recompute items.frequency = COUNT(DISTINCT dataset_id) (wrong for 2,243 of
     2,248 items before this migration).
  L. Backfill ratings.created_at (NULL for 146,963 rows re-ingested by the old
     fix_database.py).
  M. Normalize float-string subject_ids ('1.0' -> '1') where collision-free.

Usage:
    python scripts/migrations/001_reconcile_with_source.py <db_path> [--csv <path>] [--apply]

Dry-run (default) runs everything inside a transaction, prints the report, and
rolls back. --apply commits. The migration is recorded in schema_migrations and
refuses to run twice.
"""
import argparse
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

VERSION = "001"
NAME = "reconcile_with_source"

# --- B. study enrichment: DB study name -> citation metadata -----------------
# Extracted 2026-07-09 from the RA's 'studies' sheet; DOIs regex-verified.
CITATIONS = {
    "Attention and choice across domains": {
        "doi": "10.1037/xge0000482", "journal": "Journal of Experimental Psychology: General", "year": 2018,
        "citation": "Smith, S. M., & Krajbich, I. (2018). Attention and choice across domains. Journal of Experimental Psychology: General, 147(12), 1810–1826."},
    "Attitudes and attention": {
        "doi": "10.1016/j.jesp.2019.103892", "journal": "Journal of Experimental Social Psychology", "year": 2020,
        "citation": "Gwinn, R., & Krajbich, I. (2020). Attitudes and attention. Journal of Experimental Social Psychology, 86, 103892."},
    "Computational Methods for Predicting and Understanding Food Judgment": {
        "doi": "10.1177/09567976211043426", "journal": "Psychological Science", "year": 2022,
        "citation": "Gandhi, N., Zou, W., Meyer, C., Bhatia, S., & Walasek, L. (2022). Computational Methods for Predicting and Understanding Food Judgment. Psychological Science, 33(4), 579–594."},
    "Considering what we know and what we don't know: Expectations and confidence guide value integration in value-based decision-making": {
        "doi": "10.31234/osf.io/2sqyt_v1", "journal": "PsyArXiv (preprint)", "year": 2022,
        "citation": "Frömer, R., Callaway, F., Griffiths, T., & Shenhav, A. (2022). Considering what we know and what we don't know: Expectations and confidence guide value integration in value-based decision-making. PsyArXiv."},
    "Decomposing preferences into predispositions and evaluations": {
        "doi": "10.1037/xge0001162", "journal": "Journal of Experimental Psychology: General", "year": 2021,
        "citation": "Desai, N., & Krajbich, I. (2021). Decomposing preferences into predispositions and evaluations. Journal of Experimental Psychology: General, 151(8), 1883."},
    "Elucidating the underlying components of food valuation in the human orbitofrontal cortex": {
        "doi": "10.1038/s41593-017-0008-x", "journal": "Nature Neuroscience", "year": 2017,
        "citation": "Suzuki, S., Cross, L. & O'Doherty, J.P. (2017). Elucidating the underlying components of food valuation in the human orbitofrontal cortex. Nature Neuroscience, 20, 1780–1786."},
    "Explicit representation of confidence informs future value-based decisions": {
        "doi": "10.1038/s41562-016-0002", "journal": "Nature Human Behaviour", "year": 2016,
        "citation": "Folke, T., Jacobsen, C., Fleming, S. M., & De Martino, B. (2016). Explicit representation of confidence informs future value-based decisions. Nature Human Behaviour, 1(1)."},
    "High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity": {
        "doi": "10.1073/pnas.2101508119", "journal": "Proceedings of the National Academy of Sciences", "year": 2022,
        "citation": "Shevlin, B. R. K., Smith, S. M., Hausfeld, J., & Krajbich, I. (2022). High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity. PNAS, 119(6)."},
    "Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice": {
        "doi": None, "journal": "Judgment and Decision Making", "year": 2021,
        "citation": "Hascher, J., Desai, N., & Krajbich, I. (2021). Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice. Judgment & Decision Making, 16(6)."},
    "Increased BMI is associated with an altered decision-making process during healthy food choices in males and females": {
        "doi": "10.1016/j.appet.2025.107859", "journal": "Appetite", "year": 2025,
        "citation": "Larenas, G., Luarte, L., Kerr, B., Ossandón, T., Cortés, V., Baudrand, R., & Pérez Leighton, C. (2025). Increased BMI is associated with an altered decision-making process during healthy food choices in males and females. Appetite."},
    "Investigating psychological mechanisms of self-controlled decisions for food and leisure activity": {
        "doi": "10.1007/s10865-024-00469-3", "journal": "Journal of Behavioral Medicine", "year": 2024,
        "citation": "Bailey, C., & Lim, S.L. (2024). Investigating psychological mechanisms of self-controlled decisions for food and leisure activity. Journal of Behavioral Medicine, 47, 458–470."},
    "Memorable but not chosen: No effect of memorability on value-based decisions": {
        "doi": "10.31234/osf.io/xqhk8", "journal": "PsyArXiv (preprint)", "year": 2022,
        "citation": "Li, X., Bainbridge, W., & Bakkour, A. (2022). Memorable but not chosen: No effect of memorability on value-based decisions. PsyArXiv."},
    "Mental representations distinguish value-based decisions from perceptual decisions": {
        "doi": "10.3758/s13423-021-01911-2", "journal": "Psychonomic Bulletin & Review", "year": 2021,
        "citation": "Smith, S. M., & Krajbich, I. (2021). Mental representations distinguish value-based decisions from perceptual decisions. Psychonomic Bulletin & Review, 28(4), 1413–1422."},
    "Mutual inclusivity improves decision-making by smoothing out choice's competitive edge": {
        "doi": "10.1038/s41562-024-02064-7", "journal": "Nature Human Behaviour", "year": 2025,
        "citation": "Leng, X., Frömer, R., Summe, T., et al. (2025). Mutual inclusivity improves decision-making by smoothing out choice's competitive edge. Nature Human Behaviour, 9, 521–533."},
    "Neural Representations of Food-Related Attributes in the Human Orbitofrontal Cortex during Choice Deliberation in Anorexia Nervosa": {
        "doi": "10.1523/JNEUROSCI.0958-21.2021", "journal": "Journal of Neuroscience", "year": 2021,
        "citation": "Xue, A. M., Foerde, K., Walsh, B. T., Steinglass, J. E., Shohamy, D., & Bakkour, A. (2022). Neural Representations of Food-Related Attributes in the Human Orbitofrontal Cortex during Choice Deliberation in Anorexia Nervosa. Journal of Neuroscience."},
    "Peripheral Visual Information Halves Attentional Choice Biases": {
        "doi": "10.1177/09567976231184878", "journal": "Psychological Science", "year": 2023,
        "citation": "Eum, B., Dolbier, S., & Rangel, A. (2023). Peripheral Visual Information Halves Attentional Choice Biases. Psychological Science, 34(9), 984–998."},
    "Sources of confidence in value-based choice": {
        "doi": "10.1038/s41467-021-27618-5", "journal": "Nature Communications", "year": 2021,
        "citation": "Brus, J., Aebersold, H., Grueschow, M., & Polania, R. (2021). Sources of confidence in value-based choice. Nature Communications, 12(1), 7337."},
    "Spacing of cue-approach training leads to better maintenance of behavioral change": {
        "doi": "10.1371/journal.pone.0201580", "journal": "PLOS ONE", "year": 2018,
        "citation": "Bakkour, A., Botvinik-Nezer, R., Cohen, N., Hover, A. M., Poldrack, R. A., & Schonberg, T. (2018). Spacing of cue-approach training leads to better maintenance of behavioral change. PLOS ONE, 13(7), e0201580."},
    "Subjective Evaluation of Food: A Japanese Database": {
        "doi": "10.31234/osf.io/ywt3k_v1", "journal": "PsyArXiv (preprint)", "year": 2025,
        "citation": "Toyama, A., Yamashita, Y., & Suzuki, S. (2025). Subjective Evaluation of Food: A Japanese Database. PsyArXiv."},
    "The Hungry Lens: Hunger Shifts Attention and Attribute Weighting in Dietary Choice": {
        "doi": "10.7554/eLife.103736.2", "journal": "eLife", "year": 2024,
        "citation": "March, J., & Gluth, S. (2024). The Hungry Lens: Hunger Shifts Attention and Attribute Weighting in Dietary Choice. eLife, 13:RP103736."},
    "The hippocampus supports deliberation during value-based decisions": {
        "doi": "10.7554/eLife.46080", "journal": "eLife", "year": 2019,
        "citation": "Bakkour, A., Palombo, D. J., Zylberberg, A., Kang, Y. H., Reid, A., Verfaellie, M., Shadlen, M. N., & Shohamy, D. (2019). The hippocampus supports deliberation during value-based decisions. eLife, 8."},
    "The spillover effects of attentional learning on value-based choice": {
        "doi": "10.1016/j.cognition.2018.10.012", "journal": "Cognition", "year": 2019,
        "citation": "Gwinn, R. E., Leber, A., & Krajbich, I. (2019). The spillover effects of attentional learning on value-based choice. Cognition, 182, 294–306."},
    "Uncovering the computational mechanisms underlying many-alternative choice": {
        "doi": "10.7554/elife.57012", "journal": "eLife", "year": 2021,
        "citation": "Thomas, A. W., Molter, F., & Krajbich, I. (2021). Uncovering the computational mechanisms underlying many-alternative choice. eLife, 10."},
    "Visual attention modulates the integration of goal-relevant evidence and not value": {
        "doi": "10.7554/eLife.60705", "journal": "eLife", "year": 2020,
        "citation": "Sepulveda, P., Usher, M., Davies, N., Benson, A. A., Ortoleva, P., & De Martino, B. (2020). Visual attention modulates the integration of goal-relevant evidence and not value. eLife, 9, e60705."},
}

# --- D/E/F/G. per-dataset scale corrections (dataset code -> min, max, type) --
# Types: likert (discrete steps), continuous, vas (visual analog), slider
# (fine-grained discrete slider), wtp (willingness-to-pay / auction).
# Verified against final_database.csv observed ranges + the papers' Table 1.
SCALES = {
    "bakbot_BM2":          (0, 3,    "wtp"),
    "bakbot_spacing_rep":  (0, 10,   "wtp"),
    "bakpol":              (0, 10,   "continuous"),
    "balim":               (1, 5,    "likert"),
    "brusaeb":             (0, 1,    "continuous"),
    "deskrab1":            (-10, 10, "likert"),
    "deskrab2":            (-10, 10, "continuous"),
    "deskrab4":            (-10, 10, "likert"),
    "eumdol":              (1, 5,    "likert"),
    "foljac2":             (0, 1,    "wtp"),
    "ganzou_1A":           (-100, 100, "slider"),
    "ganzou_1B":           (-100, 100, "slider"),
    "ganzou_1C":           (-100, 100, "slider"),
    "ganzou_2A_control":   (-100, 100, "slider"),
    "ganzou_2A_treatment": (-100, 100, "slider"),
    "ganzou_2B_control":   (-100, 100, "slider"),
    "ganzou_2C_control":   (-100, 100, "slider"),
    "ganzou_2C_treatment": (-100, 100, "slider"),
    "gwikrab":             (1, 10,   "likert"),
    "gwileb":              (-10, 10, "likert"),
    "hasdes":              (-1, 4,   "continuous"),
    "larlua":              (0, 100,  "vas"),
    "libain1":             (0, 100,  "slider"),
    "libain2":             (0, 100,  "slider"),
    "marglu":              (0, 100,  "vas"),
    "romfred":             (-10, 10, "continuous"),
    "sepush":              (0, 3,    "wtp"),
    "shenhav1b":           (0, 10,   "continuous"),
    "shenhav2":            (0, 10,   "continuous"),
    "shenhav3a":           (0, 10,   "continuous"),
    "shenhav3b":           (0, 10,   "continuous"),
    "shenhav4":            (0, 10,   "continuous"),
    "shenhav5a":           (0, 10,   "continuous"),
    "shenhav5b":           (0, 10,   "continuous"),
    "shenhav6":            (0, 10,   "continuous"),
    "shevsmith1":          (0, 10,   "vas"),
    "smikrab":             (-870, 870, "continuous"),
    "smikrab2018":         (-10, 10, "likert"),
    "sucro":               (0, 3,    "wtp"),
    "thomolt":             (-3, 3,   "likert"),
    "toyam":               (1, 8,    "likert"),
    "xuefoe":              (1, 5,    "likert"),
}

FOLJAC2_NOTE = (
    " NOTE: ratings are stored as the source provided them, normalized to 0-1;"
    " the original elicitation was willingness-to-pay on a 0-3 scale"
    " (Folke et al., 2016) and original units are not recoverable from the source CSV."
)

EXPECTED_TOTAL_RATINGS = 588_602
EXPECTED_ROMFRED = 27_108
EXPECTED_STUDIES = 24


def now():
    return datetime.utcnow().isoformat(sep=" ")


def code_of(dataset_name):
    return dataset_name.replace(" Dataset", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--csv", default="Liking Rating Database/final_database.csv")
    ap.add_argument("--apply", action="store_true", help="commit (default: dry-run + rollback)")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"no such db: {db_path}")

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = OFF")  # we repoint FKs manually and verify after
    cur = con.cursor()
    report = {}

    cur.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, name TEXT, applied_at TEXT, details TEXT)""")
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied to {db_path}")

    ts = now()

    # ---- A. consolidate duplicate studies -----------------------------------
    dup_groups = cur.execute("""
        SELECT name FROM studies GROUP BY name HAVING COUNT(*) > 1""").fetchall()
    merged = 0
    for (name,) in dup_groups:
        rows = cur.execute("""
            SELECT s.id, (SELECT COUNT(*) FROM datasets d WHERE d.study_id = s.id) AS nds
            FROM studies s WHERE s.name = ? ORDER BY nds DESC, s.id""", (name,)).fetchall()
        canonical = rows[0][0]
        for sid, _ in rows[1:]:
            cur.execute("UPDATE datasets SET study_id=? WHERE study_id=?", (canonical, sid))
            cur.execute("DELETE FROM studies WHERE id=?", (sid,))
            merged += 1
    report["duplicate_study_rows_merged"] = merged

    # ---- B. enrich studies with citation / DOI / journal / year -------------
    enriched, missing = 0, []
    for name, meta in CITATIONS.items():
        n = cur.execute("""UPDATE studies
            SET doi=?, journal=?, publication_title=?, year=?, updated_at=?
            WHERE name=?""",
            (meta["doi"], meta["journal"], meta["citation"], meta["year"], ts, name)).rowcount
        if n == 0:
            missing.append(name)
        enriched += n
    report["studies_enriched"] = enriched
    if missing:
        raise AssertionError(f"citation names not found in DB: {missing}")

    # ---- ids by dataset code -------------------------------------------------
    ds = {code_of(r[1]): r[0] for r in cur.execute("SELECT id, name FROM datasets")}

    # ---- E. deskrab2 clamp ----------------------------------------------------
    report["deskrab2_clamped"] = cur.execute(
        "UPDATE ratings SET rating=10.0 WHERE dataset_id=? AND rating>10.0",
        (ds["deskrab2"],)).rowcount

    # ---- C. romfred re-ingest -------------------------------------------------
    csv = pd.read_csv(args.csv)
    csv["code"] = csv["dataset_subjectid"].str.rsplit("_", n=1).str[0]
    csv["subj"] = csv["dataset_subjectid"].str.rsplit("_", n=1).str[1]
    rf = csv[(csv["code"] == "romfred")].dropna(subset=["item_name", "rating"])
    rf_mean = rf.groupby(["subj", "item_name"], as_index=False)["rating"].mean()
    assert len(rf_mean) == EXPECTED_ROMFRED, f"romfred pairs {len(rf_mean)} != {EXPECTED_ROMFRED}"
    assert rf_mean["rating"].between(-10, 10).all(), "romfred source outside -10..10"

    items = {r[1]: r[0] for r in cur.execute("SELECT id, name FROM items")}
    unresolved = set(rf_mean["item_name"]) - set(items)
    assert not unresolved, f"romfred items missing from items table: {sorted(unresolved)[:5]}"

    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (ds["romfred"],))
    rows = [
        (str(uuid.uuid4()), ds["romfred"], items[it], str(subj),
         float(r), (float(r) + 10.0) / 20.0, ts)
        for subj, it, r in rf_mean[["subj", "item_name", "rating"]].itertuples(index=False)
    ]
    cur.executemany("""INSERT INTO ratings
        (id, dataset_id, item_id, subject_id, rating, normalized_rating, created_at)
        VALUES (?,?,?,?,?,?,?)""", rows)
    report["romfred_reingested"] = len(rows)

    # ---- D/F/G. scale + type updates ------------------------------------------
    assert set(SCALES) == set(ds), f"scale map mismatch: {set(SCALES) ^ set(ds)}"
    for c, (lo, hi, typ) in SCALES.items():
        cur.execute("""UPDATE datasets SET rating_scale_min=?, rating_scale_max=?,
            rating_scale_type=?, updated_at=? WHERE id=?""", (lo, hi, typ, ts, ds[c]))
    cur.execute("""UPDATE datasets SET description = COALESCE(description,'') || ?
        WHERE id=? AND COALESCE(description,'') NOT LIKE '%not recoverable%'""",
        (FOLJAC2_NOTE, ds["foljac2"]))

    # ---- H. recompute normalized_rating everywhere -----------------------------
    for c, (lo, hi, _) in SCALES.items():
        span = hi - lo
        assert span > 0, f"zero span for {c}"
        cur.execute("""UPDATE ratings SET normalized_rating = (rating - ?) / ?
            WHERE dataset_id=?""", (float(lo), float(span), ds[c]))

    # ---- M. subject_id float-string cleanup (collision-guarded) ----------------
    fixed_subjects = 0
    for c, did in ds.items():
        bad = [r[0] for r in cur.execute(
            "SELECT DISTINCT subject_id FROM ratings WHERE dataset_id=? AND subject_id LIKE '%.0'",
            (did,))]
        if not bad:
            continue
        existing = {r[0] for r in cur.execute(
            "SELECT DISTINCT subject_id FROM ratings WHERE dataset_id=?", (did,))}
        for s in bad:
            target = s[:-2]
            if target in existing:
                continue  # collision — leave as-is
            cur.execute("UPDATE ratings SET subject_id=? WHERE dataset_id=? AND subject_id=?",
                        (target, did, s))
            fixed_subjects += 1
    report["float_subject_ids_normalized"] = fixed_subjects

    # ---- I/J. dataset counts + real completeness -------------------------------
    cur.execute("""UPDATE datasets SET
        n_subjects = (SELECT COUNT(DISTINCT subject_id) FROM ratings WHERE dataset_id=datasets.id),
        n_items    = (SELECT COUNT(DISTINCT item_id)    FROM ratings WHERE dataset_id=datasets.id)""")
    cur.execute("""UPDATE datasets SET data_completeness = ROUND(
        100.0 * (SELECT COUNT(*) FROM ratings r WHERE r.dataset_id=datasets.id)
        / (n_subjects * n_items), 2)""")

    # ---- K. items.frequency ------------------------------------------------------
    cur.execute("""UPDATE items SET frequency = COALESCE(
        (SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id=items.id), 0)""")

    # ---- L. created_at backfill ---------------------------------------------------
    report["created_at_backfilled"] = cur.execute(
        "UPDATE ratings SET created_at=? WHERE created_at IS NULL", (ts,)).rowcount

    # ---- assertions -----------------------------------------------------------------
    a = {}
    a["studies"] = cur.execute("SELECT COUNT(*) FROM studies").fetchone()[0]
    assert a["studies"] == EXPECTED_STUDIES, f"studies {a['studies']} != {EXPECTED_STUDIES}"
    assert cur.execute("SELECT COUNT(*) FROM (SELECT name FROM studies GROUP BY name HAVING COUNT(*)>1)").fetchone()[0] == 0
    assert cur.execute("""SELECT COUNT(*) FROM studies s
        WHERE NOT EXISTS (SELECT 1 FROM datasets d WHERE d.study_id=s.id)""").fetchone()[0] == 0, "orphan study"
    assert cur.execute("""SELECT COUNT(*) FROM datasets d
        LEFT JOIN studies s ON s.id=d.study_id WHERE s.id IS NULL""").fetchone()[0] == 0, "orphan dataset"

    a["total_ratings"] = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    assert a["total_ratings"] == EXPECTED_TOTAL_RATINGS, f"total {a['total_ratings']} != {EXPECTED_TOTAL_RATINGS}"

    bad_range = cur.execute("""SELECT COUNT(*) FROM ratings r JOIN datasets d ON d.id=r.dataset_id
        WHERE r.rating < d.rating_scale_min - 1e-9 OR r.rating > d.rating_scale_max + 1e-9""").fetchone()[0]
    assert bad_range == 0, f"{bad_range} ratings outside declared scale"
    bad_norm = cur.execute(
        "SELECT COUNT(*) FROM ratings WHERE normalized_rating < -1e-9 OR normalized_rating > 1+1e-9").fetchone()[0]
    assert bad_norm == 0, f"{bad_norm} normalized ratings outside 0..1"

    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE created_at IS NULL").fetchone()[0] == 0
    assert cur.execute("SELECT COUNT(*) FROM studies WHERE doi IS NOT NULL").fetchone()[0] == 23
    a["completeness_range"] = cur.execute(
        "SELECT MIN(data_completeness), MAX(data_completeness) FROM datasets").fetchone()
    assert 0 < a["completeness_range"][0] <= a["completeness_range"][1] <= 100.0001
    a["scale_types"] = [r[0] for r in cur.execute(
        "SELECT DISTINCT rating_scale_type FROM datasets ORDER BY 1")]
    assert set(a["scale_types"]) <= {"likert", "continuous", "vas", "slider", "wtp"}
    report["assertions"] = a

    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))

    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {db_path}")
    else:
        con.rollback()
        print(f"\nDRY-RUN ok (rolled back) — rerun with --apply to commit to {db_path}")
    con.close()


if __name__ == "__main__":
    main()
