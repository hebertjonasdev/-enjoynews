"""Text-to-Speech using edge-tts (free, high quality)."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

import edge_tts
from rich.console import Console

from .models import VideoConfig

console = Console()

# Recommended Portuguese voices (natural, news-anchor style)
PT_BR_VOICES = {
    "thalita": "pt-BR-ThalitaMultilingualNeural",      # Female, professional, clear
    "antonio": "pt-BR-AntonioMultilingualNeural",      # Male, deep, authoritative
    "francisca": "pt-BR-FranciscaMultilingualNeural",  # Female, warm
    "iago": "pt-BR-IagoMultilingualNeural",            # Male, young
}


async def text_to_speech(
    text: str,
    voice: str = "pt-BR-ThalitaMultilingualNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    output_path: Optional[Path] = None,
) -> Path:
    """Convert text to speech using edge-tts."""
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".mp3"))

    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(str(output_path))

    console.print(f"[green]TTS saved: {output_path} ({output_path.stat().st_size} bytes)[/green]")
    return output_path


async def text_to_speech_with_subtitles(
    text: str,
    voice: str = "pt-BR-ThalitaMultilingualNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    output_path: Optional[Path] = None,
) -> tuple[Path, list[dict]]:
    """Generate TTS and return word-level timestamps for subtitles."""
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".mp3"))

    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)

    # Collect word boundaries
    word_boundaries = []
    async for chunk in communicate.stream():
        if chunk["type"] == "WordBoundary":
            word_boundaries.append({
                "text": chunk["text"],
                "offset": chunk["offset"] / 10_000_000,  # Convert to seconds
                "duration": chunk["duration"] / 10_000_000,
            })

    await communicate.save(str(output_path))

    return output_path, word_boundaries


def generate_subtitle_srt(word_boundaries: list[dict], max_chars: int = 42, max_duration: float = 3.0) -> str:
    """Generate SRT subtitle file from word boundaries."""
    # Group words into subtitle lines
    lines = []
    current_line = []
    current_start = 0.0
    current_text = ""

    for wb in word_boundaries:
        word = wb["text"].strip()
        if not word:
            continue

        if not current_line:
            current_start = wb["offset"]

        current_line.append(word)
        current_text = " ".join(current_line)

        # Check if line is too long or duration exceeded
        line_duration = wb["offset"] + wb["duration"] - current_start

        if len(current_text) > max_chars or line_duration > max_duration:
            # Finalize previous line
            if len(current_line) > 1:
                current_line.pop()
                current_text = " ".join(current_line)
                lines.append({
                    "start": current_start,
                    "end": wb["offset"],
                    "text": current_text,
                })
                # Start new line with current word
                current_line = [word]
                current_start = wb["offset"]
            else:
                # Single long word - keep it
                lines.append({
                    "start": current_start,
                    "end": wb["offset"] + wb["duration"],
                    "text": current_text,
                })
                current_line = []
                current_text = ""

    # Add last line
    if current_line:
        last_wb = word_boundaries[-1]
        lines.append({
            "start": current_start,
            "end": last_wb["offset"] + last_wb["duration"],
            "text": current_text,
        })

    # Generate SRT
    srt_lines = []
    for i, line in enumerate(lines, 1):
        start = format_srt_time(line["start"])
        end = format_srt_time(line["end"])
        srt_lines.append(f"{i}\n{start} --> {end}\n{line['text']}\n")

    return "\n".join(srt_lines)


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT time (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


async def main():
    """Test TTS generation."""
    test_text = (
        "Bom dia, sou do EnjoyNews. As principais notícias desta terça-feira. "
        "A Câmara aprova projeto que regula inteligência artificial no Brasil. "
        "O texto estabelece princípios como transparência e responsabilidade algorítmica. "
        "No exterior, EUA e China retomam diálogo sobre clima. "
        "Outras notícias em enjoynews.com.br. Até a próxima edição."
    )

    config = VideoConfig()
    audio_path, boundaries = await text_to_speech_with_subtitles(
        test_text,
        voice=config.tts_voice,
        rate=config.tts_rate,
        volume=config.tts_volume,
    )

    srt = generate_subtitle_srt(boundaries)
    srt_path = audio_path.with_suffix(".srt")
    srt_path.write_text(srt, encoding="utf-8")

    print(f"Audio: {audio_path}")
    print(f"Subtitles: {srt_path}")
    print(f"SRT preview:\n{srt[:500]}")


if __name__ == "__main__":
    asyncio.run(main())