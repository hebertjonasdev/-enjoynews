"""Video composition with ffmpeg: footage + TTS + subtitles + branding."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

import ffmpeg
from rich.console import Console

from .models import VideoConfig, VideoProject, FootageClip

console = Console()


class VideoComposer:
    """Compose final video using ffmpeg."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self.temp_dir = Path(tempfile.mkdtemp(prefix="enjoynews_compose_"))

    def _create_background(self, duration: float) -> Path:
        """Create solid color background video."""
        output = self.temp_dir / "background.mp4"
        (
            ffmpeg
            .input(f"color=c={self.config.background_color}:size={self.config.width}x{self.config.height}:rate={self.config.fps}", f="lavfi", t=duration)
            .output(str(output), vcodec="libx264", pix_fmt="yuv420p")
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    def _resize_and_pad_clip(self, clip_path: Path, target_duration: float) -> Path:
        """Resize clip to 9:16 with padding/crop, loop/truncate to target duration."""
        output = self.temp_dir / f"resized_{clip_path.stem}.mp4"

        # Get clip info
        probe = ffmpeg.probe(str(clip_path))
        video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
        w, h = int(video_info["width"]), int(video_info["height"])
        clip_duration = float(video_info.get("duration", 10))

        # Calculate scale to fit 1080x1920 keeping aspect ratio
        target_w, target_h = self.config.width, self.config.height
        scale_w = target_w / w
        scale_h = target_h / h
        scale = min(scale_w, scale_h)

        new_w = int(w * scale)
        new_h = int(h * scale)

        # Filter chain: scale -> pad to center -> loop/truncate
        (
            ffmpeg
            .input(str(clip_path))
            .filter("scale", new_w, new_h)
            .filter("pad", target_w, target_h, "(ow-iw)/2", "(oh-ih)/2", color=self.config.background_color)
            .filter("tpad", stop_mode="clone", stop_duration=target_duration)
            .output(str(output), vcodec="libx264", pix_fmt="yuv420p", t=target_duration, r=self.config.fps)
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    def _create_subtitle_filter(self, srt_path: Path) -> str:
        """Create ffmpeg subtitles filter with styling."""
        # Escape path for ffmpeg
        escaped_path = str(srt_path).replace("'", r"'\''").replace(":", r"\:")
        return (
            f"subtitles='{escaped_path}':"
            f"force_style='FontName=DejaVu Sans,FontSize={self.config.font_size},"
            f"PrimaryColour=&H{self.config.font_color[1:]},"
            f"OutlineColour=&H{self.config.font_stroke_color[1:]},"
            f"Outline={self.config.font_stroke_width},"
            f"Alignment=2,MarginV=150'"
        )

    def _create_branding_overlay(self, duration: float) -> Path:
        """Create branding text overlay (EnjoyNews logo/text)."""
        output = self.temp_dir / "branding.mp4"

        # Create text overlay with drawtext
        (
            ffmpeg
            .input(f"color=c=transparent:size={self.config.width}x{self.config.height}:rate={self.config.fps}", f="lavfi", t=duration)
            .filter("drawtext",
                text=self.config.branding_text,
                fontcolor=self.config.branding_color,
                fontsize=36,
                fontfile="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                x="(w-text_w)/2",
                y="h-th-100",
                enable=f"between(t,0,{duration})"
            )
            .output(str(output), vcodec="libx264", pix_fmt="yuva420p")
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    def compose(
        self,
        project: VideoProject,
        audio_path: Path,
        srt_path: Path,
        footage_clips: list[FootageClip],
    ) -> Path:
        """Compose final video."""
        console.print("[bold cyan]Composing video...[/bold cyan]")

        # Get audio duration
        audio_probe = ffmpeg.probe(str(audio_path))
        audio_duration = float(audio_probe["format"]["duration"])

        # Target duration (use audio duration, cap at target)
        target_duration = min(audio_duration, self.config.target_duration)

        # Prepare video segments
        segment_paths = []

        # If we have footage, use it; otherwise create background
        if footage_clips:
            # Distribute footage across duration
            clip_duration = target_duration / len(footage_clips)
            for i, clip in enumerate(footage_clips):
                resized = self._resize_and_pad_clip(Path(str(clip.url)), clip_duration)
                segment_paths.append(resized)
        else:
            # Solid background
            bg = self._create_background(target_duration)
            segment_paths = [bg]

        # Concatenate segments
        concat_file = self.temp_dir / "concat.txt"
        concat_file.write_text("\n".join(f"file '{p}'" for p in segment_paths))

        concatenated = self.temp_dir / "concatenated.mp4"
        (
            ffmpeg
            .input(str(concat_file), f="concat", safe=0)
            .output(str(concatenated), vcodec="libx264", pix_fmt="yuv420p")
            .overwrite_output()
            .run(quiet=True)
        )

        # Add subtitles
        subtitled = self.temp_dir / "subtitled.mp4"
        subtitle_filter = self._create_subtitle_filter(srt_path)
        (
            ffmpeg
            .input(str(concatenated))
            .filter("subtitles", str(srt_path).replace(":", r"\:"), force_style=(
                f"FontName=DejaVu Sans,FontSize={self.config.font_size},"
                f"PrimaryColour=&H{self.config.font_color[1:]},"
                f"OutlineColour=&H{self.config.font_stroke_color[1:]},"
                f"Outline={self.config.font_stroke_width},"
                f"Alignment=2,MarginV=150"
            ))
            .output(str(subtitled), vcodec="libx264", pix_fmt="yuv420p")
            .overwrite_output()
            .run(quiet=True)
        )

        # Add branding overlay
        branded = self.temp_dir / "branded.mp4"
        branding = self._create_branding_overlay(target_duration)
        (
            ffmpeg
            .input(str(subtitled))
            .input(str(branding))
            .filter("overlay", "(W-w)/2", "H-h-100")
            .output(str(branded), vcodec="libx264", pix_fmt="yuv420p", t=target_duration)
            .overwrite_output()
            .run(quiet=True)
        )

        # Add audio
        final_output = self.temp_dir / "final.mp4"
        (
            ffmpeg
            .input(str(branded))
            .input(str(audio_path))
            .output(
                str(final_output),
                vcodec="libx264",
                acodec="aac",
                audio_bitrate="128k",
                pix_fmt="yuv420p",
                t=target_duration,
                **{"map": "0:v:0", "map": "1:a:0"}
            )
            .overwrite_output()
            .run(quiet=True)
        )

        # Add background music (optional - low volume)
        if self.config.music_volume > 0:
            # Would need royalty-free music file
            pass

        console.print(f"[green]Video composed: {final_output}[/green]")
        return final_output


async def compose_video(
    project: VideoProject,
    config: VideoConfig,
) -> Path:
    """Main composition function."""
    composer = VideoComposer(config)

    # Generate TTS with subtitles
    from .tts import text_to_speech_with_subtitles, generate_subtitle_srt

    audio_path, boundaries = await text_to_speech_with_subtitles(
        project.script.text,
        voice=config.tts_voice,
        rate=config.tts_rate,
        volume=config.tts_volume,
    )

    srt_content = generate_subtitle_srt(boundaries)
    srt_path = audio_path.with_suffix(".srt")
    srt_path.write_text(srt_content, encoding="utf-8")

    # Fetch footage if not already in project
    footage = project.footage
    if not footage:
        from .footage import fetch_footage_for_news
        footage = await fetch_footage_for_news(project.script.news_items, config)

    # Compose
    final_path = composer.compose(project, audio_path, srt_path, footage)

    # Copy to project output
    output_path = Path(config.output_dir) / f"enjoynews_{project.date}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.replace(output_path)

    project.output_path = str(output_path)
    project.audio_path = str(audio_path)

    return output_path


if __name__ == "__main__":
    # Test composition
    from .script_gen import create_video_script
    from .models import VideoProject

    config = VideoConfig()
    script = create_video_script("2025-01-15", config)
    project = VideoProject(date="2025-01-15", script=script)

    asyncio.run(compose_video(project, config))