import React, { useState, useEffect } from "react";
import { getAnalyticsData } from "../api";

export default function AnalyticsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTierFilter, setSelectedTierFilter] = useState("ALL");

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async (query = "") => {
    setLoading(true);
    setError("");
    try {
      const res = await getAnalyticsData(query);
      setData(res);
    } catch (err) {
      setError(err.message || "Failed to load analytics dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchAnalytics(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    fetchAnalytics("");
  };

  const filteredCatalog = (data?.domain_catalog || []).filter((item) => {
    if (selectedTierFilter === "ALL") return true;
    if (selectedTierFilter === "TIER_0" && item.tier.includes("Tier-0")) return true;
    if (selectedTierFilter === "TIER_1" && item.tier.includes("Tier-1")) return true;
    if (selectedTierFilter === "TIER_2" && (item.tier.includes("Tier-2") || item.tier.includes("Fact-Checker"))) return true;
    if (selectedTierFilter === "TIER_3" && item.tier.includes("Tier-3")) return true;
    if (selectedTierFilter === "TIER_4" && item.tier.includes("Tier-4")) return true;
    return true;
  });

  return (
    <div className="analytics-page-container">
      {/* Header Section */}
      <div className="analytics-header">
        <div className="analytics-pill">
          <span className="live-dot pulse-teal"></span>
          <span>Source Diversity & Veracity Telemetry</span>
        </div>
        <h1 className="analytics-title">Trust Intelligence & Domain Registry</h1>
        <p className="analytics-subtitle">
          Real-time metrics, credibility categorization, and multi-source attribution benchmarks powering TruthLens AI’s agentic verification engine.
        </p>
      </div>

      {error && (
        <div className="analytics-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" onClick={() => fetchAnalytics(searchQuery)} className="retry-btn">
            Retry
          </button>
        </div>
      )}

      {/* KPI Engine Telemetry Row */}
      {data?.engine_metrics && (
        <div className="analytics-kpi-grid">
          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-icon">⚡</span>
              <span className="kpi-label">Avg Retrieval Latency</span>
            </div>
            <div className="kpi-value">
              {(data.engine_metrics.avg_retrieval_latency_ms / 1000).toFixed(2)}s
            </div>
            <div className="kpi-footnote">Concurrent DDG + Trafilatura RAG</div>
          </div>

          <div className="kpi-card highlight-green">
            <div className="kpi-header">
              <span className="kpi-icon">🎯</span>
              <span className="kpi-label">Benchmark Accuracy</span>
            </div>
            <div className="kpi-value">{data.engine_metrics.benchmark_accuracy_pct}%</div>
            <div className="kpi-footnote">Tested on 111 Ground-Truth Claims</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-icon">🛡️</span>
              <span className="kpi-label">Attribution Purity</span>
            </div>
            <div className="kpi-value">{data.engine_metrics.zero_hallucination_attribution_rate}%</div>
            <div className="kpi-footnote">Zero-hallucination quote constraint</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <span className="kpi-icon">🌐</span>
              <span className="kpi-label">Tracked Domains</span>
            </div>
            <div className="kpi-value">{data.total_tracked_domains}+</div>
            <div className="kpi-footnote">Tiered domain catalog with bias tracking</div>
          </div>
        </div>
      )}

      {/* Stance Distribution Gauge Bar */}
      {data?.stance_distribution && (
        <div className="stance-distribution-card">
          <div className="stance-dist-header">
            <div>
              <h2 className="stance-dist-title">Multi-Source Stance Distribution</h2>
              <p className="stance-dist-desc">
                Aggregate cross-domain consensus across verified real-time claims and articles
              </p>
            </div>
            <div className="stance-badges">
              <span className="badge-legend corroborates">
                <span className="legend-dot green"></span> Corroborating ({data.stance_distribution.corroborates_pct}%)
              </span>
              <span className="badge-legend refutes">
                <span className="legend-dot red"></span> Refuting ({data.stance_distribution.refutes_pct}%)
              </span>
              <span className="badge-legend contextual">
                <span className="legend-dot blue"></span> Neutral / Contextual ({data.stance_distribution.contextual_neutral_pct}%)
              </span>
            </div>
          </div>

          <div className="multi-progress-bar">
            <div
              className="progress-segment corroborates-bar"
              style={{ width: `${data.stance_distribution.corroborates_pct}%` }}
              title={`Corroborates: ${data.stance_distribution.corroborates_pct}%`}
            />
            <div
              className="progress-segment refutes-bar"
              style={{ width: `${data.stance_distribution.refutes_pct}%` }}
              title={`Refutes: ${data.stance_distribution.refutes_pct}%`}
            />
            <div
              className="progress-segment contextual-bar"
              style={{ width: `${data.stance_distribution.contextual_neutral_pct}%` }}
              title={`Contextual: ${data.stance_distribution.contextual_neutral_pct}%`}
            />
          </div>
        </div>
      )}

      {/* Credibility Hierarchy Tiers */}
      {data?.credibility_tiers && (
        <div className="credibility-hierarchy-section">
          <div className="section-title-wrap">
            <h2 className="analytics-section-title">Credibility Hierarchy & Sourcing Matrix</h2>
            <span className="section-badge">Algorithmic Weighting</span>
          </div>

          <div className="tier-cards-grid">
            {data.credibility_tiers.map((tier, idx) => (
              <div key={idx} className={`tier-card tier-card-${idx}`}>
                <div className="tier-card-top">
                  <span className="tier-badge-pill">{tier.trust_badge}</span>
                  <span className="tier-score-range">{tier.score_range}</span>
                </div>
                <h3 className="tier-name">{tier.tier_name}</h3>
                <p className="tier-desc">{tier.description}</p>
                <div className="tier-footer">
                  <span className="tier-count">Cataloged: {tier.domains_count} outlets</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Domain Registry Search & Table Section */}
      <div className="domain-registry-section">
        <div className="registry-controls-header">
          <div>
            <h2 className="analytics-section-title">Domain Trust Index</h2>
            <p className="registry-subtitle">
              Inspect veracity profiles, bias tendencies, and verification tiers of crawled publishers.
            </p>
          </div>

          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="registry-search-form">
            <input
              type="text"
              placeholder="Filter domain (e.g. reuters, bbc, onion)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="registry-search-input"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="clear-search-btn"
                title="Clear filter"
              >
                ✕
              </button>
            )}
            <button type="submit" className="search-submit-btn">
              Search
            </button>
          </form>
        </div>

        {/* Tier Filter Pills */}
        <div className="tier-filter-pills">
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "ALL" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("ALL")}
          >
            All Outlets ({data?.domain_catalog?.length || 0})
          </button>
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "TIER_0" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("TIER_0")}
          >
            🏛️ Tier-0 Archives
          </button>
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "TIER_1" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("TIER_1")}
          >
            📡 Tier-1 Wires
          </button>
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "TIER_2" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("TIER_2")}
          >
            🔍 Fact-Checkers
          </button>
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "TIER_3" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("TIER_3")}
          >
            📰 Major Press
          </button>
          <button
            type="button"
            className={`filter-pill ${selectedTierFilter === "TIER_4" ? "active" : ""}`}
            onClick={() => setSelectedTierFilter("TIER_4")}
          >
            🎭 Parody / Satire
          </button>
        </div>

        {/* Domain Cards Grid */}
        {loading ? (
          <div className="analytics-loading-state">
            <div className="loading-spinner"></div>
            <p>Retrieving trust telemetry from TruthLens knowledge graph...</p>
          </div>
        ) : filteredCatalog.length === 0 ? (
          <div className="empty-catalog-box">
            <span className="empty-icon">🔍</span>
            <h3>No matching domains found</h3>
            <p>Try searching for another domain name or clear your filters.</p>
            <button type="button" onClick={handleClearSearch} className="btn-reset-filters">
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="domain-cards-grid">
            {filteredCatalog.map((item, idx) => {
              const isParody = item.tier.includes("Tier-4") || item.credibility_score < 0.3;
              const isHighTrust = item.credibility_score >= 0.95;
              const pct = Math.round(item.credibility_score * 100);

              return (
                <div key={idx} className={`domain-intel-card ${isParody ? "card-parody" : ""}`}>
                  <div className="domain-card-top">
                    <div className="domain-identity">
                      <div className={`domain-avatar ${isParody ? "avatar-parody" : ""}`}>
                        {item.name.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h4 className="domain-name">{item.name}</h4>
                        <a
                          href={`https://${item.domain}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="domain-url-link"
                        >
                          {item.domain} ↗
                        </a>
                      </div>
                    </div>

                    <div className="score-badge-wrap">
                      <span className={`cred-score-pill ${isParody ? "low-score" : isHighTrust ? "high-score" : "mid-score"}`}>
                        {pct}% Trust
                      </span>
                    </div>
                  </div>

                  <p className="domain-desc">{item.description}</p>

                  <div className="domain-meta-row">
                    <div className="meta-item">
                      <span className="meta-label">Category</span>
                      <span className="meta-value">{item.category}</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Stance Bias</span>
                      <span className="meta-value">{item.stance_bias}</span>
                    </div>
                  </div>

                  <div className="domain-card-footer">
                    <span className={`domain-tier-tag ${isParody ? "tag-parody" : ""}`}>
                      {item.tier}
                    </span>
                    {item.fact_check_certified ? (
                      <span className="cert-badge" title="Certified Fact-Checker or Primary Archive">
                        ✓ Certified
                      </span>
                    ) : isParody ? (
                      <span className="parody-badge">⚠️ Fictional</span>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
