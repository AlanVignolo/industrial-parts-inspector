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

