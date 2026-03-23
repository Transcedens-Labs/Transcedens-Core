import httpx
import os
import asyncio
from typing import Optional, Dict, List
from .config import redis_client

async def trigger_remote_reflection(
    npc_id: str, 
    business_id: str, 
    session_id: str, 
    persona_dna: Optional[Dict] = None,
    recreate_persona: bool = False
) -> Optional[Dict]:
    """
    Open Core Handover Hook (Data-Pushing Model).
    Gathers local logs and DNA to send to the proprietary Cloud Soul.
    """
    # The URL of the proprietary SAAS endpoint
    api_url = os.getenv("SAAS_REFLECTION_URL", "http://localhost:8000/api/v1/soul/reflect")
    api_key = os.getenv("SAAS_API_KEY", "dev-key-123")
    
    # Step 1: Gather local state (Action Logs from Redis)
    log_key = f"logs:{business_id}:{session_id}:{npc_id}"
    try:
        # Fetch and clear logs to prevent double-reflection
        pipe = redis_client.pipeline()
        pipe.lrange(log_key, 0, -1)
        pipe.delete(log_key)
        results = pipe.execute()
        action_logs = results[0]
    except Exception as e:
        print(f"Reflection Hook: Error fetching logs from Redis: {e}")
        action_logs = []

    if not action_logs and not recreate_persona:
        return {"status": "skipped", "message": "No new logs to reflect upon."}

    headers = {
        "X-API-Key": api_key,
        "X-Session-ID": session_id,
        "Content-Type": "application/json"
    }
    
    payload = {
        "npc_id": npc_id,
        "action_logs": action_logs,
        "persona_dna": persona_dna,
        "recreate_persona": recreate_persona,
        "sync": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Deep reflection can involve multiple LLM calls and significant batching
            response = await client.post(api_url, json=payload, headers=headers, timeout=120.0)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            print(f"Proprietary Reflection Hook Failed with Status: {e.response.status_code}")
            return None
            
        except httpx.RequestError as e:
            print(f"Proprietary Reflection Hook Network Error: {e}")
            # Recommended Open-source fallback: 
            # Implement a dead-letter queue (e.g., Redis list) here to save `npc_id` 
            # for retry so the action memory queue is not flushed without reflection.
            return None
