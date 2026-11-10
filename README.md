# Pipeline DevOps para Extracción y Análisis de Datos (Éxito Colombia)

##  Descripción del Proyecto

Este proyecto es una evolución de un script de Web Scraping y análisis de sentimientos en Python, integrado con prácticas de **DevOps, Control de Versiones y Automatización**, mediante Git, GitHub y GitHub Actions.

---

##  Fases del Ciclo de Vida Implementadas (DevOps)

### 1. Control de Versiones (Git y GitHub)

- Gestión de ramas y control de cambios del script de extracción (`src/SCRAPING.py`).
- Configuración de `.gitignore` para evitar subir entornos virtuales (`.venv/`), cachés y archivos locales.

### 2. Integración Continua (CI) - GitHub Actions

- Automatización mediante el archivo YAML (`.github/workflows/pipeline.yml`).
- Uso de **Jobs, Steps y Estrategia de Matrices** para ejecutar y validar el proyecto en Python 3.10 y 3.11.
- Ejecución automatizada de pruebas, validación de sintaxis y ejecución del scraper.

### 3. Pruebas Automatizadas

- Implementación de pruebas con `pytest` para verificar la conversión de precios y el reporte de calidad de datos.
- Ejecución de las pruebas dentro del pipeline de integración continua.

### 4. Contenerización (Docker)

- Creación de un `Dockerfile` basado en imágenes de Python para definir el entorno de ejecución y preparar el empaquetamiento del proyecto con sus dependencias.

### 5. Monitoreo y Diagnóstico

- Generación de archivos CSV con los datos extraídos del catálogo de Éxito y el análisis de sentimientos.
- Almacenamiento de resultados como artefactos descargables de GitHub Actions para facilitar su consulta y revisión.

---

##  Instrucciones de Ejecución Local

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/Fercho9612/SCRAPING.git
   cd SCRAPING
   ```

2. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar el scraper:

   ```bash
   python src/SCRAPING.py
   ```

4. Ejecutar las pruebas:

   ```bash
   python -m pytest tests -vv
   ```