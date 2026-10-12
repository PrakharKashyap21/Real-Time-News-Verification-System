import React, { useState, useEffect, useRef } from "react";
import { getRadarFeed } from "../api";

export default function RadarView({ onVerifyStory }) {
  const [radarData, setRadarData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedCountry, setSelectedCountry] = useState("IN");
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [verifyingId, setVerifyingId] = useState(null);
  const [justUpdated, setJustUpdated] = useState(false);

  // Approach A: Pending new stories notification state
  const [pendingNewData, setPendingNewData] = useState(null);
  const [pendingNewCount, setPendingNewCount] = useState(0);

  const selectedCategoryRef = useRef(selectedCategory);
  selectedCategoryRef.current = selectedCategory;

  const selectedCountryRef = useRef(selectedCountry);
  selectedCountryRef.current = selectedCountry;

  const radarDataRef = useRef(radarData);
  radarDataRef.current = radarData;

  const COUNTRIES = [
    { code: "IN", name: "India", flag: "🇮🇳" },
    { code: "US", name: "United States", flag: "🇺🇸" },
    { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
    { code: "GL", name: "Global Edition", flag: "🌍" },
  ];

  const categories = [
    { label: "🔥 All Trending", val: "All" },
    { label: "🌍 World & Politics", val: "World & Politics" },
    { label: "🤖 Tech & AI", val: "Tech & AI" },
    { label: "🧬 Science & Health", val: "Science & Health" },
    { label: "📈 Markets & Finance", val: "Markets & Finance" },
  ];

  // Fetch when category or country changes
  useEffect(() => {
    fetchFeed(selectedCategory, selectedCountry, false, false, false);
    setPendingNewData(null);
    setPendingNewCount(0);
  }, [selectedCategory, selectedCountry]);

  // Silent Background Polling Engine (Every 30s)
  useEffect(() => {
    const interval = setInterval(() => {
      // Trigger silent background poll with rotation without touching manual refresh state
      fetchFeed(selectedCategoryRef.current, selectedCountryRef.current, true, false, true);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Client-Side Live Relative Timestamp Engine (ticks every 10 seconds)
  useEffect(() => {
    const timer = setInterval(() => {
      setRadarData((prev) => {
        if (!prev || !prev.items) return prev;
        const now = new Date();
        const updatedItems = prev.items.map((item) => {
          if (!item.pub_date_iso) return item;
          try {
            const pubDate = new Date(item.pub_date_iso);
            const diffMins = Math.max(0, Math.floor((now - pubDate) / 60000));
            let timeStr = "Just now";
            if (diffMins >= 1 && diffMins < 60) {
              timeStr = `${diffMins}m ago`;
            } else if (diffMins >= 60 && diffMins < 1440) {
              timeStr = `${Math.floor(diffMins / 60)}h ago`;
            } else if (diffMins >= 1440) {
              timeStr = `${Math.floor(diffMins / 1440)}d ago`;
            }
            return { ...item, published_time: timeStr };
          } catch (e) {
            return item;
          }
        });
        return { ...prev, items: updatedItems };
      });
    }, 10000);

    return () => clearInterval(timer);
  }, []);

  const fetchFeed = async (
    cat = "All",
    ctry = selectedCountryRef.current,
    isBackground = false,
    isManualRefresh = false,
    rotate = false
  ) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else if (!isBackground) {
      setLoading(true);
    }
    setError("");

    try {
      const data = await getRadarFeed(cat, ctry, rotate);

      const currentItems = radarDataRef.current?.items || [];

      if (isBackground && currentItems.length > 0) {
        // Approach A: Check if any stories are new compared to current screen
        const currentTitles = new Set(
          currentItems.map((it) => (it.title || "").trim().toLowerCase())
        );
        const freshItems = (data.items || []).filter(
          (it) => it.title && !currentTitles.has(it.title.trim().toLowerCase())
        );

        if (freshItems.length > 0) {
          // Do not abruptly replace the cards; prompt the user gracefully with the floating banner!
          setPendingNewData(data);
          setPendingNewCount(freshItems.length);
        }
      } else {
        // Immediate user-initiated fetch / category switch / manual refresh
        setRadarData(data);
        setPendingNewData(null);
        setPendingNewCount(0);
        setJustUpdated(true);
        setTimeout(() => setJustUpdated(false), 2500);
      }
    } catch (err) {
      if (!isBackground) {
        setError(err.message || "Failed to load breaking news radar stream.");
      }
    } finally {
      if (!isBackground) {
        setLoading(false);
      }
      if (isManualRefresh) {
        setIsRefreshing(false);
      }
    }
  };

  const handleApplyPendingStories = () => {
    if (pendingNewData) {
      setRadarData(pendingNewData);
      setPendingNewData(null);
      setPendingNewCount(0);
      setJustUpdated(true);
      setTimeout(() => setJustUpdated(false), 2500);
      window.scrollTo({ top: 100, behavior: "smooth" });
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

  return (
    <div className="radar-page-container">
      {/* Header */}
      <div className="radar-header">
        <div className="radar-pill">
          <span className="live-dot pulse-amber"></span>
          <span>Live Detection Stream</span>
          <span className="radar-live-indicator" title="Stream continuously updating in background">
            ⚡ LIVE
          </span>
        </div>
        <h1 className="radar-title">Breaking News Radar & Viral Claims</h1>
        <p className="radar-subtitle">
          Autonomous real-time stream tracking surging viral claims, breaking headlines, and unverified rumors across global media networks.
        </p>
      </div>

      {/* Control Bar: Categories, Country Selector & Controls */}
      <div className="radar-controls-bar">
        {/* Categories Bar */}
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

        {/* Right Tools: Country Selector, Status & Refresh */}
        <div className="radar-meta-controls">
          {/* Country Regional Edition Selector */}
          <div className="radar-country-selector-wrapper" title="Select regional breaking news edition">
            <span className="country-globe-icon">🌐</span>
            <select
              className="radar-country-select"
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              aria-label="Select News Region"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.flag} {c.name}
                </option>
              ))}
            </select>
          </div>

          {radarData?.last_updated && (
            <span className="radar-updated-tag" title="Last feed synchronization time">
              Updated: {radarData.last_updated.split(" ")[1]} UTC
            </span>
          )}

          {justUpdated && (
            <span className="radar-flash-tag animate-fade">
              ✨ Fresh Stream
            </span>
          )}

          {/* Manual Refresh Button (rotates candidate buffer immediately) */}
          <button
            type="button"
            className="radar-refresh-btn"
            onClick={() => {
              fetchFeed(selectedCategory, selectedCountry, false, true, true);
            }}
            disabled={loading || isRefreshing}
            title="Rotate to fresh stories from buffer pool now"
          >
            <span className={isRefreshing ? "spin-icon" : ""}>🔄</span> Refresh
          </button>
        </div>
      </div>

      {/* Approach A: Floating New Stories Banner */}
      {pendingNewCount > 0 && (
        <div
          className="radar-new-stories-banner"
          onClick={handleApplyPendingStories}
          role="button"
          tabIndex={0}
          title="Click to display freshly retrieved stories"
        >
          <span className="radar-pill-dot pulse-emerald"></span>
          <span className="radar-banner-text">
            ✨ <strong>{pendingNewCount} New Breaking Stories</strong> Available — Click to view latest updates
          </span>
          <span className="radar-banner-action">View Stream ↑</span>
        </div>
      )}

      {error && (
        <div className="radar-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" onClick={() => fetchFeed(selectedCategory, selectedCountry, false, false, false)} className="retry-btn">
            Retry
          </button>
        </div>
      )}

      {/* Loading State for initial fetch */}
      {loading && !radarData ? (
        <div className="radar-loading-container">
          <div className="radar-pulse-ring"></div>
          <p className="radar-loading-text">
            Scanning {COUNTRIES.find((c) => c.code === selectedCountry)?.name || "regional"} live news feeds & viral networks...
          </p>
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
                  <span className="story-time-tag" title={item.pub_date_iso || ""}>
                    {item.published_time}
                  </span>
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
