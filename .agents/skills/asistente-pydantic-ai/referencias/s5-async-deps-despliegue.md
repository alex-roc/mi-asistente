# S5 · async/await, deps y despliegue (Telegram + Render)

## async/await: el mesero que no se queda esperando

Un mesero **sin async** toma el pedido de la mesa 1, va a la cocina y **espera** el plato antes de atender a la mesa 2. Un mesero **con async** toma el pedido 1, lo deja en cocina y, **mientras se cocina**, atiende la mesa 2. Esperar al modelo (1 a 5 s) es como esperar a la cocina: el bot puede atender a otras personas mientras tanto.

| Palabra | Qué significa |
|---|---|
| `async def f()` | «Esta función puede esperar sin bloquear». Llamarla **no** la ejecuta: devuelve una corrutina |
| `await f()` | «Ejecútala y espera su resultado, sin bloquear a los demás». Solo vale **dentro** de un `async def` |
| `asyncio.run(main())` | Arranca el bucle de eventos (la cocina). **Uno solo** por programa, al final del script |

```python
async def pedido(mesa):
    await asyncio.sleep(1)        # como esperar al modelo
    return mesa

await asyncio.gather(pedido("ana"), pedido("beto"), pedido("carla"))   # a la vez: ≈ 1 s, no 3
```

`time.sleep` **bloquea** a todos: dentro de un `async def`, usa `await asyncio.sleep`. Lo mismo con las peticiones HTTP: usa `httpx.AsyncClient`, no `httpx.get`.

**¿`await` o `run_sync`? Mira dónde estás.**

| Dónde estás | Usa |
|---|---|
| Dentro de `async def` (el bot, FastAPI, una tool async, un paso de grafo) | `await agente.run(...)` |
| En una celda de notebook | `await agente.run(...)`, porque el notebook ya tiene un bucle |
| En un script normal, fuera de cualquier `async def` | `agente.run_sync(...)` o un solo `asyncio.run(main())` |

## deps y RunContext: las tools necesitan saber quién escribe

El bot atiende a muchas personas. `recordar` debe guardar en la memoria de **quien escribe**. Hay tres opciones:

| Opción | Problema |
|---|---|
| Una variable global `persona` | Con dos personas a la vez se pisan |
| Un argumento `persona` en la tool | Lo llena **el modelo**: puede equivocarse o ser engañado y escribir en los datos de otra persona |
| **`deps`** | Lo pone **tu código** en cada run; el modelo no lo ve ni lo puede cambiar ✅ |

```python
agente = Agent(MODELO, deps_type=str)                    # deps = la persona (podría ser un dataclass)

@capacidad.tool                                          # @tool, no tool_plain: recibe ctx
def recordar(ctx: RunContext[str], dato: str) -> str:    # ctx PRIMERO; el modelo solo ve «dato»
    guardar(ctx.deps, dato)                              # ctx.deps = "tg123456"
    return f"Recordado: {dato}"

await agente.run(mensaje, deps=f"tg{chat_id}")           # tu código decide quién es
```

- `@tool` exige `ctx: RunContext[...]` como primer parámetro. `@tool_plain` no lo admite.
- Si olvidas `deps=` en el `run`, `ctx.deps` vale `None`.
- Si necesitas más de un dato, usa un `@dataclass Deps: persona: str; base: Path` y `deps_type=Deps`, y lee `ctx.deps.persona`.
- Las instrucciones dinámicas también reciben `ctx` (`lo_que_se(ctx)` en `capacidades.py`).

## El núcleo: un agente es una función

El bot (o una API) solo necesita `responder(persona, mensaje)` y `decidir(persona, aprobar)`, en `asistente.py`. Así el canal (Telegram, la terminal, una API) se cambia sin tocar al agente.

## Telegram

1. En Telegram, abre **@BotFather** y escribe `/newbot`. Dale un nombre y un usuario que termine en `bot`. Te da un **token** (`123456:ABC…`), que va en `TELEGRAM_TOKEN`. Quien tenga el token controla el bot: nunca lo subas.
2. Arranca el bot (`uv run python bot.py`) y escríbele `/start`: responde con tu **número de chat**. Ponlo en `TELEGRAM_PERMITIDOS` (separa varios con comas) y reinicia el bot.
3. **¿Quién puede escribirle?** Cualquiera que encuentre su `@usuario`: los bots de Telegram son públicos. Pero `bot.py` solo **responde** a los chats de la lista y rechaza a los demás **antes** de llamar al modelo, así que no se gasta cuota. Si la lista está vacía, no responde a nadie.

| | Polling (tu equipo) | Webhook (Render) |
|---|---|---|
| Cómo llegan los mensajes | El bot pregunta a Telegram cada poco | Telegram hace un POST a `https://tu-app.onrender.com/telegram` |
| Necesita URL pública | No | Sí: Render la pone en `RENDER_EXTERNAL_URL` |
| Seguridad extra | — | `secret_token`: Telegram lo manda en cada aviso y otros no lo saben (`bot.py` lo deriva del token) |

**No uses el mismo token en los dos a la vez.** Al arrancar, el *polling* **borra el webhook**, y el bot de Render deja de recibir mensajes. Para recuperarlo, reinicia el servicio en Render (*Manual Deploy → Restart service*, o *Deploy latest commit*). Para comprobar a dónde apunta, abre `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` en tu navegador, sin compartir esa URL.

## Render (plan Free)

**A mano** (*New → Web Service*):

| Campo | Valor |
|---|---|
| Source | Tu repositorio de GitHub (conecta la cuenta la primera vez) |
| Language | Python 3 |
| Branch | `main` |
| Build Command | `uv sync --locked --no-dev` |
| Start Command | `uv run --no-sync python bot.py` |
| Instance Type | **Free** |
| Environment | `GEMINI_API_KEY`, `TELEGRAM_TOKEN`, `TELEGRAM_PERMITIDOS` (y opcionalmente `MODELO`) |

- Render instala uv solo, porque hay un `uv.lock`, y usa Python 3.12 por el archivo `.python-version`.
- Cada `git push` a `main` vuelve a desplegar (*Auto-Deploy*). Cambiar una variable en *Environment* también.
- En *Logs* debe aparecer `Webhook en https://….onrender.com/telegram`.

**Límites del plan Free:**
- **Se duerme** tras 15 minutos sin uso, y el primer mensaje tarda alrededor de un minuto. Telegram reintenta, así que la respuesta llega.
- **El disco es efímero:** al reiniciar, redesplegar o dormirse se pierden `datos/conversaciones/`, `datos/recuerdos/` y `datos/tareas/`. Para conservarlos haría falta una base externa (por ejemplo, Postgres gratuito): es la primera mejora «de producción».
- Tiene 512 MB de RAM: con Gemini alcanza, pero Ollama no cabe.
- La cuota de Gemini gratis es **diaria** por modelo: si da 429, espera o cambia `MODELO`.

## Secretos

| Dónde | Cómo |
|---|---|
| Tu equipo | `.env` (copia de `.env.example`), ignorado por `.gitignore` |
| GitHub | **Nunca** `.env`, claves ni tokens: lo subido queda en el historial |
| Render | Panel *Environment* |

Antes de subir, comprueba: `git status` no debe mostrar `.env`, y `git grep -nE "AIza[0-9A-Za-z_-]{30}"` no debe encontrar nada. Si una clave se filtró, **revócala** y crea otra (en AI Studio o con `/revoke` en @BotFather).
