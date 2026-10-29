# S1 · Pydantic AI: agente, tools y capabilities

En los ejemplos, `MODELO = "google:gemini-3.5-flash-lite"`, que necesita `GEMINI_API_KEY`. En tu equipo también sirve `"ollama:gemma4:e2b"`.

## Un agente = modelo + instrucciones

```python
from pydantic_ai import Agent

agente = Agent(MODELO, instructions="Eres un asistente experto en economía. Responde en dos frases.")
r = agente.run_sync("¿Qué es la inflación?")   # en un script, fuera de async
print(r.output)        # el texto
print(r.usage)         # tokens y llamadas al modelo
```

## Salida tipada: un contrato para la respuesta

```python
from pydantic import BaseModel, Field

class Concepto(BaseModel):
    nombre: str
    definicion: str = Field(description="Una sola frase")
    ejemplos: list[str] = Field(description="Dos ejemplos concretos")

definidor = Agent(MODELO, instructions="Define conceptos de economía.", output_type=Concepto)
r = definidor.run_sync("inflación")
r.output.ejemplos      # un objeto de Python, validado
```

Si el modelo devuelve algo que no cumple el tipo, Pydantic AI se lo devuelve para que lo corrija (reintentos).

## Tool: el modelo pide, Python hace

```python
economista = Agent(MODELO, instructions="Usa la herramienta para calcular; no hagas cuentas de memoria.")

@economista.tool_plain
def precio_futuro(precio: float, inflacion_anual_pct: float, anios: int) -> float:
    """Calcula el precio de algo después de varios años con una inflación anual constante."""
    return round(precio * (1 + inflacion_anual_pct / 100) ** anios, 2)
```

- El **nombre, el docstring y los tipos** forman el contrato: es lo único que el modelo ve de la tool.
- El ciclo es: el modelo pide la tool con argumentos, Python la ejecuta, el resultado vuelve al modelo y el modelo responde. Para verlo, recorre `r.all_messages()`, que incluye `ToolCallPart` y `ToolReturnPart`.
- Una cuenta exacta la hace el código, no el modelo.

## Capability: tools + instrucciones en un componente

```python
from pydantic_ai.capabilities import Capability

censos = Capability(
    id="censos",
    description="Consulta información demográfica.",
    instructions="Usa consultar_poblacion para obtener cifras. No inventes datos.",
)

@censos.tool_plain
def consultar_poblacion(anio: int) -> int | None:
    """Población ficticia de un año de censo (2012 o 2024)."""
    return {2012: 1000, 2024: 1200}.get(anio)

analista = Agent(MODELO, capabilities=[censos])
```

Lectura y escritura van en capabilities **separadas**. Así otro agente puede recibir solo la de lectura (mínimo privilegio).

## Tools de lectura con APIs abiertas (sin clave)

```python
import httpx

@apis.tool_plain
def inflacion(pais: str, anio: int) -> dict:
    """Inflación anual (%) de un país en un año, según el Banco Mundial.

    Args:
        pais: código de tres letras del país, como BOL, PER o ARG.
        anio: año, por ejemplo 2024.
    """
    url = f"https://api.worldbank.org/v2/country/{pais}/indicator/FP.CPI.TOTL.ZG"
    datos = httpx.get(url, params={"date": anio, "format": "json"}, timeout=15).json()
    if len(datos) < 2 or not datos[1] or datos[1][0]["value"] is None:
        return {"error": f"No hay dato de inflación para {pais} en {anio}"}   # un aviso, no un crash
    registro = datos[1][0]
    return {"pais": registro["country"]["value"], "anio": anio,
            "inflacion_pct": round(registro["value"], 2), "fuente": url}
```

- El modelo elige solo los parámetros (`pais`, `anio`). La URL y el indicador los fija tu código.
- Devuelve **solo lo útil**, no el JSON entero: son menos tokens y hay menos confusión.
- Dentro del bot (que es async), usa `async def` con `httpx.AsyncClient`, como `consultar_clima` en `capacidades.py`.
- Puedes probar la tool sola, sin modelo: `print(inflacion("BOL", 2024))`.

## Leer y escribir en SQLite

```python
import sqlite3
from typing import Literal

Categoria = Literal["transporte", "alimentacion", "educacion", "ocio", "salud"]   # lista cerrada → "enum"

@consulta.tool_plain
def consultar_gastos(categoria: Categoria) -> dict:
    """Gastos de una categoría y su total en bolivianos."""
    conexion = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)  # SOLO lectura
    conexion.row_factory = sqlite3.Row
    filas = conexion.execute(
        "SELECT fecha, descripcion, monto FROM gastos WHERE categoria = ?", (categoria,)  # SQL fijo; valores en ?
    ).fetchall()
    conexion.close()
    return {"categoria": categoria, "total_bs": sum(f["monto"] for f in filas),
            "gastos": [dict(f) for f in filas], "fuente": "gastos.db"}

@registro.tool_plain   # en esta plantilla: @registro.tool(requires_approval=True) con ctx.deps
def registrar_gasto(fecha: str, categoria: Categoria, descripcion: str, monto: float) -> str:
    """Anota un gasto nuevo. La fecha va como AAAA-MM-DD y el monto en bolivianos."""
    conexion = sqlite3.connect(DB)
    try:
        with conexion:  # transacción: todo o nada
            conexion.execute("INSERT INTO gastos VALUES (?, ?, ?, ?)", (fecha, categoria, descripcion, monto))
    except sqlite3.IntegrityError:  # CHECK (monto > 0) en la tabla
        return f"No se guardó: el monto debe ser mayor que 0 (recibí {monto})."
    finally:
        conexion.close()
    return f"Gasto registrado: {descripcion}, {monto} Bs."
```

- **Nunca** armes el SQL con lo que manda el modelo (`f"... WHERE x = '{arg}'"`): usa `?`.
- La base valida también (`CHECK`): no confíes solo en el modelo.
- Para guardar datos de cada persona, añade una columna `persona` y fíltrala con `ctx.deps` (ver `s5-async-deps-despliegue.md`).
- En Render Free el disco se borra al reiniciar: una base SQLite local se pierde (ver los límites del plan Free).
