"""Citations for the database and for the studies it draws on."""
from __future__ import annotations

from typing import Any, Optional

# The concept DOI, which Zenodo resolves to the newest version. Cite this to
# mean "the database"; cite the version DOI that release_info() reports when an
# analysis needs to name the exact bytes it ran on.
DATABASE_DOI = "10.5281/zenodo.22216442"

DATABASE_CITATION = (
    "Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a "
    "database of subjective evaluation ratings for decision-making research "
    "[Data set]. Zenodo. https://doi.org/" + DATABASE_DOI
)


def _entry(x: Any) -> Optional[dict]:
    """Accept a Dataset/Item object or a raw catalogue dict."""
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    return getattr(x, "metadata", None)


def cite(x: Any = None) -> str:
    """Citation for a dataset's source publication.

    Returns only that study's citation. Appending the database's every time
    would be noise in a loop over datasets -- call ``cite()`` with no argument
    for the database's own citation, and please include it alongside whichever
    studies you use.
    """
    entry = _entry(x)
    if entry is None:
        return DATABASE_CITATION

    citation = entry.get("citation") or entry.get("study_name") or ""
    doi = entry.get("paper_doi")
    if doi:
        citation = f"{citation} https://doi.org/{doi}"
    return citation


def bibtex(x: Any) -> str:
    """A BibTeX entry for a dataset's source publication."""
    entry = _entry(x)
    if entry is None:
        raise ValueError("bibtex() needs a dataset or item")

    authors = " and ".join(
        a.strip() for a in (entry.get("authors") or "").split(";") if a.strip()
    )
    year = entry.get("year") or ""
    first = (entry.get("first_author") or "study").lower().replace(" ", "")
    fields = [
        f"  author  = {{{authors}}}",
        f"  title   = {{{entry.get('study_name', '')}}}",
        f"  year    = {{{year}}}",
    ]
    if entry.get("journal"):
        fields.append(f"  journal = {{{entry['journal']}}}")
    if entry.get("paper_doi"):
        fields.append(f"  doi     = {{{entry['paper_doi']}}}")
    return "@article{" + f"{first}{year}" + ",\n" + ",\n".join(fields) + "\n}"
