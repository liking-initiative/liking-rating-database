"""Citations for the database and for the studies it draws on."""
from __future__ import annotations

from typing import Any, Optional

DATABASE_CITATION = (
    "Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective "
    "evaluation ratings for decision-making research. (In preparation.)"
)


def _entry(x: Any) -> Optional[dict]:
    """Accept a Dataset/Item object or a raw catalogue dict."""
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    return getattr(x, "metadata", None)


def cite(x: Any = None) -> str:
    """Citation text for a dataset, or for the database itself.

    Please cite both: the database, and the study whose data you used.
    """
    entry = _entry(x)
    if entry is None:
        return DATABASE_CITATION

    citation = entry.get("citation") or entry.get("study_name") or ""
    doi = entry.get("paper_doi")
    if doi:
        citation = f"{citation} https://doi.org/{doi}"
    return f"{citation}\n\nPlease also cite the database:\n{DATABASE_CITATION}"


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
