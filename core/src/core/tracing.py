"""Capture agent tool call traces during ingestion for visualization."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

from agents import Agent, RunHooks, Tool
from agents.run_context import RunContextWrapper
from agents.tool_context import ToolContext

from .context import GraphContext

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

ACTION_MAP = {
    "tool_similarity_search": "search",
    "tool_read_node": "read",
    "tool_list_links": "list_links",
    "tool_search_nodes": "search",
    "tool_create_node": "create",
    "tool_update_node": "update",
    "tool_get_recent_changes": "recent_changes",
}


@dataclass
class TraceStep:
    t: int
    ts: float
    action: str
    tool: str
    args: dict
    result_summary: str
    nodes: list[str]


class TracingHooks(RunHooks[GraphContext]):
    def __init__(self) -> None:
        self.steps: list[TraceStep] = []
        self._pending: dict[str, dict] = {}
        self._counter = 0
        self._start = time.monotonic()

    async def on_tool_start(
        self,
        context: RunContextWrapper[GraphContext],
        agent: Agent,
        tool: Tool,
    ) -> None:
        call_id = ""
        args: dict = {}
        if isinstance(context, ToolContext):
            call_id = context.tool_call_id
            try:
                args = json.loads(context.tool_arguments)
            except (json.JSONDecodeError, TypeError):
                args = {"_raw": context.tool_arguments}
        self._pending[call_id] = {"tool": tool.name, "args": args}

    async def on_tool_end(
        self,
        context: RunContextWrapper[GraphContext],
        agent: Agent,
        tool: Tool,
        result: str,
    ) -> None:
        call_id = ""
        if isinstance(context, ToolContext):
            call_id = context.tool_call_id

        pending = self._pending.pop(call_id, {"tool": tool.name, "args": {}})
        action = ACTION_MAP.get(pending["tool"], "unknown")
        args = pending["args"]

        # Truncate large content args (create/update node bodies)
        if action in ("create", "update") and "content" in args:
            args = {**args, "content": f"({len(args['content'])} chars)"}

        # Extract node names from args + result
        nodes_from_args = [args["name"]] if "name" in args else []
        nodes_from_result = WIKILINK_RE.findall(result[:500])
        all_nodes = list(dict.fromkeys(nodes_from_args + nodes_from_result))

        self.steps.append(
            TraceStep(
                t=self._counter,
                ts=round(time.monotonic() - self._start, 3),
                action=action,
                tool=pending["tool"],
                args=args,
                result_summary=result[:200],
                nodes=all_nodes,
            )
        )
        self._counter += 1

    def to_list(self) -> list[dict]:
        return [
            {
                "t": s.t,
                "ts": s.ts,
                "action": s.action,
                "tool": s.tool,
                "args": s.args,
                "result_summary": s.result_summary,
                "nodes": s.nodes,
            }
            for s in self.steps
        ]
