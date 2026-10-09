import React, { useState, useEffect } from "react";
import { getRadarFeed } from "../api";

export default function RadarView({ onVerifyStory }) {
  const [radarData, setRadarData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [verifyingId, setVerifyingId] = useState(null);

  useEffect(() => {
    fetchFeed(selectedCategory);
  }, [selectedCategory]);

  const fetchFeed = async (cat = "All") => {
    setLoading(true);
    setError("");
    try {
      const data = await getRadarFeed(cat);
      setRadarData(data);
    } catch (err) {
      setError(err.message || "Failed to load breaking news radar stream.");
    } finally {
      setLoading(false);
    }
  };

  const handleAuditClick = (item) => {
    setVerifyingId(item.id);
    if (onVerifyStory) {
      onVerifyStory({
        title: item.title,
        text: item.prefilled_query || item.summary,
      });
    }
  };

  const categories = [
    { label: "🔥 All Trending", val: "All" },
    { label: "🌍 World & Politics", val: "World & Politics" },
    { label: "🤖 Tech & AI", val: "Tech & AI" },
    { label: "🧬 Science & Health", val: "Science & Health" },
    { label: "📈 Markets & Finance", val: "Markets & Finance" },
  ];

  return (
    <div className="radar-page-container">
      {/* Header */}
      <div className="radar-header">
        <div className="radar-pill">
          <span className="live-dot pulse-amber"></span>
          <span>Live Detection Stream</span>
        </div>
        <h1 className="radar-title">Breaking News Radar & Viral Claims</h1>
        <p className="radar-subtitle">
          Autonomous real-time stream tracking surging viral claims, breaking headlines, and unverified rumors across global media networks.
        </p>
      </div>

      {/* Control Bar: Categories & Refresh */}
      <div className="radar-controls-bar">
        <div className="radar-category-pills">
          {categories.map((c) => (
            <button
              key={c.val}
              type="button"
              className={`radar-cat-btn ${selectedCategory === c.val ? "active" : ""}`}
              onClick={() => setSelectedCategory(c.val)}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="radar-meta-controls">
          {radarData?.last_updated && (
            <span className="radar-updated-tag">
              Updated: {radarData.last_updated.split(" ")[1]} UTC
            </span>
          )}
          <button
            type="button"
            className="radar-refresh-btn"
            onClick={() => fetchFeed(selectedCategory)}
            disabled={loading}
            title="Refresh breaking news stream"
          >
            <span className={loading ? "spin-icon" : ""}>🔄</span> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="radar-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" onClick={() => fetchFeed(selectedCategory)} className="retry-btn">
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="radar-loading-container">
          <div className="radar-pulse-ring"></div>
          <p className="radar-loading-text">Scanning global news feeds & viral networks...</p>
        </div>
      ) : !radarData?.items?.length ? (
        <div className="radar-empty-box">
          <span className="radar-empty-icon">📡</span>
          <h3>No active stories in this category right now</h3>
          <p>Try switching to "All Trending" or refresh the feed.</p>
          <button
            type="button"
            className="btn-reset-filters"
            onClick={() => setSelectedCategory("All")}
          >
            View All Trending
          </button>
        </div>
      ) : (
        /* Stories Grid */
        <div className="radar-stories-grid">
          {radarData.items.map((item) => {
            const isHigh = item.velocity === "HIGH";
            const isSurging = item.velocity === "SURGING";

            return (
              <div
                key={item.id}
                className={`radar-story-card ${item.disputed_flag ? "card-disputed" : ""}`}
              >
                {/* Card Top: Category, Velocity, Timestamp */}
                <div className="story-card-top">
                  <div className="story-badge-cluster">
                    <span className="story-category-tag">{item.category}</span>
                    <span
                      className={`story-velocity-pill ${
                        isHigh ? "velocity-high" : isSurging ? "velocity-surging" : "velocity-mod"
                      }`}
                    >
                      {isHigh ? "🔥 High Velocity" : isSurging ? "⚡ Surging" : "📈 Active"}
                    </span>
                    {item.disputed_flag && (
                      <span className="story-disputed-tag" title="Flagged as unverified or disputed rumor">
                        ⚠️ Disputed Rumor
                      </span>
                    )}
                  </div>
                  <span className="story-time-tag">{item.published_time}</span>
                </div>

                {/* Headline */}
                <h3 className="story-card-title">{item.title}</h3>

                {/* Summary */}
                <p className="story-card-summary">{item.summary}</p>

                {/* Card Bottom: Origin Preview & Action Button */}
                <div className="story-card-bottom">
                  <div className="story-origin">
                    <span className="origin-label">Source Context:</span>
                    <span className="origin-val">{item.source_preview}</span>
                  </div>

                  <button
                    type="button"
                    className="audit-story-btn"
                    onClick={() => handleAuditClick(item)}
                    disabled={verifyingId === item.id}
                  >
                    {verifyingId === item.id ? (
                      <>
                        <span className="btn-spinner"></span> Launching Audit...
                      </>
                    ) : (
                      <>
                        <span>⚡ Verify Story</span>
                        <span className="audit-arrow">→</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
