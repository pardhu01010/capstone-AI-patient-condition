from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class CaseStore:
    """Simple JSON-backed persistence layer for prototype purposes."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._cases: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._cases = {}
            return
        try:
            with self.storage_path.open("r", encoding="utf-8") as infile:
                self._cases = json.load(infile)
        except json.JSONDecodeError:
            # Corrupted file – fall back to in-memory store.
            self._cases = {}

    def _persist(self) -> None:
        tmp_path = self.storage_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as outfile:
            json.dump(self._cases, outfile, indent=2)
        tmp_path.replace(self.storage_path)

    def add_case(self, case: Dict) -> None:
        self._cases[case["case_id"]] = case
        self._persist()

    def list_cases(self) -> List[Dict]:
        return sorted(
            self._cases.values(),
            key=lambda case: case.get("created_at", ""),
            reverse=True,
        )

    def get_case(self, case_id: str) -> Optional[Dict]:
        return self._cases.get(case_id)

