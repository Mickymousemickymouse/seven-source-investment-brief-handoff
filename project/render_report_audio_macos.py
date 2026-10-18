"""Render a verified report to the configured local Mac audio directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from digest.audio import render_macos


CONFIG_PATH = Path(__file__).with_name("mac_audio_config.json")


def audio_directory(config_path: Path = CONFIG_PATH) -> Path:
    configured = json.loads(config_path.read_text(encoding="utf-8"))["mac_audio_dir"]
    directory = Path(configured)
    if not directory.is_absolute():
        raise ValueError("Mac 音频目录必须使用绝对路径")
    return directory


def render_report(report_path: Path, config_path: Path = CONFIG_PATH) -> tuple[Path, Path]:
    destination = audio_directory(config_path) / f"{report_path.stem}.wav"
    receipt_path = destination.with_name(f"{destination.stem}-receipt.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt = render_macos(report_path.read_text(encoding="utf-8"), destination)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination, receipt_path


def main() -> None:
    parser = argparse.ArgumentParser(description="将报告正文朗读到本机 Mac 音频目录")
    parser.add_argument("report", type=Path, help="已核对报告的 Markdown 文件")
    args = parser.parse_args()
    audio_path, receipt_path = render_report(args.report)
    print(json.dumps({"audio": str(audio_path), "receipt": str(receipt_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
