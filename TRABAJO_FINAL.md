# Trabajo final: tu asistente personal, desplegado

**Entrega: jueves 5 de noviembre de 2026.** Entregas dos enlaces: tu **bot de Telegram desplegado en Render** y un **video en YouTube** de 5 minutos como máximo. Es el 100 % de la nota y se aprueba con 70.

## Qué construyes

Un asistente para un **problema concreto y pequeño**: «organizar mis tareas de estudio con mis apuntes» es mejor que «gestionar toda mi vida». Parte de esta plantilla y cámbiala por tu caso, con datos inventados.

Como mínimo, tu asistente debe tener:

| Pieza | Sesión | En la plantilla |
|---|---|---|
| Instrucciones claras: para quién es, qué hace y qué **no** | S1 | `instructions` en `asistente.py` |
| Al menos una tool que **lee** datos (una API abierta, una base SQLite, la web) | S1 · S2 | `clima` |
| **Conocimiento:** 3 o más documentos (ficticios) con búsqueda y **citas** | S2 | `notas` y `datos/notas/` |
| **Memoria** por persona | S2 | `datos/conversaciones/` y `memoria` |
| Una tool que **escribe**, con **aprobación humana** (`requires_approval=True`) | S4 | `tareas` |
| Opcional: un servidor MCP, un flujo de varios pasos (Pydantic Graph) o un agente especialista | S3 · S4 | — |
| **Desplegado** como bot de Telegram en Render, con lista de permitidos | S5 | `bot.py` |

## Rúbrica (100 puntos)

| Criterio | Puntos | Para el nivel «Logrado»… |
|---|---:|---|
| **Problema** | 20 | La necesidad es real y acotada, y explicas por qué conviene un agente (y no un chatbot o un flujo fijo). |
| **Funcionamiento** | 40 | Usa sus tools y su conocimiento, cita fuentes, dice «no lo sé» sin evidencia y pide aprobación antes de escribir (rechazo y aprobación probados). |
| **Despliegue** | 20 | El bot responde en Render solo a la lista de permitidos, sin secretos en el código. |
| **Video** | 20 | Muestra el agente funcionando y explica tus decisiones de diseño, en 5 minutos como máximo. |

**Topes:**
- Si una escritura se ejecuta sin aprobación, Funcionamiento vale 20 como máximo.
- Si el bot responde a cualquiera, Despliegue vale 10 como máximo.
- Si el video no abre sin iniciar sesión o pasa mucho de 5 minutos, Video vale 10 como máximo.

La rúbrica detallada, con cuatro niveles por criterio, la comparte el docente.

## Guion del video (máximo 5 minutos)

1. **30 s:** quién lo usa, qué problema resuelve y qué queda fuera.
2. **60 s:** una petición normal en Telegram, con una tool y una respuesta con fuente.
3. **40 s:** una pregunta sin evidencia, o una API que falla. El asistente no inventa.
4. **50 s:** una acción que escribe: rechazo y aprobación (`/no` y `/si`), con el antes y el después.
5. **45 s:** la arquitectura: capabilities, memoria y dónde se pide permiso.
6. **30 s:** cómo se despliega y quién puede entrar (lista de permitidos, secreto del webhook).
7. **25 s:** una limitación real (por ejemplo, que el disco de Render se borra) y la mejora que harías primero.

Súbelo a YouTube como **no listado** (o público). Antes, revisa que no se vean claves ni tokens.

## Entrega (por el canal que indique el docente)

- [ ] El usuario de tu bot (`@…_bot`). Avísale al docente para que te pase su número de chat y lo añadas a `TELEGRAM_PERMITIDOS`.
- [ ] El enlace al video de YouTube.
- [ ] El enlace a tu repositorio. Puede ser privado si compartes el acceso con el docente. Debe tener el README de tu caso y **ningún** `.env` ni clave.

## Antes de entregar

- [ ] El bot responde hoy en Render.
- [ ] Un chat que no está en la lista recibe «No autorizado».
- [ ] Ninguna tarea se guarda sin `/si`.
- [ ] Las citas apuntan a notas que de verdad respaldan la respuesta.
- [ ] `uv run pytest` pasa.
- [ ] `git grep -nE "AIza[0-9A-Za-z_-]{30}"` no encuentra nada y `.env` no está en el repositorio.
- [ ] El README dice qué se pierde cuando Render reinicia y cómo lo resolverías.

## Si la nube falla

Si Render, Telegram o la cuota del modelo te bloquean, avisa **antes del 5 de noviembre**. Entrega entonces el bot corriendo en tu equipo (`uv run python bot.py`) junto con el error real, la fecha y la configuración sin secretos. Si los controles funcionan, puedes llegar a «Logrado» en Despliegue.
