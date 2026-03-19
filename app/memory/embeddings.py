from sentence_transformers import SentenceTransformer
import numpy as np

# Load local model (Matches semantic_cache.py)
# Dimensions: 384
model = SentenceTransformer("all-MiniLM-L6-v2")


async def get_embedding(text: str):
    # Ensure text is in lower for consistency
    if isinstance(text, list):
        embeddings = model.encode([t.lower().strip() for t in text])
        return [e.tolist() for e in embeddings]
    
    embedding = model.encode(text.lower().strip())
    return embedding.tolist()