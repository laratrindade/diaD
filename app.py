import json
import mimetypes
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth.transport.requests

APP_ROOT = Path(__file__).resolve().parent
MEDIA_DIR = (APP_ROOT / "media").resolve()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}
GDRIVE_MIME_IMAGE_PREFIX = "image/"
GDRIVE_MIME_VIDEO_PREFIX = "video/"
GDRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_CACHE_TTL_SECONDS = 21600


def _is_debug_media():
    if "debug_media" in st.secrets:
        val = st.secrets["debug_media"]
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
        return bool(val)
    return os.environ.get("DEBUG_MEDIA", "").strip().lower() in {"1", "true", "yes", "on"}


st.set_page_config(page_title="Dia do Pai", layout="wide")

st.markdown(
    """
<style>
#MainMenu, footer, header {visibility: hidden;}
html, body, .stApp {height: 100%;}
div[data-testid="stAppViewContainer"] > .main {padding: 0;}
div[data-testid="stAppViewContainer"] .block-container {padding-top: 0; padding-bottom: 0;}
div[data-testid="stAppViewContainer"] {background: radial-gradient(circle at top, #fff8ef 0%, #f6f2ea 50%, #e9e1d6 100%);}
div[data-testid="stStatusWidget"] {display: none !important;}
div[data-testid="stToolbar"] {display: none !important;}
div[data-testid="stDecoration"] {display: none !important;}
div[class*="StatusWidget"] {display: none !important;}
header[data-testid="stHeader"] {display: none !important;}
div[class*="decoration"] {display: none !important;}
div.stSkeleton {display: none !important;}
[class*="stSkeleton"] {display: none !important;}
</style>
""",
    unsafe_allow_html=True,
)


def _get_credentials():
    creds_info = None
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
    elif os.environ.get("GCP_SERVICE_ACCOUNT_JSON"):
        creds_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_JSON"])
    if not creds_info:
        raise RuntimeError("Credenciais do Google Drive não encontradas.")
    if "\\n" in str(creds_info.get("private_key", "")):
        creds_info["private_key"] = str(creds_info["private_key"]).replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return creds


def _get_drive_service(creds):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_access_token(creds):
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


def _get_drive_folder_id():
    if "gdrive_folder_id" in st.secrets:
        raw = str(st.secrets["gdrive_folder_id"]).strip()
    else:
        raw = os.environ.get("GDRIVE_FOLDER_ID")
    return _normalize_drive_id(raw)


def _get_shared_drive_id():
    if "gdrive_shared_drive_id" in st.secrets:
        raw = str(st.secrets["gdrive_shared_drive_id"]).strip()
    else:
        raw = os.environ.get("GDRIVE_SHARED_DRIVE_ID")
    return _normalize_drive_id(raw)


def _normalize_drive_id(value):
    if not value:
        return None
    v = value.strip()
    if "drive.google.com" in v:
        if "/folders/" in v:
            v = v.split("/folders/", 1)[1]
        if "/drive/folders/" in v:
            v = v.split("/drive/folders/", 1)[1]
    if "?" in v:
        v = v.split("?", 1)[0]
    return v or None


def _iter_drive_files(service, folder_id, shared_drive_id=None):
    stack = [folder_id]
    while stack:
        current = stack.pop()
        query = f"'{current}' in parents and trashed = false"
        page_token = None
        while True:
            list_kwargs = {
                "q": query,
                "fields": "nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                "pageToken": page_token,
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
                "orderBy": "name",
            }
            if shared_drive_id:
                list_kwargs.update({
                    "corpora": "drive",
                    "driveId": shared_drive_id,
                })
            resp = service.files().list(**list_kwargs).execute()
            for f in resp.get("files", []):
                if f.get("mimeType") == GDRIVE_FOLDER_MIME:
                    stack.append(f["id"])
                else:
                    yield f
            page_token = resp.get("nextPageToken")
            if not page_token:
                break


@st.cache_data(show_spinner=False, ttl=DEFAULT_CACHE_TTL_SECONDS)
def _load_metadata(folder_id, shared_drive_id):
    """Apenas carrega metadados — muito rápido."""
    creds = _get_credentials()
    service = _get_drive_service(creds)
    items = []
    for f in _iter_drive_files(service, folder_id, shared_drive_id=shared_drive_id):
        mime = f.get("mimeType") or ""
        if not (mime.startswith(GDRIVE_MIME_IMAGE_PREFIX) or mime.startswith(GDRIVE_MIME_VIDEO_PREFIX)):
            ext = Path(f.get("name", "")).suffix.lower()
            if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
                continue
            if not mime:
                mime, _ = mimetypes.guess_type(f.get("name", ""))
        if not mime:
            continue
        items.append({
            "id": f["id"],
            "name": f.get("name", ""),
            "mime": mime,
            "type": "video" if mime.startswith(GDRIVE_MIME_VIDEO_PREFIX) else "image",
        })
    return items


# --- Carrega apenas metadados (muito rápido) ---
_load_error = None
folder_id = _get_drive_folder_id()
shared_drive_id = _get_shared_drive_id()
items = []
access_token = ""

if folder_id:
    try:
        items = _load_metadata(folder_id, shared_drive_id)
        # Gera token de acesso para o JavaScript usar
        creds = _get_credentials()
        access_token = _get_access_token(creds)
    except Exception as exc:
        _load_error = exc
        st.error(f"Erro ao carregar metadados do Google Drive: {exc}")

items_json = json.dumps(items)
access_token_json = json.dumps(access_token)
debug_enabled = _is_debug_media()
debug_flag_json = "true" if debug_enabled else "false"

if debug_enabled:
    with st.expander("Debug media", expanded=True):
        st.write(f"Folder ID: {folder_id}")
        st.write(f"Itens encontrados: {len(items)}")
        if _load_error:
            st.write(f"Erro: {_load_error}")
        for i in items[:5]:
            st.write(f"- {i['name']} ({i['mime']})")

html = f"""
<!doctype html>
<html lang="pt">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Dia do Pai</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;600&display=swap" />
    <style>
      :root {{
        color-scheme: light;
        --bg: #f6f2ea;
        --ink: #2d2a26;
        --accent: #b06a4f;
        --accent-soft: #e7c9b5;
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Source Sans 3", system-ui, sans-serif;
        color: var(--ink);
        background: radial-gradient(circle at top, #fff8ef 0%, var(--bg) 50%, #e9e1d6 100%);
        display: flex;
        align-items: flex-start;
        justify-content: center;
        padding: 24px;
      }}

      .stage {{
        width: min(100%, 1100px);
        display: grid;
        gap: 20px;
      }}

      .frame {{
        position: relative;
        background: #fefcf8;
        border-radius: 24px;
        padding: 16px;
        box-shadow: 0 20px 45px rgba(45, 42, 38, 0.18);
        overflow: hidden;
        min-height: 640px;
        display: grid;
        place-items: center;
      }}

      .frame::before {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(130deg, rgba(176, 106, 79, 0.08), rgba(231, 201, 181, 0.05));
        pointer-events: none;
      }}

      .frame img,
      .frame video {{
        position: absolute;
        width: 100%;
        height: 100%;
        object-fit: contain;
        object-position: center;
        border-radius: 16px;
        opacity: 0;
        transform: scale(1.02);
        transition: opacity 0.6s ease, transform 0.8s ease;
      }}

      .frame img.show,
      .frame video.show {{
        opacity: 1;
        transform: scale(1);
      }}

      .overlay {{
        position: relative;
        z-index: 2;
        text-align: center;
        padding: 12px 16px;
        background: rgba(255, 252, 248, 0.8);
        border-radius: 14px;
        box-shadow: 0 8px 20px rgba(45, 42, 38, 0.1);
        opacity: 0;
        transition: opacity 0.6s ease;
      }}

      .loading {{
        position: absolute;
        inset: 0;
        z-index: 10;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle at top, #fff8ef 0%, #f6f2ea 50%, #e9e1d6 100%);
        border-radius: 16px;
        gap: 12px;
        font-size: 15px;
        color: #6f655d;
        transition: opacity 0.5s ease;
      }}

      .loading-bar {{
        display: block;
        width: 260px;
        height: 6px;
        border-radius: 999px;
        background: rgba(176, 106, 79, 0.25);
        overflow: hidden;
      }}

      .loading-bar::after {{
        content: "";
        display: block;
        height: 100%;
        width: 40%;
        background: var(--accent);
        border-radius: 999px;
        animation: loading-move 1.2s ease-in-out infinite;
      }}

      @keyframes loading-move {{
        0% {{ transform: translateX(-10%); }}
        50% {{ transform: translateX(230%); }}
        100% {{ transform: translateX(-10%); }}
      }}

      .overlay h1 {{
        margin: 0 0 4px;
        font-family: "Playfair Display", serif;
        font-size: clamp(28px, 4vw, 40px);
      }}

      .overlay p {{
        margin: 0;
        font-size: 16px;
      }}

      .frame.playing .overlay {{
        opacity: 0 !important;
        transform: translateY(8px);
        pointer-events: none !important;
      }}

      .controls {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
      }}

      button {{
        border: none;
        padding: 12px 20px;
        border-radius: 999px;
        background: var(--accent);
        color: #fff;
        font-weight: 600;
        font-size: 15px;
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 10px 20px rgba(176, 106, 79, 0.25);
      }}

      button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 14px 26px rgba(176, 106, 79, 0.3);
      }}

      button#pause {{ background: #6b5f56; }}
      button#next {{ background: #c98a6b; }}
      button#next-order {{ background: #9a7d67; }}

      .hint {{
        position: fixed;
        top: 16px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        text-align: center;
        color: #6f655d;
        font-size: 14px;
        background: rgba(255, 252, 248, 0.95);
        padding: 8px 18px;
        border-radius: 999px;
        box-shadow: 0 4px 16px rgba(45, 42, 38, 0.12);
        white-space: nowrap;
      }}

      .debug {{
        display: none;
        padding: 10px 14px;
        border-radius: 12px;
        background: rgba(255, 252, 248, 0.9);
        border: 1px solid rgba(45, 42, 38, 0.1);
        font-size: 12px;
        color: #3a342e;
        box-shadow: 0 8px 16px rgba(45, 42, 38, 0.08);
      }}

      @media (max-width: 700px) {{
        .frame {{ min-height: 440px; }}
        body {{ padding-top: 16px; }}
      }}
    </style>
  </head>
  <body>
    <main class="stage">
      <div class="debug" id="debug" aria-live="polite"></div>
      <div class="frame" id="frame">
        <div class="loading" id="loading">
          A carregar uma surpresa muito especial...
          <span class="loading-bar"></span>
        </div>
        <img id="photo" alt="" />
        <video id="video" playsinline preload="auto"></video>
        <div class="overlay" id="overlay">
          <h1>Dia do Pai</h1>
          <h3>19/03/2026</h3>
          <p>Memórias que passam ao acaso</p>
        </div>
      </div>
      <div class="controls">
        <button id="play" type="button">Reproduzir</button>
        <button id="pause" type="button">Pausar</button>
        <button id="next-order" type="button">Próximo</button>
        <button id="next" type="button">Próximo aleatório</button>
        <button id="sound" type="button">Desativar som</button>
      </div>
      <div class="hint" id="hint"></div>
    </main>
    <script>
      const items = {items_json};
      const ACCESS_TOKEN = {access_token_json};
      const debugEnabled = {debug_flag_json};

      const photo = document.getElementById("photo");
      const video = document.getElementById("video");
      const hint = document.getElementById("hint");
      const frame = document.getElementById("frame");
      const debugEl = document.getElementById("debug");
      const loading = document.getElementById("loading");
      const overlay = document.getElementById("overlay");
      const playBtn = document.getElementById("play");
      const pauseBtn = document.getElementById("pause");
      const nextOrderBtn = document.getElementById("next-order");
      const nextBtn = document.getElementById("next");
      const soundBtn = document.getElementById("sound");

      let currentIndex = -1;
      let timer = null;
      let isPlaying = false;
      let isMuted = false;

      const IMAGE_DURATION_MS = 6000;

      // Cache de blobs já descarregados
      const blobCache = {{}};

      function showHint(text) {{
        hint.textContent = text;
      }}

      function hideLoading() {{
        if (loading) {{
          loading.style.opacity = "0";
          setTimeout(() => {{ loading.style.display = "none"; }}, 500);
        }}
        overlay.style.opacity = "1";
        showHint("Pronto para reproduzir.");
      }}

      function initHint() {{
        if (!items.length) {{
          showHint("Sem media encontrado. Confirma a pasta configurada.");
          hideLoading();
          return;
        }}
        const readyFonts = document.fonts && document.fonts.ready
          ? document.fonts.ready
          : Promise.resolve();
        const minWait = new Promise(resolve => setTimeout(resolve, 1500));
        Promise.all([readyFonts, minWait]).then(() => {{
          window.requestAnimationFrame(() => {{
            window.requestAnimationFrame(() => {{
              hideLoading();
            }});
          }});
        }});
      }}

      // Descarrega um ficheiro do Drive via API com o token de acesso
      async function fetchDriveFile(fileId, mime) {{
        if (blobCache[fileId]) return blobCache[fileId];
        const url = `https://www.googleapis.com/drive/v3/files/${{fileId}}?alt=media&supportsAllDrives=true`;
        const resp = await fetch(url, {{
          headers: {{ "Authorization": `Bearer ${{ACCESS_TOKEN}}` }}
        }});
        if (!resp.ok) throw new Error(`Erro ao descarregar ficheiro: ${{resp.status}}`);
        const blob = await resp.blob();
        const objectUrl = URL.createObjectURL(blob);
        blobCache[fileId] = objectUrl;
        return objectUrl;
      }}

      function clearStage() {{
        photo.classList.remove("show");
        video.classList.remove("show");
        video.pause();
        video.removeAttribute("src");
        while (video.firstChild) video.removeChild(video.firstChild);
        video.load();
      }}

      function pickNext() {{
        if (!items.length) return null;
        let idx = Math.floor(Math.random() * items.length);
        if (items.length > 1 && idx === currentIndex) idx = (idx + 1) % items.length;
        currentIndex = idx;
        return items[idx];
      }}

      function pickNextOrdered() {{
        if (!items.length) return null;
        currentIndex = (currentIndex + 1) % items.length;
        return items[currentIndex];
      }}

      function scheduleNext(delay) {{
        if (timer) window.clearTimeout(timer);
        timer = window.setTimeout(() => {{
          console.log("scheduleNext fired, isPlaying=", isPlaying);
          if (isPlaying) playNext();
        }}, delay);
      }}

      async function playItem(item) {{
        if (timer) window.clearTimeout(timer);
        showHint("A carregar...");
        try {{
          const blobUrl = await fetchDriveFile(item.id, item.mime);
          if (timer) window.clearTimeout(timer);
          clearStage();
          frame.classList.add("playing");
          if (item.type === "video") {{
            video.muted = isMuted;
            video.classList.add("show");
            video.src = blobUrl;
            video.load();
            showHint("");
            video.play().catch(err => {{
              if (err.name !== "AbortError") {{
                showHint("Erro: " + err.name);
              }}
            }});
          }} else {{
            const img = new Image();
            img.onload = () => {{
              photo.src = blobUrl;
              photo.classList.add("show");
              scheduleNext(IMAGE_DURATION_MS);
              showHint("");
            }};
            img.onerror = () => scheduleNext(IMAGE_DURATION_MS);
            img.src = blobUrl;
            if (img.complete) {{
              photo.src = blobUrl;
              photo.classList.add("show");
              scheduleNext(IMAGE_DURATION_MS);
              showHint("");
            }}
          }}
        }} catch(err) {{
          showHint("Erro ao carregar: " + err.message);
          scheduleNext(2000);
        }}
      }}

      function playNext() {{
        const item = pickNext();
        if (item) playItem(item);
      }}

      function playNextOrdered() {{
        const item = pickNextOrdered();
        if (item) playItem(item);
      }}

      playBtn.addEventListener("click", () => {{
        if (!items.length) return;
        isPlaying = true;
        frame.classList.add("playing");
        if (currentIndex === -1) {{
          playNext();
        }} else if (video.classList.contains("show")) {{
          video.play();
        }} else {{
          scheduleNext(IMAGE_DURATION_MS);
        }}
      }});

      pauseBtn.addEventListener("click", () => {{
        isPlaying = false;
        if (timer) window.clearTimeout(timer);
        video.pause();
      }});

      nextOrderBtn.addEventListener("click", () => {{
        isPlaying = true;
        playNextOrdered();
      }});

      nextBtn.addEventListener("click", () => {{
        isPlaying = true;
        playNext();
      }});

      soundBtn.addEventListener("click", () => {{
        isMuted = !isMuted;
        video.muted = isMuted;
        soundBtn.textContent = isMuted ? "Ativar som" : "Desativar som";
      }});

      video.addEventListener("ended", () => {{
        if (isPlaying) playNext();
      }});

      initHint();
    </script>
  </body>
</html>
"""

components.html(html, height=900, scrolling=False)