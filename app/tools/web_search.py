from .base import BaseTool
from .registry import register_tool
from tavily import TavilyClient
import trafilatura
from app.memory.embeddings import get_embedding
import numpy as np
import asyncio

class WebSearchTool(BaseTool):


    name = "web_search"
    description = "Search the web for information"
    client = None
    
    def __init__(self):
        super().__init__()
        import os
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("WARNING: TAVILY_API_KEY not found in environment.")
        self.client = TavilyClient(api_key)
    
    #download the page and extract the text content
    def fetch_content(self, url: str):
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                return text
        except Exception:
            return None
        return None
    
    def chunk_text(self, text, chunk_size=400, overlap=100):
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk.split()) > 20:
                chunks.append(chunk)

        return chunks
    
    def cosine_sim(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    
    
    async def process_url(self, r, query_embedding):
        url = r["url"]
        title = r["title"]

        try:
            print(f"Fetching content from {url}...")
            content = await asyncio.to_thread(self.fetch_content, url)

            if not content:
                return None

            chunks = self.chunk_text(content)[:5]  # limit to first 5 chunks
            

            if not chunks:
                return None
            
            chunk_embeddings = await get_embedding(chunks)
            
            scores = [
                self.cosine_sim(query_embedding, emb)
                for emb in chunk_embeddings
            ]

            top_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:2]  # top 2 chunks

            # ✅ no embeddings anymore
            top_chunks = [chunks[i] for i in top_indices]  # just return the first 10 chunks
            

            return {
                "title": title,
                "url": url,
                "relevant_chunks": top_chunks
            }

        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            return None

    async def execute(self, query: str):

        
        print("Searching the web for: ", query)
            
        search_results = self.client.search(query, search_depth="advanced", max_results=2)
        
        final_results = []

        query_embedding = await get_embedding(query)

        for r in search_results["results"]:
            try:
                result = await asyncio.wait_for(
                    self.process_url(r, query_embedding),
                    timeout=5   # ⏱ 5 seconds per URL
                )

                if result:
                    final_results.append(result)

            except asyncio.TimeoutError:
                print(f"[TIMEOUT] Skipping slow URL: {r['url']}")
                continue

        # ✅ return structured (IMPORTANT)
        return {
            "query": query,
            "results": final_results
        }

register_tool(WebSearchTool())


