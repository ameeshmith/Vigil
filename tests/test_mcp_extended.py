import os
import sys
import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from mcp_server.server import (
    mcp,
    search_faers_reactions,
    get_faers_totals,
    compute_disproportionality,
    get_label_sections,
    check_reaction_in_label,
    search_pubmed,
    investigate_signal,
    resume_investigation,
    compare_drugs,
    get_report,
    get_report_resource,
    safety_review,
    extract_groq_api_key
)
from mcp_server.cache import TTLCache, TokenBucketRateLimiter
from api.app import app


# 1. Test All Tool Schemas and Descriptions
def test_all_10_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    expected_tools = [
        # Layer 1
        "search_faers_reactions",
        "get_faers_totals",
        "compute_disproportionality",
        "get_label_sections",
        "check_reaction_in_label",
        "search_pubmed",
        # Layer 2
        "investigate_signal",
        "resume_investigation",
        "compare_drugs",
        "get_report"
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool {expected} missing from MCP server"

    # Verify compute_disproportionality explicitly mentions zero LLM math
    comp_tool = mcp._tool_manager.get_tool("compute_disproportionality")
    assert "ZERO LLM MATH" in comp_tool.description or "never by LLM" in comp_tool.description.lower() or "never compute" in comp_tool.description.lower()


# 2. Test Missing Groq API Key Handling
@pytest.mark.asyncio
async def test_investigate_signal_missing_groq_key():
    # Ensure GROQ_API_KEY is not in env for this test
    with patch.dict(os.environ, {}, clear=True):
        res = await investigate_signal(drug="TestDrug", groq_api_key="")
        assert res["status"] == "missing_api_key"
        assert "Missing Groq API Key" in res["error"]
        assert "groq_api_key" in res["error"]


# 3. Test API Key Extraction Hierarchy
def test_extract_groq_api_key_precedence():
    # 1. Direct argument beats everything
    with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
        key = extract_groq_api_key(groq_api_key="direct_key")
        assert key == "direct_key"

    # 2. Context header beats env
    mock_ctx = MagicMock()
    mock_ctx.request_context.request.headers = {"x-groq-api-key": "header_key"}
    with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
        key = extract_groq_api_key(groq_api_key="", ctx=mock_ctx)
        assert key == "header_key"

    # 3. Fallback to env
    with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
        key = extract_groq_api_key()
        assert key == "env_key"

    # 4. Empty when none provided
    with patch.dict(os.environ, {}, clear=True):
        key = extract_groq_api_key()
        assert key == ""


# 4. Test In-Memory TTL Cache and Rate Limiter
@pytest.mark.asyncio
async def test_ttl_cache_expiration():
    cache = TTLCache(default_ttl=0.1)
    await cache.set("k1", "val1")
    assert await cache.get("k1") == "val1"

    # Wait for expiry
    await asyncio.sleep(0.15)
    assert await cache.get("k1") is None


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=2.0)
    assert await limiter.acquire(2.0) is True
    # Exceeded capacity
    assert await limiter.acquire(1.0) is False
    # Wait for refill
    await asyncio.sleep(0.15)
    assert await limiter.acquire(1.0) is True


# 5. Test Compare Drugs (Deterministic Zero-LLM Stats)
@pytest.mark.asyncio
async def test_compare_drugs_deterministic():
    mock_totals_a = {
        "drug": "DrugA", "reaction": "HEPATOTOXICITY",
        "a": 500, "b": 4500, "c": 1000, "d": 94000,
        "total_drug": 5000, "source_urls": ["url_a"],
        "status": "success"
    }
    mock_totals_b = {
        "drug": "DrugB", "reaction": "HEPATOTOXICITY",
        "a": 50, "b": 4950, "c": 1450, "d": 93550,
        "total_drug": 5000, "source_urls": ["url_b"],
        "status": "success"
    }
    mock_label_a = {"drug": "DrugA", "is_in_label": True, "section": "warnings_and_precautions", "snippet": "Liver injury noted."}
    mock_label_b = {"drug": "DrugB", "is_in_label": False, "section": "None", "snippet": ""}

    with patch("mcp_server.server.openfda.get_faers_totals", side_effect=[mock_totals_a, mock_totals_b]), \
         patch("mcp_server.server.openfda.check_reaction_in_label", side_effect=[mock_label_a, mock_label_b]):

        result = await compare_drugs(drug_a="DrugA", drug_b="DrugB", event="Hepatotoxicity")

        assert result["status"] == "success"
        assert result["event"] == "HEPATOTOXICITY"
        assert result["drug_a"]["statistics"]["prr"] > result["drug_b"]["statistics"]["prr"]
        assert result["drug_a"]["label_status"]["is_in_label"] is True
        assert result["drug_b"]["label_status"]["is_in_label"] is False
        assert "Comparative disproportionality analysis" in result["comparative_narrative"]
        assert "data_source" in result
        assert "retrieved_at" in result
        assert "disclaimer" in result


# 6. Test Human-in-the-Loop Interrupt & Resume Flow
@pytest.mark.asyncio
async def test_hitl_needs_input_and_resume():
    test_run_id = "test_hitl_run_001"
    
    # Mock GRAPH execution yielding interrupt state
    mock_snapshot_paused = MagicMock()
    mock_snapshot_paused.next = ["human_review"]
    mock_snapshot_paused.values = {
        "drug": "Atorvastatin",
        "normalized_drug": "Atorvastatin",
        "run_id": test_run_id,
        "human_review_reason": "Unlabeled statistical signal detected: ACUTE PANCREATITIS",
        "evidence": {
            "ACUTE PANCREATITIS": {
                "reaction": "ACUTE PANCREATITIS", "a": 450, "prr": 2.87,
                "signal_flag": True, "is_in_label": False
            }
        },
        "draft": "Draft assessment for Atorvastatin..."
    }

    async def mock_astream_paused(initial_state, config, stream_mode="updates"):
        yield {"writer": {"draft": "Draft text"}}

    with patch("mcp_server.server.GRAPH.astream", side_effect=mock_astream_paused), \
         patch("mcp_server.server.GRAPH.get_state", return_value=mock_snapshot_paused):

        res = await investigate_signal(drug="Atorvastatin", groq_api_key="dummy_key")
        assert res["status"] == "needs_input"
        assert "needs_input" == res["status"]
        assert "Human Review Gate" in res["question"]
        assert "ACUTE PANCREATITIS" in res["reason"]

    # Now test resuming the paused run
    mock_snapshot_resumed = MagicMock()
    mock_snapshot_resumed.values = {
        "normalized_drug": "Atorvastatin",
        "draft": "Final approved assessment text.",
        "evidence": {},
        "critic_passes": True,
        "structured_assessment": MagicMock(
            executive_summary="Final validated summary.",
            citations=["https://api.fda.gov"],
            model_dump=lambda: {"executive_summary": "Final validated summary.", "citations": ["https://api.fda.gov"]}
        )
    }

    async def mock_astream_resumed(cmd, config, stream_mode="updates"):
        yield {"human_review": {"review_status": "approved"}}

    with patch("mcp_server.server.GRAPH.astream", side_effect=mock_astream_resumed), \
         patch("mcp_server.server.GRAPH.get_state", return_value=mock_snapshot_resumed):

        resume_res = await resume_investigation(run_id=res["run_id"], answer="approve")
        assert resume_res["status"] == "completed"
        assert resume_res["summary"] == "Final validated summary."
        assert resume_res["critic_verdict"] == "PASS"


# 7. Test Progress Notifications (Mocked Context)
@pytest.mark.asyncio
async def test_progress_notifications():
    mock_ctx = MagicMock()
    mock_ctx.report_progress = AsyncMock()
    mock_ctx.info = AsyncMock()

    mock_snapshot = MagicMock()
    mock_snapshot.next = []
    mock_snapshot.values = {
        "normalized_drug": "Simvastatin",
        "evidence": {},
        "critic_passes": True,
        "draft": "Draft",
        "structured_assessment": MagicMock(
            executive_summary="Summary",
            citations=[],
            model_dump=lambda: {"executive_summary": "Summary", "citations": []}
        )
    }

    async def mock_astream(initial_state, config, stream_mode="updates"):
        yield {"intake": {}}
        yield {"planner": {}}
        yield {"investigator": {}}
        yield {"writer": {}}
        yield {"critic": {}}

    with patch("mcp_server.server.GRAPH.astream", side_effect=mock_astream), \
         patch("mcp_server.server.GRAPH.get_state", return_value=mock_snapshot):

        res = await investigate_signal(drug="Simvastatin", groq_api_key="dummy_key", ctx=mock_ctx)
        assert res["status"] == "completed"
        # Verify progress calls occurred
        assert mock_ctx.report_progress.call_count >= 4
        assert mock_ctx.info.call_count >= 4


# 8. Test Resources and Prompt Templates
def test_resources_and_prompts():
    # Example report resource
    atorva_json = get_report_resource("atorvastatin")
    data = json.loads(atorva_json)
    assert data["drug"] == "Atorvastatin"
    assert "evidence" in data

    ozempic_json = get_report_resource("ozempic")
    oz_data = json.loads(ozempic_json)
    assert oz_data["drug"] == "Ozempic"

    # Prompt template
    prompt_text = safety_review(drug="Metformin", event="Lactic Acidosis")
    assert "Metformin" in prompt_text
    assert "Lactic Acidosis" in prompt_text
    assert "search_faers_reactions" in prompt_text
    assert "compute_disproportionality" in prompt_text
    assert "check_reaction_in_label" in prompt_text
    assert "search_pubmed" in prompt_text


# 9. Test Health Endpoint & /mcp SSE Mount in FastAPI
def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Vigil AI"
    assert data["mcp_endpoint"] == "/mcp"


# 10. Test Stdio Smoke with Client SDK
@pytest.mark.asyncio
async def test_stdio_smoke_via_mcp_sdk():
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp import ClientSession

    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "stdio"
    env["PYTHONUNBUFFERED"] = "1"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server", "--stdio"],
        env=env
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_resp = await session.list_tools()
            tool_names = [t.name for t in tools_resp.tools]
            assert "search_faers_reactions" in tool_names
            assert "investigate_signal" in tool_names
            assert "compare_drugs" in tool_names
            assert "get_report" in tool_names

