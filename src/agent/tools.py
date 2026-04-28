import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import config
from langchain_core.tools import tool

from storage.conversations import close_conversation as _close_conversation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClickUpError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message

def _headers() -> dict:
    token = config.CLICK_UP_API_TOKEN
    if not token:
        raise ClickUpError("No tengo configurado el token de ClickUp.")
    return {"Authorization": token}


def _base_url() -> str:
    base_url = config.CLICK_UP_BASE_URL
    if not base_url:
        raise ClickUpError("No tengo configurado el base URL de ClickUp.")
    return base_url.rstrip("/")


def _resolve_list_id(list_id: Optional[str]) -> str:
    resolved = list_id or config.CLICKUP_LIST_ID
    if not resolved:
        raise ClickUpError("No tengo configurado el list id de ClickUp.")
    return resolved


def _parse_due_date(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        try:
            parsed = datetime.fromisoformat(stripped)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            raise ClickUpError(
                "Formato de fecha invalido. Usa ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)."
            )

    raise ClickUpError("Formato de fecha invalido.")

def _request(method: str, endpoint: str, **kwargs) -> dict:
    url = f"{_base_url()}{endpoint}"
    headers = _headers()
    try:
        response = httpx.request(method, url, headers=headers, timeout=15.0, **kwargs)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()
    except httpx.TimeoutException:
        raise ClickUpError("ClickUp tardó demasiado en responder.")
    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error ClickUp: %s - %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise ClickUpError("ClickUp respondió con un error. Intenta de nuevo.")
    except httpx.RequestError as exc:
        logger.error(f"Network error ClickUp: {exc}")
        raise ClickUpError("No pude comunicarme con ClickUp en este momento.")
    except ValueError:
        raise ClickUpError("Respuesta invalida de ClickUp.")
@tool
def get_tasks() -> str:
    """Fetch tasks from ClickUp."""
    try:
        list_id = _resolve_list_id(None)
        response = _request("GET", f"/list/{list_id}/task")
        tasks = response.get("tasks", [])
        result = [f"[task id:{t['id']}] task name: {t['name']} — status: {t['status']['status']}" for t in tasks]

        logger.info(f"Tasks retrieved successfully: {len(tasks)} tasks found.")
        logger.info(f"Tasks details: {result}")
        if not result:
            return "Dile a johan que no se encontraron tareas en click up."
        return "\n".join(result)
    except ClickUpError as exc:
        return exc.user_message
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return "Hubo un error al tratar de obtener las tareas."


@tool
def create_task(
    name: str,
    description: str = "",
    due_date: Optional[str] = None,
    priority: Optional[int] = None,
    list_id: Optional[str] = None,
) -> str:
    """Crea una nueva tarea en ClickUp con el nombre y descripción indicados.
    Úsala cuando el usuario quiera agregar, crear o registrar una nueva tarea."""
    try:
        resolved_list_id = _resolve_list_id(list_id)
        body = {"name": name, "description": description}
        parsed_due_date = _parse_due_date(due_date)
        if parsed_due_date is not None:
            body["due_date"] = parsed_due_date
        if priority is not None:
            if priority not in {1, 2, 3, 4}:
                raise ClickUpError("La prioridad debe ser 1, 2, 3 o 4.")
            body["priority"] = priority

        response = _request("POST", f"/list/{resolved_list_id}/task", json=body)
        task_id = response.get("id")
        logger.info(f"Task created successfully. ID: {task_id}, Name: {name}")
        return f"Tarea creada exitosamente. ID: {task_id}, Nombre: {name}"
    except ClickUpError as exc:
        return exc.user_message
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return "Hubo un error al tratar de crear la tarea."


@tool
def update_task(
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[int] = None,
) -> str:
    """Actualiza una tarea existente en ClickUp. Puede cambiar el nombre, la descripción
    y/o el estado (valores válidos: 'Open', 'in progress', 'complete').
    Úsala cuando el usuario quiera modificar, renombrar, completar o cambiar el estado
    de una tarea. El task_id se obtiene primero con get_tasks."""
    try:
        body = {
            k: v
            for k, v in {"name": name, "description": description, "status": status}.items()
            if v is not None and v != ""
        }
        parsed_due_date = _parse_due_date(due_date)
        if parsed_due_date is not None:
            body["due_date"] = parsed_due_date
        if priority is not None:
            if priority not in {1, 2, 3, 4}:
                raise ClickUpError("La prioridad debe ser 1, 2, 3 o 4.")
            body["priority"] = priority

        if not body:
            return "No recibí cambios para aplicar en la tarea."

        _request("PUT", f"/task/{task_id}", json=body)
        return f"Tarea {task_id} actualizada exitosamente."
    except ClickUpError as exc:
        return exc.user_message
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return "Error tratando de actualizar la tarea."

@tool
def get_task_details(task_id: str) -> str:
    """Obtiene toda la información detallada de una tarea específica en ClickUp, 
    incluyendo su descripción completa, etiquetas y subtareas.
    Úsala cuando necesites entender el contexto profundo de una tarea antes de modificarla."""
    try:
        response = _request("GET", f"/task/{task_id}")
        desc = response.get("description") or "Sin descripción"
        tags = [tag.get("name") for tag in response.get("tags", []) if tag.get("name")]
        logger.info(f"Task details retrieved successfully. ID: {task_id}, Name: {response.get('name')}")
        return f"Tarea {task_id}: {response.get('name')}\nDescripción: {desc}\nEtiquetas: {', '.join(tags) if tags else 'Ninguna'}"
    except ClickUpError as exc:
        return exc.user_message
    except Exception as e:
        logger.error(f"Error fetching task details: {e}")
        return "Error tratando de obtener los detalles de la tarea."


@tool
def delete_task(task_id: str) -> str:
    """Usa esta tool para eliminar una tarea en clickup, siempre deberas pasar el task id , sino lo conoces
    primero debes usar get_tasks para obtener el id de la tarea que quieres eliminar.
    """
    try:
        logger.info(f"Attempting to delete task. ID: {task_id}")

        _request("DELETE", f"/task/{task_id}")
        logger.info(f"Task deleted successfully. ID: {task_id}")
        return f"Tarea {task_id} eliminada exitosamente."
    except ClickUpError as exc:
        return exc.user_message
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return "Error tratando de eliminar la tarea."


@tool
def close_conversation_tool(conversation_id: str, reason: str = "") -> str:
    """Cierra una conversacion activa cuando el usuario se despide o confirma que no necesita mas ayuda."""
    try:
        _close_conversation(conversation_id, reason or None)
        return "Conversacion cerrada."
    except Exception as exc:
        logger.error(f"Error cerrando conversacion: {exc}")
        return "No pude cerrar la conversacion en este momento."

# Register all available tools
tools = [
    get_tasks,
    create_task,
    update_task,
    get_task_details,
    delete_task,
    close_conversation_tool,
]
