from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal

class PersonaDNA(BaseModel):
    model_config = ConfigDict(extra='allow')
    name: str = Field(description="Name of the NPC")
    core_identity: str = Field(description="The fundamental nature of the NPC (e.g. 'A cynical former soldier')")
    beliefs: List[str] = Field(description="Core beliefs that dictate worldview")
    goals: List[str] = Field(description="Long-term desires or objectives")
    biases: List[str] = Field(description="Irrational prejudices or hardwired tendencies")
    relationships: dict[str, str] = Field(default_factory=dict, description="Key pre-existing relationships mapped by Name -> Description")
    allowed_actions: List[str] = Field(default_factory=lambda: ["MOVE", "INTERACT", "FLEE", "ATTACK", "GIVE_ITEM", "USE_ITEM"], description="Default physical verbs available to the NPC.")
    version: int = Field(default=1, description="Evolution version of the persona")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last reflection evolution")

class SessionContext(BaseModel):
    business_id: str
    session_id: str
    npc_id: str

class MemoryBlock(BaseModel):
    summary: str = Field(description="Narrative summary of the events")
    importance: float = Field(description="Scale of 0.0 to 1.0 on how important this memory is")
    associated_entities: List[str] = Field(description="Entities involved in this memory")

class AUDNAction(BaseModel):
    action_type: Literal["ADD", "UPDATE", "DELETE", "NOOP"] = Field(description="The graph mutation type")
    subject: Optional[str] = Field(None, description="The entity performing the action or holding the relationship")
    predicate: Optional[str] = Field(None, description="The relationship or state (e.g. LIKES, FEARS)")
    object: Optional[str] = Field(None, description="The target entity")
    reasoning: str = Field(description="Explanation for why this action was chosen based on the Persona DNA")
    strength_change: Optional[float] = Field(0.0, description="If ADD/UPDATE, how much the relationship strength changes (-1.0 to 1.0)")

class ReflectionResult(BaseModel):
    blocks: List[MemoryBlock] = Field(description="Extracted narrative memory blocks")
    graph_mutations: List[AUDNAction] = Field(description="Graph changes based on the reflected events")

class EntityExtractionResult(BaseModel):
    entities: List[str] = Field(default_factory=list, description="List of names or specific unique entities extracted from the text. Empty if none.")

class WorldAction(BaseModel):
    action_type: str = Field(description="The generic type of physical action, e.g., 'MOVE', 'INTERACT', 'GIVE', 'USE', 'ATTACK'. Expandable to custom values.")
    target_entity: Optional[str] = Field(None, description="The specific name or ID of the entity this action targets, if any.")
    parameters: dict = Field(default_factory=dict, description="Any additional parameters for the action.")
