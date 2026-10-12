import React, { useState, useEffect } from "react";
import {
  ChromeIcon,
  XIcon,
  DownloadIcon,
  CopyIcon,
  CheckCircleIcon,
  SparklesIcon,
  ExternalLinkIcon
} from "./Icons";

export default function ExtensionModal({ isOpen, onClose }) {
  const [copiedPath, setCopiedPath] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopyPath = () => {
    navigator.clipboard.writeText("extension");
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleCopyChromeUrl = () => {
    navigator.clipboard.writeText("chrome://extensions/");
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <div className="ext-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ext-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="ext-modal-header">
          <div className="ext-header-brand">
            <div className="ext-brand-badge">
              <ChromeIcon size={24} style={{ color: "#38bdf8" }} />
            </div>
            <div>
              <div className="ext-pill-row">
                <span className="ext-tag">Chrome & Chromium (Manifest V3)</span>
                <span className="ext-live-dot-badge">
                  <span className="live-dot" /> Live Ready
                </span>
              </div>
              <h2 className="ext-title">TruthLens AI Browser Extension</h2>
            </div>
          </div>
          <button
            type="button"
            className="ext-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <XIcon size={18} />
          </button>
        </div>

        {/* Subtitle */}
        <p className="ext-subtitle">
          Audit breaking news, viral tweets on Twitter / X, Reddit threads, and press articles in 1-click directly in your browser without leaving the page.
        </p>

        {/* Features Row */}
        <div className="ext-features-grid">
          <div className="ext-feature-card">
            <div className="ext-feat-icon">🎯</div>
            <div className="ext-feat-title">Floating Quick-Verify</div>
            <p className="ext-feat-desc">
              Highlight 25+ characters on any webpage to trigger an instant AI fact-check pill next to your cursor.
            </p>
          </div>

          <div className="ext-feature-card">
            <div className="ext-feat-icon">⚡</div>
            <div className="ext-feat-title">Right-Click Context Menu</div>
            <p className="ext-feat-desc">
              Right-click any sentence & select "Verify with TruthLens AI" for a slide-over verdict dossier.
            </p>
          </div>

          <div className="ext-feature-card">
            <div className="ext-feat-icon">🌐</div>
            <div className="ext-feat-title">Full Dashboard Handoff</div>
            <p className="ext-feat-desc">
              Every in-page result connects directly to the TruthLens Knowledge Graph dashboard for deep analysis.
            </p>
          </div>
        </div>

        {/* 4-Step Installation Walkthrough */}
        <div className="ext-install-section">
          <div className="ext-install-title-row">
            <h3 className="ext-install-heading">
              <SparklesIcon size={15} style={{ color: "#a855f7" }} /> Quick 4-Step Installation Guide
            </h3>
            <span className="ext-install-browsers">Works on Chrome, Brave, Edge & Opera</span>
          </div>

          <div className="ext-steps-list">
            {/* Step 1 */}
            <div className="ext-step-item">
              <div className="ext-step-number">1</div>
              <div className="ext-step-body">
                <div className="ext-step-title">Get the Extension Package</div>
                <p className="ext-step-text">
                  Download the ready-to-use extension ZIP, or use the local <code>extension/</code> folder from this project repository.
                </p>
                <div className="ext-step-actions">
                  <a
                    href="http://localhost:8008/api/v2/extension/download"
                    download="truthlens-ai-chrome-extension.zip"
                    className="ext-btn-primary"
                  >
                    <DownloadIcon size={14} /> Download Extension (.zip)
                  </a>
                  <button
                    type="button"
                    className="ext-btn-secondary"
                    onClick={handleCopyPath}
                  >
                    {copiedPath ? (
                      <>
                        <CheckCircleIcon size={13} style={{ color: "#10b981" }} /> Path Copied!
                      </>
                    ) : (
                      <>
                        <CopyIcon size={13} /> Copy Folder Name (<code>extension/</code>)
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="ext-step-item">
              <div className="ext-step-number">2</div>
              <div className="ext-step-body">
                <div className="ext-step-title">Open Extension Manager</div>
                <p className="ext-step-text">
                  Paste <code>chrome://extensions/</code> in your browser address bar (or <code>brave://extensions/</code> for Brave).
                </p>
                <button
                  type="button"
                  className="ext-btn-secondary"
                  onClick={handleCopyChromeUrl}
                >
                  {copiedUrl ? (
                    <>
                      <CheckCircleIcon size={13} style={{ color: "#10b981" }} /> Copied!
                    </>
                  ) : (
                    <>
                      <CopyIcon size={13} /> Copy <code>chrome://extensions/</code>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Step 3 */}
            <div className="ext-step-item">
              <div className="ext-step-number">3</div>
              <div className="ext-step-body">
                <div className="ext-step-title">Enable Developer Mode</div>
                <p className="ext-step-text">
                  Look in the <strong>top-right corner</strong> of the Extensions page and toggle the <strong>Developer mode</strong> switch to <strong>ON</strong>.
                </p>
              </div>
            </div>

            {/* Step 4 */}
            <div className="ext-step-item">
              <div className="ext-step-number">4</div>
              <div className="ext-step-body">
                <div className="ext-step-title">Load Unpacked Extension</div>
                <p className="ext-step-text">
                  Click the <strong>"Load unpacked"</strong> button in the top-left corner and select the extracted <code>extension</code> folder. TruthLens AI is immediately ready!
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="ext-modal-footer">
          <div className="ext-footer-meta">
            <span className="ext-req-tag">Local Requirement:</span> TruthLens backend running on <code>http://localhost:8008</code>
          </div>
          <button type="button" className="ext-done-btn" onClick={onClose}>
            Got It!
          </button>
        </div>
      </div>
    </div>
  );
}
