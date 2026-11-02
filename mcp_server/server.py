import os
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from mcp_server.stats import compute_disproportionality as compute_stats
from mcp_server.openfda_client import OpenFDAClient
from mcp_server.pubmed_client import PubMedClient

PORT = int(os.environ.get("MCP_PORT", 8001))
HOST = os.environ.get("MCP_HOST", "127.0.0.1")

mcp = FastMCP("VigilAI", host=HOST, port=PORT)
openfda = OpenFDAClient()
pubmed = PubMedClient()

@mcp.tool()
async def search_faers_reactions(drug: str, limit: int = 15) -> Dict[str, Any]:
    """
    Search top MedDRA adverse reaction terms and report counts for a drug from openFDA FAERS.
    Returns the top reaction terms and counts along with the exact openFDA query URL.
    """
    return await openfda.search_faers_reactions(drug=drug, limit=limit)

@mcp.tool()
async def get_faers_totals(drug: str, reaction: str) -> Dict[str, Any]:
    """
    Get 2x2 contingency counts for disproportionality analysis:
    - a: reports with target drug and target reaction
    - b: reports with target drug and other reactions
    - c: reports with other drugs and target reaction
    - d: reports with neither
    Returns counts and openFDA source query URLs.
    """
    return await openfda.get_faers_totals(drug=drug, reaction=reaction)

@mcp.tool()
def compute_disproportionality(a: int, b: int, c: int, d: int) -> Dict[str, Any]:
    """
    Compute Proportional Reporting Ratio (PRR), Reporting Odds Ratio (ROR), 95% confidence intervals,
    chi-square with Yates' correction, and Evans criteria signal flag (PRR >= 2, a >= 3, chi_square >= 4).
    All statistical computations are strictly calculated here, NEVER by the LLM.
    """
    return compute_stats(a=a, b=b, c=c, d=d)

@mcp.tool()
async def get_label_sections(drug: str) -> Dict[str, Any]:
    """
    Fetch FDA approved label sections (Boxed Warning, Warnings and Precautions, Adverse Reactions)
    from openFDA for a specified drug.
    """
    return await openfda.get_label_sections(drug=drug)

@mcp.tool()
async def check_reaction_in_label(drug: str, reaction: str) -> Dict[str, Any]:
    """
    Check if a specific reaction term is documented in the FDA label sections for a drug.
    Returns whether it is in the label, the section name, and a verbatim snippet (< 500 characters).
    """
    return await openfda.check_reaction_in_label(drug=drug, reaction=reaction)

@mcp.tool()
async def search_pubmed(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search PubMed via NCBI E-utilities (esearch + efetch) for scientific literature.
    Returns PMIDs, article titles, publication years, short abstracts, and PubMed URLs.
    """
    return await pubmed.search_pubmed(query=query, max_results=max_results)

app = mcp.sse_app()

if __name__ == "__main__":
    print(f"Starting Vigil AI MCP Server on {HOST}:{PORT} (transport: sse)...")
    mcp.run(transport="sse")

