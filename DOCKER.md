# Docker deployment

**Source repository:** [https://github.com/OliseNS/nexus_project](https://github.com/OliseNS/nexus_project)

Run the **FastAPI backend** (NestChat / NestDB APIs) and **Nestperts** (Flask expert tools) as two containers from the same image. Data and annotation projects persist in Docker volumes or host bind mounts.

## Prerequisites

- Docker 24+ and Docker Compose v2
- A populated **bird database** at `data/bird_data_complete.db` (see the main `README.md` import steps) unless you only need Nestperts UI without NestChat DB features
- **OpenRouter** API key and any model keys in `.env`
- For Nestperts login: **Google OAuth** credentials, `SECRET_KEY`, and a seeded **`user_auth.db`** (see below)
- For **NestVision / Swift AI** in Nestperts: ONNX + PyTorch weights under **`models/`** (not in git). See **[docs/VISION_MODELS.md](docs/VISION_MODELS.md)**.

## Quick start

```bash
cp .env.example .env
# Edit .env: OPENROUTER_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, etc.

# Recommended: prepare data on the host, then use bind mounts (simplest for first deploy)
mkdir -p data logs labeller/projects models
# Copy or generate bird_data_complete.db into ./data
# Copy vision weights into ./models (see docs/VISION_MODELS.md)
python seed_root_admin.py

docker compose -f docker-compose.yml -f docker-compose.host-mounts.yml up -d --build
```

- **API / docs:** `http://localhost:8000/docs`  
- **Nestperts:** `http://localhost:5000`  
- **Ports:** override with `API_PORT` and `NESTPERTS_PORT` in the shell or in `.env` (Compose substitutes `${VAR}` from the environment).

### Default: named volumes

```bash
docker compose up -d --build
```

Copy your `bird_data_complete.db` into the named volume `nestscope_data`, for example:

```bash
docker cp ./data/bird_data_complete.db "$(docker compose ps -q api):/app/data/"
```

Or generate the database on the host (see the main `README.md`), then use `docker-compose.host-mounts.yml` so `./data` is mounted directly.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DB_PATH` | Path **inside the container** to the bird SQLite DB (default `/app/data/bird_data_complete.db`) |
| `AUTH_DB_PATH` | Nestperts auth SQLite (default `/app/data/user_auth.db`) |
| `API_BASE_URL` | Public URL browsers use to reach the API (set when behind TLS / reverse proxy) |
| `OPENROUTER_API_KEY` | Required for LLM features |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Nestperts OAuth |
| `SECRET_KEY` | Flask session signing |

OAuth **Authorized redirect URI** in Google Cloud Console must match how users reach Nestperts, e.g. `https://nestperts.example.com/auth/google/callback` when using TLS and a hostname.

## Reverse proxy and TLS

The API is started with `--proxy-headers` so `X-Forwarded-*` from nginx or Traefik is respected. Put Nestperts behind a proxy with a large `client_max_body_size` (uploads). See `deploy/nginx.conf.example`.

## Resource notes

- The image installs the full `requirements.txt` (PyTorch, vision stack, etc.) and is **large**. Build on a machine with sufficient disk and RAM.
- For **GPU** inference inside containers, you would extend the Dockerfile with NVIDIA CUDA base images and matching PyTorch builds; that is not included in the default file.

## Operations

```bash
docker compose logs -f api nestperts
docker compose ps
docker compose down
```

Backups: snapshot `./data` and `./labeller/projects` when using `docker-compose.host-mounts.yml`, or back up named volumes with `docker run --rm -v nestscope_data:/data -v $(pwd):/backup alpine tar czf /backup/nestscope_data.tgz /data`.

## Vision models (NestVision / Swift)

Weights are **not** baked into the image. Compose mounts **`/app/models`** from:

- **Named volume** `nestscope_models` (default `docker-compose.yml`), or  
- **Host bind** `./models:/app/models` when using `docker-compose.host-mounts.yml`.

Place files so they match **`server/config.yaml`** (`cv.model`, `cv.classifier`) and **`models/mobile_sam.pt`** for Swift segmentation. Full checklist, GPU notes, and CI patterns: **[docs/VISION_MODELS.md](docs/VISION_MODELS.md)**.

## Troubleshooting

- **API healthcheck failing:** `/health` opens the bird DB. Ensure `DB_PATH` exists and is readable inside the container.
- **Nestperts login redirect mismatch:** Update Google OAuth redirect URIs and any public URL env vars.
- **Permission errors on volumes:** Files on the host may be owned by root from an earlier container run; align UIDs or `chown` to user `1000` (`nestscope` in the image).
- **Detection/classification errors:** Missing ONNX or wrong path — see [docs/VISION_MODELS.md](docs/VISION_MODELS.md) and run `python labeller/diagnose.py` on the host.
