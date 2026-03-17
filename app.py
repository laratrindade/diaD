import base64
import json
import mimetypes
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_ROOT = Path(__file__).resolve().parent
MEDIA_DIR = (APP_ROOT / "media").resolve()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}

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
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _load_media_items():
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
        })

    return items


items = _load_media_items()
items_json = json.dumps(items)

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
        transition: opacity 0.3s ease, transform 0.3s ease;
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

      .hint {{
        text-align: center;
        color: #6f655d;
        font-size: 14px;
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
      <div class="frame" id="frame">
        <img id="photo" alt="" />
        <video id="video" playsinline></video>
        <div class="overlay">
          <h1>Dia do Pai</h1>
          <h3>19/03/2026</h3>
          <p>Memórias que passam ao acaso</p>
        </div>
      </div>
      <div class="controls">
        <button id="play" type="button">Reproduzir</button>
        <button id="pause" type="button">Pausar</button>
        <button id="next" type="button">Próximo aleatório</button>
      </div>
      <div class="hint" id="hint"></div>
    </main>
    <script>
      const items = {items_json};
      const photo = document.getElementById("photo");
      const video = document.getElementById("video");
      const hint = document.getElementById("hint");
      const frame = document.getElementById("frame");
      const playBtn = document.getElementById("play");
      const pauseBtn = document.getElementById("pause");
      const nextBtn = document.getElementById("next");

      let currentIndex = -1;
      let timer = null;
      let isPlaying = false;

      const IMAGE_DURATION_MS = 6000;

      function showHint(text) {{
        hint.textContent = text;
      }}

      function initHint() {{
        if (!items.length) {{
          showHint("Sem media encontrado. Confirma a pasta configurada.");
        }} else {{
          showHint("Pronto para reproduzir.");
        }}
      }}

      function clearStage() {{
        photo.classList.remove("show");
        video.classList.remove("show");
        video.pause();
        video.removeAttribute("src");
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

      function playVideo(url) {{
        clearStage();
        frame.classList.add("playing");
        video.src = url;
        video.classList.add("show");
        video.play().catch(() => {{
          showHint("Clique em Reproduzir para iniciar o vídeo.");
        }});
      }}

      function playNext() {{
        const item = pickNext();
        if (!item) return;
        if (item.type === "video") {{
          playVideo(item.url);
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

      nextBtn.addEventListener("click", () => {{
        isPlaying = true;
        frame.classList.add("playing");
        playNext();
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
