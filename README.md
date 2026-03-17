# Dia do Pai - Slideshow Streamlit

App em Streamlit que lê fotos e vídeos da pasta `media/` e reproduz aleatoriamente, mantendo a mesma estética e comportamento do site original.

## Requisitos
- Python 3.9+
- `pip install -r requirements.txt`

## Como usar (local)
1. Coloca as tuas fotos e vídeos dentro de `./media`.
2. Inicia o app:

```bash
streamlit run app.py
```

3. Abre o browser no endereço indicado pelo Streamlit.

## Extensões suportadas
- Imagens: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Vídeos: `.mp4`, `.webm`, `.ogg`, `.mov`, `.m4v`

## Deploy no Streamlit Cloud
1. Garante que `app.py`, `requirements.txt` e a pasta `media/` estão no repositório.
2. Aponta o Streamlit Cloud para este repo e faz deploy.

## Nota
Os ficheiros são incorporados como `data:` URLs para manter o comportamento sem servidor externo. Para media muito pesado, pode ficar lento; nesse caso, avisa-me que otimizo.
