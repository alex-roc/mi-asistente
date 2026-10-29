# Errores frecuentes: qué ves y qué hacer

Los mensajes son reales, reproducidos con Pydantic AI 2.57. Busca aquí una parte del texto del error.

## async / await

| Ves | Causa | Arreglo |
|---|---|---|
| `AttributeError: 'coroutine' object has no attribute 'output'` | `r = agente.run(...)` sin `await` | `r = await agente.run(...)`, o `run_sync` fuera de async |
| `<coroutine object … at 0x…>` y `RuntimeWarning: coroutine '…' was never awaited` | Llamaste a una función `async` sin `await` | Ponle `await` delante |
| `SyntaxError: 'await' outside function` | `await` suelto en un script | Mételo en `async def main()` y llama `asyncio.run(main())` |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | `asyncio.run` dentro de algo async, o en un notebook | En el notebook, `await` directo; en el código async, `await` |
| `RuntimeError: This event loop is already running` | `run_sync` dentro de `async def`, del bot o de un notebook | Cambia a `await agente.run(...)` |
| `… is bound to a different event loop` / `Event loop is closed` | Dos `asyncio.run` (o `run_sync` y luego `asyncio.run`) con el mismo cliente del modelo o del MCP | Un solo `asyncio.run(main())` por programa |
| El bot se congela con varias personas | `time.sleep` o `httpx.get` dentro de una tool `async` | `await asyncio.sleep`, `httpx.AsyncClient` |

## deps / RunContext / tools

| Ves | Causa | Arreglo |
|---|---|---|
| `ctx.deps` es `None` (o se guarda en `None.txt`) | Falta `deps=` en `agente.run(...)` | `agente.run(mensaje, deps=persona)` |
| `UserError: … First parameter of tools that take context must be annotated with RunContext[...]` | `@x.tool` sin `ctx` como primer parámetro | Añade `ctx: RunContext[str]` primero, o usa `@x.tool_plain` |
| `UserError: … RunContext annotations can only be used with tools that take context` | `@x.tool_plain` con `ctx` | Cambia a `@x.tool` |
| El modelo inventa una cita o una URL | La tool no devuelve `fuente` ni `url` | Devuelve la fuente en el resultado |
| Se pierde un dato cuando el modelo llama dos veces a la vez | La tool lee todo el archivo y lo reescribe | `open(..., "a")` o SQLite |
| `UnexpectedModelBehavior: Exceeded maximum retries` | La salida no cumple el tipo, o la tool lanza `ModelRetry` una y otra vez | Simplifica el `output_type`, aclara el docstring; para clasificar, `NativeOutput(...)` |

## Modelo y claves

| Ves | Causa | Arreglo |
|---|---|---|
| `Falta GEMINI_API_KEY` (al arrancar) | No hay clave en `.env` ni en *Environment* | Crea la clave en aistudio.google.com/apikey y ponla |
| `429 … RESOURCE_EXHAUSTED` / `exceeded your current quota` | Se acabó la cuota diaria gratis de ese modelo | Espera a mañana o cambia `MODELO` a otro modelo gratuito |
| `429 … spending cap` | La clave es de un proyecto de Google **con facturación** | Crea la clave en un proyecto sin facturación |
| `429` solo al buscar en la web | `WebSearch` sin `native=False` usa el buscador de Google, que no es gratis | `WebSearch(native=False, local=True)` |
| La búsqueda en las notas no encuentra en español | Embeddings por defecto de Chroma (en inglés) | `gemini-embedding-001` (ya está en `capacidades.py`) |

## MCP

| Ves | Causa | Arreglo |
|---|---|---|
| `MCP(local="servidor.py")` falla | `local=` solo acepta URL o un transporte | `MCP(local=StdioTransport(command=sys.executable, args=["servidor.py"]))` |
| `421 Misdirected Request` detrás de Render o de un túnel | El servidor HTTP escucha en `127.0.0.1` | `servidor.run(transport="streamable-http", host="0.0.0.0", …)` |
| El modelo ve «Error executing tool» sin detalle | Lanzaste `ValueError` en una tool MCP | Lanza `ToolError("mensaje útil")` |
| El servidor stdio no responde | Un `print` en el servidor se mezcla con los mensajes MCP | No imprimas nada en el proceso del servidor |

## Pydantic Graph

| Ves | Causa | Arreglo |
|---|---|---|
| `TypeError: object … can't be used in 'await' expression` | Un paso con `def` | `async def` |
| `takes 0 positional arguments but 1 was given` | Un paso sin parámetro | `async def paso(ctx: StepContext[...])` |
| `'StepContext' object has no attribute …` | Usaste el parámetro como si fuera el valor | El valor está en `ctx.inputs` |
| `GraphValidationError` en `build()` | Un paso sin camino al final, o inalcanzable | Conecta cada rama hasta `g.end_node` |

## Telegram y Render

| Ves | Causa | Arreglo |
|---|---|---|
| El bot contesta «No autorizado. Tu chat es N» | Tu chat no está en `TELEGRAM_PERMITIDOS` | Añade N (separa con comas) y reinicia, o guarda la variable en Render |
| El bot de Render dejó de responder después de probar en local | El *polling* local borró el webhook | Render: *Manual Deploy → Restart service* (o *Deploy latest commit*) |
| `telegram.error.Conflict: terminated by other getUpdates request` | Dos bots en *polling* con el mismo token | Deja uno solo corriendo |
| El primer mensaje tarda un minuto | Render Free se durmió | Es normal; avísalo en tu video |
| Se olvidó de todo tras un rato | El disco de Render Free se borra al dormirse o al redesplegar | Es un límite conocido; la mejora es una base externa |
| El build falla con `uv.lock` desactualizado (`--locked`) | Cambiaste `pyproject.toml` sin `uv lock` | `uv lock`, commit y push (mejor: `uv add paquete`) |
| *Port scan timeout* / *No open ports detected* | El servicio no escucha en `$PORT` | El Start Command debe ser `uv run --no-sync python bot.py` (en Render usa webhook en `$PORT`) |
| Asteriscos `**` en los mensajes | El modelo escribió Markdown | Las instrucciones piden texto plano; refuérzalo si hace falta |

## Windows

| Ves | Causa | Arreglo |
|---|---|---|
| `UnicodeEncodeError … cp1252` al imprimir emojis o tildes | Consola en cp1252 | Usa Git Bash, o `sys.stdout.reconfigure(encoding="utf-8")` |
| `UnicodeDecodeError` al leer un archivo | Se abrió sin codificación | `open(..., encoding="utf-8")` / `read_text(encoding="utf-8")` |
