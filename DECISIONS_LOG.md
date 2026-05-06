# Decisiones del Proyecto — Diario Incremental

> Cada decisión tomada en el proyecto, documentada mientras avanzamos.
> Sirve como registro de razonamiento + argumento para entrevistas.

---

## 29 Abril 2026 — Sesión 1: Kickoff Phase 1

### Decisión 1: Estructura de decisiones con argumentos explícitos
**Qué:** Crear este archivo DECISIONS_LOG.md como registro incremental de decisiones.  
**Por qué:** Muchos proyectos documentan "qué" pero no "por qué". En una entrevista, el "por qué" es lo que demuestra pensamiento ingenieril.  
**Argumento:** Cada línea aquí debe tener suficiente detalle para que Alan pueda explicar en una entrevista por qué esa decisión fue correcta en ese momento. No es un diario personal — es un artefacto de justificación técnica.  
**Alternativa rechazada:** Documentar después. Razón: las decisiones se olvidan, y la justificación inicial es la más fuerte.

---

### Decisión 2: Selección de dependencies para Phase 1
**Qué:** Agregar a requirements.txt: `albumentations`, `python-dotenv`, `pytest`, `pydantic` (explícito). Posponer: PyTorch, scikit-learn, MLflow, SQLAlchemy, psycopg2. No agregar: Pillow.  

**Por qué cada una:**

1. **Albumentations (SÍ):** Phase 1 es captura + augmentación. Necesitamos 600 → 6,000 imágenes. Albumentations es estándar en CV (faster, more optimized than manual OpenCV transforms). *Entrevista:* "¿Por qué no PIL?" → "Albumentations está diseñado específicamente para augmentación en ML, con optimizaciones y probabilidades integradas. PIL es para edición básica."

2. **python-dotenv (SÍ):** Variables de entorno desde día 1. Cuando desplegues en Pi: IP de cámara, rutas, credenciales. *Entrevista:* "¿Por qué .env?" → "Never hardcode secrets. .env + .gitignore es standard de seguridad."

3. **pytest (SÍ):** Testear API localmente sin subir a Pi cada vez. TDD = menos bugs.

4. **pydantic (SÍ, explícito):** Viene con FastAPI, pero listarlo clarifica que usamos type validation. *Entrevista:* "FastAPI + Pydantic valida todos los requests automáticamente — tipado desde el inicio."

5. **PyTorch, scikit-learn, MLflow (NO AHORA):** Phase 2 es entrenamiento. Agregarlo ahora añade peso sin beneficio. *Entrevista:* "Dependency management — no cargo librerías que no necesito hoy. Menos surface area para bugs, deploy más rápido."

6. **SQLAlchemy, psycopg2 (NO AHORA):** Phase 4 es backend + DB. Phase 1 guarda archivos locales en `/dataset/raw/`. *Entrevista:* "Phasetized dependencies. Cada phase tiene sus herramientas."

7. **Pillow (NO):** OpenCV hace todo lo que necesitamos (imread, transformaciones). Agregar Pillow es complejidad innecesaria. *Entrevista:* "Single responsibility. Una librería de imágenes, no dos."

**Patrón emergente:** Stageable architecture. Cada phase tiene sus propias deps. Esto es defendible en una entrevista porque muestra pensamiento en deployment.

---

### Decisión 3: Arquitectura del Capture API — estructura de paquete
**Qué:** `dataset/capture/` como paquete (no archivo único `capture.py`).  
**Por qué:** Escalabilidad y SRP (Single Responsibility Principle). Phase 1 es captura, pero Phase 2 agregará preprocessing/inference local. Un paquete permite modularidad: `routes.py`, `config.py`, `camera.py`, `utils.py` sin que un archivo explote a 500 líneas.  
**Alternativa rechazada:** Archivo único. Razón: Simple inicialmente, pero viola SRP y se vuelve unmaintainable.  
**Entrevista:** "Inversión mínima en estructura desde el inicio (solo crear carpeta + `__init__.py`) pero ganancia máxima en mantenibilidad. Un archivo de 500 líneas es un anti-patrón."

---

### Decisión 4: Endpoints del Capture API
**Qué endpoints:**
- `GET /video` → MJPEG stream continuo
- `POST /capture?defect_class=good` → captura foto, guarda en carpeta
- `GET /classes` → lista clases disponibles
- `GET /health` → healthcheck (¿viva la Pi?)
- `GET /stats` → cantidad de fotos por clase (monitoreo)

**Por qué cada uno:**
- `/video`: Core. MJPEG stream sin interrupciones.
- `/capture` (POST): Modifica estado (guarda archivo). Query param `defect_class` centraliza config.
- `/classes`: Simple pero crucial — cliente no hardcodea clases. Cambias config en un lugar.
- `/health`: Monitoreo vía HTTP antes de SSH. Validación rápida.
- `/stats`: Telemetría en tiempo real. Ves si tienes 150 fotos de `good` pero 50 de `crack` → necesitas capturar más. Previene datasets desbalanceados.

**Patrón:** APIs no solo exponen funcionalidad, exponen telemetría. `/stats` permite validar calidad de datos sin conectar SSH a la Pi.  
**Entrevista:** "Diseño orientado a observabilidad desde el inicio."

---

### Decisión 5: Cámara como estado global (no open/close por request)
**Qué:** `cv2.VideoCapture(0)` abierto UNA VEZ al startup, mantenido en memoria durante toda la sesión.  
**Por qué NO open/close por request:**
- Inicializar USB camera en Pi toma ~500ms–1s. 600 fotos × 1s = 10+ minutos desperdiciados.
- Stream MJPEG requiere lectura continua. Cerrar entre frames es patológico.

**Por qué SÍ global:**
- Abre al startup, mantén viva durante toda la sesión, cierra limpiamente en shutdown.
- Es state management estándar — como DB connection pool.

**Cleanup:** Context manager o shutdown hook asegura `cap.release()` al apagar API.  
**Entrevista:** "Recursos caros como cámaras se abren una vez, se mantienen abiertas, se cierran limpiamente. Abrirlas/cerrarlas por request es un anti-patrón de resource management."

---

### Decisión 6: Formato de nombre de archivo
**Qué:** `{timestamp}_{defect_class}.jpg` (ej: `2026-04-29T14-32-45-123_good.jpg`)  
**Por qué timestamp + clase vs UUID:**
- UUID es único pero no legible: `550e8400-e29b-41d4-a716-446655440000.jpg` → ¿cuándo? ¿qué clase?
- Timestamp es autoexplicativo: ves cuándo se capturó y qué clase es. Debugging fácil.
- Timestamp es suficientemente único acá: 600 fotos en ~2 horas = ~12 fotos/min. Millisegundos distinguen.

**Alternativa rechazada:** UUID. Razón: Innecesario en este contexto (tasa de captura baja), reduce legibilidad, complica correlación con logs.  
**Entrevista:** "UUID es para cuando necesitas garantía matemática de unicidad global. Aquí, timestamp + clase es simple, legible, y suficiente. Elige la herramienta correcta para el problema — no overengineer."

---

### Decisión 7: Ubicación del código — `src/capture/` vs `dataset/capture/`
**Qué:** Capture API vivirá en `src/capture/`, no en `dataset/capture/`.  
**Por qué separación:**
- `src/` = código/lógica
- `dataset/` = datos (imágenes, anotaciones)
- Capture API es lógica. Pertenece a `src/`.

**Beneficios:**
- Clean separation of concerns. En 6 meses abres el repo, sabes dónde buscar.
- Cuando Phase 2 agregues training, importas `from src.capture import ...` — natural desde `src/`, raro desde `dataset/`.
- `dataset/` permanece data-only, escalable (si después tienen 100K imágenes, no hay código mezclado).

**Alternativa rechazada:** `dataset/capture/`. Razón: Mezclar código en carpeta de datos confunde arquitectura.  
**Entrevista:** "Arquitectura modular desde día 1. Código vive acá, datos allá. Cuando onboarding un engineer nuevo, sabe exactamente dónde buscar."

---

