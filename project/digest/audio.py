"""Offline Mac narration of the verified report body."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

MIN_FREE_BYTES = 1024 ** 3


def narration_text(markdown: str) -> str:
    """Read the complete substantive body, omitting sources and audit appendices."""
    start = re.search(r"(?m)^## (?!完整7源覆盖表)", markdown)
    end = re.search(r"(?m)^## 完整7源覆盖表\s*$", markdown)
    if not start or not end or end.start() <= start.start():
        raise ValueError("正文音频边界缺失或倒置")
    body = markdown[start.start():end.start()]
    body = re.sub(r"（来源：[^）]*）", "", body)
    body = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"(?m)^#{2,4}\s*", "", body)
    body = re.sub(r"(?m)^\s*(\d+)\.\s+", r"第\1条，", body)
    body = re.sub(r"[*_`|]", "", body)
    body = re.sub(r"(?m)^\s*:?-{3,}:?\s*$", "", body)
    lines = [re.sub(r"\s+", " ", line).strip() for line in body.splitlines()]
    spoken = "\n".join(line for line in lines if line)
    title = markdown.splitlines()[0] if markdown.splitlines() else ""
    if "晨报" in title:
        return "早上好，下面是今天的隔夜市场信息播报。\n" + spoken
    if "晚报" in title:
        return "晚上好，下面是今天的晚报内容播报。\n" + spoken
    return spoken


def _voice_chunks(text: str) -> list[tuple[str, str]]:
    """Use Samantha for English phrases, keeping short tickers in Chinese flow."""
    phrase = re.compile(r"[A-Za-z][A-Za-z0-9&.+/-]*(?:\s+[A-Za-z][A-Za-z0-9&.+/-]*){1,}")
    chunks: list[tuple[str, str]] = []
    cursor = 0
    for match in phrase.finditer(text):
        if match.start() > cursor:
            chunks.append(("Tingting", text[cursor:match.start()]))
        chunks.append(("Samantha", match.group()))
        cursor = match.end()
    if cursor < len(text):
        chunks.append(("Tingting", text[cursor:]))
    return [(voice, content) for voice, content in chunks if content.strip()]


def render_macos(markdown: str, destination: Path) -> dict:
    """Generate a PCM WAV with only local system voices and verify the output."""
    spoken = narration_text(markdown)
    if not spoken.strip():
        raise ValueError("正文为空")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < MIN_FREE_BYTES:
        raise OSError("音频生成需要至少 1 GiB 可用磁盘空间")
    input_hash = hashlib.sha256(spoken.encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="digest-voice-", dir=destination.parent) as tmp:
        chunks = _voice_chunks(spoken)
        wave_parts: list[Path] = []
        for index, (voice, content) in enumerate(chunks):
            aiff = Path(tmp) / f"{index:04d}.aiff"
            wav = Path(tmp) / f"{index:04d}.wav"
            subprocess.run(["/usr/bin/say", "-v", voice, "-r", "175", "-o", str(aiff), content], check=True)
            subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(aiff), str(wav)], check=True)
            wave_parts.append(wav)
        pending = Path(tmp) / "complete.wav"
        with wave.open(str(pending), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            frames = 0
            for part in wave_parts:
                with wave.open(str(part), "rb") as segment:
                    if (segment.getnchannels(), segment.getsampwidth(), segment.getframerate()) != (1, 2, 22050):
                        raise ValueError("音频分段格式不一致")
                    data = segment.readframes(segment.getnframes())
                    output.writeframes(data)
                    frames += segment.getnframes()
        if pending.stat().st_size <= 44:
            raise ValueError("音频文件未生成")
        receipt = {"narration_sha256": input_hash, "duration_seconds": round(frames / 22050, 2)}
        verified = verify_macos(markdown, pending, receipt)
        pending.replace(destination)
    return {**verify_macos(markdown, destination, verified),
            "voices": sorted(set(voice for voice, _ in chunks))}


def verify_macos(markdown: str, destination: Path, receipt: dict) -> dict:
    """Recheck the final report text and the playable WAV before delivery."""
    expected = hashlib.sha256(narration_text(markdown).encode("utf-8")).hexdigest()
    if receipt.get("narration_sha256") != expected:
        raise ValueError("音频输入与当前报告正文不一致")
    with wave.open(str(destination), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 22050):
            raise ValueError("音频文件格式不正确")
        duration = round(audio.getnframes() / audio.getframerate(), 2)
    if duration <= 0 or duration != receipt.get("duration_seconds"):
        raise ValueError("音频时长不一致")
    digest = hashlib.sha256()
    with destination.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    audio_hash = digest.hexdigest()
    if receipt.get("audio_sha256") not in (None, audio_hash):
        raise ValueError("音频文件哈希不一致")
    return {**receipt, "audio_sha256": audio_hash, "bytes": destination.stat().st_size,
            "complete": True, "matches_report": True, "file_verified": True}
