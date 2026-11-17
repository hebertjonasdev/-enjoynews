"""Pydantic models for video pipeline."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from pydantic import BaseModel, Field, HttpUrl


class VideoConfig(BaseModel):
    """Runtime configuration for video generation."""
    output_dir: str = "output"
    width: int = 1080
    height: int = 1920  # 9:16 vertical
    fps: int = 30
    target_duration: float = 40.0  # seconds
    font_size: int = 48
    font_color: str = "#FFFFFF"
    font_stroke_color: str = "#000000"
    font_stroke_width: int = 2
    background_color: str = "#1A1A1A"
    branding_text: str = "EnjoyNews"
    branding_color: str = "#E86C00"
    music_volume: float = 0.15
    tts_voice: str = "pt-BR-ThalitaMultilingualNeural"  # edge-tts voice
    tts_rate: str = "+0%"
    tts_volume: str = "+0%"
    pexels_key: str | None = None
    pixabay_key: str | None = None
    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_refresh_token: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_access_token: str | None = None


class NewsItem(BaseModel):
    """News item from cluster index."""
    id: str
    theme: str
    primary_id: str
    primary_headline: str
    importance: int
    category: str | None = None
    url: str


class VideoScript(BaseModel):
    """Generated video script."""
    text: str
    duration_estimate: float  # seconds
    word_count: int
    news_items: list[NewsItem] = Field(default_factory=list)


class FootageClip(BaseModel):
    """Stock footage clip."""
    url: HttpUrl
    duration: float
    width: int
    height: int
    source: str  # pexels, pixabay
    search_query: str
    attribution: str | None = None


class VideoProject(BaseModel):
    """Complete video project."""
    date: str
    script: VideoScript
    footage: list[FootageClip] = Field(default_factory=list)
    audio_path: str | None = None
    output_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UploadResult(BaseModel):
    """Result of platform upload."""
    platform: str  # youtube, tiktok
    video_id: str | None = None
    url: str | None = None
    success: bool
    error: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)