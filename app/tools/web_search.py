from .base import BaseTool
from .registry import register_tool
from duckduckgo_search import DDGS

class WebSearchTool(BaseTool):


    name = "web_search"
    description = "Search the web for information"

    async def execute(self, query: str):

        results = []
        print("Searching the web for: ", query)
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results = 10, region="us-en")
            print("Search results: ", search_results)
            for r in search_results:
                results.append(
                    f"{r['title']} - {r['href']}\n{r['body']}"
                )



        return f"Results for {query}: \n\n" + "\n\n".join(results)


register_tool(WebSearchTool())


