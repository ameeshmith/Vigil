/**
 * Vigil AI Frontend
 * Full-page snap-scroll navigation, SSE streaming, and interactive pharmacovigilance review
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const snapContainer = document.getElementById("snapContainer");
  const sections = Array.from(document.querySelectorAll(".snap-section"));
  const navDots = Array.from(document.querySelectorAll(".dot-btn"));
  const headerStatusDot = document.getElementById("headerStatusDot");
  const headerStatusText = document.getElementById("headerStatusText");

  const drugForm = document.getElementById("drugForm");
  const drugInput = document.getElementById("drugInput");
  const runBtn = document.getElementById("runBtn");
  const exampleChips = document.querySelectorAll(".chip-btn");

  const pipelineBar = document.getElementById("pipelineBar");
  const traceLog = document.getElementById("traceLog");
  const signalsTableContainer = document.getElementById("signalsTableContainer");
  const toggleQueriesBtn = document.getElementById("toggleQueriesBtn");
  const queriesDrawer = document.getElementById("queriesDrawer");
  const assessmentContainer = document.getElementById("assessmentContainer");
  const reviewCard = document.getElementById("reviewCard");

  let currentRunId = null;
  let activeEventSource = null;
  let collectedQueries = new Set();
  let currentRunData = null;

  // -------------------------------------------------------------
  // 1. Full-Page Snap Scroll & Navigation
  // -------------------------------------------------------------
  function scrollToSection(targetId) {
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  }

  navDots.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      scrollToSection(targetId);
    });
  });

  // IntersectionObserver for active section
  const observerOptions = {
    root: snapContainer,
    threshold: 0.55
  };

  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const secId = entry.target.id;
        navDots.forEach(btn => {
          if (btn.getAttribute("data-target") === secId) {
            btn.classList.add("active");
          } else {
            btn.classList.remove("active");
          }
        });
      }
    });
  }, observerOptions);

  sections.forEach(sec => sectionObserver.observe(sec));

  // Keyboard navigation (1-6, arrows, PageUp/Down)
  window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;

    const currentIndex = sections.findIndex(sec => {
      const rect = sec.getBoundingClientRect();
      return rect.top >= -100 && rect.top <= window.innerHeight / 2;
    });

    if (e.key >= "1" && e.key <= "6") {
      const idx = parseInt(e.key, 10) - 1;
      if (sections[idx]) {
        e.preventDefault();
        scrollToSection(sections[idx].id);
      }
    } else if (e.key === "ArrowDown" || e.key === "PageDown") {
      if (currentIndex < sections.length - 1) {
        e.preventDefault();
        scrollToSection(sections[currentIndex + 1].id);
      }
    } else if (e.key === "ArrowUp" || e.key === "PageUp") {
      if (currentIndex > 0) {
        e.preventDefault();
        scrollToSection(sections[currentIndex - 1].id);
      }
    }
  });

  // Example chips
  exampleChips.forEach(chip => {
    chip.addEventListener("click", () => {
      drugInput.value = chip.getAttribute("data-drug");
      startInvestigation(chip.getAttribute("data-drug"));
    });
  });

  // Form submit
  drugForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const drug = drugInput.value.trim();
    if (drug) {
      startInvestigation(drug);
    }
  });

  // -------------------------------------------------------------
  // 2. Dispatch Run & SSE Stream
  // -------------------------------------------------------------
  async function startInvestigation(drug) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    setSystemStatus("running", "ANALYZING");
    resetUIForNewRun();
    scrollToSection("sec-trace");

    try {
      const resp = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drug })
      });

      if (!resp.ok) {
        throw new Error(`Failed to initiate run: ${resp.statusText}`);
      }

      const data = await resp.json();
      currentRunId = data.run_id;
      connectToSSE(currentRunId);
    } catch (err) {
      setSystemStatus("idle", "ERROR");
      appendTraceLog("error", "API Error", err.message);
    }
  }

  function resetUIForNewRun() {
    traceLog.innerHTML = "";
    signalsTableContainer.innerHTML = `<div class="quiet-placeholder">Investigation in progress. Awaiting statistical evidence...</div>`;
    assessmentContainer.innerHTML = `<div class="quiet-placeholder">Awaiting synthesis completion...</div>`;
    reviewCard.innerHTML = `<div class="quiet-placeholder">Awaiting investigation results for human review evaluation...</div>`;
    collectedQueries.clear();
    toggleQueriesBtn.style.display = "none";
    queriesDrawer.style.display = "none";
    queriesDrawer.innerHTML = "";

    document.querySelectorAll(".pipeline-step").forEach(step => {
      step.classList.remove("active", "done");
    });
  }

  function setSystemStatus(stateClass, text) {
    headerStatusDot.className = `status-dot ${stateClass}`;
    headerStatusText.textContent = text;
  }

  function updatePipeline(activeNode) {
    const nodes = ["intake", "planner", "investigator", "writer", "critic", "human_review"];
    const activeIdx = nodes.indexOf(activeNode);

    nodes.forEach((node, idx) => {
      const el = document.querySelector(`.pipeline-step[data-node="${node}"]`);
      if (!el) return;
      if (idx < activeIdx) {
        el.classList.add("done");
        el.classList.remove("active");
      } else if (idx === activeIdx) {
        el.classList.add("active");
        el.classList.remove("done");
      } else {
        el.classList.remove("active", "done");
      }
    });
  }

  // -------------------------------------------------------------
  // 3. SSE Event Processing
  // -------------------------------------------------------------
  function connectToSSE(runId) {
    activeEventSource = new EventSource(`/api/runs/${runId}/events`);

    activeEventSource.addEventListener("node_start", (e) => {
      const data = JSON.parse(e.data);
      updatePipeline(data.node);
      appendTraceLog("node_start", data.node.toUpperCase(), data.message);
    });

    activeEventSource.addEventListener("node_end", (e) => {
      const data = JSON.parse(e.data);
      appendTraceLog("node_end", data.node.toUpperCase(), data.message);
    });

    activeEventSource.addEventListener("tool_call", (e) => {
      const data = JSON.parse(e.data);
      appendTraceLog("tool_call", data.data.tool || "TOOL", data.message, data.data.arguments);
    });

    activeEventSource.addEventListener("tool_result", (e) => {
      const data = JSON.parse(e.data);
      if (data.data.source_url) {
        collectedQueries.add(data.data.source_url);
      }
      if (Array.isArray(data.data.source_urls)) {
        data.data.source_urls.forEach(u => collectedQueries.add(u));
      }
      appendTraceLog("tool_result", data.data.tool || "RESULT", data.message, null, data.data.source_url);
    });

    activeEventSource.addEventListener("critic_verdict", (e) => {
      const data = JSON.parse(e.data);
      appendTraceLog("critic_verdict", "CRITIC AUDIT", data.message);
    });

    activeEventSource.addEventListener("warning", (e) => {
      const data = JSON.parse(e.data);
      appendTraceLog("warning", "SYSTEM NOTICE", data.message);
    });

    activeEventSource.addEventListener("interrupt", (e) => {
      const data = JSON.parse(e.data);
      updatePipeline("human_review");
      setSystemStatus("review", "NEEDS REVIEW");
      appendTraceLog("warning", "HITL GATE", data.message);
      renderHumanReviewRequired(data.data);
      scrollToSection("sec-review");
    });

    activeEventSource.addEventListener("final", (e) => {
      const data = JSON.parse(e.data);
      setSystemStatus("done", "COMPLETED");
      document.querySelectorAll(".pipeline-step").forEach(s => {
        s.classList.remove("active");
        s.classList.add("done");
      });
      currentRunData = data.data;
      renderSignalsTable(data.data.evidence);
      renderAssessment(data.data.assessment, data.data.draft);
      renderCompletedReviewState();
    });

    activeEventSource.addEventListener("error", (e) => {
      // Stream error or failure event
      if (e.data) {
        const data = JSON.parse(e.data);
        setSystemStatus("idle", "ERROR");
        appendTraceLog("error", "SYSTEM NOTICE", data.message || "Execution terminated.");
        showDrugNotFoundError(data.message || "Drug not found in openFDA FAERS.");
      }
    });
  }

  function showDrugNotFoundError(msg) {
    const errorHtml = `
      <div style="padding: 2.5rem; background: rgba(239, 68, 68, 0.08); border: 1px solid var(--accent-signal); border-radius: 4px; text-align: center;">
        <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-signal); text-transform: uppercase; margin-bottom: 0.5rem;">[ Record Not Found in FAERS ]</div>
        <div style="font-size: 1.15rem; font-weight: 600; margin-bottom: 0.8rem; color: #fff;">${escapeHtml(msg)}</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; max-width: 620px; margin: 0 auto 1.2rem auto; line-height: 1.5;">
          openFDA FAERS primarily records FDA-approved generic substances (e.g. <em>Naproxen</em>, <em>Atorvastatin</em>, <em>Semaglutide</em>) and US brand names.
          If searching an international product or fixed-dose combination, search directly for the active generic chemical ingredient.
        </p>
      </div>
    `;
    signalsTableContainer.innerHTML = errorHtml;
    assessmentContainer.innerHTML = errorHtml;
    reviewCard.innerHTML = errorHtml;
  }

  function appendTraceLog(type, label, message, args = null, sourceUrl = null) {
    const entry = document.createElement("div");
    entry.className = `trace-entry ${type}`;

    let metaHtml = `<span class="trace-meta"><span>${label}</span>`;
    if (sourceUrl) {
      metaHtml += `<a href="${sourceUrl}" target="_blank" rel="noopener" class="trace-source-link">[source url]</a>`;
    }
    metaHtml += `</span>`;

    let bodyHtml = `<span class="trace-body">${escapeHtml(message)}</span>`;
    if (args) {
      bodyHtml += `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">Args: ${escapeHtml(JSON.stringify(args))}</div>`;
    }

    entry.innerHTML = metaHtml + bodyHtml;
    traceLog.appendChild(entry);
    traceLog.scrollTop = traceLog.scrollHeight;
  }

  // -------------------------------------------------------------
  // 4. Render Results (Signals, Assessment, Review)
  // -------------------------------------------------------------
  function renderSignalsTable(evidenceMap) {
    if (!evidenceMap || Object.keys(evidenceMap).length === 0) {
      signalsTableContainer.innerHTML = `<div class="quiet-placeholder">No statistical signals detected.</div>`;
      return;
    }

    let rowsHtml = "";
    for (const [rxn, ev] of Object.entries(evidenceMap)) {
      const isFlagged = ev.signal_flag;
      const isUnlabeled = !ev.is_in_label;
      let badgeClass = "normal";
      let badgeText = "Normal";

      if (isFlagged && isUnlabeled) {
        badgeClass = "flagged-unlabeled";
        badgeText = "SIGNAL // UNLABELED";
      } else if (isFlagged && !isUnlabeled) {
        badgeClass = "flagged-labeled";
        badgeText = "SIGNAL // LABELED";
      }

      const labelStatus = ev.is_in_label ? `Labeled (${ev.label_section || "Adverse Reactions"})` : "Not in Label";

      rowsHtml += `
        <tr>
          <td style="font-weight: 600;">${escapeHtml(rxn)}</td>
          <td style="font-family: var(--font-mono);">${ev.a}</td>
          <td style="font-family: var(--font-mono); font-weight: 700;">${ev.prr}</td>
          <td style="font-family: var(--font-mono);">${ev.ror} <span style="font-size: 0.7rem; color: var(--text-muted);">[${ev.ror_ci_lower}-${ev.ror_ci_upper}]</span></td>
          <td style="font-family: var(--font-mono);">${ev.chi_square}</td>
          <td><span class="signal-flag-badge ${badgeClass}">${badgeText}</span></td>
          <td style="color: ${ev.is_in_label ? 'var(--accent-labeled)' : 'var(--accent-signal)'}; font-size: 0.78rem;">${escapeHtml(labelStatus)}</td>
        </tr>
      `;
    }

    signalsTableContainer.innerHTML = `
      <table class="signals-table">
        <thead>
          <tr>
            <th>Adverse Reaction (MedDRA)</th>
            <th>Reports (a)</th>
            <th>PRR</th>
            <th>ROR (95% CI)</th>
            <th>Chi²</th>
            <th>Signal Status</th>
            <th>FDA Package Insert</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    `;

    // Populate queries drawer
    if (collectedQueries.size > 0) {
      toggleQueriesBtn.style.display = "block";
      queriesDrawer.innerHTML = Array.from(collectedQueries).map(u => `<div><a href="${u}" target="_blank" rel="noopener" style="color: var(--accent-cyan); text-decoration: none;">${escapeHtml(u)}</a></div>`).join("");
      toggleQueriesBtn.onclick = () => {
        const isShown = queriesDrawer.style.display === "block";
        queriesDrawer.style.display = isShown ? "none" : "block";
        toggleQueriesBtn.textContent = isShown ? "[+] Show all openFDA & PubMed query URLs" : "[-] Hide query URLs";
      };
    }
  }

  function renderAssessment(assessment, fallbackDraft) {
    if (!assessment && !fallbackDraft) {
      assessmentContainer.innerHTML = `<div class="quiet-placeholder">Assessment could not be compiled.</div>`;
      return;
    }

    const findings = assessment ? assessment.detailed_findings : fallbackDraft;
    const limitations = assessment ? assessment.limitations : "FAERS reports represent spontaneous unverified submissions and do not demonstrate causality or true incidence.";
    const citations = (assessment && assessment.citations) ? assessment.citations : [];

    let citationsHtml = "";
    if (citations.length > 0) {
      citationsHtml = `<div style="margin-top: 1rem;"><div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.4rem;">VERIFIED SOURCES & CITATIONS:</div>`;
      citations.forEach((c, idx) => {
        citationsHtml += `<a href="${c}" target="_blank" rel="noopener" class="citation-chip">[Ref ${idx+1}]</a>`;
      });
      citationsHtml += `</div>`;
    }

    assessmentContainer.innerHTML = `
      <div class="assessment-text">${escapeHtml(findings)}</div>
      <div class="limitations-box">
        <div class="limitations-title">Mandatory Pharmacovigilance Limitations</div>
        <div>${escapeHtml(limitations)}</div>
      </div>
      ${citationsHtml}
    `;
  }

  function renderHumanReviewRequired(interruptData) {
    reviewCard.innerHTML = `
      <div class="review-badge alert">Action Required // Human Review Gate</div>
      <h3 class="review-reason">Flagged: ${escapeHtml(interruptData.reason || "Prospective safety risk detected")}</h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5;">
        Automated surveillance detected high-risk or unlabeled disproportionality signals. 
        Safety scientist intervention is required prior to finalizing clinical dissemination.
      </p>
      <div class="review-actions">
        <button class="btn-approve" id="approveBtn">Approve Assessment</button>
        <button class="btn-edit" id="editBtn">Edit Findings</button>
        <button class="btn-investigate" id="investigateBtn">Investigate More</button>
      </div>
    `;

    document.getElementById("approveBtn").onclick = () => submitReviewAction("approve");
    document.getElementById("investigateBtn").onclick = () => submitReviewAction("investigate_more");
    document.getElementById("editBtn").onclick = () => {
      const currentDraft = interruptData.draft || "";
      const edited = prompt("Edit the safety assessment draft:", currentDraft);
      if (edited !== null) {
        submitReviewAction("edit", { edited_draft: edited });
      }
    };
  }

  function renderCompletedReviewState() {
    reviewCard.innerHTML = `
      <div class="review-badge approved">Gate Cleared // Finalized</div>
      <h3 class="review-reason" style="color: #ffffff;">Investigation Audit Complete</h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5;">
        All statistical metrics verified by MCP tools and audited by critic loops. Assessment validated.
      </p>
      <button class="download-json-btn" id="downloadJsonBtn">
        ↓ Download Complete Run JSON
      </button>
    `;

    document.getElementById("downloadJsonBtn").onclick = () => {
      if (!currentRunData && !currentRunId) return;
      window.open(`/api/runs/${currentRunId}`, "_blank");
    };
  }

  async function submitReviewAction(action, payload = {}) {
    if (!currentRunId) return;
    try {
      const resp = await fetch(`/api/runs/${currentRunId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, payload })
      });
      if (resp.ok) {
        reviewCard.innerHTML = `<div class="quiet-placeholder">Decision '${action}' submitted. Resuming workflow...</div>`;
      }
    } catch (err) {
      alert(`Review submission error: ${err.message}`);
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

