# Dia do Pai - Slideshow Local

Pequeno site local em Python (Flask) que lê fotos e vídeos de uma pasta específica e reproduz aleatoriamente.

## Requisitos
- Python 3.9+
- `pip install flask`

## Como usar
1. Cria uma pasta com as tuas fotos e vídeos (ex: `/Users/laratrindade/MediaPai`).
2. Inicia o servidor definindo a pasta:

```bash
MEDIA_DIR="/caminho/para/pasta" python server.py
```

3. Abre o browser em `http://localhost:8000`.

## Extensões suportadas
- Imagens: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Vídeos: `.mp4`, `.webm`, `.ogg`, `.mov`, `.m4v`

## Dica
Se não definires `MEDIA_DIR`, o app tenta usar `./media` dentro do projeto.
