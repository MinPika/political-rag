from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.db_config import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, nullable=False, unique=True)
    title = Column(Text)
    domain = Column(String(255))
    source_type = Column(String(50))  # govt, media, research, etc.
    layer = Column(Integer)
    published_at = Column(DateTime)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String(10))
    geo = Column(JSONB)
    trust_score = Column(Float)
    parser_version = Column(String(50))
    raw_blob_url = Column(Text)
    raw_html = Column(Text)
    extra_metadata = Column(JSONB)

    # Relationships
    chunks = relationship(
        "Chunk", back_populates="source", cascade="all, delete-orphan"
    )
    pdf_extractions = relationship(
        "PDFExtraction", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_source_type", "source_type"),
        Index("idx_source_domain", "domain"),
        Index("idx_source_published", "published_at"),
        Index("idx_source_geo", "geo", postgresql_using="gin"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    seq = Column(Integer)
    text = Column(Text, nullable=False)
    word_count = Column(Integer)
    embedding_id = Column(String(255))
    entities = Column(JSONB)
    tags = Column(JSONB)
    sentiment = Column(JSONB)
    leadership_polarity = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source = relationship("Source", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_source", "source_id"),
        Index("idx_chunk_tags", "tags", postgresql_using="gin"),
        Index("idx_chunk_entities", "entities", postgresql_using="gin"),
    )


class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text)
    summary = Column(Text)
    issues = Column(JSONB)
    geo = Column(JSONB)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    cluster_members = Column(JSONB)
    criticality_score = Column(Float)
    political_impact_score = Column(Float)
    governance_impact_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_narrative_issues", "issues", postgresql_using="gin"),
        Index("idx_narrative_geo", "geo", postgresql_using="gin"),
    )


class ScrapingLog(Base):
    __tablename__ = "scraping_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, nullable=False)
    scraper_type = Column(String(50))
    status = Column(String(20))  # success, failed, partial
    items_scraped = Column(Integer, default=0)
    error_message = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column(JSONB)


class PDFExtraction(Base):
    __tablename__ = "pdf_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    source_url = Column(Text, nullable=False)
    title = Column(Text)
    domain = Column(String(255))
    source_type = Column(String(50))
    language = Column(String(10))
    geo = Column(JSONB)  # ✅ Can store dict directly
    extracted_text = Column(Text)

    source = relationship("Source", back_populates="pdf_extractions")
