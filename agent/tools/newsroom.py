"""
Newsroom Tool - Web Search for Market Intelligence.
Enables the agent to stay updated with external signals.
"""
from typing import List, Optional
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup


class NewsroomTool:
    """
    Provides web search capabilities to the agent.
    Fetches real-time market data, competitor news, and industry trends.
    """

    def __init__(self, enabled: bool = True, max_results: int = 5):
        self.enabled = enabled
        self.max_results = max_results

    async def search(self, query: str, topic: str = "general") -> str:
        """
        Search the web for relevant information.
        
        Args:
            query: Search query string
            topic: Context topic (e.g., "competitor", "market", "regulation")
            
        Returns:
            Formatted search results as context string
        """
        if not self.enabled:
            return "External search is disabled in configuration."

        try:
            results = []
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=self.max_results))
                
                for res in search_results:
                    title = res.get('title', 'No title')
                    body = res.get('body', 'No description')
                    href = res.get('href', '')
                    
                    # Optionally fetch full content if needed
                    content = body
                    if href and len(body) < 100:
                        content = await self._fetch_page_content(href)
                    
                    results.append(f"[Source: {title}]({href})\n{content}\n")

            if not results:
                return f"No external information found for: {query}"

            context = f"## External Intelligence: {topic}\n\n" + "\n---\n".join(results)
            return context

        except Exception as e:
            return f"Search failed: {str(e)}. Proceeding with internal data only."

    async def _fetch_page_content(self, url: str, timeout: int = 5) -> str:
        """Fetch and extract main content from a webpage."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Extract clean text
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts and styles
                for script in soup(["script", "style", "nav", "footer"]):
                    script.decompose()
                
                text = soup.get_text(separator=' ', strip=True)
                # Limit content length
                return text[:1000] if len(text) > 1000 else text
                
        except Exception:
            return ""

    def generate_search_queries(self, user_query: str, business_context: str) -> List[str]:
        """
        Generate relevant search queries based on user question and business context.
        This helps the agent know WHAT to search for.
        """
        queries = []
        
        # Always include a general market context query
        queries.append(f"{business_context} market trends 2024")
        
        # If user query mentions specific topics, add targeted searches
        keywords = ["competitor", "pricing", "regulation", "law", "policy", "market share"]
        for keyword in keywords:
            if keyword in user_query.lower():
                queries.append(f"{user_query} {keyword}")
                break
        
        return queries[:3]  # Limit to 3 queries max
