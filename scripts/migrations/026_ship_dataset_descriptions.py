#!/usr/bin/env python
"""
Migration 026 -- give every dataset a description, so its caveats travel
with the data.

The scale-and-construct verification (docs/SCALE_VERIFICATION.md) established
what each dataset measures and how it is scored, and turned up caveats that
change how the numbers should be read: two datasets measure tastiness rather
than liking, three are missing ratings non-randomly, several hold means rather
than single responses, and several come from one experiment of a paper that
ran more than one.

None of that shipped. It lived in a repository document that is not part of a
release, and in codebook prose that describes the corpus rather than any
particular dataset. `catalog.json` already carries a per-dataset
`description` field, and 31 of 55 datasets left it empty -- including every
one of the datasets whose caveat matters most. Someone loading `larlua`
programmatically got no signal that it is tastiness, which is the same failure
that made shipping the healthiness datasets unacceptable.

The wording here is restricted to what verification established: a construct
named by the paper, a scale quoted from it, or a fact about the stored values
that can be checked against the data.

Usage:
    python scripts/migrations/026_ship_dataset_descriptions.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "026"
NAME = "ship_dataset_descriptions"

SHENHAV = (
    "Liking for consumer products, rated on an analogue scale: participants "
    "\"were instructed to rate how much they would like to have each one, by "
    "clicking on an analog liking scale from 0 (not at all) to 10 (a lot)\". "
    "Part of a multi-experiment paper; this is experiment {exp}."
)

D = {
 "bakbot_BM2":
   "Willingness-to-pay for 60 snack foods, elicited in an incentive-compatible BDM "
   "auction: participants \"indicated their willingness-to-pay (WTP) for each "
   "individual item by selecting a value on a visual analog scale\", bidding against "
   "a computer counter-bid drawn as \"a random number between 0 and 3 in 25 cent "
   "increments\". Samples 1-3 of the paper's four.",
 "bakbot_spacing_rep":
   "Willingness-to-pay for 60 snack foods in the same $0-3 BDM auction as "
   "bakbot_BM2; sample 4 of the paper's four. NOTE: the authors' source file stores "
   "this sample's bids on a 0-10 range rather than in dollars. The raw values here "
   "have been divided by 10/3 to put them in the dollars the paper reports, which "
   "makes them comparable with bakbot_BM2; normalized_rating is unaffected either "
   "way. The rescaling is supported by the slider step ratio being exactly 10/3 and "
   "by rescaled item means matching bakbot_BM2's on shared stimuli (r = 0.98).",
 "bakpol":
   "Preference for 30 food items, rated 0-10: participants were \"instructed to rate "
   "how much they prefer to eat the food item on the screen from 0 (prefer least to "
   "eat) to 10 (prefer most to eat)\". From the patient experiment of a paper whose "
   "other experiment used a $0-3 BDM auction instead.",
 "balim":
   "Liking for 60 foods on a five-point scale (strongly dislike, dislike, neutral, "
   "like, strongly like). The source file also holds tastiness and healthiness "
   "ratings for the same foods, and liking ratings for a separate set of physical "
   "activities; only food liking is held here.",
 "deskrab1":
   "Desire to eat 144 snack foods, rated on a -10..10 slider: \"-10 corresponded to "
   "really not wanting to eat the food at the end of the study, 10 corresponded to "
   "really wanting to eat the food ... and 0 corresponded to being indifferent\". "
   "From Experiment 2 of the paper. Experiment 1, which rated 101 foods on a 0-10 "
   "scale with a separate dislike option, is not held in this database.",
 "deskrab2":
   "Desire to eat 144 snack foods on the same -10..10 slider as deskrab1, from "
   "another condition of the paper's Experiment 2. Responses here are continuous "
   "rather than integer-valued.",
 "deskrab4":
   "Desire to eat 144 snack foods on the same -10..10 slider as deskrab1, from "
   "another condition of the paper's Experiment 2.",
 "eumdol":
   "Liking for 60 snack foods: \"How much would you LIKE to eat this food?\", 1 = "
   "\"don't like\" to 5 = \"like a lot\", in 0.25 intervals on a slider. NOTE: each "
   "item was rated twice and the stored value is the average of the two, as in the "
   "paper's own analysis.",
 "gwikrab":
   "Liking for food items: participants completed \"a rating task, rating from 1 to "
   "10 how much they would like to eat the displayed food item (1 being 'not at all' "
   "and 10 being 'would love to')\".",
 "gwileb":
   "Liking for snack foods on \"a rating scale from -10 to +10 in increments of "
   "one\", where \"-10\" indicated the item was very disliked and \"+10\" very "
   "liked. From the paper's Experiment 2, which \"expanded the number of food items "
   "to 147\"; Experiment 1 used 91 items and is not held here.",
 "hasdes":
   "Liking for 144 snack foods: \"You will rate each food on a scale from 0 to 4. 4 "
   "means you would really like to eat the food. 0 means you would neither like nor "
   "dislike to eat the food.\" NOTE: the task also offered a \"Would Not Eat\" "
   "button, and those responses are stored here as -1, which is why the declared "
   "scale is -1..4 rather than the paper's 0..4. 586 of 3,168 ratings (18.5%) are "
   "that button. Placing it below 0 preserves the ordering but asserts a spacing the "
   "study never defined.",
 "larlua":
   "IMPORTANT: this dataset measures TASTINESS, not liking. Participants \"rated "
   "them (in the same order) for healthiness and tastiness using a VAS scale from 0 "
   "to 100\", and the tastiness ratings are what is held here. All 86 item names are "
   "opaque source codes with no readable labels, so the dataset supports no "
   "item-level comparison with the rest of the database.",
 "libain1":
   "Preference for 138 food images: participants \"were asked to rate all 138 food "
   "stimuli on a scale from 0 to 10 for how much they would prefer to eat that food "
   "today\". NOTE: the source file stored these on 0-100, ten times the scale the "
   "paper reports; raw values here have been divided by 10 to match the paper. "
   "normalized_rating is unaffected.",
 "libain2":
   "Preference for 138 food items on the same 0-10 scale as libain1, differing only "
   "in that each image was replaced by the word or words for the food. The same "
   "rescaling from the source file's 0-100 applies.",
 "marglu":
   "Wanting for 66 food images: \"How much would you like to eat this item at the "
   "end of the experiment? Not at all - very much\", recorded by moving a slider. "
   "The source study also collected tastiness, healthiness and perceived caloric "
   "content for the same images; only wanting is held here. NOTE: the paper "
   "describes the response as a continuous slider but never states its numeric "
   "endpoints, so the declared 0..100 comes from the source data rather than the "
   "publication.",
 "sepush":
   "Willingness-to-pay for 60 snack food items: participants \"were asked to report "
   "on a scale from GBP 0 to GBP 3 the maximum they would be willing to pay\" in a "
   "BDM procedure. Values are in pounds, not dollars.",
 "shevsmith1":
   "Desire to consume 144 snack foods: participants rated \"their desire to consume "
   "each of 144 snack foods on a continuous scale from 0 to 10\", where 0 means "
   "neither liking nor disliking and 10 really liking the food. IMPORTANT: the task "
   "also offered a \"Would Not Eat\" button and those responses are absent from this "
   "data -- 5,311 ratings are held against 6,336 subject-item cells, so roughly 16% "
   "are missing and they are systematically each participant's most-disliked foods. "
   "Per-item means computed from this dataset are biased upward.",
 "smikrab":
   "Food-liking for 100 food images -- \"how much they wanted to eat the food\" -- "
   "recorded by clicking on \"a rating scale (1,740 pixels long)\", which is what the "
   "-870..870 range encodes: pixel offsets from the scale's midpoint. The source "
   "study collected four ratings per item (food-liking, image size, weight, and "
   "liking of the package); only food-liking is held here.",
 "smikrab2018":
   "Desire to eat 147 snack food items \"on a discrete scale from -10 to 10\", where "
   "-10 indicates extreme dislike, 10 extreme liking, and 0 neither.",
 "sucro":
   "Willingness-to-pay for 56 food items in a BDM auction: \"a participant was "
   "endowed with $3 and made a bid, $0, $1, $2 or $3\". NOTE: the paper allows only "
   "those four whole-dollar bids, but the values here fall on half-dollar steps "
   "because they are means of two bids per item -- 82% land on integers and 18% on "
   "halves, the signature of averaging two responses that usually agree.",
 "thomolt":
   "Liking for 80 snack foods: subjects indicated \"how much they would like to eat "
   "the item at the end of the experiment\" on \"a 7-point rating scale, ranging from "
   "-3 (not at all) to 3 (very much), with 0 denoting indifference\".",
 "toyam":
   "Likability for food images: participants rated them \"in terms of likability "
   "('Do you like the food?') ... on an eight-point Likert scale ranging from 1 "
   "(strongly disagree) to 8 (strongly agree)\". The source study also collected "
   "tastiness (\"Is the food tasty?\") and healthiness (\"Is the food healthy?\") for "
   "the same images; only likability is held here. Values are per-subject means "
   "where the source carried unstructured repeats.",
 "xuefoe":
   "IMPORTANT: this dataset measures TASTINESS, not liking. Participants \"were "
   "asked to rate the tastiness of 76 food items on a 5-point Likert scale from bad "
   "to neutral to good\" and \"were instructed to rate the food items only on "
   "taste\"; the scale direction was counterbalanced across participants. The source "
   "study also collected healthiness ratings, which are not held here.",
}
for exp, codes in {"1b": ["shenhav1b"], "2": ["shenhav2"], "3a": ["shenhav3a"],
                   "3b": ["shenhav3b"], "4": ["shenhav4"], "5a": ["shenhav5a"],
                   "5b": ["shenhav5b"], "6": ["shenhav6"]}.items():
    for c in codes:
        D[c] = SHENHAV.format(exp=exp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    ts = datetime.utcnow().isoformat(sep=" ")
    written = []
    for code, text in sorted(D.items()):
        row = cur.execute(
            "SELECT id, description FROM datasets WHERE name LIKE ?", (code + " %",)).fetchone()
        assert row, f"{code} not found"
        did, existing = row
        # Only fill blanks. A description written at ingest is not overwritten here.
        assert not (existing or "").strip(), f"{code} already has a description"
        cur.execute("UPDATE datasets SET description=?, updated_at=? WHERE id=?",
                    (" ".join(text.split()), ts, did))
        written.append(code)

    blank = [r[0] for r in cur.execute(
        "SELECT replace(name,' Dataset','') FROM datasets "
        "WHERE description IS NULL OR TRIM(description)=''")]
    assert not blank, f"still blank after migration: {blank}"

    n = cur.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    assert len(written) + (n - len(written)) == n

    report = {
        "descriptions_written": len(written),
        "datasets": written,
        "datasets_total": n,
        "blank_remaining": 0,
        "reason": ("per-dataset caveats established by the scale-and-construct "
                   "verification were not shipping: catalog.json carries a "
                   "description field and 31 of 55 datasets left it empty, "
                   "including every dataset measuring a construct other than "
                   "liking and every dataset missing ratings non-randomly"),
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps({k: v for k, v in report.items() if k != "datasets"}, indent=2))
    print(f"  wrote: {', '.join(written)}")

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
