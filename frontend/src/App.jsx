import React, { useState, useEffect, useRef } from "react";
import OmniSearchInput from "./components/OmniSearchInput";
import V2VerificationResult from "./components/V2VerificationResult";
import HistoryDrawer from "./components/HistoryDrawer";
import ArchitectureSection from "./components/ArchitectureSection";
import DocumentAuditView from "./components/DocumentAuditView";
import AnalyticsView from "./components/AnalyticsView";
import RadarView from "./components/RadarView";
import ImageAuditView from "./components/ImageAuditView";
import AudioAuditView from "./components/AudioAuditView";
import ChatbotBridgeView from "./components/ChatbotBridgeView";
import { verifyNewsV2 } from "./api";

const LOCAL_STORAGE_KEY = "truthlens_verification_history_v1";

function App() {
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "chatbot" || window.location.hash === "#chatbot") return "chatbot";
      if (tabParam === "audio-audit" || window.location.hash === "#audio-audit") return "audio-audit";
      if (tabParam === "image-audit" || window.location.hash === "#image-audit") return "image-audit";
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
  const [activeQuery, setActiveQuery] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("q") || params.get("claim") || params.get("text");
      const title = params.get("title") || "";
      if (q) return { title, text: q };
    } catch (e) {
      // ignore
    }
    return { title: "", text: "" };
  });
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState("");
  const autoVerifiedRef = useRef(false);

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

  // URL Query Parameter Auto-Verification & Demo Loader
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const queryParam = params.get("q") || params.get("claim") || params.get("text");
      const titleParam = params.get("title") || "";

      if (queryParam && !autoVerifiedRef.current) {
        autoVerifiedRef.current = true;
        setActiveTab("verify");
        handleVerify({ title: titleParam, text: queryParam });
        return;
      }

      if (params.get("demo") === "1" && !verificationResult) {
        if (history.length > 0) {
          handleSelectHistoryItem(history[0]);
        } else {
          setVerificationResult({
            overall_assessment: "SUPPORTED",
            assessment_summary: "Multi-source wire consensus confirms the core factual statements regarding Tata Trent standalone revenue growth and brand store expansion.",
            has_conflict: false,
            claims: [
              {
                claim_id: "claim_demo_1",
                text: "Tata Group retail arm Trent reported standalone revenue surge led by Zudio and Westside expansion.",
                verdict: "SUPPORTED",
                reasoning: "Confirmed by earnings filings and multiple primary financial press reports citing official regulatory disclosures.",
                supporting_evidence_count: 3,
                contradicting_evidence_count: 0,
                neutral_evidence_count: 1,
                evidence: [
                  {
                    id: "ev_1",
                    title: "Tata's Trent reports strong Q2 net profit surge driven by retail network",
                    publisher: "Reuters",
                    domain: "reuters.com",
                    url: "https://reuters.com",
                    snippet: "Trent Ltd posted substantial year-on-year revenue gains as apparel chains Westside and Zudio expanded rapidly across tier-1 and tier-2 markets.",
                    stance: "SUPPORTS"
                  },
                  {
                    id: "ev_2",
                    title: "Trent Q2 financial results: Net profit up, retail footprint expands",
                    publisher: "Bloomberg",
                    domain: "bloomberg.com",
                    url: "https://bloomberg.com",
                    snippet: "Standalone quarterly revenue jumped 46 percent according to stock exchange disclosures filed on Wednesday.",
                    stance: "SUPPORTS"
                  },
                  {
                    id: "ev_3",
                    title: "Financial Express Market Desk: Trent quarterly earnings breakdown",
                    publisher: "Financial Express",
                    domain: "financialexpress.com",
                    url: "https://financialexpress.com",
                    snippet: "Tata-backed fashion and retail enterprise Trent continues robust expansion trajectory.",
                    stance: "SUPPORTS"
                  },
                  {
                    id: "ev_4",
                    title: "Trent Limited corporate overview and regulatory history",
                    publisher: "Wikipedia",
                    domain: "en.wikipedia.org",
                    url: "https://en.wikipedia.org",
                    snippet: "Trent is an Indian retail company and part of the Tata Group, operating Westside and Zudio.",
                    stance: "NEUTRAL"
                  }
                ]
              }
            ],
            service_status: { gemini_api: "ok" }
          });
          setActiveQuery({
            title: "Trent Q2 Revenue Growth",
            text: "Tata Group retail arm Trent reported standalone revenue surge led by Zudio and Westside expansion."
          });
        }
      }
    } catch (e) {
      // ignore
    }
  }, []);

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

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [activeTab]);

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
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  };

  return (
    <div className="app-layout">
      {/* Ambient Cosmic Aurora Glow */}
      <div className="ambient-background-glow" aria-hidden="true">
        <div className="glow-orb glow-orb-primary" />
        <div className="glow-orb glow-orb-secondary" />
        <div className="glow-orb glow-orb-accent" />
      </div>

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
            className={`nav-tab-link ${activeTab === "image-audit" ? "active" : ""}`}
            onClick={() => switchTab("image-audit")}
          >
            🖼️ Image Audit
          </button>
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "audio-audit" ? "active" : ""}`}
            onClick={() => switchTab("audio-audit")}
          >
            🎙️ Audio Audit
          </button>
          <button
            type="button"
            className={`nav-tab-link ${activeTab === "chatbot" ? "active" : ""}`}
            onClick={() => switchTab("chatbot")}
          >
            📱 Chatbot Bridge
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
        <div key={activeTab + (verificationResult ? "-result" : "-landing")} className="tab-viewport-fade">
          {activeTab === "chatbot" ? (
            <ChatbotBridgeView
              onOpenInDashboard={(claim) => {
                switchTab("verify");
                handleVerify({ title: "Chat Forward Claim", text: claim });
              }}
            />
          ) : activeTab === "audio-audit" ? (
            <AudioAuditView
              onAuditToLiveVerify={(story) => {
                switchTab("verify");
                handleVerify({ title: story.title, text: story.text });
              }}
            />
          ) : activeTab === "image-audit" ? (
            <ImageAuditView
              onAuditToLiveVerify={(story) => {
                switchTab("verify");
                handleVerify({ title: story.title, text: story.text });
              }}
            />
          ) : activeTab === "radar" ? (
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
        </div>
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
