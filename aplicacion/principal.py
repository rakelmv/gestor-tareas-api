from fastapi import FastAPI

from aplicacion.base_de_datos import Base, engine
from aplicacion.rutas import tareas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API de Gestión de Tareas")

app.include_router(tareas.router)
