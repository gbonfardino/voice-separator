# Voice Separator API 🎤

Isola la voce da video/audio usando AI (Demucs).

## Deploy su VPS

```bash
# Build e avvia
docker-compose up -d --build

# Verifica status
curl http://localhost:5000/health
```

## Uso

```bash
# Separa voce da video MP4
VIDEO_B64=$(base64 -w 0 video.mp4)
curl -X POST http://localhost:5000/separate-voice \
  -H "Content-Type: application/json" \
  -d "{\"video\": \"$VIDEO_B64\", \"format\": \"mp3\"}"
```

## Endpoint

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/separate-voice` | Isola voce (input: video base64) |
| GET | `/health` | Health check |

## Requisiti VPS
- RAM: minimo 2GB, consigliato 3GB+
- Spazio: ~2GB per immagine Docker + modello
