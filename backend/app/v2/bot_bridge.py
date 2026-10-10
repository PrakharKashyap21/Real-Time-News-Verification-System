import os
import re
import json
import time
import logging
import urllib.parse
from typing import Optional, Dict, Any, List

from backend.app.v2.schemas import (
    BotVerificationRequest,
    BotVerificationResponse,
    BotPresetScenario
)
from backend.app.v2.rag_verifier import get_rag_verifier

logger = logging.getLogger(__name__)

VIRAL_BOT_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "preset_500_currency_fake",
        "platform": "whatsapp",
        "title": "Viral WhatsApp Forward: ₹500 Note Green Stripe Fake Alert",
        "sender_label": "Family WhatsApp Group",
        "viral_text": "⚠️ URGENT WARNING FROM RBI! ⚠️\nPlease check your 500 Rupee currency notes immediately! Any 500 note where the green security thread line is near the Governor's signature instead of Mahatma Gandhi photo is 100% FAKE. Banks will not accept it from tomorrow. Forward to all friends and family groups to save everyone from huge loss!",
        "category": "Currency & Banking Hoax",
        "is_forwarded": True,
        "simulated_verdict": "CONTRADICTED"
    },
    {
        "id": "preset_unesco_anthem",
        "platform": "whatsapp",
        "title": "WhatsApp Chain Message: UNESCO Best Anthem in the World",
        "sender_label": "Neighbourhood Watch Group",
        "viral_text": "Forwarded as received: Proud moment for every Indian! UNESCO has just officially declared India's National Anthem 'Jana Gana Mana' as the BEST National Anthem in the world among 193 countries. BBC has confirmed this news. Do not break the chain, forward to at least 10 people today!",
        "category": "Social Media Chain Rumor",
        "is_forwarded": True,
        "simulated_verdict": "CONTRADICTED"
    },
    {
        "id": "preset_rbi_gdp_projection",
        "platform": "telegram",
        "title": "Telegram News Channel: RBI Raises FY27 GDP Projection",
        "sender_label": "India Economic Pulse (Telegram)",
        "viral_text": "RBI Monetary Policy Committee has raised the FY27 GDP growth projection by 40 basis points to 7.1 percent, citing strong domestic capital expenditure and resilient agricultural output across key states.",
        "category": "Economy & Markets",
        "is_forwarded": False,
        "simulated_verdict": "SUPPORTED"
    },
    {
        "id": "preset_emergency_curfew",
        "platform": "telegram",
        "title": "Viral Telegram Alert: Nationwide 15-Day Army Curfew",
        "sender_label": "Breaking News Alerts (Forwarded)",
        "viral_text": "URGENT BREAKING: Central government has declared nationwide military lockdown and emergency curfew starting tonight at 10 PM. All grocery stores, chemist shops, and petrol stations will be shut down for 15 days. Army convoys moving into cities. Store essentials immediately!",
        "category": "Public Safety Panic",
        "is_forwarded": True,
        "simulated_verdict": "CONTRADICTED"
    }
]


class BotBridgeManager:
    """
    Production-ready bridge and webhook dispatcher for WhatsApp & Telegram fact-checking bots.
    Cleans forwarded noise, coordinates with Gemini Agentic RAG, and produces high-readability chat cards.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.whatsapp_token = os.getenv("WHATSAPP_TOKEN")

    def sanitize_forwarded_text(self, text: str) -> str:
        """Strips out forward headers, chain-letter threats, and spam punctuation to isolate the core claim."""
        if not text:
            return ""

        cleaned = text.strip()

        # Remove common chain letter prefixes
        chain_prefixes = [
            r"(?i)^forwarded\s+as\s+received\s*[:\n\-]*",
            r"(?i)^forwarded\s+many\s+times\s*[:\n\-]*",
            r"(?i)^urgent\s+warning\s*[:\n\-!]*",
            r"(?i)^urgent\s+breaking\s*[:\n\-!]*",
            r"(?i)^breaking\s+news\s*[:\n\-!]*",
            r"(?i)^must\s+watch\s*[:\n\-!]*",
            r"(?i)^do\s+not\s+ignore\s*[:\n\-!]*",
            r"(?i)^proud\s+moment\s*[:\n\-!]*"
        ]
        for pat in chain_prefixes:
            cleaned = re.sub(pat, "", cleaned).strip()

        # Remove chain letter suffixes (e.g. "forward to 10 people", "share with everyone")
        chain_suffixes = [
            r"(?i)forward\s+to\s+at\s+least\s+\d+\s+people.*$",
            r"(?i)forward\s+to\s+all\s+friends\s+and\s+family.*$",
            r"(?i)share\s+with\s+\d+\s+groups.*$",
            r"(?i)do\s+not\s+break\s+the\s+chain.*$",
            r"(?i)save\s+everyone\s+from\s+huge\s+loss.*$"
        ]
        for pat in chain_suffixes:
            cleaned = re.sub(pat, "", cleaned).strip()

        # Remove excessive repeated emojis (keep reasonable punctuation)
        cleaned = re.sub(r"[⚠️🚨🛑❌✅‼️]{3,}", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned or text.strip()

    def _generate_chat_reply_markdown(
        self,
        platform: str,
        verdict: str,
        credibility_score: float,
        claim_text: str,
        explanation: str,
        top_sources: List[str],
        shareable_url: str
    ) -> str:
        """Builds an authentic, beautifully formatted WhatsApp/Telegram chat message bubble."""
        if verdict == "SUPPORTED":
            verdict_badge = "✅ *VERIFIED / ACCURATE*"
            emoji = "🟢"
            status_text = "AUTHENTIC"
        elif verdict == "CONTRADICTED":
            verdict_badge = "❌ *DEBUNKED / FALSE INFORMATION*"
            emoji = "🔴"
            status_text = "FABRICATED"
        else:
            verdict_badge = "⚠️ *UNVERIFIED / DISPUTED ASSERTION*"
            emoji = "🟡"
            status_text = "UNSUBSTANTIATED"

        sources_lines = ""
        if top_sources:
            sources_lines = "\n📰 *Corroborating News Wires:*\n" + "\n".join([f"  • {src}" for src in top_sources[:3]])

        # WhatsApp and Telegram both support standard *bold* and _italic_
        message = (
            f"🔍 *TruthLens AI Fact-Check Report*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{verdict_badge}\n"
            f"📊 *Credibility Index:* {credibility_score}%\n\n"
            f"📌 *Forwarded Claim:* \n\"{claim_text}\"\n\n"
            f"🔎 *Investigative Breakdown:*\n{explanation}\n"
            f"{sources_lines}\n\n"
            f"🔗 *Full Interactive Verification Dossier:*\n{shareable_url}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ _Verify any forward anytime with TruthLens Bot._"
        )
        return message

    def verify_message(self, request: BotVerificationRequest) -> BotVerificationResponse:
        """Main verification routine for chatbot interactions and webhooks."""
        raw = (request.message_text or "").strip()
        sanitized = self.sanitize_forwarded_text(raw)
        if len(sanitized) < 15:
            sanitized = raw

        rag = get_rag_verifier()
        doc_audit = rag.audit_document(
            content=sanitized,
            title="Chat Forward Claim",
            filename=f"{request.platform}_message.txt"
        )

        status_map = {
            "HIGH_CREDIBILITY": "SUPPORTED",
            "HIGH_RISK": "CONTRADICTED",
            "MIXED_CREDIBILITY": "UNVERIFIED"
        }
        verdict = status_map.get(doc_audit.overall_status.upper(), doc_audit.overall_status.upper())
        score = doc_audit.authenticity_score

        top_sources = []
        source_links = []
        if doc_audit.audited_claims and len(doc_audit.audited_claims) > 0:
            first_claim = doc_audit.audited_claims[0]
            top_sources = getattr(first_claim, "top_sources", []) or []
            source_links = getattr(first_claim, "source_links", []) or []

        headline = sanitized.split(".")[0] if "." in sanitized else sanitized[:75]
        if len(headline) > 85:
            headline = headline[:82] + "..."

        explanation = doc_audit.executive_assessment or "Verification completed against global and regional news wires."

        # Public shareable query URL for truth verification dashboard
        query_encoded = urllib.parse.quote_plus(sanitized[:120])
        shareable_url = f"http://localhost:5173/?q={query_encoded}"

        # Emoji mapping
        emoji_map = {
            "SUPPORTED": "🟢",
            "CONTRADICTED": "🔴",
            "UNVERIFIED": "🟡"
        }
        status_emoji = emoji_map.get(verdict, "⚪")

        formatted_reply = self._generate_chat_reply_markdown(
            platform=request.platform or "whatsapp",
            verdict=verdict,
            credibility_score=score,
            claim_text=sanitized[:180] + ("..." if len(sanitized) > 180 else ""),
            explanation=explanation,
            top_sources=top_sources,
            shareable_url=shareable_url
        )

        return BotVerificationResponse(
            platform=request.platform or "whatsapp",
            raw_claim=raw,
            sanitized_claim=sanitized,
            verdict=verdict,
            credibility_score=score,
            status_emoji=status_emoji,
            headline=headline,
            explanation=explanation,
            formatted_chat_reply=formatted_reply,
            top_sources=top_sources,
            source_links=source_links,
            shareable_url=shareable_url,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        )

    def process_telegram_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handles standard Telegram Bot API webhook updates."""
        message = payload.get("message", {}) or payload.get("channel_post", {})
        text = message.get("text", "") or message.get("caption", "")
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        user = message.get("from", {})
        sender_name = user.get("first_name", "Telegram User")
        is_forwarded = bool(message.get("forward_date") or message.get("forward_from") or message.get("forward_from_chat"))

        if not text:
            return {
                "status": "ignored",
                "reason": "No text content found in Telegram message."
            }

        # Check for /start or /help commands
        if text.strip().lower() in ["/start", "/help"]:
            welcome_msg = (
                "👋 *Welcome to TruthLens AI Fact-Checker Bot!*\n\n"
                "Forward any news message, viral rumor, or text here.\n"
                "I will cross-reference it with live global news wires and fact-checking registries in real-time."
            )
            return {
                "status": "command",
                "chat_id": chat_id,
                "reply_text": welcome_msg
            }

        req = BotVerificationRequest(
            message_text=text,
            platform="telegram",
            sender_id=str(chat_id) if chat_id else None,
            sender_name=sender_name,
            is_forwarded=is_forwarded
        )
        res = self.verify_message(req)

        return {
            "status": "ok",
            "chat_id": chat_id,
            "reply_text": res.formatted_chat_reply,
            "verification_data": res.dict()
        }

    def process_whatsapp_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handles standard WhatsApp Cloud API / Twilio webhook events."""
        # Check WhatsApp Cloud API structure
        entry = (payload.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages and len(messages) > 0:
            msg = messages[0]
            text = (msg.get("text") or {}).get("body", "")
            sender_id = msg.get("from")
            is_forwarded = bool(msg.get("context", {}).get("forwarded"))
        else:
            # Fallback to Twilio WhatsApp webhook format (Body, From, WaId)
            text = payload.get("Body", "") or payload.get("text", "")
            sender_id = payload.get("From", "") or payload.get("WaId", "")
            is_forwarded = True

        if not text:
            return {
                "status": "ignored",
                "reason": "No text body in WhatsApp message."
            }

        req = BotVerificationRequest(
            message_text=text,
            platform="whatsapp",
            sender_id=str(sender_id),
            sender_name="WhatsApp Contact",
            is_forwarded=is_forwarded
        )
        res = self.verify_message(req)

        return {
            "status": "ok",
            "recipient_id": sender_id,
            "reply_text": res.formatted_chat_reply,
            "verification_data": res.dict()
        }

    def get_presets(self) -> List[BotPresetScenario]:
        """Returns the curated list of realistic viral forwarded claims."""
        return [BotPresetScenario(**p) for p in VIRAL_BOT_PRESETS]


_bot_bridge_instance: Optional[BotBridgeManager] = None

def get_bot_bridge() -> BotBridgeManager:
    global _bot_bridge_instance
    if _bot_bridge_instance is None:
        _bot_bridge_instance = BotBridgeManager()
    return _bot_bridge_instance
