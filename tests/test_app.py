import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app import app  # noqa: E402


def test_home_activo():
    r = app.test_client().get("/")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "activo"


def test_health_ok():
    r = app.test_client().get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"