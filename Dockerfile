# 1. Imagen base con Python
FROM python:3.10-slim

# 2. Instalar herramientas del sistema necesarias
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. Definir carpeta de trabajo en el contenedor
WORKDIR /app

# 4. Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el código fuente
COPY src/ /app/src/

# 6. Comando ejecutor por defecto al arrancar el contenedor
CMD ["python", "src/SCRAPING.py"]