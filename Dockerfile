FROM python:3.11-slim

# Installa FFmpeg e dipendenze sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-scarica il modello Demucs (evita download al primo uso)
RUN python -c "from audio_separator.separator import Separator; s = Separator(); s.load_model('htdemucs_ft.yaml')" || true

COPY . .

EXPOSE 5000

# Usa gunicorn per produzione
CMD ["python", "app.py"]
