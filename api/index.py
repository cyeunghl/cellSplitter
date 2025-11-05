from pathlib import Path
from flask import Flask

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(
    __name__,
    static_folder=str(PUBLIC_DIR),
    static_url_path=""
)
