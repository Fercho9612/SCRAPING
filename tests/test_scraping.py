
import sys
from pathlib import Path

import pandas as pd

# Permite importar el scraper desde la carpeta src
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from SCRAPING import precio_a_numero, reporte_calidad


def test_precio_a_numero():
    assert precio_a_numero("$ 2.499.900") == 2499900
    assert precio_a_numero("$ 850.000") == 850000
    assert precio_a_numero("") is None
    assert precio_a_numero("Sin precio") is None


def test_reporte_calidad():
    datos = pd.DataFrame({
        "producto": ["Portátil HP", ""],
        "precio": ["$ 2.500.000", "$ 3.000.000"],
        "precio_num": [2500000, 3000000],
        "url_detalle": ["https://ejemplo.com/1", ""]
    })

    # La función debe ejecutarse sin errores
    reporte_calidad(datos)
