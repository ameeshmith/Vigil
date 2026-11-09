import asyncio
import httpx
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from mcp_server.cache import TTLCache, TokenBucketRateLimiter
from mcp_server.constants import DISCLAIMER, current_iso_timestamp

OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

def strip_drug_dosage(name: str) -> str:
    """Remove dosage numbers, strengths, and units (e.g., '250', '20mg', '1.5ml', 'tablets')."""
    cleaned = re.sub(r'(?i)\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|tab|tabs|tablet|tablets|cap|caps|capsule|capsules|oral|iv|im)?\b', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else name.strip()

class OpenFDAClient:
    def __init__(self, timeout: float = 15.0, max_retries: int = 3, cache_ttl: float = 300.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self._cached_total_faers: Optional[int] = None
        self.cache = TTLCache(default_ttl=cache_ttl)
        self.rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=15.0)

    async def _fetch_with_backoff(self, url: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any], str]:
        """Fetch JSON from openFDA with caching, rate-limiting, and exponential backoff on 429s/transient errors."""
        headers = {"User-Agent": "VigilAI/1.0 (Drug Safety Research Demo)"}
        full_url = url
        if params:
            query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            full_url = f"{url}?{query_string}"

        cache_key = f"openfda:{full_url}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached[0], cached[1], cached[2]

        await self.rate_limiter.wait_for_token(1.0)

        delay = 1.0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        res_json = response.json()
                        res_url = str(response.url)
                        await self.cache.set(cache_key, (200, res_json, res_url))
                        return 200, res_json, res_url
                    elif response.status_code == 404:
                        res_json = {"error": "Not found in openFDA", "results": []}
                        res_url = str(response.url)
                        await self.cache.set(cache_key, (404, res_json, res_url), ttl=60.0)
                        return 404, res_json, res_url
                    elif response.status_code == 429:
                        if attempt < self.max_retries:
                            await asyncio.sleep(delay)
                            delay *= 2.0
                            continue
                        return 429, {"error": "Rate limit exceeded (429)", "results": []}, str(response.url)
                    else:
                        if attempt < self.max_retries and response.status_code >= 500:
                            await asyncio.sleep(delay)
                            delay *= 2.0
                            continue
                        return response.status_code, {"error": f"HTTP {response.status_code}", "detail": response.text[:200]}, str(response.url)
                except (httpx.TimeoutException, httpx.RequestError) as ex:
                    if attempt < self.max_retries:
                        await asyncio.sleep(delay)
                        delay *= 2.0
                        continue
                    return 500, {"error": f"Request failed: {str(ex)}"}, full_url
        return 500, {"error": "Max retries exceeded"}, full_url

    async def get_total_faers_count(self) -> Tuple[int, str]:
        """Get the total number of FAERS adverse event reports recorded in openFDA."""
        if self._cached_total_faers is not None and self._cached_total_faers > 0:
            return self._cached_total_faers, f"{OPENFDA_EVENT_URL}?search=_exists_:safetyreportid"

        status, data, url = await self._fetch_with_backoff(OPENFDA_EVENT_URL, {"search": "_exists_:safetyreportid", "limit": 1})
        if status == 200 and "meta" in data and "results" in data["meta"]:
            total = data["meta"]["results"].get("total", 0)
            self._cached_total_faers = total
            return total, url
        # Fallback approximate total if query fails
        return 20000000, url

    async def search_faers_reactions(self, drug: str, limit: int = 15) -> Dict[str, Any]:
        """
        Retrieve top MedDRA reaction terms and counts for a drug.
        Tries generic_name, brand_name, and medicinalproduct across raw and dosage-stripped variants.
        """
        timestamp = current_iso_timestamp()
        clean_raw = drug.strip().upper()
        clean_stripped = strip_drug_dosage(clean_raw).upper()

        drug_candidates = [clean_raw]
        if clean_stripped and clean_stripped != clean_raw:
            drug_candidates.append(clean_stripped)

        queries = []
        for d in drug_candidates:
            queries.extend([
                f'patient.drug.openfda.generic_name:"{d}"',
                f'patient.drug.openfda.brand_name:"{d}"',
                f'patient.drug.medicinalproduct:"{d}"'
            ])

        last_url = ""
        for query in queries:
            params = {
                "search": query,
                "count": "patient.reaction.reactionmeddrapt.exact"
            }
            status, data, url = await self._fetch_with_backoff(OPENFDA_EVENT_URL, params)
            last_url = url
            if status == 200 and "results" in data and len(data["results"]) > 0:
                raw_results = data["results"][:limit]
                reactions = [{"reaction": item.get("term"), "count": item.get("count")} for item in raw_results]
                return {
                    "drug": drug,
                    "matched_field": query.split(":")[0],
                    "count_reactions": len(reactions),
                    "reactions": reactions,
                    "source_url": url,
                    "data_source": "openFDA FAERS event.json",
                    "retrieved_at": timestamp,
                    "status": "success",
                    "disclaimer": DISCLAIMER
                }

        return {
            "drug": drug,
            "matched_field": None,
            "count_reactions": 0,
            "reactions": [],
            "source_url": last_url,
            "data_source": "openFDA FAERS event.json",
            "retrieved_at": timestamp,
            "status": "no_data_found",
            "disclaimer": DISCLAIMER
        }

    async def get_faers_totals(self, drug: str, reaction: str) -> Dict[str, Any]:
        """
        Fetch contingency counts (a, b, c, d) for a specific drug and reaction pair.
        a = reports with target drug AND target reaction
        b = reports with target drug WITHOUT target reaction (total_drug - a)
        c = reports with target reaction WITHOUT target drug (total_reaction - a)
        d = reports with neither (total_faers - a - b - c)
        """
        timestamp = current_iso_timestamp()
        clean_drug = drug.strip().upper()
        clean_rxn = reaction.strip().upper()

        total_faers, faers_url = await self.get_total_faers_count()
        source_urls = [faers_url]

        # 1. Total drug reports (try generic, brand, medicinalproduct across raw and stripped)
        clean_stripped = strip_drug_dosage(clean_drug)
        drug_trials = [clean_drug]
        if clean_stripped and clean_stripped != clean_drug:
            drug_trials.append(clean_stripped)

        total_drug = 0
        winning_query = f'patient.drug.openfda.generic_name:"{clean_drug}"'

        for dt in drug_trials:
            for field in ("openfda.generic_name", "openfda.brand_name", "medicinalproduct"):
                trial_q = f'patient.drug.{field}:"{dt}"'
                status, data, url_drug = await self._fetch_with_backoff(OPENFDA_EVENT_URL, {"search": trial_q, "limit": 1})
                if status == 200 and "meta" in data and "results" in data["meta"]:
                    cnt = data["meta"]["results"].get("total", 0)
                    if cnt > total_drug:
                        total_drug = cnt
                        winning_query = trial_q
                        source_urls.append(url_drug)
                        break
            if total_drug > 0:
                break
        
        drug_query = winning_query

        # 2. Total reaction reports across all drugs
        rxn_query = f'patient.reaction.reactionmeddrapt.exact:"{clean_rxn}"'
        status, data, url_rxn = await self._fetch_with_backoff(OPENFDA_EVENT_URL, {"search": rxn_query, "limit": 1})
        source_urls.append(url_rxn)
        total_reaction = 0
        if status == 200 and "meta" in data and "results" in data["meta"]:
            total_reaction = data["meta"]["results"].get("total", 0)

        # 3. Reports with both drug and reaction (a)
        both_query = f'{drug_query}+AND+{rxn_query}'
        status, data, url_both = await self._fetch_with_backoff(OPENFDA_EVENT_URL, {"search": both_query, "limit": 1})
        source_urls.append(url_both)
        a = 0
        if status == 200 and "meta" in data and "results" in data["meta"]:
            a = data["meta"]["results"].get("total", 0)

        # Contingency calculation
        b = max(0, total_drug - a)
        c = max(0, total_reaction - a)
        d = max(0, total_faers - (a + b + c))

        return {
            "drug": drug,
            "reaction": reaction,
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "total_drug": total_drug,
            "total_reaction": total_reaction,
            "total_faers": total_faers,
            "source_urls": source_urls,
            "data_source": "openFDA FAERS event.json",
            "retrieved_at": timestamp,
            "status": "success" if total_drug > 0 else "drug_not_found",
            "disclaimer": DISCLAIMER
        }

    async def get_label_sections(self, drug: str) -> Dict[str, Any]:
        """
        Retrieve Boxed Warning, Warnings and Precautions, and Adverse Reactions
        sections from openFDA drug labels.
        """
        timestamp = current_iso_timestamp()
        clean_drug = drug.strip().upper()

        queries = [
            f'openfda.generic_name:"{clean_drug}"',
            f'openfda.brand_name:"{clean_drug}"',
            f'openfda.substance_name:"{clean_drug}"'
        ]

        last_url = ""
        for query in queries:
            status, data, url = await self._fetch_with_backoff(OPENFDA_LABEL_URL, {"search": query, "limit": 1})
            last_url = url
            if status == 200 and "results" in data and len(data["results"]) > 0:
                label = data["results"][0]
                
                boxed_warning = " ".join(label.get("boxed_warning", []))
                warnings_and_precautions = " ".join(label.get("warnings_and_precautions", []) or label.get("warnings", []))
                adverse_reactions = " ".join(label.get("adverse_reactions", []))

                return {
                    "drug": drug,
                    "has_label": True,
                    "sections": {
                        "boxed_warning": boxed_warning[:4000],
                        "warnings_and_precautions": warnings_and_precautions[:6000],
                        "adverse_reactions": adverse_reactions[:6000]
                    },
                    "source_url": url,
                    "data_source": "openFDA label.json",
                    "retrieved_at": timestamp,
                    "status": "success",
                    "disclaimer": DISCLAIMER
                }

        return {
            "drug": drug,
            "has_label": False,
            "sections": {
                "boxed_warning": "",
                "warnings_and_precautions": "",
                "adverse_reactions": ""
            },
            "source_url": last_url,
            "data_source": "openFDA label.json",
            "retrieved_at": timestamp,
            "status": "label_not_found",
            "disclaimer": DISCLAIMER
        }

    async def check_reaction_in_label(self, drug: str, reaction: str) -> Dict[str, Any]:
        """
        Check if a reaction term is present in any label section, returning
        the matching section and a context snippet under 500 characters.
        """
        timestamp = current_iso_timestamp()
        label_res = await self.get_label_sections(drug)
        if not label_res.get("has_label"):
            return {
                "drug": drug,
                "reaction": reaction,
                "is_in_label": False,
                "section": "None",
                "snippet": "No FDA drug label found for this drug.",
                "source_url": label_res.get("source_url", OPENFDA_LABEL_URL),
                "data_source": "openFDA label.json",
                "retrieved_at": timestamp,
                "disclaimer": DISCLAIMER
            }

        sections = label_res.get("sections", {})
        reaction_terms = [reaction.lower()]
        parts = reaction.lower().split()
        if len(parts) > 1:
            reaction_terms.append(" ".join(parts[-2:]))

        for sec_name, text in sections.items():
            if not text:
                continue
            text_lower = text.lower()
            for term in reaction_terms:
                idx = text_lower.find(term)
                if idx != -1:
                    start = max(0, idx - 150)
                    end = min(len(text), idx + len(term) + 250)
                    snippet = text[start:end].replace("\n", " ").strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."
                    snippet = snippet[:490]
                    return {
                        "drug": drug,
                        "reaction": reaction,
                        "is_in_label": True,
                        "section": sec_name,
                        "snippet": snippet,
                        "source_url": label_res.get("source_url"),
                        "data_source": "openFDA label.json",
                        "retrieved_at": timestamp,
                        "disclaimer": DISCLAIMER
                    }

        return {
            "drug": drug,
            "reaction": reaction,
            "is_in_label": False,
            "section": "None",
            "snippet": f"The term '{reaction}' does not appear in Boxed Warning, Warnings & Precautions, or Adverse Reactions sections.",
            "source_url": label_res.get("source_url"),
            "data_source": "openFDA label.json",
            "retrieved_at": timestamp,
            "disclaimer": DISCLAIMER
        }
