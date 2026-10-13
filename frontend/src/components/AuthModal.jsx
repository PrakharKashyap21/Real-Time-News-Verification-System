import React, { useState, useEffect } from "react";
import {
  UserIcon,
  LockIcon,
  MailIcon,
  EyeIcon,
  EyeOffIcon,
  XIcon,
  SparklesIcon,
  ShieldCheckIcon,
  CheckCircleIcon
} from "./Icons";
import { loginUser, signupUser, loginDemoUser } from "../api";

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // 'login' or 'signup'
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Senior Fact-Checker");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      setError("");
      setSuccessMsg("");
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setIsLoading(true);

    try {
      let data;
      if (mode === "signup") {
        if (!name.trim()) throw new Error("Please enter your full name.");
        if (!email.trim()) throw new Error("Please enter your email address.");
        if (password.length < 6) throw new Error("Password must be at least 6 characters.");
        data = await signupUser({ name, email, password, role: "Fact-Checker" });
      } else {
        if (!email.trim() || !password) throw new Error("Please enter both email and password.");
        data = await loginUser(email, password);
      }

      // Save auth tokens
      localStorage.setItem("truthlens_auth_token", data.access_token);
      localStorage.setItem("truthlens_user_profile", JSON.stringify(data.user));

      setSuccessMsg(data.message || "Authentication successful!");
      setTimeout(() => {
        onAuthSuccess(data.user);
        onClose();
      }, 700);
    } catch (err) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError("");
    setSuccessMsg("");
    setIsLoading(true);
    try {
      const data = await loginDemoUser();
      localStorage.setItem("truthlens_auth_token", data.access_token);
      localStorage.setItem("truthlens_user_profile", JSON.stringify(data.user));
      setSuccessMsg("Welcome Demo Investigator! 1-Click login activated.");
      setTimeout(() => {
        onAuthSuccess(data.user);
        onClose();
      }, 600);
    } catch (err) {
      setError(err.message || "Failed to sign in with demo account.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Split View */}
        <div className="auth-split-grid">
          {/* Left Hero Brand Panel */}
          <div className="auth-brand-panel">
            <div className="auth-brand-content">
              <div className="auth-brand-pill">
                <span className="live-dot" />
                <span>Cloud Intelligence Auth</span>
              </div>
              <h2 className="auth-brand-title">
                TruthLens <span className="auth-title-gradient">AI</span>
              </h2>
              <p className="auth-brand-desc">
                Elevate your investigative workflow with persistent cloud dossier history, multi-modal analysis, and real-time consensus graph access.
              </p>

              <div className="auth-perks-list">
                <div className="auth-perk-item">
                  <div className="auth-perk-icon">🛡️</div>
                  <div>
                    <div className="auth-perk-title">Cross-Device Verification Sync</div>
                    <div className="auth-perk-sub">Audit history preserved securely in cloud</div>
                  </div>
                </div>

                <div className="auth-perk-item">
                  <div className="auth-perk-icon">📑</div>
                  <div>
                    <div className="auth-perk-title">Full Multi-Modal Dossiers</div>
                    <div className="auth-perk-sub">Document PDFs, Audio forensics & Vision OCR</div>
                  </div>
                </div>

                <div className="auth-perk-item">
                  <div className="auth-perk-icon">⭐</div>
                  <div>
                    <div className="auth-perk-title">Verified Fact-Checker Identity</div>
                    <div className="auth-perk-sub">Personalized audit signatures & export dossiers</div>
                  </div>
                </div>
              </div>

              <div className="auth-brand-footer">
                <ShieldCheckIcon size={14} style={{ color: "#38bdf8" }} />
                <span>Zero tracking • Passwords encrypted with PBKDF2</span>
              </div>
            </div>
          </div>

          {/* Right Form Panel */}
          <div className="auth-form-panel">
            {/* Header Row: Tabs + Close Button (prevents overlap) */}
            <div className="auth-header-action-row">
              <div className="auth-tabs-row">
                <button
                  type="button"
                  className={`auth-tab-btn ${mode === "login" ? "active" : ""}`}
                  onClick={() => {
                    setMode("login");
                    setError("");
                  }}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  className={`auth-tab-btn ${mode === "signup" ? "active" : ""}`}
                  onClick={() => {
                    setMode("signup");
                    setError("");
                  }}
                >
                  Create Account
                </button>
              </div>

              <button
                type="button"
                className="auth-close-btn"
                onClick={onClose}
                aria-label="Close dialog"
              >
                <XIcon size={18} />
              </button>
            </div>

            {/* Quick 1-Click Demo Login Button */}
            <div className="auth-demo-banner">
              <button
                type="button"
                className="auth-demo-btn"
                onClick={handleDemoLogin}
                disabled={isLoading}
              >
                <SparklesIcon size={15} style={{ color: "#f59e0b" }} />
                <span>Continue as Demo Investigator (1-Click)</span>
              </button>
              <span className="auth-demo-hint">Instant access for evaluators & recruiters • No password required</span>
            </div>

            <div className="auth-divider">
              <span>or sign in with email</span>
            </div>

            {/* Alert Messages */}
            {error && (
              <div className="auth-alert error" role="alert">
                <span>⚠️ {error}</span>
              </div>
            )}
            {successMsg && (
              <div className="auth-alert success" role="alert">
                <CheckCircleIcon size={15} style={{ color: "#10b981" }} />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Main Form */}
            <form onSubmit={handleSubmit} className="auth-form-fields">
              {mode === "signup" && (
                <div className="auth-field">
                  <label className="auth-label">Full Name</label>
                  <div className="auth-input-wrapper">
                    <UserIcon size={16} className="auth-input-icon" />
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="e.g. Jane Smith"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      disabled={isLoading}
                    />
                  </div>
                </div>
              )}

              <div className="auth-field">
                <label className="auth-label">Email Address</label>
                <div className="auth-input-wrapper">
                  <MailIcon size={16} className="auth-input-icon" />
                  <input
                    type="email"
                    className="auth-input"
                    placeholder="name@organization.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="auth-field">
                <label className="auth-label">Password</label>
                <div className="auth-input-wrapper">
                  <LockIcon size={16} className="auth-input-icon" />
                  <input
                    type={showPassword ? "text" : "password"}
                    className="auth-input"
                    placeholder={mode === "signup" ? "At least 6 characters" : "Enter your password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="auth-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span>Authenticating...</span>
                ) : mode === "signup" ? (
                  <span>Create Account & Start Auditing</span>
                ) : (
                  <span>Sign In to TruthLens AI</span>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
