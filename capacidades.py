"""Las capabilities de tu asistente: una pieza de cada sesión. Cámbialas por las tuyas.

Cada capability junta tools + instrucciones. Dos tipos de tool:
  @x.tool_plain   la tool NO necesita saber quién escribe (el clima, buscar en notas).
  @x.tool         la tool recibe ctx: RunContext[str]; ctx.deps es la persona (recordar, tareas).
"""

import os
from functools import cache
from pathlib import Path

import chromadb
import httpx
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction, OpenAIEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

DATOS = Path(__file__).parent / "datos"

# ── S1 · Una tool que lee una API abierta (Open-Meteo, sin clave) ──────────────────────
clima = Capability(
    id="clima",
    description="Clima actual de ciudades de Bolivia.",
    instructions="Usa consultar_clima para hablar del clima. No inventes temperaturas.",
)
COORDENADAS = {"la paz": (-16.50, -68.15), "cochabamba": (-17.39, -66.16), "santa cruz": (-17.78, -63.18)}


@clima.tool_plain
async def consultar_clima(ciudad: str) -> dict:
    """Temperatura (°C) y viento (km/h) actuales en La Paz, Cochabamba o Santa Cruz."""
    coordenadas = COORDENADAS.get(ciudad.lower().strip())
    if coordenadas is None:
        return {"error": f"No conozco «{ciudad}». Ciudades: {', '.join(COORDENADAS)}"}
    parametros = {"latitude": coordenadas[0], "longitude": coordenadas[1], "current": "temperature_2m,wind_speed_10m"}
    try:
        async with httpx.AsyncClient(timeout=15) as cliente:
            actual = (await cliente.get("https://api.open-meteo.com/v1/forecast", params=parametros)).json()["current"]
    except (httpx.HTTPError, KeyError) as error:  # la API falló: se dice, no se inventa
        return {"error": f"No pude consultar el clima: {str(error)[:120]}"}
    return {
        "ciudad": ciudad,
        "temperatura_c": actual["temperature_2m"],
        "viento_kmh": actual["wind_speed_10m"],
        "fuente": "open-meteo.com",
    }


# ── S2 · Conocimiento interno: RAG sobre datos/notas/*.md ──────────────────────────────
def funcion_embeddings():
    """El modelo de embeddings según MODELO: Gemini u Ollama; si no, el pequeño de Chroma (en inglés)."""
    modelo = os.getenv("MODELO", "google:")
    if modelo.startswith("google:"):
        return OpenAIEmbeddingFunction(
            api_key=os.environ["GEMINI_API_KEY"],
            api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
            model_name="gemini-embedding-001",
        )
    if modelo.startswith("ollama:"):
        return OpenAIEmbeddingFunction(api_key="ollama", api_base=os.environ["OLLAMA_BASE_URL"], model_name="embeddinggemma")
    return DefaultEmbeddingFunction()


@cache  # se indexa la primera vez que alguien busca, y una sola vez (el disco de Render es efímero)
def indice():
    coleccion = chromadb.EphemeralClient().get_or_create_collection(
        "notas", embedding_function=funcion_embeddings(), configuration={"hnsw": {"space": "cosine"}}
    )
    divisor = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)  # trozos de ~300 caracteres
    for archivo in sorted((DATOS / "notas").glob("*.md")):
        trozos = divisor.split_text(archivo.read_text(encoding="utf-8"))
        coleccion.upsert(ids=[f"{archivo.name}#{i}" for i in range(len(trozos))], documents=trozos)
    return coleccion


notas = Capability(
    id="notas",
    description="Notas de la persona: preferencias, planes y datos útiles.",
    instructions=(
        "Para datos personales usa buscar_notas y cita la fuente entre corchetes, por ejemplo [viajes.md#0]. "
        "Si los fragmentos no tienen la respuesta, di que no está en las notas. No inventes."
    ),
)


@notas.tool_plain
def buscar_notas(pregunta: str) -> list[dict]:
    """Busca en las notas los fragmentos más parecidos a la pregunta."""
    try:
        r = indice().query(query_texts=[pregunta], n_results=3)
    except Exception as error:  # cuota o red del modelo de embeddings
        indice.cache_clear()  # la próxima búsqueda vuelve a intentar indexar
        return [{"error": f"No pude buscar en las notas: {str(error)[:120]}"}]
    return [{"fuente": f, "texto": t} for f, t in zip(r["ids"][0], r["documents"][0])]


# ── S2 · Memoria de largo plazo: un archivo por persona (ctx.deps es la persona) ───────
def archivo_de(carpeta: str, persona: str) -> Path:
    (DATOS / carpeta).mkdir(parents=True, exist_ok=True)
    return DATOS / carpeta / f"{persona}.txt"


def lo_que_se(ctx: RunContext[str]) -> str:
    """Instrucción dinámica: se calcula en cada run con los recuerdos de ESA persona."""
    archivo = archivo_de("recuerdos", ctx.deps)
    recuerdos = archivo.read_text(encoding="utf-8").splitlines() if archivo.exists() else []
    return "Lo que sabes de la persona: " + ("; ".join(recuerdos) or "nada todavía.")


memoria = Capability(
    id="memoria",
    description="Recuerda datos duraderos de la persona.",
    instructions=["Si la persona cuenta un dato duradero sobre sí misma, guárdalo con recordar.", lo_que_se],
)


@memoria.tool
def recordar(ctx: RunContext[str], dato: str) -> str:
    """Guarda un dato duradero sobre la persona, en una frase corta. Ejemplo: «Es vegetariana»."""
    with archivo_de("recuerdos", ctx.deps).open("a", encoding="utf-8") as archivo:  # "a": añade sin borrar
        archivo.write(dato + "\n")
    return f"Recordado: {dato}"


# ── S4 · Una acción que escribe, con aprobación humana ─────────────────────────────────
tareas = Capability(
    id="tareas",
    description="Lista de tareas pendientes de la persona.",
    instructions="Para anotar una tarea usa crear_tarea; la persona la aprobará antes de guardarla.",
)


@tareas.tool(requires_approval=True)  # el agente se pausa hasta que la persona apruebe o rechace
def crear_tarea(ctx: RunContext[str], titulo: str, fecha: str) -> str:
    """Anota una tarea pendiente con su fecha (AAAA-MM-DD)."""
    with archivo_de("tareas", ctx.deps).open("a", encoding="utf-8") as archivo:
        archivo.write(f"{fecha} · {titulo}\n")
    return f"Tarea guardada: {titulo} ({fecha})"


@tareas.tool
def ver_tareas(ctx: RunContext[str]) -> list[str]:
    """Las tareas pendientes de la persona."""
    archivo = archivo_de("tareas", ctx.deps)
    return archivo.read_text(encoding="utf-8").splitlines() if archivo.exists() else []
