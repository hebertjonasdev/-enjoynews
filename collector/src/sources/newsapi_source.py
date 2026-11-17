"""NewsAPI.org, GNews.io, Currents, MediaStack, WorldNews, Guardian source adapters."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from ..models import Category, RawArticle, SourceType


@dataclass
class NewsAPIConfig:
    api_key: str
    base_url: str = "https://newsapi.org/v2"
    language: str = "pt"
    page_size: int = 50


@dataclass
class GNewsConfig:
    api_key: str
    base_url: str = "https://gnews.io/api/v4"
    language: str = "pt"
    max_results: int = 50


CATEGORY_MAPPING_NEWS_API = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}

CATEGORY_MAPPING_GNEWS = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}


class NewsAPISource:
    """NewsAPI.org free tier adapter (100 req/day)."""

    def __init__(self, config: NewsAPIConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_top_headlines(
        self,
        category: str = "general",
        country: str = "br",
        page: int = 1,
    ) -> list[RawArticle]:
        """Fetch top headlines for a category."""
        params = {
            "apiKey": self.config.api_key,
            "category": category,
            "country": country,
            "language": self.config.language,
            "pageSize": self.config.page_size,
            "page": page,
        }
        url = f"{self.config.base_url}/top-headlines"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            if published:
                published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            else:
                published_at = datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"NewsAPI - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=CATEGORY_MAPPING_NEWS_API.get(category),
                tags=[category],
                metadata={"newsapi_category": category, "newsapi_source": item.get("source")},
            ))
        return articles

    async def fetch_everything(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
    ) -> list[RawArticle]:
        """Search articles (limited in free tier)."""
        params = {
            "apiKey": self.config.api_key,
            "q": query,
            "language": self.config.language,
            "pageSize": self.config.page_size,
            "page": page,
            "sortBy": "publishedAt",
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        url = f"{self.config.base_url}/everything"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"NewsAPI - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=Category.BRASIL,  # default, will be reclassified
                tags=[query],
                metadata={"newsapi_query": query, "newsapi_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


class GNewsSource:
    """GNews.io free tier adapter (100 req/day)."""

    def __init__(self, config: GNewsConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_top_headlines(
        self,
        category: str = "general",
        country: str = "br",
        page: int = 1,
    ) -> list[RawArticle]:
        params = {
            "token": self.config.api_key,
            "category": category,
            "lang": self.config.language,
            "country": country,
            "max": self.config.max_results,
            "page": page,
        }
        url = f"{self.config.base_url}/top-headlines"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"GNews - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.GNEWS,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("source", {}).get("name"),
                language=self.config.language,
                category_hint=CATEGORY_MAPPING_GNEWS.get(category),
                tags=[category],
                metadata={"gnews_category": category, "gnews_source": item.get("source")},
            ))
        return articles

    async def fetch_search(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
    ) -> list[RawArticle]:
        params = {
            "token": self.config.api_key,
            "q": query,
            "lang": self.config.language,
            "max": self.config.max_results,
            "page": page,
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        url = f"{self.config.base_url}/search"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"GNews - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.GNEWS,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("source", {}).get("name"),
                language=self.config.language,
                category_hint=Category.BRASIL,
                tags=[query],
                metadata={"gnews_query": query, "gnews_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


# ============================================================
# Additional News APIs (from public-apis/public-apis)
# ============================================================

CATEGORY_MAPPING_CURRENTS = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}

CATEGORY_MAPPING_MEDIASTACK = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}

CATEGORY_MAPPING_WORLDNEWS = {
    "general": Category.MUNDO,
    "business": Category.ECONOMIA,
    "tech": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}

CATEGORY_MAPPING_GUARDIAN = {
    "news": Category.MUNDO,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "sport": Category.ESPORTES,
    "culture": Category.CULTURA,
    "environment": Category.MEIO_AMBIENTE,
    "politics": Category.POLITICA,
}


@dataclass
class CurrentsConfig:
    api_key: str
    base_url: str = "https://api.currentsapi.services/v1"
    language: str = "pt"
    page_size: int = 50


class CurrentsSource:
    """Currents API - 100 req/day free."""

    def __init__(self, config: CurrentsConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_latest(self, category: str = "general", page: int = 1) -> list[RawArticle]:
        params = {
            "apiKey": self.config.api_key,
            "category": category,
            "language": self.config.language,
            "page_size": self.config.page_size,
            "page": page,
        }
        resp = await self.client.get(f"{self.config.base_url}/latest-news", params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("news", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("published")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"Currents - {item.get('source', 'Unknown')}",
                source_type=SourceType.NEWSAPI,  # reuse type
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=CATEGORY_MAPPING_CURRENTS.get(category),
                tags=[category],
                metadata={"currents_category": category, "currents_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


@dataclass
class MediaStackConfig:
    api_key: str
    base_url: str = "http://api.mediastack.com/v1"
    language: str = "pt"
    limit: int = 50


class MediaStackSource:
    """MediaStack - 100 req/month free (backup only)."""

    def __init__(self, config: MediaStackConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_news(self, category: str = "general", country: str = "br", page: int = 1) -> list[RawArticle]:
        params = {
            "access_key": self.config.api_key,
            "categories": category,
            "countries": country,
            "languages": self.config.language,
            "limit": self.config.limit,
            "offset": (page - 1) * self.config.limit,
        }
        resp = await self.client.get(f"{self.config.base_url}/news", params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("data", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("published_at")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"MediaStack - {item.get('source', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=CATEGORY_MAPPING_MEDIASTACK.get(category),
                tags=[category],
                metadata={"mediastack_category": category, "mediastack_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


@dataclass
class WorldNewsConfig:
    api_key: str
    base_url: str = "https://api.worldnewsapi.com"
    language: str = "pt"
    number: int = 50


class WorldNewsSource:
    """World News API - 100 req/day free."""

    def __init__(self, config: WorldNewsConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_top_news(self, category: str = "general", page: int = 1) -> list[RawArticle]:
        params = {
            "api-key": self.config.api_key,
            "category": category,
            "language": self.config.language,
            "number": self.config.number,
            "page": page,
        }
        resp = await self.client.get(f"{self.config.base_url}/top-news", params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("news", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publish_date")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"WorldNews - {item.get('source_name', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("summary") or item.get("text"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=CATEGORY_MAPPING_WORLDNEWS.get(category),
                tags=[category],
                metadata={"worldnews_category": category, "worldnews_source": item.get("source_name")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


@dataclass
class GuardianConfig:
    api_key: str
    base_url: str = "https://content.guardianapis.com"
    page_size: int = 50


class GuardianSource:
    """The Guardian API - 500 req/day free (UK/Global focus)."""

    def __init__(self, config: GuardianConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_search(self, section: str = "news", page: int = 1) -> list[RawArticle]:
        params = {
            "api-key": self.config.api_key,
            "section": section,
            "page-size": self.config.page_size,
            "page": page,
            "show-fields": "bodyText,thumbnail,byline",
            "lang": "pt",
        }
        resp = await self.client.get(f"{self.config.base_url}/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("response", {}).get("results", []):
            if not item.get("webUrl") or not item.get("webTitle"):
                continue
            published = item.get("webPublicationDate")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            fields = item.get("fields", {})
            articles.append(RawArticle(
                url=item["webUrl"],
                title=item["webTitle"],
                source_name=f"Guardian - {item.get('sectionName', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("webUrl"),
                published_at=published_at,
                raw_text=fields.get("bodyText") or fields.get("trailText"),
                author=fields.get("byline"),
                language="en",  # Guardian is English
                category_hint=CATEGORY_MAPPING_GUARDIAN.get(section),
                tags=[section],
                metadata={"guardian_section": section, "guardian_id": item.get("id")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


# Convenience functions for pipeline
async def fetch_newsapi_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from NewsAPI for multiple categories."""
    if not api_key:
        return []
    config = NewsAPIConfig(api_key=api_key)
    source = NewsAPISource(config)
    cats = categories or list(CATEGORY_MAPPING_NEWS_API.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_top_headlines(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"NewsAPI error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_gnews_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from GNews for multiple categories."""
    if not api_key:
        return []
    config = GNewsConfig(api_key=api_key)
    source = GNewsSource(config)
    cats = categories or list(CATEGORY_MAPPING_GNEWS.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_top_headlines(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"GNews error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_currents_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from Currents API."""
    if not api_key:
        return []
    config = CurrentsConfig(api_key=api_key)
    source = CurrentsSource(config)
    cats = categories or list(CATEGORY_MAPPING_CURRENTS.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_latest(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"Currents error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_mediastack_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from MediaStack (backup - low quota)."""
    if not api_key:
        return []
    config = MediaStackConfig(api_key=api_key)
    source = MediaStackSource(config)
    cats = categories or list(CATEGORY_MAPPING_MEDIASTACK.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_news(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"MediaStack error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_worldnews_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from World News API."""
    if not api_key:
        return []
    config = WorldNewsConfig(api_key=api_key)
    source = WorldNewsSource(config)
    cats = categories or list(CATEGORY_MAPPING_WORLDNEWS.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_top_news(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"WorldNews error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_guardian_articles(api_key: str, sections: list[str] | None = None) -> list[RawArticle]:
    """Fetch from The Guardian API."""
    if not api_key:
        return []
    config = GuardianConfig(api_key=api_key)
    source = GuardianSource(config)
    secs = sections or list(CATEGORY_MAPPING_GUARDIAN.keys())
    all_articles = []
    for sec in secs:
        try:
            articles = await source.fetch_search(section=sec)
            all_articles.extend(articles)
        except Exception as e:
            print(f"Guardian error for {sec}: {e}")
    await source.close()
    return all_articles