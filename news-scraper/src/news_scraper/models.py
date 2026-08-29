from datetime import datetime, timezone

import uuid as uuid_pkg

from sqlalchemy import DateTime, Float, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


metadata = Base.metadata


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    full_text: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    entities: Mapped[dict | None] = mapped_column(JSONB)
    event_type: Mapped[str | None] = mapped_column(Text)
    entity_scores: Mapped[dict | None] = mapped_column(JSONB)
    scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow
    )


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
        unique=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    company_keyword: Mapped[str] = mapped_column(Text, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending", default="pending"
    )
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))