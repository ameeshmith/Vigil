import os
import time
import asyncio
from typing import Optional, Callable, Any, List, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from agent.state import FinalAssessment

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_CRITIC_MODEL = os.environ.get("GROQ_CRITIC_MODEL", "llama-3.3-70b-versatile")

def get_chat_model(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    is_critic: bool = False
) -> ChatGroq:
    """Instantiate a ChatGroq client with requested configuration."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not model_name:
        model_name = DEFAULT_CRITIC_MODEL if is_critic else DEFAULT_MODEL
    
    return ChatGroq(
        api_key=api_key or "gsk_dummy_key_for_testing",
        model=model_name,
        temperature=temperature,
        max_retries=0  # Handled in custom resilient loop for SSE trace visibility
    )

async def call_llm_with_resilience(
    llm: Any,
    messages: List[BaseMessage],
    tools: Optional[List[Any]] = None,
    on_trace_event: Optional[Callable[[str, str], Any]] = None,
    max_429_retries: int = 4
) -> AIMessage:
    """
    Execute LLM call with exponential backoff on 429 rate limits and trace event emissions.
    Also handles malformed tool-call retries (up to 2 times).
    """
    bound_llm = llm
    if tools:
        bound_llm = llm.bind_tools(tools, tool_choice="auto")

    current_messages = list(messages)
    tool_retry_count = 0
    max_tool_retries = 2

    while True:
        wait_time = 2.0
        success = False
        last_error = None
        response = None

        # 429 Rate Limit Retry Loop
        for attempt in range(max_429_retries + 1):
            try:
                response = await bound_llm.ainvoke(current_messages)
                success = True
                break
            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                # Check for rate limit or quota
                if "429" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
                    if on_trace_event:
                        on_trace_event("warning", f"Rate limited by Groq API (429). Retrying in {wait_time:.1f}s (attempt {attempt+1}/{max_429_retries})...")
                    await asyncio.sleep(wait_time)
                    wait_time = min(30.0, wait_time * 2.0)
                else:
                    # Non-429 error (could be malformed JSON or tool call format error)
                    break

        if not success:
            raise last_error

        # Check for malformed tool calls or tool call parsing failure
        # In LangChain / Groq, invalid tool calls often populate additional_kwargs or invalid_tool_calls
        invalid_calls = getattr(response, "invalid_tool_calls", None)
        if invalid_calls and tool_retry_count < max_tool_retries:
            tool_retry_count += 1
            if on_trace_event:
                on_trace_event("warning", f"Malformed tool call detected from LLM. Retrying with error feedback ({tool_retry_count}/{max_tool_retries})...")
            
            # Feed error back to model
            current_messages.append(response)
            error_msg = f"Your previous tool call was malformed: {invalid_calls}. Please regenerate the tool call with valid JSON arguments adhering strictly to the schema."
            current_messages.append(HumanMessage(content=error_msg))
            continue

        return response

async def generate_structured_assessment(
    prompt: str,
    on_trace_event: Optional[Callable[[str, str], Any]] = None
) -> FinalAssessment:
    """Generate structured FinalAssessment using Pydantic output schema, with 1 retry on validation failure."""
    llm = get_chat_model(temperature=0.0)
    structured_llm = llm.with_structured_output(FinalAssessment)

    for attempt in range(2):
        try:
            res = await structured_llm.ainvoke([
                SystemMessage(content="You are a senior pharmacovigilance safety scientist. Output only the structured drug safety assessment according to the specified schema."),
                HumanMessage(content=prompt)
            ])
            if isinstance(res, FinalAssessment):
                return res
            elif isinstance(res, dict):
                return FinalAssessment(**res)
        except Exception as e:
            if on_trace_event:
                on_trace_event("warning", f"Structured output parsing failed on attempt {attempt+1}: {str(e)}. Retrying...")
            if attempt == 1:
                # Fallback minimal valid structure if LLM parsing fails completely
                return FinalAssessment(
                    drug="Specified Drug",
                    executive_summary="Preliminary automated pharmacovigilance synthesis.",
                    signals=[],
                    detailed_findings=f"Assessment generation encountered parsing difficulty: {str(e)}",
                    clinical_recommendation="Consult full FAERS reports and medical reference.",
                    limitations="Spontaneous reporting in FAERS does not establish causation and is subject to reporting bias and lack of denominator incidence data.",
                    citations=["https://api.fda.gov/drug/event.json"]
                )
            await asyncio.sleep(1.0)

