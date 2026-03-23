from typing import List, Optional
from langchain_neo4j import Neo4jGraph
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue
from .repository import BaseEpisodicRepository, BaseGraphRepository

class StandardEpisodicRepository(BaseEpisodicRepository):
    """A standard episodic memory implementation using Qdrant."""
    def __init__(self, vector_store: QdrantVectorStore):
        self.vector_store = vector_store
        
    def add_memories(self, npc_id: str, memories: List[str], metadatas: Optional[List[dict]] = None) -> bool:
        if not metadatas:
            metadatas = [{"npc_id": npc_id} for _ in memories]
        else:
            for meta in metadatas:
                meta["npc_id"] = npc_id
        self.vector_store.add_texts(texts=memories, metadatas=metadatas)
        return True
        
    def search_memories(self, npc_id: str, query: str, limit: int = 5) -> List[str]:
        filter_obj = Filter(
            must=[FieldCondition(key="metadata.npc_id", match=MatchValue(value=npc_id))]
        )
        results = self.vector_store.similarity_search(query=query, k=limit, filter=filter_obj)
        return [doc.page_content for doc in results]

class StandardGraphRepository(BaseGraphRepository):
    """A basic graph memory implementation using Neo4j."""
    def __init__(self, graph: Neo4jGraph):
        self.graph = graph
        
    def apply_mutations(self, npc_id: str, mutations: List[dict]):
        """Standard implementation of graph updates (no complex A.U.D.N logic)."""
        for mutation in mutations:
            action_type = mutation.get("action_type")
            sub = mutation.get("subject")
            pred = (mutation.get("predicate") or "").upper().replace(" ", "_")
            obj = mutation.get("object")
            
            if not sub or not obj or not pred:
                continue

            if action_type in ["ADD", "UPDATE"]:
                query = f"""
                MERGE (s:Entity {{name: $sub, npc_id: $npc_id}})
                MERGE (o:Entity {{name: $obj, npc_id: $npc_id}})
                MERGE (s)-[r:{pred}]->(o)
                SET r.last_updated = timestamp()
                """
                self.graph.query(query, params={"sub": sub, "obj": obj, "npc_id": npc_id})
            elif action_type == "DELETE":
                query = f"""
                MATCH (s:Entity {{name: $sub, npc_id: $npc_id}})-[r:{pred}]->(o:Entity {{name: $obj, npc_id: $npc_id}})
                DELETE r
                """
                self.graph.query(query, params={"sub": sub, "obj": obj, "npc_id": npc_id})
                
    def get_top_relationships(self, npc_id: str, limit: int = 10) -> List[str]:
        query = """
        MATCH (s:Entity {npc_id: $npc_id})-[r]->(o:Entity {npc_id: $npc_id})
        RETURN s.name AS sub, type(r) AS rel, o.name AS obj
        LIMIT $limit
        """
        results = self.graph.query(query, params={"npc_id": npc_id, "limit": limit})
        return [f"{res['sub']} {res['rel']} {res['obj']}" for res in results]

    def search_relationships_by_entities(self, npc_id: str, entities: List[str], limit: int = 10) -> List[str]:
        if not entities: return []
        query = """
        UNWIND $entities AS ent
        MATCH (e:Entity {npc_id: $npc_id})-[r]-(e2:Entity)
        WHERE toLower(e.name) CONTAINS toLower(ent) OR toLower(ent) CONTAINS toLower(e.name)
        RETURN DISTINCT e.name AS src, type(r) AS rel, e2.name AS dst
        LIMIT $limit
        """
        results = self.graph.query(query, params={"entities": entities, "npc_id": npc_id, "limit": limit})
        return [f"{res['src']} {res['rel']} {res['dst']}" for res in results]

    def apply_global_decay(self, npc_id: str, decay_amount: float = 0.05):
        """Standard decay does nothing or basic archival (Placeholder for Open Core)."""
        pass
