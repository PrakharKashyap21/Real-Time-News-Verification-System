// TruthLens AI - Popup Controller Script

document.addEventListener("DOMContentLoaded", () => {
  const statusIndicator = document.getElementById("backend-status");
  const statusLabel = statusIndicator.querySelector(".status-label");
  const tabTitleEl = document.getElementById("active-tab-title");
  const btnVerifyPage = document.getElementById("btn-verify-current-page");
  const claimTextarea = document.getElementById("claim-text");
  const btnVerifyClaim = document.getElementById("btn-verify-claim");
  const sampleChips = document.querySelectorAll(".sample-chip");

  const resultCard = document.getElementById("result-card");
  const resultLoading = document.getElementById("result-loading");
  const resultContent = document.getElementById("result-content");
  const verdictBadge = document.getElementById("verdict-badge");
  const verdictIcon = document.getElementById("verdict-icon");
  const verdictLabel = document.getElementById("verdict-label");
  const resultSummary = document.getElementById("result-summary");
  const sourcesContainer = document.getElementById("sources-container");

  let activeTabInfo = { url: "", title: "" };

  // 1. Check Backend Health
  chrome.runtime.sendMessage({ action: "API_CHECK_HEALTH" }, (resp) => {
    if (resp && resp.isHealthy) {
      statusIndicator.className = "status-indicator online";
      statusLabel.textContent = "Connected";
    } else {
      statusIndicator.className = "status-indicator offline";
      statusLabel.textContent = "Offline";
      statusIndicator.title = "Start TruthLens backend on port 8008";
    }
  });

  // 2. Fetch Active Tab Info
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0]) {
      activeTabInfo.url = tabs[0].url || "";
      activeTabInfo.title = tabs[0].title || "Web Page";
      tabTitleEl.textContent = activeTabInfo.title;
      tabTitleEl.title = activeTabInfo.title;
    }
  });

  // 3. Quick Sample Chips
  sampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const claim = chip.getAttribute("data-claim");
      if (claim) {
        claimTextarea.value = claim;
        triggerVerification(claim, "Quick Sample");
      }
    });
  });

  // 4. Verify Current Page Button
  btnVerifyPage.addEventListener("click", () => {
    if (!activeTabInfo.url) return;
    claimTextarea.value = activeTabInfo.title;
    triggerPageVerification(activeTabInfo.url, activeTabInfo.title);
  });

  // 5. Verify Claim Button
  btnVerifyClaim.addEventListener("click", () => {
    const claim = claimTextarea.value.trim();
    if (claim) {
      triggerVerification(claim, "Direct Claim");
    }
  });

  async function triggerVerification(text, title) {
    showLoading();

    try {
      const resp = await chrome.runtime.sendMessage({
        action: "API_VERIFY_CLAIM",
        payload: { title, text }
      });

      if (resp && resp.success && resp.data) {
        renderResult(resp.data);
      } else {
        showError(resp?.error || "Failed to verify claim.");
      }
    } catch (err) {
      showError(err.message || "Communication error with background script.");
    }
  }

  async function triggerPageVerification(url, title) {
    showLoading();

    try {
      const extractResp = await chrome.runtime.sendMessage({
        action: "API_EXTRACT_URL",
        payload: { url }
      });

      let textToVerify = title;
      if (extractResp && extractResp.success && extractResp.data && extractResp.data.success) {
        textToVerify = extractResp.data.text.slice(0, 700);
      }

      const verifyResp = await chrome.runtime.sendMessage({
        action: "API_VERIFY_CLAIM",
        payload: { title, text: textToVerify }
      });

      if (verifyResp && verifyResp.success && verifyResp.data) {
        renderResult(verifyResp.data);
      } else {
        showError(verifyResp?.error || "Failed to verify page content.");
      }
    } catch (err) {
      showError(err.message || "Failed to extract and verify page.");
    }
  }

  function showLoading() {
    resultCard.classList.remove("hidden");
    resultLoading.classList.remove("hidden");
    resultContent.classList.add("hidden");
    btnVerifyClaim.disabled = true;
    btnVerifyPage.disabled = true;
  }

  function renderResult(data) {
    resultLoading.classList.add("hidden");
    resultContent.classList.remove("hidden");
    btnVerifyClaim.disabled = false;
    btnVerifyPage.disabled = false;

    const overall = (data.overall_assessment || "UNVERIFIED").toUpperCase();
    const summary = data.assessment_summary || "Verification analysis complete.";
    const claims = data.claims || [];

    let allEvidence = [];
    claims.forEach(c => {
      if (c.evidence && Array.isArray(c.evidence)) {
        allEvidence = allEvidence.concat(c.evidence);
      }
    });

    verdictBadge.className = "verdict-banner";
    if (overall.includes("SUPPORTED") || overall.includes("VERIFIED") || overall.includes("TRUE")) {
      verdictBadge.classList.add("verdict-supported");
      verdictIcon.textContent = "🟢";
      verdictLabel.textContent = "VERIFIED / ACCURATE";
    } else if (overall.includes("CONTRADICTED") || overall.includes("FALSE")) {
      verdictBadge.classList.add("verdict-contradicted");
      verdictIcon.textContent = "🔴";
      verdictLabel.textContent = "FALSE / DEBUNKED";
    } else if (overall.includes("MISLEADING") || overall.includes("PARTIAL")) {
      verdictBadge.classList.add("verdict-misleading");
      verdictIcon.textContent = "🟠";
      verdictLabel.textContent = "MISLEADING / DISPUTED";
    } else {
      verdictBadge.classList.add("verdict-unverified");
      verdictIcon.textContent = "⚪";
      verdictLabel.textContent = "UNVERIFIED / NO EVIDENCE";
    }

    resultSummary.textContent = summary;

    // Render sources
    sourcesContainer.innerHTML = "";
    if (allEvidence.length > 0) {
      const seen = new Set();
      allEvidence.slice(0, 4).forEach((ev) => {
        if (!seen.has(ev.url) && ev.url) {
          seen.add(ev.url);
          const link = document.createElement("a");
          link.href = ev.url;
          link.target = "_blank";
          link.className = "source-item";
          link.textContent = `🌐 ${ev.publisher || ev.domain || "Source"}`;
          sourcesContainer.appendChild(link);
        }
      });
    }

    if (sourcesContainer.children.length === 0) {
      const note = document.createElement("span");
      note.style.color = "#64748b";
      note.style.fontSize = "11px";
      note.textContent = "No external news wire links found.";
      sourcesContainer.appendChild(note);
    }
  }

  function showError(msg) {
    resultLoading.classList.add("hidden");
    resultContent.classList.remove("hidden");
    btnVerifyClaim.disabled = false;
    btnVerifyPage.disabled = false;

    verdictBadge.className = "verdict-banner verdict-contradicted";
    verdictIcon.textContent = "⚠️";
    verdictLabel.textContent = "VERIFICATION ERROR";
    resultSummary.textContent = msg;
    sourcesContainer.innerHTML = "";
  }

  const footerOpenApp = document.getElementById("footer-open-app");
  if (footerOpenApp) {
    footerOpenApp.addEventListener("click", (e) => {
      const currentClaim = claimTextarea ? claimTextarea.value.trim() : "";
      if (currentClaim) {
        e.preventDefault();
        const url = `http://localhost:5173/?q=${encodeURIComponent(currentClaim)}&title=${encodeURIComponent("Claim Check")}`;
        chrome.tabs.create({ url });
      }
    });
  }
});
