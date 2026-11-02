import time
import asyncio
from typing import Dict, Any, List, Optional, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from agent.state import AgentState, ReactionEvidence, FinalAssessment, SignalSummary
from agent.llm import get_chat_model, call_llm_with_resilience, generate_structured_assessment
from agent.guardrails import validate_assessment_guardrails
from agent.mcp_client import load_agent_mcp_tools, LOCAL_MCP_TOOLS
from mcp_server.stats import compute_disproportionality
from mcp_server.openfda_client import OpenFDAClient, strip_drug_dosage
from mcp_server.pubmed_client import PubMedClient

openfda = OpenFDAClient()
pubmed = PubMedClient()

def add_event(state: AgentState, node: str, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
    evt = {
        "node": node,
        "event_type": event_type,
        "message": message,
        "data": data or {},
        "timestamp": time.time()
    }
    state.events.append(evt)

async def resolve_drug_active_ingredient(raw_drug: str) -> Optional[Dict[str, str]]:
    """Map international trade names, combination drugs, or dosage brands to active generic ingredients."""
    prompt = f"""You are a clinical pharmacologist.
Given drug name: '{raw_drug}':
1. Identify if this is a combination product or trade name (e.g. 'Naxdom 250' -> Naproxen + Domperidone).
2. Return the primary active generic ingredient that will have adverse event reports in FDA FAERS.
Respond strictly in JSON format:
{{"generic_name": "NAPROXEN", "notes": "Combination product: Naproxen + Domperidone"}}
If it is already a generic name, respond with:
{{"generic_name": "{raw_drug}", "notes": ""}}
"""
    try:
        llm = get_chat_model(temperature=0.0)
        res = await llm.ainvoke([
            SystemMessage(content="You are a clinical pharmacovigilance specialist. Output strictly JSON."),
            HumanMessage(content=prompt)
        ])
        content = res.content.strip()
        import json, re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None

async def intake_node(state: AgentState) -> Dict[str, Any]:
    """Normalize drug name and query initial FAERS reaction pool to ensure drug exists."""
    drug = state.drug.strip()
    clean_name = strip_drug_dosage(drug)
    state.normalized_drug = clean_name.title()
    add_event(state, "intake", "node_start", f"Initiating intake and normalization for drug: '{drug}'")
    
    # Tool call: search_faers_reactions
    add_event(state, "intake", "tool_call", f"Querying openFDA FAERS for top adverse reaction terms: '{clean_name}'", {
        "tool": "search_faers_reactions",
        "arguments": {"drug": clean_name, "limit": 15}
    })
    
    faers_res = await openfda.search_faers_reactions(clean_name, limit=15)
    source_url = faers_res.get("source_url", "")
    reactions = faers_res.get("reactions", [])
    
    # If not found or low report volume (< 5 reactions), attempt clinical generic resolution
    if len(reactions) < 5:
        add_event(state, "intake", "node_step", f"Low or zero reports for trade name '{clean_name}'. Resolving active pharmaceutical ingredients...")
        resolved = await resolve_drug_active_ingredient(drug)
        if resolved and resolved.get("generic_name") and resolved["generic_name"].strip().upper() != clean_name.upper():
            gen_name = resolved["generic_name"].strip().upper()
            add_event(state, "intake", "tool_call", f"Querying FAERS for resolved active generic ingredient: '{gen_name}'", {
                "tool": "search_faers_reactions",
                "arguments": {"drug": gen_name, "limit": 15}
            })
            faers_res_gen = await openfda.search_faers_reactions(gen_name, limit=15)
            gen_reactions = faers_res_gen.get("reactions", [])
            if gen_reactions:
                reactions = gen_reactions
                source_url = faers_res_gen.get("source_url", source_url)
                notes = resolved.get("notes", "")
                state.normalized_drug = gen_name.title()
                add_event(state, "intake", "node_step", f"Successfully resolved '{drug}' -> '{gen_name.title()}' ({len(reactions)} reaction terms found in FAERS). {notes}")

    add_event(state, "intake", "tool_result", f"Retrieved {len(reactions)} reaction candidates from openFDA", {
        "tool": "search_faers_reactions",
        "source_url": source_url,
        "reactions_sample": [r["reaction"] for r in reactions[:5]] if reactions else [],
        "count_reactions": len(reactions)
    })

    if not reactions:
        err_msg = f"No adverse event records found in openFDA FAERS for '{drug}'. FAERS predominantly tracks US-licensed brand names and generic active ingredients."
        add_event(state, "intake", "error", err_msg)
        return {
            "normalized_drug": state.normalized_drug,
            "candidate_reactions": [],
            "error": err_msg,
            "events": state.events
        }

    add_event(state, "intake", "node_end", f"Intake complete: {len(reactions)} candidate reactions discovered for {state.normalized_drug}.")
    return {
        "normalized_drug": state.normalized_drug,
        "candidate_reactions": reactions,
        "events": state.events
    }

async def planner_node(state: AgentState) -> Dict[str, Any]:
    """Safety scientist planner decides which reactions warrant investigation (up to 5)."""
    add_event(state, "planner", "node_start", "Planning safety surveillance priorities based on clinical risk profile...")
    
    if not state.candidate_reactions:
        return {"selected_reactions": []}

    candidate_text = "\n".join([f"- {r['reaction']}: {r['count']} reports" for r in state.candidate_reactions[:15]])
    
    prompt = f"""You are a pharmacovigilance safety scientist.
Drug under investigation: {state.normalized_drug}

Below are the top reported MedDRA adverse events in openFDA FAERS:
{candidate_text}

Task: Select up to 4 to 5 reactions that warrant rigorous safety investigation.
Prioritize:
1. Significant organ toxicities (e.g., hepatic, renal, cardiac, neurological, pancreatitis, rhabdomyolysis)
2. Serious immunological or cutaneous events
3. High-volume unexpected safety signals
Avoid prioritizing non-specific or mild symptoms (e.g., nausea, headache) unless they are clinically sentinel.

Respond ONLY with a JSON list of reaction names matching exactly the names from the list above.
Example: ["RHABDOMYOLYSIS", "ACUTE KIDNEY INJURY", "HEPATIC ENZYME INCREASED"]
"""
    llm = get_chat_model(temperature=0.0)
    try:
        response = await call_llm_with_resilience(
            llm=llm,
            messages=[
                SystemMessage(content="You are a clinical pharmacovigilance specialist. Always output valid JSON arrays."),
                HumanMessage(content=prompt)
            ]
        )
        content = response.content.strip()
        # Parse JSON array
        import json
        import re
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            selected = json.loads(match.group(0))
        else:
            selected = [r["reaction"] for r in state.candidate_reactions[:4]]
    except Exception as e:
        # Fallback to top 4 candidate reactions
        selected = [r["reaction"] for r in state.candidate_reactions[:4]]

    # Ensure reactions exist in candidates and limit to at most 5
    valid_candidates = {r["reaction"].upper(): r["reaction"] for r in state.candidate_reactions}
    cleaned_selected = []
    for s in selected:
        s_upper = str(s).strip().upper()
        if s_upper in valid_candidates and valid_candidates[s_upper] not in cleaned_selected:
            cleaned_selected.append(valid_candidates[s_upper])
        elif len(cleaned_selected) < 5 and str(s).strip() not in cleaned_selected:
            cleaned_selected.append(str(s).strip())

    if not cleaned_selected:
        cleaned_selected = [r["reaction"] for r in state.candidate_reactions[:3]]

    selected_final = cleaned_selected[:5]
    
    add_event(state, "planner", "node_end", f"Planner selected {len(selected_final)} high-priority reactions for investigation: {', '.join(selected_final)}", {
        "selected_reactions": selected_final
    })
    
    return {
        "selected_reactions": selected_final,
        "events": state.events
    }

async def investigator_node(state: AgentState) -> Dict[str, Any]:
    """
    ReAct tool loop executing pharmacovigilance surveillance:
    For each selected reaction:
      1. get_faers_totals -> counts a, b, c, d
      2. compute_disproportionality -> PRR, ROR, 95% CIs, chi2, Evans signal_flag
      3. check_reaction_in_label -> checks FDA package insert
      4. search_pubmed -> ONLY if signal_flag is True and is_in_label is False
    """
    add_event(state, "investigator", "node_start", f"Beginning rigorous statistical and regulatory investigation for {len(state.selected_reactions)} reactions...")
    drug = state.normalized_drug
    evidence_map = dict(state.evidence)

    for reaction in state.selected_reactions:
        add_event(state, "investigator", "tool_call", f"Calculating 2x2 contingency totals for {reaction}", {
            "tool": "get_faers_totals",
            "arguments": {"drug": drug, "reaction": reaction}
        })
        
        totals_res = await openfda.get_faers_totals(drug=drug, reaction=reaction)
        a = totals_res.get("a", 0)
        b = totals_res.get("b", 0)
        c = totals_res.get("c", 0)
        d = totals_res.get("d", 0)
        source_urls = list(totals_res.get("source_urls", []))

        add_event(state, "investigator", "tool_result", f"Contingency counts for {reaction}: a={a}, b={b}, c={c}, d={d}", {
            "tool": "get_faers_totals",
            "counts": {"a": a, "b": b, "c": c, "d": d},
            "source_urls": source_urls[:2]
        })

        # Step 2: Compute disproportionality (All stats computed in tool, never LLM)
        add_event(state, "investigator", "tool_call", f"Computing Evans disproportionality metrics for {reaction}", {
            "tool": "compute_disproportionality",
            "arguments": {"a": a, "b": b, "c": c, "d": d}
        })
        
        stats = compute_disproportionality(a=a, b=b, c=c, d=d)
        prr = stats["prr"]
        ror = stats["ror"]
        chi2 = stats["chi_square"]
        signal_flag = stats["signal_flag"]

        add_event(state, "investigator", "tool_result", f"Disproportionality for {reaction}: PRR={prr}, ROR={ror}, Chi2={chi2}, SignalFlag={signal_flag}", {
            "tool": "compute_disproportionality",
            "metrics": stats
        })

        # Step 3: Check FDA label
        add_event(state, "investigator", "tool_call", f"Checking FDA approved label sections for {reaction}", {
            "tool": "check_reaction_in_label",
            "arguments": {"drug": drug, "reaction": reaction}
        })
        
        label_res = await openfda.check_reaction_in_label(drug=drug, reaction=reaction)
        is_in_label = label_res.get("is_in_label", False)
        section = label_res.get("section", "None")
        snippet = label_res.get("snippet", "")
        if label_res.get("source_url"):
            source_urls.append(label_res.get("source_url"))

        add_event(state, "investigator", "tool_result", f"Label check for {reaction}: InLabel={is_in_label} (Section: {section})", {
            "tool": "check_reaction_in_label",
            "is_in_label": is_in_label,
            "section": section,
            "snippet": snippet[:180] + ("..." if len(snippet) > 180 else "")
        })

        # Step 4: PubMed literature search ONLY if signal is flagged AND unlabeled
        pubmed_articles = []
        if signal_flag and not is_in_label:
            pubmed_query = f"{drug} {reaction} adverse event"
            add_event(state, "investigator", "tool_call", f"Signal flagged & unlabeled! Searching PubMed for scientific literature: '{pubmed_query}'", {
                "tool": "search_pubmed",
                "arguments": {"query": pubmed_query, "max_results": 3}
            })
            
            pubmed_res = await pubmed.search_pubmed(query=pubmed_query, max_results=3)
            pubmed_articles = pubmed_res.get("articles", [])
            if pubmed_res.get("search_url"):
                source_urls.append(pubmed_res.get("search_url"))

            add_event(state, "investigator", "tool_result", f"Found {len(pubmed_articles)} PubMed publications for unlabeled signal {reaction}", {
                "tool": "search_pubmed",
                "articles": [{"pmid": a["pmid"], "title": a["title"]} for a in pubmed_articles]
            })

        evidence_map[reaction] = ReactionEvidence(
            reaction=reaction,
            a=a,
            b=b,
            c=c,
            d=d,
            total_drug=a + b,
            total_reaction=a + c,
            prr=prr,
            prr_ci_lower=stats["prr_ci_lower"],
            prr_ci_upper=stats["prr_ci_upper"],
            ror=ror,
            ror_ci_lower=stats["ror_ci_lower"],
            ror_ci_upper=stats["ror_ci_upper"],
            chi_square=chi2,
            signal_flag=signal_flag,
            is_in_label=is_in_label,
            label_section=section,
            label_snippet=snippet,
            pubmed_articles=pubmed_articles,
            source_urls=list(set(source_urls))
        )

    add_event(state, "investigator", "node_end", f"Investigation completed for {len(evidence_map)} reactions.")
    return {
        "evidence": evidence_map,
        "events": state.events
    }

async def writer_node(state: AgentState) -> Dict[str, Any]:
    """Produce the safety synthesis and structured assessment."""
    add_event(state, "writer", "node_start", "Drafting structured pharmacovigilance safety assessment...")
    
    # Compile factual context from evidence
    lines = []
    signals_data = []
    citations_set = set()

    for rxn, ev in state.evidence.items():
        label_text = f"Labeled in FDA insert ({ev.label_section})" if ev.is_in_label else "UNLABELED in FDA insert"
        flag_text = "FLAGGED SIGNAL (Evans: PRR>=2, a>=3, Chi2>=4)" if ev.signal_flag else "No statistical signal"
        lines.append(
            f"Reaction: {rxn}\n"
            f"- FAERS Counts: a={ev.a}, b={ev.b}, c={ev.c}, d={ev.d}\n"
            f"- Statistics: PRR={ev.prr} (95% CI: {ev.prr_ci_lower}-{ev.prr_ci_upper}), "
            f"ROR={ev.ror} (95% CI: {ev.ror_ci_lower}-{ev.ror_ci_upper}), Chi-Square={ev.chi_square}\n"
            f"- Signal Status: {flag_text}\n"
            f"- FDA Label Status: {label_text}\n"
            f"- Label Snippet: {ev.label_snippet or 'None'}\n"
        )
        if ev.pubmed_articles:
            art_strs = [f"PMID {art['pmid']}: {art['title']} ({art['url']})" for art in ev.pubmed_articles]
            lines.append("- PubMed Evidence: " + "; ".join(art_strs))
            for art in ev.pubmed_articles:
                citations_set.add(art["url"])
        for u in ev.source_urls:
            citations_set.add(u)

        signals_data.append(SignalSummary(
            reaction=rxn,
            prr=ev.prr,
            ror=ev.ror,
            signal_flag=ev.signal_flag,
            is_in_label=ev.is_in_label,
            label_status=label_text,
            clinical_note=f"PRR {ev.prr}, ROR {ev.ror}. {label_text}."
        ))

    evidence_summary = "\n".join(lines)
    critic_notes = f"\nPrevious Critic Feedback: {state.critic_feedback}" if state.critic_feedback else ""

    prompt = f"""You are a junior drug safety scientist writing an executive pharmacovigilance assessment.
Drug: {state.normalized_drug}

GROUND TRUTH TOOL EVIDENCE (Never invent numbers or alter statistics):
{evidence_summary}
{critic_notes}

MANDATORY RULES:
1. Every statistical number (PRR, ROR, counts a, b, c, d, chi-square) in your text must match the ground truth numbers above.
2. Clearly distinguish between LABELED safety risks and UNLABELED prospective signals.
3. Every claim must cite the openFDA query, FDA label section, or PubMed PMID.
4. MANDATORY LIMITATIONS: You must explicitly state the core limitations of spontaneous adverse event reporting (FAERS does not establish causation, lack of denominator/incidence rates, reporting bias, duplicate reports).
5. Educational demonstration disclaimer must be included.

Draft an executive, structured summary.
"""
    llm = get_chat_model(temperature=0.0)
    try:
        response = await call_llm_with_resilience(
            llm=llm,
            messages=[
                SystemMessage(content="You are a meticulous pharmacovigilance scientist. Stick strictly to verified tool evidence and avoid fabricating any numbers."),
                HumanMessage(content=prompt)
            ]
        )
        draft_text = response.content.strip()
    except Exception as e:
        draft_text = f"Automated Safety Assessment for {state.normalized_drug}:\n\nEvidence Summary:\n{evidence_summary}\n\nLimitations: FAERS spontaneous reporting represents unverified reports, subject to bias and absence of incidence denominators."

    # Guarantee mandatory limitations block presence in draft
    mandatory_limitations_footer = (
        "\n\n### Limitations\n"
        "FAERS data reflects spontaneous voluntary reporting and cannot establish definitive medical causation or causality. "
        "The lack of denominator data precludes calculating true population incidence rates, and reports are subject to notoriety bias, underreporting, and duplicate submissions."
    )
    lower_draft = draft_text.lower()
    if not any(w in lower_draft for w in ["causation", "causality", "causal"]) or "spontaneous" not in lower_draft:
        draft_text = draft_text + mandatory_limitations_footer

    # Generate structured FinalAssessment
    structured = FinalAssessment(
        drug=state.normalized_drug,
        executive_summary=f"Safety review for {state.normalized_drug} assessing {len(state.evidence)} MedDRA adverse event terms.",
        signals=signals_data,
        detailed_findings=draft_text,
        clinical_recommendation="Periodic surveillance recommended; review flagged unlabeled events with clinical teams.",
        limitations="FAERS data represents spontaneous post-marketing reports and cannot establish definitive biological causation. Lacks patient incidence denominators; affected by underreporting, notoriety bias, and duplicate entries.",
        citations=list(citations_set)
    )

    add_event(state, "writer", "node_end", "Assessment draft compiled.", {
        "signals_count": len(signals_data),
        "citations_count": len(citations_set)
    })
    
    return {
        "draft": draft_text,
        "structured_assessment": structured,
        "events": state.events
    }

async def critic_node(state: AgentState) -> Dict[str, Any]:
    """Critic checks numeric fidelity against tool outputs, citation presence, and limitations."""
    add_event(state, "critic", "node_start", "Auditing safety assessment draft for statistical fidelity and compliance...")
    
    is_valid, issues = validate_assessment_guardrails(
        assessment_text=state.draft,
        evidence=state.evidence
    )

    loop_count = state.critic_loop_count + 1
    
    if is_valid:
        feedback = "Assessment verified: All numbers match verified tool evidence, citations present, mandatory limitations included."
        add_event(state, "critic", "critic_verdict", f"PASS: {feedback}", {
            "verdict": "PASS",
            "loop_count": loop_count
        })
        return {
            "critic_passes": True,
            "critic_feedback": feedback,
            "critic_loop_count": loop_count,
            "events": state.events
        }
    else:
        feedback = f"Quality audit failed ({len(issues)} issues): " + "; ".join(issues)
        add_event(state, "critic", "critic_verdict", f"RETRY: {feedback}", {
            "verdict": "FAIL",
            "issues": issues,
            "loop_count": loop_count
        })
        return {
            "critic_passes": False,
            "critic_feedback": feedback,
            "critic_loop_count": loop_count,
            "events": state.events
        }

def route_critic(state: AgentState) -> Literal["writer", "human_review"]:
    """Route after critic: if passed or exceeded 2 loops, proceed to human review; otherwise revise with writer."""
    if state.critic_passes or state.critic_loop_count >= 2:
        return "human_review"
    return "writer"

async def human_review_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph interrupt before finalizing if any signal is unlabeled or evidence is thin."""
    add_event(state, "human_review", "node_start", "Evaluating human review criteria...")
    
    has_unlabeled_signal = any(ev.signal_flag and not ev.is_in_label for ev in state.evidence.values())
    thin_evidence = any(ev.a < 10 for ev in state.evidence.values())
    
    needs_review = has_unlabeled_signal or thin_evidence

    if needs_review and state.review_status == "pending":
        reasons = []
        if has_unlabeled_signal:
            reasons.append("Unlabeled statistical safety signal detected")
        if thin_evidence:
            reasons.append("Low report count (<10 reports)")
        reason_str = " & ".join(reasons)
        
        state.needs_human_review = True
        state.human_review_reason = reason_str
        
        add_event(state, "human_review", "interrupt", f"Pausing for human review: {reason_str}", {
            "reason": reason_str,
            "unlabeled_signals": [ev.reaction for ev in state.evidence.values() if ev.signal_flag and not ev.is_in_label]
        })
        
        # LangGraph interrupt
        user_input = interrupt({
            "drug": state.normalized_drug,
            "reason": reason_str,
            "signals": [s.model_dump() for s in (state.structured_assessment.signals if state.structured_assessment else [])],
            "draft": state.draft
        })

        # When resumed with Command(resume=...):
        action = "approve"
        payload = {}
        if isinstance(user_input, dict):
            action = user_input.get("action", "approve")
            payload = user_input.get("payload", {})
        elif isinstance(user_input, str):
            action = user_input

        add_event(state, "human_review", "node_end", f"Human review resumed with decision: '{action}'", {
            "action": action
        })
        
        if action == "edit" and "edited_draft" in payload:
            return {
                "draft": payload["edited_draft"],
                "review_status": "edited",
                "needs_human_review": False,
                "events": state.events
            }
        elif action == "investigate_more":
            return {
                "review_status": "investigate_more",
                "needs_human_review": False,
                "events": state.events
            }
        else:
            return {
                "review_status": "approved",
                "needs_human_review": False,
                "events": state.events
            }

    state.review_status = "approved"
    state.needs_human_review = False
    add_event(state, "human_review", "node_end", "Human review gate cleared automatically (no unlabeled signals or thin evidence).")
    return {
        "review_status": "approved",
        "needs_human_review": False,
        "events": state.events
    }

def route_intake(state: AgentState) -> Literal["planner", END]:
    """If drug was not found or candidate reactions empty, terminate graph immediately."""
    if state.error or not state.candidate_reactions:
        return END
    return "planner"

def route_human_review(state: AgentState) -> Literal["investigator", END]:
    """If user requested more investigation, loop back to investigator; else terminate."""
    if state.review_status == "investigate_more":
        return "investigator"
    return END

def build_safety_agent_graph(checkpointer: Optional[Any] = None):
    """Build the LangGraph workflow."""
    builder = StateGraph(AgentState)
    
    builder.add_node("intake", intake_node)
    builder.add_node("planner", planner_node)
    builder.add_node("investigator", investigator_node)
    builder.add_node("writer", writer_node)
    builder.add_node("critic", critic_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", route_intake)
    builder.add_edge("planner", "investigator")
    builder.add_edge("investigator", "writer")
    builder.add_edge("writer", "critic")
    builder.add_conditional_edges("critic", route_critic)
    builder.add_conditional_edges("human_review", route_human_review)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)

