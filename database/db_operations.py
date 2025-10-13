from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database.models import Source, Chunk, ScrapingLog
from loguru import logger
from datetime import datetime
import uuid

class DatabaseOperations:
    def __init__(self, db: Session):
        self.db = db
    
    def save_source(self, source_data: Dict) -> Optional[uuid.UUID]:
        """Save source to database"""
        try:
            # Check if source already exists
            existing = self.db.query(Source).filter(
                Source.source_url == source_data['source_url']
            ).first()
            
            if existing:
                logger.debug(f"Source already exists: {source_data['source_url']}")
                return existing.id
            
            # Remove fields that aren't in the Source model
            source_data_copy = source_data.copy()
            source_data_copy.pop('raw_content', None)  # Remove raw_content
            
            source = Source(**source_data_copy)
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
            
            logger.info(f"✅ Saved source: {source.title[:50]}... (ID: {source.id})")
            return source.id
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving source: {e}")
            return None
    
    def save_chunks(self, chunks: List[Dict]) -> int:
        """Save multiple chunks to database"""
        saved_count = 0
        
        try:
            for chunk_data in chunks:
                # Remove fields not in Chunk model
                chunk_copy = chunk_data.copy()
                chunk_copy.pop('embedding_vector', None)
                chunk_copy.pop('embedding_dimension', None)
                chunk_copy.pop('embedding_model', None)
                
                chunk = Chunk(**chunk_copy)
                self.db.add(chunk)
                saved_count += 1
            
            self.db.commit()
            logger.info(f"✅ Saved {saved_count} chunks")
            return saved_count
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving chunks: {e}")
            return 0
    
    def log_scraping(self, url: str, scraper_type: str, status: str, 
                     items_scraped: int = 0, error_message: str = None) -> None:
        """Log scraping activity"""
        try:
            log = ScrapingLog(
                source_url=url,
                scraper_type=scraper_type,
                status=status,
                items_scraped=items_scraped,
                error_message=error_message
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging scraping: {e}")
    
    def get_sources_by_type(self, source_type: str, limit: int = 100) -> List[Source]:
        """Get sources by type"""
        return self.db.query(Source).filter(
            Source.source_type == source_type
        ).limit(limit).all()
    
    def get_chunks_by_source(self, source_id: uuid.UUID) -> List[Chunk]:
        """Get all chunks for a source"""
        return self.db.query(Chunk).filter(
            Chunk.source_id == source_id
        ).all()