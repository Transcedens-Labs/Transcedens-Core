from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, START, END
from .config import llm_mind, checkpointer, episodic_repo, graph_repo
from .cache_manager import get_cached_relationships, set_cached_relationships
from .prompts import MIND_HEARTBEAT_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage

class HeartbeatState(TypedDict):
    npc_id: str
    persona_dna_str: str  
    current_context: str
    short_term_goals: str
    extracted_entities: List[str]
    map_context: List[str]
    vector_context: List[str]
    available_actions_override: Optional[List[str]]
    next_action: str
    action_meta: dict

def map_retrieval_node(state: HeartbeatState):
    """Retrieve overarching relational concepts about the NPC's world from Core Cache."""
    core_map = get_cached_relationships(state["npc_id"])
    if not core_map:
        core_map = graph_repo.get_top_relationships(npc_id=state["npc_id"], limit=5)
        set_cached_relationships(state["npc_id"], core_map)
        
    return {"map_context": core_map}

def vector_retrieval_node(state: HeartbeatState):
    """Retrieve episodic blocks relevant to current context and goals."""
    query_str = f"Goals: {state['short_term_goals']}. Context: {state['current_context']}."
    vector_context = episodic_repo.search_memories(npc_id=state["npc_id"], query=query_str, limit=3)
    return {"vector_context": vector_context}

def action_generation_node(state: HeartbeatState):
    """Generate the next tactical action using Gemini Flash (Mind)."""
    override = state.get('available_actions_override')
    constraint_msg = f"[SYSTEM OVERRIDE: You MAY ONLY choose physical actions from this exact list: {override}.]" if override is not None else "Check your Persona DNA for 'allowed_actions'. You may only choose physical actions explicitly listed there."
    
    sys_msg = SystemMessage(content=MIND_HEARTBEAT_SYSTEM_PROMPT.format(
        persona_dna=state["persona_dna_str"],
        action_constraints=constraint_msg
    ))
    
    context_str = "--- Inner Map ---\n" + "\n".join(state.get("map_context", []))
    context_str += "\n\n--- Past Experiences ---\n" + "\n".join(state.get("vector_context", []))
    
    prompt = f"Memory Context:\n{context_str}\n\nCurrent State:\n{state['current_context']}\nGoals: {state['short_term_goals']}\n\nWhat is your next action? Output only the action."
    
    response = llm_mind.invoke([sys_msg, HumanMessage(content=prompt)])
    
    import re
    full_text = str(response.content).strip()
    action_match = re.search(r"<ACTION>(.*?)</ACTION>", full_text, re.DOTALL)
    
    action_dict = {}
    next_action_speech = full_text
    
    if action_match:
        import json
        try:
            action_dict = json.loads(action_match.group(1).strip())
        except:
            pass
        next_action_speech = full_text[:action_match.start()].strip()
        
    return {"next_action": next_action_speech, "action_meta": action_dict}

heartbeat_builder = StateGraph(HeartbeatState)
heartbeat_builder.add_node("map_retrieval", map_retrieval_node)
heartbeat_builder.add_node("vector_retrieval", vector_retrieval_node)
heartbeat_builder.add_node("decide_action", action_generation_node)

heartbeat_builder.add_edge(START, "map_retrieval")
heartbeat_builder.add_edge(START, "vector_retrieval")
heartbeat_builder.add_edge("map_retrieval", "decide_action")
heartbeat_builder.add_edge("vector_retrieval", "decide_action")
heartbeat_builder.add_edge("decide_action", END)

# Note: We compile this inside server.py lifespan with AsyncRedisSaver
