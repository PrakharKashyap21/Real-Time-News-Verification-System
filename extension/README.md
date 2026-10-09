# 🔍 TruthLens AI — Chrome Extension (Manifest V3)

> **Real-time 1-click fact-checking directly in your web browser.** Verify viral social media posts, controversial claims, and web articles on Twitter/X, Reddit, or news sites without leaving the page.

---

## ⚡ Features

1. **Highlight & Right-Click Context Menu**:
   - Highlight any sentence or paragraph on any webpage.
   - Right-click and choose **"🔍 Verify selection with TruthLens AI"**.
   - A sleek in-page card slides in with the verdict, evidence sources, and credibility breakdown.

2. **Floating Quick-Action Pill**:
   - Selecting 25+ characters on any page automatically reveals a subtle floating **"🔍 Verify with TruthLens"** pill next to your cursor.

3. **Toolbar Extension Popup (`popup.html`)**:
   - **"Fact-Check This Page"**: Automatically reads the current webpage's title and article text to check its veracity.
   - **Manual Claim Input**: Type or paste any claim with 1-click preset sample buttons (*NASA JWST*, *Garlic COVID Hoax*, *Chandrayaan-3*).
   - **Backend Status Badge**: Shows live connection status to the local TruthLens AI server.

4. **1-Click Evidence Graph Bridge**:
   - Every verification card has an **"Open in Full Dashboard ↗"** button that opens `http://localhost:5173/` with the claim preloaded into the interactive SVG Knowledge Graph.

---

## 🚀 How to Install in Google Chrome, Brave, or Edge

1. Open your browser and navigate to:
   - **Chrome**: `chrome://extensions/`
   - **Brave**: `brave://extensions/`
   - **Edge**: `edge://extensions/`
2. In the top-right corner, enable **Developer mode**.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `extension/` folder in this repository:
   ```
   /Users/prakharkashyap/Documents/Real-Time-News-Verification-System/extension
   ```
5. The **TruthLens AI** extension is now installed and active! Pin it to your browser toolbar for quick access.

---

## ⚙️ Architecture & Local Requirements

- **Backend**: TruthLens AI FastAPI server must be running on `http://127.0.0.1:8008` (or `http://localhost:8008`).
  ```bash
  uvicorn backend.app.main:app --host 127.0.0.1 --port 8008 --reload
  ```
- **Manifest Version**: V3 compliant.
- **Permissions**: `contextMenus`, `storage`, `activeTab`, `scripting`.
