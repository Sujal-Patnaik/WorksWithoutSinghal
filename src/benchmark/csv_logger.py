import csv
import os
from typing import Dict, Optional


class IterationCSVLogger:
    """Writes per-iteration ALNS metrics for reproducible analysis."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self._fh = open(output_path, "w", newline="", encoding="utf-8")
        self._writer: Optional[csv.DictWriter] = None

    def log(self, row: Dict[str, object]) -> None:
        if self._writer is None:
            fieldnames = list(row.keys())
            self._writer = csv.DictWriter(self._fh, fieldnames=fieldnames)
            self._writer.writeheader()
        self._writer.writerow(row)

    def close(self) -> None:
        if self._fh and not self._fh.closed:
            self._fh.close()
