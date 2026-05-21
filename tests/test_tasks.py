# Tests para los endpoints de tareas

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

# Motor SQLite en memoria compartido entre hilos del test
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client():
    """Crea las tablas, inyecta la sesión de test y las elimina al terminar."""
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ── GET /tasks/status/{status} ──────────────────────────────────────────────


def test_list_tasks_by_status_returns_matching_tasks(client):
    """Happy path: devuelve solo las tareas con el estado solicitado."""
    client.post("/tasks/", json={"title": "Tarea pendiente"})
    client.post(
        "/tasks/",
        json={"title": "Tarea en progreso", "status": "in_progress"},
    )
    client.post("/tasks/", json={"title": "Otra pendiente"})

    response = client.get("/tasks/status/pending")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(t["status"] == "pending" for t in data)


def test_list_tasks_by_status_returns_empty_when_no_match(client):
    """Happy path: devuelve lista vacía si no hay tareas con ese estado."""
    client.post("/tasks/", json={"title": "Solo pendiente"})

    response = client.get("/tasks/status/done")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_by_status_invalid_status_returns_422(client):
    """Caso de error: un estado inválido devuelve 422."""
    response = client.get("/tasks/status/invalid_status")

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
