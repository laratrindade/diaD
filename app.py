import base64
import os
import random
from pathlib import Path

import streamlit as st

APP_ROOT = Path(__file__).resolve().parent
DEFAULT_MEDIA_DIR = (APP_ROOT / "media").resolve()
MEDIA_DIR = Path(os.environ.get("MEDIA_DIR", str(DEFAULT_MEDIA_DIR))).expanduser().resolve()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}
ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS


st.set_page_config(page_title="Dia do Pai", layout="wide")


st.markdown(
    """
    <style>
      :root {
        --bg: #f7f1e7;
        --ink: #1f1a12;
        --accent: #c46a4a;
        --muted: #6d5e50;
      }
      .stApp {
        background: radial-gradient(circle at 20% 20%, #fff7ef 0%, #f7f1e7 45%, #efe6d8 100%);
        color: var(--ink);
      }
      header, [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
      }
      .stApp > header {
        display: none !important;
      }
      .block-container {
        padding-top: 1rem !important;
      }
      .hero {
        min-height: 68vh;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
      }
      .hero h1 {
        font-family: "Playfair Display", "Times New Roman", serif;
        font-size: clamp(2.6rem, 6vw, 4.4rem);
        letter-spacing: 0.06em;
        margin: 0;
        color: var(--ink);
      }
      .hero .date {
        margin-top: 0.6rem;
        font-size: clamp(1rem, 2vw, 1.4rem);
        letter-spacing: 0.24em;
        color: var(--muted);
        text-transform: uppercase;
      }
      .stage-box {
        margin: 2.5rem auto 0;
        max-width: 1100px;
        min-height: 70vh;
        background: #f7f2eb;
        border-radius: 28px;
        box-shadow: 0 26px 60px rgba(60, 41, 26, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.8);
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .center-card {
        position: absolute;
        inset: 50% auto auto 50%;
        transform: translate(-50%, -50%);
        background: #fbf6f1;
        padding: 1.6rem 2.2rem;
        border-radius: 18px;
        box-shadow: 0 18px 40px rgba(60, 41, 26, 0.2);
        border: 1px solid rgba(196, 106, 74, 0.2);
        text-align: center;
        z-index: 2;
      }
      .center-card h1 {
        font-family: "Playfair Display", "Times New Roman", serif;
        font-size: clamp(1.8rem, 4vw, 2.6rem);
        margin: 0;
      }
      .center-card .date {
        margin-top: 0.4rem;
        font-size: 0.95rem;
        letter-spacing: 0.2em;
        color: var(--muted);
        text-transform: uppercase;
      }
      .center-card .subtitle {
        margin-top: 0.6rem;
        font-size: 0.95rem;
        color: var(--muted);
      }
      .media-box {
        max-width: 1280px;
        min-height: 78vh;
        margin: 2.5rem auto 0;
        background: #f7f2eb;
        border-radius: 28px;
        box-shadow: 0 26px 60px rgba(60, 41, 26, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
      }
      .media-box img,
      .media-box video {
        max-width: 82%;
        max-height: 70%;
        width: auto;
        height: auto;
        object-fit: contain;
        display: block;
      }
      .footer-upload {
        margin-top: 3rem;
        display: flex;
        justify-content: center;
      }
      .footer-upload .stFileUploader {
        width: min(720px, 92vw);
        padding: 18px 20px;
        border-radius: 18px;
        border: 1px dashed rgba(196, 106, 74, 0.35);
        background: rgba(255, 255, 255, 0.7);
      }
      button[kind="primary"] {
        background: var(--accent) !important;
        border: none !important;
      }
      .controls {
        margin: 0.8rem auto 0;
        display: flex;
        justify-content: center;
        gap: 0.8rem;
      }
      .controls button[kind="primary"] {
        border-radius: 999px !important;
        padding: 0.5rem 1.4rem !important;
        font-weight: 600 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


if not MEDIA_DIR.exists():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data(show_spinner=False)
def list_media(media_dir: Path):
    files = []
    if not media_dir.exists() or not media_dir.is_dir():
        return files

    for path in media_dir.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in ALL_EXTS:
            files.append(path)

    return files


def pick_random(files):
    if not files:
        return None
    return random.choice(files)


def save_uploads(uploaded_files, media_dir: Path):
    saved = []
    for file in uploaded_files:
        original_name = Path(file.name).name
        ext = Path(original_name).suffix.lower()
        if ext not in ALL_EXTS:
            continue

        target = media_dir / original_name
        if target.exists():
            stem = Path(original_name).stem
            for idx in range(1, 1000):
                candidate = media_dir / f"{stem}_{idx}{ext}"
                if not candidate.exists():
                    target = candidate
                    break

        with target.open("wb") as handle:
            handle.write(file.getbuffer())
        saved.append(target)

    return saved


files = list_media(MEDIA_DIR)

if not files:
    st.info("Ainda nao ha midias na pasta. Envie fotos ou videos para comecar.")
    st.markdown("<div class='footer-upload'>", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Enviar fotos e videos",
        type=[ext.lstrip(".") for ext in sorted(ALL_EXTS)],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if uploaded:
        saved_files = save_uploads(uploaded, MEDIA_DIR)
        if saved_files:
            st.success(f"Guardado: {len(saved_files)} arquivo(s)")
            list_media.clear()
        else:
            st.warning("Nenhum arquivo suportado foi enviado.")
    st.stop()

if "current" not in st.session_state:
    st.session_state.current = pick_random(files)
if "playing" not in st.session_state:
    st.session_state.playing = False


def start_play():
    st.session_state.playing = True


def next_media():
    st.session_state.playing = True
    st.session_state.current = pick_random(files)


def _media_data_url(path: Path) -> str:
    ext = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
        ".m4v": "video/x-m4v",
    }
    mime = mime_map.get(ext, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"

current = st.session_state.current

if current is None or not current.exists():
    st.session_state.current = pick_random(files)
    current = st.session_state.current
    if current is None:
        st.info("Sem midias disponiveis.")
        st.stop()

ext = current.suffix.lower()

if st.session_state.playing:
    media_url = _media_data_url(current)
    if ext in IMAGE_EXTS:
        inner = f'<img src="{media_url}" alt="media">'
    else:
        inner = (
            f'<video src="{media_url}" controls playsinline></video>'
        )
else:
    inner = (
        '<div class="center-card">'
        "<h1>Dia do Pai</h1>"
        '<div class="date">19/03/2026</div>'
        '<div class="subtitle">Memorias que passam ao acaso</div>'
        "</div>"
    )

st.markdown(f'<div class="media-box">{inner}</div>', unsafe_allow_html=True)

st.markdown("<div class='controls'>", unsafe_allow_html=True)
col_a, col_b = st.columns([1, 1])
with col_a:
    st.button("Reproduzir", type="primary", on_click=start_play)
with col_b:
    st.button("Proximo", type="primary", on_click=next_media)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='footer-upload'>", unsafe_allow_html=True)
uploaded = st.file_uploader(
    "Enviar fotos e videos",
    type=[ext.lstrip(".") for ext in sorted(ALL_EXTS)],
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown("</div>", unsafe_allow_html=True)
if uploaded:
    saved_files = save_uploads(uploaded, MEDIA_DIR)
    if saved_files:
        st.success(f"Guardado: {len(saved_files)} arquivo(s)")
        list_media.clear()
    else:
        st.warning("Nenhum arquivo suportado foi enviado.")
