from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ReactionEvidence(BaseModel):
    reaction: str
    a: int = 0
    b: int = 0
    c: int = 0
    d: int = 0
    total_drug: int = 0
    total_reaction: int = 0
    prr: float = 0.0
    prr_ci_lower: float = 0.0
    prr_ci_upper: float = 0.0
    ror: float = 0.0
    ror_ci_lower: float = 0.0
    ror_ci_upper: float = 0.0
    chi_square: float = 0.0
    signal_flag: bool = False
    is_in_label: bool = False
    label_section: Optional[str] = "None"
    label_snippet: Optional[str] = None
    pubmed_articles: List[Dict[str, Any]] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)

class SignalSummary(BaseModel):
    reaction: str
    prr: float
    ror: float
    signal_flag: bool
    is_in_label: bool
    label_status: str
    clinical_note: str

class FinalAssessment(BaseModel):
    drug: str
    executive_summary: str
    signals: List[SignalSummary] = Field(default_factory=list)
    detailed_findings: str
    clinical_recommendation: str
    limitations: str
    disclaimer: str = (
        "Educational and pharmacovigilance research demonstration only. "
        "Not intended for direct clinical care or individual medical decision making."
    )
    citations: List[str] = Field(default_factory=list)

class TraceEvent(BaseModel):
    node: str
    event_type: str  # "node_start", "node_end", "tool_call", "tool_result", "critic_verdict", "token", "interrupt", "error"
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0

class AgentState(BaseModel):
    drug: str
    normalized_drug: str = ""
    candidate_reactions: List[Dict[str, Any]] = Field(default_factory=list)
    selected_reactions: List[str] = Field(default_factory=list)
    evidence: Dict[str, ReactionEvidence] = Field(default_factory=dict)
    draft: str = ""
    structured_assessment: Optional[FinalAssessment] = None
    critic_feedback: str = ""
    critic_passes: bool = False
    critic_loop_count: int = 0
    review_status: str = "pending"  # "pending", "approved", "edited", "investigate_more"
    needs_human_review: bool = False
    human_review_reason: str = ""
    human_review_input: Optional[Dict[str, Any]] = None
    run_id: str = ""
    events: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None

