from fastapi.testclient import TestClient
from app.main import app

# Sans "with", TestClient ne lance pas le démarrage (pas de connexion à la base)
client = TestClient(app)
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
def test_create_sans_titre_est_refuse():
    r = client.post("/api/todos", json={})
    assert r.status_code == 422 # rejeté par Pydantic avant tout accès à la base