"""Pruebas sin modelo real ni internet: uv run pytest

Un modelo falso (FunctionModel) pide la tool que queremos, y comprobamos lo que hace el código.
"""

import os
from types import SimpleNamespace

os.environ.setdefault("GEMINI_API_KEY_LOCAL", "clave-de-prueba")  # para importar sin .env (no se llama a Gemini)

import pytest  # noqa: E402
from pydantic_ai import ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402

import asistente  # noqa: E402
import bot  # noqa: E402
import capacidades  # noqa: E402
from config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    """Cada prueba usa su propia gastos.db, no la de datos/."""
    monkeypatch.setattr(capacidades, "DB", tmp_path / "gastos.db")


def pide(tool: str, args: dict) -> FunctionModel:
    """Un modelo falso: la 1.ª vez pide la tool; cuando recibe su resultado, responde texto."""

    def responder(mensajes, info):
        ultimo = mensajes[-1].parts[-1]
        if isinstance(ultimo, ToolReturnPart):
            return ModelResponse(parts=[TextPart(f"Resultado: {ultimo.content}")])
        return ModelResponse(parts=[ToolCallPart(tool, args)])

    return FunctionModel(responder)


def test_consultar_gastos_sin_modelo():
    gastos = capacidades.consultar_gastos("transporte")  # una tool es una función normal
    assert gastos["total_bs"] == 67


async def test_registrar_gasto_escribe_en_la_base():
    with asistente.asistente.override(model=pide("registrar_gasto", {
        "fecha": "2030-05-14", "categoria": "ocio", "descripcion": "Teatro", "monto": 30,
    })):
        respuesta = await asistente.responder("Anota 30 Bs de teatro.")
    assert "Gasto registrado" in respuesta
    assert capacidades.consultar_gastos("ocio")["total_bs"] == 70  # 40 del CSV + 30


async def test_monto_negativo_no_se_guarda():
    with asistente.asistente.override(model=pide("registrar_gasto", {
        "fecha": "2030-05-14", "categoria": "ocio", "descripcion": "Error", "monto": -5,
    })):
        respuesta = await asistente.responder("Anota -5 Bs.")
    assert "No se guardó" in respuesta
    assert capacidades.consultar_gastos("ocio")["total_bs"] == 40


async def test_chat_ajeno_se_rechaza_sin_llamar_al_modelo(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", "123")
    respuestas = []

    async def reply_text(texto):
        respuestas.append(texto)

    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=999), message=SimpleNamespace(text="hola", reply_text=reply_text)
    )
    with asistente.asistente.override(model=FunctionModel(modelo_prohibido)):
        await bot.mensaje(update, None)
    assert "No autorizado" in respuestas[0] and "999" in respuestas[0]


def test_permitidos(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", " 123, 456 ,")
    assert settings.permitidos == {"123", "456"}
    monkeypatch.setattr(settings, "telegram_permitidos", "")
    assert settings.permitidos == set()  # vacío = nadie
