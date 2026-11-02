import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import urllib.parse

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

class PubMedClient:
    def __init__(self, timeout: float = 15.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    async def search_pubmed(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search PubMed for scientific articles relevant to query using NCBI E-utilities.
        Returns PMIDs, titles, short abstracts, and PubMed URLs.
        """
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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. ESearch
            try:
                res = await client.get(ESEARCH_URL, params=search_params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    id_list = data.get("esearchresult", {}).get("idlist", [])
                    pmids = id_list[:max_results]
            except Exception as e:
                return {
                    "query": clean_query,
                    "count": 0,
                    "articles": [],
                    "search_url": search_url,
                    "error": str(e)
                }

            if not pmids:
                return {
                    "query": clean_query,
                    "count": 0,
                    "articles": [],
                    "search_url": search_url,
                    "message": "No PubMed records found for this query."
                }

            # 2. EFetch (XML)
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml"
            }
            fetch_url = f"{EFETCH_URL}?{urllib.parse.urlencode(fetch_params)}"
            articles = []

            try:
                f_res = await client.get(EFETCH_URL, params=fetch_params, headers=headers)
                if f_res.status_code == 200:
                    root = ET.fromstring(f_res.text)
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
            except Exception as e:
                # If XML parsing fails, still return basic PMID links
                articles = [{"pmid": p, "title": f"PubMed Article {p}", "abstract": "Parsing details omitted", "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/"} for p in pmids]

            return {
                "query": clean_query,
                "count": len(articles),
                "articles": articles,
                "search_url": search_url,
                "fetch_url": fetch_url
            }

