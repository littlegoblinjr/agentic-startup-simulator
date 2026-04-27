from sentence_transformers import SentenceTransformer
import numpy as np

# Lazy-loaded model singleton — only downloaded/loaded on first use,
# not at import time. Prevents OOM crash during server startup on
# memory-constrained environments (e.g. Render free tier).
_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


async def get_embedding(text: str):
    model = _get_model()
    # Ensure text is in lower for consistency
    if isinstance(text, list):
        embeddings = model.encode([t.lower().strip() for t in text])
        return [e.tolist() for e in embeddings]
    
    embedding = model.encode(text.lower().strip())
    return embedding.tolist()