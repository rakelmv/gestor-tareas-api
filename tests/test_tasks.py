# Tests de la API de gestión de tareas con pytest y FastAPI TestClient
#
# COBERTURA ACTUAL: solo happy path básico
#   - POST /tasks  → crear tarea correctamente
#   - GET  /tasks  → listar tareas
#
# PENDIENTE DE CUBRIR:
#   - POST /tasks con título vacío o menor de 3 caracteres (error 422)
#   - GET  /tasks/{id} con id inexistente (error 404)
#   - PATCH /tasks/{id} sobre una tarea con estado "done" (error 400)
#   - PATCH /tasks/{id} con id inexistente (error 404)
#   - DELETE /tasks/{id} con id inexistente (error 404)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

# StaticPool garantiza que todas las sesiones comparten la misma conexión en memoria;
# sin él cada sesión abriría una conexión nueva y vería una base de datos vacía distinta
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    # Sustituye la dependencia de BD real por la sesión de test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    # 1. Crear tablas en el engine de test antes de instanciar el TestClient;
    #    principal.py ya no llama create_all al importarse (usa lifespan),
    #    así que aquí tenemos control total sobre qué engine se usa
    Base.metadata.create_all(bind=engine_test)

    # 2. Sobreescribir la dependencia de BD para que todas las peticiones usen engine_test
    app.dependency_overrides[get_db] = override_get_db

    # 3. TestClient sin context manager: no dispara el lifespan de la app,
    #    evitando que el create_all de producción interfiera con engine_test
    yield TestClient(app)

    # 4. Limpieza al terminar cada test
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_test)


# ---------------------------------------------------------------------------
# Happy path: crear tarea
# ---------------------------------------------------------------------------

def test_crear_tarea_correctamente(client):
    # Verifica que una tarea válida se crea y devuelve los campos esperados
    payload = {"title": "Tarea de prueba", "description": "Descripción de ejemplo"}
    response = client.post("/tasks/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tarea de prueba"
    assert data["description"] == "Descripción de ejemplo"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


# ---------------------------------------------------------------------------
# Happy path: listar tareas
# ---------------------------------------------------------------------------

def test_listar_tareas_vacio(client):
    # Sin tareas creadas la respuesta debe ser una lista vacía
    response = client.get("/tasks/")

    assert response.status_code == 200
    assert response.json() == []


def test_listar_tareas_con_datos(client):
    # Crea dos tareas y comprueba que ambas aparecen en el listado
    client.post("/tasks/", json={"title": "Primera tarea"})
    client.post("/tasks/", json={"title": "Segunda tarea"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# TODO: casos de error — pendientes de implementar
# ---------------------------------------------------------------------------

# def test_crear_tarea_titulo_vacio(client):
#     # Debería devolver 422 cuando el título está vacío o tiene menos de 3 caracteres
#     pass

# def test_obtener_tarea_no_encontrada(client):
#     # Debería devolver 404 cuando el id no existe
#     pass

# def test_actualizar_tarea_completada(client):
#     # Debería devolver 400 cuando se intenta modificar una tarea con estado "done"
#     pass
