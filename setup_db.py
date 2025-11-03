from config.db_config import engine, Base
from database.models import Source, Chunk, Narrative, ScrapingLog, PDFExtraction
from loguru import logger


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


if __name__ == "__main__":
    create_tables()


