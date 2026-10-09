import React from "react";

const ArchitectureSection = () => {
  return (
    <section className="architecture-section" id="how-it-works">
      <div className="arch-header">
        <span className="arch-pill">System Architecture</span>
        <h2 className="arch-title">Autonomous Real-Time Verification Engine</h2>
        <p className="arch-subtitle">
          How TruthLens AI eliminates hallucinations and verifies facts in sub-4 seconds using Agentic RAG.
        </p>
      </div>

      <div className="arch-grid">
        <div className="arch-card">
          <div className="arch-card-badge">01</div>
          <div className="arch-card-icon">⚡</div>
          <h3 className="arch-card-title">Live DuckDuckGo Search</h3>
          <p className="arch-card-desc">
            Dispatches targeted search queries across live breaking news, official archives, and investigative journalism portals.
          </p>
        </div>

        <div className="arch-card">
          <div className="arch-card-badge">02</div>
          <div className="arch-card-icon">📑</div>
          <h3 className="arch-card-title">Concurrent Deep Extraction</h3>
          <p className="arch-card-desc">
            Scrapes complete article body paragraphs via Trafilatura in parallel with strict timeouts to avoid surface-level summaries.
          </p>
        </div>

        <div className="arch-card">
          <div className="arch-card-badge">03</div>
          <div className="arch-card-icon">🧠</div>
          <h3 className="arch-card-title">Gemini AI Synthesis</h3>
          <p className="arch-card-desc">
            Deconstructs claims into core propositions, evaluates corroborating vs contradictory stances, and flags distortions.
          </p>
        </div>

        <div className="arch-card">
          <div className="arch-card-badge">04</div>
          <div className="arch-card-icon">🛡️</div>
          <h3 className="arch-card-title">Attributed Citations</h3>
          <p className="arch-card-desc">
            Provides 100% transparent evidence cards with exact quotes, publisher domains, and direct external source links.
          </p>
        </div>
      </div>

      <div className="ratings-legend-card">
        <h4 className="legend-heading">Verdict Taxonomy</h4>
        <div className="legend-grid">
          <div className="legend-box supported">
            <span className="legend-status-dot"></span>
            <div>
              <strong>SUPPORTED</strong>
              <p>Confirmed by authoritative news and verified official statements.</p>
            </div>
          </div>
          <div className="legend-box contradicted">
            <span className="legend-status-dot"></span>
            <div>
              <strong>CONTRADICTED</strong>
              <p>Refuted or proven false by credible reporting and archives.</p>
            </div>
          </div>
          <div className="legend-box misleading">
            <span className="legend-status-dot"></span>
            <div>
              <strong>MISLEADING</strong>
              <p>Contains factual distortions, missing context, or cherry-picked quotes.</p>
            </div>
          </div>
          <div className="legend-box unverified">
            <span className="legend-status-dot"></span>
            <div>
              <strong>UNVERIFIED</strong>
              <p>Inconclusive due to an absence of indexed external journalism.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ArchitectureSection;
