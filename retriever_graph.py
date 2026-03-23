import os
from typing import List, Optional, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field, ConfigDict

from .config import llm, episodic_repo, graph_repo

def get_content(content) -> str:
    """Ensure LLM content is a string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
        return "".join(text_parts)
    return str(content)

class RetrieverState(TypedDict):
    npc_id: str
    persona_profile: str
    question: str
    map_context: List[str]
    vector_context: List[str]
    final_response: str

class EntityExtraction(BaseModel):
    model_config = ConfigDict(extra='allow')
    entities: List[str] = Field(description="Names of people, objects, locations, or concepts.")

# Node 1: Memory Map Retrieval
def map_retrieval_node(state: RetrieverState):
    # Extract entities from question to search graph
    sys_msg = SystemMessage(content="Extract key entities from the question to search in a memory graph.")
    llm_structured = llm.with_structured_output(EntityExtraction)
    res = llm_structured.invoke([sys_msg, HumanMessage(content=state["question"])])
    
    entities = res.entities if res and res.entities else []
    
    map_context = []
    if entities:
        map_context = graph_repo.search_relationships_by_entities(
            npc_id=state["npc_id"], 
            entities=entities, 
            limit=10
        )
            
    return {"map_context": map_context}

# Node 2: Vector Store Retrieval
def vector_retrieval_node(state: RetrieverState):
    # Enrich query
    enriched_query = state["question"]
    if state.get("map_context"):
        enriched_query += "\nGraph Context: " + ", ".join(state["map_context"])
        
    vector_context = episodic_repo.search_memories(
        npc_id=state["npc_id"], 
        query=enriched_query, 
        limit=5
    )
        
    return {"vector_context": vector_context}

# Node 3: Response Generation
def response_generation_node(state: RetrieverState):
    persona = state["persona_profile"]
    sys_msg = SystemMessage(content=f"You are the NPC. Embody this persona completely:\n{persona}\n\nUse the provided memory context to answer the user's question, but do not break character or mention that you are an AI or that you are looking at 'memory context'. Speak directly as the character.")
    
    context_str = "--- Graph Memory ---\n" + "\n".join(state.get("map_context", []))
    context_str += "\n\n--- Detailed Memories ---\n" + "\n".join(state.get("vector_context", []))
    
    prompt = f"Memory Context:\n{context_str}\n\nQuestion:\n{state['question']}"
    
    response = llm.invoke([sys_msg, HumanMessage(content=prompt)])
    
    return {"final_response": get_content(response.content)}

# Build Retriever Graph
builder = StateGraph(RetrieverState)
builder.add_node("map_retrieval", map_retrieval_node)
builder.add_node("vector_retrieval", vector_retrieval_node)
builder.add_node("response", response_generation_node)

builder.add_edge(START, "map_retrieval")
builder.add_edge("map_retrieval", "vector_retrieval")
builder.add_edge("vector_retrieval", "response")
builder.add_edge("response", END)

retriever_graph = builder.compile()
