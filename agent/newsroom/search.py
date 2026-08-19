"""
Newsroom Module - Web search capability for market intelligence.
Provides external context to complement internal data analysis.
"""
from typing import List, Optional
import asyncio
from duckduckgo_search import DDGS
import trafilatura
import httpx
from api.config import settings


class Newsroom:
    """
    Autonomous web search engine for market context.
    Fetches relevant news, competitor info, and industry trends.
    """
    
    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else settings.newsroom.enabled
        self.max_results = settings.newsroom.max_results
        self.timeout = settings.newsroom.timeout_seconds
    
    async def search_market_context(
        self, 
        query: str, 
        topic: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Search for market context related to a business question.
        
        Args:
            query: The search query (e.g., "SaaS churn rates 2026")
            topic: Optional topic category for filtering
            limit: Override max_results
            
        Returns:
            Formatted string with search results and sources
        """
        if not self.enabled:
            return "External search disabled (air-gap mode or configuration)."
        
        limit = limit or self.max_results
        
        try:
            # Perform DuckDuckGo search
            results = await self._search_web(query, limit)
            
            if not results:
                return f"No external information found for: {query}"
            
            # Format results
            formatted = self._format_results(results, query)
            return formatted
            
        except Exception as e:
            return f"Search failed: {str(e)}. Proceeding with internal data only."
    
    async def _search_web(self, query: str, limit: int) -> List[dict]:
        """Execute web search using DuckDuckGo."""
        loop = asyncio.get_event_loop()
        
        def sync_search():
            results = []
            try:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=limit))
                    for res in search_results:
                        results.append({
                            'title': res.get('title', 'No title'),
                            'body': res.get('body', 'No description'),
                            'url': res.get('href', ''),
                            'source': self._extract_domain(res.get('href', ''))
                        })
            except Exception as e:
                print(f"DuckDuckGo search error: {e}")
            return results
        
        return await loop.run_in_executor(None, sync_search)
    
    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and extract main content from a webpage."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Extract main content using trafilatura
                content = trafilatura.extract(response.text)
                return content
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None
    
    def _format_results(self, results: List[dict], query: str) -> str:
        """Format search results into readable context."""
        if not results:
            return "No relevant external information found."
        
        header = f"📰 Market Intelligence for: {query}\n"
        header += "=" * 50 + "\n\n"
        
        body = ""
        for i, res in enumerate(results, 1):
            body += f"[{i}] **{res['title']}**\n"
            body += f"   Source: {res['source']}\n"
            body += f"   {res['body']}\n"
            body += f"   URL: {res['url']}\n\n"
        
        footer = "\n💡 Tip: Cross-reference these insights with internal data."
        
        return header + body + footer
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return "Unknown"
    
    async def get_competitor_intel(self, company_names: List[str]) -> str:
        """Get intelligence on specific competitors."""
        queries = [f"{name} recent news 2026", f"{name} product launches"]
        
        all_results = []
        for query in queries:
            results = await self.search_market_context(query, limit=3)
            all_results.append(results)
        
        return "\n\n".join(all_results)
    
    async def get_industry_trends(self, industry: str) -> str:
        """Get trending topics in a specific industry."""
        query = f"{industry} trends 2026 market analysis"
        return await self.search_market_context(query, limit=5)


# Singleton instance
newsroom = Newsroom()
