import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from render_report_audio_macos import CONFIG_PATH, audio_directory, render_report


class MacAudioEntrypointTests(unittest.TestCase):
    def test_configured_output_is_local_music_directory(self):
        if not CONFIG_PATH.is_file():
            self.skipTest("目标设备尚未创建本机音频配置")
        directory = audio_directory(CONFIG_PATH)
        self.assertTrue(directory.is_absolute())
        self.assertNotIn("REPLACE_WITH_LOCAL_USER", str(directory))

    def test_render_uses_configured_directory_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = folder / "2026-10-15-2100.md"
            report.write_text("# 已核对报告", encoding="utf-8")
            config = folder / "mac_audio_config.json"
            config.write_text(json.dumps({"mac_audio_dir": str(folder / "local-audio")}), encoding="utf-8")
            with patch("render_report_audio_macos.render_macos", return_value={"complete": True}) as render:
                audio_path, receipt_path = render_report(report, config)
            self.assertEqual(audio_path, folder / "local-audio/2026-10-15-2100.wav")
            render.assert_called_once_with("# 已核对报告", audio_path)
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8")), {"complete": True})

    def test_relative_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text('{"mac_audio_dir": "outputs/audio"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "绝对路径"):
                audio_directory(config)


if __name__ == "__main__":
    unittest.main()
