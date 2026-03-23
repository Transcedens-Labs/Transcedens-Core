from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseEpisodicRepository(ABC):
    @abstractmethod
    def add_memories(self, npc_id: str, memories: List[str], metadatas: Optional[List[dict]] = None) -> bool:
        pass
        
    @abstractmethod
    def search_memories(self, npc_id: str, query: str, limit: int = 5) -> List[str]:
        pass

class BaseGraphRepository(ABC):
    @abstractmethod
    def apply_mutations(self, npc_id: str, mutations: List[dict]):
        pass
        
    @abstractmethod
    def get_top_relationships(self, npc_id: str, limit: int = 10) -> List[str]:
        pass

    @abstractmethod
    def search_relationships_by_entities(self, npc_id: str, entities: List[str], limit: int = 10) -> List[str]:
        pass

    @abstractmethod
    def apply_global_decay(self, npc_id: str, decay_amount: float = 0.05):
        pass
