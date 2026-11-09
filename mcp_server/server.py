import os
import sys

# Ensure repository root is on sys.path regardless of where Python is invoked from
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState, FinalAssessment
from agent.graph import build_safety_agent_graph, get_default_checkpointer
from agent.llm import get_chat_model
from mcp_server.stats import compute_disproportionality as compute_stats
from mcp_server.openfda_client import OpenFDAClient
from mcp_server.pubmed_client import PubMedClient
from mcp_server.constants import DISCLAIMER, current_iso_timestamp

PORT = int(os.environ.get("MCP_PORT", 8001))
HOST = os.environ.get("MCP_HOST", "127.0.0.1")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

mcp = FastMCP("VigilAI", host=HOST, port=PORT)
openfda = OpenFDAClient()
pubmed = PubMedClient()

# Shared persistent checkpointer & compiled graph
CHECKPOINTER = get_default_checkpointer()
GRAPH = build_safety_agent_graph(checkpointer=CHECKPOINTER)


def extract_groq_api_key(groq_api_key: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Extract Groq API key in order of precedence:
    1. Direct argument passed by client/tool caller
    2. HTTP Request header 'X-Groq-Api-Key' via FastMCP Context
    3. GROQ_API_KEY environment variable (for local testing/CLI)
    """
    if groq_api_key and groq_api_key.strip():
        return groq_api_key.strip()

    if ctx and hasattr(ctx, "request_context") and ctx.request_context:
        req = getattr(ctx.request_context, "request", None)
        if req and hasattr(req, "headers"):
            hdr = req.headers.get("x-groq-api-key") or req.headers.get("X-Groq-Api-Key")
            if hdr and hdr.strip():
                return hdr.strip()

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    return ""


def save_run_record(run_id: str, data: Dict[str, Any]) -> str:
    """Save execution report to data/ directory for persistence."""
    cleaned_id = run_id.replace("run_", "")
    path = os.path.join(DATA_DIR, f"run_{cleaned_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[Warning] Failed to save report {run_id}: {e}", file=sys.stderr)
    return path


# ==============================================================================
# LAYER 1: LOW-LEVEL DETERMINISTIC STATS & PHARMACOVIGILANCE LOOKUP TOOLS
# Zero LLM math: All disproportionality metrics computed in Python.
# No API key required.
# ==============================================================================

@mcp.tool()
async def search_faers_reactions(drug: str, limit: int = 15) -> Dict[str, Any]:
    """
    Search top MedDRA adverse drug reaction terms and report counts for a drug from FDA FAERS.
    
    WHEN TO USE:
    Call this first to discover candidate adverse events associated with a drug before
    calculating statistical disproportionality.
    
    INPUTS:
    - drug: Name of the pharmaceutical substance or brand (e.g. 'Atorvastatin', 'Ozempic')
    - limit: Number of top reactions to return (default: 15, max: 50)
    
    OUTPUTS:
    - reactions: List of dicts with 'reaction' (MedDRA PT) and 'count' (FAERS case reports)
    - data_source: openFDA FAERS endpoint
    - retrieved_at: ISO 8601 retrieval timestamp
    - disclaimer: Educational/research disclaimer
    """
    print(f"[Vigil MCP] search_faers_reactions called: drug={drug!r}, limit={limit}", file=sys.stderr)
    res = await openfda.search_faers_reactions(drug=drug, limit=limit)
    print(f"[Vigil MCP] search_faers_reactions result: status={res.get('status')}, reactions={res.get('count_reactions')}, matched={res.get('matched_drug')}", file=sys.stderr)
    return res


@mcp.tool()
async def get_faers_totals(drug: str, reaction: str) -> Dict[str, Any]:
    """
    Retrieve 2x2 contingency table counts for a drug-reaction pair from openFDA FAERS.
    
    WHEN TO USE:
    Use this after selecting a candidate reaction to fetch the cell counts (a, b, c, d)
    required for disproportionality calculation.
    
    CONTINGENCY TABLE STRUCTURE:
    - a: Target Drug + Target Reaction reports
    - b: Target Drug + Other Reaction reports (total_drug - a)
    - c: Other Drugs + Target Reaction reports (total_reaction - a)
    - d: Other Drugs + Other Reactions (total_faers - a - b - c)
    
    INPUTS:
    - drug: Target drug name (e.g. 'Simvastatin')
    - reaction: Target MedDRA Preferred Term (e.g. 'Rhabdomyolysis')
    
    OUTPUTS:
    - a, b, c, d integers, totals, source_urls, data_source, retrieved_at, disclaimer.
    """
    print(f"[Vigil MCP] get_faers_totals called: drug={drug!r}, reaction={reaction!r}", file=sys.stderr)
    res = await openfda.get_faers_totals(drug=drug, reaction=reaction)
    print(f"[Vigil MCP] get_faers_totals result: status={res.get('status')}, a={res.get('a')}, b={res.get('b')}, c={res.get('c')}, d={res.get('d')}", file=sys.stderr)
    return res


@mcp.tool()
def compute_disproportionality(a: int, b: int, c: int, d: int) -> Dict[str, Any]:
    """
    Compute pharmacovigilance disproportionality statistics (PRR, ROR, Yates' Chi-Square).
    
    ZERO LLM MATH GUARANTEE:
    All calculations are evaluated strictly in Python with zero division protection.
    Never compute these formulas with an LLM.
    
    SIGNAL CRITERIA (Evans Criteria):
    A statistical signal is flagged if:
    1. PRR >= 2.0
    2. a >= 3 reports
    3. Chi-square with Yates' continuity correction >= 4.0
    
    INPUTS:
    - a: Reports with target drug and target reaction
    - b: Reports with target drug and other reactions
    - c: Reports with other drugs and target reaction
    - d: Reports with other drugs and other reactions
    
    OUTPUTS:
    - prr, prr_ci_lower, prr_ci_upper (95% CI)
    - ror, ror_ci_lower, ror_ci_upper (95% CI)
    - chi_square (Yates' corrected)
    - signal_flag: boolean (Evans criteria met)
    """
    print(f"[Vigil MCP] compute_disproportionality called: a={a}, b={b}, c={c}, d={d}", file=sys.stderr)
    res = compute_stats(a=a, b=b, c=c, d=d)
    print(f"[Vigil MCP] compute_disproportionality result: prr={res.get('prr')}, ror={res.get('ror')}, chi2={res.get('chi_square')}, signal={res.get('signal_flag')}", file=sys.stderr)
    return res


@mcp.tool()
async def get_label_sections(drug: str) -> Dict[str, Any]:
    """
    Retrieve official FDA package insert sections (Boxed Warning, Warnings & Precautions, Adverse Reactions).
    
    WHEN TO USE:
    Query this to inspect the official regulatory prescribing information for a drug to
    verify if an adverse reaction is already known and labeled.
    
    INPUTS:
    - drug: Drug name (e.g. 'Semaglutide')
    
    OUTPUTS:
    - sections: Dict with 'boxed_warning', 'warnings_and_precautions', 'adverse_reactions'
    - has_label: boolean indicating whether FDA label was located
    - source_url, data_source, retrieved_at, disclaimer.
    """
    print(f"[Vigil MCP] get_label_sections called: drug={drug!r}", file=sys.stderr)
    res = await openfda.get_label_sections(drug=drug)
    print(f"[Vigil MCP] get_label_sections result: status={res.get('status')}, has_label={res.get('has_label')}, matched={res.get('matched_drug')}", file=sys.stderr)
    return res


@mcp.tool()
async def check_reaction_in_label(drug: str, reaction: str) -> Dict[str, Any]:
    """
    Check if a specific adverse reaction term is documented in the FDA approved drug label.
    
    WHEN TO USE:
    Chain this after computing disproportionality to classify signals as LABELED (already known)
    or UNLABELED (potential new prospective safety signal).
    
    INPUTS:
    - drug: Drug name (e.g. 'Atorvastatin')
    - reaction: Adverse reaction term (e.g. 'Pancreatitis')
    
    OUTPUTS:
    - is_in_label: boolean
    - section: Matching label section name ('boxed_warning', 'warnings_and_precautions', 'adverse_reactions', or 'None')
    - snippet: Contextual verbatim snippet (< 500 characters) showing the exact labeling text
    """
    print(f"[Vigil MCP] check_reaction_in_label called: drug={drug!r}, reaction={reaction!r}", file=sys.stderr)
    res = await openfda.check_reaction_in_label(drug=drug, reaction=reaction)
    print(f"[Vigil MCP] check_reaction_in_label result: is_in_label={res.get('is_in_label')}, section={res.get('section')}, matched={res.get('matched_drug')}", file=sys.stderr)
    return res


@mcp.tool()
async def search_pubmed(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search PubMed biomedical literature via NCBI E-utilities (esearch + efetch).
    
    WHEN TO USE:
    Strictly when an Evans-criteria statistical signal is ABSENT from the FDA drug label,
    search PubMed to retrieve published case reports, clinical trials, or mechanisms.
    
    INPUTS:
    - query: Biomedical search query (e.g. 'Atorvastatin AND Acute Pancreatitis')
    - max_results: Number of articles to retrieve (default: 5)
    
    OUTPUTS:
    - articles: List of PMIDs, titles, publication years, short abstracts, and PubMed URLs
    - data_source, retrieved_at, disclaimer.
    """
    return await pubmed.search_pubmed(query=query, max_results=max_results)


# ==============================================================================
# LAYER 2: HIGH-LEVEL AGENT WORKFLOW & INVESTIGATION TOOLS
# Wraps the LangGraph workflow: Planner -> Investigator -> Writer -> Critic -> Human Review.
# ==============================================================================

@mcp.tool()
async def investigate_signal(
    drug: str,
    event: Optional[str] = None,
    max_revisions: int = 2,
    groq_api_key: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Execute the full autonomous Vigil AI pharmacovigilance investigation for a drug.
    
    Coordinates the 4-agent LangGraph workflow:
    1. Planner Node: Selects clinically sentinel adverse reactions from FAERS.
    2. Investigator Node: Gathers 2x2 contingency tables, evaluates disproportionality (zero-LLM math),
       checks FDA package insert, and conditionally searches PubMed for unlabeled signals.
    3. Writer Node: Synthesizes evidence, citations, and mandatory FAERS limitations.
    4. Critic Node: Deterministically validates all figures against tool outputs.
    5. Human Review Gate: If an unlabeled signal or thin evidence is found, pauses with status 'needs_input'.
    
    INPUTS:
    - drug: Drug name to investigate (e.g. 'Atorvastatin', 'Ozempic')
    - event: Optional specific reaction to investigate (e.g. 'Pancreatitis'). If omitted, top signals are selected.
    - max_revisions: Max critique-revision cycles (default: 2)
    - groq_api_key: Caller's Groq API key (can also be supplied via 'X-Groq-Api-Key' HTTP header or GROQ_API_KEY env)
    
    OUTPUTS:
    - If Human Review required: Returns status 'needs_input', run_id, question, reason, and draft.
    - If Completed: Returns status 'completed', run_id, summary, statistics, citations, critic_verdict, and assessment.
    """
    api_key = extract_groq_api_key(groq_api_key, ctx)
    if not api_key:
        return {
            "status": "missing_api_key",
            "error": (
                "Missing Groq API Key. High-level agent synthesis requires an LLM. "
                "Please provide your Groq API key via the 'groq_api_key' parameter, "
                "the 'X-Groq-Api-Key' HTTP header, or set GROQ_API_KEY in the environment."
            ),
            "run_id": "",
            "disclaimer": DISCLAIMER,
            "retrieved_at": current_iso_timestamp()
        }

    run_id = f"mcp_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": run_id}}

    selected_rxns = [event.strip().upper()] if event and event.strip() else []
    initial_state = AgentState(
        drug=drug,
        run_id=run_id,
        api_key=api_key,
        selected_reactions=selected_rxns
    )

    stage_progress = {
        "intake": (15, "Normalizing drug name and fetching FAERS baseline..."),
        "planner": (35, "Selecting safety-critical candidate reactions..."),
        "investigator": (65, "Computing disproportionality statistics & auditing FDA labels..."),
        "writer": (85, "Synthesizing clinical safety dossier & citations..."),
        "critic": (95, "Validating statistical fidelity & regulatory compliance..."),
        "human_review": (100, "Evaluating human review safety threshold...")
    }

    try:
        if ctx:
            await ctx.report_progress(5, 100, f"Initiating Vigil AI investigation for {drug}...")
            await ctx.info(f"Starting investigation for {drug} (run_id: {run_id})")

        # Stream graph updates with 90-second timeout guard
        async def run_stream():
            last_node = ""
            async for step in GRAPH.astream(initial_state.model_dump(), config=config, stream_mode="updates"):
                if isinstance(step, dict):
                    for node_name in step.keys():
                        last_node = node_name
                        if node_name in stage_progress and ctx:
                            pct, msg = stage_progress[node_name]
                            try:
                                await ctx.report_progress(pct, 100, msg)
                                await ctx.info(f"[{node_name.upper()}] {msg}")
                            except Exception:
                                pass
            return last_node

        await asyncio.wait_for(run_stream(), timeout=90.0)

        # Inspect final checkpoint snapshot
        snapshot = GRAPH.get_state(config)
        state_vals = snapshot.values

        # Check for intake failure (drug not found)
        if state_vals.get("error"):
            return {
                "status": "not_found",
                "run_id": run_id,
                "drug": drug,
                "error": state_vals["error"],
                "disclaimer": DISCLAIMER,
                "retrieved_at": current_iso_timestamp()
            }

        # Check if graph paused at Human Review Gate interrupt
        if snapshot.next and "human_review" in snapshot.next:
            reason = state_vals.get("human_review_reason", "Unlabeled statistical signal or thin evidence detected")
            evidence_summary = {}
            for k, ev in state_vals.get("evidence", {}).items():
                evidence_summary[k] = ev.model_dump() if hasattr(ev, "model_dump") else ev

            question = (
                f"Vigil AI Human Review Gate: Review required for '{state_vals.get('normalized_drug', drug)}'. "
                f"Reason: {reason}. "
                f"Call 'resume_investigation(run_id=\"{run_id}\", answer=\"approve\")' to finalize, "
                f"'edit' to provide modified text, or 'investigate_more' to deepen surveillance."
            )

            result = {
                "status": "needs_input",
                "run_id": run_id,
                "drug": state_vals.get("normalized_drug", drug),
                "question": question,
                "reason": reason,
                "evidence": evidence_summary,
                "draft": state_vals.get("draft", ""),
                "disclaimer": DISCLAIMER,
                "retrieved_at": current_iso_timestamp()
            }
            save_run_record(run_id, result)
            return result

        # Investigation completed
        sa = state_vals.get("structured_assessment")
        evidence_dict = {
            k: (v.model_dump() if hasattr(v, "model_dump") else v)
            for k, v in state_vals.get("evidence", {}).items()
        }
        statistics_list = [
            {
                "reaction": k,
                "a": v.get("a", 0),
                "prr": v.get("prr", 0.0),
                "ror": v.get("ror", 0.0),
                "chi_square": v.get("chi_square", 0.0),
                "signal_flag": v.get("signal_flag", False),
                "is_in_label": v.get("is_in_label", False)
            }
            for k, v in evidence_dict.items()
        ]

        assessment_data = sa.model_dump() if hasattr(sa, "model_dump") else (sa or {})

        result = {
            "status": "completed",
            "run_id": run_id,
            "drug": state_vals.get("normalized_drug", drug),
            "summary": assessment_data.get("executive_summary", ""),
            "statistics": statistics_list,
            "evidence": evidence_dict,
            "citations": assessment_data.get("citations", []),
            "critic_verdict": "PASS" if state_vals.get("critic_passes") else "AUDITED",
            "assessment": assessment_data,
            "draft": state_vals.get("draft", ""),
            "data_source": "openFDA FAERS, FDA Drug Labels, NCBI PubMed",
            "retrieved_at": current_iso_timestamp(),
            "disclaimer": DISCLAIMER
        }

        save_run_record(run_id, result)
        if ctx:
            await ctx.report_progress(100, 100, "Safety investigation completed.")
        return result

    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "run_id": run_id,
            "drug": drug,
            "error": f"Signal investigation timed out after 90 seconds. Current progress checkpointed under run_id '{run_id}'.",
            "disclaimer": DISCLAIMER,
            "retrieved_at": current_iso_timestamp()
        }
    except Exception as e:
        return {
            "status": "error",
            "run_id": run_id,
            "drug": drug,
            "error": f"Investigation failed: {str(e)}",
            "disclaimer": DISCLAIMER,
            "retrieved_at": current_iso_timestamp()
        }


@mcp.tool()
async def resume_investigation(
    run_id: str,
    answer: str,
    edited_draft: Optional[str] = None,
    groq_api_key: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Resume an investigation that paused at the Human Review Gate interrupt().
    
    INPUTS:
    - run_id: Execution thread identifier returned by investigate_signal (with status 'needs_input')
    - answer: Decision choice: 'approve', 'edit', or 'investigate_more'
    - edited_draft: Optional clinician-edited text (used when answer is 'edit')
    - groq_api_key: Optional Groq API key
    
    OUTPUTS:
    - Final validated structured safety assessment report.
    """
    config = {"configurable": {"thread_id": run_id}}
    snapshot = GRAPH.get_state(config)

    if not snapshot.values:
        # Check if saved run file exists
        saved_path = os.path.join(DATA_DIR, f"run_{run_id.replace('run_', '')}.json")
        if os.path.exists(saved_path):
            try:
                with open(saved_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("status") == "completed":
                        return data
            except Exception:
                pass
        return {
            "status": "error",
            "run_id": run_id,
            "error": f"No active paused checkpoint found for run_id '{run_id}'.",
            "disclaimer": DISCLAIMER
        }

    clean_action = answer.strip().lower()
    if clean_action not in ("approve", "edit", "investigate_more"):
        clean_action = "approve"

    resume_payload = {
        "action": clean_action,
        "payload": {"edited_draft": edited_draft} if edited_draft else {}
    }

    if ctx:
        await ctx.report_progress(50, 100, f"Resuming investigation with decision: '{clean_action}'...")
        await ctx.info(f"Resuming {run_id} with decision '{clean_action}'")

    resume_cmd = Command(resume=resume_payload)

    try:
        async for _ in GRAPH.astream(resume_cmd, config=config, stream_mode="updates"):
            pass

        updated_snapshot = GRAPH.get_state(config)
        state_vals = updated_snapshot.values
        sa = state_vals.get("structured_assessment")
        evidence_dict = {
            k: (v.model_dump() if hasattr(v, "model_dump") else v)
            for k, v in state_vals.get("evidence", {}).items()
        }
        assessment_data = sa.model_dump() if hasattr(sa, "model_dump") else (sa or {})

        result = {
            "status": "completed",
            "run_id": run_id,
            "drug": state_vals.get("normalized_drug", ""),
            "summary": assessment_data.get("executive_summary", ""),
            "evidence": evidence_dict,
            "citations": assessment_data.get("citations", []),
            "critic_verdict": "PASS" if state_vals.get("critic_passes") else "AUDITED",
            "assessment": assessment_data,
            "draft": state_vals.get("draft", ""),
            "data_source": "openFDA FAERS, FDA Drug Labels, NCBI PubMed",
            "retrieved_at": current_iso_timestamp(),
            "disclaimer": DISCLAIMER
        }

        save_run_record(run_id, result)
        if ctx:
            await ctx.report_progress(100, 100, "Investigation resumed and completed.")
        return result

    except Exception as e:
        return {
            "status": "error",
            "run_id": run_id,
            "error": f"Failed to resume run: {str(e)}",
            "disclaimer": DISCLAIMER
        }


@mcp.tool()
async def compare_drugs(
    drug_a: str,
    drug_b: str,
    event: str,
    groq_api_key: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Perform a side-by-side pharmacovigilance disproportionality comparison between two drugs
    for a specific adverse reaction event.
    
    ZERO-LLM MATH:
    Contingency counts, PRR, ROR, 95% CIs, and Yates' Chi-Square are computed purely in Python.
    
    INPUTS:
    - drug_a: Name of the first drug (e.g. 'Atorvastatin')
    - drug_b: Name of the comparator drug (e.g. 'Simvastatin')
    - event: Target adverse reaction MedDRA term (e.g. 'Rhabdomyolysis')
    - groq_api_key: Optional Groq API key for generating comparative narrative
    
    OUTPUTS:
    - Side-by-side statistics, labeling status, and comparative narrative.
    """
    clean_event = event.strip().upper()
    timestamp = current_iso_timestamp()

    if ctx:
        await ctx.report_progress(20, 100, f"Querying FAERS totals for {drug_a} & {drug_b}...")

    # Concurrently fetch FAERS totals and label checks for both drugs
    t_a_task = openfda.get_faers_totals(drug_a, clean_event)
    t_b_task = openfda.get_faers_totals(drug_b, clean_event)
    lbl_a_task = openfda.check_reaction_in_label(drug_a, clean_event)
    lbl_b_task = openfda.check_reaction_in_label(drug_b, clean_event)

    t_a, t_b, lbl_a, lbl_b = await asyncio.gather(t_a_task, t_b_task, lbl_a_task, lbl_b_task)

    if ctx:
        await ctx.report_progress(60, 100, "Computing disproportionality statistics...")

    # Deterministic stats (zero-LLM math)
    stats_a = compute_stats(t_a["a"], t_a["b"], t_a["c"], t_a["d"])
    stats_b = compute_stats(t_b["a"], t_b["b"], t_b["c"], t_b["d"])

    # Comparative Narrative (LLM if key present, else deterministic objective summary)
    api_key = extract_groq_api_key(groq_api_key, ctx)
    narrative = ""

    if api_key:
        if ctx:
            await ctx.report_progress(80, 100, "Synthesizing comparative narrative...")
        prompt = f"""You are a clinical pharmacovigilance epidemiologist.
Synthesize a concise 3-4 sentence comparative safety analysis comparing two drugs for '{clean_event}':

Drug A ({drug_a}):
- Reports: {t_a['a']} (Total Drug Reports: {t_a['total_drug']})
- PRR: {stats_a['prr']} (95% CI: {stats_a['prr_ci_lower']} - {stats_a['prr_ci_upper']})
- ROR: {stats_a['ror']} (95% CI: {stats_a['ror_ci_lower']} - {stats_a['ror_ci_upper']})
- Yates Chi2: {stats_a['chi_square']} (Evans Signal: {stats_a['signal_flag']})
- FDA Label Status: {'Labeled in ' + lbl_a.get('section', '') if lbl_a.get('is_in_label') else 'Unlabeled'}

Drug B ({drug_b}):
- Reports: {t_b['a']} (Total Drug Reports: {t_b['total_drug']})
- PRR: {stats_b['prr']} (95% CI: {stats_b['prr_ci_lower']} - {stats_b['prr_ci_upper']})
- ROR: {stats_b['ror']} (95% CI: {stats_b['ror_ci_lower']} - {stats_b['ror_ci_upper']})
- Yates Chi2: {stats_b['chi_square']} (Evans Signal: {stats_b['signal_flag']})
- FDA Label Status: {'Labeled in ' + lbl_b.get('section', '') if lbl_b.get('is_in_label') else 'Unlabeled'}

Highlight relative reporting rates and labeling discrepancies objectively. Do not fabricate numbers.
"""
        try:
            llm = get_chat_model(temperature=0.0, api_key=api_key)
            resp = await llm.ainvoke([
                SystemMessage(content="You are a clinical pharmacovigilance specialist. Output strictly the comparative narrative."),
                HumanMessage(content=prompt)
            ])
            narrative = resp.content.strip()
        except Exception:
            narrative = ""

    if not narrative:
        # Deterministic comparative summary fallback
        sig_a_str = "meets" if stats_a["signal_flag"] else "does not meet"
        sig_b_str = "meets" if stats_b["signal_flag"] else "does not meet"
        lbl_a_str = f"documented in {lbl_a.get('section')}" if lbl_a.get("is_in_label") else "unlabeled"
        lbl_b_str = f"documented in {lbl_b.get('section')}" if lbl_b.get("is_in_label") else "unlabeled"

        narrative = (
            f"Comparative disproportionality analysis for '{clean_event}': "
            f"{drug_a} shows a PRR of {stats_a['prr']} (95% CI: {stats_a['prr_ci_lower']}-{stats_a['prr_ci_upper']}, "
            f"{t_a['a']} reports; {lbl_a_str}), which {sig_a_str} Evans criteria. "
            f"In comparison, {drug_b} exhibits a PRR of {stats_b['prr']} (95% CI: {stats_b['prr_ci_lower']}-{stats_b['prr_ci_upper']}, "
            f"{t_b['a']} reports; {lbl_b_str}), which {sig_b_str} Evans criteria. "
            f"Spontaneous reporting figures cannot determine clinical incidence rates."
        )

    if ctx:
        await ctx.report_progress(100, 100, "Drug comparison complete.")

    return {
        "status": "success",
        "event": clean_event,
        "drug_a": {
            "drug": drug_a,
            "counts": {"a": t_a["a"], "b": t_a["b"], "c": t_a["c"], "d": t_a["d"], "total_drug": t_a["total_drug"]},
            "statistics": stats_a,
            "label_status": {
                "is_in_label": lbl_a.get("is_in_label", False),
                "section": lbl_a.get("section", "None"),
                "snippet": lbl_a.get("snippet", "")
            }
        },
        "drug_b": {
            "drug": drug_b,
            "counts": {"a": t_b["a"], "b": t_b["b"], "c": t_b["c"], "d": t_b["d"], "total_drug": t_b["total_drug"]},
            "statistics": stats_b,
            "label_status": {
                "is_in_label": lbl_b.get("is_in_label", False),
                "section": lbl_b.get("section", "None"),
                "snippet": lbl_b.get("snippet", "")
            }
        },
        "comparative_narrative": narrative,
        "data_source": "openFDA FAERS & FDA Drug Labels",
        "retrieved_at": timestamp,
        "disclaimer": DISCLAIMER
    }


@mcp.tool()
async def get_report(run_id: str) -> Dict[str, Any]:
    """
    Fetch a saved pharmacovigilance safety investigation report by its run_id.
    
    INPUTS:
    - run_id: Unique execution identifier (e.g. 'atorvastatin', 'ozempic', or a run UUID)
    
    OUTPUTS:
    - The stored report JSON object including assessment, disproportionality statistics, and evidence.
    """
    clean_id = run_id.replace("run_", "").strip().lower()

    # 1. Check data/ directory for run_{clean_id}.json
    candidate_paths = [
        os.path.join(DATA_DIR, f"run_{clean_id}.json"),
        os.path.join(DATA_DIR, f"run_{run_id}.json"),
        os.path.join(DATA_DIR, f"{clean_id}.json"),
        os.path.join(DATA_DIR, f"{run_id}.json")
    ]

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                return {"status": "error", "error": f"Failed reading report file: {str(e)}"}

    # 2. Check active checkpoints
    config = {"configurable": {"thread_id": run_id}}
    snapshot = GRAPH.get_state(config)
    if snapshot.values:
        state_vals = snapshot.values
        sa = state_vals.get("structured_assessment")
        return {
            "status": "checkpoint_found",
            "run_id": run_id,
            "drug": state_vals.get("drug", ""),
            "assessment": sa.model_dump() if hasattr(sa, "model_dump") else sa,
            "draft": state_vals.get("draft", ""),
            "evidence": state_vals.get("evidence", {}),
            "disclaimer": DISCLAIMER
        }

    return {
        "status": "not_found",
        "run_id": run_id,
        "error": f"Report for run_id '{run_id}' not found.",
        "disclaimer": DISCLAIMER
    }


# ==============================================================================
# RESOURCES & PROMPT TEMPLATES
# ==============================================================================

@mcp.resource("vigil://reports/{run_id}")
def get_report_resource(run_id: str) -> str:
    """Read a saved pharmacovigilance safety report as JSON."""
    clean_id = run_id.replace("run_", "").strip().lower()
    candidate_paths = [
        os.path.join(DATA_DIR, f"run_{clean_id}.json"),
        os.path.join(DATA_DIR, f"run_{run_id}.json")
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()

    return json.dumps({
        "error": f"Resource vigil://reports/{run_id} not found.",
        "run_id": run_id,
        "status": "not_found"
    }, indent=2)


@mcp.prompt("safety_review")
def safety_review(drug: str, event: Optional[str] = None) -> str:
    """Guided prompt template for client LLMs conducting a pharmacovigilance safety investigation."""
    event_clause = f" with primary focus on the adverse reaction '{event}'" if event else ""
    return f"""You are a clinical pharmacovigilance safety specialist utilizing the Vigil AI MCP Server.
Conduct a comprehensive post-marketing safety investigation for '{drug}'{event_clause}.

INVESTIGATION PROTOCOL:
1. Signal Discovery:
   - Call `search_faers_reactions(drug='{drug}')` to retrieve top adverse reaction counts from FDA FAERS.
2. Disproportionality Metrics (Zero LLM Math):
   - For priority reactions, call `get_faers_totals(drug='{drug}', reaction=...)` to retrieve 2x2 contingency counts.
   - Pass counts (a, b, c, d) to `compute_disproportionality(a=..., b=..., c=..., d=...)`.
   - Record PRR, ROR, 95% confidence intervals, and whether the Evans Criteria (PRR >= 2, a >= 3, chi2 >= 4) is met.
3. Label Concordance:
   - Call `check_reaction_in_label(drug='{drug}', reaction=...)` to classify signals as LABELED or UNLABELED.
4. Targeted Literature Synthesis:
   - If and ONLY IF an Evans-criteria signal is UNLABELED, call `search_pubmed(query=...)` to retrieve corroborating clinical literature.
5. Synthesis & Limitations:
   - Synthesize findings clearly distinguishing between labeled risks and potential new safety signals.
   - Explicitly cite all FAERS and PubMed queries.
   - Always state the core limitations of spontaneous adverse event reporting (absence of true incidence denominator, reporting bias, duplicate submissions).
"""


# SSE App instance for mounting in FastAPI
app = mcp.sse_app()

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse").lower()
    if "--stdio" in sys.argv or transport == "stdio":
        # Stdio mode for local clients (Claude Desktop, Cursor)
        print("Starting Vigil AI MCP Server in STDIO mode...", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        # Streamable HTTP / SSE mode for hosted deployment
        print(f"Starting Vigil AI MCP Server on {HOST}:{PORT} (transport: sse)...")
        mcp.run(transport="sse")
