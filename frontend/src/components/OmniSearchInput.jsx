import React, { useState, useEffect, useRef } from "react";
import { extractArticleFromUrl } from "../api";

const SUPPORTED_LANGUAGES = [
  { code: "auto", label: "Auto-Detect", flag: "🌐" },
  { code: "hi", label: "हिन्दी (Hindi)", flag: "🇮🇳" },
  { code: "hinglish", label: "Hinglish (Roman)", flag: "💬" },
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "bn", label: "বাংলা (Bengali)", flag: "🇮🇳" },
  { code: "ta", label: "தமிழ் (Tamil)", flag: "🇮🇳" },
  { code: "te", label: "తెలుగు (Telugu)", flag: "🇮🇳" },
  { code: "mr", label: "मराठी (Marathi)", flag: "🇮🇳" }
];

const detectScriptClientSide = (text) => {
  if (!text || text.trim().length < 3) return null;
  if (/[\u0900-\u097F]/.test(text)) return "हिन्दी (Hindi)";
  if (/[\u0980-\u09FF]/.test(text)) return "বাংলা (Bengali)";
  if (/[\u0B80-\u0BFF]/.test(text)) return "தமிழ் (Tamil)";
  if (/[\u0C00-\u0C7F]/.test(text)) return "తెలుగు (Telugu)";

  const hinglishWords = [
    "karega", "karenge", "sarkar", "sarkaar", "yojna", "yojana",
    "khabar", "daawa", "dawa", "aadesh", "faisla", "rupaye", "rupey",
    "paisa", "paise", "nakli", "asli", "waale", "wale", "sabko", "milega",
    "band", "khulenge", "chutti", "nahi", "nahin", "nhi", "viral", "whatsapp"
  ];
  const words = text.toLowerCase().split(/\s+/);
  if (words.some((w) => hinglishWords.includes(w.replace(/[^a-z]/g, "")))) {
    return "Hinglish (Roman Hindi)";
  }
  return null;
};

const TRENDING_EXAMPLES = [
  {
    type: "claim",
    label: "🇮🇳 ₹500 Note Rumor (हिन्दी)",
    title: "RBI 500 Currency Note Ban Rumor",
    text: "सोशल मीडिया पर दावा किया जा रहा है कि RBI ने ₹500 के स्टार मार्क वाले नोटों को अवैध घोषित कर बंद कर दिया है।",
    language: "hi"
  },
  {
    type: "claim",
    label: "⚡ Free Bijli Subsidy (Hinglish)",
    title: "PM Muft Bijli Yojna WhatsApp Message",
    text: "WhatsApp forward keh raha hai ki sarkar sabhi nagriko ke account me 5000 rupaye bijli subsidy direct bhej rahi hai link se claim karein.",
    language: "hinglish"
  },
  {
    type: "claim",
    label: "📈 Trent Q2 Revenue",
    title: "Trent Q2 standalone revenue",
    text: "Indian retailer Trent reported a 23% year-on-year rise in standalone revenue in the July-September 2026 quarter.",
    language: "en"
  },
  {
    type: "claim",
    label: "🦠 5G COVID Hoax",
    title: "5G and Coronavirus",
    text: "5G mobile towers transmit coronavirus pathogens and cause COVID-19 infections.",
    language: "en"
  },
  {
    type: "claim",
    label: "🚀 NASA Artemis I",
    title: "NASA Artemis Mission",
    text: "NASA launched the Artemis I mission to test the Orion spacecraft and Space Launch System rocket.",
    language: "en"
  },
  {
    type: "url",
    label: "🌐 BBC Tech Article",
    url: "https://www.bbc.com/news/technology",
    language: "en"
  }
];

const LOADING_STEPS = [
  { text: "🔍 Searching live web, breaking news & regional archives...", delay: 0 },
  { text: "📄 Reading source paragraphs & fact-check wires...", delay: 3500 },
  { text: "🧠 Analyzing claims & cross-verifying stance with Gemini AI...", delay: 7000 },
  { text: "✨ Formulating multilingual verdict & citations...", delay: 11000 }
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
  const [selectedLanguage, setSelectedLanguage] = useState("auto");
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
            sourceUrl: rawInput,
            language: selectedLanguage
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
      text: rawInput,
      language: selectedLanguage
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
    if (example.language) {
      setSelectedLanguage(example.language);
    }
  };

  const handleClear = () => {
    setInputText("");
    setHeadline("");
    setSelectedLanguage("auto");
    if (setValidationError) setValidationError("");
  };

  const detectedScript = detectScriptClientSide(inputText);

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
                : "Ask anything in Hindi, Hinglish, or English to verify with live news wires..."
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

            {/* Language Selector Dropdown */}
            <div className="omni-lang-badge-wrapper" title="Claim & response language mode">
              <select
                className="omni-lang-select"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                disabled={isLoading || isExtracting}
                aria-label="Select Claim Language"
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Live Client Script Detection Chip */}
            {detectedScript && selectedLanguage === "auto" && (
              <span className="omni-detected-pill" title="Script automatically detected from your typing">
                ✨ {detectedScript}
              </span>
            )}

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
