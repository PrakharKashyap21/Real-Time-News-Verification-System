import React, { useState, useRef } from "react";
import { auditUploadedImage } from "../api";

export default function ImageAuditView({ onAuditToLiveVerify }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditResult, setAuditResult] = useState(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const processFile = (file) => {
    setError("");
    const validTypes = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    if (!validTypes.includes(file.type.toLowerCase()) && !/\.(png|jpe?g|webp)$/i.test(file.name)) {
      setError("Unsupported file format. Please upload a PNG, JPG, or WEBP image.");
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setError("File exceeds 15MB limit. Please upload a smaller image.");
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setAuditResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files?.[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleClear = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setAuditResult(null);
    setError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const runAudit = async () => {
    if (!selectedFile) return;
    setIsAuditing(true);
    setError("");

    try {
      const data = await auditUploadedImage(selectedFile);
      setAuditResult(data);
    } catch (err) {
      setError(err.message || "Failed to audit the uploaded image. Please try again.");
    } finally {
      setIsAuditing(false);
    }
  };

  const loadPresetSample = async (sampleType) => {
    handleClear();
    setIsAuditing(true);
    setError("");

    // Create a demo canvas graphic for instant interactive demonstration
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 450;
    const ctx = canvas.getContext("2d");

    // Background
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, 800, 450);

    // Header bar
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, 800, 60);

    // Social banner title
    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 22px sans-serif";
    ctx.fillText("Breaking Viral News Desk", 30, 40);

    // Headline
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 26px sans-serif";

    let text1 = "";
    let text2 = "";

    if (sampleType === "5g") {
      text1 = "BREAKING: Viral study claims 5G cellular towers";
      text2 = "cause viral flu transmission across urban centers.";
    } else if (sampleType === "tata") {
      text1 = "Tata's Trent reports massive 46% Q2 revenue surge";
      text2 = "driven by Zudio and Westside apparel footprint.";
    } else {
      text1 = "James Webb Space Telescope confirms biosignatures";
      text2 = "and definitive proof of alien life on exoplanet K2-18b.";
    }

    ctx.fillText(text1, 30, 140);
    ctx.fillText(text2, 30, 185);

    // Meta details
    ctx.fillStyle = "#94a3b8";
    ctx.font = "16px sans-serif";
    ctx.fillText("Posted 14m ago • 45.2K Reposts • Verified Account @NewsAlerts", 30, 240);

    // Border line
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 2;
    ctx.strokeRect(20, 20, 760, 410);

    canvas.toBlob(async (blob) => {
      if (blob) {
        const file = new File([blob], `${sampleType}_viral_claim.png`, { type: "image/png" });
        setSelectedFile(file);
        setPreviewUrl(URL.createObjectURL(file));

        try {
          const data = await auditUploadedImage(file);
          setAuditResult(data);
        } catch (err) {
          setError(err.message || "Failed to audit sample image.");
        } finally {
          setIsAuditing(false);
        }
      }
    }, "image/png");
  };

  const getVerdictBadge = (verdict) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
      case "VERIFIED":
        return <span className="image-verdict-tag tag-sup">✅ Verified Factual</span>;
      case "CONTRADICTED":
      case "FALSE":
        return <span className="image-verdict-tag tag-con">❌ False / Fabricated</span>;
      case "MISLEADING":
        return <span className="image-verdict-tag tag-mis">⚠️ Misleading / Out of Context</span>;
      case "UNVERIFIED":
      default:
        return <span className="image-verdict-tag tag-unv">❓ Unverified Rumor</span>;
    }
  };

  const getRiskBadge = (risk) => {
    switch (risk?.toUpperCase()) {
      case "HIGH":
        return <span className="risk-pill risk-high">🔥 High Manipulation Risk</span>;
      case "MEDIUM":
        return <span className="risk-pill risk-med">⚠️ Moderate Manipulation Risk</span>;
      case "LOW":
      default:
        return <span className="risk-pill risk-low">🛡️ Low Manipulation Risk</span>;
    }
  };

  return (
    <div className="image-audit-container">
      {/* Header */}
      <div className="image-audit-header">
        <div className="image-audit-pill">
          <span className="live-dot pulse-purple"></span>
          <span>Multimodal Forensic Vision</span>
        </div>
        <h1 className="image-audit-title">Screenshot & Image Claim Verifier</h1>
        <p className="image-audit-subtitle">
          Upload screenshots of viral tweets, fabricated headlines, or photos to transcribe text via Gemini Vision, detect digital tampering, and audit factual claims against live news archives.
        </p>
      </div>

      {/* Preset Demo Strip */}
      <div className="preset-demo-bar">
        <span className="preset-label">Try instant sample:</span>
        <button
          type="button"
          className="preset-btn"
          onClick={() => loadPresetSample("5g")}
          disabled={isAuditing}
        >
          📱 Viral 5G Claim
        </button>
        <button
          type="button"
          className="preset-btn"
          onClick={() => loadPresetSample("jwst")}
          disabled={isAuditing}
        >
          🔭 NASA Exoplanet Banner
        </button>
        <button
          type="button"
          className="preset-btn"
          onClick={() => loadPresetSample("tata")}
          disabled={isAuditing}
        >
          📈 Tata Trent Earnings Post
        </button>
      </div>

      {/* Upload Dropzone */}
      {!previewUrl && (
        <div
          className="image-dropzone"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".png,.jpg,.jpeg,.webp"
            style={{ display: "none" }}
          />
          <div className="dropzone-icon">🖼️</div>
          <h3 className="dropzone-title">Drop your screenshot or image here</h3>
          <p className="dropzone-subtitle">
            Supports PNG, JPG, or WEBP up to 15MB • Captures social posts, newspaper clips, memes
          </p>
          <button type="button" className="btn-browse-image">
            Browse Image
          </button>
        </div>
      )}

      {/* Selected Image Preview & Action Card */}
      {previewUrl && !auditResult && !isAuditing && (
        <div className="image-preview-card">
          <div className="preview-media-pane">
            <img src={previewUrl} alt="Upload Preview" className="preview-thumb" />
          </div>
          <div className="preview-meta-pane">
            <h4 className="preview-filename">{selectedFile?.name || "Uploaded Image"}</h4>
            <span className="preview-filesize">
              {((selectedFile?.size || 0) / 1024).toFixed(1)} KB • {selectedFile?.type || "image/png"}
            </span>

            <p className="preview-instructions">
              Ready for multimodal OCR transcription, forensic font/metadata inspection, and cross-reference fact-checking.
            </p>

            <div className="preview-actions">
              <button
                type="button"
                className="btn-run-audit"
                onClick={runAudit}
                disabled={isAuditing}
              >
                ⚡ Run Multimodal Forensic Audit
              </button>
              <button
                type="button"
                className="btn-cancel-preview"
                onClick={handleClear}
              >
                Change Image
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Scanning State */}
      {isAuditing && (
        <div className="image-scanning-card">
          <div className="scanning-radar-ring"></div>
          <h3 className="scanning-title">Analyzing Multimodal Image Forensics...</h3>
          <p className="scanning-subtitle">
            Transcribing text via Gemini Vision, analyzing compression artifacts, and cross-referencing news wires with TruthLens RAG.
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="image-audit-error">
          <span>⚠️ {error}</span>
          <button type="button" onClick={handleClear} className="retry-btn">
            Dismiss
          </button>
        </div>
      )}

      {/* Audit Results View */}
      {auditResult && (
        <div className="image-audit-results">
          {/* Top Hero Verdict Card */}
          <div className="audit-hero-card">
            <div className="hero-top-cluster">
              <div className="hero-status-group">
                <span className="media-type-badge">📸 {auditResult.media_type}</span>
                {getRiskBadge(auditResult.visual_manipulation_risk)}
              </div>
              <div className="hero-verdict-wrap">
                {getVerdictBadge(auditResult.overall_verdict)}
              </div>
            </div>

            <h2 className="audit-headline">"{auditResult.extracted_headline}"</h2>
            <p className="audit-summary">{auditResult.authenticity_summary}</p>

            <div className="audit-meta-row">
              <div className="meta-box">
                <span className="meta-lbl">Dimensions</span>
                <span className="meta-val">{auditResult.dimensions}</span>
              </div>
              <div className="meta-box">
                <span className="meta-lbl">File Size</span>
                <span className="meta-val">{auditResult.file_size_kb} KB</span>
              </div>
              <div className="meta-box">
                <span className="meta-lbl">Tamper Risk</span>
                <span className="meta-val">{auditResult.visual_manipulation_risk}</span>
              </div>
              <div className="meta-box">
                <span className="meta-lbl">Confidence</span>
                <span className="meta-val">{Math.round(auditResult.confidence_score * 100)}%</span>
              </div>
            </div>
          </div>

          {/* Visual Observations & Transcribed Content Grid */}
          <div className="audit-details-grid">
            {/* Transcribed Text Card */}
            <div className="detail-panel-card">
              <div className="panel-header">
                <span className="panel-icon">📝</span>
                <h4 className="panel-title">Transcribed Content & Core Claim</h4>
              </div>

              <div className="transcription-body">
                <div className="transcription-claim-box">
                  <span className="transcription-lbl">Core Assertion Verified:</span>
                  <p className="transcription-claim-text">{auditResult.core_claim}</p>
                </div>

                {auditResult.extracted_text && (
                  <div className="transcription-raw-box">
                    <span className="transcription-lbl">Full Verbatim Text Extracted:</span>
                    <p className="transcription-raw-text">{auditResult.extracted_text}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Forensic Visual Clues Card */}
            <div className="detail-panel-card">
              <div className="panel-header">
                <span className="panel-icon">🔬</span>
                <h4 className="panel-title">Forensic Visual Observations</h4>
              </div>

              <div className="observations-body">
                {auditResult.visual_observations && auditResult.visual_observations.length > 0 ? (
                  <ul className="observations-list">
                    {auditResult.visual_observations.map((obs, idx) => (
                      <li key={idx} className="observation-item">
                        <span className="obs-bullet">•</span>
                        <span>{obs}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="observations-empty">
                    Standard digital compression observed with no overt pixel-level font inconsistencies.
                  </p>
                )}

                {previewUrl && (
                  <div className="analyzed-thumb-box">
                    <span className="thumb-lbl">Analyzed Media Source:</span>
                    <img src={previewUrl} alt="Analyzed Media" className="analyzed-thumb" />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Audited Fact-Check Claims List */}
          {auditResult.claims_breakdown && auditResult.claims_breakdown.length > 0 && (
            <div className="fact-checks-card">
              <h3 className="fact-checks-title">
                📰 Cross-Referenced Fact-Checks & News Reports ({auditResult.claims_breakdown.length})
              </h3>
              <div className="fact-checks-list">
                {auditResult.claims_breakdown.map((claim, idx) => (
                  <div key={idx} className="claim-audit-row">
                    <div className="claim-row-header">
                      <span className="claim-row-badge">Assertion #{idx + 1}</span>
                      <span className={`claim-verdict-pill verdict-${claim.verdict.toLowerCase()}`}>
                        {claim.verdict}
                      </span>
                    </div>
                    <p className="claim-row-text">"{claim.text}"</p>
                    <p className="claim-row-reasoning">{claim.reasoning}</p>

                    {claim.top_sources && claim.top_sources.length > 0 && (
                      <div className="claim-row-sources">
                        <span className="sources-lbl">Attributed Publishers:</span>
                        {claim.top_sources.map((src, sIdx) => (
                          <span key={sIdx} className="src-chip">
                            🌐 {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Row */}
          <div className="audit-footer-actions">
            {onAuditToLiveVerify && (
              <button
                type="button"
                className="btn-action-primary"
                onClick={() =>
                  onAuditToLiveVerify({
                    title: auditResult.extracted_headline,
                    text: auditResult.core_claim || auditResult.extracted_text,
                  })
                }
              >
                🕸️ Open in Interactive Evidence Graph →
              </button>
            )}
            <button
              type="button"
              className="btn-action-secondary"
              onClick={handleClear}
            >
              Upload Another Image
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
