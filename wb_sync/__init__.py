from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
__path__ = [str(_ROOT / "src" / "wb_sync")]
