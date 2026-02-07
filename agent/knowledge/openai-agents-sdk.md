# OpenAI Agents SDK — Key Patterns

Reference for building our agent layer. Based on research of official docs + examples.

## Tool Definition

```python
@function_tool
async def tool_read_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Kebab-case node name"],
) -> str:
    """Read a knowledge node's full content."""
    ...
```

- First param typed `RunContextWrapper[T]` is auto-excluded from schema, injected at runtime
- `Annotated[type, "description"]` becomes the param description in JSON schema
- Tools return `str` (what the model sees as tool result)
- Sync and async tools both work — SDK handles both

## Agent Definition

```python
agent = Agent[GraphContext](
    name="Ingestion Agent",
    instructions=INSTRUCTIONS,          # str or Callable[[RunContextWrapper, Agent], str]
    tools=ALL_TOOLS,
    output_type=IngestionResult,        # Pydantic model — agent MUST produce this shape
    model="gpt-4.1",
    model_settings=ModelSettings(temperature=0.2),
)
```

- Dynamic instructions: pass a callable that receives context + agent, returns str
- `output_type` constrains final output — loop continues until model produces matching JSON with no tool calls
- `clone()` for variants: `ceo_agent = base_agent.clone(instructions="CEO perspective...")`

## Running

```python
result = await Runner.run(agent, input=text, context=ctx, max_turns=25)
output: IngestionResult = result.final_output  # parsed Pydantic model
```

- `max_turns` prevents runaway agents
- `result.to_input_list()` for multi-turn conversations
- `Runner.run_sync()` for scripts/CLI
- `call_model_input_filter` in RunConfig to trim context in long traversals

## Sub-Agents (Manager Pattern)

Better than handoffs for our use case — calling agent stays in control:

```python
sub_agent = Agent[GraphContext](
    name="Entity Extractor",
    output_type=ExtractedEntities,
    tools=[],
)

main_agent = Agent[GraphContext](
    tools=[
        *ALL_TOOLS,
        sub_agent.as_tool(
            tool_name="extract_entities",
            tool_description="Extract entities from text.",
            max_turns=5,
        ),
    ],
)
```

## Handoffs (Peer Transfer)

For routing, not sub-tasks. Target agent takes over completely:

```python
triage_agent = Agent[GraphContext](
    handoffs=[ingest_agent, query_agent],
)
```

## Lifecycle Hooks

```python
class LoggingHooks(RunHooks[GraphContext]):
    async def on_tool_start(self, context, agent, tool): ...
    async def on_tool_end(self, context, agent, tool, result): ...
    async def on_agent_start(self, context, agent): ...
    async def on_agent_end(self, context, agent, output): ...
```

## Key Insights

- `tool_use_behavior="run_llm_again"` (default) is correct for graph exploration
- Disabled tools (`is_enabled=False`) are hidden from LLM, not just blocked
- Instructions matter more than tool count — invest in comprehensive prompts
- Context object is never sent to LLM — purely dependency injection
