"""Upload video to YouTube Shorts and TikTok."""
from __future__ import annotations

import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from rich.console import Console

from .models import UploadResult, VideoConfig

console = Console()

# YouTube API scopes
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_TOKEN_FILE = Path("youtube_token.pickle")

# TikTok API
TIKTOK_UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


class YouTubeUploader:
    """Upload videos to YouTube (Shorts)."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self.credentials: Optional[Credentials] = None
        self.youtube = None

    def authenticate(self) -> bool:
        """Authenticate with YouTube API using OAuth2."""
        creds = None

        # Load existing token
        if YOUTUBE_TOKEN_FILE.exists():
            with open(YOUTUBE_TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not (self.config.youtube_client_id and self.config.youtube_client_secret):
                    console.print("[red]YouTube OAuth credentials not configured[/red]")
                    return False

                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": self.config.youtube_client_id,
                            "client_secret": self.config.youtube_client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["http://localhost:8080"],
                        }
                    },
                    YOUTUBE_SCOPES,
                )
                creds = flow.run_local_server(port=8080)

            # Save token
            with open(YOUTUBE_TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        self.credentials = creds
        self.youtube = build("youtube", "v3", credentials=creds)
        return True

    def upload_shorts(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> UploadResult:
        """Upload video as YouTube Short."""
        if not self.youtube:
            if not self.authenticate():
                return UploadResult(
                    platform="youtube",
                    success=False,
                    error="Authentication failed",
                )

        # Prepare metadata
        body = {
            "snippet": {
                "title": title[:100],  # Max 100 chars
                "description": description[:5000],
                "tags": tags or ["EnjoyNews", "noticias", "resumo", "brasil", "shorts"],
                "categoryId": "25",  # News & Politics
                "defaultLanguage": "pt",
                "defaultAudioLanguage": "pt",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        # Media upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=1024 * 1024,
            resumable=True,
            mimetype="video/mp4",
        )

        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    console.print(f"[dim]Upload progress: {int(status.progress() * 100)}%[/dim]")

            video_id = response["id"]
            video_url = f"https://youtube.com/shorts/{video_id}"

            console.print(f"[green]YouTube Short uploaded: {video_url}[/green]")
            return UploadResult(
                platform="youtube",
                video_id=video_id,
                url=video_url,
                success=True,
            )

        except Exception as e:
            console.print(f"[red]YouTube upload failed: {e}[/red]")
            return UploadResult(
                platform="youtube",
                success=False,
                error=str(e),
            )


class TikTokUploader:
    """Upload videos to TikTok."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self.access_token = config.tiktok_access_token

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str = "",
    ) -> UploadResult:
        """Upload video to TikTok."""
        if not all([self.config.tiktok_client_key, self.config.tiktok_client_secret, self.access_token]):
            return UploadResult(
                platform="tiktok",
                success=False,
                error="TikTok credentials not configured",
            )

        # TikTok uses a two-step upload: init -> upload chunks -> complete
        # For simplicity, using the direct post API (requires video < 100MB)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Step 1: Initialize upload
        init_data = {
            "post_info": {
                "title": title[:150],
                "description": description[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_path.stat().st_size,
                "chunk_size": video_path.stat().st_size,
                "total_chunk_count": 1,
            },
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                # Init
                resp = client.post(TIKTOK_UPLOAD_URL, headers=headers, json=init_data)
                resp.raise_for_status()
                init_result = resp.json()

                if init_result.get("error", {}).get("code") != "ok":
                    return UploadResult(
                        platform="tiktok",
                        success=False,
                        error=init_result["error"]["message"],
                    )

                upload_url = init_result["data"]["upload_url"]
                video_id = init_result["data"]["video_id"]

                # Upload video file
                with open(video_path, "rb") as f:
                    upload_headers = {"Content-Range": f"bytes 0-{video_path.stat().st_size - 1}/{video_path.stat().st_size}"}
                    upload_resp = client.put(upload_url, headers=upload_headers, content=f.read())
                    upload_resp.raise_for_status()

            video_url = f"https://www.tiktok.com/@enjoynews/video/{video_id}"
            console.print(f"[green]TikTok video uploaded: {video_url}[/green]")
            return UploadResult(
                platform="tiktok",
                video_id=video_id,
                url=video_url,
                success=True,
            )

        except Exception as e:
            console.print(f"[red]TikTok upload failed: {e}[/red]")
            return UploadResult(
                platform="tiktok",
                success=False,
                error=str(e),
            )


def get_youtube_auth_url(config: VideoConfig) -> str:
    """Generate OAuth2 authorization URL for YouTube (run once to get refresh token)."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": config.youtube_client_id,
                "client_secret": config.youtube_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080"],
            }
        },
        scopes=YOUTUBE_SCOPES,
        redirect_uri="http://localhost:8080",
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


async def upload_to_platforms(
    video_path: Path,
    title: str,
    description: str,
    config: VideoConfig,
) -> list[UploadResult]:
    """Upload to all configured platforms."""
    results = []

    # YouTube Shorts
    if config.youtube_client_id and config.youtube_client_secret:
        yt = YouTubeUploader(config)
        result = yt.upload_shorts(video_path, title, description)
        results.append(result)

    # TikTok
    if config.tiktok_client_key and config.tiktok_client_secret and config.tiktok_access_token:
        tt = TikTokUploader(config)
        result = tt.upload_video(video_path, title, description)
        results.append(result)

    return results


def main():
    """CLI for uploading videos."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Upload video to platforms")
    parser.add_argument("--file", required=True, help="Path to video file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--shorts", action="store_true", help="Upload to YouTube Shorts")
    parser.add_argument("--tiktok", action="store_true", help="Upload to TikTok")
    parser.add_argument("--youtube-auth", action="store_true", help="Generate YouTube auth URL")
    args = parser.parse_args()

    if args.youtube_auth:
        from dotenv import load_dotenv
        load_dotenv()
        config = VideoConfig(
            youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID"),
            youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
        )
        print("Visit this URL to authorize:")
        print(get_youtube_auth_url(config))
        return

    if not args.shorts and not args.tiktok:
        print("Specify --shorts and/or --tiktok")
        return

    # Load config
    config = VideoConfig(
        youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
        youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        tiktok_client_key=os.getenv("TIKTOK_CLIENT_KEY"),
        tiktok_client_secret=os.getenv("TIKTOK_CLIENT_SECRET"),
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
    )

    video_path = Path(args.file)
    if not video_path.exists():
        print(f"File not found: {video_path}")
        return

    # Run uploads
    import asyncio
    results = asyncio.run(upload_to_platforms(video_path, args.title, args.description, config))

    for result in results:
        if result.success:
            print(f"✓ {result.platform}: {result.url}")
        else:
            print(f"✗ {result.platform}: {result.error}")


if __name__ == "__main__":
    main()