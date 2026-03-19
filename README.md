# Feliz dia do Pai!!! - Slideshow Streamlit

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
1. Garante que `app.py` e `requirements.txt` estão no repositório.
2. Aponta o Streamlit Cloud para este repo e faz deploy.

## Google Drive (pasta privada)
Este app pode ler fotos e vídeos diretamente de uma pasta privada no Google Drive.

### Passos
1. Cria uma Service Account no Google Cloud e faz download do JSON.
2. Partilha a pasta do Drive com o email da Service Account, com acesso de leitor.
3. Define o `GDRIVE_FOLDER_ID` com o ID da pasta.
4. Guarda as credenciais no Streamlit Cloud em `Secrets` como `gcp_service_account`.
5. Guarda o ID da pasta como `gdrive_folder_id` em `Secrets`.
6. Se a pasta estiver num Shared Drive, adiciona também `gdrive_shared_drive_id`.

### Exemplo de Secrets (Streamlit Cloud)
```toml
gcp_service_account = { 
  "type": "service_account",
  "project_id": "teu-projeto",
  "private_key_id": "…",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n…\\n-----END PRIVATE KEY-----\\n",
  "client_email": "teu-sa@teu-projeto.iam.gserviceaccount.com",
  "client_id": "…",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "…"
}
gdrive_folder_id = "ID_DA_TUA_PASTA"
gdrive_shared_drive_id = "ID_DO_SHARED_DRIVE"
```

### Variáveis de ambiente (opcional)
- `GDRIVE_FOLDER_ID`: ID da pasta no Drive.
- `GDRIVE_SHARED_DRIVE_ID`: ID do Shared Drive (se aplicável).
- `GCP_SERVICE_ACCOUNT_JSON`: JSON completo da service account, se não usares `Secrets`.

## Nota
Os ficheiros são incorporados como `data:` URLs para manter o comportamento sem servidor externo. Para media muito pesado, pode ficar lento; nesse caso, avisa-me que otimizo.

## Performance (carregamento mais rápido)
Podes limitar o número e o tamanho dos ficheiros pré-carregados para reduzir o tempo de arranque:

```toml
MAX_PRELOAD_ITEMS = 40
MAX_TOTAL_MB = 200
MAX_SINGLE_MB = 60
```

Estas chaves podem ser colocadas nos `Secrets` (Streamlit Cloud) ou como variáveis de ambiente.


debug_media = true
