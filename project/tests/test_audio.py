import unittest
import tempfile
import wave
from pathlib import Path

from digest.audio import _voice_chunks, narration_text, verify_macos


class AudioInputTests(unittest.TestCase):
    def test_full_body_and_exclusions(self):
        report = "# 标题\n元数据\n## 本期最重要的5条\n1. **消息**正文。（来源：甲）\n## 一、市场复盘\n美股走势。\n## 完整7源覆盖表\n不播\n"
        spoken = narration_text(report)
        self.assertIn("消息正文", spoken)
        self.assertIn("美股走势", spoken)
        self.assertNotIn("元数据", spoken)
        self.assertNotIn("来源", spoken)
        self.assertNotIn("不播", spoken)

    def test_english_phrase_uses_approved_voice(self):
        chunks = _voice_chunks("人工智能 OpenAI earnings 上升")
        self.assertIn(("Samantha", "OpenAI earnings"), chunks)

    def test_evening_opening_and_current_report_hash(self):
        report = "# 10月15日晚报\n## 本期最重要的5条\n1. **消息**正文。（来源：甲；乙）\n## 完整7源覆盖表\n不播\n"
        spoken = narration_text(report)
        self.assertTrue(spoken.startswith("晚上好，下面是今天的晚报内容播报。"))
        self.assertIn("消息正文", spoken)
        self.assertNotIn("来源", spoken)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "audio.wav"
            with wave.open(str(destination), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(22050)
                audio.writeframes(b"\0" * 22050 * 2)
            import hashlib
            receipt = {"narration_sha256": hashlib.sha256(spoken.encode()).hexdigest(),
                       "duration_seconds": 1.0}
            checked = verify_macos(report, destination, receipt)
            self.assertTrue(checked["matches_report"] and checked["file_verified"])
            with self.assertRaisesRegex(ValueError, "报告正文不一致"):
                verify_macos(report.replace("消息", "新消息"), destination, checked)


if __name__ == "__main__":
    unittest.main()
