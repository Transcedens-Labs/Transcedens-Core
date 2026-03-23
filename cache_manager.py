import json
from typing import List, Optional
from .config import redis_client

# --- Warm State Caching (Performance) ---
def set_warm_state(npc_id: str, persona_dna_str: str):
    """Cache the persona DNA in Redis to reduce client-side payload."""
    redis_client.set(f"warm_state:{npc_id}", persona_dna_str, ex=3600*24) # 24hr cache

def get_warm_state(npc_id: str) -> Optional[str]:
    """Retrieve the cached persona DNA."""
    return redis_client.get(f"warm_state:{npc_id}")

# --- Relational State Caching (Step 5 Optimization) ---
def set_cached_relationships(npc_id: str, relationships: List[str]):
    """Write-Through cache for top relationships to bypass Neo4j reads."""
    redis_client.set(f"rel_state:{npc_id}", json.dumps(relationships), ex=3600*24) # 24hr cache

def get_cached_relationships(npc_id: str) -> Optional[List[str]]:
    """Retrieve the cached top relationships. Returns None if cache miss."""
    cached = redis_client.get(f"rel_state:{npc_id}")
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None
    return None
