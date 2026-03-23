from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator, Dict, Any
import json
import uvicorn
from sse_starlette.sse import EventSourceResponse

from .reflex_api import agenerate_reflex_stream
from .heartbeat_graph import heartbeat_builder
from .config import llm_mind, DB_MODE

app = FastAPI(
    title="Transcedens-Core Open API",
    description="Minimal standalone API for Transcedens NPCs.",
    version="0.1.0"
)

# --- Request Models ---

class ReflexRequest(BaseModel):
    npc_id: str = Field(..., description="Unique identifier for the NPC.")
    persona_dna_str: str = Field(..., description="The core personality and behavioral rules for the NPC.")
    immediate_stimulus: str = Field(..., description="The player input or world event to react to.")
    available_actions_override: Optional[List[str]] = Field(None, description="Optional list of physical actions the NPC is restricted to.")

class MindRequest(BaseModel):
    npc_id: str = Field(..., description="Unique identifier for the NPC.")
    persona_dna_str: str = Field(..., description="The core personality and behavioral rules for the NPC.")
    current_context: str = Field(..., description="Environmental or situational context at the moment of the heartbeat.")
    short_term_goals: str = Field(..., description="The technical objectives or tactical plans currently active.")
    available_actions_override: Optional[List[str]] = Field(None, description="Optional list of physical actions the NPC is restricted to.")

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "online", "db_mode": DB_MODE}

@app.post("/api/v1/reflex/stream")
async def reflex_stream(req: ReflexRequest):
    """
    Standalone Reflex endpoint for System 1 reactions.
    """
    async def event_generator():
        try:
            async for chunk in agenerate_reflex_stream(
                req.npc_id, 
                req.persona_dna_str, 
                req.immediate_stimulus, 
                req.available_actions_override
            ):
                yield {"data": json.dumps(chunk)}
            yield {"event": "done", "data": "null"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())

@app.post("/api/v1/mind/heartbeat")
async def mind_heartbeat(req: MindRequest):
    """
    Standalone Mind endpoint for System 2 planning.
    Note: In Lite Mode, this uses local state instead of Neo4j/Qdrant.
    """
    # Compile the graph without checkpointers for simplicity in the open core version
    # Users can add checkpointers if they setup Redis
    mind_graph = heartbeat_builder.compile()
    
    state = {
        "npc_id": req.npc_id,
        "persona_dna_str": req.persona_dna_str,
        "current_context": req.current_context,
        "short_term_goals": req.short_term_goals,
        "map_context": [],
        "vector_context": [],
        "available_actions_override": req.available_actions_override,
        "next_action": "",
        "action_meta": {}
    }

    try:
        final_state = await mind_graph.ainvoke(state)
        return {
            "action": final_state.get("next_action"),
            "meta": final_state.get("action_meta"),
            "context_used": {
                "map": final_state.get("map_context", []),
                "vector": final_state.get("vector_context", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("core.api:app", host="0.0.0.0", port=8000, reload=True)
