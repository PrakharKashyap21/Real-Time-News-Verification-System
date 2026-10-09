import React, { useState, useEffect } from "react";
import { extractArticleFromUrl } from "../api";

const SAMPLE_CLAIMS = [
  {
    label: "📈 Trent Q2 Revenue",
    title: "Trent Q2 standalone revenue",
    text: "Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter."
  },
  {
    label: "🦠 5G COVID Hoax",
    title: "5G and Coronavirus",
    text: "5G mobile towers transmit coronavirus pathogens and cause COVID-19 infections."
  },
  {
    label: "🚀 NASA Artemis I",
    title: "NASA Artemis Mission",
    text: "NASA launched the Artemis I mission to test the Orion spacecraft and Space Launch System rocket."
  },
  {
    label: "💼 Microsoft Acquisition",
    title: "Microsoft Activision Deal",
    text: "Microsoft acquired video game publisher Activision Blizzard for approximately $69 billion in an all-cash transaction."
  }
];

const SAMPLE_URLS = [
  {
    label: "🌐 NASA Artemis Release",
    url: "https://www.nasa.gov/news-release/nasa-prepares-for-artemis-ii-mission-to-the-moon/"
  },
  {
    label: "📰 BBC Tech News",
    url: "https://www.bbc.com/news/technology"
  }
];

const LOADING_STEPS = [
  { text: "🔍 Searching live web, breaking news & fact-checks...", delay: 0 },
  { text: "📄 Fetching and reading full article paragraphs...", delay: 3500 },
  { text: "🧠 Analyzing facts & evaluating stance with Gemini AI...", delay: 7000 },
  { text: "✨ Formulating structured verdict & citations...", delay: 11000 }
];

const NewsForm = ({ onSubmit, isLoading, validationError, setValidationError, submitLabel = "Verify News" }) => {
  const [inputMode, setInputMode] = useState("text"); // "text" | "url"
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [isExtractingUrl, setIsExtractingUrl] = useState(false);
  const [urlExtractSuccess, setUrlExtractSuccess] = useState(false);
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);

  const totalLength = title.trim().length + text.trim().length;

  useEffect(() => {
    let timers = [];
    if (isLoading) {
      setLoadingStepIndex(0);
      LOADING_STEPS.forEach((step, idx) => {
        if (idx > 0) {
          const t = setTimeout(() => {
            setLoadingStepIndex(idx);
          }, step.delay);
          timers.push(t);
        }
      });
    } else {
      setLoadingStepIndex(0);
    }
    return () => timers.forEach(clearTimeout);
  }, [isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (setValidationError) setValidationError("");

    const trimmedTitle = title.trim();
    const trimmedText = text.trim();

    if (!trimmedTitle && !trimmedText) {
      if (setValidationError) setValidationError("Please enter a headline or article text to verify.");
      return;
    }

    if (trimmedTitle.length + trimmedText.length < 10) {
      if (setValidationError) setValidationError("Input text is too short. Please provide at least 10 characters.");
      return;
    }

    onSubmit({ title: trimmedTitle, text: trimmedText, sourceUrl: url.trim() || undefined });
  };

  const handleExtractUrl = async (targetUrl = url) => {
    const rawUrl = (targetUrl || "").trim();
    if (!rawUrl) {
      if (setValidationError) setValidationError("Please enter a valid article URL.");
      return;
    }

    setIsExtractingUrl(true);
    setUrlExtractSuccess(false);
    if (setValidationError) setValidationError("");

    try {
      const data = await extractArticleFromUrl(rawUrl);
      if (data && data.success) {
        if (data.title) setTitle(data.title);
        if (data.text) setText(data.text);
        setUrlExtractSuccess(true);
      } else {
        if (setValidationError) setValidationError(data?.error || "Could not extract article content from URL.");
      }
    } catch (err) {
      if (setValidationError) setValidationError(err.message || "Failed to extract content from URL.");
    } finally {
      setIsExtractingUrl(false);
    }
  };

  const handleSelectSample = (sample) => {
    if (isLoading) return;
    setInputMode("text");
    setTitle(sample.title);
    setText(sample.text);
    setUrl("");
    setUrlExtractSuccess(false);
    if (setValidationError) setValidationError("");
  };

  const handleSelectSampleUrl = (sample) => {
    if (isLoading) return;
    setUrl(sample.url);
    handleExtractUrl(sample.url);
  };

  const handleClear = () => {
    if (isLoading) return;
    setTitle("");
    setText("");
    setUrl("");
    setUrlExtractSuccess(false);
    if (setValidationError) setValidationError("");
  };

  return (
    <form className="news-form" onSubmit={handleSubmit}>
      {/* Mode Switcher */}
      <div className="input-mode-tabs">
        <button
          type="button"
          className={`mode-tab-btn ${inputMode === "text" ? "active" : ""}`}
          onClick={() => {
            setInputMode("text");
            if (setValidationError) setValidationError("");
          }}
          disabled={isLoading || isExtractingUrl}
        >
          📝 Claim / Text
        </button>
        <button
          type="button"
          className={`mode-tab-btn ${inputMode === "url" ? "active" : ""}`}
          onClick={() => {
            setInputMode("url");
            if (setValidationError) setValidationError("");
          }}
          disabled={isLoading || isExtractingUrl}
        >
          🔗 Article URL
        </button>
      </div>

      {inputMode === "url" ? (
        <div className="url-input-section">
          <div className="presets-container">
            <span className="presets-label">⚡ Try Sample URLs:</span>
            <div className="presets-grid">
              {SAMPLE_URLS.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="preset-chip-btn"
                  onClick={() => handleSelectSampleUrl(sample)}
                  disabled={isLoading || isExtractingUrl}
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="url-input" className="form-label">
              Article Web Address <span className="label-required">*</span>
            </label>
            <div className="url-input-action-row">
              <input
                id="url-input"
                type="url"
                className="form-input url-input"
                placeholder="https://news-website.com/article-slug..."
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setUrlExtractSuccess(false);
                  if (setValidationError) setValidationError("");
                }}
                disabled={isLoading || isExtractingUrl}
              />
              <button
                type="button"
                className="extract-url-btn"
                onClick={() => handleExtractUrl()}
                disabled={isLoading || isExtractingUrl || !url.trim()}
              >
                {isExtractingUrl ? "Extracting..." : "📥 Fetch"}
              </button>
            </div>
          </div>

          {urlExtractSuccess && (
            <div className="url-success-banner">
              ✓ Article extracted successfully. Review or edit below before verifying.
            </div>
          )}
        </div>
      ) : (
        /* Text / Claim Mode Presets */
        <div className="presets-container">
          <span className="presets-label">⚡ Try Quick Examples:</span>
          <div className="presets-grid">
            {SAMPLE_CLAIMS.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                className="preset-chip-btn"
                onClick={() => handleSelectSample(sample)}
                disabled={isLoading}
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Headline / Topic Input */}
      <div className="form-group">
        <label htmlFor="headline-input" className="form-label">
          Headline / Topic <span className="label-optional">(Optional)</span>
        </label>
        <input
          id="headline-input"
          type="text"
          className="form-input"
          placeholder="e.g., Trent Q2 Standalone Revenue, Artemis I Launch..."
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            if (setValidationError) setValidationError("");
          }}
          disabled={isLoading || isExtractingUrl}
        />
      </div>

      {/* Claim / Article Body Input */}
      <div className="form-group">
        <div className="form-label-row">
          <label htmlFor="article-text-input" className="form-label">
            Claim / News Content <span className="label-required">*</span>
          </label>
          <span className="char-count" aria-live="polite">
            {totalLength} chars {totalLength > 0 && totalLength < 10 ? "(min 10 chars)" : ""}
          </span>
        </div>
        <textarea
          id="article-text-input"
          className="form-textarea"
          rows={5}
          placeholder="Paste full news story, claim statement, or viral quote..."
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (setValidationError) setValidationError("");
          }}
          disabled={isLoading || isExtractingUrl}
        />
      </div>

      {validationError && (
        <div className="validation-alert" role="alert">
          ⚠️ {validationError}
        </div>
      )}

      <div className="form-actions">
        <button
          type="submit"
          className={`submit-button ${isLoading ? "loading" : ""}`}
          disabled={isLoading || isExtractingUrl}
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              <span>Verifying with AI...</span>
            </>
          ) : (
            `✨ ${submitLabel}`
          )}
        </button>

        {(title || text || url) && !isLoading && !isExtractingUrl && (
          <button
            type="button"
            className="clear-button"
            onClick={handleClear}
            disabled={isLoading}
          >
            Clear
          </button>
        )}
      </div>

      {isLoading && (
        <div className="live-loading-container" aria-live="polite">
          <div className="loading-steps-header">
            <span className="loading-pulsar"></span>
            <span className="loading-current-text">{LOADING_STEPS[loadingStepIndex].text}</span>
          </div>
          <div className="loading-progress-bar">
            <div
              className="loading-progress-fill"
              style={{ width: `${((loadingStepIndex + 1) / LOADING_STEPS.length) * 100}%` }}
            ></div>
          </div>
        </div>
      )}
    </form>
  );
};

export default NewsForm;
