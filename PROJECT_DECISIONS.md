# Industrial Parts Inspector — Technical Decisions & Project Plan

> Living document. Updated as the project evolves.  
> Every decision here has a reason. Every reason can be defended in an interview.

---

## Hardware

| Component | Spec | Why |
|-----------|------|-----|
| Raspberry Pi 5 | 8GB RAM | Enough headroom to run ONNX Runtime inference, FastAPI, and OpenCV simultaneously without swapping. The 4GB variant would be tight with large models. |
| USB Camera | 3.0 USB Camera at `/dev/video0` | USB 3.0 delivers enough bandwidth for 1080p30 capture. The official Pi camera module requires the CSI connector — USB is more universally portable to other hardware. |
| 3D Printer | Available | Allows controlled defect generation: we define exactly what each defect class looks like, ensuring label quality. This is a significant advantage over real-world datasets where defects are rare and inconsistent. |

---

## Python Version — 3.11

**Chosen:** Python 3.11

**Why not 3.12 or 3.13:**  
PyTorch, ONNX Runtime, and OpenCV lag behind the latest Python releases by 3–6 months on ARM64 (the Pi's architecture). Wheels for `aarch64` are built less frequently than for `x86_64`. Using bleeding-edge Python on edge hardware is a reliable way to spend hours debugging missing wheels instead of building the project.

**Why not 3.10 or older:**  
3.11 introduced significant performance improvements (~25% faster than 3.10 on CPU-bound workloads according to the Python core team). For inference on the Pi's CPU, this matters. 3.10 is also approaching end-of-life.

**3.11 is the stable production target for ARM64 ML workloads in 2026.**

**Interview answer:** *"I chose Python 3.11 because it's the version with the best ARM64 wheel availability for PyTorch and ONNX Runtime, and it's significantly faster than 3.10 on CPU-bound inference — which matters when running on edge hardware."*

---

## OpenCV — `opencv-python-headless` 4.x

**Chosen:** `opencv-python-headless`

**Why not `opencv-python`:**  
The standard `opencv-python` package includes GUI dependencies (`libgtk`, `libqt`) that require a display server. The Pi runs headless (no monitor, no X server) as a server — importing the regular package raises `cannot connect to X server` errors at runtime. `headless` strips all GUI code and is ~40% smaller.

**Why not `opencv-contrib-python-headless`:**  
`contrib` includes experimental and non-free algorithms (SIFT, SURF, etc.). We don't need them for preprocessing and augmentation. Adding them increases image size and introduces potential licensing issues. Add contrib only when a specific algorithm requires it.

**Why OpenCV at all and not just PIL/Pillow:**  
Pillow is a good image manipulation library but OpenCV is the industry standard for computer vision pipelines. It provides: efficient video capture from cameras, real-time frame processing, contour detection, geometric transformations, and color space operations — all with C++ internals and Python bindings. Pillow doesn't handle video streams.

**Interview answer:** *"I used `opencv-python-headless` because the Pi runs without a display server and the standard package raises import errors without one. Headless gives identical CV functionality at 40% less size."*

---

## FastAPI over Flask

**Why FastAPI:**
- **Async by default** — critical for a streaming video endpoint. A synchronous framework blocks the thread while serving the stream, making it unable to handle concurrent requests (e.g., streaming video while someone triggers a capture).
- **Automatic OpenAPI docs** — `/docs` endpoint works out of the box. Useful for testing the API without writing a client.
- **Pydantic validation** — request bodies and path parameters are validated and typed automatically. Less boilerplate, fewer bugs.
- **Industry adoption** — FastAPI has become the standard for ML/AI APIs. It appears in the majority of AI Engineer job postings.

**Interview answer:** *"FastAPI's async support is essential for the MJPEG stream endpoint — a synchronous server would block the thread on the stream and couldn't handle concurrent capture requests."*

---

## Uvicorn as ASGI server

**Why Uvicorn over Gunicorn:**  
Gunicorn is a WSGI server — it predates async Python and doesn't support ASGI natively. FastAPI is an ASGI framework. Uvicorn is the reference ASGI server. For production with multiple workers, the combination is `gunicorn -k uvicorn.workers.UvicornWorker` — but on the Pi, a single Uvicorn process is appropriate for this workload.

**Why not Hypercorn or Daphne:**  
Uvicorn is the default recommended by the FastAPI documentation and has the widest adoption in the ecosystem. Less operational risk.

---

## Video Streaming — MJPEG over WebRTC or HLS

**Chosen:** MJPEG (Motion JPEG) over HTTP

**What it is:** Each frame is encoded as a JPEG and sent as part of a `multipart/x-mixed-replace` HTTP response. The browser reassembles them into a video stream.

**Why not WebRTC:**  
WebRTC provides low-latency bidirectional video but requires a signaling server, STUN/TURN servers for NAT traversal, and significant setup complexity. For a local network inspection system, this is massive overengineering.

**Why not HLS:**  
HLS (HTTP Live Streaming) introduces 5–30 second latency by design (it segments video into files). Completely wrong for real-time inspection.

**Why MJPEG:**  
Simple to implement (a generator function + `StreamingResponse`), natively supported by all browsers without plugins, works on local network, latency is essentially just network + encoding time (~50–100ms). Appropriate for the use case.

**Tradeoff to know:** MJPEG doesn't compress motion between frames (each frame is independent), so it uses more bandwidth than H.264. On a local network this is irrelevant.

**Interview answer:** *"I used MJPEG because it's the simplest streaming protocol that works natively in browsers without plugins, has acceptable latency for local network inspection, and avoids the infrastructure complexity of WebRTC."*

---

## Dataset Design

### Piece geometry

**Chosen piece:** a simple flat disc or rectangular tile (~40mm × 40mm × 5mm).

**Why simple geometry:**
- Consistent orientation — round or square pieces are easier to position repeatably
- Defects are clearly visible — cracks and holes on a flat surface are unambiguous
- Fast to print — one piece in ~15 minutes allows rapid iteration on defect design
- Easy to annotate bounding boxes — defects on flat surfaces have clear boundaries

**Why not complex geometry:**  
A complex part (gears, brackets) makes it harder to define what a "defect" looks like vs. intentional geometry. Ambiguous labels = noisy dataset = poor model performance.

### Defect classes

| Class | Description | How to produce |
|-------|-------------|----------------|
| `good` | No defects, clean surface | Normal print, standard settings |
| `crack` | Surface crack or layer separation | Intentionally underextrude, or score the surface after printing |
| `hole` | Missing material, void | Modify G-code to skip infill in a region, or drill after printing |
| `deformed` | Warped, shifted layers, or wrong shape | Print with bed adhesion issues, or deliberately warp with heat |

### Dataset size targets

| Class | Raw photos | After augmentation |
|-------|------------|-------------------|
| `good` | 150 | ~1,500 |
| `crack` | 150 | ~1,500 |
| `hole` | 150 | ~1,500 |
| `deformed` | 150 | ~1,500 |
| **Total** | **600** | **~6,000** |

**Why 150 raw per class and not 100:**  
With 4 augmentation strategies (flip, rotate, brightness, noise) at conservative multipliers, 100 raw gives ~800 augmented. 150 raw gives ~1,200–1,500 — enough to train ResNet50 with transfer learning without significant overfitting risk. More is better, and printing time is cheap.

**Why not use a public dataset:**  
The narrative for interviews is "I built a custom dataset with a 3D printer." Public datasets are generic. A custom dataset demonstrates end-to-end ownership of the ML pipeline — data collection, annotation, augmentation, training — which is exactly what industrial AI roles require.

### Capture setup

- **Distance:** camera 20–30cm above the piece, perpendicular
- **Lighting:** consistent lighting source, same position for every shot — variation in lighting is handled by augmentation, not by inconsistent setup
- **Background:** solid dark background (black foam or paper) — makes the piece stand out and simplifies future contour detection
- **Pieces per class:** print 3 physical pieces per class. Vary angle and position between shots, not the piece itself.

---

## Model Architecture — ResNet50 Multi-Task

**Why ResNet50 and not a custom CNN:**  
Training a CNN from scratch requires large datasets (tens of thousands of images). Transfer learning with ResNet50 (pre-trained on ImageNet's 1.2M images) allows fine-tuning on 600–1,500 images with strong performance. The ImageNet features (edges, textures, shapes) transfer well to industrial defect detection.

**Why multi-task (single model, three heads) and not three separate models:**
- Shared feature extraction — the backbone learns representations useful for all three tasks simultaneously. A crack that's relevant for classification is also relevant for localization.
- Less compute on the Pi — one forward pass instead of three.
- Fewer models to maintain, version, and deploy.
- More interesting architecturally — demonstrates knowledge of multi-task learning.

**Why not YOLO directly:**  
YOLO is optimized for detecting multiple objects of multiple classes in a single image. Our problem is: one piece per image, classify it, score it, and locate the defect. A classification backbone with task-specific heads is the right architecture. YOLO would be appropriate if we were inspecting multiple parts simultaneously on a conveyor belt — that's a future extension.

**Interview answer:** *"I chose a single ResNet50 backbone with three task-specific heads over separate models because shared feature extraction reduces compute on edge hardware and the tasks are semantically related — features useful for classifying a crack are also useful for localizing it."*

---

## ONNX Runtime on Pi — not PyTorch

**Why export to ONNX for inference:**
- PyTorch inference requires the full PyTorch runtime (~800MB). ONNX Runtime is ~150MB.
- ONNX Runtime applies graph optimizations automatically for the target hardware (ARM64 in this case).
- ONNX is the industry standard for model deployment — used by Microsoft, Meta, and in production ML systems.
- Exporting to ONNX also validates that the model is portable — it will run on any hardware that supports ONNX Runtime.

**Interview answer:** *"I exported to ONNX because the Pi has limited storage and RAM. ONNX Runtime is 5x lighter than PyTorch runtime and applies hardware-specific optimizations automatically for ARM64."*

---

## Package Manager — uv

**Why uv over pip:**  
uv is a Rust-based Python package manager that resolves and installs packages 10–100x faster than pip. It also creates reproducible lockfiles. In 2026 it's becoming the standard for new Python projects. Using it demonstrates awareness of the current Python ecosystem.

**Why not Poetry:**  
Poetry adds complexity (pyproject.toml format, custom dependency resolution) that is unnecessary for a project of this scope. uv with a `requirements.txt` is simpler and more portable.

---

## Deployment Model — Pi as edge server, Railway as cloud backend

**Two-tier architecture:**

```
[Pi — edge]                    [Railway — cloud]
capture API (FastAPI)    →     backend API (FastAPI)
ONNX inference                 PostgreSQL
local stream                   persistent storage
                               dashboard
```

**Why separate:**
- The Pi handles latency-sensitive work: camera capture and real-time inference.
- The cloud backend handles persistence, historical queries, and the public-facing dashboard.
- This mirrors real industrial architectures where edge devices send results to a central system.

**Why Railway:**  
Free tier is sufficient for a portfolio project. Automatic deploys from GitHub. No infrastructure management.

---

## Bounding Box Annotation — LabelImg

**Why LabelImg over Roboflow:**  
LabelImg runs locally, no account required, exports to standard formats (YOLO, Pascal VOC, COCO). Roboflow is excellent but is a SaaS product — for a personal project, a local tool is simpler and avoids vendor lock-in for the annotation workflow.

**Annotation format:** Pascal VOC XML (stores absolute pixel coordinates). Will be normalized to [0,1] relative coordinates before feeding to the model.

---

## Project Phases

### Phase 1 — Dataset (current)
- [ ] Capture API on Pi (FastAPI + OpenCV + MJPEG stream)
- [ ] Print pieces: 3 per class × 4 classes = 12 pieces
- [ ] Capture: 150 photos per class = 600 total
- [ ] Annotate bounding boxes with LabelImg
- [ ] Augmentation pipeline (Albumentations)
- [ ] EDA notebook

### Phase 2 — Model
- [ ] PyTorch Dataset class
- [ ] ResNet50 multi-task architecture
- [ ] Training loop with MLflow tracking
- [ ] Evaluation: F1 (classification), MAE (quality score), IoU (bounding box)
- [ ] ONNX export and validation

### Phase 3 — Edge inference
- [ ] ONNX Runtime inference script on Pi
- [ ] Visual overlay: bounding box + class + quality score on frame
- [ ] Inference API endpoint on Pi

### Phase 4 — Backend + Dashboard
- [ ] FastAPI backend on Railway
- [ ] PostgreSQL schema + SQLAlchemy models + Alembic migrations
- [ ] Endpoints: receive detections, query history, statistics
- [ ] Dashboard: real-time feed + historical charts

### Phase 5 — Polish + Deploy
- [ ] Docker multi-stage build
- [ ] GitHub Actions CI
- [ ] README with architecture diagram, metrics, demo GIF
- [ ] Interview preparation for every decision in this document

---

## Interview Questions This Project Prepares You For

- "Why ResNet50 and not a custom CNN?"
- "Why multi-task and not three separate models?"
- "Why ONNX on the Pi and not PyTorch directly?"
- "Why MJPEG and not WebRTC?"
- "How did you build the dataset?"
- "How would you detect model drift in production?"
- "How would you scale to 10 cameras on a production line?"
- "What's the difference between IoU and accuracy for evaluating localization?"
- "Why Python 3.11 and not 3.12?"
- "Why `opencv-python-headless` and not `opencv-python`?"
- "How would you handle a new defect class without retraining from scratch?"
- "What's the latency of your inference pipeline end-to-end?"
