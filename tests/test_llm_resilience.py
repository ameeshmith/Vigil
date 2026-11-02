import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from agent.llm import call_llm_with_resilience

@pytest.mark.asyncio
async def test_simulated_429_backoff_and_recovery():
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound

    trace_events = []
    def on_event(ev_type, msg):
        trace_events.append((ev_type, msg))

    # First call raises 429, second call succeeds
    valid_ai_msg = AIMessage(content="Final synthesized assessment without error.")
    mock_bound.ainvoke = AsyncMock(side_effect=[
        Exception("HTTP 429 Too Many Requests: Rate limit exceeded for default tier."),
        valid_ai_msg
    ])

    with pytest.MonkeyPatch.context() as mp:
        # Patch asyncio.sleep so test runs instantly without waiting 2s
        mp.setattr(asyncio, "sleep", AsyncMock())
        
        res = await call_llm_with_resilience(
            llm=mock_llm,
            messages=[HumanMessage(content="Investigate drug safety.")],
            tools=["dummy_tool"],
            on_trace_event=on_event,
            max_429_retries=2
        )

    assert res.content == "Final synthesized assessment without error."
    assert mock_bound.ainvoke.call_count == 2
    assert any("429" in msg for _, msg in trace_events)

@pytest.mark.asyncio
async def test_malformed_tool_call_retry():
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound

    trace_events = []
    def on_event(ev_type, msg):
        trace_events.append((ev_type, msg))

    # 1st call returns an AIMessage with invalid_tool_calls
    bad_msg = AIMessage(content="")
    bad_msg.invalid_tool_calls = [{"name": "compute_disproportionality", "args": "{bad_json: 1,"}]

    # 2nd call returns valid AIMessage
    good_msg = AIMessage(content="Tool execution resolved correctly.")
    good_msg.invalid_tool_calls = []

    mock_bound.ainvoke = AsyncMock(side_effect=[bad_msg, good_msg])

    res = await call_llm_with_resilience(
        llm=mock_llm,
        messages=[HumanMessage(content="Calculate statistics.")],
        tools=["dummy_tool"],
        on_trace_event=on_event
    )

    assert res.content == "Tool execution resolved correctly."
    assert mock_bound.ainvoke.call_count == 2
    assert any("Malformed tool call" in msg for _, msg in trace_events)

