# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Who I am

Alan — mechatronics engineer from Mendoza, Argentina, building a portfolio to land a remote AI/ML Engineer role. I have ~2 years of Python experience (AI-assisted coding style: I read, understand, and adapt code but don't write from scratch). I'm doing a postgraduate specialization in AI.

This is my second portfolio project. The first was `hydraulic-system-monitor` — a classical ML pipeline with scikit-learn/XGBoost, MLflow, FastAPI, and Docker deployed on Railway.

## Project Overview

Real-time visual inspection system for 3D-printed industrial parts running on a Raspberry Pi 5 with a USB camera. The model performs three simultaneous tasks:

- **Classification** — defect type: `good` / `crack` / `hole` / `deformed`
- **Regression** — quality score 0.0–1.0
- **Localization** — bounding box over the defective area

Stack: OpenCV → ResNet50 multi-task head → ONNX export → ONNX Runtime on Pi → FastAPI → PostgreSQL → dashboard.

## Current phase

**Week 4 — Dataset capture.** Building the capture API that runs on the Raspberry Pi (SSH accessible at `192.168.100.67`). The API streams live video and allows remote photo capture organized by defect class.

## Dev environment

- **Development machine:** WSL2 (Ubuntu) on Windows, VS Code + Remote WSL
- **Package manager:** `uv` (not pip directly)
- **Pi:** Raspberry Pi 5, USB camera at `/dev/video0`, SSH key auth configured
- **Workflow:** develop on WSL2 → push to GitHub → pull on Pi

## Environment setup

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Commands

```bash
# Run capture API (on the Pi)
uvicorn dataset.capture:app --host 0.0.0.0 --port 8000 --reload

# Run FastAPI backend
uvicorn app.api.main:app --reload

# Run tests
pytest

# Run single test
pytest tests/path/to/test_file.py::test_function_name
```

## Architecture

- **`dataset/`** — capture API, raw images in `dataset/raw/{good,crack,hole,deformed}/`, augmented in `dataset/augmented/`
- **`src/`** — model definition (ResNet50 multi-task), dataset loader, training loop, MLflow tracking
- **`inference/`** — ONNX export script, inference pipeline for the Pi with visual overlay
- **`app/`** — FastAPI backend + PostgreSQL via SQLAlchemy
- **`dashboard/`** — real-time inspection dashboard
- **`notebooks/`** — EDA and prototyping
- **`tests/`** — test suite

Data flow: Pi camera → capture API → `dataset/raw/` → training (`src/`) → ONNX export → Pi inference → FastAPI backend → dashboard.

## How to help me

- Explain decisions, don't just write code — I need to understand architecture choices to defend them in interviews
- Point out when something is not production-grade and explain why
- Use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- Everything in English
- When I'm stuck, guide me toward the solution rather than giving it directly
- Flag any security issues (credentials, exposed ports, etc.)

## Key decisions already made

- `uv` over `pip` for package management
- `opencv-python-headless` (no GUI dependencies — runs headless on Pi)
- Multi-task single model over three separate models (efficiency + shared features)
- ONNX Runtime on Pi over PyTorch (lighter, faster inference on edge hardware)
- FastAPI over Flask (async, automatic docs, type validation)