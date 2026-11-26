import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import app as api  # noqa: E402


@pytest.fixture
def cliente():
    return api.app.test_client()


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_home_lista_endpoints(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "/resumen" in r.get_json()["endpoints"]


def test_resumen_con_datos(cliente, tmp_path, monkeypatch):
    cat = tmp_path / "catalogo.csv"
    det = tmp_path / "detalles.csv"
    cat.write_text("nombre,precio_num\nA,1000000\nB,2000000\nC,texto\n", encoding="utf-8")
    det.write_text("nombre,sentimiento\nA,positivo\nB,negativo\nC,positivo\n", encoding="utf-8")
    monkeypatch.setattr(api, "CATALOGO", cat)
    monkeypatch.setattr(api, "DETALLES", det)

    r = cliente.get("/resumen")
    datos = r.get_json()
    assert r.status_code == 200
    assert datos["total_productos"] == 3
    assert datos["precio_min"] == 1000000
    assert datos["precio_max"] == 2000000
    assert datos["sentimientos"]["positivo"] == 2


def test_resumen_sin_archivo(cliente, tmp_path, monkeypatch):
    monkeypatch.setattr(api, "CATALOGO", tmp_path / "no_existe.csv")
    r = cliente.get("/resumen")
    assert r.status_code == 404