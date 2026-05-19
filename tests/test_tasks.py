import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine_test)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_test)


def test_crear_tarea_correctamente(client):
    payload = {"title": "Tarea de prueba", "description": "Descripción de ejemplo"}
    response = client.post("/tasks/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tarea de prueba"
    assert data["description"] == "Descripción de ejemplo"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


def test_listar_tareas_vacio(client):
    response = client.get("/tasks/")

    assert response.status_code == 200
    assert response.json() == []


def test_listar_tareas_con_datos(client):
    client.post("/tasks/", json={"title": "Primera tarea"})
    client.post("/tasks/", json={"title": "Segunda tarea"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2
