# Pipeline DevOps para Extracción y Análisis de Datos (Mercado Libre)

## 📌 Descripción del Proyecto
Este proyecto es una evolución de la **Unidad 1** (script de Web Scraping y análisis de sentimiento en Python) integrado con prácticas de **DevOps, Control de Versiones y Automatización (Unidades 2 y 3)**.

---

## 🚀 Fases del Ciclo de Vida Implementadas (DevOps)

### 1. Control de Versiones (Git y GitHub)
* Gestión de ramas y control de cambios del script de extracción (`SCRAPING_EA1.py`).
* Configuración de `.gitignore` para proteger credenciales y evitar subir entornos virtuales (`.venv/`) o datos locales (`perfil_ml/`).

### 2. Integración Continua (CI) - GitHub Actions
* Automatización mediante YAML (`.github/workflows/pipeline.yml`).
* Uso de **Jobs, Steps y Estrategia de Matrices** para validar la compilación del script en múltiples versiones de Python (3.10 y 3.11) de forma paralela.

### 3. Contenerización (Docker)
* Creación de un `Dockerfile` basado en imágenes ligeras de Python para empaquetar el script junto a sus dependencias, asegurando portabilidad (*"funciona en cualquier entorno"*).

### 4. Monitoreo y Diagnóstico
* El script cuenta con funciones nativas de respaldo de artefactos (`diagnostico_ml.png` y archivos CSV) integradas en el pipeline para la trazabilidad de errores ante bloqueos o cambios en el DOM de la plataforma web.

---

## 🛠️ Instrucciones de Ejecución Local

1. Clonar el repositorio:
   ```bash
   git clone <url-del-repositorio>
   cd mi-proyecto-scraping