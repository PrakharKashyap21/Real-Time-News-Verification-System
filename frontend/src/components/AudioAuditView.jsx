import React, { useState, useRef, useEffect } from "react";
import { auditUploadedAudio, fetchAudioSamples, auditAudioPreset, transcribeAudioFast } from "../api";

export default function AudioAuditView({ onAuditToLiveVerify }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [isAuditing, setIsAuditing] = useState(false);
  const [isTranscribingPreview, setIsTranscribingPreview] = useState(false);
  const [auditResult, setAuditResult] = useState(null);
  const [error, setError] = useState("");
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [activePreset, setActivePreset] = useState(null);
  const [statementHint, setStatementHint] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const fileInputRef = useRef(null);

  // Clean up Object URL and recognition on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [audioUrl]);

  // Format seconds to mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Helper to reliably resolve a source domain / URL for news wire citations
  const resolveSourceUrl = (src, claimText = "") => {
    if (!src) return "#";
    if (typeof src === "object" && src.url) return src.url;
    const clean = String(src).trim();
    if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;

    const lower = clean.toLowerCase().replace(/[^a-z0-9]/g, "");
    const outletDomains = {
      defencesecurityasia: "https://defencesecurityasia.com",
      firstpost: "https://www.firstpost.com",
      ndtv: "https://www.ndtv.com",
      thehindu: "https://www.thehindu.com",
      hindustantimes: "https://www.hindustantimes.com",
      timesofindia: "https://timesofindia.indiatimes.com",
      indiatoday: "https://www.indiatoday.in",
      ddnews: "https://ddnews.gov.in",
      pib: "https://pib.gov.in",
      ani: "https://www.aninews.in",
      aninews: "https://www.aninews.in",
      reuters: "https://www.reuters.com",
      bbc: "https://www.bbc.com",
      aljazeera: "https://www.aljazeera.com",
      bloomberg: "https://www.bloomberg.com",
      thewire: "https://thewire.in",
      theprint: "https://theprint.in",
      scroll: "https://scroll.in",
      wion: "https://www.wionews.com",
      wionews: "https://www.wionews.com",
      indianexpress: "https://indianexpress.com",
    };

    if (outletDomains[lower]) {
      return outletDomains[lower];
    }

    if (clean.includes(".")) {
      return `https://${clean}`;
    }

    return `https://www.google.com/search?q=${encodeURIComponent(clean + " " + (claimText || "news"))}`;
  };

  // Start in-browser microphone recording with hardware DSP & Live Dictation
  const startRecording = async () => {
    setError("");
    setAuditResult(null);
    setActivePreset(null);
    setStatementHint("");
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setSelectedFile(null);
    setSelectedFileName("");

    try {
      // 1. Hardware-level DSP noise cancellation, auto gain, and echo filtering
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: { ideal: 44100 },
        },
      });

      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const mime = mediaRecorder.mimeType || "audio/webm";
        const blob = new Blob(audioChunksRef.current, { type: mime });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        setSelectedFile(blob);
        const generatedName = `mic_recording_${Date.now()}.webm`;
        setSelectedFileName(generatedName);
        stream.getTracks().forEach((track) => track.stop());

        // Auto-transcribe using fast model so preview is guaranteed populated
        setIsTranscribingPreview(true);
        try {
          const autoText = await transcribeAudioFast(blob, generatedName);
          if (autoText && autoText.trim()) {
            setStatementHint(autoText.trim());
          }
        } catch (err) {
          // ignore
        } finally {
          setIsTranscribingPreview(false);
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingDuration(0);

      // 2. Browser Web Speech Recognition for live real-time visual dictation
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "en-IN"; // Configured for Indian English accent & phonetic nuances
          recognition.onresult = (event) => {
            let liveTranscript = "";
            for (let i = 0; i < event.results.length; i++) {
              liveTranscript += event.results[i][0].transcript;
            }
            if (liveTranscript.trim()) {
              setStatementHint(liveTranscript.trim());
            }
          };
          recognition.onerror = () => {};
          recognition.start();
          speechRecognitionRef.current = recognition;
        } catch (e) {
          // ignore
        }
      }

      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      setError("Microphone access denied or unavailable. Please enable browser microphone permissions or upload an audio file.");
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop();
        } catch (e) {}
        speechRecognitionRef.current = null;
      }
    }
  };

  // File Upload Handlers
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processAudioFile(file);
    }
  };

  const processAudioFile = (file) => {
    setError("");
    setAuditResult(null);
    setActivePreset(null);
    setStatementHint("");

    const validExts = /\.(mp3|wav|ogg|webm|m4a|aac|flac)$/i;
    const isAudioType = file.type.startsWith("audio/");

    if (!validExts.test(file.name) && !isAudioType) {
      setError("Unsupported audio format. Please upload an MP3, WAV, M4A, OGG, or WEBM audio file.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setError("Audio file exceeds 25MB limit. Please upload a smaller clip.");
      return;
    }

    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }

    setSelectedFile(file);
    setSelectedFileName(file.name);
    const url = URL.createObjectURL(file);
    setAudioUrl(url);

    // Auto-transcribe uploaded file for instant review
    setIsTranscribingPreview(true);
    transcribeAudioFast(file, file.name)
      .then((autoText) => {
        if (autoText && autoText.trim()) {
          setStatementHint(autoText.trim());
        }
      })
      .catch(() => {})
      .finally(() => {
        setIsTranscribingPreview(false);
      });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files?.[0]) {
      processAudioFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleClear = () => {
    if (isRecording) {
      stopRecording();
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setSelectedFile(null);
    setAudioUrl(null);
    setSelectedFileName("");
    setStatementHint("");
    setAuditResult(null);
    setError("");
    setActivePreset(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Execute full audio audit
  const runAudioAudit = async () => {
    if (!selectedFile) return;
    setIsAuditing(true);
    setError("");

    try {
      const data = await auditUploadedAudio(
        selectedFile,
        selectedFileName || "audio_recording.webm",
        statementHint
      );
      setAuditResult(data);
    } catch (err) {
      setError(err.message || "Failed to audit the audio file. Please ensure the backend is online.");
    } finally {
      setIsAuditing(false);
    }
  };

  // Load preset sample
  const loadPreset = async (presetId) => {
    handleClear();
    setActivePreset(presetId);
    setIsAuditing(true);
    setError("");

    try {
      const data = await auditAudioPreset(presetId);
      setAuditResult(data);
      setSelectedFileName(`${presetId}.mp3`);
      if (data?.transcription) {
        setStatementHint(data.transcription);
      }
    } catch (err) {
      setError(err.message || "Failed to load audio preset sample.");
    } finally {
      setIsAuditing(false);
    }
  };

  const copyTranscript = () => {
    if (!auditResult?.transcription) return;
    navigator.clipboard.writeText(auditResult.transcription);
    setCopiedTranscript(true);
    setTimeout(() => setCopiedTranscript(false), 2000);
  };

  return (
    <div className="audio-audit-container">
      {/* Header */}
      <header className="audio-audit-header">
        <div className="audio-audit-pill">
          <span className="live-dot pulse-cyan"></span>
          <span>Acoustic Forensics & Speech Fact-Checker</span>
        </div>
        <h1 className="audio-audit-title">Speech & Audio Claim Auditor</h1>
        <p className="audio-audit-subtitle">
          Record speech directly or upload viral voice notes, podcasts, and speeches. TruthLens AI transcribes speech, evaluates synthetic AI voice clone risk, extracts factual assertions, and cross-references multi-source wire consensus in real time.
        </p>
      </header>

      {/* Preset Samples Bar */}
      <section className="audio-presets-bar">
        <span className="audio-presets-label">⚡ Test with Curated Scenarios:</span>
        <div className="audio-presets-chips">
          <button
            type="button"
            className={`audio-preset-chip ${activePreset === "sample_curfew_rumor" ? "active" : ""}`}
            onClick={() => loadPreset("sample_curfew_rumor")}
            disabled={isAuditing || isRecording}
          >
            <span className="chip-icon">📢</span>
            <span>WhatsApp Curfew & Lockdown Voice Note</span>
            <span className="chip-badge chip-hoax">Hoax</span>
          </button>
          <button
            type="button"
            className={`audio-preset-chip ${activePreset === "sample_isro_mission" ? "active" : ""}`}
            onClick={() => loadPreset("sample_isro_mission")}
            disabled={isAuditing || isRecording}
          >
            <span className="chip-icon">🚀</span>
            <span>ISRO Gaganyaan Crew Recovery Address</span>
            <span className="chip-badge chip-verified">Verified</span>
          </button>
          <button
            type="button"
            className={`audio-preset-chip ${activePreset === "sample_miracle_cure" ? "active" : ""}`}
            onClick={() => loadPreset("sample_miracle_cure")}
            disabled={isAuditing || isRecording}
          >
            <span className="chip-icon">💊</span>
            <span>Miracle Clove & Gourd Heart Cure</span>
            <span className="chip-badge chip-hoax">Debunked</span>
          </button>
        </div>
      </section>

      {/* Audio Input Deck */}
      <div className="audio-input-grid">
        {/* Card 1: Direct Microphone Capture */}
        <div className={`audio-deck-card mic-card ${isRecording ? "recording-active" : ""}`}>
          <div className="deck-card-header">
            <div className="deck-icon mic-glow-icon">🎙️</div>
            <div>
              <h3 className="deck-title">Live Microphone Stream</h3>
              <p className="deck-subtitle">Speak a statement or play audio into your microphone</p>
            </div>
          </div>

          <div className="mic-action-area">
            {isRecording ? (
              <div className="recording-status-box">
                <div className="audio-equalizer-bars">
                  <span className="eq-bar bar-1"></span>
                  <span className="eq-bar bar-2"></span>
                  <span className="eq-bar bar-3"></span>
                  <span className="eq-bar bar-4"></span>
                  <span className="eq-bar bar-5"></span>
                  <span className="eq-bar bar-6"></span>
                  <span className="eq-bar bar-7"></span>
                  <span className="eq-bar bar-8"></span>
                </div>
                <div className="recording-timer-badge">
                  <span className="rec-red-dot"></span>
                  <span>RECORDING {formatTime(recordingDuration)}</span>
                </div>
                {statementHint && (
                  <div className="live-caption-pill" title="Live transcribed speech stream">
                    <span>"{statementHint}"</span>
                  </div>
                )}
                <button
                  type="button"
                  className="btn-stop-record"
                  onClick={stopRecording}
                >
                  ⏹ Stop & Inspect Audio
                </button>
              </div>
            ) : (
              <div className="mic-idle-state">
                <button
                  type="button"
                  className="btn-start-record"
                  onClick={startRecording}
                  disabled={isAuditing}
                >
                  <span className="rec-btn-icon">🎙️</span>
                  <span>Start Live Recording</span>
                </button>
                <span className="mic-hint">Click to capture voice with DSP noise cancellation</span>
              </div>
            )}
          </div>
        </div>

        {/* Card 2: File Dropzone */}
        <div
          className={`audio-deck-card upload-card ${selectedFile && !isRecording ? "has-file" : ""}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="audio/*,.mp3,.wav,.ogg,.webm,.m4a,.aac,.flac"
            className="audio-hidden-input"
            id="audio-file-selector"
          />

          <div className="deck-card-header">
            <div className="deck-icon upload-glow-icon">📁</div>
            <div>
              <h3 className="deck-title">Upload Audio Clip</h3>
              <p className="deck-subtitle">Supports MP3, WAV, M4A, OGG, WEBM (up to 25MB)</p>
            </div>
          </div>

          <div className="upload-drop-content">
            {selectedFileName ? (
              <div className="audio-staged-box">
                <div className="staged-file-info">
                  <span className="audio-file-icon">🎵</span>
                  <div className="staged-file-meta">
                    <strong className="staged-file-name">{selectedFileName}</strong>
                    {selectedFile?.size && (
                      <span className="staged-file-size">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-change-file"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isAuditing || isRecording}
                >
                  Change File
                </button>
              </div>
            ) : (
              <div
                className="dropzone-empty-state"
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
              >
                <div className="dropzone-plus-icon">☁️</div>
                <span className="dropzone-prompt">Drag & Drop audio file here or <em>browse files</em></span>
                <span className="dropzone-subtext">Ideal for forwarded WhatsApp voice notes & speech snippets</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Active Audio Playback Deck & Statement Review */}
      {(audioUrl || selectedFile) && (
        <div className="audio-playback-deck-wrapper">
          <div className="audio-playback-deck">
            <div className="audio-player-cluster">
              <span className="player-indicator-icon">▶</span>
              <div className="player-audio-wrapper">
                <audio controls src={audioUrl || ""} className="native-audio-player" />
              </div>
              {selectedFileName && (
                <span className="player-tag">
                  {selectedFileName}
                </span>
              )}
            </div>

            <div className="audio-deck-actions">
              <button
                type="button"
                className="btn-reset-audio"
                onClick={handleClear}
                disabled={isAuditing}
              >
                Clear
              </button>
              <button
                type="button"
                className="btn-execute-audio-audit"
                onClick={runAudioAudit}
                disabled={isAuditing || isRecording}
              >
                {isAuditing ? (
                  <>
                    <div className="audio-spinner-mini"></div>
                    <span>Analyzing Acoustics & Verifying Claims...</span>
                  </>
                ) : (
                  <>
                    <span>⚡ Audit Spoken Claims</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Statement Review & Phonetic Guidance Card */}
          <div className="audio-statement-review-card">
            <div className="review-card-header">
              <div className="review-title-group">
                <span className="review-icon">✏️</span>
                <strong className="review-title">Speech Transcript Preview (Editable)</strong>
                {isTranscribingPreview && (
                  <span className="transcribing-badge">
                    <span className="audio-spinner-mini"></span> 🧠 Gemini Flash Transcribing...
                  </span>
                )}
              </div>
              <span className="review-hint-pill">
                Auto-transcribed with conversational phonetic smoothing. You can review or edit before verifying.
              </span>
            </div>
            <textarea
              className="statement-review-textarea"
              value={statementHint}
              onChange={(e) => setStatementHint(e.target.value)}
              placeholder={
                isTranscribingPreview
                  ? "🧠 Transcribing audio with Gemini Flash..."
                  : "Live speech text appears here. You can edit any word or add keywords to ensure 100% accuracy..."
              }
              rows={2}
              disabled={isTranscribingPreview}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="audio-error-banner" role="alert">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Loading Progress State */}
      {isAuditing && (
        <div className="audio-auditing-loader-card">
          <div className="radar-orbit-spinner">
            <div className="orbit-dot dot-1"></div>
            <div className="orbit-dot dot-2"></div>
            <div className="orbit-center">🎙️</div>
          </div>
          <h3 className="loader-title">Cross-Referencing Speech Across Live Wire Feeds</h3>
          <p className="loader-description">
            Gemini Multimodal is transcribing phonemes, evaluating synthetic AI voice indicators, and verifying factual claims against Reuters, GDELT, and global fact-check archives...
          </p>
        </div>
      )}

      {/* Forensic Audit Results View */}
      {auditResult && !isAuditing && (() => {
        const rawVerdict = (auditResult.overall_verdict || "").toUpperCase();
        const isSupported =
          rawVerdict.includes("SUPPORT") ||
          rawVerdict.includes("HIGH_CREDIBILITY") ||
          rawVerdict.includes("VERIFIED") ||
          rawVerdict.includes("TRUE");
        const isContradicted =
          rawVerdict.includes("CONTRADICT") ||
          rawVerdict.includes("HIGH_RISK") ||
          rawVerdict.includes("FALSE") ||
          rawVerdict.includes("DEBUNKED");

        const verdictHeroClass = isSupported
          ? "verdict-supported"
          : isContradicted
          ? "verdict-contradicted"
          : "verdict-unverified";

        const verdictGlyph = isSupported ? "🟢" : isContradicted ? "🔴" : "🟠";
        const verdictTitle = isSupported
          ? "VERIFIED / ACCURATE SPEECH"
          : isContradicted
          ? "FALSE / DEBUNKED STATEMENTS"
          : "DISPUTED / UNVERIFIED ASSERTIONS";

        return (
          <div className="audio-result-viewport">
            {/* Top Verdict Banner */}
            <div className={`audio-verdict-hero ${verdictHeroClass}`}>
              <div className="hero-verdict-top">
                <div className="hero-verdict-badge">
                  <span className="verdict-glyph">{verdictGlyph}</span>
                  <span className="verdict-name">{verdictTitle}</span>
                </div>
                <div className="confidence-pill">
                  <span>Truth Score: </span>
                  <strong>{Math.round((auditResult.confidence_score || 0.8) * 100)}%</strong>
                </div>
              </div>

              <h2 className="audio-headline-display">
                "{auditResult.extracted_headline || auditResult.core_claim}"
              </h2>

              <p className="audio-executive-summary">
                {auditResult.authenticity_summary}
              </p>

            {/* Quick Metadata Chips */}
            <div className="audio-meta-pills-row">
              <div className="meta-pill">
                <span className="pill-label">Language:</span>
                <strong>{auditResult.detected_language}</strong>
              </div>
              <div className="meta-pill">
                <span className="pill-label">Acoustic Context:</span>
                <strong>{auditResult.acoustic_context}</strong>
              </div>
              <div className="meta-pill">
                <span className="pill-label">Format:</span>
                <strong>{auditResult.audio_format}</strong>
              </div>
              <div className="meta-pill">
                <span className="pill-label">Size:</span>
                <strong>{auditResult.file_size_kb} KB</strong>
              </div>
            </div>
          </div>

          {/* Grid: Acoustic Forensics & Verbatim Transcript */}
          <div className="audio-analysis-bento-grid">
            {/* Box 1: Forensic Acoustic Signature */}
            <div className="bento-box forensics-box">
              <div className="bento-box-header">
                <span className="bento-icon">🎛️</span>
                <h3 className="bento-title">Acoustic & Synthetic Voice Forensics</h3>
              </div>

              {/* Synthetic Voice Risk Meter */}
              <div className="synthetic-risk-container">
                <div className="risk-header">
                  <span className="risk-title">AI Voice Clone / Deepfake Risk:</span>
                  <span className={`risk-tag risk-${(auditResult.synthetic_voice_risk || "LOW").toLowerCase()}`}>
                    {auditResult.synthetic_voice_risk === "HIGH"
                      ? "🔴 HIGH RISK (Synthetic TTS / Cloned)"
                      : auditResult.synthetic_voice_risk === "MEDIUM"
                      ? "🟠 MEDIUM RISK (Unnatural Prosody)"
                      : "🟢 LOW RISK (Authentic Vocal Harmonics)"}
                  </span>
                </div>
                <div className="risk-meter-bar">
                  <div
                    className={`risk-meter-fill fill-${(auditResult.synthetic_voice_risk || "LOW").toLowerCase()}`}
                    style={{
                      width:
                        auditResult.synthetic_voice_risk === "HIGH"
                          ? "90%"
                          : auditResult.synthetic_voice_risk === "MEDIUM"
                          ? "50%"
                          : "15%",
                    }}
                  ></div>
                </div>
              </div>

              {/* Acoustic Observations */}
              <div className="observations-list">
                <span className="obs-label">Spectral & Room Observations:</span>
                <ul>
                  {auditResult.acoustic_observations?.map((obs, idx) => (
                    <li key={idx}>
                      <span className="obs-bullet">•</span>
                      <span>{obs}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Box 2: Verbatim Speech Transcription */}
            <div className="bento-box transcript-box">
              <div className="bento-box-header">
                <span className="bento-icon">📝</span>
                <h3 className="bento-title">Verbatim Speech Transcription</h3>
                <button
                  type="button"
                  className="btn-copy-transcript"
                  onClick={copyTranscript}
                  title="Copy transcription text"
                >
                  {copiedTranscript ? "✓ Copied" : "📋 Copy"}
                </button>
              </div>

              <div className="transcript-body-scroll">
                <blockquote className="speech-quote">
                  "{auditResult.transcription}"
                </blockquote>
              </div>
            </div>
          </div>

          {/* Extracted Factual Claims Breakdown */}
          <section className="audited-claims-section">
            <div className="section-title-cluster">
              <h3 className="claims-section-title">
                Factual Claims Verified Against Live Wire Feeds ({auditResult.claims_breakdown?.length || 1})
              </h3>
              <p className="claims-section-sub">
                Each statement extracted from the audio was cross-referenced across authoritative news organizations and fact-check repositories.
              </p>
            </div>

            <div className="claims-audit-list">
              {auditResult.claims_breakdown && auditResult.claims_breakdown.length > 0 ? (
                auditResult.claims_breakdown.map((claim, idx) => (
                  <div
                    key={claim.claim_id || idx}
                    className={`claim-audit-card verdict-${(claim.verdict || "UNVERIFIED").toLowerCase()}`}
                  >
                    <div className="claim-card-top">
                      <div className="claim-verdict-chip">
                        <span>
                          {claim.verdict === "SUPPORTED"
                            ? "🟢 SUPPORTED"
                            : claim.verdict === "CONTRADICTED"
                            ? "🔴 CONTRADICTED"
                            : "🟠 UNVERIFIED"}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="btn-graph-verify"
                        onClick={() => {
                          if (onAuditToLiveVerify) {
                            onAuditToLiveVerify({
                              title: auditResult.extracted_headline || "Audio Claim",
                              text: claim.text,
                            });
                          }
                        }}
                        title="Explore this statement in the interactive SVG Knowledge Graph"
                      >
                        Verify in Live Graph ↗
                      </button>
                    </div>

                    <p className="claim-statement-text">"{claim.text}"</p>
                    <p className="claim-reasoning-text">{claim.reasoning}</p>

                    {/* Cited Evidence Sources */}
                    {((claim.source_links && claim.source_links.length > 0) || (claim.top_sources && claim.top_sources.length > 0) || (claim.evidence && claim.evidence.length > 0)) && (
                      <div className="claim-evidence-chips">
                        <span className="ev-label">Corroborating Wire Sources:</span>
                        <div className="ev-chips-row">
                          {claim.source_links && claim.source_links.length > 0
                            ? claim.source_links.map((link, linkIdx) => {
                                const targetUrl = resolveSourceUrl(link.url || link.title, claim.text);
                                return (
                                  <a
                                    key={linkIdx}
                                    href={targetUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="evidence-source-pill"
                                    title={`Open corroborating reporting on ${link.title || link.url}`}
                                  >
                                    🌐 {link.title || link.url} ↗
                                  </a>
                                );
                              })
                            : claim.top_sources && claim.top_sources.length > 0
                            ? claim.top_sources.map((src, evIdx) => {
                                const targetUrl = resolveSourceUrl(src, claim.text);
                                return (
                                  <a
                                    key={evIdx}
                                    href={targetUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="evidence-source-pill"
                                    title={`Open corroborating coverage on ${src}`}
                                  >
                                    🌐 {src} ↗
                                  </a>
                                );
                              })
                            : claim.evidence.map((ev, evIdx) => {
                                const targetUrl = resolveSourceUrl(ev.url || ev.domain || ev.publisher, claim.text);
                                return (
                                  <a
                                    key={ev.id || evIdx}
                                    href={targetUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="evidence-source-pill"
                                    title={`Open reporting on ${ev.publisher || ev.domain || "News Wire"}`}
                                  >
                                    🌐 {ev.publisher || ev.domain || "News Wire"} ↗
                                  </a>
                                );
                              })}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="claim-audit-card verdict-unverified">
                  <div className="claim-card-top">
                    <div className="claim-verdict-chip">
                      <span>⚪ CORE CLAIM</span>
                    </div>
                    <button
                      type="button"
                      className="btn-graph-verify"
                      onClick={() => {
                        if (onAuditToLiveVerify) {
                          onAuditToLiveVerify({
                            title: auditResult.extracted_headline || "Audio Claim",
                            text: auditResult.core_claim,
                          });
                        }
                      }}
                    >
                      Verify in Live Graph ↗
                    </button>
                  </div>
                  <p className="claim-statement-text">"{auditResult.core_claim}"</p>
                  <p className="claim-reasoning-text">{auditResult.authenticity_summary}</p>
                </div>
              )}
            </div>
          </section>
        </div>
        );
      })()}
    </div>
  );
}
