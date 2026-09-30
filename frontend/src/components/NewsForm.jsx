import React, { useState } from "react";

const NewsForm = ({ onSubmit, isLoading, validationError, setValidationError, submitLabel = "Detect News" }) => {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  const totalLength = title.trim().length + text.trim().length;

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError("");

    const trimmedTitle = title.trim();
    const trimmedText = text.trim();

    if (!trimmedTitle && !trimmedText) {
      setValidationError("Please enter a headline or article text to analyze.");
      return;
    }

    if (trimmedTitle.length + trimmedText.length < 10) {
      setValidationError("Input text is too short. Please provide at least 10 characters of content.");
      return;
    }

    onSubmit({ title: trimmedTitle, text: trimmedText });
  };

  const handleClear = () => {
    if (isLoading) return;
    setTitle("");
    setText("");
    setValidationError("");
  };

  return (
    <form className="news-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="headline-input" className="form-label">
          Headline <span className="label-optional">(Optional)</span>
        </label>
        <input
          id="headline-input"
          type="text"
          className="form-input"
          placeholder="Enter news article headline or title..."
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
            Article Text <span className="label-required">*</span>
          </label>
          <span className="char-count" aria-live="polite">
            {totalLength} chars {totalLength > 0 && totalLength < 10 ? "(minimum 10 needed)" : ""}
          </span>
        </div>
        <textarea
          id="article-text-input"
          className="form-textarea"
          rows={6}
          placeholder="Paste full news article or claim statements here..."
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
          {validationError}
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
              <span>Analyzing & Verifying...</span>
            </>
          ) : (
            submitLabel
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
        <div className="loading-notice" aria-live="polite">
          <span className="loading-dot-pulse"></span>
          <span>Searching Google Fact Check, live news records, and reference archives. This may take 5–15 seconds...</span>
        </div>
      )}
    </form>
  );
};

export default NewsForm;
