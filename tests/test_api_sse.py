import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from api.app import app
from api.routes import broadcast_event, RUNS

@pytest.mark.asyncio
async def test_sse_event_stream_order():
    transport = ASGITransport(app=app)
    
    # Mock background graph execution so this SSE test focuses strictly on SSE streaming and order
    with patch("api.routes.execute_graph_run", new=AsyncMock()):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create a run
            resp = await client.post("/api/runs", json={"drug": "Simvastatin"})
            assert resp.status_code == 200
            data = resp.json()
            run_id = data["run_id"]
            assert run_id in RUNS

            # 2. Add sequential test events to the run queue
            event_types = ["node_start", "tool_call", "tool_result", "critic_verdict", "final"]
            for idx, et in enumerate(event_types):
                await broadcast_event(run_id, et, f"Event {et} #{idx}", {"step": idx})

            # 3. Read SSE stream
            received_events = []
            async with client.stream("GET", f"/api/runs/{run_id}/events") as stream_resp:
                assert stream_resp.status_code == 200
                assert "text/event-stream" in stream_resp.headers["content-type"]
                
                async for line in stream_resp.aiter_lines():
                    if line.startswith("event:"):
                        ev_name = line.replace("event:", "").strip()
                        received_events.append(ev_name)
                    # Once we have captured the 5 test events, exit stream
                    if len(received_events) >= len(event_types):
                        break

            # 4. Check order of stream events
            for expected in event_types:
                assert expected in received_events
            
            indices = [received_events.index(et) for et in event_types]
            assert indices == sorted(indices), f"Event stream order violated: {received_events}"
