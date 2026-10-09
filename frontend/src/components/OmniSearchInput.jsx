import React, { useState, useEffect, useRef } from "react";
import { extractArticleFromUrl } from "../api";

const TRENDING_EXAMPLES = [
  {
    type: "claim",
    label: "📈 Trent Q2 Revenue",
    title: "Trent Q2 standalone revenue",
    text: "Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter."
  },
  {
    type: "claim",
    label: "🦠 5G COVID Hoax",
    title: "5G and Coronavirus",
    text: "5G mobile towers transmit coronavirus pathogens and cause COVID-19 infections."
  },
  {
    type: "claim",
    label: "🚀 NASA Artemis I",
    title: "NASA Artemis Mission",
    text: "NASA launched the Artemis I mission to test the Orion spacecraft and Space Launch System rocket."
  },
  {
    type: "claim",
    label: "💼 Microsoft Acquisition",
    title: "Microsoft Activision Deal",
    text: "Microsoft acquired video game publisher Activision Blizzard for approximately $69 billion in an all-cash transaction."
  },
  {
    type: "url",
    label: "🌐 BBC Tech Article",
    url: "https://www.bbc.com/news/technology"
  }
];

const LOADING_STEPS = [
  { text: "🔍 Searching live web, breaking news & fact-checks...", delay: 0 },
  { text: "📄 Fetching and reading full article paragraphs...", delay: 3500 },
  { text: "🧠 Analyzing facts & evaluating stance with Gemini AI...", delay: 7000 },
  { text: "✨ Formulating structured verdict & citations...", delay: 11000 }
];

const OmniSearchInput = ({
  onSubmit,
  isLoading,
  validationError,
  setValidationError,
  initialText = "",
  initialTitle = "",
  isCompact = false
}) => {
  const [inputText, setInputText] = useState(initialText);
  const [headline, setHeadline] = useState(initialTitle);
  const [showHeadlineInput, setShowHeadlineInput] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const textareaRef = useRef(null);

  // Sync if initial props change
  useEffect(() => {
    if (initialText) setInputText(initialText);
    if (initialTitle) setHeadline(initialTitle);
  }, [initialText, initialTitle]);

  const isUrl = inputText.trim().startsWith("http://") || inputText.trim().startsWith("https://");

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

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleVerify();
    }
  };

  const handleVerify = async () => {
    if (setValidationError) setValidationError("");
    const rawInput = inputText.trim();

    if (!rawInput && !headline.trim()) {
      if (setValidationError) setValidationError("Please enter a news claim or paste an article URL.");
      return;
    }

    // If input is a URL, extract it first then verify
    if (isUrl) {
      setIsExtracting(true);
      try {
        const extracted = await extractArticleFromUrl(rawInput);
        if (extracted && extracted.success) {
          const extractedTitle = headline.trim() || extracted.title || "";
          const extractedText = extracted.text || "";
          if (extractedText.length < 10) {
            if (setValidationError) setValidationError("Extracted article content is too brief for fact-checking.");
            return;
          }
          onSubmit({
            title: extractedTitle,
            text: extractedText,
            sourceUrl: rawInput
          });
        } else {
          if (setValidationError) setValidationError(extracted?.error || "Could not extract article content from URL.");
        }
      } catch (err) {
        if (setValidationError) setValidationError(err.message || "Failed to fetch content from URL.");
      } finally {
        setIsExtracting(false);
      }
      return;
    }

    // Regular claim/headline verification
    if (rawInput.length + headline.trim().length < 10) {
      if (setValidationError) setValidationError("Please provide at least 10 characters of content.");
      return;
    }

    onSubmit({
      title: headline.trim() || undefined,
      text: rawInput
    });
  };

  const handleSelectExample = async (example) => {
    if (isLoading || isExtracting) return;
    if (setValidationError) setValidationError("");

    if (example.type === "url") {
      setInputText(example.url);
      setHeadline("");
    } else {
      setInputText(example.text);
      setHeadline(example.title || "");
    }
  };

  const handleClear = () => {
    setInputText("");
    setHeadline("");
    if (setValidationError) setValidationError("");
  };

  return (
    <div className={`omni-search-wrapper ${isCompact ? "compact-mode" : ""}`}>
      {/* Omni AI Input Box */}
      <div className="omni-search-card">
        {showHeadlineInput && (
          <div className="omni-headline-row">
            <input
              type="text"
              className="omni-headline-input"
              placeholder="Headline / Topic (Optional)..."
              value={headline}
              onChange={(e) => {
                setHeadline(e.target.value);
                if (setValidationError) setValidationError("");
              }}
              disabled={isLoading || isExtracting}
            />
            <button
              type="button"
              className="omni-remove-headline-btn"
              onClick={() => {
                setHeadline("");
                setShowHeadlineInput(false);
              }}
              title="Remove headline field"
            >
              ✕
            </button>
          </div>
        )}

        <div className="omni-textarea-container">
          <textarea
            ref={textareaRef}
            className="omni-textarea"
            rows={isCompact ? 2 : 4}
            placeholder={
              isCompact
                ? "Verify another claim or paste news URL..."
                : "Ask anything, paste a news claim, viral statement, or article URL to verify..."
            }
            value={inputText}
            onChange={(e) => {
              setInputText(e.target.value);
              if (setValidationError) setValidationError("");
            }}
            onKeyDown={handleKeyDown}
            disabled={isLoading || isExtracting}
          />
        </div>

        {/* Input Bar Bottom Controls */}
        <div className="omni-bottom-bar">
          <div className="omni-left-tools">
            {isUrl ? (
              <span className="omni-url-indicator">
                🔗 Web URL Detected
              </span>
            ) : !showHeadlineInput ? (
              <button
                type="button"
                className="omni-tool-btn"
                onClick={() => setShowHeadlineInput(true)}
                disabled={isLoading || isExtracting}
              >
                + Add Headline
              </button>
            ) : null}

            {inputText.trim().length > 0 && (
              <span className="omni-char-count">{inputText.trim().length} chars</span>
            )}
          </div>

          <div className="omni-right-tools">
            {(inputText || headline) && !isLoading && !isExtracting && (
              <button
                type="button"
                className="omni-clear-btn"
                onClick={handleClear}
                disabled={isLoading || isExtracting}
              >
                Clear
              </button>
            )}

            <button
              type="button"
              className={`omni-submit-btn ${isLoading || isExtracting ? "loading" : ""}`}
              onClick={handleVerify}
              disabled={isLoading || isExtracting || (!inputText.trim() && !headline.trim())}
            >
              {isLoading || isExtracting ? (
                <>
                  <span className="omni-spinner"></span>
                  <span>{isExtracting ? "Extracting..." : "Verifying..."}</span>
                </>
              ) : (
                <>
                  <span>✨ Verify</span>
                  <span className="shortcut-hint">↵</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {validationError && (
        <div className="omni-alert" role="alert">
          ⚠️ {validationError}
        </div>
      )}

      {/* Quick Trending Chips */}
      {!isCompact && (
        <div className="trending-chips-row">
          <span className="trending-label">Trending:</span>
          <div className="trending-chips-list">
            {TRENDING_EXAMPLES.map((ex, idx) => (
              <button
                key={idx}
                type="button"
                className="trending-chip"
                onClick={() => handleSelectExample(ex)}
                disabled={isLoading || isExtracting}
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Progress Bar when Loading */}
      {(isLoading || isExtracting) && (
        <div className="omni-live-progress" aria-live="polite">
          <div className="progress-header">
            <span className="pulsar-dot"></span>
            <span className="progress-step-text">
              {isExtracting ? "📄 Fetching and parsing web article content..." : LOADING_STEPS[loadingStepIndex].text}
            </span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: isExtracting
                  ? "45%"
                  : `${((loadingStepIndex + 1) / LOADING_STEPS.length) * 100}%`
              }}
            ></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OmniSearchInput;
