from typing import Dict, Any
from .config import episodic_repo, graph_repo
from .schema import ReflectionResult, AUDNAction, MemoryBlock

def apply_reflection_result(npc_id: str, result_dict: Dict[str, Any]) -> bool:
    """
    Applies a ReflectionResult (mutations and memories) to local repositories.
    This is the 'Receiver' part of the Tier 1 Soul Bridge.
    """
    try:
        # 1. Parse into Structured Schema
        result = ReflectionResult(**result_dict)
        
        # 2. Apply Memory Blocks to Vector Store (Qdrant)
        if result.blocks:
            memories = [block.summary for block in result.blocks]
            metadatas = [{
                "importance": block.importance,
                "entities": block.associated_entities
            } for block in result.blocks]
            
            episodic_repo.add_memories(npc_id=npc_id, memories=memories, metadatas=metadatas)
            print(f"Applied {len(result.blocks)} memory blocks to Qdrant.")

        # 3. Apply Graph Mutations to Memory Map (Neo4j)
        if result.graph_mutations:
            # Convert objects to dicts for repository
            mutation_dicts = [m.model_dump() for m in result.graph_mutations]
            graph_repo.apply_mutations(npc_id=npc_id, mutations=mutation_dicts)
            print(f"Applied {len(result.graph_mutations)} graph mutations to Neo4j.")
            
        return True
        
    except Exception as e:
        print(f"Mutation Applier Error: {e}")
        return False
