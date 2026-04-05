import os
import redis
from typing import List, Optional, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from langchain_neo4j import Neo4jGraph
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model
from .standard_repository import StandardEpisodicRepository, StandardGraphRepository

load_dotenv()

# --- Memory Repositories (Open Core Abstraction Layer) ---
DB_MODE = os.getenv("DB_MODE", "LITE") # OPTIONS: STANDARD, LITE

# --- Open Core Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google_genai")

# --- 3-Tier Cognitive Stack LLMs ---
# Automatically routes to correct provider (openai, anthropic, ollama, etc.) based on LLM_PROVIDER

# The Reflex: Nervous System (< 1s latency)
llm_reflex = init_chat_model(
    model=os.getenv("REFLEX_MODEL", "gemini-3.1-flash-lite-preview"),
    model_provider=LLM_PROVIDER,
    temperature=0.4,
    max_tokens=60
)

# The Mind: Consciousness (1-10 Min latency)
llm_mind = init_chat_model(
    model=os.getenv("MIND_MODEL", "gemini-3.1-flash-lite-preview"),
    model_provider=LLM_PROVIDER,
    temperature=0.2
)

# Alias for legacy components until fully refactored
llm = llm_mind

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2-preview", 
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

if DB_MODE == "STANDARD":
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY", None)
    )
else:
    qdrant_client = None

def get_vector_store(collection_name: str) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embeddings
    )

def get_neo4j_graph() -> Optional[Neo4jGraph]:
    if DB_MODE == "LITE": return None
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )

# (DB_MODE is moved up)

if DB_MODE == "LITE":
    from .standard_lite_repository import StandardLiteEpisodicRepository, StandardLiteGraphRepository
    episodic_repo = StandardLiteEpisodicRepository()
    graph_repo = StandardLiteGraphRepository()
else:
    from .standard_repository import StandardEpisodicRepository, StandardGraphRepository
    episodic_repo = StandardEpisodicRepository(get_vector_store("npc_memories"))
    graph_repo = StandardGraphRepository(get_neo4j_graph())

# Redis 'Warm State' Buffer Connection
if DB_MODE == "STANDARD":
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    # LangGraph Redis Checkpointer
    from langgraph.checkpoint.redis import RedisSaver
    checkpointer = RedisSaver.from_conn_string(redis_url)
else:
    redis_client = None
    # LangGraph Memory Checkpointer (Zero-Infra)
    checkpointer = MemorySaver()
