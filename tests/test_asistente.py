"""Pruebas sin modelo real ni internet: uv run pytest

Un modelo falso (FunctionModel) pide las tools que queremos, y comprobamos lo que hace el código:
la memoria va a la persona correcta (deps) y nada se escribe sin aprobación.
"""

import os
from types import SimpleNamespace

os.environ.setdefault("GEMINI_API_KEY", "clave-de-prueba")  # para importar sin .env (no se llama a Gemini)
os.environ.setdefault("TELEGRAM_TOKEN", "123:token-de-prueba")

import asistente  # noqa: E402
import bot  # noqa: E402
import capacidades  # noqa: E402
import pytest  # noqa: E402
from pydantic_ai import ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402


@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    """Cada prueba escribe en una carpeta temporal, no en datos/."""
    monkeypatch.setattr(capacidades, "DATOS", tmp_path)
    monkeypatch.setattr(asistente, "CONVERSACIONES", tmp_path / "conversaciones")


def pide(tool: str, args: dict) -> FunctionModel:
    """Un modelo falso: la 1.ª vez pide la tool; cuando recibe su resultado, responde texto."""

    def responder(mensajes, info):
        if isinstance(mensajes[-1].parts[-1], ToolReturnPart):
            return ModelResponse(parts=[TextPart("Listo.")])
        return ModelResponse(parts=[ToolCallPart(tool, args)])

    return FunctionModel(responder)


async def test_recordar_guarda_en_la_persona_de_deps(tmp_path):
    with asistente.agente.override(model=pide("recordar", {"dato": "Es vegetariana"})):
        r = await asistente.responder("ana", "Recuerda que soy vegetariana.")
    assert r.texto == "Listo."
    assert (tmp_path / "recuerdos" / "ana.txt").read_text(encoding="utf-8") == "Es vegetariana\n"
    assert not (tmp_path / "recuerdos" / "beto.txt").exists()


async def test_crear_tarea_espera_aprobacion(tmp_path):
    tarea = tmp_path / "tareas" / "ana.txt"
    with asistente.agente.override(model=pide("crear_tarea", {"titulo": "Estudiar", "fecha": "2030-05-20"})):
        r = await asistente.responder("ana", "Anota estudiar el 20 de mayo.")
        assert r.pendiente and "crear_tarea" in r.pendiente[0]
        assert not tarea.exists()  # el modelo la pidió, pero no se escribió nada

        r = await asistente.decidir("ana", aprobar=False)
        assert not tarea.exists()  # rechazada: sigue sin escribirse

        await asistente.responder("ana", "Anótala de nuevo.")
        await asistente.decidir("ana", aprobar=True)
    assert tarea.read_text(encoding="utf-8") == "2030-05-20 · Estudiar\n"


async def test_decidir_sin_nada_pendiente():
    r = await asistente.decidir("nadie", aprobar=True)
    assert r.texto == "No hay nada pendiente."


async def test_chat_ajeno_se_rechaza_sin_llamar_al_modelo(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PERMITIDOS", "123")
    respuestas = []

    async def reply_text(texto):
        respuestas.append(texto)

    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=999), message=SimpleNamespace(text="hola", reply_text=reply_text)
    )
    with asistente.agente.override(model=FunctionModel(modelo_prohibido)):
        await bot.mensaje(update, None)
    assert "No autorizado" in respuestas[0] and "999" in respuestas[0]


def test_permitidos(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PERMITIDOS", " 123, 456 ,")
    assert bot.permitidos() == {"123", "456"}
    monkeypatch.setenv("TELEGRAM_PERMITIDOS", "")
    assert bot.permitidos() == set()  # vacío = nadie
