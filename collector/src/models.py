"""Pydantic models for collector pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Category(str, Enum):
    """Editorial categories matching EnjoyNews sections."""
    BRASIL = "Brasil"
    MUNDO = "Mundo"
    ECONOMIA = "Economia"
    TECNOLOGIA = "Tecnologia"
    ESPORTES = "Esportes"
    CIENCIA = "Ciência"
    CULTURA = "Cultura"
    LATINO_AMERICA = "Latino-América"
    SAUDE = "Saúde"
    MEIO_AMBIENTE = "Meio Ambiente"
    POLITICA = "Política"
    EDUCACAO = "Educação"


class SourceType(str, Enum):
    """Origin of the article."""
    RSS = "rss"
    NEWSAPI = "newsapi"
    GNEWS = "gnews"
    NITTER = "nitter"
    SITEMAP = "sitemap"
    MANUAL = "manual"


class Importance(int, Enum):
    """Editorial importance 1-5."""
    LOW = 1
    MEDIUM_LOW = 2
    MEDIUM = 3
    HIGH = 4
    BREAKING = 5


class RawArticle(BaseModel):
    """Article as fetched from source (before LLM processing)."""
    url: HttpUrl
    title: str = Field(..., min_length=1, max_length=500)
    source_name: str = Field(..., min_length=1)
    source_type: SourceType
    source_url: HttpUrl | None = None
    published_at: datetime
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    raw_html: str | None = None
    raw_text: str | None = None
    author: str | None = None
    language: str = "pt"
    category_hint: Category | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("published_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            from dateutil import parser
            return parser.parse(v)
        raise ValueError(f"Invalid datetime: {v}")


class Summary(BaseModel):
    """LLM-generated journalistic summary."""
    headline: str = Field(..., min_length=1, max_length=120)
    kicker: str = Field(..., min_length=1, max_length=80)  # "Categoria | Subcategoria"
    lead: str = Field(..., min_length=1, max_length=300)
    body: list[str] = Field(..., min_length=1, max_length=5)
    context: str = Field(..., min_length=1, max_length=300)
    tags: list[str] = Field(default_factory=list, max_length=10)
    importance: Importance = Importance.MEDIUM
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_used: str = Field(..., min_length=1)

    @property
    def full_text(self) -> str:
        """Complete article text for publishing."""
        parts = [self.lead]
        parts.extend(self.body)
        parts.append(self.context)
        return "\n\n".join(parts)


class ProcessedArticle(BaseModel):
    """Final article ready for publishing."""
    id: str = Field(..., min_length=1)  # UUID or hash
    raw: RawArticle
    summary: Summary
    hero_image_url: HttpUrl | None = None
    hero_image_alt: str | None = None
    hero_image_credit: str | None = None
    clustered_with: list[str] = Field(default_factory=list)  # IDs of related articles
    is_primary_in_cluster: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mdx_frontmatter(self) -> dict[str, Any]:
        """Convert to Astro MDX frontmatter."""
        return {
            "title": self.summary.headline,
            "description": self.summary.lead,
            "pubDate": self.raw.published_at.isoformat(),
            "updatedDate": self.created_at.isoformat(),
            "heroImage": str(self.hero_image_url) if self.hero_image_url else None,
            "heroImageAlt": self.hero_image_alt,
            "heroImageCredit": self.hero_image_credit,
            "category": self.raw.category_hint.value if self.raw.category_hint else None,
            "tags": self.summary.tags,
            "sourceName": self.raw.source_name,
            "sourceUrl": str(self.raw.url),
            "importance": self.summary.importance.value,
            "kicker": self.summary.kicker,
        }

    def to_mdx_content(self) -> str:
        """Full MDX body content."""
        return self.summary.full_text


class Cluster(BaseModel):
    """Group of articles about the same story."""
    id: str
    primary: ProcessedArticle
    related: list[ProcessedArticle] = Field(default_factory=list)
    theme: str = Field(..., min_length=1, max_length=200)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineConfig(BaseModel):
    """Runtime configuration."""
    max_articles_per_run: int = 50
    dedup_window_minutes: int = 1440
    min_confidence: float = 0.6
    max_clusters: int = 20
    output_dir: str = "output/posts"
    # LLM Providers (priority order)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-70b-versatile"
    together_api_key: str | None = None
    together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    hf_api_token: str | None = None
    hf_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    # News APIs
    newsapi_key: str | None = None
    gnews_key: str | None = None
    currents_key: str | None = None
    mediastack_key: str | None = None
    worldnews_key: str | None = None
    guardian_key: str | None = None
    # Social / Other
    nitter_instances: list[str] = Field(default_factory=list)
    # Enrichment APIs
    brasil_api_key: str | None = None
    worldbank_key: str | None = None
    alphavantage_key: str | None = None
    coingecko_key: str | None = None
    openweather_key: str | None = None
    restcountries_key: str | None = None
    # General
    request_timeout: int = 30
    user_agent: str = "EnjoyNewsBot/0.1 (+https://enjoynews.com.br/bot)"