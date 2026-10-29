"""El núcleo: tu agente y dos funciones, responder y decidir, con una memoria por persona.

Pruébalo en la terminal (sin Telegram):  uv run python asistente.py
"""

import os
import re
from pathlib import Path

import pydantic_ai
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, ConversationTypeAdapter, DeferredToolRequests
from pydantic_ai.capabilities import ProcessHistory

pydantic_ai.BANNER_ENABLED = False  # sin el aviso de Logfire en cada arranque

load_dotenv(override=True)  # .env gana a las variables de tu terminal; en Render no hay .env: usa el panel
MODELO = os.getenv("MODELO", "google:gemini-3.5-flash-lite")

if MODELO.startswith("google:"):
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Falta GEMINI_API_KEY: ponla en tu .env (en tu equipo) o en Environment (en Render).")
    os.environ.pop("GOOGLE_API_KEY", None)  # si tu terminal tuviera otra clave de Google, ganaría a la del .env
if MODELO.startswith("ollama:"):  # Ollama habla el protocolo de OpenAI en /v1
    ollama = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/").removesuffix("/v1")
    os.environ["OLLAMA_BASE_URL"] = ollama + "/v1"

from capacidades import clima, memoria, notas, tareas  # noqa: E402  (después de leer las variables)

agente = Agent(
    MODELO,
    deps_type=str,  # deps = la persona que escribe: cada una tiene su memoria y sus tareas
    # ← Cambia esto por tu caso: para quién es, qué hace y qué NO hace.
    instructions=(
        "Eres un asistente personal. Responde en español, breve y en texto plano (sin Markdown). "
        "No inventes datos: si no lo sabes o una herramienta falla, dilo."
    ),
    capabilities=[
        clima,  # S1 · una tool que lee una API abierta
        notas,  # S2 · RAG sobre datos/notas/, con citas
        memoria,  # S2 · memoria de largo plazo por persona
        tareas,  # S4 · una tool que escribe, con aprobación humana
        # ← aquí enchufas tus capabilities
        ProcessHistory(lambda mensajes: mensajes[-20:]),  # el modelo ve solo los últimos 20 mensajes
    ],
    output_type=[str, DeferredToolRequests],  # texto, o una pausa para pedir aprobación
)

CONVERSACIONES = Path(__file__).parent / "datos" / "conversaciones"


class Respuesta(BaseModel):
    texto: str
    pendiente: list[str] = []  # acciones que esperan la aprobación de la persona


def _archivo(persona: str) -> Path:
    CONVERSACIONES.mkdir(parents=True, exist_ok=True)
    return CONVERSACIONES / f"{re.sub(r'[^a-zA-Z0-9_-]', '_', persona)}.json"  # nombre de archivo seguro


def cargar(persona: str):
    """La conversación guardada de la persona, o None si es la primera vez."""
    archivo = _archivo(persona)
    return ConversationTypeAdapter.validate_json(archivo.read_bytes()) if archivo.exists() else None


def _guardar_y_responder(persona: str, r) -> Respuesta:
    _archivo(persona).write_bytes(ConversationTypeAdapter.dump_json(r.conversation))
    if isinstance(r.output, DeferredToolRequests):  # el agente quiere escribir: pide permiso
        return Respuesta(
            texto="Necesito tu aprobación para:",
            pendiente=[f"{c.tool_name}({c.args_as_dict()})" for c in r.output.approvals],
        )
    return Respuesta(texto=r.output)


async def responder(persona: str, mensaje: str) -> Respuesta:
    """Lo único que necesita el bot: quién escribe y qué dice."""
    r = await agente.run(mensaje, deps=persona, conversation=cargar(persona))
    return _guardar_y_responder(persona, r)


async def decidir(persona: str, aprobar: bool) -> Respuesta:
    """La persona aprueba (o rechaza) lo que quedó en pausa, y el agente continúa."""
    conversacion = cargar(persona)
    if conversacion is None or conversacion.deferred_tool_requests is None:
        return Respuesta(texto="No hay nada pendiente.")
    decision = conversacion.deferred_tool_requests.build_results(
        approvals={c.tool_call_id: aprobar for c in conversacion.deferred_tool_requests.approvals}
    )
    r = await agente.run(deps=persona, conversation=conversacion, deferred_tool_results=decision)
    return _guardar_y_responder(persona, r)


if __name__ == "__main__":  # conversación en la terminal: escribe /si o /no para aprobar, «salir» para terminar
    import asyncio

    async def conversar():
        persona = "yo"
        while (mensaje := input("tú> ").strip()) not in {"", "salir"}:
            if mensaje in {"/si", "/no"}:
                respuesta = await decidir(persona, aprobar=mensaje == "/si")
            else:
                respuesta = await responder(persona, mensaje)
            print("asistente>", respuesta.texto, *respuesta.pendiente, "(/si o /no)" if respuesta.pendiente else "")

    asyncio.run(conversar())  # un solo asyncio.run: todo lo async vive dentro
