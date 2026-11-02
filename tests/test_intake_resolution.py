import pytest
from unittest.mock import patch, AsyncMock
from agent.state import AgentState
from agent.graph import build_safety_agent_graph
from mcp_server.openfda_client import strip_drug_dosage

def test_strip_drug_dosage():
    assert strip_drug_dosage("Naxdom 250") == "Naxdom"
    assert strip_drug_dosage("Atorvastatin 20mg") == "Atorvastatin"
    assert strip_drug_dosage("Ozempic 1 mg") == "Ozempic"
    assert strip_drug_dosage("Metformin 500 tablets") == "Metformin"

@pytest.mark.asyncio
async def test_intake_routes_to_end_on_not_found():
    graph = build_safety_agent_graph()
    config = {"configurable": {"thread_id": "test_not_found_1"}}

    # Mock openFDA returning 0 results
    empty_faers = {"status": "no_data_found", "reactions": [], "source_url": ""}

    with patch("agent.graph.openfda.search_faers_reactions", new=AsyncMock(return_value=empty_faers)), \
         patch("agent.graph.resolve_drug_active_ingredient", new=AsyncMock(return_value=None)):
        
        initial = AgentState(drug="TotallyFakeDrug123", run_id="run_fake")
        res = await graph.ainvoke(initial.model_dump(), config=config)
        
        snapshot = graph.get_state(config)
        assert snapshot.next == ()
        assert snapshot.values.get("error") is not None
        assert "No adverse event records found in openFDA FAERS" in snapshot.values.get("error")

