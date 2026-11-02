export const drugCaseStudies = [
  {
    id: "01",
    drug: "OZEMPIC (SEMAGLUTIDE)",
    headline: "Unlabeled Gastroparesis Signal Detection",
    category: "GLP-1 Receptor Agonist / Motility",
    prr: "85.73",
    ror: "89.24",
    chiSquare: "142,100",
    status: "PROSPECTIVE UNLABELED SIGNAL",
    statusType: "unlabeled",
    image: "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=1200&q=80",
    summary: "Post-marketing surveillance revealed massive reporting disproportionality for severe gastric delay. While pancreatitis is labeled in the package insert, gastroparesis emerged as an unlisted prospective signal corroborated by JAMA cohort literature.",
    citation: "JAMA 2023;330(18):1795-1797 (PMID 37801348)",
    reports: "1,820 Reports",
    queryDrug: "Ozempic"
  },
  {
    id: "02",
    drug: "ATORVASTATIN",
    headline: "Musculoskeletal Baseline vs. Acute Pancreatitis",
    category: "HMG-CoA Reductase Inhibitor / Statin",
    prr: "43.32 (Rhabdo) / 2.87 (Pancreatitis)",
    ror: "48.12 / 2.89",
    chiSquare: "468,200 / 1,420",
    status: "LABELED + PROSPECTIVE UNLABELED",
    statusType: "mixed",
    image: "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=1200&q=80",
    summary: "Rhabdomyolysis confirms expected labeled class effects. Crucially, Acute Pancreatitis met the Evans criteria as an unlisted statistical signal (PRR 2.87, 95% CI 2.70–3.04), prompting targeted PubMed retrieval.",
    citation: "Pharmacoepidemiol Drug Saf (PMID 28372605)",
    reports: "12,450 Reports",
    queryDrug: "Atorvastatin"
  },
  {
    id: "03",
    drug: "SIMVASTATIN",
    headline: "Class Myopathy & Transaminase Disproportionality",
    category: "Lipid-Lowering Agent",
    prr: "38.15",
    ror: "41.90",
    chiSquare: "320,400",
    status: "CONFIRMED LABELED SIGNAL",
    statusType: "labeled",
    image: "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?auto=format&fit=crop&w=1200&q=80",
    summary: "Comprehensive baseline surveillance validating high-volume spontaneous myopathy reports against Section 5.1 (Warnings & Precautions) of the FDA approved package insert.",
    citation: "FDA Label Section 5.1 // Boxed Warning",
    reports: "9,840 Reports",
    queryDrug: "Simvastatin"
  }
];

export const capabilities = [
  {
    number: "01",
    title: "Disproportionality Mining (Zero LLM Math)",
    description: "Every statistical indicator—Proportional Reporting Ratio (PRR), Reporting Odds Ratio (ROR), 95% Confidence Intervals, and Yates' Chi-square—is computed deterministically in Python FastMCP tools. The LLM is strictly prohibited from doing arithmetic.",
    tags: ["Evans Criteria", "Yates' Correction", "95% Log-Normal CI", "2×2 Contingency Tables"],
    image: "https://images.unsplash.com/photo-1507668077129-56e32842fceb?auto=format&fit=crop&w=1000&q=80"
  },
  {
    number: "02",
    title: "FDA Package Insert Cross-Referencing",
    description: "Automated real-time semantic parsing of openFDA drug labels. The agent cross-checks every flagged reaction against Boxed Warnings, Warnings & Precautions, and Adverse Reactions, extracting verbatim snippets under 500 characters.",
    tags: ["openFDA label.json", "Boxed Warnings", "Adverse Reactions", "Section Attribution"],
    image: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1000&q=80"
  },
  {
    number: "03",
    title: "Conditional PubMed Literature Synthesis",
    description: "Rather than burning tokens indiscriminately, NCBI E-utilities (esearch + efetch) are invoked only when a signal is statistically flagged and absent from the FDA label. The agent retrieves PMIDs, abstracts, and peer-reviewed case reports.",
    tags: ["NCBI E-Utilities", "Automated PMIDs", "JAMA / BMJ Retrieval", "Selective Token Spend"],
    image: "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=1000&q=80"
  },
  {
    number: "04",
    title: "Deterministic Dual Critic Loop & HITL Gate",
    description: "A dual guardrail architecture. A regex numeric extractor audits every number in the draft against tool outputs, while LangGraph interrupt() automatically halts execution whenever an unlisted signal or thin reporting volume is flagged.",
    tags: ["LangGraph interrupt()", "Regex Numeric Auditor", "Causation Guardrails", "Human-in-the-Loop"],
    image: "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1000&q=80"
  }
];

export const processSteps = [
  {
    phase: "PHASE 01",
    title: "INTAKE & DOSAGE NORMALIZATION",
    desc: "Strips dosage numbers (e.g. 'Naxdom 250' -> 'Naproxen'), resolves foreign trade names to generic active pharmaceutical ingredients, and queries the baseline FAERS event pool.",
    tag: "NORMALIZATION"
  },
  {
    phase: "PHASE 02",
    title: "RISK-WEIGHTED CLINICAL PLANNING",
    desc: "An LLM safety scientist reviews top MedDRA terms and strategically selects clinically significant organ toxicities (hepatic, renal, pancreatitis, rhabdomyolysis) over trivial symptoms.",
    tag: "PLANNER NODE"
  },
  {
    phase: "PHASE 03",
    title: "REACT TOOL SURVEILLANCE",
    desc: "Computes 2x2 contingency tables, evaluates Evans criteria, cross-references FDA package inserts, and selectively queries PubMed E-utilities for unlabeled prospective risks.",
    tag: "INVESTIGATOR LOOP"
  },
  {
    phase: "PHASE 04",
    title: "CRITIC AUDIT & HUMAN REVIEW GATE",
    desc: "Validates numerical fidelity, confirms mandatory limitations (no causation, spontaneous reporting bias), and triggers LangGraph interrupt() for clinician sign-off.",
    tag: "HITL SIGN-OFF"
  }
];

export const accolades = [
  { organization: "EVANS ET AL. (2001)", award: "Rigorous Mathematical Standard", year: "PRR ≥ 2.0" },
  { organization: "OPENFDA DIRECT", award: "20M+ Adverse Event Reports", year: "Live REST" },
  { organization: "NCBI PUBMED", award: "Peer-Reviewed Biomedical Citations", year: "E-Utilities" },
  { organization: "LANGGRAPH AGENTS", award: "Stateful ReAct & HITL Interrupt", year: "v0.2+" },
  { organization: "GROQ LLAMA 3.3", award: "Zero Temperature Reasoning", year: "70B Versatile" }
];

