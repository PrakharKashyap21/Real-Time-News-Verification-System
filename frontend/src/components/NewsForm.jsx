import React, { useState, useEffect } from "react";

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

const LOADING_STEPS = [
  { text: "🔍 Searching live web, breaking news & fact-checks...", delay: 0 },
  { text: "📄 Fetching and reading full article paragraphs...", delay: 3500 },
  { text: "🧠 Analyzing facts & evaluating stance with Gemini AI...", delay: 7000 },
  { text: "✨ Formulating structured verdict & citations...", delay: 11000 }
];

const NewsForm = ({ onSubmit, isLoading, validationError, setValidationError, submitLabel = "Verify News" }) => {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
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
    setValidationError("");

    const trimmedTitle = title.trim();
    const trimmedText = text.trim();

    if (!trimmedTitle && !trimmedText) {
      setValidationError("Please enter a headline or article text to verify.");
      return;
    }

    if (trimmedTitle.length + trimmedText.length < 10) {
      setValidationError("Input text is too short. Please provide at least 10 characters of content.");
      return;
    }

    onSubmit({ title: trimmedTitle, text: trimmedText });
  };

  const handleSelectSample = (sample) => {
    if (isLoading) return;
    setTitle(sample.title);
    setText(sample.text);
    if (setValidationError) setValidationError("");
  };

  const handleClear = () => {
    if (isLoading) return;
    setTitle("");
    setText("");
    if (setValidationError) setValidationError("");
  };

  return (
    <form className="news-form" onSubmit={handleSubmit}>
      {/* Quick Example Presets */}
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
            if (validationError) setValidationError("");
          }}
          disabled={isLoading}
        />
      </div>

      <div className="form-group">
        <div className="form-label-row">
          <label htmlFor="article-text-input" className="form-label">
            Claim / News Article Content <span className="label-required">*</span>
          </label>
          <span className="char-count" aria-live="polite">
            {totalLength} chars {totalLength > 0 && totalLength < 10 ? "(min 10 chars)" : ""}
          </span>
        </div>
        <textarea
          id="article-text-input"
          className="form-textarea"
          rows={5}
          placeholder="Paste full news story, statement, or tweet/headline to verify..."
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (validationError) setValidationError("");
          }}
          disabled={isLoading}
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
          disabled={isLoading}
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

        {(title || text) && !isLoading && (
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
