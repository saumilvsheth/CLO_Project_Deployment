from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
PDF_DIR = DATA / "pdfs"
RUNS_DIR = DATA / "runs"
REVIEWS_PATH = DATA / "reviews.json"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()
