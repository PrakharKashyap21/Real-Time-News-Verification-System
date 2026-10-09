import React, { useState, useEffect } from "react";
import NewsForm from "./components/NewsForm";
import V2VerificationResult from "./components/V2VerificationResult";
import RecentHistory from "./components/RecentHistory";
import EmptyState from "./components/EmptyState";
import { verifyNewsV2 } from "./api";

const LOCAL_STORAGE_KEY = "truthlens_verification_history_v1";

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [activeHistoryId, setActiveHistoryId] = useState(null);
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
    setVerificationResult(null);
    setActiveHistoryId(null);

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

      setHistory((prev) => [newItem, ...prev.filter((item) => item.text !== text)].slice(0, 10));
      setActiveHistoryId(newItem.id);
    } catch (err) {
      setError(err.message || "An error occurred while performing real-time verification.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectHistoryItem = (item) => {
    setVerificationResult(item.result);
    setActiveHistoryId(item.id);
    setError("");
    setValidationError("");
  };

  const handleClearHistory = () => {
    setHistory([]);
    if (activeHistoryId) {
      setActiveHistoryId(null);
    }
  };

  const handleDeleteHistoryItem = (id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
    if (activeHistoryId === id) {
      setActiveHistoryId(null);
    }
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="header">
        <div className="header-badge">
          <span className="live-pulsar"></span>
          <span>Agentic RAG Fact Checking</span>
        </div>
        <h1 className="main-title">TruthLens AI</h1>
        <p className="subtitle">
          Autonomous real-time news verification and deep source attribution powered by DuckDuckGo, Trafilatura & Google Gemini AI.
        </p>
      </header>

      {/* Main 2-Column Dashboard Layout */}
      <main className="dashboard-grid">
        {/* Left Column: Input Form + Recent History */}
        <section className="left-panel">
          <div className="card form-card">
            <NewsForm
              onSubmit={handleVerify}
              isLoading={isLoading}
              validationError={validationError}
              setValidationError={setValidationError}
              submitLabel="Verify News"
            />
          </div>

          <RecentHistory
            history={history}
            onSelectHistoryItem={handleSelectHistoryItem}
            onClearHistory={handleClearHistory}
            onDeleteItem={handleDeleteHistoryItem}
            activeId={activeHistoryId}
          />
        </section>

        {/* Right Column: Verification Results / Live Skeleton / Empty Overview */}
        <section className="right-panel">
          {error && (
            <div className="error-card" role="alert">
              <div className="error-title">⚠️ Verification Error</div>
              <div className="error-message">{error}</div>
            </div>
          )}

          {verificationResult ? (
            <div className="v2-result-wrapper">
              <V2VerificationResult result={verificationResult} />
            </div>
          ) : isLoading ? (
            <div className="card live-analysis-card">
              <div className="analysis-loading-header">
                <div className="loading-orbit-spinner"></div>
                <div>
                  <h3 className="analysis-loading-title">Autonomous Fact-Checking in Progress</h3>
                  <p className="analysis-loading-subtitle">
                    Searching indexed news sources, crawling article paragraphs, and synthesizing claims with Gemini AI...
                  </p>
                </div>
              </div>
              <div className="skeleton-grid">
                <div className="skeleton-box skeleton-hero"></div>
                <div className="skeleton-box skeleton-text"></div>
                <div className="skeleton-box skeleton-text-short"></div>
                <div className="skeleton-box skeleton-card"></div>
              </div>
            </div>
          ) : (
            <EmptyState />
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="disclaimer-container">
          <p className="disclaimer-text">
            <strong>TruthLens AI</strong> searches live breaking news, official archives, and investigative journalism to verify facts with transparent citations.
          </p>
          <p className="disclaimer-text">
            Claims marked <em>UNVERIFIED</em> indicate an absence of indexed external reporting rather than proven falsehood.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
