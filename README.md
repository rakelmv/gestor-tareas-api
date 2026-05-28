# API de Gestión de Tareas

API REST para gestionar el ciclo de vida de tareas, construida con **FastAPI** y **SQLAlchemy**. Permite crear, consultar, actualizar parcialmente y eliminar tareas. Cada tarea cuenta con un identificador único, título, descripción opcional, estado (`pending`, `in_progress`, `done`) y fecha de creación asignada automáticamente.

## Requisitos previos

| Requisito | Versión mínima |
|---|---|
| Python | 3.12+ |
| pip | incluido con Python |

### Dependencias principales

| Paquete | Versión | Propósito |
|---|---|---|
| FastAPI | 0.136.1 | Framework web asíncrono |
| SQLAlchemy | 2.0.49 | ORM para acceso a datos |
| Pydantic | 2.13.4 | Validación de datos |
| Uvicorn | 0.46.0 | Servidor ASGI |
| pytest | 9.0.3 | Framework de tests |
| httpx | 0.28.1 | Cliente HTTP para tests |

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/rakelmv/gestor-tareas-api.git
   cd gestor-tareas-api
   ```

2. Crear y activar un entorno virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
   ```

3. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

## Cómo arrancar la aplicación

```bash
uvicorn aplicacion.principal:app --reload
```

La API quedará disponible en `http://127.0.0.1:8000`.
La documentación interactiva (Swagger UI) se genera automáticamente en `http://127.0.0.1:8000/docs`.

## Endpoints

Todos los endpoints se sirven bajo el prefijo `/tasks`.

### 1. Listar todas las tareas

| | |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/tasks/` |
| **Parámetros** | Ninguno |

**Ejemplo de petición:**

```bash
curl http://127.0.0.1:8000/tasks/
```

**Ejemplo de respuesta** (`200 OK`):

```json
[
  {
    "id": 1,
    "title": "Revisar pull request",
    "description": "Revisar los cambios del PR #10",
    "status": "pending",
    "created_at": "2026-05-28T14:00:00"
  }
]
```

---

### 2. Obtener una tarea por id

| | |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (int) — identificador de la tarea |

**Ejemplo de petición:**

```bash
curl http://127.0.0.1:8000/tasks/1
```

**Ejemplo de respuesta** (`200 OK`):

```json
{
  "id": 1,
  "title": "Revisar pull request",
  "description": "Revisar los cambios del PR #10",
  "status": "pending",
  "created_at": "2026-05-28T14:00:00"
}
```

**Error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

---

### 3. Crear una nueva tarea

| | |
|---|---|
| **Método** | `POST` |
| **Ruta** | `/tasks/` |
| **Cuerpo (JSON)** | `title` (str, obligatorio), `description` (str, opcional), `status` (str, opcional — por defecto `"pending"`) |

Valores válidos para `status`: `pending`, `in_progress`, `done`.

**Ejemplo de petición:**

```bash
curl -X POST http://127.0.0.1:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Escribir documentación", "description": "Redactar el README del proyecto"}'
```

**Ejemplo de respuesta** (`201 Created`):

```json
{
  "id": 2,
  "title": "Escribir documentación",
  "description": "Redactar el README del proyecto",
  "status": "pending",
  "created_at": "2026-05-28T14:05:00"
}
```

---

### 4. Actualizar parcialmente una tarea

| | |
|---|---|
| **Método** | `PATCH` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (int) — identificador de la tarea |
| **Cuerpo (JSON)** | `title` (str, opcional), `description` (str, opcional), `status` (str, opcional) |

Solo se actualizan los campos incluidos en el cuerpo de la petición.

**Ejemplo de petición:**

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/2 \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Ejemplo de respuesta** (`200 OK`):

```json
{
  "id": 2,
  "title": "Escribir documentación",
  "description": "Redactar el README del proyecto",
  "status": "in_progress",
  "created_at": "2026-05-28T14:05:00"
}
```

**Error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

---

### 5. Eliminar una tarea

| | |
|---|---|
| **Método** | `DELETE` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (int) — identificador de la tarea |

**Ejemplo de petición:**

```bash
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

**Respuesta** (`204 No Content`): sin cuerpo.

**Error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

## Cómo ejecutar los tests

```bash
pytest tests/ -v
```

Los tests utilizan una base de datos SQLite en memoria con `StaticPool` para garantizar aislamiento entre casos. No afectan al archivo `tareas.db` de producción.

## Estructura del proyecto

```
gestor-tareas-api/
├── aplicacion/                  # Código fuente de la aplicación
│   ├── principal.py             # Punto de entrada: instancia FastAPI y registro de routers
│   ├── base_de_datos.py         # Configuración del engine y sesión de SQLAlchemy
│   ├── modelos.py               # Modelos ORM (tabla tasks, enum TaskStatus)
│   ├── esquemas.py              # Esquemas Pydantic de entrada y respuesta
│   └── rutas/                   # Endpoints REST organizados por recurso
│       └── tareas.py            # CRUD de tareas
├── tests/                       # Suite de tests automatizados
│   └── test_tasks.py            # Tests de los endpoints de tareas
├── requirements.txt             # Dependencias del proyecto
├── AGENTS.md                    # Instrucciones y convenciones para colaboradores
└── .gitignore
```
