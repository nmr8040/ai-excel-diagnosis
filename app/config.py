import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

if os.getenv("RENDER"):
    _default_db = "sqlite:////tmp/excel_diagnosis.db"
    _default_upload = "/tmp/uploads"
else:
    _default_db = f"sqlite:///{BASE_DIR / 'data/db/excel_diagnosis.db'}"
    _default_upload = str(BASE_DIR / "data/uploads")

DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", _default_upload))
AI_PROVIDER = os.getenv("AI_PROVIDER", "dummy")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data/db").mkdir(parents=True, exist_ok=True)
