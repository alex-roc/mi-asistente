# S4 · Flujos agénticos con Pydantic Graph

Un agente solo decide **qué tool** usar. Un **flujo** decide **el orden de los pasos** con código: primero extraer, luego calcular y después confirmar. Se arma como un **grafo**:

- **Nodos (pasos):** funciones, con IA o sin ella.
- **Aristas:** qué paso va después de cuál.
- **Estado:** una «cajita» que todos los pasos comparten y modifican.
- **Decisión:** según lo que devolvió un paso, se sigue por una rama u otra.
- **Fork/join:** varios pasos a la vez y luego se juntan sus resultados.

Úsalo cuando el orden importa o hay pasos que **no** deben depender del modelo. Si una tool basta, no hace falta un grafo.

```python
from pydantic_graph import GraphBuilder, StepContext, TypeExpression, reduce_dict_update
```

## Cadena: un paso tras otro

```python
g = GraphBuilder(input_type=str, output_type=str)

@g.step
async def extraer(ctx: StepContext[None, None, str]) -> Gasto:         # con IA
    return (await extractor.run(ctx.inputs)).output

@g.step
async def convertir(ctx: StepContext[None, None, Gasto]) -> str:       # sin IA: una cuenta es código
    return f"{ctx.inputs.descripcion}: {round(ctx.inputs.monto_bs / 6.96, 2)} USD"

g.add(
    g.edge_from(g.start_node).to(extraer),
    g.edge_from(extraer).to(convertir),
    g.edge_from(convertir).to(g.end_node),
)
grafo = g.build()                        # revisa que todo esté conectado

salida = await grafo.run(inputs="Gasté 70 Bs en el almuerzo.")
print(grafo.render(direction="LR"))      # el diagrama en Mermaid (pégalo en mermaid.live)
```

**`ctx: StepContext[estado, deps, entrada]`:**
- `ctx.inputs` es lo que devolvió el paso anterior.
- `ctx.state` es la cajita compartida.
- `ctx.deps` es lo que pone tu código con `grafo.run(deps=...)`.

Los corchetes son para el editor. El parámetro `ctx` es **obligatorio**: el grafo siempre pasa un único argumento, el contexto, y nunca el valor directo. Los pasos son **`async def`**.

Para ejecutarlo paso a paso: `async with grafo.iter(inputs=...) as ejecucion: async for evento in ejecucion: ...`

## Router: estado + decisión

```python
@dataclass
class Consulta:
    pedido: str = ""
    destino: str = ""

g = GraphBuilder(state_type=Consulta, input_type=str, output_type=str)

@g.step
async def clasificar(ctx: StepContext[Consulta, None, str]) -> Literal["clima", "cocina", "charla"]:
    ctx.state.pedido = ctx.inputs
    ctx.state.destino = (await router.run(ctx.inputs)).output.destino   # router: output_type=NativeOutput(Ruta)
    return ctx.state.destino

@g.step
async def clima(ctx: StepContext[Consulta, None, object]) -> str:      # object: recibe la ruta y no la usa
    return (await meteorologo.run(ctx.state.pedido)).output
# … cocina y charla igual

g.add(
    g.edge_from(g.start_node).to(clasificar),
    g.edge_from(clasificar).to(
        g.decision()
        .branch(g.match(TypeExpression[Literal["clima"]]).to(clima))
        .branch(g.match(TypeExpression[Literal["cocina"]]).to(cocina))
        .branch(g.match(TypeExpression[Literal["charla"]]).to(charla))
    ),
    g.edge_from(clima, cocina, charla).to(g.end_node),
)
estado = Consulta()
respuesta = await grafo.run(state=estado, inputs="¿Qué lleva el silpancho?")
```

Para clasificar, `output_type=NativeOutput(Ruta)` (JSON directo) es más fiable que la salida por tool: con algunos modelos, el router responde la pregunta en vez de clasificarla.

## En paralelo: fork y join

```python
g.add(
    g.edge_from(g.start_node).to(recibir),
    g.edge_from(recibir).to(preguntar_clima, preguntar_cocina),        # los dos a la vez
    g.edge_from(preguntar_clima, preguntar_cocina).to(juntar),
    g.edge_from(juntar).to(redactar),
    g.edge_from(redactar).to(g.end_node),
)
juntar = g.join(reduce_dict_update, initial_factory=dict[str, str], node_id="juntar")
# cada trabajador devuelve {"clima": …} o {"cocina": …}; el join los une en un dict
```

## Bucle con tope: escritor y revisor

El paso `revisar` devuelve `"corregir"` (vuelve a `escribir`) o `"listo"` (sigue a `entregar`). En el estado lleva `intentos`: **siempre pon un tope** (`if aprobado or intentos >= 3: return "listo"`), porque si no, un modelo terco da vueltas sin fin y gasta cuota.

## Aprobación humana

En un script, un nodo puede ser una persona: el paso `preguntar` hace `input("¿Apruebas? [s/N]")` y una decisión lleva a `agendar` o a `cancelar`.

**En el bot no hay `input()`.** Para pedir permiso desde Telegram, usa lo que ya trae la plantilla:

```python
@tareas.tool(requires_approval=True)            # el agente se pausa antes de ejecutar
def crear_tarea(ctx: RunContext[str], titulo: str, fecha: str) -> str: ...

agente = Agent(..., output_type=[str, DeferredToolRequests])
# r.output es DeferredToolRequests → el bot pregunta «Responde /si o /no»
# decidir(): conversacion.deferred_tool_requests.build_results(approvals={id: True/False})
#            y agente.run(conversation=conversacion, deferred_tool_results=decision)
```

Si se rechaza, la tool **no se ejecuta**. La aprobación está en el código, no en el prompt.

## Un grafo dentro de tu asistente

Para que el bot use un flujo, envuélvelo en una tool async:

```python
@mi_capacidad.tool_plain
async def planificar_viaje(pedido: str) -> str:
    """Arma un plan de viaje en varios pasos: extraer, presupuestar y redactar."""
    return await grafo.run(inputs=pedido)
```

## Errores típicos

- Un paso con `def` en vez de `async def` pasa `build()`, pero al ejecutar da `TypeError: object … can't be used in 'await' expression`.
- Un paso sin parámetro da `takes 0 positional arguments but 1 was given`.
- `def paso(texto: str)` recibe igualmente el contexto: `'StepContext' object has no attribute 'upper'`. Usa `ctx.inputs`.
- Una rama sin arista a `g.end_node`, o un paso inalcanzable, hace que `build()` dé `GraphValidationError`.
- En un script, usa **un solo** `asyncio.run(main())` con `await grafo.run(...)` dentro. `grafo.run_sync(...)` seguido de otro `asyncio.run` da «bound to a different event loop».
