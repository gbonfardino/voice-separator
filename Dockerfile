FROM python:3.10-slim

# Installa FFmpeg e dipendenze sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installa torch CPU-only prima (evita conflitti)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# Poi installa demucs e altre dipendenze
RUN pip install --no-cache-dir demucs soundfile flask

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
