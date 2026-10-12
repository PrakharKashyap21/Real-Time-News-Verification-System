import React from "react";
import {
  ClockIcon,
  BookOpenIcon,
  CheckCircleIcon,
  XCircleIcon,
  AlertTriangleIcon,
  HelpCircleIcon
} from "./Icons";

const RecentHistory = ({ history, onSelectHistoryItem, onClearHistory, onDeleteItem, activeId }) => {
  if (!history || history.length === 0) {
    return (
      <div className="card history-card empty-history">
        <div className="history-header">
          <div className="history-title-group">
            <span className="history-icon" style={{ display: "inline-flex", alignItems: "center" }}>
              <ClockIcon size={16} style={{ color: "#38bdf8" }} />
            </span>
            <h3 className="history-title">Recent Verifications</h3>
          </div>
        </div>
        <p className="empty-history-text">
          No previous verifications yet. Verified claims and articles will be saved here for quick review.
        </p>
      </div>
    );
  }

  const getBadgeClass = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return "badge-supported";
      case "CONTRADICTED":
        return "badge-contradicted";
      case "MISLEADING":
        return "badge-misleading";
      case "UNVERIFIED":
      default:
        return "badge-unverified";
    }
  };

  const getVerdictIcon = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return <CheckCircleIcon size={12} style={{ color: "#10b981", verticalAlign: "middle" }} />;
      case "CONTRADICTED":
        return <XCircleIcon size={12} style={{ color: "#ef4444", verticalAlign: "middle" }} />;
      case "MISLEADING":
        return <AlertTriangleIcon size={12} style={{ color: "#f59e0b", verticalAlign: "middle" }} />;
      case "UNVERIFIED":
      default:
        return <HelpCircleIcon size={12} style={{ color: "#94a3b8", verticalAlign: "middle" }} />;
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return "Just now";
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div className="card history-card">
      <div className="history-header">
        <div className="history-title-group">
          <span className="history-icon" style={{ display: "inline-flex", alignItems: "center" }}>
            <ClockIcon size={16} style={{ color: "#38bdf8" }} />
          </span>
          <h3 className="history-title">Recent Verifications</h3>
          <span className="history-count">{history.length}</span>
        </div>
        <button
          type="button"
          className="history-clear-btn"
          onClick={onClearHistory}
          title="Clear all saved verifications"
        >
          Clear
        </button>
      </div>

      <div className="history-list">
        {history.map((item) => {
          const isActive = activeId === item.id;
          const displayTitle = item.title || item.text.slice(0, 60) + (item.text.length > 60 ? "..." : "");
          return (
            <div
              key={item.id}
              className={`history-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectHistoryItem(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelectHistoryItem(item)}
            >
              <div className="history-item-top">
                <span className={`history-verdict-badge ${getBadgeClass(item.result?.overall_assessment)}`}>
                  {getVerdictIcon(item.result?.overall_assessment)} {item.result?.overall_assessment || "VERIFIED"}
                </span>
                <span className="history-item-time">{formatTimestamp(item.timestamp)}</span>
              </div>
              <div className="history-item-title">{displayTitle}</div>
              <div className="history-item-footer">
                <span className="history-item-sources" style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                  <BookOpenIcon size={12} style={{ color: "#818cf8" }} /> {(item.result?.claims || []).flatMap((c) => c.evidence || []).length} sources
                </span>
                <button
                  type="button"
                  className="history-delete-item-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteItem(item.id);
                  }}
                  title="Remove from history"
                  aria-label="Delete history item"
                >
                  ✕
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RecentHistory;
