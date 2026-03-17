import os
import random
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory, abort

APP_ROOT = Path(__file__).resolve().parent
# Pasta fixa de media para a fase 1 (dentro do projeto)
MEDIA_DIR = (APP_ROOT / "media").resolve()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}

app = Flask(__name__)


def _iter_media():
    if not MEDIA_DIR.exists() or not MEDIA_DIR.is_dir():
        return []

    files = []
    for path in MEDIA_DIR.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
            rel = path.relative_to(MEDIA_DIR)
            files.append(rel.as_posix())

    return files


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/media_list")
def media_list():
    files = _iter_media()
    random.shuffle(files)
    items = []
    for rel in files:
        ext = Path(rel).suffix.lower()
        items.append({
            "url": f"/media/{rel}",
            "type": "video" if ext in VIDEO_EXTS else "image",
        })
    return jsonify({"items": items})


@app.route("/media/<path:filename>")
def media(filename):
    file_path = (MEDIA_DIR / filename).resolve()
    if not str(file_path).startswith(str(MEDIA_DIR)):
        abort(404)
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    return send_from_directory(MEDIA_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Avoid the reloader in hosted environments where signals are restricted.
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
