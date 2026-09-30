import React, { useState } from "react";

const V2VerificationResult = ({ result }) => {
  if (!result) return null;

  const {
    overall_assessment,
    assessment_summary,
    has_conflict,
    claims,
    linguistic_signal,
    service_status,
    disclaimer
  } = result;

  const getVerdictClass = (verdict) => {
    switch (verdict) {
      case "SUPPORTED":
        return "badge-supported";
      case "CONTRADICTED":
        return "badge-contradicted";
      case "UNVERIFIED":
      default:
        return "badge-unverified";
    }
  };

  const getVerdictExplanation = (verdict) => {
    switch (verdict) {
      case "SUPPORTED":
        return "All extracted claims in this article were corroborated by external fact-checks, live news reporting, or reference sources.";
      case "CONTRADICTED":
        return "One or more extracted claims were directly contradicted or debunked by external fact-checks or reporting.";
      case "UNVERIFIED":
      default:
        return "Available external evidence is insufficient or inconclusive to confirm or refute the claims. Note: UNVERIFIED does NOT mean the article is false; it indicates an absence of matched external reporting.";
    }
  };

  const getStrengthClass = (strength) => {
    switch (strength) {
      case "STRONG":
        return "strength-strong";
      case "MODERATE":
        return "strength-moderate";
      case "LIMITED":
        return "strength-limited";
      case "NONE":
      default:
        return "strength-none";
    }
  };

  const getUncertaintyClass = (level) => {
    switch (level) {
      case "LOW":
        return "uncertainty-low";
      case "MEDIUM":
        return "uncertainty-medium";
      case "HIGH":
      default:
        return "uncertainty-high";
    }
  };

  const getStanceBadge = (stance) => {
    switch (stance) {
      case "SUPPORTS":
        return <span className="stance-badge stance-supports">Supports</span>;
      case "CONTRADICTS":
        return <span className="stance-badge stance-contradicts">Contradicts</span>;
      case "NEUTRAL":
      default:
        return <span className="stance-badge stance-neutral">Neutral</span>;
    }
  };

  // Check if article has mixed claim outcomes
  const verdicts = claims ? claims.map((c) => c.verdict) : [];
  const uniqueVerdicts = Array.from(new Set(verdicts));
  const isMultiClaimMixed = uniqueVerdicts.length > 1;

  // Check service status alerts
  const hasServiceIssue =
    service_status &&
    (service_status.fact_check_api !== "ok" ||
      service_status.live_news_api !== "ok" ||
      service_status.reference_api !== "ok");

  return (
    <div className="v2-verification-container">
      {/* Overall Assessment Header */}
      <div className={`overall-card ${getVerdictClass(overall_assessment)}`}>
        <div className="overall-header">
          <div className="overall-title-group">
            <span className="overall-label">Overall Article Assessment</span>
            <span className={`verdict-pill ${getVerdictClass(overall_assessment)}`}>
              {overall_assessment}
            </span>
          </div>
          {has_conflict && (
            <span className="conflict-flag-badge">
              ⚠️ Conflicting Evidence Detected
            </span>
          )}
        </div>

        <p className="overall-summary">{assessment_summary}</p>

        <div className="verdict-explanation-box">
          <strong>What this means:</strong> {getVerdictExplanation(overall_assessment)}
        </div>
      </div>

      {/* Multi-claim Mixed Notice */}
      {isMultiClaimMixed && (
        <div className="mixed-claims-notice" role="note">
          <div className="mixed-claims-title">📊 Multi-Claim Article Breakdown</div>
          <p className="mixed-claims-text">
            This article contains multiple claims with differing verification outcomes. Review the claim-by-claim breakdown below to see the evidence for each individual assertion.
          </p>
        </div>
      )}

      {/* Service Status Warning Banners */}
      {hasServiceIssue && (
        <div className="service-warning-banner" role="alert">
          <div className="service-warning-title">⚠️ External Provider Availability Notice</div>
          <ul>
            {service_status.fact_check_api === "missing_api_key" && (
              <li>Google Fact Check API key is not configured on the server. Fact-check evidence retrieval is currently unavailable.</li>
            )}
            {service_status.fact_check_api && service_status.fact_check_api.startsWith("error") && (
              <li>Google Fact Check API encountered an issue ({service_status.fact_check_api}). Fact-check results may be partial.</li>
            )}
            {service_status.live_news_api && service_status.live_news_api === "missing_api_key" && (
              <li>Live News API key is not configured on the server. Live news coverage retrieval is unavailable.</li>
            )}
            {service_status.live_news_api && service_status.live_news_api === "rate_limited" && (
              <li>Live news search provider reached its rate limit. Live news coverage may be partial.</li>
            )}
            {service_status.live_news_api && service_status.live_news_api.startsWith("error") && (
              <li>Live news search encountered an issue ({service_status.live_news_api}). News results may be partial.</li>
            )}
            {service_status.reference_api && service_status.reference_api === "rate_limited" && (
              <li>General reference provider reached its rate limit. Reference encyclopedia results may be partial.</li>
            )}
            {service_status.reference_api && service_status.reference_api === "timeout" && (
              <li>General reference retrieval timed out. Reference encyclopedia results may be partial.</li>
            )}
            {service_status.reference_api && service_status.reference_api.startsWith("error") && (
              <li>General reference provider encountered an issue ({service_status.reference_api}).</li>
            )}
          </ul>
        </div>
      )}

      {/* Article-level Linguistic SVM Signal Banner (Informational Only) */}
      {linguistic_signal && (
        <div className="linguistic-signal-card">
          <div className="linguistic-signal-header">
            <span className="signal-title">Linguistic Pattern Signal (V1 SVM Baseline)</span>
            <span className="signal-score">Margin Confidence: {linguistic_signal.confidence.toFixed(1)}%</span>
          </div>
          <p className="signal-message">{linguistic_signal.message}</p>
          <div className="signal-disclaimer">
            Informational baseline only: The linguistic signal is derived strictly from text style classification (V1 SVM) and does NOT evaluate factual truth or external evidence.
          </div>
        </div>
      )}

      {/* Extracted Claims Section */}
      <div className="claims-section">
        <h2 className="claims-section-title">
          Extracted Claims ({claims ? claims.length : 0})
        </h2>

        {!claims || claims.length === 0 ? (
          <div className="empty-claims-card">
            No distinct factual claims were extracted from the input text. Please provide more detailed news content.
          </div>
        ) : (
          claims.map((claim, index) => (
            <ClaimCard
              key={claim.claim_id || index}
              claim={claim}
              index={index}
              getVerdictClass={getVerdictClass}
              getStrengthClass={getStrengthClass}
              getUncertaintyClass={getUncertaintyClass}
              getStanceBadge={getStanceBadge}
            />
          ))
        )}
      </div>

      {/* System Disclaimer & Limitations */}
      <div className="v2-disclaimer-card">
        <div className="disclaimer-title">System Scope & Evidence Limitations</div>
        <p className="disclaimer-body">
          {disclaimer ||
            "Verification is based on aggregated live news, fact-check databases, and reference encyclopedias. UNVERIFIED claims do not imply falsity, but rather an absence of conclusive external reporting."}
        </p>
        <p className="disclaimer-sub">
          Evidence availability directly affects verification. The system does not claim to establish absolute objective truth; it reflects the corroboration or refutation found in publicly indexed sources.
        </p>
      </div>
    </div>
  );
};

const ClaimCard = ({ claim, index, getVerdictClass, getStrengthClass, getUncertaintyClass, getStanceBadge }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const {
    text,
    verdict,
    reasoning,
    evidence_strength,
    uncertainty_level,
    has_conflicting_evidence,
    supporting_evidence_count,
    contradicting_evidence_count,
    neutral_evidence_count,
    semantic_relation,
    evidence,
    linguistic_signal
  } = claim;

  const fcEvidence = evidence ? evidence.filter((e) => e.source_type === "FACT_CHECK_API") : [];
  const newsEvidence = evidence ? evidence.filter((e) => e.source_type === "LIVE_NEWS_SEARCH") : [];
  const refEvidence = evidence ? evidence.filter((e) => e.source_type === "GENERAL_REFERENCE") : [];
  const totalEvidenceCount = evidence ? evidence.length : 0;

  return (
    <div className="claim-card">
      <div className="claim-header" onClick={() => setIsExpanded(!isExpanded)} role="button" tabIndex={0}>
        <div className="claim-title-area">
          <span className="claim-number">Claim #{index + 1}</span>
          <p className="claim-text">"{text}"</p>
        </div>

        <div className="claim-meta-tags">
          <span className={`verdict-pill ${getVerdictClass(verdict)}`}>{verdict}</span>
          {semantic_relation && (
            <span className="meta-pill semantic-rel-pill">
              NLI: {semantic_relation}
            </span>
          )}
          <span className={`meta-pill ${getStrengthClass(evidence_strength)}`}>
            Strength: {evidence_strength}
          </span>
          <span className={`meta-pill ${getUncertaintyClass(uncertainty_level)}`}>
            Uncertainty: {uncertainty_level}
          </span>
          <button type="button" className="expand-toggle-btn" aria-label="Toggle claim details">
            {isExpanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="claim-body">
          {/* Deterministic Reasoning */}
          <div className="reasoning-box">
            <strong>Verification Reasoning:</strong> {reasoning}
          </div>

          {/* Evidence Counts Pill Breakdown */}
          {totalEvidenceCount > 0 && (
            <div className="evidence-counts-row">
              <span className="count-pill count-supports">
                Supports: {supporting_evidence_count}
              </span>
              <span className="count-pill count-contradicts">
                Contradicts: {contradicting_evidence_count}
              </span>
              <span className="count-pill count-neutral">
                Neutral: {neutral_evidence_count}
              </span>
            </div>
          )}

          {/* Special Situation Banners */}
          {has_conflicting_evidence && (
            <div className="claim-alert alert-conflict">
              <strong>⚠️ Conflicting evidence found:</strong> Both supporting and contradicting sources were retrieved for this claim. Review individual evidence items below.
            </div>
          )}

          {verdict === "UNVERIFIED" && totalEvidenceCount === 0 && (
            <div className="claim-alert alert-no-evidence">
              <strong>No sufficiently relevant external evidence found.</strong> No independent fact-checks, live news coverage, or encyclopedia articles were matched for this claim. It remains UNVERIFIED due to evidence absence (which does not mean false).
            </div>
          )}

          {/* Per-Claim Linguistic Signal */}
          {linguistic_signal && (
            <div className="claim-linguistic-signal">
              <span className="signal-badge-label">Linguistic Signal (V1 SVM):</span>
              <span className="signal-badge-val">
                {linguistic_signal.prediction} ({linguistic_signal.confidence.toFixed(1)}% margin)
              </span>
            </div>
          )}

          {/* Evidence Items Section */}
          {totalEvidenceCount > 0 && (
            <div className="evidence-sections-wrapper">
              <h4 className="evidence-heading">
                Retrieved Evidence ({totalEvidenceCount} items: {fcEvidence.length} Fact-Checks, {newsEvidence.length} Live News, {refEvidence.length} References)
              </h4>

              {/* Fact Check Evidence List */}
              {fcEvidence.length > 0 && (
                <div className="evidence-group">
                  <h5 className="group-title">🔍 Fact-Check Reports ({fcEvidence.length})</h5>
                  <div className="evidence-grid">
                    {fcEvidence.map((item, idx) => (
                      <EvidenceCard key={item.id || idx} item={item} getStanceBadge={getStanceBadge} />
                    ))}
                  </div>
                </div>
              )}

              {/* Live News Evidence List */}
              {newsEvidence.length > 0 && (
                <div className="evidence-group">
                  <h5 className="group-title">📰 Live News Coverage ({newsEvidence.length})</h5>
                  <div className="evidence-grid">
                    {newsEvidence.map((item, idx) => (
                      <EvidenceCard key={item.id || idx} item={item} getStanceBadge={getStanceBadge} />
                    ))}
                  </div>
                </div>
              )}

              {/* General Reference Evidence List */}
              {refEvidence.length > 0 && (
                <div className="evidence-group">
                  <h5 className="group-title">📚 Reference Knowledge Base ({refEvidence.length})</h5>
                  <div className="evidence-grid">
                    {refEvidence.map((item, idx) => (
                      <EvidenceCard key={item.id || idx} item={item} getStanceBadge={getStanceBadge} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const EvidenceCard = ({ item, getStanceBadge }) => {
  const getSourceTypeLabel = (sourceType) => {
    switch (sourceType) {
      case "FACT_CHECK_API":
        return "Fact Check API";
      case "LIVE_NEWS_SEARCH":
        return "Live News Search";
      case "GENERAL_REFERENCE":
        return "General Reference (Wikipedia)";
      default:
        return sourceType;
    }
  };

  return (
    <div className="evidence-item-card">
      <div className="evidence-item-header">
        <div className="publisher-info">
          <span className="publisher-name">{item.publisher || item.domain}</span>
          {item.publish_date && <span className="publish-date">• {item.publish_date}</span>}
        </div>
        {getStanceBadge(item.stance)}
      </div>

      <h5 className="evidence-title">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="evidence-link"
        >
          {item.title || "External Source"} ↗
        </a>
      </h5>

      {item.snippet && <p className="evidence-snippet">"{item.snippet}"</p>}

      <div className="evidence-footer">
        <span className="source-type-tag">
          {getSourceTypeLabel(item.source_type)}
        </span>

        {item.claim_reviewed && (
          <span className="claim-reviewed-tag">
            Reviewed: "{item.claim_reviewed}"
          </span>
        )}

        {item.raw_rating && (
          <span className="raw-rating-tag">
            Rating: <strong>{item.raw_rating}</strong>
          </span>
        )}
      </div>
    </div>
  );
};

export default V2VerificationResult;
