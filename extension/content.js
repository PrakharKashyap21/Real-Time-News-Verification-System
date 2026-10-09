// TruthLens AI - In-Page Content Script

(function () {
  let activeModal = null;
  let floatingTooltip = null;

  // Listen for background worker messages
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "SHOW_VERIFICATION_MODAL") {
      createOrShowModal(msg.text, msg.title);
    } else if (msg.action === "VERIFY_PAGE_URL") {
      handlePageUrlVerification(msg.url, msg.title);
    }
  });

  // Floating Quick-Action Pill on text selection
  document.addEventListener("mouseup", (e) => {
    // Avoid triggering inside our own modal or the floating pill itself!
    if (activeModal && activeModal.contains(e.target)) return;
    if (floatingTooltip && (floatingTooltip === e.target || floatingTooltip.contains(e.target))) return;

    const selection = window.getSelection();
    const text = selection ? selection.toString().trim() : "";

    if (text.length >= 20 && text.length <= 1500) {
      try {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        if (rect && rect.width > 0 && rect.height > 0) {
          showFloatingPill(rect, text);
        }
      } catch (err) {
        // Selection range error fallback
      }
    } else {
      removeFloatingPill();
    }
  });

  document.addEventListener("mousedown", (e) => {
    // If clicking outside the floating tooltip and outside the modal, dismiss the tooltip
    if (floatingTooltip && !floatingTooltip.contains(e.target)) {
      removeFloatingPill();
    }
  });

  function showFloatingPill(rect, text) {
    removeFloatingPill();

    const pill = document.createElement("div");
    pill.className = "truthlens-floating-pill";
    pill.setAttribute("role", "button");
    pill.setAttribute("tabindex", "0");
    pill.innerHTML = `
      <span class="tl-pill-icon">🔍</span>
      <span class="tl-pill-text">Verify with TruthLens</span>
    `;

    // Position carefully below selection, clamped within viewport
    const scrollY = window.scrollY || window.pageYOffset || 0;
    const scrollX = window.scrollX || window.pageXOffset || 0;
    const top = scrollY + rect.bottom + 8;
    const left = Math.max(12, Math.min(window.innerWidth - 180, scrollX + rect.left + rect.width / 2 - 75));

    pill.style.top = `${top}px`;
    pill.style.left = `${left}px`;

    const handleAction = (e) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      const claimText = text;
      removeFloatingPill();
      createOrShowModal(claimText, document.title || "Selected News Claim");
    };

    // Prevent text deselection on mousedown/pointerdown
    pill.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
    });

    pill.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
    });

    pill.addEventListener("click", handleAction);

    document.body.appendChild(pill);
    floatingTooltip = pill;
  }

  function removeFloatingPill() {
    if (floatingTooltip && floatingTooltip.parentNode) {
      floatingTooltip.parentNode.removeChild(floatingTooltip);
    }
    floatingTooltip = null;
  }

  async function handlePageUrlVerification(url, title) {
    createOrShowModal("Fetching article text from page...", title || url);
    updateModalState("LOADING", "Reading and analyzing page article content...");

    try {
      const extractResp = await chrome.runtime.sendMessage({
        action: "API_EXTRACT_URL",
        payload: { url }
      });

      if (extractResp && extractResp.success && extractResp.data && extractResp.data.success) {
        const text = extractResp.data.text.slice(0, 800);
        executeVerification(text, extractResp.data.title || title);
      } else {
        // Fallback to meta description or selection
        const metaDesc = document.querySelector('meta[name="description"]')?.content || "";
        executeVerification(metaDesc || title, title);
      }
    } catch (err) {
      executeVerification(title, title);
    }
  }

  function createOrShowModal(claimText, title) {
    removeFloatingPill();

    if (activeModal) {
      activeModal.remove();
      activeModal = null;
    }

    const modal = document.createElement("div");
    modal.id = "truthlens-modal-root";
    modal.className = "truthlens-inpage-modal";

    modal.innerHTML = `
      <div class="tl-modal-card">
        <div class="tl-modal-header">
          <div class="tl-brand-cluster">
            <span class="tl-brand-logo">TruthLens</span>
            <span class="tl-brand-ai">AI</span>
            <span class="tl-badge">Agentic RAG</span>
          </div>
          <button type="button" class="tl-close-btn" id="tl-btn-close" title="Close (ESC)">✕</button>
        </div>

        <div class="tl-claim-box">
          <span class="tl-claim-label">Selected Statement:</span>
          <p class="tl-claim-text" id="tl-claim-content">"${escapeHtml(claimText)}"</p>
        </div>

        <div class="tl-result-body" id="tl-result-container">
          <div class="tl-loading-state">
            <div class="tl-radar-spinner"></div>
            <p class="tl-loading-text">Cross-referencing live news wires & fact-check archives...</p>
          </div>
        </div>

        <div class="tl-modal-footer">
          <button type="button" class="tl-dashboard-link" id="tl-open-web-app">
            Open in Full Dashboard ↗
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    activeModal = modal;

    // Event listeners
    modal.querySelector("#tl-btn-close").addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });

    document.addEventListener("keydown", handleEscKey);

    modal.querySelector("#tl-open-web-app").addEventListener("click", () => {
      const query = encodeURIComponent(claimText);
      const titleParam = encodeURIComponent(title || "Selected Claim");
      window.open(`http://localhost:5173/?q=${query}&title=${titleParam}`, "_blank");
    });

    executeVerification(claimText, title);
  }

  function handleEscKey(e) {
    if (e.key === "Escape") closeModal();
  }

  function closeModal() {
    if (activeModal) {
      activeModal.classList.add("tl-closing");
      setTimeout(() => {
        if (activeModal && activeModal.parentNode) {
          activeModal.parentNode.removeChild(activeModal);
        }
        activeModal = null;
        document.removeEventListener("keydown", handleEscKey);
      }, 200);
    }
  }

  function updateModalState(state, message) {
    const container = document.getElementById("tl-result-container");
    if (!container) return;

    if (state === "LOADING") {
      container.innerHTML = `
        <div class="tl-loading-state">
          <div class="tl-radar-spinner"></div>
          <p class="tl-loading-text">${escapeHtml(message)}</p>
        </div>
      `;
    }
  }

  async function executeVerification(claimText, title) {
    try {
      const response = await chrome.runtime.sendMessage({
        action: "API_VERIFY_CLAIM",
        payload: {
          title: title || "Web Claim",
          text: claimText
        }
      });

      if (!response || !response.success || !response.data) {
        showError(response?.error || "Could not connect to TruthLens AI backend.");
        return;
      }

      renderVerificationResult(response.data);
    } catch (err) {
      showError(err.message || "Failed to communicate with TruthLens AI.");
    }
  }

  function renderVerificationResult(data) {
    const container = document.getElementById("tl-result-container");
    if (!container) return;

    const overall = (data.overall_assessment || "UNVERIFIED").toUpperCase();
    const summary = data.assessment_summary || "Verification analysis complete.";
    const claims = data.claims || [];

    let allEvidence = [];
    claims.forEach(c => {
      if (c.evidence && Array.isArray(c.evidence)) {
        allEvidence = allEvidence.concat(c.evidence);
      }
    });

    let verdictClass = "tl-verdict-unverified";
    let verdictIcon = "⚪";
    let verdictLabel = "UNVERIFIED";

    if (overall.includes("SUPPORTED") || overall.includes("VERIFIED") || overall.includes("TRUE")) {
      verdictClass = "tl-verdict-supported";
      verdictIcon = "🟢";
      verdictLabel = "VERIFIED / ACCURATE";
    } else if (overall.includes("CONTRADICTED") || overall.includes("FALSE")) {
      verdictClass = "tl-verdict-contradicted";
      verdictIcon = "🔴";
      verdictLabel = "FALSE / DEBUNKED";
    } else if (overall.includes("MISLEADING") || overall.includes("PARTIAL")) {
      verdictClass = "tl-verdict-misleading";
      verdictIcon = "🟠";
      verdictLabel = "MISLEADING / DISPUTED";
    }

    let sourcesHtml = "";
    if (allEvidence.length > 0) {
      const uniqueSources = [];
      const seen = new Set();
      allEvidence.forEach(ev => {
        if (!seen.has(ev.url) && ev.url) {
          seen.add(ev.url);
          uniqueSources.push(ev);
        }
      });

      sourcesHtml = `
        <div class="tl-sources-block">
          <span class="tl-sources-title">Attributed Sources (${uniqueSources.length}):</span>
          <div class="tl-sources-chips">
            ${uniqueSources.slice(0, 4).map(s => `
              <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="tl-source-chip">
                🌐 ${escapeHtml(s.publisher || s.domain || "News Source")}
              </a>
            `).join("")}
          </div>
        </div>
      `;
    } else {
      sourcesHtml = `
        <div class="tl-sources-block">
          <p class="tl-no-sources">No corroborating reporting found on indexed wire services.</p>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="tl-verdict-banner ${verdictClass}">
        <div class="tl-verdict-top">
          <span class="tl-verdict-icon">${verdictIcon}</span>
          <span class="tl-verdict-title">${verdictLabel}</span>
        </div>
        <p class="tl-verdict-summary">${escapeHtml(summary)}</p>
      </div>

      ${sourcesHtml}
    `;
  }

  function showError(msg) {
    const container = document.getElementById("tl-result-container");
    if (!container) return;
    container.innerHTML = `
      <div class="tl-error-banner">
        <span class="tl-error-icon">⚠️</span>
        <div class="tl-error-details">
          <strong>Verification Unavailable</strong>
          <p>${escapeHtml(msg)}</p>
          <small>Make sure the TruthLens AI backend is running (<code>http://localhost:8008</code>).</small>
        </div>
      </div>
    `;
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
})();
