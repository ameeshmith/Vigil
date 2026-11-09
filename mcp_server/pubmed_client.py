import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
import urllib.parse
from mcp_server.cache import TTLCache, TokenBucketRateLimiter
from mcp_server.constants import DISCLAIMER, current_iso_timestamp

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

class PubMedClient:
    def __init__(self, timeout: float = 15.0, max_retries: int = 3, cache_ttl: float = 300.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache = TTLCache(default_ttl=cache_ttl)
        # NCBI limits requests to 3 per second without an API key
        self.rate_limiter = TokenBucketRateLimiter(rate=3.0, capacity=3.0)

    async def search_pubmed(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search PubMed for scientific articles relevant to query using NCBI E-utilities.
        Returns PMIDs, titles, short abstracts, and PubMed URLs with timestamps and disclaimer.
        """
        timestamp = current_iso_timestamp()
        clean_query = query.strip()
        search_params = {
            "db": "pubmed",
            "term": clean_query,
            "retmode": "json",
            "retmax": str(max_results),
            "sort": "relevance"
        }
        headers = {"User-Agent": "VigilAI/1.0 (Drug Safety Demo)"}
        
        search_url = f"{ESEARCH_URL}?{urllib.parse.urlencode(search_params)}"
        pmids: List[str] = []

        cache_key_search = f"pubmed:esearch:{search_url}"
        cached_search = await self.cache.get(cache_key_search)
        if cached_search is not None:
            pmids = cached_search
        else:
            await self.rate_limiter.wait_for_token(1.0)
            delay = 1.0
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for attempt in range(self.max_retries + 1):
                    try:
                        res = await client.get(ESEARCH_URL, params=search_params, headers=headers)
                        if res.status_code == 200:
                            data = res.json() if callable(res.json) else {}
                            id_list = data.get("esearchresult", {}).get("idlist", [])
                            pmids = id_list[:max_results]
                            await self.cache.set(cache_key_search, pmids)
                            break
                        elif res.status_code == 429:
                            if attempt < self.max_retries:
                                await asyncio.sleep(delay)
                                delay *= 2.0
                                continue
                            break
                        elif res.status_code >= 500:
                            if attempt < self.max_retries:
                                await asyncio.sleep(delay)
                                delay *= 2.0
                                continue
                            break
                    except (httpx.TimeoutException, httpx.RequestError):
                        if attempt < self.max_retries:
                            await asyncio.sleep(delay)
                            delay *= 2.0
                            continue
                        break

        if not pmids:
            return {
                "query": clean_query,
                "count": 0,
                "articles": [],
                "search_url": search_url,
                "message": "No PubMed records found for this query.",
                "data_source": "NCBI PubMed E-Utilities (esearch)",
                "retrieved_at": timestamp,
                "disclaimer": DISCLAIMER,
                "status": "no_data_found"
            }

        # 2. EFetch (XML)
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }
        fetch_url = f"{EFETCH_URL}?{urllib.parse.urlencode(fetch_params)}"
        cache_key_fetch = f"pubmed:efetch:{fetch_url}"
        cached_articles = await self.cache.get(cache_key_fetch)
        if cached_articles is not None:
            articles = cached_articles
        else:
            articles = []
            await self.rate_limiter.wait_for_token(1.0)
            delay = 1.0
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for attempt in range(self.max_retries + 1):
                    try:
                        f_res = await client.get(EFETCH_URL, params=fetch_params, headers=headers)
                        if f_res.status_code == 200:
                            text_body = f_res.text if isinstance(f_res.text, str) else str(f_res.text)
                            try:
                                root = ET.fromstring(text_body)
                                for article_node in root.findall(".//PubmedArticle"):
                                    pmid_el = article_node.find(".//MedlineCitation/PMID")
                                    pmid = pmid_el.text if pmid_el is not None else ""
                                    
                                    title_el = article_node.find(".//ArticleTitle")
                                    title = "".join(title_el.itertext()).strip() if title_el is not None else "Untitled"
                                    
                                    abstract_parts = []
                                    for ab_text in article_node.findall(".//AbstractText"):
                                        part = "".join(ab_text.itertext()).strip()
                                        if part:
                                            abstract_parts.append(part)
                                    
                                    full_abstract = " ".join(abstract_parts)
                                    short_abstract = full_abstract[:350] + ("..." if len(full_abstract) > 350 else "") if full_abstract else "No abstract available."
                                    
                                    pub_year_el = article_node.find(".//JournalIssue/PubDate/Year")
                                    pub_year = pub_year_el.text if pub_year_el is not None else "Recent"
                                    
                                    articles.append({
                                        "pmid": pmid,
                                        "title": title,
                                        "abstract": short_abstract,
                                        "year": pub_year,
                                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                                    })
                            except Exception:
                                articles = [{"pmid": p, "title": f"PubMed Article {p}", "abstract": "Parsing details omitted", "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/"} for p in pmids]
                            
                            await self.cache.set(cache_key_fetch, articles)
                            break
                        elif f_res.status_code == 429:
                            if attempt < self.max_retries:
                                await asyncio.sleep(delay)
                                delay *= 2.0
                                continue
                            break
                        elif f_res.status_code >= 500:
                            if attempt < self.max_retries:
                                await asyncio.sleep(delay)
                                delay *= 2.0
                                continue
                            break
                    except (httpx.TimeoutException, httpx.RequestError):
                        if attempt < self.max_retries:
                            await asyncio.sleep(delay)
                            delay *= 2.0
                            continue
                        break

            if not articles:
                articles = [{"pmid": p, "title": f"PubMed Article {p}", "abstract": "Fetch details unavailable", "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/"} for p in pmids]

        return {
            "query": clean_query,
            "count": len(articles),
            "articles": articles,
            "search_url": search_url,
            "fetch_url": fetch_url,
            "data_source": "NCBI PubMed E-Utilities (esearch + efetch)",
            "retrieved_at": timestamp,
            "disclaimer": DISCLAIMER,
            "status": "success"
        }
