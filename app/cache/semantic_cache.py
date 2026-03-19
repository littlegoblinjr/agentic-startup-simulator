from app.tools.executor import execute_tool
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os

CACHE_FILE = "semantic_cache.json"

model = SentenceTransformer("all-MiniLM-L6-v2")

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        cache_data = json.load(f)
else:
    cache_data = []

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def find_similar(query_embedding, threshold=0.80):
    best_match = None
    best_score = 0

    for item in cache_data:
        cached_embedding = np.array(item["embedding"])
        score = cosine_similarity(query_embedding, cached_embedding)

        if score > threshold and score > best_score:
            best_score = score
            best_match = item

    return best_match


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f)


async def semantic_cached_search(query: str):

    query = query.lower().strip()

    query_embedding = model.encode(query)

    # 🔍 check semantic match
    match = find_similar(query_embedding)

    if match:
        print(f"[SEMANTIC CACHE HIT] {query} ~ {match['query']}")
        return match["result"]

    print(f"[CACHE MISS] {query}")

    # 🔥 CALL YOUR EXISTING TOOL (unchanged)
    result = await execute_tool("web_search", {"query": query})

    # ⚠️ only cache valid results
    if result and "results" in result and len(result["results"]) > 0:

        cache_data.append({
            "query": query,
            "embedding": query_embedding.tolist(),
            "result": result
        })

        save_cache()

    return result