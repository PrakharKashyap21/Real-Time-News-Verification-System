import React from "react";

const EmptyState = ({ onSelectSample }) => {
  return (
    <div className="card overview-card">
      <div className="overview-header">
        <div className="engine-badge">
          <span className="pulse-dot"></span>
          <span>TruthLens Autonomous Verification Engine</span>
        </div>
        <h2 className="overview-title">How TruthLens Verifies Live News</h2>
        <p className="overview-desc">
          TruthLens AI conducts automated, multi-source investigative fact-checking in real time by synthesizing live search, deep web scraping, and generative AI reasoning.
        </p>
      </div>

      <div className="pipeline-grid">
        <div className="pipeline-step-card">
          <div className="step-number">01</div>
          <div className="step-icon">🌐</div>
          <h4 className="step-title">Live News Retrieval</h4>
          <p className="step-desc">
            Dispatches live search queries across reputable news outlets, official archives, and investigative journalism portals.
          </p>
        </div>

        <div className="pipeline-step-card">
          <div className="step-number">02</div>
          <div className="step-icon">📑</div>
          <h4 className="step-title">Deep Full-Text Extraction</h4>
          <p className="step-desc">
            Extracts full article body paragraphs concurrently to inspect detailed reporting beyond superficial headlines.
          </p>
        </div>

        <div className="pipeline-step-card">
          <div className="step-number">03</div>
          <div className="step-icon">🧠</div>
          <h4 className="step-title">Gemini Reasoning & NLI</h4>
          <p className="step-desc">
            Decomposes multi-sentence claims, matches specific propositions against evidence, and classifies corroborating vs contradictory stances.
          </p>
        </div>

        <div className="pipeline-step-card">
          <div className="step-number">04</div>
          <div className="step-icon">🛡️</div>
          <h4 className="step-title">Attributed Verdicts</h4>
          <p className="step-desc">
            Produces structured transparent reports with direct quotes, domain credibility indicators, and exact source citations.
          </p>
        </div>
      </div>

      <div className="verdict-legend">
        <div className="legend-title">Understanding Verdict Ratings:</div>
        <div className="legend-items">
          <div className="legend-item supported">
            <span className="legend-dot"></span>
            <strong>SUPPORTED:</strong> Confirmed by authoritative reporting.
          </div>
          <div className="legend-item contradicted">
            <span className="legend-dot"></span>
            <strong>CONTRADICTED:</strong> Debunked or refuted by evidence.
          </div>
          <div className="legend-item misleading">
            <span className="legend-dot"></span>
            <strong>MISLEADING:</strong> Partial truths mixed with false context.
          </div>
          <div className="legend-item unverified">
            <span className="legend-dot"></span>
            <strong>UNVERIFIED:</strong> Inconclusive or unindexed external reporting.
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmptyState;
