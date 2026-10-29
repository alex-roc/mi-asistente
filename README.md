# Mi asistente

Plantilla para el trabajo final del curso **«Más allá de los chatbots»** de Alex Ojeda Copa: un asistente personal hecho con [Pydantic AI](https://pydantic.dev/docs/ai/) que se usa por **Telegram** y se despliega gratis en **Render**.

Ya trae una pieza de cada sesión:

| Pieza | Sesión | Dónde |
|---|---|---|
| Una tool que lee una API abierta (el clima, con Open-Meteo) | S1 | `capacidades.py` → `clima` |
| Búsqueda en tus documentos con citas (RAG con Chroma y embeddings de Gemini) | S2 | `capacidades.py` → `notas`, y `datos/notas/` |
| Memoria por persona: la conversación y los datos duraderos | S2 | `asistente.py` y `capacidades.py` → `memoria` |
| Una acción que escribe, con aprobación humana (`/si` o `/no`) | S4 | `capacidades.py` → `tareas` |
| `async`/`await` y `deps` (quién escribe) | S5 | `asistente.py` → `responder` y `decidir` |
| Bot de Telegram con lista de permitidos: *polling* en tu equipo y webhook en Render | S5 | `bot.py` |

Lo que tienes que hacer está en **[TRABAJO_FINAL.md](TRABAJO_FINAL.md)**: requisitos, rúbrica, guion del video y fecha.

---

## 0 · Lo que necesitas

| Qué | Para qué | Dónde |
|---|---|---|
| **uv** y **git** | Instalar y ejecutar; subir tu código | Los instalaste en la S0. En Windows, usa **Git Bash** |
| Una cuenta de **GitHub** | Guardar tu código; Render lo lee de ahí | [github.com](https://github.com) |
| Una clave de **Gemini** (gratis) | El modelo y los embeddings | [aistudio.google.com/apikey](https://aistudio.google.com/apikey), en un proyecto **sin facturación** |
| **Telegram** en tu teléfono o computadora | Crear y usar el bot | [telegram.org](https://telegram.org) |
| Una cuenta de **Render** (gratis, sin tarjeta) | Publicar el bot en internet | [render.com](https://render.com): entra con *GitHub* |

## 1 · Tu copia de la plantilla

1. Arriba en esta página, pulsa **Use this template → Create a new repository**.
2. Ponle un nombre (por ejemplo, `asistente-estudio`). Puede ser **privado**.
3. Clónalo en tu equipo y entra en la carpeta:

```bash
git clone https://github.com/TU-USUARIO/asistente-estudio.git
cd asistente-estudio
```

## 2 · En tu equipo

```bash
cp .env.example .env     # y escribe tu GEMINI_API_KEY en .env (nunca subas .env)
uv sync                  # instala Python 3.12 y las dependencias en .venv/
uv run python asistente.py
```

Conversa en la terminal. Prueba estos mensajes:
- «¿Qué clima hace en Cochabamba?»: usa la tool del clima.
- «¿Cuánto cuesta el viaje a Tarata?»: busca en las notas y cita `[viajes.md#0]`.
- «Recuerda que soy vegetariana»: lo guarda en la memoria.
- «Anota estudiar Estadística el 2030-05-20»: pide aprobación; escribe `/si` o `/no`.

Escribe `salir` para terminar.

Para comprobar que todo está en orden sin gastar cuota del modelo, corre las pruebas:

```bash
uv run pytest
```

## 3 · Tu bot de Telegram

**3.1 · Crea el bot**
1. En Telegram, busca **@BotFather** (con la marca azul de verificado) y pulsa *Iniciar*.
2. Escribe `/newbot`.
3. Escribe el **nombre** que verá la gente, por ejemplo «Asistente de estudio».
4. Escribe el **usuario**, que tiene que terminar en `bot`, por ejemplo `asistente_estudio_ana_bot`.
5. BotFather te da un **token** como `7812345678:AAH…`. Cópialo en `.env`: `TELEGRAM_TOKEN=7812345678:AAH…`

Ese token es la llave del bot: quien lo tenga lo controla. No lo compartas ni lo subas a GitHub. Si se filtra, escribe `/revoke` en @BotFather para invalidarlo.

**3.2 · Arráncalo y averigua tu número de chat**

```bash
uv run python bot.py
```

Abre tu bot en Telegram (el enlace `t.me/…_bot` que te dio BotFather) y pulsa **Iniciar**, o escribe `/start`. Te responde con «Tu número de chat es 123456789…».

**3.3 · Autorízate**
1. Detén el bot con Ctrl+C.
2. Pon tu número en `.env`: `TELEGRAM_PERMITIDOS=123456789`. Para varias personas, separa los números con comas.
3. Vuelve a ejecutar `uv run python bot.py`.
4. Escríbele «¿Qué clima hace en La Paz?» y prueba la aprobación con `/si` y `/no`.

> **¿Cualquiera puede escribirle a mi bot?** Cualquiera que encuentre su usuario puede *escribirle* (en Telegram no existen los bots privados). Pero el bot solo *responde* a los números de `TELEGRAM_PERMITIDOS`. A los demás les contesta «No autorizado» **sin llamar al modelo**, así que no gastan tu cuota. Si la lista está vacía, no responde a nadie.

Mientras corre en tu equipo, el bot usa ***polling***: pregunta a Telegram cada poco si hay mensajes nuevos. Si apagas la computadora, se apaga el bot. Para que funcione siempre, súbelo a Render.

## 4 · Despliegue en Render (paso a paso, a mano)

**4.1 · Sube tu código a GitHub**

```bash
git status               # .env NO debe aparecer en la lista
git add .
git commit -m "Mi asistente"
git push
```

**4.2 · Crea el servicio en Render**
1. Entra a [dashboard.render.com](https://dashboard.render.com) con tu cuenta de GitHub.
2. Pulsa **+ New → Web Service**.
3. En *Source Code*, elige **GitHub**. La primera vez, pulsa **Configure GitHub** (o *Connect GitHub*) y dale acceso a tu repositorio, a todos o solo a ese.
4. Elige tu repositorio y completa el formulario:

| Campo | Valor |
|---|---|
| **Name** | `asistente-estudio`. Será parte de la URL: `https://asistente-estudio.onrender.com` |
| **Language** | `Python 3` |
| **Branch** | `main` |
| **Region** | La que quieras, por ejemplo *Virginia (US East)* |
| **Root Directory** | (vacío) |
| **Build Command** | `uv sync --locked --no-dev` |
| **Start Command** | `uv run --no-sync python bot.py` |
| **Instance Type** | **Free** |

5. En **Environment Variables**, pulsa *Add Environment Variable* y añade:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | Tu clave de Gemini |
| `TELEGRAM_TOKEN` | El token de BotFather |
| `TELEGRAM_PERMITIDOS` | Tu número de chat (y el del docente, separados por coma) |

6. Pulsa **Deploy Web Service**. La primera vez tarda unos minutos.

**4.3 · Comprueba que funciona**
1. En la pestaña **Logs** debe aparecer `Webhook en https://asistente-estudio.onrender.com/telegram` y luego *Your service is live 🎉*.
2. **Detén el bot de tu equipo** (Ctrl+C), si seguía corriendo.
3. Escríbele al bot en Telegram: ahora responde desde Render, con la computadora apagada.

En Render el mismo `bot.py` funciona con **webhook**: Telegram envía cada mensaje a tu URL. El código se da cuenta solo, porque Render define `RENDER_EXTERNAL_URL`. Además, Telegram firma cada aviso con un secreto derivado de tu token, así que nadie más puede hacerse pasar por Telegram.

**4.4 · Actualizar**
- Cada `git push` a `main` vuelve a desplegar solo (*Auto-Deploy*).
- Si cambias una variable en **Environment** y la guardas, Render también vuelve a desplegar.
- Para añadir a alguien: edita `TELEGRAM_PERMITIDOS` y guarda.

> **Atajo opcional:** en vez de los pasos 4.2.2 a 4.2.6, puedes usar **+ New → Blueprint**, elegir tu repositorio y rellenar las variables que te pide. Render lee `render.yaml`, que tiene la misma configuración.

### Límites del plan Free

| Límite | Qué significa |
|---|---|
| **Se duerme** tras 15 minutos sin mensajes | El primer mensaje tarda alrededor de un minuto en responder; los siguientes son rápidos |
| **El disco es efímero** | Al dormirse, reiniciar o redesplegar se borran `datos/conversaciones/`, `datos/recuerdos/` y `datos/tareas/`. Las notas se vuelven a indexar solas. Conservarlos requiere una base de datos externa: es la primera mejora «de producción» |
| 512 MB de memoria | Alcanza con Gemini; Ollama no cabe |
| La cuota de Gemini gratis es **diaria** | Si responde «El modelo no respondió», mira los logs: un `429` es cuota. Espera o cambia `MODELO` |

## 5 · Hazlo tuyo

1. **Instrucciones** (`asistente.py`): para quién es, qué hace y qué **no** hace.
2. **Documentos** (`datos/notas/*.md`): cambia las notas de ejemplo por las de tu caso (3 o más, ficticias).
3. **Capabilities** (`capacidades.py`): añade las tuyas y enchúfalas en `asistente.py`, en la línea «← aquí enchufas tus capabilities».
   - Si la tool lee o guarda algo **de cada persona** (sus gastos, sus notas), usa `@tu_capacidad.tool` con `ctx: RunContext[str]` como primer parámetro y `ctx.deps` como la persona. En Telegram, la persona es `tg<número de chat>`. Nunca pongas la persona como argumento: los argumentos los llena el modelo.
   - Si la tool no depende de la persona (el clima), usa `@tu_capacidad.tool_plain`.
   - Toda tool que **escribe** lleva `requires_approval=True`.
4. **Pruebas** (`tests/`): copia una prueba y adáptala a tu tool que escribe.
5. **Dependencias:** `uv add nombre-paquete`, nunca a mano. Luego haz commit de `pyproject.toml` y `uv.lock`.

## 6 · Pide ayuda a una IA

Este repositorio trae un **skill** con todo lo que vimos en el curso (S0 a S5): reglas, recetas con código probado y una tabla de errores reales. Está en [`.agents/skills/asistente-pydantic-ai/`](.agents/skills/asistente-pydantic-ai/SKILL.md).

| Herramienta | Cómo lo usa |
|---|---|
| **Claude Code** | Solo: lee `CLAUDE.md` y el skill (`.claude/skills/`). Pídele, por ejemplo: «añade una capability para mis gastos en SQLite, con aprobación para registrar» |
| **Codex**, **Cursor**, **GitHub Copilot**, **Gemini CLI** | Leen `AGENTS.md`, que les indica dónde está el skill |
| **ChatGPT**, **Claude.ai**, **Gemini** (en la web) | Adjunta `SKILL.md` y la referencia que necesites (por ejemplo, `referencias/errores.md`) y pega tu código y el error completo |

La IA te ayuda, pero tú respondes por el código: entiende cada cambio antes de aceptarlo, y nunca le pegues tus claves ni tokens.

## 7 · Problemas frecuentes

| Ves | Qué hacer |
|---|---|
| `Falta GEMINI_API_KEY` o `Falta TELEGRAM_TOKEN` | Ponlas en `.env` (equipo) o en *Environment* (Render) |
| El bot responde «No autorizado. Tu chat es N» | Añade N a `TELEGRAM_PERMITIDOS` y reinicia el bot (en Render, guarda la variable) |
| El bot de Render dejó de responder **después de probar en tu equipo** | Al arrancar, el *polling* local borra el webhook. En Render, ve a **Manual Deploy → Restart service** (o *Deploy latest commit*) |
| `Conflict: terminated by other getUpdates request` | Tienes dos bots en *polling* con el mismo token: deja uno solo |
| «El modelo no respondió» | Mira los logs: un `429` es la cuota diaria (espera o cambia `MODELO`); un `spending cap` es una clave de un proyecto con facturación |
| El build de Render falla por `uv.lock` | Cambiaste dependencias sin `uv lock`: corre `uv lock`, haz commit y push |
| Se olvidó de todo | Render Free borra el disco al dormirse o al redesplegar (ver los límites) |
| Más errores (async, deps, MCP, grafos) | [`referencias/errores.md`](.agents/skills/asistente-pydantic-ai/referencias/errores.md) |

Para ver a dónde apunta el webhook de tu bot, abre en tu navegador `https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo`. No compartas esa URL: lleva tu token.

## Archivos

```
├── asistente.py        el agente: responder(persona, mensaje) y decidir(persona, aprobar)
├── capacidades.py      clima, notas, memoria y tareas  ← aquí van las tuyas
├── bot.py              Telegram: /start, permitidos, /si y /no; polling o webhook
├── datos/notas/        tus documentos (ficticios)
├── tests/              pruebas sin modelo real
├── pyproject.toml      dependencias (uv.lock las fija)
├── .python-version     Python 3.12 (lo leen uv y Render)
├── .env.example        las variables, sin valores
├── render.yaml         atajo para Render (Blueprint)
├── TRABAJO_FINAL.md    lo que se entrega y cómo se evalúa
├── AGENTS.md, CLAUDE.md  instrucciones para asistentes de IA
└── .agents/skills/     el skill del curso
```

---

Autor: **Alex Ojeda Copa**. Código bajo licencia [MIT](LICENSE).
