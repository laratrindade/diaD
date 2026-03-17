# Dia do Pai - Slideshow Local

App local em Python (Streamlit) que lê fotos e videos de uma pasta especifica, permite upload, e reproduz aleatoriamente.

## Requisitos
- Python 3.9+
- `pip install -r requirements.txt`

## Como usar
1. Cria uma pasta com as tuas fotos e videos (ex: `/Users/laratrindade/MediaPai`).
2. Inicia o app definindo a pasta:

```bash
MEDIA_DIR="/caminho/para/pasta" streamlit run app.py
```

3. Abre o browser no URL que o Streamlit mostrar (ex: `http://localhost:8501`).

## Extensões suportadas
- Imagens: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Videos: `.mp4`, `.webm`, `.ogg`, `.mov`, `.m4v`

## Dica
Se nao definires `MEDIA_DIR`, o app tenta usar `./media` dentro do projeto.

## Uso rapido
- Envia fotos e videos na secao "Enviar novas midias".
- Clica em "Proximo aleatorio" para sortear outra midia.



python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py

python3 server.py
lsof -ti:8000 | xargs kill -9 
