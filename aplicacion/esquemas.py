# Esquemas Pydantic para validación de datos de entrada y serialización de respuestas

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from aplicacion.modelos import TaskStatus


# Esquema para crear una nueva tarea; solo el título es obligatorio
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.pending


# Esquema para actualizar una tarea; todos los campos son opcionales (PATCH parcial)
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


# Esquema de respuesta que devuelve la API; incluye los campos generados por la BD
class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    created_at: datetime

    # from_attributes permite construir el esquema desde un objeto ORM de SQLAlchemy
    model_config = {"from_attributes": True}
