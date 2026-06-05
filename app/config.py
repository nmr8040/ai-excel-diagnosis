import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data/db/excel_diagnosis.db'}")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "data/uploads"))
AI_PROVIDER = os.getenv("AI_PROVIDER", "dummy")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data/db").mkdir(parents=True, exist_ok=True)
