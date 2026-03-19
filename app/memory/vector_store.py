from typing import List

from .embeddings import get_embedding
from pydantic import BaseModel
from .db import execute, fetch
import json
from app.core.llm_config import client, DEFAULT_MODEL

async def store_memory(content:str, metadata: dict):
    embedding  = await get_embedding(content)
    
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    
    await execute(
        """
    INSERT INTO memories (content, embedding, metadata)
    VALUES ($1, $2, $3)
    """,
        
        content, embedding_str, json.dumps(metadata)
    )
    
async def retrieve_memory(query: str, memory_type: str, k: int = 5):
    query_embedding  = await get_embedding(query)
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    rows = await fetch(
        """
        SELECT content, embedding <-> $1 AS distance
        FROM memories
        WHERE metadata->>'type' = $2
        ORDER BY embedding <-> $1
        LIMIT $3   
        """
        ,
        embedding_str, memory_type, k
    )
    
    if not rows:
        return []

    return [
    {
        "content": r["content"],
        "distance": r["distance"]
    }
    for r in rows
]
    
class ReRankItem(BaseModel):
    index: int
    score: float 
       
class ReRankSchema(BaseModel):
    ranking: List[ReRankItem]
    
    
async def rerank(query, rows, telemetry=None):
    if not rows:
        return []
    
    texts = [r["content"] for r in rows]
    prompt = f"""
    You are a reranking system.
    Rank these documents by relevance to the query.
    Return JSON format: {{"ranking": [{{"index": int, "score": float}}]}}
    Rules:
    - index MUST be between 0 and {len(rows)-1}
    """
    
    try:
        response = await client.beta.chat.completions.parse(
            model = DEFAULT_MODEL,
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments:\n" + "\n\n".join(texts)}
            ],
            response_format = ReRankSchema
        )
        
        usage = response.usage.model_dump() if hasattr(response, "usage") else None
        if telemetry:
            telemetry.log_event("vector_store", "rerank", {"query": query, "count": len(rows)}, usage=usage)
            
        reranked = response.choices[0].message.parsed.ranking
        reranked_rows = []
        for item in reranked:
            if 0 <= item.index < len(rows):
                row = rows[item.index].copy()
                row["rerank_score"] = item.score
                reranked_rows.append(row)
        return reranked_rows
    except Exception as e:
        print(f"RERANK ERROR: {e}")
        return rows # Fallback to original order