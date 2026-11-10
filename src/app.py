# -*- coding: utf-8 -*-
"""
API web ligera para publicar los resultados del scraper de Éxito Colombia.
No ejecuta Selenium: sirve los CSV que genera el pipeline (data/).
"""
import os
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, send_file

# src/app.py -> la raíz del proyecto es el nivel superior (igual que SCRAPING.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))

CATALOGO = DATA_DIR / "catalogo_exito.csv"
DETALLES = DATA_DIR / "detalles_sentimientos_exito.csv"

app = Flask(__name__)
app.json.ensure_ascii = False  # respeta tildes y ñ en el JSON


def _leer(ruta):
    return pd.read_csv(ruta, encoding="utf-8-sig") if ruta.exists() else None


@app.route("/")
def home():
    return jsonify({
        "proyecto": "Scraping de computadores - Éxito Colombia",
        "estado": "activo",
        "endpoints": ["/health", "/resumen", "/catalogo.csv", "/detalles.csv"],
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "catalogo_disponible": CATALOGO.exists(),
        "detalles_disponible": DETALLES.exists(),
    })


@app.route("/resumen")
def resumen():
    cat = _leer(CATALOGO)
    if cat is None:
        return jsonify({"error": "catalogo_exito.csv aún no está disponible"}), 404

    salida = {"total_productos": int(len(cat))}
    precios = cat["precio_num"].dropna() if "precio_num" in cat.columns else []
    if len(precios) > 0:
        salida["precio_min"] = int(precios.min())
        salida["precio_max"] = int(precios.max())
        salida["precio_promedio"] = int(round(precios.mean()))

    det = _leer(DETALLES)
    if det is not None and "sentimiento" in det.columns:
        conteo = det["sentimiento"].value_counts()
        salida["sentimientos"] = {str(k): int(v) for k, v in conteo.items()}
        salida["productos_analizados"] = int(len(det))
    return jsonify(salida)


@app.route("/catalogo.csv")
def catalogo():
    if not CATALOGO.exists():
        return jsonify({"error": "CSV aún no generado"}), 404
    return send_file(CATALOGO, mimetype="text/csv", download_name="catalogo_exito.csv")


@app.route("/detalles.csv")
def detalles():
    if not DETALLES.exists():
        return jsonify({"error": "CSV aún no generado"}), 404
    return send_file(DETALLES, mimetype="text/csv", download_name="detalles_sentimientos_exito.csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))