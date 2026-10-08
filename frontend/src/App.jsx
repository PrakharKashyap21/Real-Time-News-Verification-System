import React, { useState } from "react";
import NewsForm from "./components/NewsForm";
import V2VerificationResult from "./components/V2VerificationResult";
import { verifyNewsV2 } from "./api";

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState("");

  const handleVerify = async ({ title, text }) => {
    setIsLoading(true);
    setError("");
    setVerificationResult(null);

    try {
      const data = await verifyNewsV2(title, text);
      setVerificationResult(data);
    } catch (err) {
      setError(err.message || "An error occurred while performing real-time verification.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1 className="main-title">TruthLens AI</h1>
        <p className="subtitle">
          Autonomous real-time news verification and fact-checking powered by Agentic RAG & Google Gemini AI.
        </p>
      </header>

      <main className="main-content">
        <div className="card form-card">
          <NewsForm
            onSubmit={handleVerify}
            isLoading={isLoading}
            validationError={validationError}
            setValidationError={setValidationError}
            submitLabel="Verify News"
          />
        </div>

        {error && (
          <div className="error-card" role="alert">
            <div className="error-title">Error</div>
            <div className="error-message">{error}</div>
          </div>
        )}

        {/* Verification Result Output */}
        {verificationResult && (
          <div className="v2-result-wrapper">
            <V2VerificationResult result={verificationResult} />
          </div>
        )}
      </main>

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
