"""Main video pipeline entry point."""
from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

import orjson
from rich.console import Console

from .models import VideoConfig, VideoProject
from .script_gen import create_video_script, load_cluster_index, select_top_news
from .compose import compose_video
from .upload import upload_to_platforms

console = Console()


def load_config_from_env() -> VideoConfig:
    """Load configuration from environment variables."""
    return VideoConfig(
        output_dir=os.getenv("VIDEO_OUTPUT_DIR", "output/video"),
        pexels_key=os.getenv("PEXELS_KEY"),
        pixabay_key=os.getenv("PIXABAY_KEY"),
        youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
        youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        tiktok_client_key=os.getenv("TIKTOK_CLIENT_KEY"),
        tiktok_client_secret=os.getenv("TIKTOK_CLIENT_SECRET"),
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
    )


async def main():
    parser = argparse.ArgumentParser(description="EnjoyNews Daily Video Generator")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Date for video (YYYY-MM-DD)")
    parser.add_argument("--output", default="output/video", help="Output directory")
    parser.add_argument("--skip-upload", action="store_true", help="Generate video but don't upload")
    parser.add_argument("--script-only", action="store_true", help="Only generate and print script")
    args = parser.parse_args()

    config = load_config_from_env()
    config.output_dir = args.output

    console.rule(f"[bold]EnjoyNews Video Pipeline - {args.date}[/bold]")

    # Generate script
    script = create_video_script(args.date, config)
    console.print(f"[cyan]Script ({script.word_count} words, ~{script.duration_estimate:.1f}s):[/cyan]")
    console.print(script.text)

    if args.script_only:
        return 0

    # Create project
    project = VideoProject(date=args.date, script=script)

    # Compose video
    try:
        output_path = await compose_video(project, config)
        console.print(f"[bold green]Video generated: {output_path}[/bold green]")
    except Exception as e:
        console.print(f"[red]Composition failed: {e}[/red]")
        return 1

    # Upload
    if not args.skip_upload:
        title = f"Resumão EnjoyNews {datetime.strptime(args.date, '%Y-%m-%d').strftime('%d/%m/%Y')}"
        description = (
            f"As principais notícias de {args.date} em 40 segundos.\n\n"
            f"📰 Portal: https://enjoynews.com.br\n"
            f"#EnjoyNews #Noticias #Resumo #Shorts"
        )
        results = await upload_to_platforms(output_path, title, description, config)

        for result in results:
            if result.success:
                console.print(f"[green]✓ {result.platform}: {result.url}[/green]")
            else:
                console.print(f"[red]✗ {result.platform}: {result.error}[/red]")

    console.rule("[bold green]Video pipeline complete[/bold green]")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)