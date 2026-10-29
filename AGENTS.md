# Instrucciones para asistentes de IA (Claude, Codex, Copilot, Cursor, Gemini…)

Este repositorio es la plantilla del trabajo final del curso «Más allá de los chatbots» (Alex Ojeda Copa): un asistente personal con **Pydantic AI 2.57** que se usa por **Telegram** y se despliega en **Render**. Quien te pide ayuda está aprendiendo.

**Antes de proponer o cambiar código, lee `.agents/skills/asistente-pydantic-ai/SKILL.md`** y la referencia que corresponda en esa carpeta. Ahí están las reglas, las recetas y los errores reales del curso.

## Reglas mínimas

- Responde en español, simple y paso a paso. Haz cambios pequeños sobre la plantilla, sin reescribirla.
- No inventes APIs de Pydantic AI: la versión está fijada en 2.57.
- Toda tool que escribe lleva `requires_approval=True`.
- Los datos de cada persona van por `deps` (`ctx: RunContext[str]`, `ctx.deps`), nunca como argumento de la tool.
- No quites la lista `TELEGRAM_PERMITIDOS` ni el rechazo antes de llamar al modelo.
- Nunca escribas claves ni tokens en archivos versionados: van en `.env` o en *Environment* de Render.
- Dentro de `async def`, usa `await agente.run(...)`. Hay un solo `asyncio.run` por programa.
- Los datos de práctica son ficticios.

## Comandos

```bash
uv sync                      # instalar
uv run python asistente.py   # probar en la terminal
uv run python bot.py         # el bot en el equipo (polling)
uv run pytest                # pruebas sin modelo real; córrelas después de cada cambio
uv add paquete               # nueva dependencia (nunca edites uv.lock a mano)
```
