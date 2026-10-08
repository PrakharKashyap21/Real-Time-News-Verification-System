import React, { useState } from "react";

const V2VerificationResult = ({ result }) => {
  if (!result) return null;

  const [copied, setCopied] = useState(false);

  const {
    overall_assessment,
    assessment_summary,
    has_conflict,
    claims,
    service_status,
    disclaimer
  } = result;

  const getVerdictClass = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return "verdict-supported";
      case "CONTRADICTED":
        return "verdict-contradicted";
      case "MISLEADING":
        return "verdict-misleading";
      case "UNVERIFIED":
      default:
        return "verdict-unverified";
    }
  };

  const getVerdictIcon = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return "✅";
      case "CONTRADICTED":
        return "❌";
      case "MISLEADING":
        return "⚠️";
      case "UNVERIFIED":
      default:
        return "❓";
    }
  };

  const getVerdictDescription = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return "All core factual statements in this news claim were directly confirmed by live journalism and credible reporting.";
      case "CONTRADICTED":
        return "Credible external news reports or official sources refute or debunk one or more key assertions in this claim.";
      case "MISLEADING":
        return "This claim mixes verified facts with false, distorted, or unconfirmed claims.";
      case "UNVERIFIED":
      default:
        return "No sufficient indexed news coverage or fact-check records were found. Note: UNVERIFIED indicates a lack of external reporting, not necessarily falsehood.";
    }
  };

  const getStanceBadge = (stance) => {
    switch (stance?.toUpperCase()) {
      case "SUPPORTS":
        return <span className="stance-chip stance-supports">✓ Corroborates</span>;
      case "CONTRADICTS":
        return <span className="stance-chip stance-contradicts">✗ Refutes</span>;
      case "NEUTRAL":
      default:
        return <span className="stance-chip stance-neutral">○ Context</span>;
    }
  };

  const handleCopyReport = () => {
    const reportText = `[News Verification Report]
Overall Verdict: ${overall_assessment}
Summary: ${assessment_summary}

Claims Evaluated:
${(claims || []).map((c, i) => `\n${i + 1}. "${c.text}" -> ${c.verdict}\nReasoning: ${c.reasoning}`).join("\n")}

Sources Consulted:
${(claims || []).flatMap((c) => c.evidence || []).map((e) => `- ${e.publisher}: ${e.title} (${e.url})`).join("\n") || "No sources"}
`;

    navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const totalSources = (claims || []).reduce((acc, c) => acc + (c.evidence ? c.evidence.length : 0), 0);

  return (
    <div className="v2-verification-container">
      {/* Top Banner with Verdict & Copy Button */}
      <div className={`hero-verdict-card ${getVerdictClass(overall_assessment)}`}>
        <div className="hero-verdict-header">
          <div className="hero-verdict-badge-group">
            <span className="verdict-emoji">{getVerdictIcon(overall_assessment)}</span>
            <span className="hero-verdict-title">{overall_assessment}</span>
          </div>

          <button
            type="button"
            className="copy-report-btn"
            onClick={handleCopyReport}
            title="Copy structured summary to clipboard"
          >
            {copied ? "✓ Copied!" : "📋 Copy Report"}
          </button>
        </div>

        <p className="hero-verdict-summary">{assessment_summary}</p>

        <div className="hero-verdict-footer">
          <div className="verdict-guide-box">
            <strong>Analysis Context:</strong> {getVerdictDescription(overall_assessment)}
          </div>
          {has_conflict && (
            <div className="conflict-alert-badge">
              ⚠️ Conflicting reports found across different publishers
            </div>
          )}
        </div>
      </div>

      {/* Stats Summary Strip */}
      <div className="stats-strip">
        <div className="stat-item">
          <span className="stat-num">{claims ? claims.length : 0}</span>
          <span className="stat-label">Claims Extracted</span>
        </div>
        <div className="stat-item">
          <span className="stat-num">{totalSources}</span>
          <span className="stat-label">Verified Sources</span>
        </div>
        <div className="stat-item">
          <span className="stat-num">
            {service_status?.gemini_api === "ok" ? "Gemini AI" : "Heuristic"}
          </span>
          <span className="stat-label">Reasoning Engine</span>
        </div>
      </div>

      {/* Claims Breakdown Section */}
      <div className="claims-section">
        <h3 className="section-heading">Detailed Claim-by-Claim Verification</h3>

        {(!claims || claims.length === 0) ? (
          <div className="empty-state-box">
            No distinct factual claims were extracted. Try submitting a longer news excerpt.
          </div>
        ) : (
          claims.map((claim, index) => (
            <ClaimCard
              key={claim.claim_id || index}
              claim={claim}
              index={index}
              getVerdictClass={getVerdictClass}
              getVerdictIcon={getVerdictIcon}
              getStanceBadge={getStanceBadge}
            />
          ))
        )}
      </div>

      {/* Disclaimer */}
      <div className="disclaimer-footer-card">
        <span className="disclaimer-icon">ℹ️</span>
        <p className="disclaimer-text">
          {disclaimer ||
            "Verification is powered by real-time web news retrieval and Google Gemini AI reasoning. UNVERIFIED claims indicate an absence of indexed external reporting rather than proven falsehood."}
        </p>
      </div>
    </div>
  );
};

const ClaimCard = ({ claim, index, getVerdictClass, getVerdictIcon, getStanceBadge }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const {
    text,
    verdict,
    reasoning,
    supporting_evidence_count = 0,
    contradicting_evidence_count = 0,
    neutral_evidence_count = 0,
    evidence = []
  } = claim;

  return (
    <div className={`claim-card-modern ${getVerdictClass(verdict)}`}>
      <div
        className="claim-header-modern"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
      >
        <div className="claim-headline-area">
          <span className="claim-badge-num">Claim #{index + 1}</span>
          <h4 className="claim-quote-text">"{text}"</h4>
        </div>

        <div className="claim-verdict-pill-area">
          <span className={`verdict-pill-modern ${getVerdictClass(verdict)}`}>
            {getVerdictIcon(verdict)} {verdict}
          </span>
          <button type="button" className="accordion-arrow" aria-label="Toggle details">
            {isExpanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="claim-content-modern">
          {/* AI Explanation Box */}
          <div className="ai-reasoning-card">
            <div className="reasoning-header">
              <span className="ai-icon">💡</span>
              <span className="ai-label">AI Verification Analysis</span>
            </div>
            <p className="reasoning-text">{reasoning}</p>
          </div>

          {/* Stance Counter */}
          {evidence.length > 0 && (
            <div className="stance-counters-bar">
              <span className="counter-pill sup">✓ {supporting_evidence_count} Supporting</span>
              <span className="counter-pill con">✗ {contradicting_evidence_count} Refuting</span>
              <span className="counter-pill neu">○ {neutral_evidence_count} Mentioning</span>
            </div>
          )}

          {/* Evidence Sources List */}
          {evidence.length > 0 ? (
            <div className="sources-container">
              <h5 className="sources-title">📰 Citations & Verified Sources ({evidence.length})</h5>
              <div className="sources-grid">
                {evidence.map((item, idx) => (
                  <SourceCard key={item.id || idx} item={item} getStanceBadge={getStanceBadge} />
                ))}
              </div>
            </div>
          ) : (
            <div className="no-sources-alert">
              No direct external news articles or fact-checks were retrieved for this specific assertion.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SourceCard = ({ item, getStanceBadge }) => {
  return (
    <div className="source-citation-card">
      <div className="source-card-header">
        <div className="publisher-badge">
          <span className="publisher-logo-icon">🌐</span>
          <span className="publisher-name">{item.publisher || item.domain}</span>
        </div>
        {getStanceBadge(item.stance)}
      </div>

      <h5 className="source-headline">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="source-external-link"
        >
          {item.title} <span className="external-arrow">↗</span>
        </a>
      </h5>

      {item.snippet && (
        <div className="quote-callout">
          <span className="quote-mark">“</span>
          <p className="quote-body">{item.snippet}</p>
        </div>
      )}

      <div className="source-footer">
        <span className="source-domain-tag">{item.domain}</span>
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="read-article-link"
        >
          Read Source →
        </a>
      </div>
    </div>
  );
};

export default V2VerificationResult;
