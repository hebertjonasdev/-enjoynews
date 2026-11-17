"""Stock footage search and download (Pexels + Pixabay free APIs)."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console
from tqdm.asyncio import tqdm

from .models import FootageClip, VideoConfig

console = Console()


class PexelsClient:
    """Pexels API client for video search."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/videos"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": api_key},
        )

    async def search_videos(
        self,
        query: str,
        orientation: str = "portrait",
        size: str = "medium",
        per_page: int = 5,
    ) -> list[dict]:
        """Search for videos."""
        params = {
            "query": query,
            "orientation": orientation,
            "size": size,
            "per_page": per_page,
        }
        resp = await self.client.get(f"{self.base_url}/search", params=params)
        resp.raise_for_status()
        return resp.json().get("videos", [])

    async def get_popular_videos(self, per_page: int = 10) -> list[dict]:
        """Get popular videos as fallback."""
        resp = await self.client.get(f"{self.base_url}/popular", params={"per_page": per_page})
        resp.raise_for_status()
        return resp.json().get("videos", [])

    async def download_video(self, video_files: list[dict], output_path: Path) -> bool:
        """Download best quality vertical video file."""
        # Prefer portrait 1080x1920 or similar
        best_file = None
        for vf in video_files:
            w, h = vf.get("width", 0), vf.get("height", 0)
            if h > w and h >= 1080:  # Vertical, at least 1080p height
                if best_file is None or (vf.get("height", 0) < best_file.get("height", 0)):
                    best_file = vf

        if not best_file:
            # Fallback: any vertical
            for vf in video_files:
                if vf.get("height", 0) > vf.get("width", 0):
                    best_file = vf
                    break

        if not best_file:
            return False

        try:
            resp = await self.client.get(best_file["link"], timeout=60.0)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return True
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            return False

    async def close(self):
        await self.client.aclose()


class PixabayClient:
    """Pixabay API client for video search."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pixabay.com/api/videos"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_videos(
        self,
        query: str,
        orientation: str = "vertical",
        per_page: int = 5,
    ) -> list[dict]:
        params = {
            "key": self.api_key,
            "q": query,
            "orientation": orientation,
            "per_page": per_page,
            "video_type": "film",
        }
        resp = await self.client.get(self.base_url, params=params)
        resp.raise_for_status()
        return resp.json().get("hits", [])

    async def download_video(self, video_data: dict, output_path: Path) -> bool:
        """Download video from Pixabay (selects best vertical quality)."""
        videos = video_data.get("videos", {})
        # Prefer large vertical
        best = videos.get("large") or videos.get("medium") or videos.get("small")
        if not best:
            return False

        url = best.get("url")
        if not url:
            return False

        try:
            resp = await self.client.get(url, timeout=60.0)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return True
        except Exception as e:
            console.print(f"[red]Pixabay download failed: {e}[/red]")
            return False

    async def close(self):
        await self.client.aclose()


# Keyword mapping for news categories → footage search terms
CATEGORY_KEYWORDS = {
    "Política": ["government building", "congress", "voting", "flag", "capital city"],
    "Brasil": ["brazil", "brazilian flag", "brasilia", "rio de janeiro", "sao paulo"],
    "Mundo": ["world map", "globe", "international flags", "united nations", "diplomacy"],
    "Economia": ["stock market", "financial district", "currency", "trading", "bank"],
    "Tecnologia": ["artificial intelligence", "server room", "coding", "smartphone", "robot"],
    "Ciência": ["laboratory", "scientist", "research", "dna", "space", "telescope"],
    "Saúde": ["hospital", "doctor", "medical", "vaccine", "healthcare"],
    "Meio Ambiente": ["forest", "climate change", "renewable energy", "ocean", "wildlife"],
    "Latino-América": ["latin america", "south america map", "buenos aires", "mexico city", "santiago"],
    "Esportes": ["stadium", "football", "soccer", "olympics", "athlete"],
    "Cultura": ["theater", "museum", "art gallery", "music", "book"],
    "Educação": ["university", "classroom", "students", "graduation", "library"],
    "default": ["news studio", "breaking news", "journalist", "microphone", "camera"],
}


def get_search_queries(category: str | None, headline: str) -> list[str]:
    """Generate search queries from category and headline."""
    queries = []

    # Category-based
    if category:
        queries.extend(CATEGORY_KEYWORDS.get(category, CATEGORY_KEYWORDS["default"]))

    # Extract keywords from headline (simple approach)
    import re
    words = re.findall(r"\b[A-Za-zÀ-ÿ]{4,}\b", headline)
    # Filter common words
    stopwords = {"para", "com", "dos", "das", "que", "uma", "mais", "muito", "sobre", "entre",
                 "após", "antes", "durante", "contra", "desde", "até", "onde", "como", "quando",
                 "the", "and", "for", "with", "from", "that", "this", "have", "been", "were"}
    keywords = [w.lower() for w in words if w.lower() not in stopwords and len(w) > 3]
    queries.extend(keywords[:3])

    return queries[:5]  # Max 5 queries


async def fetch_footage_for_news(
    news_items: list,
    config: VideoConfig,
    max_clips: int = 5,
) -> list[FootageClip]:
    """Fetch stock footage for news items."""
    clips = []
    temp_dir = Path(tempfile.mkdtemp(prefix="enjoynews_footage_"))

    pexels = PexelsClient(config.pexels_key) if config.pexels_key else None
    pixabay = PixabayClient(config.pixabay_key) if config.pixabay_key else None

    if not pexels and not pixabay:
        console.print("[yellow]No stock footage API keys configured[/yellow]")
        return []

    queries_used = set()

    for item in news_items[:max_clips]:
        category = item.category if hasattr(item, 'category') else item.get('category')
        headline = item.primary_headline if hasattr(item, 'primary_headline') else item.get('primary_headline', '')

        queries = get_search_queries(category, headline)

        for query in queries:
            if query in queries_used:
                continue
            queries_used.add(query)

            # Try Pexels first
            if pexels:
                try:
                    videos = await pexels.search_videos(query, orientation="portrait", per_page=3)
                    for vid in videos:
                        clip_path = temp_dir / f"pexels_{vid['id']}.mp4"
                        if await pexels.download_video(vid.get("video_files", []), clip_path):
                            clips.append(FootageClip(
                                url=clip_path,
                                duration=vid.get("duration", 10),
                                width=1080,
                                height=1920,
                                source="pexels",
                                search_query=query,
                                attribution=f"Pexels / {vid.get('user', {}).get('name', 'Unknown')}",
                            ))
                            if len(clips) >= max_clips:
                                break
                except Exception as e:
                    console.print(f"[yellow]Pexels error for '{query}': {e}[/yellow]")

            if len(clips) >= max_clips:
                break

            # Try Pixabay
            if pixabay:
                try:
                    videos = await pixabay.search_videos(query, orientation="vertical", per_page=3)
                    for vid in videos:
                        clip_path = temp_dir / f"pixabay_{vid['id']}.mp4"
                        if await pixabay.download_video(vid, clip_path):
                            clips.append(FootageClip(
                                url=clip_path,
                                duration=vid.get("duration", 10),
                                width=1080,
                                height=1920,
                                source="pixabay",
                                search_query=query,
                                attribution=f"Pixabay / {vid.get('user', 'Unknown')}",
                            ))
                            if len(clips) >= max_clips:
                                break
                except Exception as e:
                    console.print(f"[yellow]Pixabay error for '{query}': {e}[/yellow]")

            if len(clips) >= max_clips:
                break

    if pexels:
        await pexels.close()
    if pixabay:
        await pixabay.close()

    console.print(f"[green]Downloaded {len(clips)} footage clips[/green]")
    return clips


async def main():
    """Test footage fetching."""
    config = VideoConfig(
        pexels_key=os.getenv("PEXELS_KEY"),
        pixabay_key=os.getenv("PIXABAY_KEY"),
    )

    # Mock news items
    class MockItem:
        category = "Tecnologia"
        primary_headline = "Câmara aprova regulação de inteligência artificial"

    clips = await fetch_footage_for_news([MockItem()], config, max_clips=3)
    for clip in clips:
        print(f"  {clip.source}: {clip.url} ({clip.duration}s) - {clip.search_query}")


if __name__ == "__main__":
    asyncio.run(main())