import React, { useState, useMemo } from "react";

export default function EvidenceKnowledgeGraph({ claims = [], overallAssessment = "SUPPORTED" }) {
  const [selectedClaimIndex, setSelectedClaimIndex] = useState(0);
  const [selectedStanceFilter, setSelectedStanceFilter] = useState("ALL");
  const [activeNode, setActiveNode] = useState(null);

  const activeClaim = claims[selectedClaimIndex] || claims[0];

  // Extract evidence nodes for the selected claim
  const evidenceList = useMemo(() => {
    if (!activeClaim) return [];
    return activeClaim.evidence || [];
  }, [activeClaim]);

  // Filter evidence based on stance toggle
  const filteredEvidence = useMemo(() => {
    if (selectedStanceFilter === "ALL") return evidenceList;
    return evidenceList.filter((e) => e.stance?.toUpperCase() === selectedStanceFilter);
  }, [evidenceList, selectedStanceFilter]);

  // Layout calculation for SVG nodes
  const layout = useMemo(() => {
    const width = 860;
    const height = 480;
    const centerX = width / 2;
    const centerY = height / 2;
    const radiusX = 280;
    const radiusY = 145;

    const nodes = filteredEvidence.map((ev, i) => {
      const count = filteredEvidence.length;
      // Distribute evenly in an ellipse around center
      const angle = (2 * Math.PI * i) / (count || 1) - Math.PI / 2;
      const x = centerX + radiusX * Math.cos(angle);
      const y = centerY + radiusY * Math.sin(angle);
      return {
        ...ev,
        nodeId: `node_${i}`,
        x,
        y,
        stance: ev.stance?.toUpperCase() || "NEUTRAL",
      };
    });

    return { width, height, centerX, centerY, nodes };
  }, [filteredEvidence]);

  const getStanceColor = (stance) => {
    switch (stance) {
      case "SUPPORTS":
        return "#10b981"; // Emerald
      case "CONTRADICTS":
        return "#ef4444"; // Red
      case "NEUTRAL":
      default:
        return "#3b82f6"; // Blue
    }
  };

  const getVerdictGlow = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return "#10b981";
      case "CONTRADICTED":
        return "#ef4444";
      case "MISLEADING":
        return "#f59e0b";
      case "UNVERIFIED":
      default:
        return "#94a3b8";
    }
  };

  if (!claims || claims.length === 0) {
    return null;
  }

  return (
    <div className="evidence-graph-card">
      <div className="graph-card-header">
        <div className="graph-title-group">
          <div className="graph-pill">
            <span className="live-dot pulse-teal"></span>
            <span>Interactive Visual Intelligence</span>
          </div>
          <h3 className="graph-card-title">Evidence Network & Knowledge Graph</h3>
          <p className="graph-card-desc">
            Visual topology mapping verified claim assertions to external news wires, official archives, and investigative debunkers.
          </p>
        </div>

        {/* Claim Selector if multiple claims */}
        {claims.length > 1 && (
          <div className="graph-claim-selector">
            <span className="claim-select-label">Select Assertion:</span>
            <div className="claim-select-pills">
              {claims.map((c, idx) => (
                <button
                  key={c.claim_id || idx}
                  type="button"
                  className={`claim-pill-btn ${selectedClaimIndex === idx ? "active" : ""}`}
                  onClick={() => {
                    setSelectedClaimIndex(idx);
                    setActiveNode(null);
                  }}
                >
                  Claim #{idx + 1}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filter Toolbar */}
      <div className="graph-filter-bar">
        <div className="graph-stance-filters">
          <button
            type="button"
            className={`graph-filter-btn ${selectedStanceFilter === "ALL" ? "active" : ""}`}
            onClick={() => setSelectedStanceFilter("ALL")}
          >
            All Sources ({evidenceList.length})
          </button>
          <button
            type="button"
            className={`graph-filter-btn sup ${selectedStanceFilter === "SUPPORTS" ? "active" : ""}`}
            onClick={() => setSelectedStanceFilter("SUPPORTS")}
          >
            <span className="filter-dot green"></span> Corroborating (
            {evidenceList.filter((e) => e.stance?.toUpperCase() === "SUPPORTS").length})
          </button>
          <button
            type="button"
            className={`graph-filter-btn con ${selectedStanceFilter === "CONTRADICTS" ? "active" : ""}`}
            onClick={() => setSelectedStanceFilter("CONTRADICTS")}
          >
            <span className="filter-dot red"></span> Refuting (
            {evidenceList.filter((e) => e.stance?.toUpperCase() === "CONTRADICTS").length})
          </button>
          <button
            type="button"
            className={`graph-filter-btn neu ${selectedStanceFilter === "NEUTRAL" ? "active" : ""}`}
            onClick={() => setSelectedStanceFilter("NEUTRAL")}
          >
            <span className="filter-dot blue"></span> Context (
            {evidenceList.filter((e) => e.stance?.toUpperCase() === "NEUTRAL").length})
          </button>
        </div>

        <div className="graph-legend-hints">
          <span className="hint-label">Tip: Click any source node to inspect cited text</span>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="graph-canvas-container">
        {filteredEvidence.length === 0 ? (
          <div className="graph-empty-state">
            <span className="empty-graph-icon">🕸️</span>
            <p className="empty-graph-text">
              No evidence sources matched the current filter for this claim.
            </p>
            <button
              type="button"
              className="btn-reset-graph"
              onClick={() => setSelectedStanceFilter("ALL")}
            >
              Reset Filter
            </button>
          </div>
        ) : (
          <svg
            className="evidence-svg-canvas"
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              {/* Glow Filters */}
              <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              <filter id="glow-blue" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Connecting Edges */}
            <g className="edges-layer">
              {layout.nodes.map((node) => {
                const isSelected = activeNode?.id === node.id;
                const strokeColor = getStanceColor(node.stance);

                // Quadratic curve control point slightly bowed
                const midX = (layout.centerX + node.x) / 2;
                const midY = (layout.centerY + node.y) / 2;
                const controlX = midX + (layout.centerY - node.y) * 0.08;
                const controlY = midY + (node.x - layout.centerX) * 0.08;

                const pathData = `M ${layout.centerX} ${layout.centerY} Q ${controlX} ${controlY} ${node.x} ${node.y}`;

                return (
                  <g key={`edge_${node.nodeId}`}>
                    <path
                      d={pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isSelected ? 3 : 1.5}
                      strokeOpacity={isSelected ? 0.9 : 0.45}
                      strokeDasharray={isSelected ? "none" : "5,4"}
                      className={`edge-path ${isSelected ? "edge-active" : ""}`}
                    />
                    {/* Small pulse particle along edge */}
                    <circle
                      r={isSelected ? 3 : 2}
                      fill={strokeColor}
                      opacity={0.8}
                    >
                      <animateMotion
                        path={pathData}
                        dur={node.stance === "SUPPORTS" ? "3s" : "4s"}
                        repeatCount="indefinite"
                      />
                    </circle>
                  </g>
                );
              })}
            </g>

            {/* Central Claim Node */}
            <g
              className="center-claim-group"
              transform={`translate(${layout.centerX}, ${layout.centerY})`}
            >
              {/* Outer decorative ring */}
              <circle
                r="72"
                fill="none"
                stroke={getVerdictGlow(activeClaim?.verdict || overallAssessment)}
                strokeWidth="1.5"
                strokeOpacity="0.3"
                strokeDasharray="6,4"
              >
                <animateTransform
                  attributeName="transform"
                  type="rotate"
                  from="0"
                  to="360"
                  dur="40s"
                  repeatCount="indefinite"
                />
              </circle>

              {/* Central base node circle */}
              <circle
                r="56"
                fill="#0f172a"
                stroke={getVerdictGlow(activeClaim?.verdict || overallAssessment)}
                strokeWidth="2.5"
                filter={`drop-shadow(0 0 12px ${getVerdictGlow(
                  activeClaim?.verdict || overallAssessment
                )}40)`}
              />

              {/* Central Claim Label */}
              <text
                textAnchor="middle"
                y="-14"
                fill="#94a3b8"
                fontSize="9"
                fontWeight="700"
                letterSpacing="1"
              >
                VERIFIED CLAIM
              </text>
              <text
                textAnchor="middle"
                y="6"
                fill="#ffffff"
                fontSize="11"
                fontWeight="800"
              >
                {activeClaim?.verdict?.toUpperCase() || overallAssessment}
              </text>
              <text
                textAnchor="middle"
                y="22"
                fill="#64748b"
                fontSize="8.5"
                fontWeight="600"
              >
                {layout.nodes.length} Connected Sources
              </text>
            </g>

            {/* Evidence Source Nodes */}
            <g className="evidence-nodes-layer">
              {layout.nodes.map((node) => {
                const isSelected = activeNode?.id === node.id;
                const color = getStanceColor(node.stance);
                const publisherName = node.publisher || node.domain || "News";
                const shortName =
                  publisherName.length > 14
                    ? publisherName.substring(0, 13) + "…"
                    : publisherName;

                return (
                  <g
                    key={node.nodeId}
                    className={`evidence-node-item ${isSelected ? "selected-node" : ""}`}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveNode(node);
                    }}
                  >
                    {/* Invisible expanded hit target for effortless 1-click selection */}
                    <circle
                      r="46"
                      fill="transparent"
                      className="node-hit-target"
                    />

                    {/* Glowing highlight aura when selected */}
                    {isSelected && (
                      <circle
                        r="34"
                        fill="none"
                        stroke={color}
                        strokeWidth="2"
                        strokeOpacity="0.8"
                        strokeDasharray="4,3"
                        style={{ pointerEvents: "none" }}
                      >
                        <animateTransform
                          attributeName="transform"
                          type="rotate"
                          from="0"
                          to="360"
                          dur="12s"
                          repeatCount="indefinite"
                        />
                      </circle>
                    )}

                    {/* Node circle */}
                    <circle
                      r="24"
                      className="node-base-circle"
                      fill="#1e293b"
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 2}
                      filter={`drop-shadow(0 0 8px ${color}40)`}
                      style={{ pointerEvents: "none" }}
                    />

                    {/* Node icon / initials */}
                    <text
                      textAnchor="middle"
                      y="4"
                      fill={color}
                      fontSize="10"
                      fontWeight="800"
                      fontFamily="sans-serif"
                      style={{ pointerEvents: "none", userSelect: "none" }}
                    >
                      {publisherName.substring(0, 2).toUpperCase()}
                    </text>

                    {/* Publisher text badge below node */}
                    <rect
                      x="-48"
                      y="29"
                      width="96"
                      height="18"
                      rx="9"
                      className="node-badge-rect"
                      fill="#0f172a"
                      stroke={color}
                      strokeWidth="0.8"
                      strokeOpacity="0.6"
                      style={{ pointerEvents: "none" }}
                    />
                    <text
                      textAnchor="middle"
                      y="41"
                      fill="#e2e8f0"
                      fontSize="8.5"
                      fontWeight="600"
                      style={{ pointerEvents: "none", userSelect: "none" }}
                    >
                      {shortName}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        )}
      </div>

      {/* Selected Node Details Inspector */}
      {activeNode && (
        <div className="graph-node-inspector">
          <div className="inspector-top">
            <div className="inspector-publisher-group">
              <span className="inspector-avatar">
                {(activeNode.publisher || activeNode.domain || "N").substring(0, 2).toUpperCase()}
              </span>
              <div>
                <h4 className="inspector-title">{activeNode.publisher || activeNode.domain}</h4>
                <a
                  href={activeNode.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inspector-url-link"
                >
                  {activeNode.domain} ↗
                </a>
              </div>
            </div>

            <div className="inspector-badges">
              <span
                className={`inspector-stance-tag ${
                  activeNode.stance === "SUPPORTS"
                    ? "tag-sup"
                    : activeNode.stance === "CONTRADICTS"
                    ? "tag-con"
                    : "tag-neu"
                }`}
              >
                {activeNode.stance === "SUPPORTS"
                  ? "✓ Corroborating Evidence"
                  : activeNode.stance === "CONTRADICTS"
                  ? "✗ Refuting / Debunking Evidence"
                  : "○ Neutral / Contextual Reference"}
              </span>
              <button
                type="button"
                className="close-inspector-btn"
                onClick={() => setActiveNode(null)}
                title="Close Inspector"
              >
                ✕
              </button>
            </div>
          </div>

          <h5 className="inspector-headline">{activeNode.title}</h5>

          {activeNode.snippet && (
            <div className="inspector-quote-callout">
              <span className="quote-mark">“</span>
              <p className="quote-body">{activeNode.snippet}</p>
            </div>
          )}

          <div className="inspector-actions">
            <a
              href={activeNode.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inspector-visit-btn"
            >
              Open Full Source Article ↗
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
