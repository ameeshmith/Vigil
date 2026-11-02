import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  Terminal, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  ExternalLink, 
  FileText, 
  Download, 
  ShieldCheck, 
  ChevronDown, 
  ChevronUp, 
  Send, 
  Sparkles,
  ArrowRight,
  RotateCw
} from 'lucide-react';

export default function Workbench({ externalDrug, onDrugProcessed }) {
  const getApiBase = () => {
    if (typeof window !== 'undefined' && window.location.port && window.location.port !== '8000') {
      return `http://${window.location.hostname}:8000`;
    }
    return '';
  };
  const API_BASE = getApiBase();

  const [drug, setDrug] = useState('');
  const [activeRunId, setActiveRunId] = useState(null);
  const [runStatus, setRunStatus] = useState('idle'); // idle | running | review | done | error
  const [statusMessage, setStatusMessage] = useState('READY FOR QUERY');
  const [activeNode, setActiveNode] = useState(null);
  const [traceLogs, setTraceLogs] = useState([]);
  const [evidenceMap, setEvidenceMap] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [fallbackDraft, setFallbackDraft] = useState('');
  const [collectedQueries, setCollectedQueries] = useState([]);
  const [showQueriesDrawer, setShowQueriesDrawer] = useState(false);
  const [reviewRequiredData, setReviewRequiredData] = useState(null);
  const [editNote, setEditNote] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [completeRunData, setCompleteRunData] = useState(null);

  const eventSourceRef = useRef(null);
  const traceEndRef = useRef(null);

  // Auto scroll trace to bottom
  useEffect(() => {
    if (traceEndRef.current) {
      traceEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [traceLogs]);

  // Handle external drug trigger from Hero or Case Studies
  useEffect(() => {
    if (externalDrug && externalDrug !== drug) {
      setDrug(externalDrug);
      startInvestigation(externalDrug);
      if (onDrugProcessed) onDrugProcessed();
    }
  }, [externalDrug]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const PIPELINE_NODES = [
    { key: 'intake', label: 'INTAKE' },
    { key: 'planner', label: 'PLANNER' },
    { key: 'investigator', label: 'INVESTIGATOR' },
    { key: 'writer', label: 'WRITER' },
    { key: 'critic', label: 'CRITIC' },
    { key: 'human_review', label: 'HUMAN REVIEW' }
  ];

  const startInvestigation = async (drugName) => {
    const targetDrug = (drugName || drug).trim();
    if (!targetDrug) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setRunStatus('running');
    setStatusMessage('ANALYZING FAERS ARCHIVE');
    setActiveNode('intake');
    setTraceLogs([]);
    setEvidenceMap(null);
    setAssessment(null);
    setFallbackDraft('');
    setCollectedQueries([]);
    setShowQueriesDrawer(false);
    setReviewRequiredData(null);
    setCompleteRunData(null);

    try {
      const resp = await fetch(`${API_BASE}/api/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drug: targetDrug })
      });

      if (!resp.ok) {
        throw new Error(`Failed to initiate run: ${resp.statusText}`);
      }

      const data = await resp.json();
      setActiveRunId(data.run_id);
      connectToSSE(data.run_id);
    } catch (err) {
      setRunStatus('error');
      setStatusMessage('ERROR');
      addTraceLog('error', 'API CONNECTION ERROR', `${err.message}. Ensure backend is running (python run.py) on port 8000.`);
    }
  };

  const addTraceLog = (type, label, message, args = null, sourceUrl = null) => {
    setTraceLogs(prev => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        type,
        label,
        message,
        args,
        sourceUrl,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };

  const connectToSSE = (runId) => {
    const es = new EventSource(`${API_BASE}/api/runs/${runId}/events`);
    eventSourceRef.current = es;

    es.addEventListener('node_start', (e) => {
      const data = JSON.parse(e.data);
      setActiveNode(data.node);
      setStatusMessage(`EXECUTING ${data.node.toUpperCase()}`);
      addTraceLog('node_start', data.node.toUpperCase(), data.message);
    });

    es.addEventListener('node_end', (e) => {
      const data = JSON.parse(e.data);
      addTraceLog('node_end', data.node.toUpperCase(), data.message);
    });

    es.addEventListener('tool_call', (e) => {
      const data = JSON.parse(e.data);
      addTraceLog('tool_call', data.data.tool || 'TOOL', data.message, data.data.arguments);
    });

    es.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data);
      const newUrls = [];
      if (data.data.source_url) newUrls.push(data.data.source_url);
      if (Array.isArray(data.data.source_urls)) newUrls.push(...data.data.source_urls);

      if (newUrls.length > 0) {
        setCollectedQueries(prev => Array.from(new Set([...prev, ...newUrls])));
      }

      addTraceLog('tool_result', data.data.tool || 'RESULT', data.message, null, data.data.source_url);
    });

    es.addEventListener('critic_verdict', (e) => {
      const data = JSON.parse(e.data);
      addTraceLog('critic_verdict', 'CRITIC AUDIT', data.message);
    });

    es.addEventListener('warning', (e) => {
      const data = JSON.parse(e.data);
      addTraceLog('warning', 'SYSTEM NOTICE', data.message);
    });

    es.addEventListener('interrupt', (e) => {
      const data = JSON.parse(e.data);
      setActiveNode('human_review');
      setRunStatus('review');
      setStatusMessage('HUMAN REVIEW REQUIRED');
      setReviewRequiredData(data.data);
      addTraceLog('warning', 'HITL GATE TRIGGERED', data.message);
    });

    es.addEventListener('final', (e) => {
      const data = JSON.parse(e.data);
      setRunStatus('done');
      setStatusMessage('INVESTIGATION COMPLETE');
      setActiveNode(null);
      setEvidenceMap(data.data.evidence || {});
      setAssessment(data.data.assessment || null);
      setFallbackDraft(data.data.draft || '');
      setCompleteRunData(data.data);
      addTraceLog('node_end', 'FINAL', 'Investigation completed and verified.');
      es.close();
    });

    es.addEventListener('error', (e) => {
      if (e.data) {
        try {
          const data = JSON.parse(e.data);
          setRunStatus('error');
          setStatusMessage('TERMINATED');
          addTraceLog('error', 'EXECUTION HALTED', data.message);
        } catch (_) {
          // ignore
        }
      }
    });
  };

  const handleReviewAction = async (action, customPayload = null) => {
    if (!activeRunId) return;
    setIsSubmittingReview(true);

    try {
      const resp = await fetch(`${API_BASE}/api/runs/${activeRunId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          payload: customPayload || (action === 'edit' ? editNote : null)
        })
      });

      if (!resp.ok) {
        throw new Error('Failed to submit review');
      }

      setRunStatus('running');
      setStatusMessage('RESUMING AGENT WITH REVIEW DIRECTIVE');
      setReviewRequiredData(null);
    } catch (err) {
      addTraceLog('error', 'REVIEW FAILED', err.message);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const downloadJson = () => {
    if (!completeRunData) return;
    const blob = new Blob([JSON.stringify(completeRunData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vigil-run-${activeRunId || 'data'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeIndex = PIPELINE_NODES.findIndex(n => n.key === activeNode);

  return (
    <section id="workbench" className="py-24 md:py-32 px-6 md:px-12 max-w-[1720px] mx-auto border-t border-[#121212]/15 dark:border-white/15">
      
      {/* Header Meta */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div>
          <div className="flex items-center gap-2 font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96] mb-2">
            <span className="w-2 h-2 rounded-full bg-[#FF3E14]" />
            <span>INTERACTIVE WORKBENCH</span>
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl lg:text-5xl tracking-tight text-[#121212] dark:text-[#F5F2EB]">
            Drug Safety Investigation<span className="text-[#FF3E14]">.</span>
          </h2>
        </div>

        {/* Live Engine Status Pill */}
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-[#121212]/5 dark:bg-white/5 border border-[#121212]/10 dark:border-white/10 font-mono-code text-xs">
          <span className={`w-2 h-2 rounded-full ${
            runStatus === 'running' ? 'bg-[#FF3E14] animate-ping' :
            runStatus === 'review' ? 'bg-amber-500 animate-pulse' :
            runStatus === 'done' ? 'bg-emerald-600' :
            runStatus === 'error' ? 'bg-rose-600' : 'bg-[#6E6C65]'
          }`} />
          <span className="text-[#121212] dark:text-[#F5F2EB] font-medium tracking-wide">{statusMessage}</span>
        </div>
      </div>

      {/* Drug Search Command Bar */}
      <div className="mb-10 bg-white dark:bg-[#151518] rounded-2xl p-4 md:p-6 shadow-xs border border-[#121212]/10 dark:border-white/10">
        <form 
          onSubmit={(e) => { e.preventDefault(); startInvestigation(); }}
          className="flex flex-col md:flex-row items-center gap-3"
        >
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6E6C65] dark:text-[#9E9C96]" />
            <input 
              type="text"
              value={drug}
              onChange={(e) => setDrug(e.target.value)}
              placeholder="Enter drug name (e.g. Atorvastatin, Ozempic, Naxdom 250)..."
              className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-[#F5F2EB]/50 dark:bg-[#1D1D22] border border-[#121212]/10 dark:border-white/15 text-[#121212] dark:text-[#F5F2EB] font-sans text-base focus:outline-none focus:border-[#121212] dark:focus:border-white/30 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={runStatus === 'running' || !drug.trim()}
            className="w-full md:w-auto px-7 py-3.5 rounded-xl bg-[#121212] dark:bg-[#F5F2EB] text-[#F5F2EB] dark:text-[#0C0C0D] font-mono-code text-xs uppercase tracking-wider font-semibold hover:bg-[#FF3E14] dark:hover:bg-[#FF3E14] dark:hover:text-white transition-colors duration-300 disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2 cursor-pointer"
          >
            {runStatus === 'running' ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin text-[#F5F2EB] dark:text-[#0C0C0D]" />
                <span>INVESTIGATING...</span>
              </>
            ) : (
              <>
                <span>ANALYZE DRUG</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        {/* Pre-fill Chips */}
        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[#121212]/5 dark:border-white/5 font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96]">
          <span>EXAMPLES:</span>
          {[
            { label: 'Atorvastatin', drug: 'Atorvastatin' },
            { label: 'Ozempic', drug: 'Ozempic' },
            { label: 'Simvastatin', drug: 'Simvastatin' },
            { label: 'Naxdom 250', drug: 'Naxdom 250' }
          ].map(chip => (
            <button
              key={chip.label}
              type="button"
              onClick={() => {
                setDrug(chip.drug);
                startInvestigation(chip.drug);
              }}
              className="px-2.5 py-1 rounded bg-[#F5F2EB] dark:bg-[#1D1D22] hover:bg-[#121212] dark:hover:bg-white hover:text-[#F5F2EB] dark:hover:text-[#0C0C0D] border border-[#121212]/10 dark:border-white/10 transition-colors text-xs font-mono text-[#121212] dark:text-[#F5F2EB] cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* LangGraph Agent Pipeline Progress Bar */}
      <div className="mb-10 bg-white dark:bg-[#151518] rounded-xl p-4 md:p-5 border border-[#121212]/10 dark:border-white/10">
        <div className="flex items-center justify-between mb-3 font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96]">
          <span className="font-semibold text-[#121212] dark:text-[#F5F2EB]">AGENT PIPELINE</span>
          <span>LANGGRAPH STATEGRAPH</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {PIPELINE_NODES.map((node, idx) => {
            const isCurrent = node.key === activeNode;
            const isCompleted = activeIndex !== -1 && idx < activeIndex;
            return (
              <div 
                key={node.key}
                className={`p-3 rounded-lg border text-center transition-all ${
                  isCurrent 
                    ? 'bg-[#FF3E14] text-white border-[#FF3E14] shadow-md font-bold' 
                    : isCompleted 
                    ? 'bg-[#121212] dark:bg-white/10 text-[#F5F2EB] border-[#121212] dark:border-white/20'
                    : 'bg-[#F5F2EB]/50 dark:bg-[#1D1D22]/60 text-[#6E6C65] dark:text-[#9E9C96] border-[#121212]/10 dark:border-white/10'
                }`}
              >
                <div className="font-mono-code text-[10px] opacity-75">STEP 0{idx + 1}</div>
                <div className="font-mono-code text-xs uppercase tracking-wider font-bold mt-1 flex items-center justify-center gap-1.5">
                  {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                  {isCurrent && <Activity className="w-3.5 h-3.5 animate-spin" />}
                  <span>{node.label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two-Column Studio Layout: Trace Log & Disproportionality Signals Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
        
        {/* Column 1: Live Agent Trace (5 cols) */}
        <div className="lg:col-span-5 bg-[#121212] dark:bg-[#101012] border border-white/5 rounded-2xl p-6 text-[#F5F2EB] flex flex-col h-[560px] shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#FF3E14]" />
              <span className="font-mono-code text-xs uppercase tracking-wider font-semibold">LIVE REASONING TRACE</span>
            </div>
            <span className="font-mono-code text-[10px] text-white/50">{traceLogs.length} EVENTS</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-2 custom-scrollbar">
            {traceLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-white/40 text-center px-4">
                <Sparkles className="w-6 h-6 mb-2 text-[#FF3E14]" />
                <p>Waiting for drug intake initiation.</p>
                <p className="text-[11px] mt-1">Queries will stream openFDA FAERS, package inserts, and critic verdicts here in real-time.</p>
              </div>
            ) : (
              traceLogs.map((log) => (
                <div key={log.id} className="p-2.5 rounded bg-white/5 border border-white/5 text-[11px] leading-relaxed">
                  <div className="flex items-center justify-between mb-1 opacity-60 text-[10px]">
                    <span className="text-[#FF3E14] font-bold">[{log.label}]</span>
                    <span>{log.timestamp}</span>
                  </div>
                  <div className="text-white/90 break-words">{log.message}</div>
                  {log.args && (
                    <pre className="mt-1 p-1.5 rounded bg-black/40 text-emerald-300 text-[10px] overflow-x-auto">
                      {JSON.stringify(log.args, null, 2)}
                    </pre>
                  )}
                  {log.sourceUrl && (
                    <a 
                      href={log.sourceUrl} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="inline-flex items-center gap-1 mt-1 text-[#FF3E14] hover:underline text-[10px]"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      <span>Verify source query</span>
                    </a>
                  )}
                </div>
              ))
            )}
            <div ref={traceEndRef} />
          </div>
        </div>

        {/* Column 2: Evans Disproportionality Signals Table (7 cols) */}
        <div className="lg:col-span-7 bg-white dark:bg-[#151518] rounded-2xl p-6 border border-[#121212]/10 dark:border-white/10 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-[#121212]/10 dark:border-white/10 mb-4">
              <div>
                <h3 className="font-display font-bold text-xl text-[#121212] dark:text-[#F5F2EB]">
                  Statistical Disproportionality Metrics
                </h3>
                <p className="font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96] mt-0.5">
                  Evans Criteria: PRR ≥ 2.0, N ≥ 3, Yates' χ² ≥ 4.0
                </p>
              </div>
              {collectedQueries.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowQueriesDrawer(!showQueriesDrawer)}
                  className="flex items-center gap-1.5 font-mono-code text-xs text-[#FF3E14] hover:underline cursor-pointer"
                >
                  <span>{collectedQueries.length} Raw Query URLs</span>
                  {showQueriesDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>

            {/* Queries Drawer */}
            {showQueriesDrawer && (
              <div className="mb-4 p-3 rounded-lg bg-[#F5F2EB] dark:bg-[#1D1D22] border border-[#121212]/10 dark:border-white/10 text-xs font-mono max-h-36 overflow-y-auto space-y-1">
                {collectedQueries.map((url, i) => (
                  <div key={i} className="truncate">
                    <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#121212] dark:text-[#F5F2EB] hover:text-[#FF3E14] hover:underline flex items-center gap-1">
                      <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{url}</span>
                    </a>
                  </div>
                ))}
              </div>
            )}

            {/* Signals Table */}
            <div className="overflow-x-auto">
              {!evidenceMap || Object.keys(evidenceMap).length === 0 ? (
                <div className="py-24 text-center text-[#6E6C65] dark:text-[#9E9C96] font-mono-code text-xs">
                  {runStatus === 'running' 
                    ? 'Computing 2×2 contingency counts and Evans metrics...' 
                    : 'No statistical signals populated yet. Run an investigation above.'}
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#121212]/10 dark:border-white/10 font-mono-code text-[11px] text-[#6E6C65] dark:text-[#9E9C96] uppercase tracking-wider">
                      <th className="py-2.5 pr-3">MedDRA Reaction</th>
                      <th className="py-2.5 px-2">Cases (a)</th>
                      <th className="py-2.5 px-2">PRR</th>
                      <th className="py-2.5 px-2">ROR (95% CI)</th>
                      <th className="py-2.5 px-2">Chi²</th>
                      <th className="py-2.5 px-2">Signal Status</th>
                      <th className="py-2.5 pl-2">FDA Label Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#121212]/5 dark:divide-white/5 font-mono text-xs">
                    {Object.entries(evidenceMap).map(([rxn, ev]) => {
                      const isFlagged = ev.signal_flag;
                      const isUnlabeled = !ev.is_in_label;
                      return (
                        <tr key={rxn} className="hover:bg-[#F5F2EB]/50 dark:hover:bg-white/5 transition-colors">
                          <td className="py-3 pr-3 font-semibold text-[#121212] dark:text-[#F5F2EB] font-sans text-sm">{rxn}</td>
                          <td className="py-3 px-2 text-[#121212] dark:text-[#F5F2EB] font-mono">{ev.a}</td>
                          <td className="py-3 px-2 font-bold font-mono text-[#121212] dark:text-[#F5F2EB]">{ev.prr}</td>
                          <td className="py-3 px-2 font-mono text-[#6E6C65] dark:text-[#9E9C96]">
                            {ev.ror} <span className="text-[10px] text-[#6E6C65]/70 dark:text-white/40">[{ev.ror_ci_lower}–{ev.ror_ci_upper}]</span>
                          </td>
                          <td className="py-3 px-2 font-mono text-[#121212] dark:text-[#F5F2EB]">{ev.chi_square}</td>
                          <td className="py-3 px-2">
                            {isFlagged && isUnlabeled ? (
                              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#FF3E14] text-white">
                                UNLABELED SIGNAL
                              </span>
                            ) : isFlagged && !isUnlabeled ? (
                              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#121212] dark:bg-white/20 text-[#F5F2EB]">
                                LABELED SIGNAL
                              </span>
                            ) : (
                              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-gray-200 dark:bg-white/10 text-[#6E6C65] dark:text-[#9E9C96]">
                                NORMAL
                              </span>
                            )}
                          </td>
                          <td className="py-3 pl-2 text-[11px]">
                            {ev.is_in_label ? (
                              <span className="text-emerald-700 dark:text-emerald-400 font-semibold font-sans">
                                Labeled ({ev.label_section || 'Adverse Reactions'})
                              </span>
                            ) : (
                              <span className="text-[#FF3E14] font-semibold font-sans">
                                Absent from Label
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Human Review Gate Card (Conditionally shown if review required or completed) */}
      <AnimatePresence>
        {runStatus === 'review' && reviewRequiredData && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-12 rounded-2xl p-6 md:p-8 bg-amber-500/10 border-2 border-amber-500/30"
          >
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-amber-600" />
              <h3 className="font-display font-bold text-2xl text-[#121212] dark:text-[#F5F2EB]">
                Human-in-the-Loop Gate: Safety Scientist Review Required
              </h3>
            </div>
            
            <p className="font-sans text-base text-[#121212]/80 dark:text-white/80 mb-6 leading-relaxed">
              LangGraph has paused execution checkpointed via MemorySaver. One or more disproportionality signals are unlisted in current FDA approved prescribing information, or clinical reporting density requires safety review.
            </p>

            <div className="mb-6">
              <label className="block font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96] mb-2 font-semibold">
                Clinical Modification Directive / Directive Notes:
              </label>
              <textarea 
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                placeholder="Optional: Instruct the agent to adjust clinical interpretation, focus on specific literature, or append caveats..."
                className="w-full p-4 rounded-xl bg-white dark:bg-[#1D1D22] border border-[#121212]/15 dark:border-white/15 text-[#121212] dark:text-[#F5F2EB] text-sm font-sans focus:outline-none focus:border-[#121212] dark:focus:border-white/30"
                rows={3}
              />
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={() => handleReviewAction('approve')}
                disabled={isSubmittingReview}
                className="px-6 py-3 rounded-xl bg-[#121212] dark:bg-[#F5F2EB] text-[#F5F2EB] dark:text-[#0C0C0D] font-mono-code text-xs uppercase tracking-wider font-semibold hover:bg-emerald-600 dark:hover:bg-emerald-500 dark:hover:text-white transition-colors cursor-pointer"
              >
                Approve & Finalize Assessment
              </button>

              <button
                type="button"
                onClick={() => handleReviewAction('edit')}
                disabled={isSubmittingReview || !editNote.trim()}
                className="px-6 py-3 rounded-xl bg-white dark:bg-transparent text-[#121212] dark:text-[#F5F2EB] border border-[#121212]/20 dark:border-white/20 font-mono-code text-xs uppercase tracking-wider font-semibold hover:bg-[#121212] hover:text-white dark:hover:bg-white/10 transition-colors cursor-pointer"
              >
                Apply Edit Directive
              </button>

              <button
                type="button"
                onClick={() => handleReviewAction('investigate_more')}
                disabled={isSubmittingReview}
                className="px-6 py-3 rounded-xl bg-[#FF3E14] text-white font-mono-code text-xs uppercase tracking-wider font-semibold hover:bg-[#d63410] transition-colors cursor-pointer"
              >
                Request Deeper Investigation
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Safety Assessment & Synthesis Section */}
      <div className="bg-white dark:bg-[#151518] rounded-2xl p-8 md:p-12 border border-[#121212]/10 dark:border-white/10 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#121212]/10 dark:border-white/10 mb-8">
          <div>
            <div className="font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96] uppercase tracking-wider">SYNTHESIS & AUDIT</div>
            <h3 className="font-display font-bold text-3xl text-[#121212] dark:text-[#F5F2EB]">
              Verified Safety Assessment
            </h3>
          </div>
          {completeRunData && (
            <button
              type="button"
              onClick={downloadJson}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#121212]/15 dark:border-white/15 text-[#121212] dark:text-[#F5F2EB] font-mono-code text-xs font-semibold hover:bg-[#121212] dark:hover:bg-white hover:text-white dark:hover:text-black transition-colors cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>EXPORT COMPLETE AUDIT JSON</span>
            </button>
          )}
        </div>

        {!assessment && !fallbackDraft ? (
          <div className="py-16 text-center text-[#6E6C65] dark:text-[#9E9C96] font-mono-code text-xs">
            Awaiting assessment compilation from the Writer and Critic nodes...
          </div>
        ) : (
          <div className="space-y-8 font-sans">
            
            {/* Detailed Findings */}
            <div>
              <h4 className="font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96] font-bold mb-3">
                CLINICAL EVIDENCE FINDINGS:
              </h4>
              <div className="p-6 rounded-xl bg-[#F5F2EB]/50 dark:bg-[#1D1D22]/60 border border-[#121212]/5 dark:border-white/10 text-[#121212] dark:text-[#F5F2EB] leading-relaxed text-base whitespace-pre-line">
                {assessment ? assessment.detailed_findings : fallbackDraft}
              </div>
            </div>

            {/* Citations Pill List */}
            {assessment && assessment.citations && assessment.citations.length > 0 && (
              <div>
                <h4 className="font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96] font-bold mb-3">
                  VERIFIED CITATIONS & SOURCES:
                </h4>
                <div className="flex flex-wrap gap-2">
                  {assessment.citations.map((cite, idx) => (
                    <span 
                      key={idx} 
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#121212]/5 dark:bg-white/10 border border-[#121212]/10 dark:border-white/15 font-mono text-xs text-[#121212] dark:text-[#F5F2EB]"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-[#FF3E14]" />
                      <span>{cite}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Mandatory Limitations Block */}
            <div className="p-6 rounded-xl bg-[#121212] dark:bg-[#101012] text-[#F5F2EB] border border-[#121212] dark:border-white/10">
              <div className="flex items-center gap-2 text-[#FF3E14] font-mono-code text-xs font-bold uppercase tracking-wider mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span>MANDATORY PHARMACOVIGILANCE LIMITATIONS:</span>
              </div>
              <p className="text-white/80 text-sm leading-relaxed font-sans">
                {assessment ? assessment.limitations : "FAERS reports represent spontaneous unverified post-marketing submissions and cannot demonstrate biological causality or true incidence rates due to underreporting, notoriety bias, and absence of total exposure denominators."}
              </p>
            </div>
          </div>
        )}
      </div>

    </section>
  );
}

