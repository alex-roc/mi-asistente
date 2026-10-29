# S2 · Conocimiento, contexto y memoria

Hay tres fuentes de conocimiento:
- **externo:** la web y Wikipedia;
- **interno:** tus documentos, con RAG;
- **memoria:** la conversación y los datos duraderos de cada persona.

## Conocimiento externo: la web, con capabilities ya hechas

```python
from pydantic_ai.capabilities import WebFetch, WebSearch
from pydantic_ai.common_tools.web_fetch import web_fetch_tool

investigador = Agent(
    MODELO,
    instructions="Para datos actuales usa la web y di de qué URL sacaste el dato.",
    capabilities=[
        WebSearch(native=False, local=True),                                    # DuckDuckGo, gratis
        WebFetch(native=False, local=web_fetch_tool(max_content_length=5000)),  # leer una URL, recortada
    ],
)
```

`native=False` es obligatorio con Gemini gratis: el buscador nativo de Google no entra en la capa gratuita y da 429. En esta plantilla, añade antes los extras: `uv add "pydantic-ai-slim[google,openai,duckduckgo,web-fetch]==2.57.0"`.

## Una fuente de confianza: tu propia tool, con URL para citar

```python
@enciclopedia.tool_plain
async def resumen_wikipedia(tema: str) -> dict:
    """Resumen corto de un artículo de Wikipedia en español, con su URL.

    Args:
        tema: título del artículo, por ejemplo «Cochabamba».
    """
    titulo = tema[:1].upper() + tema[1:].replace(" ", "_")
    url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{titulo}"
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "mi-asistente"}) as cliente:
        respuesta = await cliente.get(url, follow_redirects=True)
    if respuesta.status_code != 200:
        return {"error": f"No encontré el artículo «{tema}» en Wikipedia"}
    datos = respuesta.json()
    return {"titulo": datos["title"], "resumen": datos["extract"], "url": datos["content_urls"]["desktop"]["page"]}
```

Si la tool no devuelve `url` o `fuente`, el modelo **inventa** una cita.

## Conocimiento interno: RAG

1. **Leer:** de Markdown con `read_text(encoding="utf-8")`, o de PDF con `pypdf.PdfReader(pdf).pages[i].extract_text()`.
2. **Fragmentar:** `RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)` hace trozos de unos 300 caracteres, que se solapan 50 y se cortan de preferencia entre párrafos.
3. **Indexar:** se calcula un embedding por trozo y se guarda en Chroma con un id que sirve de fuente (`archivo.md#3`).
4. **Buscar:** se calcula el embedding de la pregunta y se devuelven los trozos más parecidos (similitud de coseno).
5. **Responder citando:** el agente usa la búsqueda como **tool** (RAG agéntico) y cita `[archivo.md#3]`.

**Léxica o semántica.** La búsqueda léxica cuenta palabras en común: «¿cuánto pago de alquiler?» no encuentra «canon de arrendamiento». Un **embedding** convierte el texto en un vector que resume su significado, y el coseno mide si dos vectores apuntan al mismo lado: 1 quiere decir «mismo sentido» y 0, «nada que ver».

```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

embeddings = OpenAIEmbeddingFunction(            # Gemini, por su API compatible con OpenAI
    api_key=os.environ["GEMINI_API_KEY"],
    api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
    model_name="gemini-embedding-001",
)
coleccion = chromadb.EphemeralClient().get_or_create_collection(
    "notas", embedding_function=embeddings, configuration={"hnsw": {"space": "cosine"}})
coleccion.upsert(ids=["viajes.md#0"], documents=["Presupuesto del viaje: 90 Bs…"])
r = coleccion.query(query_texts=["¿cuánto cuesta el viaje?"], n_results=3)
# r["ids"][0], r["documents"][0], r["distances"][0]   (similitud = 1 - distancia)
```

- El modelo de embeddings por defecto de Chroma (all-MiniLM) está entrenado en inglés y encuentra mal en español. Usa `gemini-embedding-001`, o `embeddinggemma` con Ollama.
- `EphemeralClient` vive en memoria. `PersistentClient(path="indice")` guarda en disco, pero en Render Free el disco se borra, así que la plantilla vuelve a indexar al arrancar.
- Las instrucciones deben decir qué hacer si no hay evidencia: «Si los fragmentos no tienen la respuesta, di que no está en las notas».
- La plantilla ya lo hace en `capacidades.py` (`indice()` y `buscar_notas`). Para usar PDFs, añade `uv add pypdf` y lee las páginas antes de fragmentar.

## Memoria de la conversación

```python
from pydantic_ai import ConversationTypeAdapter

t1 = agente.run_sync("Me llamo Ana y el sábado viajo a Tarata.")
t2 = agente.run_sync("¿A dónde viajo el sábado?", conversation=t1.conversation)   # recuerda

# Que sobreviva a un reinicio: un archivo JSON por persona
archivo.write_bytes(ConversationTypeAdapter.dump_json(t2.conversation))
conversacion = ConversationTypeAdapter.validate_json(archivo.read_bytes())
```

- Cada run empieza de cero si no le pasas `conversation=`.
- **Una conversación por persona.** Si se mezclan, Beto ve lo que dijo Ana.
- `ProcessHistory(lambda mensajes: mensajes[-20:])` (en `capabilities`) limita lo que ve el modelo, para no llenar el contexto.
- La plantilla lo hace en `asistente.py` (`cargar` y `_guardar_y_responder`).

## Memoria de largo plazo: una tool `recordar` + instrucciones dinámicas

```python
def lo_que_se(ctx: RunContext[str]) -> str:
    """Se vuelve a calcular en cada run, con los recuerdos de ESA persona."""
    return "Lo que sabes de la persona: " + ("; ".join(leer(ctx.deps)) or "nada todavía.")

memoria = Capability(
    id="memoria",
    description="Recuerda datos duraderos de la persona.",
    instructions=["Si la persona cuenta un dato duradero sobre sí misma, guárdalo con recordar.", lo_que_se],
)

@memoria.tool
def recordar(ctx: RunContext[str], dato: str) -> str:
    """Guarda un dato duradero sobre la persona, en una frase corta."""
    with archivo_de("recuerdos", ctx.deps).open("a", encoding="utf-8") as f:   # "a": añade, no reescribe
        f.write(dato + "\n")
    return f"Recordado: {dato}"
```

El modelo puede pedir **dos llamadas a la vez** (`recordar` dos veces). Si cada llamada lee todo el archivo y lo reescribe, se pierde una. Por eso hay que añadir con `open("a")` o usar SQLite.
