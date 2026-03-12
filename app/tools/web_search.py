from .base import BaseTool
from .registry import register_tool
from tavily import TavilyClient

class WebSearchTool(BaseTool):


    name = "web_search"
    description = "Search the web for information"
    client = TavilyClient(r"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")
    async def execute(self, query: str):

        results = []
        print("Searching the web for: ", query)
            
        search_results = self.client.search(query, search_depth="advanced", max_results=5)
        #print("Search results: ", search_results)
        for r in search_results["results"]:
                results.append(
                    f"{r['title']} - {r['url']}\n{r['content']}"
                )



        return f"Results for {query}: \n\n" + "\n\n".join(results)


register_tool(WebSearchTool())


