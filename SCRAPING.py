# -*- coding: utf-8 -*-
"""
Scraper Éxito Colombia - catálogo (todas las páginas) + detalle + sentimiento.
- Adaptado para la estructura web de Éxito (VTEX).
- Scroll y paginación para recorrer el listado.
- Perfil persistente y análisis de sentimiento con pysentimiento/nltk.
"""
import sys
import os
import subprocess
from pathlib import Path

# ==========================================
# 0. AUTOGESTIÓN DE ENTORNO
# ==========================================
BASE_DIR = Path(globals().get("__file__", "script.py")).resolve().parent
VENV_DIR = BASE_DIR / ".venv"
PERFIL = BASE_DIR / "perfil_scraper_ml"
PYTHON_VENV = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

if not os.environ.get("ML_VENV_OK"):
    if str(VENV_DIR) not in os.path.realpath(sys.executable):
        print("⚙️  [Automático] Configurando entorno virtual...", flush=True)
        if not VENV_DIR.exists():
            print("   Creando .venv local...", flush=True)
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
            print("   Instalando dependencias (pandas, selenium, nltk)...", flush=True)
            subprocess.check_call([str(PYTHON_VENV), "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([str(PYTHON_VENV), "-m", "pip", "install", "pandas", "selenium", "nltk", "pysentimiento"])
        os.environ["ML_VENV_OK"] = "1"
        print("🔄 Reiniciando dentro del entorno virtual...", flush=True)
        os.execv(str(PYTHON_VENV), [str(PYTHON_VENV)] + sys.argv)

# ==========================================
# 1. IMPORTS Y CONFIGURACIÓN
# ==========================================
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, SessionNotCreatedException,
)

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

nltk.download("vader_lexicon", quiet=True)

URL_BASE = "https://www.exito.com/tecnologia/computadores/computadores-de-escritorio-y-all-in-one"

MAX_DETALLES = 3            # productos que se abren en la fase 2
MAX_PAGINAS_SEGURIDAD = 15  # tope de seguridad contra bucles
SCROLL_PASOS = 20           # scrolls máximos por página
USAR_PERFIL = True          # reutiliza cookies/sesión
CERRAR_AL_FINAL = False     # False = espera ENTER antes de cerrar

# Selectores adaptados a la estructura típica de Éxito / VTEX
SEL_ITEMS = "article, div[class*='productCard'], div[data-fs-product-card]"
SEL_DESC = "div[data-fs-product-description], div[class*='description'], section[class*='product-description']"
SEL_RESENA = "div[class*='review'], div[class*='comment']"

SCRIPT_CATALOGO = """
const pick = (el, sels) => {
  for (const s of sels) { const n = el.querySelector(s); if (n) return n; }
  return null;
};
const items = Array.from(document.querySelectorAll(
  "article, div[class*='productCard'], div[data-fs-product-card]"
));
const out = [];
for (const el of items) {
  const tEl = pick(el, ['h3', 'h2', 'a[title]', '[class*="title"]', '[class*="name"]']);
  const priceEl = pick(el, ['[class*="price"]', '[data-fs-price]']);
  const a = pick(el, ['a[href]']);
  const texto = el.innerText || el.textContent || '';
  
  out.push({
    titulo: tEl ? (tEl.innerText || tEl.textContent || tEl.getAttribute('title') || '').trim() : '',
    precio_texto: priceEl ? (priceEl.innerText || priceEl.textContent || '').trim() : '',
    envio_gratis: /env[íi]o\\s+gratis/i.test(texto),
    patrocinado: /patrocinad|publicidad/i.test(texto),
    url: a ? (a.href.startsWith('http') ? a.href.split('?')[0] : 'https://www.exito.com' + a.href.split('?')[0]) : ''
  });
}
return out;
"""

# ==========================================
# 2. NAVEGADOR
# ==========================================
def obtener_opciones_navegador():
    options = webdriver.ChromeOptions()

    rutas = [
        os.path.expanduser("~\\AppData\\Local\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
        "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
    ]
    for ruta in rutas:
        if os.path.exists(ruta):
            options.binary_location = ruta
            break

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=es-CO")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    if USAR_PERFIL:
        try:
            PERFIL.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        options.add_argument(f"--user-data-dir={PERFIL}")

    return options


def crear_driver():
    try:
        driver = webdriver.Chrome(options=obtener_opciones_navegador())
    except SessionNotCreatedException as e:
        print("\n❌ Chrome no pudo arrancar.", flush=True)
        print("   Cierra TODAS las ventanas de Chrome/Brave y reintenta.", flush=True)
        print(f"   Perfil en uso: {PERFIL}", flush=True)
        print(f"   Detalle: {str(e)[:300]}", flush=True)
        sys.exit(1)
    driver.set_page_load_timeout(45)
    return driver


def navegar(driver, url, etiqueta=""):
    try:
        driver.get(url)
        return True
    except TimeoutException:
        print(f"⏱️  '{etiqueta}' excedió la carga; cortando y siguiendo.", flush=True)
        try:
            driver.execute_script("window.stop()")
        except WebDriverException:
            pass
        return False


def pausa_hasta_enter(motivo="Cuando termines, pulsa [ENTER] aquí"):
    print(f"\n⏸️  {motivo}", flush=True)
    try:
        input("👉 [ENTER] para continuar: ")
    except (EOFError, OSError):
        print("⚠️  Sin consola interactiva; continúo.", flush=True)

# ==========================================
# 3. UTILIDADES DE DATOS
# ==========================================
def precio_a_numero(texto):
    if not texto:
        return None
    digitos = re.sub(r"[^\d]", "", texto)
    if not digitos:
        return None
    return int(digitos)


_sia = SentimentIntensityAnalyzer()
_analizador_es = None


def cargar_analizador_es():
    global _analizador_es
    try:
        from pysentimiento import SentimentAnalyzer
        _analizador_es = SentimentAnalyzer("es")
        print("✅ Analizador en español (pysentimiento) activo.", flush=True)
    except Exception:
        print("⚠️  pysentimiento no instalado: uso VADER (inglés).", flush=True)


def analizar_sentimiento(texto):
    texto = (texto or "").strip()
    if len(texto) < 5:
        return "Sin datos", 0.0, "sin_texto"

    if _analizador_es is not None:
        try:
            r = _analizador_es.predict(texto[:1000])
            mapa = {"POS": "Positivo", "NEU": "Neutral", "NEG": "Negativo"}
            prob = max(r.probas.values()) if hasattr(r, "probas") else 0.0
            return mapa.get(r.output, r.output), round(float(prob), 3), "pysentimiento"
        except Exception:
            pass

    score = _sia.polarity_scores(texto)["compound"]
    if score >= 0.05:
        etiqueta = "Positivo"
    elif score <= -0.05:
        etiqueta = "Negativo"
    else:
        etiqueta = "Neutral"
    return etiqueta, round(score, 3), "vader"


def texto_de(driver, selectores):
    for sel in selectores.split(","):
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel.strip())
            txt = (el.text or "").strip()
            if txt:
                return txt
        except WebDriverException:
            continue
    return ""

# ==========================================
# 4. LISTADO Y SCROLL
# ==========================================
def contar_items(driver):
    return len(driver.find_elements(By.CSS_SELECTOR, SEL_ITEMS))


def cargar_todo(driver, pausa=1.0, max_pasos=SCROLL_PASOS):
    """Realiza scroll hacia abajo para activar el lazy loading de Éxito."""
    anterior, estables = -1, 0
    for _ in range(max_pasos):
        n = contar_items(driver)
        if n == anterior:
            estables += 1
            if estables >= 2:
                break
        else:
            estables = 0
        anterior = n
        driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8)")
        time.sleep(pausa)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(pausa)
    return contar_items(driver)


def extraer_catalogo(driver):
    print(f"📄 Página actual: {driver.title!r}", flush=True)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SEL_ITEMS))
        )
    except TimeoutException:
        print("⚠️  No apareció el contenedor de productos tras 20 s; intento extraer igual.", flush=True)

    filas, vistos = [], set()
    pagina = 1

    n_dom = cargar_todo(driver)
    brutos = driver.execute_script(SCRIPT_CATALOGO) or []

    for b in brutos:
        titulo = (b.get("titulo") or "").strip()
        url = (b.get("url") or "").strip()
        if not titulo or not url or url in vistos:
            continue
        vistos.add(url)

        precio_txt = b.get("precio_texto", "")
        numero = precio_a_numero(precio_txt)

        filas.append({
            "producto": titulo,
            "precio": precio_txt,
            "precio_num": numero,
            "envio_gratis": b.get("envio_gratis", False),
            "patrocinado": b.get("patrocinado", False),
            "pagina": pagina,
            "estado": "Disponible en Éxito",
            "url_detalle": url,
        })

    df = pd.DataFrame(filas)
    print(f"   Productos únicos extraídos: {len(df)}", flush=True)
    return df


def reporte_calidad(df):
    if df.empty:
        return
    total = len(df)
    print("📊 Calidad de los datos:", flush=True)
    for col in ("producto", "precio", "precio_num", "url_detalle"):
        if col not in df.columns:
            continue
        if df[col].dtype == object:
            nulos = int((df[col].fillna("") == "").sum())
        else:
            nulos = int(df[col].isna().sum())
        print(f"   {col:12s}: {total - nulos}/{total} con dato", flush=True)
    print("", flush=True)

# ==========================================
# 5. DETALLE + SENTIMIENTO
# ==========================================
def extraer_detalles(driver, df_cat):
    cargar_analizador_es()
    detalles = []
    total = min(MAX_DETALLES, len(df_cat))

    for i, (_, row) in enumerate(df_cat.head(MAX_DETALLES).iterrows(), start=1):
        print(f"🔎 Detalle {i}/{total}: {row['producto'][:45]}...", flush=True)
        navegar(driver, row["url_detalle"], "detalle")

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
            )
        except TimeoutException:
            print("   ⚠️  Título del detalle no apareció; sigo con lo que haya.", flush=True)

        descripcion = texto_de(driver, SEL_DESC)
        origen = "descripcion"
        if not descripcion:
            descripcion = texto_de(driver, SEL_RESENA)
            origen = "resena"
        if not descripcion:
            origen = "sin_texto"

        etiqueta, score, motor = analizar_sentimiento(descripcion)
        detalles.append({
            "producto": row["producto"],
            "precio": row["precio"],
            "precio_num": row["precio_num"],
            "texto_analizado": (descripcion[:300] + "...") if descripcion else "",
            "origen_texto": origen,
            "sentimiento": etiqueta,
            "score": score,
            "motor": motor,
            "url": row["url_detalle"],
        })
        print(f"   → {etiqueta} ({score}) [{motor} / {origen}]", flush=True)

    return pd.DataFrame(detalles)

# ==========================================
# 6. PROGRAMA PRINCIPAL
# ==========================================
def main():
    print("\n🚀 Iniciando el navegador para Éxito...", flush=True)
    driver = crear_driver()
    mantener_abierto = not CERRAR_AL_FINAL
    df_cat = pd.DataFrame()
    df_det = pd.DataFrame()

    try:
        print(f"🌐 Navegando al catálogo:\n   {URL_BASE}", flush=True)
        navegar(driver, URL_BASE, "listado")

        df_cat = extraer_catalogo(driver)
        reporte_calidad(df_cat)

        if df_cat.empty:
            print("\n⚠️  No se encontraron productos. Revisa la URL o estructura.", flush=True)
            mantener_abierto = True
            return

        df_det = extraer_detalles(driver, df_cat)

        df_cat.to_csv("catalogo_exito.csv", index=False, encoding="utf-8-sig")
        df_det.to_csv("detalles_sentimientos_exito.csv", index=False, encoding="utf-8-sig")

        print("=" * 60, flush=True)
        print(f"✅ Listo. {len(df_cat)} productos, {len(df_det)} analizados.", flush=True)
        if not df_det.empty:
            print(df_det[["producto", "sentimiento", "score", "motor"]].to_string(), flush=True)
        print("📁 catalogo_exito.csv / detalles_sentimientos_exito.csv", flush=True)
        print("=" * 60 + "\n", flush=True)

    except KeyboardInterrupt:
        mantener_abierto = True
        print("\n⏹️  Interrumpido con Ctrl+C. El navegador sigue abierto.", flush=True)

    except WebDriverException as e:
        mantener_abierto = True
        print(f"\n💥 Error del navegador: {e}", flush=True)

    finally:
        if mantener_abierto:
            pausa_hasta_enter("🔓 El navegador sigue abierto. ENTER para cerrarlo")
        try:
            driver.quit()
            print("🔒 Navegador cerrado.", flush=True)
        except WebDriverException:
            pass


if __name__ == "__main__":
    main()