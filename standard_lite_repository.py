import uuid
from typing import List, Optional, Dict, Any
from .repository import BaseEpisodicRepository, BaseGraphRepository

class StandardLiteEpisodicRepository(BaseEpisodicRepository):
    """
    A zero-infrastructure episodic memory implementation.
    Stores memories in-memory (useful for local development/testing).
    Note: State is lost on server restart.
    """
    def __init__(self):
        self.memories: Dict[str, List[Dict[str, Any]]] = {}
        
    def add_memories(self, npc_id: str, memories: List[str], metadatas: Optional[List[dict]] = None) -> bool:
        if npc_id not in self.memories:
            self.memories[npc_id] = []
        
        for i, text in enumerate(memories):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            self.memories[npc_id].append({
                "id": str(uuid.uuid4()),
                "text": text,
                "metadata": meta
            })
        return True
        
    def search_memories(self, npc_id: str, query: str, limit: int = 5) -> List[str]:
        """Simple keyword-based 'search' for zero-infra lite mode."""
        if npc_id not in self.memories:
            return []
            
        npc_mems = self.memories[npc_id]
        # Very simple fuzzy match/keyword search for 'Lite' mode
        query_words = set(query.lower().split())
        scored_mems = []
        for mem in npc_mems:
            text = mem["text"].lower()
            score = sum(1 for word in query_words if word in text)
            scored_mems.append((score, mem["text"]))
            
        # Sort by score descending
        scored_mems.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored_mems[:limit]]

class StandardLiteGraphRepository(BaseGraphRepository):
    """
    A zero-infrastructure graph memory implementation.
    Stores relationships in a local dictionary.
    """
    def __init__(self):
        # Format: {npc_id: {(subject, predicate, object): strength}}
        self.graphs: Dict[str, Dict[tuple, float]] = {}
        
    def _ensure_npc(self, npc_id: str):
        if npc_id not in self.graphs:
            self.graphs[npc_id] = {}

    def apply_mutations(self, npc_id: str, mutations: List[dict]):
        self._ensure_npc(npc_id)
        for mutation in mutations:
            action = mutation.get("action_type")
            sub = mutation.get("subject")
            pred = (mutation.get("predicate") or "").upper().replace(" ", "_")
            obj = mutation.get("object")
            
            if not sub or not obj or not pred: continue
            
            key = (sub, pred, obj)
            if action in ["ADD", "UPDATE"]:
                # In Lite mode, we just store it. If mutation has strength, we use it.
                strength = mutation.get("strength_change", 1.0)
                current = self.graphs[npc_id].get(key, 0.0)
                self.graphs[npc_id][key] = max(0.0, min(1.0, current + strength))
            elif action == "DELETE":
                if key in self.graphs[npc_id]:
                    del self.graphs[npc_id][key]

    def get_top_relationships(self, npc_id: str, limit: int = 10) -> List[str]:
        if npc_id not in self.graphs: return []
        
        # Sort by 'strength' (value)
        items = list(self.graphs[npc_id].items())
        items.sort(key=lambda x: x[1], reverse=True)
        
        return [f"{s} {p} {o} (strength: {v:.2f})" for (s, p, o), v in items[:limit]]

    def search_relationships_by_entities(self, npc_id: str, entities: List[str], limit: int = 10) -> List[str]:
        if npc_id not in self.graphs or not entities: return []
        
        results = []
        entities_lower = [e.lower() for e in entities]
        
        for (s, p, o), v in self.graphs[npc_id].items():
            s_low, o_low = s.lower(), o.lower()
            if any(e in s_low or s_low in e or e in o_low or o_low in e for e in entities_lower):
                results.append((v, f"{s} {p} {o}"))
                
        results.sort(key=lambda x: x[0], reverse=True)
        return [text for v, text in results[:limit]]

    def apply_global_decay(self, npc_id: str, decay_amount: float = 0.05):
        if npc_id not in self.graphs: return
        
        to_delete = []
        for key, v in self.graphs[npc_id].items():
            new_v = v - decay_amount
            if new_v <= 0:
                to_delete.append(key)
            else:
                self.graphs[npc_id][key] = new_v
                
        for key in to_delete:
            del self.graphs[npc_id][key]
