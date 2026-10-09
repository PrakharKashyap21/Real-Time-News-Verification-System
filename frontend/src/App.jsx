import React, { useState, useEffect } from "react";
import OmniSearchInput from "./components/OmniSearchInput";
import V2VerificationResult from "./components/V2VerificationResult";
import HistoryDrawer from "./components/HistoryDrawer";
import ArchitectureSection from "./components/ArchitectureSection";
import DocumentAuditView from "./components/DocumentAuditView";
import AnalyticsView from "./components/AnalyticsView";
import RadarView from "./components/RadarView";
import { verifyNewsV2 } from "./api";

const LOCAL_STORAGE_KEY = "truthlens_verification_history_v1";

function App() {
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "radar" || window.location.hash === "#radar") return "radar";
      if (tabParam === "analytics" || window.location.hash === "#analytics") return "analytics";
      if (tabParam === "doc-audit" || window.location.hash === "#doc-audit") return "doc-audit";
    } catch (e) {
      // ignore
    }
    return "verify";
  });
  const [isLoading, setIsLoading] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [activeQuery, setActiveQuery] = useState({ title: "", text: "" });
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState("");


  const [history, setHistory] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.warn("Failed to load verification history from localStorage", e);
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(history));
    } catch (e) {
      console.warn("Failed to save history to localStorage", e);
    }
  }, [history]);

  const handleVerify = async ({ title, text, sourceUrl }) => {
    setIsLoading(true);
    setError("");
    setValidationError("");
    setActiveQuery({ title: title || "", text: text || "" });

    try {
      const data = await verifyNewsV2(title, text);
      setVerificationResult(data);

      const newItem = {
        id: `tl_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        timestamp: new Date().toISOString(),
        title: title || "",
        text: text || "",
        sourceUrl: sourceUrl || "",
        result: data,
      };

      setHistory((prev) => [newItem, ...prev.filter((item) => item.text !== text)].slice(0, 15));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err.message || "An error occurred while performing real-time verification.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectHistoryItem = (item) => {
    setVerificationResult(item.result);
    setActiveQuery({ title: item.title || "", text: item.text || "" });
    setError("");
    setValidationError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleClearHistory = () => {
    setHistory([]);
  };

  const handleDeleteHistoryItem = (id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
  };

  const handleResetHome = () => {
    setVerificationResult(null);
    setActiveQuery({ title: "", text: "" });
    setError("");
    setValidationError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const switchTab = (tab) => {
    setActiveTab(tab);
    setError("");
    setValidationError("");
    try {
      const url = tab === "verify" ? window.location.pathname : `?tab=${tab}`;
      window.history.replaceState(null, "", url);
    } catch (e) {
      // ignore
    }
    if (tab === "verify") {
      handleResetHome();
    }
  };

  return (
    <div className="app-layout">
      {/* Sleek Top Navbar */}
      <nav className="navbar">
        <div className="nav-brand" onClick={() => switchTab("verify")} role="button" tabIndex={0}>
          <span className="brand-logo">TruthLens</span>
          <span className="brand-ai">AI</span>
          <span className="nav-badge">Agentic RAG</span>
        </div>

        {/* Primary Page Navigation Tabs */}
        <div className="nav-center-tabs">
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "verify" ? "active" : ""}`}
            onClick={() => switchTab("verify")}
          >
            🔍 Live Verify
          </button>
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "radar" ? "active" : ""}`}
            onClick={() => switchTab("radar")}
          >
            ⚡ Radar
          </button>
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "doc-audit" ? "active" : ""}`}
            onClick={() => switchTab("doc-audit")}
          >
            📑 Doc Audit
          </button>
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => switchTab("analytics")}
          >
            📊 Analytics
          </button>
        </div>

        <div className="nav-actions">
          {activeTab === "verify" && verificationResult && (
            <button
              type="button"
              className="nav-btn nav-new-btn"
              onClick={handleResetHome}
            >
              + New Search
            </button>
          )}

          <a href="#how-it-works" className="nav-link">
            Architecture
          </a>

          <button
            type="button"
            className="nav-btn nav-history-btn"
            onClick={() => setIsDrawerOpen(true)}
            title="Open Recent Verification History"
          >
            <span>🕒 History</span>
            {history.length > 0 && <span className="nav-history-count">{history.length}</span>}
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-viewport">
        {activeTab === "radar" ? (
          <RadarView
            onVerifyStory={(story) => {
              switchTab("verify");
              handleVerify({ title: story.title, text: story.text });
            }}
          />
        ) : activeTab === "analytics" ? (
          <AnalyticsView />
        ) : activeTab === "doc-audit" ? (
          <DocumentAuditView />
        ) : !verificationResult ? (
          /* Initial Minimalist Landing State (Perplexity / Grok style) */
          <div className="hero-landing-container">
            <div className="hero-center-header">

              <div className="hero-pill">
                <span className="live-dot"></span>
                <span>Real-Time Autonomous Fact-Checking</span>
              </div>
              <h1 className="hero-headline">Where claims meet evidence.</h1>
              <p className="hero-tagline">
                Verify breaking news, viral statements, and article URLs with real-time web retrieval, deep paragraph extraction, and Google Gemini AI.
              </p>
            </div>

            {/* Omni Search AI Box */}
            <div className="hero-search-area">
              <OmniSearchInput
                onSubmit={handleVerify}
                isLoading={isLoading}
                validationError={validationError}
                setValidationError={setValidationError}
                initialText={activeQuery.text}
                initialTitle={activeQuery.title}
                isCompact={false}
              />
            </div>

            {error && (
              <div className="error-card-floating" role="alert">
                <strong>⚠️ Verification Failed:</strong> {error}
              </div>
            )}

            {/* Below-the-fold Architecture Section */}
            <ArchitectureSection />
          </div>
        ) : (
          /* Active Result State */
          <div className="result-view-container">
            {/* Compact Search Bar at Top */}
            <div className="compact-search-container">
              <OmniSearchInput
                onSubmit={handleVerify}
                isLoading={isLoading}
                validationError={validationError}
                setValidationError={setValidationError}
                initialText=""
                initialTitle=""
                isCompact={true}
              />
            </div>

            {error && (
              <div className="error-card-floating" role="alert">
                <strong>⚠️ Verification Failed:</strong> {error}
              </div>
            )}

            {/* Full Width Verification Report */}
            <div className="result-report-card">
              <V2VerificationResult result={verificationResult} />
            </div>
          </div>
        )}
      </main>

      {/* Slide-over Recent History Drawer */}
      <HistoryDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        history={history}
        onSelectHistoryItem={handleSelectHistoryItem}
        onClearHistory={handleClearHistory}
        onDeleteItem={handleDeleteHistoryItem}
      />

      {/* Modern Footer */}
      <footer className="footer-bar">
        <div className="footer-content">
          <p className="footer-main-text">
            <strong>TruthLens AI</strong> searches live news, official archives, and investigative journalism to verify facts with transparent citations.
          </p>
          <p className="footer-sub-text">
            Powered by DuckDuckGo, Trafilatura & Google Gemini AI • Zero Hallucination Attribution
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
