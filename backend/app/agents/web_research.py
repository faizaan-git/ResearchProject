
from ddgs import DDGS
import trafilatura


class WebResearchAgent:
    """
    Searches the web and extracts useful research content.
    """

    def search_web(self, queries: list[str], max_results: int = 5) -> dict:

        if not queries:
            raise ValueError("At least one search query is required.")

        all_sources = []
        seen_urls = set()
        errors = []

        for query in queries[:10]:

            try:
                results = DDGS().text(
                    query,
                    max_results=max_results
                )

                for result in results or []:

                    url = result.get("href", "")
                    title = result.get("title", "Untitled")
                    snippet = result.get("body", "")

                    if not url.startswith(("http://", "https://")):
                        continue

                    if url in seen_urls:
                        continue

                    seen_urls.add(url)

                    content = ""
                    content_source = "search_snippet"

                    try:
                        downloaded = trafilatura.fetch_url(url)

                        if downloaded:
                            extracted = trafilatura.extract(downloaded)

                            if extracted and len(extracted.strip()) > 100:
                                content = extracted[:6000]
                                content_source = "webpage"

                    except Exception:
                        pass

                    # Use search snippet as fallback
                    if not content:
                        content = snippet

                    all_sources.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "content": content,
                        "content_extracted": (
                            content_source == "webpage"
                        ),
                        "content_source": content_source,
                        "search_query": query
                    })

            except Exception as error:
                errors.append({
                    "query": query,
                    "error": str(error)
                })

        return {
            "total_sources": len(all_sources),
            "sources": all_sources,
            "errors": errors,
            "status": (
                "completed" if all_sources
                else "no_sources_found"
            )
        }


web_research_agent = WebResearchAgent()
