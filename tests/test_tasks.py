# Tests de integración para los endpoints REST de tareas

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

# Motor de base de datos en memoria compartida para los tests
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Crea las tablas antes de cada test y las elimina después."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    """Cliente HTTP de prueba vinculado a la app con la BD en memoria."""
    return TestClient(app)


# ---------- POST /tasks/ ----------

def test_create_task_minimal(client):
    """Crear tarea solo con título usa valores por defecto."""
    response = client.post("/tasks/", json={"title": "Nueva tarea"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Nueva tarea"
    assert data["description"] is None
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


def test_create_task_full(client):
    """Crear tarea con todos los campos."""
    payload = {
        "title": "Tarea completa",
        "description": "Descripción detallada",
        "status": "in_progress",
    }
    response = client.post("/tasks/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tarea completa"
    assert data["description"] == "Descripción detallada"
    assert data["status"] == "in_progress"


def test_create_task_without_title(client):
    """Crear tarea sin título devuelve 422."""
    response = client.post("/tasks/", json={})
    assert response.status_code == 422


# ---------- GET /tasks/ ----------

def test_list_tasks_empty(client):
    """Lista vacía cuando no hay tareas."""
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_with_data(client):
    """Lista devuelve las tareas creadas."""
    client.post("/tasks/", json={"title": "Tarea 1"})
    client.post("/tasks/", json={"title": "Tarea 2"})
    response = client.get("/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Tarea 1"
    assert data[1]["title"] == "Tarea 2"


# ---------- GET /tasks/{id} ----------

def test_get_task_by_id(client):
    """Obtener una tarea existente por su id."""
    create_resp = client.post("/tasks/", json={"title": "Buscar"})
    task_id = create_resp.json()["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Buscar"


def test_get_task_not_found(client):
    """Obtener tarea inexistente devuelve 404 con detalle."""
    response = client.get("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ---------- PATCH /tasks/{id} ----------

def test_update_task_title(client):
    """Actualizar solo el título de una tarea."""
    create_resp = client.post("/tasks/", json={"title": "Original"})
    task_id = create_resp.json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"title": "Modificado"})
    assert response.status_code == 200
    assert response.json()["title"] == "Modificado"


def test_update_task_status(client):
    """Cambiar el estado de una tarea a done."""
    create_resp = client.post("/tasks/", json={"title": "Pendiente"})
    task_id = create_resp.json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_update_task_description(client):
    """Añadir descripción a una tarea existente."""
    create_resp = client.post("/tasks/", json={"title": "Sin desc"})
    task_id = create_resp.json()["id"]
    response = client.patch(
        f"/tasks/{task_id}", json={"description": "Ahora con descripción"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Ahora con descripción"


def test_update_task_not_found(client):
    """Actualizar tarea inexistente devuelve 404 con detalle."""
    response = client.patch("/tasks/9999", json={"title": "Nada"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ---------- DELETE /tasks/{id} ----------

def test_delete_task(client):
    """Eliminar una tarea existente devuelve 204 y ya no aparece en la lista."""
    create_resp = client.post("/tasks/", json={"title": "Borrar"})
    task_id = create_resp.json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    # Verificar que la tarea ya no existe
    get_resp = client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 404


def test_delete_task_not_found(client):
    """Eliminar tarea inexistente devuelve 404 con detalle."""
    response = client.delete("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ---------------------------------------------------------------------------
# Regresión: POST /tasks/ — validación de longitud mínima del título
# ---------------------------------------------------------------------------


def test_create_task_title_too_short_rejected(client):
    """Un título con menos de 3 caracteres debe ser rechazado con 400."""
    response = client.post("/tasks/", json={"title": "ab"})
    assert response.status_code == 400
    assert response.json()["detail"] == "El título debe tener al menos 3 caracteres"


def test_create_task_title_only_spaces_rejected(client):
    """Un título compuesto solo por espacios se considera vacío y debe rechazarse."""
    response = client.post("/tasks/", json={"title": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "El título debe tener al menos 3 caracteres"


def test_create_task_title_empty_rejected(client):
    """Un título vacío debe ser rechazado con 400."""
    response = client.post("/tasks/", json={"title": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "El título debe tener al menos 3 caracteres"


# ---------------------------------------------------------------------------
# Regresión: PATCH /tasks/{id} — bloqueo de modificación de tareas completadas
# ---------------------------------------------------------------------------


def test_update_done_task_rejected(client):
    """Modificar una tarea ya completada debe devolver 400."""
    r = client.post("/tasks/", json={"title": "Tarea completa", "status": "done"})
    task_id = r.json()["id"]

    response = client.patch(f"/tasks/{task_id}", json={"title": "Nuevo título"})
    assert response.status_code == 400
    assert response.json()["detail"] == "No se puede modificar una tarea completada"
