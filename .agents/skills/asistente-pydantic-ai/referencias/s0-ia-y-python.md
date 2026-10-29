# S0 · Repaso: IA y Python para agentes

## IA, en cinco ideas

- **Predictiva, generativa y agéntica.** La predictiva clasifica o estima, la generativa produce texto o imágenes y la agéntica **actúa**: decide qué herramienta usar, la usa y sigue.
- **Un LLM predice el siguiente token.** No consulta una base de datos ni tiene reloj: por eso un agente necesita tools para los datos actuales (clima, hora, gastos).
- **Contexto y temperatura.** El contexto es todo lo que el modelo ve en una llamada: instrucciones, historial, resultados de tools. Tiene un límite de tokens. La temperatura controla cuánto varía la respuesta.
- **Límites.** Alucina (inventa con seguridad), tiene una fecha de corte, cuesta dinero o cuota por token y puede obedecer a texto malicioso. El diseño del agente compensa esos límites con tools con fuente, «no lo sé», aprobación humana y mínimo privilegio.
- **Un buen prompt** dice el rol, la tarea, el formato y los límites («Responde en español, breve. Si no está en las notas, dilo»).

## De chatbot a agente

| | Chatbot | Agente |
|---|---|---|
| Datos | Lo que memorizó | Consulta tools (APIs, documentos, bases) |
| Acciones | Solo responde | Puede escribir, con permiso |
| Control | El prompt | Código: tipos, permisos, flujos |

## Python que usa el curso

- **uv** gestiona Python, el entorno y las dependencias:
  - `uv sync` instala lo de `pyproject.toml` y `uv.lock` en `.venv/`.
  - `uv run python archivo.py` ejecuta con ese entorno.
  - `uv add paquete` añade una dependencia.
- **Anotaciones de tipo:** `def f(ciudad: str) -> dict:`. Pydantic AI las lee para armar el contrato de cada tool, así que no son decoración.
- **Pydantic `BaseModel`:** una clase con campos tipados que valida los datos. Sirve para la salida estructurada (`output_type=Gasto`).

```python
from pydantic import BaseModel, Field

class Gasto(BaseModel):
    descripcion: str
    monto_bs: float = Field(gt=0, description="Monto en bolivianos")
```

- **Decoradores** (`@capability.tool_plain`): una línea encima de una función que la «registra» en otro objeto. La función sigue siendo normal, y puedes llamarla tú para probarla.
- **`.env` y `load_dotenv()`:** las claves se leen de variables de entorno, nunca se escriben en el código.
- **Notebooks en VS Code:** en una celda puedes escribir `await agente.run(...)` directamente, porque el notebook ya corre dentro de un bucle async. Por eso, ahí `run_sync` falla (ver `s5-async-deps-despliegue.md`).
- **Windows:** abre los archivos con `encoding="utf-8"` y usa Git Bash para que los comandos sean los mismos que en Mac o Linux.
