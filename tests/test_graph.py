import pytest
from unittest.mock import patch, AsyncMock
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from agent.state import AgentState, ReactionEvidence, FinalAssessment
from agent.graph import build_safety_agent_graph

@pytest.mark.asyncio
async def test_graph_interrupt_and_resume():
    checkpointer = MemorySaver()
    graph = build_safety_agent_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test_thread_123"}}

    # Mock openFDA responses
    mock_reactions = {
        "status": "success",
        "reactions": [
            {"reaction": "RHABDOMYOLYSIS", "count": 150},
            {"reaction": "PANCREATITIS", "count": 90}
        ],
        "source_url": "https://api.fda.gov/mock_faers"
    }

    mock_totals = {
        "drug": "MOCKDRUG",
        "reaction": "RHABDOMYOLYSIS",
        "a": 50,
        "b": 950,
        "c": 100,
        "d": 98900,
        "total_drug": 1000,
        "total_reaction": 150,
        "source_urls": ["https://api.fda.gov/mock_totals"]
    }

    # Unlabeled signal (is_in_label = False)
    mock_label = {
        "is_in_label": False,
        "section": "None",
        "snippet": "Not found in label",
        "source_url": "https://api.fda.gov/mock_label"
    }

    mock_pubmed = {
        "count": 1,
        "articles": [{
            "pmid": "99999999",
            "title": "Severe Rhabdomyolysis Case Report",
            "abstract": "Patient developed acute rhabdomyolysis.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/99999999/"
        }]
    }

    # Mock LLM calls to avoid live Groq API call in test
    async def mock_call_llm(*args, **kwargs):
        class MockAIMessage:
            content = '["RHABDOMYOLYSIS"]'
            invalid_tool_calls = []
        return MockAIMessage()

    with patch("agent.graph.openfda.search_faers_reactions", new=AsyncMock(return_value=mock_reactions)), \
         patch("agent.graph.openfda.get_faers_totals", new=AsyncMock(return_value=mock_totals)), \
         patch("agent.graph.openfda.check_reaction_in_label", new=AsyncMock(return_value=mock_label)), \
         patch("agent.graph.pubmed.search_pubmed", new=AsyncMock(return_value=mock_pubmed)), \
         patch("agent.graph.call_llm_with_resilience", side_effect=mock_call_llm):

        initial_state = AgentState(drug="MockDrug", run_id="test_run_123")
        
        # 1. Run until human_review interrupt
        res = await graph.ainvoke(initial_state.model_dump(), config=config)
        
        # Verify graph paused at human_review interrupt
        snapshot = graph.get_state(config)
        assert snapshot.next == ("human_review",)
        assert len(snapshot.tasks) > 0
        interrupt_val = snapshot.tasks[0].interrupts[0].value
        assert "Unlabeled statistical safety signal detected" in interrupt_val.get("reason", "")
        assert interrupt_val.get("drug") == "Mockdrug"

        # 2. Resume graph with user approval
        res_resumed = await graph.ainvoke(Command(resume={"action": "approve"}), config=config)
        
        # Verify graph completed
        final_snapshot = graph.get_state(config)
        assert final_snapshot.next == ()
        assert final_snapshot.values.get("review_status") == "approved"
        assert final_snapshot.values.get("needs_human_review") is False
