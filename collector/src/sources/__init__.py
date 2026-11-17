"""Sources package for EnjoyNews collector."""
from .rss_sources import (
    RssSource,
    ALL_RSS_SOURCES,
    get_enabled_sources,
    count_by_category,
    BRASIL_SOURCES,
    MUNDO_SOURCES,
    LATAM_SOURCES,
    OFFICIAL_SOURCES,
    TECH_SCIENCE_SOURCES,
    CULTURE_SOURCES,
)
from .newsapi_source import (
    NewsAPISource,
    GNewsSource,
    fetch_newsapi_articles,
    fetch_gnews_articles,
    NewsAPIConfig,
    GNewsConfig,
)
from .nitter_source import (
    NitterSource,
    fetch_nitter_articles,
    NitterConfig,
    NITTER_ACCOUNTS,
    NITTER_HASHTAGS,
)
from .sitemap_source import (
    SitemapSource,
    fetch_sitemap_articles,
    SitemapSourceConfig,
    SITEMAP_SOURCES,
)

__all__ = [
    # RSS
    "RssSource",
    "ALL_RSS_SOURCES",
    "get_enabled_sources",
    "count_by_category",
    "BRASIL_SOURCES",
    "MUNDO_SOURCES",
    "LATAM_SOURCES",
    "OFFICIAL_SOURCES",
    "TECH_SCIENCE_SOURCES",
    "CULTURE_SOURCES",
    # NewsAPI/GNews
    "NewsAPISource",
    "GNewsSource",
    "fetch_newsapi_articles",
    "fetch_gnews_articles",
    "NewsAPIConfig",
    "GNewsConfig",
    # Nitter
    "NitterSource",
    "fetch_nitter_articles",
    "NitterConfig",
    "NITTER_ACCOUNTS",
    "NITTER_HASHTAGS",
    # Sitemap
    "SitemapSource",
    "fetch_sitemap_articles",
    "SitemapSourceConfig",
    "SITEMAP_SOURCES",
]