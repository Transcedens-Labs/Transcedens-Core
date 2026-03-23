import re
from typing import Optional, List
from langchain_core.messages import SystemMessage, HumanMessage
from .config import llm_reflex, graph_repo
from .cache_manager import get_cached_relationships, set_cached_relationships
from .prompts import REFLEX_ACTION_SYSTEM_PROMPT
from .schema import EntityExtractionResult

def generate_reflex_response(npc_id: str, persona_dna_str: str, immediate_stimulus: str, available_actions_override: Optional[List[str]] = None) -> dict:
    """
    Very fast < 1s latency call bypassing RAG databases completely. 
    Uses only Persona DNA and immediate stimulus to react as the 'Nervous System'.
    """
    constraint_msg = f"[SYSTEM OVERRIDE: You MAY ONLY choose physical actions from this exact list: {available_actions_override}.]" if available_actions_override is not None else "Check your Persona DNA for 'allowed_actions'. You may only choose physical actions explicitly listed there."
    sys_msg = SystemMessage(content=REFLEX_ACTION_SYSTEM_PROMPT.format(persona_dna=persona_dna_str, action_constraints=constraint_msg))
    response = llm_reflex.invoke([
        sys_msg, 
        HumanMessage(content=f"Stimulus: {immediate_stimulus}\nReact instantly:")
    ])
    response_text = str(response.content).strip()
    
    import re
    action_match = re.search(r"<ACTION>(.*?)</ACTION>", response_text, re.DOTALL)
    
    action_dict = {}
    reaction_speech = response_text
    
    if action_match:
        import json
        try:
            action_dict = json.loads(action_match.group(1).strip())
        except:
            pass
        reaction_speech = response_text[:action_match.start()].strip()
        
    return {"reaction": reaction_speech, "action": action_dict}

async def agenerate_reflex_stream(npc_id: str, persona_dna_str: str, immediate_stimulus: str, available_actions_override: Optional[List[str]] = None):
    """
    Native async generator for the Reflex endpoint, yielding event dicts for SSE.
    Implements a Hybrid Gated (System 1 / System 2) check to prevent unnecessary Neo4j reads.
    """
    # 1. Fetch Core Cache (System 1)
    core_map = get_cached_relationships(npc_id)
    if not core_map:
        core_map = graph_repo.get_top_relationships(npc_id=npc_id, limit=5)
        set_cached_relationships(npc_id, core_map)
    
    # Fast-Pass String Heuristic (Detecting unknown capitalized words)
    sentences = re.split(r'[.!?]\s+', immediate_stimulus)
    caps = []
    for s in sentences:
        words = s.strip().split()
        if len(words) > 1:
            caps.extend([w.strip('.,!?"\'') for w in words[1:] if w and w[0].isupper()])
            
    # Check if we have potential non-core entities
    needs_deep_think = False
    core_names = []
    for r in core_map:
        parts = r.split()
        if len(parts) >= 3:
            core_names.append(parts[0].lower())
            core_names.append(parts[2].lower())
    
    for c in caps:
        if c.lower() not in core_names and len(c) > 2:
            needs_deep_think = True
            break
            
    contextual_map = []
    if needs_deep_think:
        # Emit Cognitive Pause
        yield {"type": "cognitive_pause", "data": {"state": "extracting_memory", "entities_detected": caps[:3]}}
        
        # System 2: Extraction & DB Pull
        prompt = f"Identify the specific names of people or uniquely named entities interacting in this text. Reply ONLY with the names. Ignore objects.\nText: {immediate_stimulus}"
        llm_structured = llm_reflex.with_structured_output(EntityExtractionResult)
        try:
            res = await llm_structured.ainvoke([HumanMessage(content=prompt)])
            entities = res.entities if res else []
            if entities:
                if hasattr(graph_repo, "get_contextual_relationships"):
                    contextual_map = graph_repo.get_contextual_relationships(npc_id, entities)
        except Exception as e:
            print(f"Reflex extraction failed: {e}")
            
    final_map = list(set(core_map + contextual_map))
    context_injection = f"--- Memory Context ---\n" + "\n".join(final_map) + "\n\n" if final_map else ""

    constraint_msg = f"[SYSTEM OVERRIDE: You MAY ONLY choose physical actions from this exact list: {available_actions_override}.]" if available_actions_override is not None else "Check your Persona DNA for 'allowed_actions'. You may only choose physical actions explicitly listed there."
    sys_msg = SystemMessage(content=REFLEX_ACTION_SYSTEM_PROMPT.format(persona_dna=persona_dna_str, action_constraints=constraint_msg))
    
    buffer = ""
    in_action = False
    action_json_str = ""

    async for chunk in llm_reflex.astream([
        sys_msg, 
        HumanMessage(content=f"{context_injection}Stimulus: {immediate_stimulus}\nReact instantly:")
    ]):
        content = chunk.content
        if not content: continue
        if isinstance(content, list):
            text_parts = [part.get("text", "") if isinstance(part, dict) else str(part) for part in content]
            token = "".join(text_parts)
        else:
            token = str(content)
            
        if not token:
            continue

        if in_action:
            action_json_str += token
            continue
            
        buffer += token
        
        tag_idx = buffer.find("<ACTION>")
        if tag_idx != -1:
            if tag_idx > 0:
                yield {"type": "token", "data": buffer[:tag_idx]}
            in_action = True
            action_json_str = buffer[tag_idx + len("<ACTION>"):]
            buffer = ""
            continue
            
        lt_idx = buffer.rfind("<")
        if lt_idx != -1:
            potential_tag = buffer[lt_idx:]
            if "<ACTION>".startswith(potential_tag):
                if lt_idx > 0:
                    yield {"type": "token", "data": buffer[:lt_idx]}
                    buffer = buffer[lt_idx:]
            else:
                yield {"type": "token", "data": buffer}
                buffer = ""
        else:
            yield {"type": "token", "data": buffer}
            buffer = ""

    if buffer and not in_action:
        yield {"type": "token", "data": buffer}
        
    if in_action and action_json_str:
        action_json_str = action_json_str.replace("</ACTION>", "").strip()
        try:
            import json
            action_dict = json.loads(action_json_str)
            yield {"type": "action", "data": action_dict}
        except Exception as e:
            print(f"Failed to parse action JSON: {e}")

