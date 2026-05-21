from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_task_short_title_returns_422():
    response = client.post("/tasks/", json={"title": "ab"})
    assert response.status_code == 422


def test_patch_done_task_returns_400():
    response = client.post("/tasks/", json={"title": "Test task", "status": "done"})
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(f"/tasks/{task_id}", json={"title": "Updated"})
    assert response.status_code == 400
