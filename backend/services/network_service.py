"""
Per-dataset preference networks, estimated offline with bootEGA.

Within a single dataset every item co-occurs with every other, so the
co-occurrence network used across the database says nothing here. What does
carry structure is how the ratings themselves relate: items sit close when
the same people rated them alike.

Those networks are fitted in R (EGAnet's bootEGA) by
``scripts/estimate_networks.R`` and read from disk here. Bootstrapping a
graphical model several hundred times is seconds of compute per dataset —
not something to run per page view, and not something to ask a visitor's
browser for.

Each file also records how its items were chosen, because that restriction is
part of what the figure means: a graphical model over items needs more
subjects than items, and most datasets here have the opposite.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# Committed alongside the database so a deployment needs no build step; the
# environment variable exists so a local estimation run can be pointed at.
NETWORK_DIR = Path(
    os.environ.get("LIKING_NETWORK_DIR", REPO_ROOT / "data-release" / "networks")
)


class NetworkService:
    """Serves the precomputed per-dataset networks."""

    _cache: Dict[str, Dict[str, Any]] = {}
    _index: Optional[List[Dict[str, Any]]] = None

    def _path(self, code: str) -> Path:
        # Codes come from dataset names and are used as filenames; keep them
        # to a safe shape rather than trusting the caller.
        safe = "".join(c for c in code if c.isalnum() or c in "_-")
        return NETWORK_DIR / f"{safe}.json"

    def available(self) -> List[Dict[str, Any]]:
        """Which datasets have a network, and for those that don't, why not."""
        if self._index is not None:
            return self._index
        rows: List[Dict[str, Any]] = []
        if NETWORK_DIR.exists():
            for path in sorted(NETWORK_DIR.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                rows.append({
                    "dataset_code": data.get("dataset_code", path.stem),
                    "estimated": bool(data.get("estimated")),
                    "reason": data.get("reason"),
                    "n_dimensions": data.get("n_dimensions"),
                    "items_estimated": (data.get("selection") or {}).get("items_estimated"),
                })
        self._index = rows
        return rows

    def get(self, code: str) -> Optional[Dict[str, Any]]:
        """One dataset's network, or None if no file exists for it."""
        if code in self._cache:
            return self._cache[code]
        path = self._path(code)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        self._cache[code] = data
        return data


network_service = NetworkService()
