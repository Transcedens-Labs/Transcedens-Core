import mcp.types as types
from mcp.server import Server
from typing import Any

from .standard_repository import StandardEpisodicRepository, StandardGraphRepository
from .config import get_vector_store, get_neo4j_graph

# Create a unified MCP server instance for memory access
mcp_server = Server("transcedens-memory-mcp")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available memory tools.
    Provides standardized MCP access to the underlying Qdrant and Neo4j repositories.
    """
    return [
        types.Tool(
            name="search_episodic_memory",
            description="Search the episodic memory (Vector DB) for past events relevant to a query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "npc_id": {"type": "string", "description": "The ID of the NPC whose memory to search"},
                    "query": {"type": "string", "description": "The search query based on current context"},
                    "limit": {"type": "integer", "description": "Maximum number of memories to return", "default": 5}
                },
                "required": ["npc_id", "query"]
            }
        ),
        types.Tool(
            name="get_relationships",
            description="Get the relational memory graph (Graph DB) showing how this NPC feels about other entities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "npc_id": {"type": "string", "description": "The ID of the NPC whose relationships to fetch"}
                },
                "required": ["npc_id"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """
    Execute a memory tool call.
    Uses the abstract Repository pattern to interact with the databases.
    """
    if not arguments:
        raise ValueError("Missing arguments")

    npc_id = arguments.get("npc_id")
    if not npc_id:
        raise ValueError("Missing required argument: npc_id")

    if name == "search_episodic_memory":
        query = arguments.get("query")
        limit = arguments.get("limit", 5)
        
        # Instantiate repository using the active connection
        repo = StandardEpisodicRepository(get_vector_store("npc_memories"))
        results = repo.search_memories(npc_id=npc_id, query=query, limit=limit)
        
        # Return as an MCP TextContent block
        formatted = "\n".join(f"- {mem}" for mem in results) if results else "No relevant episodic memories found."
        return [types.TextContent(type="text", text=formatted)]

    elif name == "get_relationships":
        # Instantiate repository using the active connection
        repo = StandardGraphRepository(get_neo4j_graph())
        results = repo.get_top_relationships(npc_id=npc_id)
        
        # Return as an MCP TextContent block
        formatted = "\n".join(f"- {rel}" for rel in results) if results else "No significant relationships found."
        return [types.TextContent(type="text", text=formatted)]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdio transport (standard for local MCP tools)
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
