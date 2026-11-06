# -*- coding: utf-8 -*-
"""
Scraper Mercado Libre Colombia - catálogo (todas las páginas) + detalle + sentimiento.
- Scroll hasta agotar el lazy loading de cada página.
- Recorre TODAS las páginas que el sitio declare (con validación al final).
- Pausa bloqueante para login manual: no navega ni cierra mientras escribes.
- Perfil persistente para no repetir el login.
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
PERFIL = BASE_DIR / "perfil_ml"
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

URL_BASE = "https://listado.mercadolibre.com.co/_Container_fs-computo-ofertas?forceContainer=true"

MAX_DETALLES = 3            # productos que se abren en la fase 2
MAX_PAGINAS_SEGURIDAD = 15  # tope de seguridad contra bucles
SCROLL_PASOS = 25           # scrolls máximos por página
USAR_PERFIL = True          # reutiliza cookies/sesión
CERRAR_AL_FINAL = False     # False = espera ENTER antes de cerrar

SEL_ITEMS = ("li.ui-search-layout__item, div.ui-search-result__wrapper, "
             "li.poly-card, div.poly-card")
SEL_DESC = ("p.ui-pdp-description__content, div.ui-pdp-description__content, "
            "div.ui-pdp-description span")
SEL_RESENA = ("p.ui-review-capability-comments__comment__content, "
              "div.ui-review-capability-comments p")

SCRIPT_CATALOGO = """
const pick = (el, sels) => {
for (const s of sels) { const n = el.querySelector(s); if (n) return n; }
return null;
};
const items = Array.from(document.querySelectorAll(
'li.ui-search-layout__item, div.ui-search-result__wrapper, li.poly-card, div.poly-card'
));
const out = [];
for (const el of items) {
const tEl = pick(el, ['h2.ui-search-item__title', 'h3.poly-component__title',
'a.poly-component__title', '.ui-search-item__title', 'h2', 'h3']);
const moneyEl = pick(el, ['.andes-money-amount']);
const frac = pick(el, ['.andes-money-amount__fraction']);
const cents = pick(el, ['.andes-money-amount__cents']);
const sym = pick(el, ['.andes-money-amount__currency-symbol']);
const a = pick(el, ['a.ui-search-link', 'a.poly-component__link',
'a.poly-component__title', 'a[href*="MLC-"]', 'a[href*="/p/MLC"]']);
const texto = el.innerText || el.textContent || '';
out.push({
titulo: tEl ? (tEl.innerText || tEl.textContent || '').trim() : '',
precio_texto: frac ? (frac.innerText || frac.textContent || '').trim() : '',
centavos: cents ? (cents.innerText || cents.textContent || '').trim() : '',
moneda: sym ? (sym.innerText || sym.textContent || '').trim() : '',
precio_aria: moneyEl ? (moneyEl.getAttribute('aria-label') || '') : '',
envio_gratis: /env[íi]o\\s+gratis/i.test(texto),
vendidos: (texto.match(/([\\d\\.]+)\\s*vendidos/i) || [''])[0],
patrocinado: /patrocinad|publicidad/i.test(texto),
url: a ? a.href.split('?')[0] : ''
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
    PERFIL.mkdir(parents=True, exist_ok=True)
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


def en_login(driver):
    try:
    u = (driver.current_url or "").lower()
except WebDriverException:
return False
claves = ("/login", "lgz/login", "account-verification", "captcha", "checkout/v3/login")
return any(k in u for k in claves)


def asegurar_sesion(driver, max_rondas=3):
    for ronda in range(max_rondas):
    if not en_login(driver):
    return True
print("\n🔐 Mercado Libre pide iniciar sesión.", flush=True)
print("   El script NO navega ni cierra nada hasta que pulses ENTER.", flush=True)
pausa_hasta_enter(f"Escribe tus datos en el navegador (ronda {ronda + 1}/{max_rondas})")
if en_login(driver):
    print("⚠️  Sigue en login. No voy a navegar ni cerrar el navegador.", flush=True)
return False
return True

# ==========================================
# 3. UTILIDADES DE DATOS
# ==========================================
def precio_a_numero(texto, centavos=""):
    if not texto:
    return None
digitos = re.sub(r"[^\d]", "", texto)
if not digitos:
    return None
valor = int(digitos)
if centavos and centavos.isdigit():
    valor += int(centavos) / 100
return valor


_sia = SentimentIntensityAnalyzer()
_analizador_es = None


def cargar_analizador_es():
    global _analizador_es
try:
    from pysentimiento import SentimentAnalyzer
_analizador_es = SentimentAnalyzer("es")
print("✅ Analizador en español (pysentimiento) activo.", flush=True)
except Exception:
print("⚠️  pysentimiento no instalado: uso VADER, que es un léxico en INGLÉS.", flush=True)
print("    Para español: pip install pysentimiento", flush=True)


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
# 4. LISTADO: SCROLL, PAGINACIÓN Y VALIDACIÓN
# ==========================================
def contar_items(driver):
    return len(driver.find_elements(By.CSS_SELECTOR, SEL_ITEMS))


def cargar_todo(driver, pausa=0.8, max_pasos=SCROLL_PASOS):
    """Baja hasta que el DOM deja de crecer (lazy loading)."""
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
driver.execute_script("window.scrollBy(0, window.innerHeight * 0.9)")
time.sleep(pausa)

driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(pausa)
return contar_items(driver)


def paginas_declaradas(driver):
    """Lee el paginador y devuelve el número de página más alto que ofrece el sitio."""
try:
    n = driver.execute_script("""
const nums = Array.from(document.querySelectorAll(
'.andes-pagination__button a, .andes-pagination__link'
)).map(a => parseInt((a.innerText || a.textContent || '').trim(), 10))
.filter(n => !isNaN(n));
return nums.length ? Math.max.apply(null, nums) : 1;
""")
return int(n or 1)
except WebDriverException:
return 1


def primer_href(driver):
    try:
    return driver.find_element(By.CSS_SELECTOR, SEL_ITEMS + " a").get_attribute("href") or ""
except WebDriverException:
return ""


def ir_a_siguiente(driver, href_previo):
    """Clic real en 'Siguiente' y espera a que cambie el primer resultado."""
selectores = ("li.andes-pagination__button--next a",
              "a.andes-pagination__link[title='Siguiente']",
              "a[aria-label='Siguiente']",
              "a.andes-pagination__link:not(.andes-pagination__link--disabled)[href*='_Desde_']")
for sel in selectores:
    try:
    boton = driver.find_element(By.CSS_SELECTOR, sel)
if not boton.is_enabled() or not boton.is_displayed():
    continue
driver.execute_script("arguments[0].scrollIntoView({block:'center'});", boton)
driver.execute_script("arguments[0].click();", boton)
WebDriverWait(driver, 25).until(
    lambda d: primer_href(d) not in ("", href_previo)
)
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, SEL_ITEMS))
)
return True
except (WebDriverException, TimeoutException):
continue
return False


def extraer_catalogo(driver):
    print(f"📄 Página actual: {driver.title!r}", flush=True)

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SEL_ITEMS))
    )
except TimeoutException:
print("⚠️  No apareció el contenedor tras 20 s; intento extraer igual.", flush=True)

filas, vistos = [], set()
hrefs_pagina = {primer_href(driver)}
total_declarado = paginas_declaradas(driver)
pagina = 1

print(f"🧭 El sitio declara {total_declarado} página(s).", flush=True)

while pagina <= MAX_PAGINAS_SEGURIDAD:
    n_dom = cargar_todo(driver)
brutos = driver.execute_script(SCRIPT_CATALOGO) or []

nuevos = 0
for b in brutos:
    titulo = (b.get("titulo") or "").strip()
url = (b.get("url") or "").strip()
if not titulo or not url or url in vistos:
    continue
vistos.add(url)
numero = precio_a_numero(b.get("precio_texto", ""), b.get("centavos", ""))
if numero is None and b.get("precio_aria"):
    numero = precio_a_numero(b["precio_aria"])
filas.append({
    "producto": titulo,
    "precio": (f"{b.get('moneda', '')}{b.get('precio_texto', '')}".strip()
               or b.get("precio_aria", "")),
    "precio_num": numero,
    "envio_gratis": b.get("envio_gratis", False),
    "vendidos": b.get("vendidos", ""),
    "patrocinado": b.get("patrocinado", False),
    "pagina": pagina,
    "estado": "Disponible en Mercado Libre",
    "url_detalle": url,
})
nuevos += 1

print(f"   Página {pagina}/{total_declarado}: {n_dom} tarjetas en DOM | "
      f"+{nuevos} nuevos | acumulado {len(filas)}", flush=True)

if pagina >= total_declarado:
    print("   ✅ Última página declarada alcanzada.", flush=True)
break

href = primer_href(driver)
if not ir_a_siguiente(driver, href):
    print("   ⛔ No se pudo avanzar: botón ausente, deshabilitado o bloqueo.", flush=True)
break

href_nuevo = primer_href(driver)
if href_nuevo in hrefs_pagina:
    print("   ⛔ La página no cambió (posible bucle). Detengo la paginación.", flush=True)
break
hrefs_pagina.add(href_nuevo)

pagina += 1
total_declarado = max(total_declarado, paginas_declaradas(driver))
asegurar_sesion(driver)

df = pd.DataFrame(filas)

print("\n" + "=" * 60, flush=True)
print("🧾 VALIDACIÓN DE COBERTURA", flush=True)
print(f"   Páginas declaradas por el sitio : {total_declarado}", flush=True)
print(f"   Páginas efectivamente recorridas: {pagina}", flush=True)
if pagina >= total_declarado:
    print("   ✅ Cobertura completa.", flush=True)
else:
print(f"   ⚠️  Faltan {total_declarado - pagina} página(s): revisa login o bloqueos.", flush=True)
print(f"   Productos únicos extraídos     : {len(df)}", flush=True)
if not df.empty:
    print(f"   Reparto por página            : {df['pagina'].value_counts().sort_index().to_dict()}",
          flush=True)
print("=" * 60 + "\n", flush=True)

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
print(f"   patrocinados : {int(df['patrocinado'].sum())}", flush=True)
print("", flush=True)


def diagnosticar_vacio(driver):
    print("\n⚠️  Cero productos. Diagnóstico:", flush=True)
try:
    html = driver.page_source
print(f"   title : {driver.title!r}", flush=True)
print(f"   url   : {driver.current_url}", flush=True)
print(f"   html  : {len(html)} caracteres", flush=True)
print(f"   muro  : {'captcha' in html.lower() or 'verific' in html.lower()}", flush=True)
driver.save_screenshot("diagnostico_ml.png")
with open("diagnostico_ml.html", "w", encoding="utf-8") as f:
    f.write(html)
print("   Guardados diagnostico_ml.png y diagnostico_ml.html", flush=True)
except WebDriverException as e:
print(f"   No pude leer la página: {e}", flush=True)

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
        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ui-pdp-title, h1"))
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
    print("\n🚀 Iniciando el navegador...", flush=True)
driver = crear_driver()
mantener_abierto = not CERRAR_AL_FINAL
df_cat = pd.DataFrame()
df_det = pd.DataFrame()

try:
    print(f"🌐 Navegando al catálogo:\n   {URL_BASE}", flush=True)
navegar(driver, URL_BASE, "listado")

if not asegurar_sesion(driver):
    mantener_abierto = True
print("\n🛑 Abortado: sigue la pantalla de login.", flush=True)
return

df_cat = extraer_catalogo(driver)
reporte_calidad(df_cat)

if df_cat.empty:
    diagnosticar_vacio(driver)
mantener_abierto = True
return

df_det = extraer_detalles(driver, df_cat)

df_cat.to_csv("catalogo_mercadolibre.csv", index=False, encoding="utf-8-sig")
df_det.to_csv("detalles_sentimientos_mercadolibre.csv", index=False, encoding="utf-8-sig")

print("=" * 60, flush=True)
print(f"✅ Listo. {len(df_cat)} productos, {len(df_det)} analizados.", flush=True)
if not df_det.empty:
    print(df_det[["producto", "sentimiento", "score", "motor"]].to_string(), flush=True)
print("📁 catalogo_mercadolibre.csv / detalles_sentimientos_mercadolibre.csv", flush=True)
print("=" * 60, flush=True)

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
