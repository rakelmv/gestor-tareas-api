# Tests para la API de gestión de tareas

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from aplicacion.base_de_datos import Base, get_db
from aplicacion.modelos import Task, TaskStatus
from aplicacion.principal import app

# Motor en memoria compartido para toda la suite de tests
engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_test
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Fixture reutilizable: crea las tablas antes de cada test y las destruye después
import pytest


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /tasks/ — lista de tareas
# ---------------------------------------------------------------------------


class TestListTasks:
    def test_list_tasks_empty(self, client):
        response = client.get("/tasks/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tasks_multiple(self, client):
        client.post("/tasks/", json={"title": "A"})
        client.post("/tasks/", json={"title": "B"})
        response = client.get("/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"A", "B"}


# ---------------------------------------------------------------------------
# GET /tasks/{task_id} — obtener una tarea
# ---------------------------------------------------------------------------


class TestGetTask:
    def test_get_task_not_found(self, client):
        response = client.get("/tasks/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_get_task_not_found_zero_id(self, client):
        response = client.get("/tasks/0")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_get_task_not_found_negative_id(self, client):
        response = client.get("/tasks/-1")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_get_task_invalid_id_type(self, client):
        response = client.get("/tasks/abc")
        assert response.status_code == 422

    def test_get_task_success(self, client):
        created = client.post("/tasks/", json={"title": "Mi tarea"}).json()
        response = client.get(f"/tasks/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Mi tarea"


# ---------------------------------------------------------------------------
# POST /tasks/ — crear tarea
# ---------------------------------------------------------------------------


class TestCreateTask:
    def test_create_task_minimal(self, client):
        response = client.post("/tasks/", json={"title": "Solo titulo"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Solo titulo"
        assert data["description"] is None
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    def test_create_task_all_fields(self, client):
        payload = {
            "title": "Completa",
            "description": "Desc",
            "status": "in_progress",
        }
        response = client.post("/tasks/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Completa"
        assert data["description"] == "Desc"
        assert data["status"] == "in_progress"

    def test_create_task_status_done(self, client):
        response = client.post(
            "/tasks/", json={"title": "Done", "status": "done"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "done"

    def test_create_task_missing_title(self, client):
        response = client.post("/tasks/", json={})
        assert response.status_code == 422

    def test_create_task_null_title(self, client):
        response = client.post("/tasks/", json={"title": None})
        assert response.status_code == 422

    def test_create_task_invalid_status(self, client):
        response = client.post(
            "/tasks/", json={"title": "T", "status": "invalid"}
        )
        assert response.status_code == 422

    def test_create_task_empty_body(self, client):
        response = client.post(
            "/tasks/",
            content="",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_create_task_invalid_json(self, client):
        response = client.post(
            "/tasks/",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_create_task_extra_fields_ignored(self, client):
        response = client.post(
            "/tasks/", json={"title": "T", "extra": "val"}
        )
        assert response.status_code == 201
        assert "extra" not in response.json()

    def test_create_task_empty_description(self, client):
        response = client.post(
            "/tasks/", json={"title": "T", "description": ""}
        )
        assert response.status_code == 201
        assert response.json()["description"] == ""

    def test_create_task_created_at_format(self, client):
        response = client.post("/tasks/", json={"title": "T"})
        data = response.json()
        dt = datetime.fromisoformat(data["created_at"])
        assert isinstance(dt, datetime)

    def test_create_task_ids_increment(self, client):
        r1 = client.post("/tasks/", json={"title": "A"})
        r2 = client.post("/tasks/", json={"title": "B"})
        assert r2.json()["id"] > r1.json()["id"]


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id} — actualizar tarea
# ---------------------------------------------------------------------------


class TestUpdateTask:
    def test_update_task_not_found(self, client):
        response = client.patch("/tasks/9999", json={"title": "X"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_update_task_not_found_zero_id(self, client):
        response = client.patch("/tasks/0", json={"title": "X"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_update_task_invalid_id_type(self, client):
        response = client.patch("/tasks/abc", json={"title": "X"})
        assert response.status_code == 422

    def test_update_task_title_only(self, client):
        created = client.post("/tasks/", json={"title": "Orig"}).json()
        response = client.patch(
            f"/tasks/{created['id']}", json={"title": "Nuevo"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Nuevo"
        assert data["description"] is None
        assert data["status"] == "pending"

    def test_update_task_description_only(self, client):
        created = client.post(
            "/tasks/", json={"title": "T", "description": "Orig"}
        ).json()
        response = client.patch(
            f"/tasks/{created['id']}", json={"description": "Nueva desc"}
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Nueva desc"
        assert response.json()["title"] == "T"

    def test_update_task_status_only(self, client):
        created = client.post("/tasks/", json={"title": "T"}).json()
        response = client.patch(
            f"/tasks/{created['id']}", json={"status": "done"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_update_task_multiple_fields(self, client):
        created = client.post("/tasks/", json={"title": "T"}).json()
        response = client.patch(
            f"/tasks/{created['id']}",
            json={"title": "New", "status": "in_progress", "description": "D"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New"
        assert data["status"] == "in_progress"
        assert data["description"] == "D"

    def test_update_task_empty_body(self, client):
        created = client.post("/tasks/", json={"title": "T"}).json()
        response = client.patch(f"/tasks/{created['id']}", json={})
        assert response.status_code == 200
        assert response.json()["title"] == "T"

    def test_update_task_invalid_status(self, client):
        created = client.post("/tasks/", json={"title": "T"}).json()
        response = client.patch(
            f"/tasks/{created['id']}", json={"status": "bad"}
        )
        assert response.status_code == 422

    def test_update_task_set_description_to_none(self, client):
        created = client.post(
            "/tasks/", json={"title": "T", "description": "D"}
        ).json()
        response = client.patch(
            f"/tasks/{created['id']}", json={"description": None}
        )
        assert response.status_code == 200
        assert response.json()["description"] is None

    def test_update_task_preserves_created_at(self, client):
        created = client.post("/tasks/", json={"title": "T"}).json()
        updated = client.patch(
            f"/tasks/{created['id']}", json={"title": "New"}
        ).json()
        assert created["created_at"] == updated["created_at"]


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id} — eliminar tarea
# ---------------------------------------------------------------------------


class TestDeleteTask:
    def test_delete_task_not_found(self, client):
        response = client.delete("/tasks/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_delete_task_not_found_zero_id(self, client):
        response = client.delete("/tasks/0")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_delete_task_invalid_id_type(self, client):
        response = client.delete("/tasks/abc")
        assert response.status_code == 422

    def test_delete_task_success(self, client):
        created = client.post("/tasks/", json={"title": "Borrar"}).json()
        response = client.delete(f"/tasks/{created['id']}")
        assert response.status_code == 204
        assert response.content == b""

    def test_delete_task_double_delete(self, client):
        created = client.post("/tasks/", json={"title": "Borrar"}).json()
        client.delete(f"/tasks/{created['id']}")
        response = client.delete(f"/tasks/{created['id']}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_delete_task_then_get(self, client):
        created = client.post("/tasks/", json={"title": "Borrar"}).json()
        client.delete(f"/tasks/{created['id']}")
        response = client.get(f"/tasks/{created['id']}")
        assert response.status_code == 404

    def test_delete_task_does_not_affect_others(self, client):
        r1 = client.post("/tasks/", json={"title": "Keep"}).json()
        r2 = client.post("/tasks/", json={"title": "Remove"}).json()
        client.delete(f"/tasks/{r2['id']}")
        remaining = client.get("/tasks/").json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == r1["id"]


# ---------------------------------------------------------------------------
# Modelos y esquemas — cobertura directa
# ---------------------------------------------------------------------------


class TestModels:
    def test_task_status_enum_values(self):
        assert TaskStatus.pending.value == "pending"
        assert TaskStatus.in_progress.value == "in_progress"
        assert TaskStatus.done.value == "done"

    def test_task_status_is_str(self):
        assert isinstance(TaskStatus.pending, str)

    def test_task_status_enum_members(self):
        members = list(TaskStatus)
        assert len(members) == 3

    def test_task_model_tablename(self):
        assert Task.__tablename__ == "tasks"

    def test_task_model_default_status(self):
        db = TestingSessionLocal()
        try:
            task = Task(title="Test default")
            db.add(task)
            db.commit()
            db.refresh(task)
            assert task.status == TaskStatus.pending
            assert task.created_at is not None
            assert task.id is not None
        finally:
            db.close()


class TestGetDbDependency:
    def test_get_db_yields_and_closes(self):
        from aplicacion.base_de_datos import get_db as real_get_db

        gen = real_get_db()
        session = next(gen)
        assert session is not None
        try:
            gen.send(None)
        except StopIteration:
            pass
