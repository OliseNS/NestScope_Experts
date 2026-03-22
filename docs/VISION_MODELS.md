# Vision model deployment

**Repository:** [nexus_project](https://github.com/OliseNS/nexus_project)

Nestperts (and any server-side CV routes) load **bird detection**, **species classification**, and **interactive segmentation** weights from the repository **`models/`** directory at runtime. Those files are **not committed** to git (see `.gitignore`); you must ship them as part of your deployment artifact, volume, or object-storage sync.

## What the app expects

Paths are **relative to the project root** (inside Docker: `/app`). Filenames are controlled by **`server/config.yaml`** under the `cv:` key:

| Purpose | Config key | Default (current `config.yaml`) |
|--------|------------|----------------------------------|
| Detection (ONNX) | `cv.model` | `models/swift_UQ_int8.onnx` |
| Species classifier (ONNX) | `cv.classifier` | `models/classifier_swift.onnx` |
| Swift AI segmentation (PyTorch) | *(fixed path in code)* | `models/mobile_sam.pt` |

`labeller/app.py` falls back to `models/swift.onnx` if config cannot be read; keep your **`server/config.yaml`** in sync with the files you actually deploy.

### Species / class labels

The ONNX classifier resolves labels using (in order) a passed `classes_file`, `class_names.txt` at the repo root, or **`labeller/data/species_list.json`**. Ensure at least one of these matches your model’s output size (see `labeller/onnx_classifier.py`).

### Verify a machine before go-live

From the repo root (with the virtualenv active):

```bash
python labeller/diagnose.py
```

This checks dependencies and whether expected paths under `models/` exist.

---

## 1. Bare metal or VM (no Docker)

1. Create `models/` next to `server/`, `labeller/`, etc.
2. Copy your ONNX and `.pt` weights into `models/` using the names in `server/config.yaml` (or edit `config.yaml` to match your filenames).
3. Install **`onnxruntime`** (CPU) or **`onnxruntime-gpu`** on GPU hosts (must match CUDA version). The code uses `CUDAExecutionProvider` when available.
4. Restart Nestperts after changing weights or `config.yaml`.

For **GPU**: install NVIDIA drivers, CUDA/cuDNN compatible with your `onnxruntime-gpu` wheel, then confirm `onnxruntime` lists `CUDAExecutionProvider` in `get_available_providers()`.

---

## 2. Docker / Docker Compose

The default stack mounts a persistent **`models`** location so containers do not need to bake weights into the image.

### Bind mount (recommended for teams)

Use the existing overlay:

```bash
mkdir -p models
# copy swift_UQ_int8.onnx, classifier_swift.onnx, mobile_sam.pt, etc. into ./models

docker compose -f docker-compose.yml -f docker-compose.host-mounts.yml up -d --build
```

`docker-compose.host-mounts.yml` maps **`./models:/app/models`** for both `api` and `nestperts`. Nestperts runs inference locally; **both** services receive the same mount so future API-side CV features see identical paths.

### Named volumes

If you use only `docker-compose.yml`, populate the **`nestscope_models`** volume once:

```bash
docker compose up -d --build
docker cp ./models/swift_UQ_int8.onnx "$(docker compose ps -q nestperts):/app/models/"
# repeat for each file, or tar/rsync into the volume
```

Or use a short-lived container with `-v nestscope_models:/app/models` to bulk-copy.

### Image build note

`models/` is **gitignored**; `docker build` usually does **not** include weights. Rely on **volume mounts** or a private build step that `COPY`’s weights from a CI secret path.

---

## 3. GPU inference in containers

The stock `Dockerfile` is **CPU-oriented** (`pip install` pulls CPU `onnxruntime` unless you change it). To use **NVIDIA GPUs**:

1. Install the **NVIDIA Container Toolkit** on the host and use the GPU device flags in Compose (`deploy.resources.reservations.devices` or `runtime: nvidia` depending on your stack).
2. Replace **`onnxruntime`** with **`onnxruntime-gpu`** in the image (or an extra `pip install onnxruntime-gpu` that matches your CUDA version).
3. Use an **NVIDIA CUDA base image** or add CUDA libraries to the runtime; match versions to the ONNX Runtime GPU wheel you install.

Exact CUDA/cuDNN pairs change often—follow [ONNX Runtime GPU docs](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) and the [PyTorch CUDA index](https://pytorch.org/get-started/locally/) if you also run `mobile_sam.pt` on GPU inside the same container.

---

## 4. CI/CD: shipping weights without git

Typical patterns:

| Pattern | How |
|--------|-----|
| **Private artifact** | Build job downloads weights from S3/GCS/Azure Blob using OIDC or secrets, writes to `models/` before `docker compose up` or before `docker build` with a multi-stage `COPY`. |
| **Host sync** | Ansible/rsync `models/` from a secure file share to the server before `docker compose up`. |
| **Init container** | Kubernetes `initContainer` runs `aws s3 sync` (or similar) into a shared `emptyDir` volume mounted at `/app/models`. |

Never commit large `.onnx` / `.pt` files to a public repository.

---

## 5. Changing models or paths

1. Edit **`server/config.yaml`** `cv.model` and `cv.classifier` to new filenames.
2. Place the new files under **`models/`** (or update paths to subfolders, e.g. `models/production/detector.onnx`).
3. Restart Nestperts (and the API if it serves CV in your fork).
4. Run **`python labeller/diagnose.py`** again to confirm paths.

---

## 6. Troubleshooting

| Symptom | What to check |
|--------|----------------|
| `Model not found at ...` in API responses | File exists at `PROJECT_ROOT` + path from `config.yaml`; Docker mounts `./models` → `/app/models`. |
| Classification shows generic `CLASS_0` … | `species_list.json` / `class_names.txt` count vs model output classes. |
| Slow inference | CPU-only; enable GPU or reduce image size / batch in the UI. |
| `CUDAExecutionProvider` not used | `onnxruntime-gpu` installed, GPU visible in container, drivers on host. |

For Docker-specific issues, see **`../DOCKER.md`**.
