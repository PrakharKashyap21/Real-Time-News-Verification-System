// TruthLens AI - Background Service Worker (Manifest V3)

const DEFAULT_API_BASE = "http://localhost:8008";

// Register Context Menus on Installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "truthlens-verify-selection",
    title: "🔍 Verify selection with TruthLens AI",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "truthlens-verify-page",
    title: "📑 Verify current article with TruthLens AI",
    contexts: ["page"]
  });

  console.log("TruthLens AI Extension context menus registered.");
});

// Handle Context Menu Clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "truthlens-verify-selection" && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      action: "SHOW_VERIFICATION_MODAL",
      text: info.selectionText.trim(),
      title: tab.title || "Selected Claim"
    });
  } else if (info.menuItemId === "truthlens-verify-page") {
    chrome.tabs.sendMessage(tab.id, {
      action: "VERIFY_PAGE_URL",
      url: tab.url,
      title: tab.title || ""
    });
  }
});

// Message Listener for API Requests (Bypasses web page CORS limits)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "API_VERIFY_CLAIM") {
    handleVerifyClaim(request.payload)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true; // Keep channel open for async response
  }

  if (request.action === "API_EXTRACT_URL") {
    handleExtractUrl(request.payload)
      .then(result => sendResponse({ success: true, data: result }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === "API_CHECK_HEALTH") {
    checkHealth()
      .then(result => sendResponse({ success: true, isHealthy: result }))
      .catch(() => sendResponse({ success: false, isHealthy: false }));
    return true;
  }
});

async function getApiBase() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["truthlens_api_url"], (res) => {
      resolve(res.truthlens_api_url || DEFAULT_API_BASE);
    });
  });
}

async function checkHealth() {
  try {
    const apiBase = await getApiBase();
    const resp = await fetch(`${apiBase}/health`, { method: "GET" });
    return resp.ok;
  } catch (e) {
    return false;
  }
}

async function handleVerifyClaim(payload) {
  const apiBase = await getApiBase();
  try {
    const resp = await fetch(`${apiBase}/v2/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title || "",
        text: payload.text || ""
      })
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Server returned ${resp.status}: ${errText.slice(0, 100)}`);
    }

    return await resp.json();
  } catch (error) {
    console.error("TruthLens verification error:", error);
    throw new Error(
      error.message || "Failed to connect to TruthLens AI backend at http://localhost:8008"
    );
  }
}

async function handleExtractUrl(payload) {
  const apiBase = await getApiBase();
  try {
    const resp = await fetch(`${apiBase}/v2/extract-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: payload.url })
    });

    if (!resp.ok) {
      throw new Error(`Server returned ${resp.status}`);
    }

    return await resp.json();
  } catch (error) {
    throw new Error(error.message || "Failed to extract article content from URL.");
  }
}
