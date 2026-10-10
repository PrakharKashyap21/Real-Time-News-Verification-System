import unittest
from unittest.mock import MagicMock, patch

from backend.app.v2.bot_bridge import BotBridgeManager, get_bot_bridge
from backend.app.v2.schemas import BotVerificationRequest, BotVerificationResponse, DocumentAuditResponse


class TestBotBridge(unittest.TestCase):

    def setUp(self):
        self.bridge = BotBridgeManager()

    def test_sanitize_forwarded_text(self):
        raw_msg = (
            "Forwarded as received:\n"
            "⚠️ URGENT WARNING FROM RBI! ⚠️\n"
            "Any 500 note where the green security line is near the signature is fake!\n"
            "Forward to all friends and family groups to save everyone from huge loss!"
        )
        cleaned = self.bridge.sanitize_forwarded_text(raw_msg)
        self.assertNotIn("Forwarded as received", cleaned)
        self.assertNotIn("Forward to all friends", cleaned)
        self.assertIn("Any 500 note", cleaned)

    def test_get_presets(self):
        presets = self.bridge.get_presets()
        self.assertGreaterEqual(len(presets), 3)
        self.assertEqual(presets[0].id, "preset_500_currency_fake")
        self.assertIn(presets[0].platform, ["whatsapp", "telegram"])

    def test_telegram_start_command(self):
        payload = {
            "update_id": 10001,
            "message": {
                "message_id": 1,
                "chat": {"id": 123456789},
                "from": {"first_name": "Prakhar"},
                "text": "/start"
            }
        }
        res = self.bridge.process_telegram_webhook(payload)
        self.assertEqual(res["status"], "command")
        self.assertEqual(res["chat_id"], 123456789)
        self.assertIn("TruthLens AI Fact-Checker Bot", res["reply_text"])

    @patch("backend.app.v2.bot_bridge.get_rag_verifier")
    def test_verify_message(self, mock_get_rag):
        mock_rag = MagicMock()
        mock_audit = MagicMock()
        mock_audit.overall_status = "HIGH_RISK"
        mock_audit.authenticity_score = 12.0
        mock_audit.executive_assessment = "PIB and RBI have officially refuted this viral forward."
        mock_audit.audited_claims = []
        mock_rag.audit_document.return_value = mock_audit
        mock_get_rag.return_value = mock_rag

        req = BotVerificationRequest(
            message_text="RBI issues alert that 500 notes with green line near signature are invalid.",
            platform="whatsapp",
            is_forwarded=True
        )
        res = self.bridge.verify_message(req)
        self.assertIsInstance(res, BotVerificationResponse)
        self.assertEqual(res.verdict, "CONTRADICTED")
        self.assertEqual(res.credibility_score, 12.0)
        self.assertIn("DEBUNKED", res.formatted_chat_reply)
        self.assertIn("TruthLens AI Fact-Check Report", res.formatted_chat_reply)


if __name__ == "__main__":
    unittest.main()
