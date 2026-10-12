import React from "react";
import {
  ClockIcon,
  SearchGraphIcon,
  BookOpenIcon,
  CheckCircleIcon,
  XCircleIcon,
  AlertTriangleIcon,
  HelpCircleIcon
} from "./Icons";

const HistoryDrawer = ({ isOpen, onClose, history, onSelectHistoryItem, onClearHistory, onDeleteItem, activeId }) => {
  if (!isOpen) return null;

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
    <div className="drawer-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="drawer-icon" style={{ display: "inline-flex", alignItems: "center" }}>
              <ClockIcon size={16} style={{ color: "#38bdf8" }} />
            </span>
            <h3 className="drawer-title">Verification History</h3>
            <span className="drawer-badge">{history.length}</span>
          </div>
          <div className="drawer-actions">
            {history.length > 0 && (
              <button
                type="button"
                className="drawer-clear-btn"
                onClick={onClearHistory}
                title="Clear all history"
              >
                Clear All
              </button>
            )}
            <button
              type="button"
              className="drawer-close-btn"
              onClick={onClose}
              aria-label="Close history drawer"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="drawer-content">
          {history.length === 0 ? (
            <div className="drawer-empty-state">
              <span className="drawer-empty-icon" style={{ display: "inline-flex", justifyContent: "center" }}>
                <SearchGraphIcon size={36} style={{ color: "#64748b" }} />
              </span>
              <p className="drawer-empty-title">No verifications yet</p>
              <p className="drawer-empty-desc">
                Whenever you fact-check a news claim or article URL, it will be saved here for instant recall.
              </p>
            </div>
          ) : (
            <div className="drawer-list">
              {history.map((item) => {
                const isActive = activeId === item.id;
                const displayTitle = item.title || item.text.slice(0, 75) + (item.text.length > 75 ? "..." : "");
                const sourcesCount = (item.result?.claims || []).flatMap((c) => c.evidence || []).length;

                return (
                  <div
                    key={item.id}
                    className={`drawer-item ${isActive ? "active" : ""}`}
                    onClick={() => {
                      onSelectHistoryItem(item);
                      onClose();
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="drawer-item-top">
                      <span className={`drawer-verdict-badge ${getBadgeClass(item.result?.overall_assessment)}`}>
                        {getVerdictIcon(item.result?.overall_assessment)} {item.result?.overall_assessment || "VERIFIED"}
                      </span>
                      <span className="drawer-item-time">{formatTimestamp(item.timestamp)}</span>
                    </div>

                    <div className="drawer-item-title">{displayTitle}</div>

                    <div className="drawer-item-footer">
                      <span className="drawer-item-sources" style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <BookOpenIcon size={12} style={{ color: "#818cf8" }} /> {sourcesCount} verified {sourcesCount === 1 ? "source" : "sources"}
                      </span>
                      <button
                        type="button"
                        className="drawer-delete-item-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteItem(item.id);
                        }}
                        title="Delete item"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryDrawer;
