import base64
import json
import mimetypes
import os
import random
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

APP_ROOT = Path(__file__).resolve().parent
MEDIA_DIR = (APP_ROOT / "media").resolve()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}
GDRIVE_MIME_IMAGE_PREFIX = "image/"
GDRIVE_MIME_VIDEO_PREFIX = "video/"
GDRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
GDRIVE_FOLDER_ID = None

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_MAX_ITEMS = 40
DEFAULT_MAX_TOTAL_MB = 200
DEFAULT_MAX_SINGLE_MB = 60
DEFAULT_CACHE_TTL_SECONDS = 21600


def _is_debug_media():
    if "debug_media" in st.secrets:
        val = st.secrets["debug_media"]
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
        return bool(val)
    return os.environ.get("DEBUG_MEDIA", "").strip().lower() in {"1", "true", "yes", "on"}


def _get_int_setting(key, default):
    if key in st.secrets:
        try:
            return int(st.secrets[key])
        except Exception:
            return default
    raw = os.environ.get(key)
    if raw:
        try:
            return int(raw)
        except Exception:
            return default
    return default

st.set_page_config(page_title="Dia do Pai", layout="wide")

st.markdown(
    """
<style>
#MainMenu, footer, header {visibility: hidden;}
html, body, .stApp {height: 100%;}
/* Remove Streamlit default padding */
div[data-testid="stAppViewContainer"] > .main {padding: 0;}
div[data-testid="stAppViewContainer"] .block-container {padding-top: 0; padding-bottom: 0;}
div[data-testid="stAppViewContainer"] {background: radial-gradient(circle at top, #fff8ef 0%, #f6f2ea 50%, #e9e1d6 100%);}
/* Esconde barra do topo */
div[data-testid="stStatusWidget"] {display: none !important;}
div[data-testid="stToolbar"] {display: none !important;}
div[data-testid="stDecoration"] {display: none !important;}
div[class*="StatusWidget"] {display: none !important;}
/* Barra laranja do topo */
header[data-testid="stHeader"] {display: none !important;}
div[class*="decoration"] {display: none !important;}
/* Skeleton loader azul */
div.stSkeleton {display: none !important;}
[class*="stSkeleton"] {display: none !important;}
</style>
""",
    unsafe_allow_html=True,
)


def _get_drive_service():
    creds_info = None
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
    elif os.environ.get("GCP_SERVICE_ACCOUNT_JSON"):
        creds_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_JSON"])

    if not creds_info:
        raise RuntimeError("Credenciais do Google Drive não encontradas.")
    if "\\n" in str(creds_info.get("private_key", "")):
        # Auto-fix common copy issue from JSON
        creds_info["private_key"] = str(creds_info["private_key"]).replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


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


def _list_drive_files_metadata(service, folder_id, shared_drive_id=None, limit=20):
    files = []
    query = f"'{folder_id}' in parents and trashed = false"
    page_token = None
    while len(files) < limit:
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
            files.append(f)
            if len(files) >= limit:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def _download_drive_file(service, file_id):
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


@st.cache_data(show_spinner=False, ttl=DEFAULT_CACHE_TTL_SECONDS)
def _download_drive_file_cached(file_id, modified_time):
    service = _get_drive_service()
    return _download_drive_file(service, file_id)


def _parse_data_url(data_url):
    if not data_url or not data_url.startswith("data:"):
        return None, None
    header, b64 = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    return mime, base64.b64decode(b64)


def _parse_data_url(data_url):
    if not data_url or not data_url.startswith("data:"):
        return None, None
    header, b64 = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    return mime, base64.b64decode(b64)


def _load_media_items(progress_cb=None):
    # Prefer Google Drive if configured
    folder_id = _get_drive_folder_id()
    if folder_id:
        service = _get_drive_service()
        shared_drive_id = _get_shared_drive_id()
        items = []
        errors = []
        max_items = _get_int_setting("MAX_PRELOAD_ITEMS", DEFAULT_MAX_ITEMS)
        max_total_mb = _get_int_setting("MAX_TOTAL_MB", DEFAULT_MAX_TOTAL_MB)
        max_single_mb = _get_int_setting("MAX_SINGLE_MB", DEFAULT_MAX_SINGLE_MB)
        max_total_bytes = max_total_mb * 1024 * 1024
        max_single_bytes = max_single_mb * 1024 * 1024
        total_bytes = 0
        candidates = list(_iter_drive_files(service, folder_id, shared_drive_id=shared_drive_id))
        total_candidates = len(candidates) if candidates else 1
        for f in candidates:
            if progress_cb:
                progress_cb(f, total_candidates)
            mime = f.get("mimeType") or ""
            if not (mime.startswith(GDRIVE_MIME_IMAGE_PREFIX) or mime.startswith(GDRIVE_MIME_VIDEO_PREFIX)):
                # Fallback: check extension if Drive mime isn't helpful
                ext = Path(f.get("name", "")).suffix.lower()
                if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
                    continue
                if not mime:
                    mime, _ = mimetypes.guess_type(f.get("name", ""))
            if not mime:
                continue
            size = int(f.get("size") or 0)
            if size and size > max_single_bytes:
                errors.append({
                    "name": f.get("name", ""),
                    "mime": mime,
                    "error": f"Ficheiro demasiado grande ({size} bytes)",
                    "size": size,
                })
                continue
            if max_total_bytes and size and (total_bytes + size > max_total_bytes):
                continue
            try:
                data = _download_drive_file_cached(f["id"], f.get("modifiedTime"))
                if max_total_bytes and (total_bytes + len(data) > max_total_bytes):
                    continue
                url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
                items.append({
                    "url": url,
                    "type": "video" if mime.startswith(GDRIVE_MIME_VIDEO_PREFIX) else "image",
                    "name": f.get("name", ""),
                    "mime": mime,
                })
                total_bytes += len(data)
                if max_items and len(items) >= max_items:
                    break
            except Exception as exc:
                errors.append({
                    "name": f.get("name", ""),
                    "mime": mime,
                    "error": str(exc),
                    "size": f.get("size"),
                })
        return {"items": items, "errors": errors}

    # Fallback to local media folder
    if not MEDIA_DIR.exists() or not MEDIA_DIR.is_dir():
        return []

    items = []
    for path in MEDIA_DIR.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
            continue
        mime, _ = mimetypes.guess_type(path.name)
        if not mime:
            mime = "video/mp4" if ext in VIDEO_EXTS else "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        url = f"data:{mime};base64,{data}"
        items.append({
            "url": url,
            "type": "video" if ext in VIDEO_EXTS else "image",
            "name": path.name,
            "mime": mime,
        })

    return {"items": items, "errors": []}


_load_error = None
folder_id_for_debug = _get_drive_folder_id()
loading_placeholder = st.empty()
progress_placeholder = st.empty()

def _progress_cb(file_info, total):
    if not total:
        return
    if not hasattr(_progress_cb, "count"):
        _progress_cb.count = 0
    _progress_cb.count += 1

try:
    result = _load_media_items(progress_cb=_progress_cb)
except Exception as exc:
    _load_error = exc
    st.error(f"Erro ao carregar media do Google Drive: {exc}")
    result = {"items": [], "errors": []}
loading_placeholder.empty()
progress_placeholder.empty()
items = result.get("items", [])
load_errors = result.get("errors", [])
items_json = json.dumps(items)
debug_info = None
debug_enabled = _is_debug_media()
if debug_enabled:
    debug_info = {
        "folder_id_set": bool(folder_id_for_debug),
        "shared_drive_id_set": bool(_get_shared_drive_id()),
        "has_service_account": "gcp_service_account" in st.secrets or bool(os.environ.get("GCP_SERVICE_ACCOUNT_JSON")),
        "items_count": len(items),
        "error": str(_load_error) if _load_error else "",
    }
debug_json = json.dumps(debug_info)
debug_flag_json = "true" if debug_enabled else "false"

if debug_enabled:
    with st.expander("Debug media", expanded=True):
        st.write(f"Folder ID definido: {bool(folder_id_for_debug)}")
        st.write(f"Shared Drive ID definido: {bool(_get_shared_drive_id())}")
        st.write(f"Secrets com service account: {'gcp_service_account' in st.secrets}")
        st.write(f"Chaves em st.secrets: {list(st.secrets.keys())}")
        if "gdrive_folder_id" in st.secrets:
            st.write(f"gdrive_folder_id (raw): {st.secrets['gdrive_folder_id']}")
        st.write(f"MAX_PRELOAD_ITEMS: {_get_int_setting('MAX_PRELOAD_ITEMS', DEFAULT_MAX_ITEMS)}")
        st.write(f"MAX_TOTAL_MB: {_get_int_setting('MAX_TOTAL_MB', DEFAULT_MAX_TOTAL_MB)}")
        st.write(f"MAX_SINGLE_MB: {_get_int_setting('MAX_SINGLE_MB', DEFAULT_MAX_SINGLE_MB)}")
        st.write(f"Itens carregados: {len(items)}")
        video_count = sum(1 for i in items if i.get("type") == "video")
        st.write(f"Vídeos detectados: {video_count}")
        if _load_error:
            st.write(f"Erro: {_load_error}")
        if load_errors:
            st.write("Erros ao baixar ficheiros:")
            for err in load_errors[:5]:
                st.write(f"- {err.get('name')} ({err.get('mime')}): {err.get('error')}")
        try:
            _svc = _get_drive_service()
            _shared_id = _get_shared_drive_id()
            _files = _list_drive_files_metadata(_svc, folder_id_for_debug, shared_drive_id=_shared_id)
            st.write(f"Ficheiros na pasta (topo): {len(_files)}")
            for f in _files[:5]:
                size = f.get("size")
                size_txt = f"{size} bytes" if size else "size?"
                st.write(f"- {f.get('name')} ({f.get('mimeType')}, {size_txt})")
        except Exception as exc:
            st.write(f"Falha ao listar ficheiros: {exc}")
        if video_count:
            first_video = next(i for i in items if i.get("type") == "video")
            mime, blob = _parse_data_url(first_video["url"])
            st.write(f"Preview vídeo: {mime}")
            if blob:
                st.video(blob)

if folder_id_for_debug and not items:
    st.warning(
        "Não encontrei media no Google Drive. Confirma se a pasta está partilhada "
        "com a Service Account e se o Drive API está ativado no projeto."
    )
    if _is_debug_media():
        try:
            _svc = _get_drive_service()
            _shared_id = _get_shared_drive_id()
            _files = _list_drive_files_metadata(_svc, folder_id_for_debug, shared_drive_id=_shared_id)
            st.info(f"Debug: encontrei {len(_files)} ficheiros na pasta de topo.")
            for f in _files[:10]:
                st.write(f"- {f.get('name')} ({f.get('mimeType')})")
        except Exception as exc:
            st.error(f"Debug: falha ao listar ficheiros no Drive: {exc}")

html = f"""
<!doctype html>
<html lang="pt">
  <head>
    <script>
      (function() {{
        function hideDecorations() {{
          try {{
            const parent = window.parent || window.top;
            if (!parent || !parent.document) return;
            const doc = parent.document;
            const selectors = [
              '[data-testid="stDecoration"]',
              '[data-testid="stToolbar"]',
              '[data-testid="stHeader"]',
              'header',
            ];
            selectors.forEach(sel => {{
              doc.querySelectorAll(sel).forEach(el => {{
                el.style.setProperty('display', 'none', 'important');
              }});
            }});
          }} catch(e) {{}}
        }}
        hideDecorations();
        setTimeout(hideDecorations, 100);
        setTimeout(hideDecorations, 500);
        setTimeout(hideDecorations, 1000);
      }})();
    </script>
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

      * {{
        box-sizing: border-box;
      }}

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
        50% {{ transform: translateX(130%); }}
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
        opacity: 0;
        transform: translateY(8px);
        pointer-events: none;
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

      button#pause {{
        background: #6b5f56;
      }}

      button#next {{
        background: #c98a6b;
      }}

      button#next-order {{
        background: #9a7d67;
      }}

      .hint {{
        text-align: center;
        color: #6f655d;
        font-size: 14px;
      }}

      .loading {{
        position: absolute;
        top: 24px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 3;
        text-align: center;
        color: #6f655d;
        font-size: 14px;
        padding: 8px 14px;
        border-radius: 999px;
        background: rgba(255, 252, 248, 0.95);
        box-shadow: 0 8px 16px rgba(45, 42, 38, 0.08);
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
        .frame {{
          min-height: 440px;
        }}
        body {{
          padding-top: 16px;
        }}
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
        <button id="sound" type="button">Ativar som</button>
      </div>
      <div class="hint" id="hint">A carregar uma surpresa muito especial...</div>
    </main>
    <script>
      const items = {items_json};
      const debug = {debug_json};
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
      let isMuted = true;

      const IMAGE_DURATION_MS = 6000;

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
        }} else {{
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
      }}

      function renderDebug() {{
        if (!debug) return;
        debugEl.style.display = "block";
        debugEl.textContent =
          "debug_media: folder_id=" + debug.folder_id_set +
          " | shared_drive_id=" + debug.shared_drive_id_set +
          " | service_account=" + debug.has_service_account +
          " | items=" + debug.items_count +
          (debug.error ? " | erro=" + debug.error : "");
      }}

      function clearStage() {{
        photo.classList.remove("show");
        video.classList.remove("show");
        video.pause();
        video.removeAttribute("src");
        while (video.firstChild) {{
          video.removeChild(video.firstChild);
        }}
        video.load();
      }}

      function pickNext() {{
        if (!items.length) return null;
        let idx = Math.floor(Math.random() * items.length);
        if (items.length > 1 && idx === currentIndex) {{
          idx = (idx + 1) % items.length;
        }}
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
          if (isPlaying) playNext();
        }}, delay);
      }}

      function playImage(url) {{
        clearStage();
        frame.classList.add("playing");
        photo.src = url;
        photo.onload = () => photo.classList.add("show");
        scheduleNext(IMAGE_DURATION_MS);
      }}

      function playVideo(item) {{
        clearStage();
        frame.classList.add("playing");
        const source = document.createElement("source");
        source.src = item.url;
        if (item.mime) {{
          source.type = item.mime;
        }}
        video.appendChild(source);
        video.muted = isMuted;
        video.load();
        video.classList.add("show");
        video.play().catch((err) => {{
          const reason = err && err.name ? err.name : "erro";
          showHint("Erro ao reproduzir vídeo: " + reason);
          console.error(err);
        }});
      }}

      function playNext() {{
        const item = pickNext();
        if (!item) return;
        if (item.type === "video") {{
          const mime = item.mime || "";
          if (mime && video.canPlayType(mime) === "") {{
            showHint("Vídeo não suportado pelo browser. Converte para MP4 (H.264).");
            scheduleNext(1500);
            return;
          }}
          playVideo(item);
          if (debugEnabled) {{
            const support = mime ? video.canPlayType(mime) : "sem mime";
            showHint("Debug vídeo: " + (item.name || "sem nome") + " | mime=" + (mime || "n/a") + " | canPlayType=" + support);
          }}
        }} else {{
          playImage(item.url);
        }}
      }}

      function playNextOrdered() {{
        const item = pickNextOrdered();
        if (!item) return;
        if (item.type === "video") {{
          const mime = item.mime || "";
          if (mime && video.canPlayType(mime) === "") {{
            showHint("Vídeo não suportado pelo browser. Converte para MP4 (H.264).");
            scheduleNext(1500);
            return;
          }}
          playVideo(item);
          if (debugEnabled) {{
            const support = mime ? video.canPlayType(mime) : "sem mime";
            showHint("Debug vídeo: " + (item.name || "sem nome") + " | mime=" + (mime || "n/a") + " | canPlayType=" + support);
          }}
        }} else {{
          playImage(item.url);
        }}
      }}

      playBtn.addEventListener("click", () => {{
        if (!items.length) return;
        isPlaying = true;
        frame.classList.add("playing");
        showHint("");
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
        frame.classList.remove("playing");
        if (timer) window.clearTimeout(timer);
        video.pause();
      }});

      nextOrderBtn.addEventListener("click", () => {{
        isPlaying = true;
        frame.classList.add("playing");
        playNextOrdered();
      }});

      nextBtn.addEventListener("click", () => {{
        isPlaying = true;
        frame.classList.add("playing");
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
      renderDebug();
    </script>
  </body>
</html>
"""

components.html(html, height=900, scrolling=False)
