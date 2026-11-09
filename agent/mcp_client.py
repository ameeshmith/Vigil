import os
import asyncio
from typing import List, Dict, Any
from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.tools import load_mcp_tools

from mcp_server.stats import compute_disproportionality as _mcp_compute_stats
from mcp_server.openfda_client import OpenFDAClient
from mcp_server.pubmed_client import PubMedClient

_openfda = OpenFDAClient()
_pubmed = PubMedClient()

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8001/sse")

# Direct in-process LangChain wrapped tools (used as fallback or in testing)
@tool("search_faers_reactions")
async def local_search_faers_reactions(drug: str, limit: int = 15) -> Dict[str, Any]:
    """Search top MedDRA adverse reaction terms and report counts for a drug from openFDA FAERS."""
    return await _openfda.search_faers_reactions(drug=drug, limit=limit)

@tool("get_faers_totals")
async def local_get_faers_totals(drug: str, reaction: str) -> Dict[str, Any]:
    """Get 2x2 contingency counts (a, b, c, d) for disproportionality analysis from openFDA."""
    return await _openfda.get_faers_totals(drug=drug, reaction=reaction)

@tool("compute_disproportionality")
def local_compute_disproportionality(a: int, b: int, c: int, d: int) -> Dict[str, Any]:
    """Compute PRR, ROR, 95% CI, chi-square and Evans signal flag. All numbers computed here, never by LLM."""
    return _mcp_compute_stats(a=a, b=b, c=c, d=d)

@tool("get_label_sections")
async def local_get_label_sections(drug: str) -> Dict[str, Any]:
    """Fetch FDA label sections (Boxed Warning, Warnings & Precautions, Adverse Reactions) from openFDA."""
    return await _openfda.get_label_sections(drug=drug)

@tool("check_reaction_in_label")
async def local_check_reaction_in_label(drug: str, reaction: str) -> Dict[str, Any]:
    """Check whether a reaction term appears in FDA drug label, with context snippet."""
    return await _openfda.check_reaction_in_label(drug=drug, reaction=reaction)

@tool("search_pubmed")
async def local_search_pubmed(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search PubMed via NCBI E-utilities (esearch + efetch) for scientific literature."""
    return await _pubmed.search_pubmed(query=query, max_results=max_results)

LOCAL_MCP_TOOLS: List[BaseTool] = [
    local_search_faers_reactions,
    local_get_faers_totals,
    local_compute_disproportionality,
    local_get_label_sections,
    local_check_reaction_in_label,
    local_search_pubmed
]

async def load_agent_mcp_tools(mcp_url: str = MCP_SERVER_URL, prefer_local: bool = False) -> List[BaseTool]:
    """
    Load tools via langchain-mcp-adapters over HTTP/SSE transport.
    Falls back gracefully to local wrapped FastMCP tools if server is starting or unreachable.
    """
    if prefer_local:
        return LOCAL_MCP_TOOLS

    try:
        connection = {"transport": "sse", "url": mcp_url}
        tools = await asyncio.wait_for(load_mcp_tools(connection=connection), timeout=3.0)
        return tools
    except Exception:
        # Graceful fallback to identical local FastMCP tools
        return LOCAL_MCP_TOOLS
