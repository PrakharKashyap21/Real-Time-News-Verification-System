import unittest
from backend.app.v2.audio_auditor import AudioClaimAuditor, AUDIO_SAMPLES_PRESETS
from backend.app.v2.schemas import AudioAuditResponse


class TestAudioAudit(unittest.TestCase):
    def setUp(self):
        self.auditor = AudioClaimAuditor(api_key="test_dummy_key")

    def test_audio_metadata_detection(self):
        dummy_wav_bytes = b"RIFF" + b"\x00" * 32000
        meta = self._get_metadata(dummy_wav_bytes, "test_recording.wav", "audio/wav")
        self.assertEqual(meta["format"], "WAV")
        self.assertGreater(meta["file_size_kb"], 0)
        self.assertGreaterEqual(meta["estimated_duration_sec"], 1.0)

    def _get_metadata(self, audio_bytes, filename, mime):
        return self.auditor._detect_audio_metadata(audio_bytes, filename, mime)

    def test_preset_sample_audit(self):
        self.assertTrue(len(AUDIO_SAMPLES_PRESETS) >= 3)
        sample = AUDIO_SAMPLES_PRESETS[0]
        self.assertIn("transcript", sample)
        self.assertIn("core_claim", sample)

    def test_heuristic_audio_fallback(self):
        fb = self.auditor._heuristic_audio_fallback("whatsapp_audio.mp3")
        self.assertIn("detected_language", fb)
        self.assertIn("acoustic_context", fb)
        self.assertIn("transcription", fb)
        self.assertEqual(fb["synthetic_voice_risk"], "LOW")


if __name__ == "__main__":
    unittest.main()
