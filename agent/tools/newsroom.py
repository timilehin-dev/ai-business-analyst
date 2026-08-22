"""
Newsroom Tool - Web Search for Market Intelligence.
Enables the agent to stay updated with external signals.

Implementation note: queries DuckDuckGo's HTML endpoint directly with
httpx + BeautifulSoup. This deliberately avoids the `duckduckgo-search`
package, which drags in `pyreqwest-impersonate` (a Rust-backed dependency
that breaks Docker builds on source-only releases). Same search backend,
zero extra dependencies.
"""
import datetime
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, unquote

import httpx
from bs4 import BeautifulSoup

DDG_HTML_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


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
            results = await self._search_ddg(query)

            if not results:
                return f"No external information found for: {query}"

            formatted = []
            for res in results:
                title = res.get('title', 'No title')
                body = res.get('body', 'No description')
                href = res.get('href', '')

                # Optionally fetch full content if the snippet is thin
                content = body
                if href and len(body) < 100:
                    content = await self._fetch_page_content(href) or body

                formatted.append(f"[Source: {title}]({href})\n{content}\n")

            context = f"## External Intelligence: {topic}\n\n" + "\n---\n".join(formatted)
            return context

        except Exception as e:
            return f"Search failed: {str(e)}. Proceeding with internal data only."

    async def _search_ddg(self, query: str) -> List[dict]:
        """Query the DuckDuckGo HTML endpoint and parse result links."""
        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.get(DDG_HTML_URL, params={"q": query}, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            for result in soup.select("div.result"):
                link = result.select_one("a.result__a")
                if not link:
                    continue
                href = link.get("href", "")
                results.append({
                    "title": link.get_text(strip=True),
                    "href": self._decode_redirect(href),
                    "body": self._snippet_text(result),
                })
                if len(results) >= self.max_results:
                    break
            return results

    @staticmethod
    def _snippet_text(result) -> str:
        """Extract the snippet text from a DDG result block."""
        snippet = result.select_one("a.result__snippet")
        if snippet:
            return snippet.get_text(strip=True)
        # Fallback: any text node after the title link
        text = result.get_text(separator=' ', strip=True)
        return text[:300]

    @staticmethod
    def _decode_redirect(href: str) -> str:
        """DDG wraps result URLs in /l/?uddg=<encoded>. Unwrap them."""
        if "uddg=" in href:
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            if "uddg" in params:
                return unquote(params["uddg"][0])
        return href

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
        year = datetime.date.today().year
        queries = []

        # Always include a general market context query
        queries.append(f"{business_context} market trends {year}")

        # If user query mentions specific topics, add targeted searches
        keywords = ["competitor", "pricing", "regulation", "law", "policy", "market share"]
        for keyword in keywords:
            if keyword in user_query.lower():
                queries.append(f"{user_query} {keyword}")
                break

        return queries[:3]  # Limit to 3 queries max
