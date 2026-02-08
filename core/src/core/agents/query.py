from agents import Agent

from ..context import GraphContext
from ..tools import READ_TOOLS

BASE_QUERY_INSTRUCTIONS = """You are an organizational knowledge graph query agent. You answer questions by searching and traversing the knowledge graph.

## Your Workflow

### Step 1: Search
Start by understanding the question. Then:
- Call similarity_search with the key concepts from the question
- Call search_nodes for specific names, projects, or terms mentioned
- If the question is about recent changes, call get_recent_changes

### Step 2: Traverse
For each relevant search result:
- Call read_node to get the full content
- Call list_links to see connected nodes
- Follow the most promising links by reading those nodes too

Explore at least 2-3 nodes deep via wikilinks. Don't stop at the first result.

### Step 3: Synthesize
Compose your answer from what you've gathered:
- Direct answers to the question
- Relevant context the questioner should know
- Attribution: cite which nodes using [[node-name]] format

## Rules
- Do NOT make up information. If the graph doesn't contain the answer, say so.
- Do NOT call the same tool with identical arguments twice.
- If you find conflicting information across nodes, flag the contradiction.
- Cite your sources using [[node-name]] wikilink format.
"""


def make_query_agent(user_text: str) -> Agent[GraphContext]:
    """Create a query agent. The user's full text IS the perspective — we pass it
    as context in the instructions so the agent tailors depth/framing accordingly."""
    instructions = f"""The user asked: "{user_text}"

Tailor your response to match what this person seems to need — if they mention being a CEO or executive, be concise and strategic. If they ask technical questions, be detailed. If they seem new, explain context. If unclear, default to a thorough but readable response.

{BASE_QUERY_INSTRUCTIONS}"""
    return Agent[GraphContext](
        name="Query Agent",
        instructions=instructions,
        tools=READ_TOOLS,
        model="gpt-4.1",
    )
