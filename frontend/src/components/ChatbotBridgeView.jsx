import React, { useState, useEffect, useRef } from "react";
import { verifyBotMessage, fetchBotPresets, simulateWebhookCall } from "../api";

export default function ChatbotBridgeView({ onOpenInDashboard }) {
  const [platform, setPlatform] = useState("whatsapp"); // 'whatsapp' | 'telegram'
  const [inputText, setIsInputText] = useState("");
  const [isForwarded, setIsForwarded] = useState(true);
  const [chatHistory, setChatHistory] = useState([
    {
      id: "init-bot-welcome",
      sender: "bot",
      time: "Just now",
      text: "👋 Welcome to TruthLens AI Chatbot!\n\nForward any unverified news, WhatsApp chain message, or viral Telegram text here. I will cross-reference it against live breaking news and accredited fact-checking wires in real time."
    }
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [presets, setPresets] = useState([]);
  const [copiedId, setCopiedId] = useState(null);
  const [activeTab, setActiveTab] = useState("chat"); // 'chat' | 'webhooks'
  const [webhookPayload, setWebhookPayload] = useState(
    JSON.stringify(
      {
        update_id: 10001,
        message: {
          message_id: 42,
          chat: { id: 987654321 },
          from: { first_name: "Rahul", username: "rahul_news" },
          text: "UNESCO officially declares Jana Gana Mana best national anthem in the world"
        }
      },
      null,
      2
    )
  );
  const [webhookResult, setWebhookResult] = useState(null);
  const [isTestingWebhook, setIsTestingWebhook] = useState(false);

  const chatBodyRef = useRef(null);

  // Auto-scroll ONLY the internal phone chat container, NEVER scrolling the main browser window
  const scrollToBottom = (behavior = "smooth") => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTo({
        top: chatBodyRef.current.scrollHeight,
        behavior: behavior
      });
    }
  };

  // Keep main window stable at top when switching tabs
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);

  // Only scroll inside the phone chat when new messages are sent/received
  useEffect(() => {
    if (chatHistory.length > 1 || isProcessing) {
      scrollToBottom();
    }
  }, [chatHistory, isProcessing]);

  // Load presets on mount
  useEffect(() => {
    const loadPresets = async () => {
      try {
        const data = await fetchBotPresets();
        setPresets(data);
      } catch (err) {
        console.warn("Failed to load presets:", err);
      }
    };
    loadPresets();
  }, []);

  // Send message
  const handleSendMessage = async (customText, customIsForwarded = isForwarded) => {
    const textToSend = (customText !== undefined ? customText : inputText).trim();
    if (!textToSend || isProcessing) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: "user",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      text: textToSend,
      isForwarded: customIsForwarded
    };

    setChatHistory((prev) => [...prev, userMsg]);
    if (customText === undefined) {
      setIsInputText("");
    }
    setIsProcessing(true);

    try {
      const response = await verifyBotMessage(textToSend, platform, customIsForwarded);
      const botMsgId = `bot-${Date.now()}`;
      const botMsg = {
        id: botMsgId,
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        verificationData: response,
        formattedReply: response.formatted_chat_reply
      };
      setChatHistory((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg = {
        id: `bot-err-${Date.now()}`,
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: `⚠️ Verification Error: ${err.message || "Failed to cross-reference with fact-checking registry."}`
      };
      setChatHistory((prev) => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Run mock webhook test
  const handleTestWebhook = async () => {
    setIsTestingWebhook(true);
    setWebhookResult(null);
    try {
      const parsed = JSON.parse(webhookPayload);
      const res = await simulateWebhookCall(platform, parsed);
      setWebhookResult(res);
    } catch (err) {
      setWebhookResult({ error: err.message || "Invalid JSON or server error" });
    } finally {
      setIsTestingWebhook(false);
    }
  };

  return (
    <div className="chatbot-bridge-container">
      {/* Centered Header matching Audio & Image Audit views */}
      <header className="chatbot-header">
        <div className="chatbot-pill">
          <span className="live-dot pulse-green"></span>
          <span>WhatsApp & Telegram Fact-Checker</span>
        </div>
        <h1 className="chatbot-title">WhatsApp & Telegram Chatbot Bridge</h1>
        <p className="chatbot-subtitle">
          Instant viral forward fact-checker. Connects directly to WhatsApp Cloud API and Telegram Bot webhooks to debunk forwarded rumors with accredited news wire archives.
        </p>
      </header>

      {/* Centered Control & Switcher Bar */}
      <div className="chatbot-control-bar">
        <div className="platform-toggle-group">
          <button
            type="button"
            className={`platform-btn ${platform === "whatsapp" ? "active-whatsapp" : ""}`}
            onClick={() => setPlatform("whatsapp")}
          >
            <span className="platform-icon">💬</span> WhatsApp Mode
          </button>
          <button
            type="button"
            className={`platform-btn ${platform === "telegram" ? "active-telegram" : ""}`}
            onClick={() => setPlatform("telegram")}
          >
            <span className="platform-icon">✈️</span> Telegram Mode
          </button>
        </div>

        <div className="mode-toggle-group">
          <button
            type="button"
            className={`tab-switch-btn ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            💬 Chat Simulator
          </button>
          <button
            type="button"
            className={`tab-switch-btn ${activeTab === "webhooks" ? "active" : ""}`}
            onClick={() => setActiveTab("webhooks")}
          >
            🔌 Webhook Hub
          </button>
        </div>
      </div>

      {activeTab === "chat" ? (
        <div className="chatbot-layout-grid">
          {/* Left Column: Preset Viral Rumor Scenarios */}
          <div className="chatbot-presets-panel">
            <div className="panel-title-row">
              <span className="panel-icon">🔥</span>
              <h3 className="panel-heading">Viral Forwards Simulator</h3>
            </div>
            <p className="presets-desc">
              Tap any realistic viral WhatsApp/Telegram rumor to test instant debunks and fact-check responses:
            </p>

            <div className="presets-stack">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  className="preset-forward-card"
                  onClick={() => handleSendMessage(preset.viral_text, preset.is_forwarded)}
                >
                  <div className="preset-card-top">
                    <span className={`preset-platform-badge ${preset.platform}`}>
                      {preset.platform === "whatsapp" ? "💬 WhatsApp" : "✈️ Telegram"}
                    </span>
                    <span className="preset-cat-badge">{preset.category}</span>
                  </div>
                  <strong className="preset-card-title">{preset.title}</strong>
                  <p className="preset-card-snippet">"{preset.viral_text}"</p>
                  <div className="preset-card-footer">
                    <span className="preset-sender-tag">👤 {preset.sender_label}</span>
                    <span className="btn-try-preset">Test Forward →</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Tips */}
            <div className="bot-info-tip-box">
              <span className="tip-icon">💡</span>
              <div className="tip-content">
                <strong>How the Bot Engine Works:</strong>
                <p>
                  Incoming forwarded messages automatically have spam chain-letter prefixes stripped.
                  The core claim is extracted, cross-referenced with accredited news wires via Agentic RAG,
                  and returned as a WhatsApp/Telegram ready markdown card.
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Phone Mockup Chat Window */}
          <div className={`phone-simulator-frame ${platform}`}>
            {/* Phone Top Notch & Status */}
            <div className="phone-status-bar">
              <span className="status-time">09:41</span>
              <div className="phone-notch"></div>
              <div className="status-icons">
                <span>📶</span>
                <span>🛜</span>
                <span>🔋</span>
              </div>
            </div>

            {/* Chat Contact Header */}
            <div className={`phone-chat-header ${platform}`}>
              <div className="header-contact-info">
                <div className="contact-avatar-circle">
                  <span>🛡️</span>
                </div>
                <div className="contact-text-group">
                  <div className="contact-name-row">
                    <strong className="contact-name">TruthLens AI Fact-Checker</strong>
                    <span className="verified-badge" title="Official Verified Bot">✓</span>
                  </div>
                  <span className="contact-status-sub">
                    {isProcessing ? "Verifying with news wires..." : "Online • Real-Time News Bridge"}
                  </span>
                </div>
              </div>

              <div className="chat-header-actions">
                <button
                  type="button"
                  className="btn-clear-chat"
                  onClick={() =>
                    setChatHistory([
                      {
                        id: "init-bot-welcome",
                        sender: "bot",
                        time: "Just now",
                        text: "👋 TruthLens Bot ready. Forward any news snippet or viral claim to verify."
                      }
                    ])
                  }
                  title="Clear conversation"
                >
                  🔄
                </button>
              </div>
            </div>

            {/* Chat Scrollable Body */}
            <div className="phone-chat-body" ref={chatBodyRef}>
              {chatHistory.map((msg) => (
                <div
                  key={msg.id}
                  className={`chat-bubble-row ${msg.sender === "user" ? "user-row" : "bot-row"}`}
                >
                  <div
                    className={`chat-bubble ${msg.sender === "user" ? `user-bubble ${platform}` : "bot-bubble"}`}
                  >
                    {/* User Forwarded Label */}
                    {msg.sender === "user" && msg.isForwarded && (
                      <div className="forwarded-tag">
                        <span className="fwd-icon">↪</span> Forwarded many times
                      </div>
                    )}

                    {/* Standard Text or Rich Verification Card */}
                    {msg.verificationData ? (
                      <div className="rich-factcheck-card">
                        <div className="card-header-badge-row">
                          <span className="card-brand">🔍 TruthLens Fact-Check</span>
                          <span
                            className={`card-verdict-tag ${
                              msg.verificationData.verdict === "SUPPORTED"
                                ? "tag-supported"
                                : msg.verificationData.verdict === "CONTRADICTED"
                                ? "tag-contradicted"
                                : "tag-unverified"
                            }`}
                          >
                            {msg.verificationData.verdict === "SUPPORTED"
                              ? "✅ VERIFIED"
                              : msg.verificationData.verdict === "CONTRADICTED"
                              ? "❌ DEBUNKED / FAKE"
                              : "⚠️ UNVERIFIED"}
                          </span>
                        </div>

                        {/* Credibility Gauge */}
                        <div className="card-credibility-meter">
                          <div className="meter-label-row">
                            <span>Credibility Score:</span>
                            <strong className="meter-val">{msg.verificationData.credibility_score}%</strong>
                          </div>
                          <div className="meter-bar-track">
                            <div
                              className={`meter-bar-fill ${
                                msg.verificationData.credibility_score > 60
                                  ? "fill-high"
                                  : msg.verificationData.credibility_score < 30
                                  ? "fill-low"
                                  : "fill-mid"
                              }`}
                              style={{ width: `${msg.verificationData.credibility_score}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Explanation */}
                        <p className="card-explanation-text">
                          {msg.verificationData.explanation}
                        </p>

                        {/* Source citations */}
                        {msg.verificationData.top_sources && msg.verificationData.top_sources.length > 0 && (
                          <div className="card-sources-section">
                            <span className="card-sources-label">Cited News Wires:</span>
                            <div className="card-sources-chips">
                              {msg.verificationData.top_sources.map((src, sIdx) => (
                                <span key={sIdx} className="card-source-chip">
                                  📰 {src}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Interactive Buttons on the bubble */}
                        <div className="card-bubble-actions">
                          <button
                            type="button"
                            className="btn-bubble-action"
                            onClick={() => copyToClipboard(msg.formattedReply, msg.id)}
                            title="Copy formatted reply to forward back to WhatsApp"
                          >
                            {copiedId === msg.id ? "✓ Copied Reply!" : "📋 Copy Fact-Check Reply"}
                          </button>

                          {onOpenInDashboard && (
                            <button
                              type="button"
                              className="btn-bubble-action secondary"
                              onClick={() => onOpenInDashboard(msg.verificationData.sanitized_claim)}
                              title="Open in deep RAG search"
                            >
                              🔍 Open in Live Graph
                            </button>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="bubble-text">{msg.text}</p>
                    )}

                    <div className="bubble-meta">
                      <span className="bubble-time">{msg.time}</span>
                      {msg.sender === "user" && <span className="read-receipt">✓✓</span>}
                    </div>
                  </div>
                </div>
              ))}

              {/* Bot Typing Indicator */}
              {isProcessing && (
                <div className="chat-bubble-row bot-row">
                  <div className="chat-bubble bot-bubble typing-bubble">
                    <span className="typing-label">TruthLens Bot checking live wires</span>
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input Bar */}
            <div className="phone-chat-input-bar">
              <button
                type="button"
                className={`btn-forward-toggle ${isForwarded ? "active" : ""}`}
                onClick={() => setIsForwarded(!isForwarded)}
                title={isForwarded ? "Forwarded tag active" : "Mark as direct message"}
              >
                ↪ {isForwarded ? "Fwd: ON" : "Direct"}
              </button>

              <textarea
                className="chat-input-textarea"
                value={inputText}
                onChange={(e) => setIsInputText(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={
                  platform === "whatsapp"
                    ? "Paste forwarded WhatsApp message..."
                    : "Paste Telegram rumor or forward..."
                }
                rows={1}
                disabled={isProcessing}
              />

              <button
                type="button"
                className={`btn-send-message ${platform}`}
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isProcessing}
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Webhooks Developer Tab */
        <div className="webhook-dev-hub">
          <div className="webhook-info-header">
            <span className="hub-badge">DEVELOPER API & WEBHOOK BRIDGE</span>
            <h3>Production Webhook Integrations</h3>
            <p>
              Connect your actual Telegram Bot or WhatsApp Cloud API directly to TruthLens AI.
              Incoming forwarded messages trigger automated factual retrieval and instant replies.
            </p>
          </div>

          <div className="webhook-endpoints-grid">
            {/* Telegram Endpoint Card */}
            <div className="endpoint-card">
              <div className="endpoint-header">
                <span className="platform-tag telegram">✈️ Telegram Bot API</span>
                <span className="method-badge">POST</span>
              </div>
              <code className="endpoint-url">
                http://localhost:8008/v2/bot/webhook/telegram
              </code>
              <p className="endpoint-desc">
                Register with Telegram via <code>setWebhook</code>. Accepts standard Telegram <code>Update</code> payloads with <code>message.text</code>.
              </p>
              <div className="endpoint-actions">
                <button
                  type="button"
                  className="btn-copy-curl"
                  onClick={() =>
                    copyToClipboard(
                      `curl -F "url=http://your-domain.com/v2/bot/webhook/telegram" https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook`,
                      "tg-curl"
                    )
                  }
                >
                  {copiedId === "tg-curl" ? "✓ Copied!" : "📋 Copy Webhook Setup Command"}
                </button>
              </div>
            </div>

            {/* WhatsApp Endpoint Card */}
            <div className="endpoint-card">
              <div className="endpoint-header">
                <span className="platform-tag whatsapp">💬 WhatsApp Cloud API</span>
                <span className="method-badge">POST</span>
              </div>
              <code className="endpoint-url">
                http://localhost:8008/v2/bot/webhook/whatsapp
              </code>
              <p className="endpoint-desc">
                Compatible with Meta WhatsApp Business Cloud API & Twilio WhatsApp webhooks.
              </p>
              <div className="endpoint-actions">
                <button
                  type="button"
                  className="btn-copy-curl"
                  onClick={() =>
                    copyToClipboard(
                      `curl -X POST http://localhost:8008/v2/bot/webhook/whatsapp -H "Content-Type: application/json" -d '{"Body":"RBI 500 note fake alert","From":"whatsapp:+919876543210"}'`,
                      "wa-curl"
                    )
                  }
                >
                  {copiedId === "wa-curl" ? "✓ Copied!" : "📋 Copy Twilio Test Command"}
                </button>
              </div>
            </div>
          </div>

          {/* Interactive Webhook Simulator */}
          <div className="interactive-webhook-tester">
            <div className="tester-header">
              <h4>🧪 Live Webhook Dispatch Tester</h4>
              <span>Simulate an incoming HTTP webhook payload to verify backend response</span>
            </div>

            <div className="tester-grid">
              <div className="tester-col">
                <label className="tester-label">Incoming JSON Webhook Payload:</label>
                <textarea
                  className="tester-json-editor"
                  value={webhookPayload}
                  onChange={(e) => setWebhookPayload(e.target.value)}
                  rows={9}
                />
                <button
                  type="button"
                  className="btn-dispatch-test"
                  onClick={handleTestWebhook}
                  disabled={isTestingWebhook}
                >
                  {isTestingWebhook ? "⚡ Dispatching..." : "🚀 Send Mock Webhook HTTP Request"}
                </button>
              </div>

              <div className="tester-col">
                <label className="tester-label">Backend Response Payload:</label>
                <pre className="tester-json-response">
                  {webhookResult
                    ? JSON.stringify(webhookResult, null, 2)
                    : "// Click 'Send Mock Webhook' to view verified JSON reply..."}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
