from loguru import logger
from config.db_config import SessionLocal
from database.db_operations import DatabaseOperations
from scrapers.govt_scraper import GovernmentScraper
from scrapers.media_scraper import MediaScraper
from scrapers.social_scraper import SocialScraper
from scrapers.youtube_scraper import YouTubeScraper
from processors.normalizer import Normalizer
from processors.chunker import Chunker
from processors.tagger import Tagger
from processors.embedder import Embedder, VectorStoreManager
from typing import List, Dict, Optional
import sys
from datetime import datetime
import argparse

class DataScrapingOrchestrator:
    def __init__(self, skip_embeddings: bool = False):
        self.db = SessionLocal()
        self.db_ops = DatabaseOperations(self.db)
        
        # Initialize scrapers
        self.scrapers = {
            "government": GovernmentScraper(),
            "media": MediaScraper(),
            "social": SocialScraper(),
            "youtube": YouTubeScraper()
        }
        
        # Initialize processors
        self.normalizer = Normalizer()
        self.chunker = Chunker()
        self.tagger = Tagger()
        self.embedder = Embedder() if not skip_embeddings else None
        self.vector_store = VectorStoreManager(self.db_ops) if not skip_embeddings else None
        
        # Statistics
        self.stats = {
            "total_sources": 0,
            "total_chunks": 0,
            "total_embeddings": 0,
            "failed_sources": 0,
            "failed_chunks": 0,
            "start_time": datetime.utcnow()
        }
    
    def run_full_pipeline(self, scraper_types: List[str] = None, 
                         limit_per_scraper: Optional[int] = None):
        """Run complete scraping and processing pipeline"""
        logger.info("=" * 80)
        logger.info("🚀 Starting Indore Political RAG Data Scraping Pipeline")
        logger.info("=" * 80)
        logger.info(f"Start time: {self.stats['start_time']}")
        
        if scraper_types is None:
            scraper_types = ["government", "media", "youtube", "social"]
        
        logger.info(f"Active scrapers: {', '.join(scraper_types)}")
        logger.info(f"Embeddings enabled: {self.embedder is not None}")
        if limit_per_scraper:
            logger.info(f"Limit per scraper: {limit_per_scraper} sources")
        logger.info("=" * 80)
        
        for scraper_type in scraper_types:
            if scraper_type not in self.scrapers:
                logger.warning(f"⚠️  Unknown scraper type: {scraper_type}")
                continue
            
            self._process_scraper_type(scraper_type, limit_per_scraper)
        
        self._print_final_report()
    
    def _process_scraper_type(self, scraper_type: str, limit: Optional[int] = None):
        """Process a single scraper type"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📥 Running {scraper_type.upper()} scraper")
        logger.info(f"{'=' * 80}")
        
        scraper_start_time = datetime.utcnow()
        scraper_sources = 0
        scraper_chunks = 0
        
        try:
            # Step 1: Scrape
            scraper = self.scrapers[scraper_type]
            sources = scraper.scrape()
            
            if not sources:
                logger.warning(f"⚠️  No sources found for {scraper_type}")
                return
            
            # Apply limit if specified
            if limit and len(sources) > limit:
                logger.info(f"Limiting to first {limit} sources")
                sources = sources[:limit]
            
            logger.info(f"Found {len(sources)} sources to process")
            
            # Step 2: Process each source
            for idx, source_data in enumerate(sources, 1):
                logger.info(f"\n--- Processing source {idx}/{len(sources)} ---")
                
                success = self._process_single_source(
                    source_data, 
                    scraper_type,
                    idx,
                    len(sources)
                )
                
                if success:
                    scraper_sources += 1
                    # Count chunks from this source
                    # (approximation - actual count would require tracking)
                    scraper_chunks += success
        
        except Exception as e:
            logger.error(f"❌ Error in {scraper_type} scraper: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            scraper_duration = (datetime.utcnow() - scraper_start_time).total_seconds()
            logger.info(f"\n{'─' * 80}")
            logger.info(f"✅ {scraper_type.upper()} scraper complete")
            logger.info(f"   Duration: {scraper_duration:.2f}s")
            logger.info(f"   Sources processed: {scraper_sources}")
            logger.info(f"   Chunks created: {scraper_chunks}")
            logger.info(f"{'─' * 80}")
    
    def _process_single_source(self, source_data: Dict, scraper_type: str, 
                              current: int, total: int) -> Optional[int]:
        """Process a single source through the full pipeline"""
        try:
            # Step 1: Normalize
            logger.debug("Step 1: Normalizing source data...")
            source_data = self.normalizer.normalize_source(source_data)
            
            # Step 2: Save source
            logger.debug("Step 2: Saving source to database...")
            source_id = self.db_ops.save_source(source_data)
            if not source_id:
                logger.warning("⚠️  Source already exists or failed to save")
                return None
            
            self.stats["total_sources"] += 1
            
            # Step 3: Extract and chunk content
            content = source_data.get('raw_content', '')
            if not content or len(content.strip()) < 50:
                logger.warning("⚠️  Source has insufficient content for chunking")
                return 0
            
            logger.debug(f"Step 3: Chunking content ({len(content)} chars)...")
            chunks = self.chunker.chunk_text(content, str(source_id))
            
            if not chunks:
                logger.warning("⚠️  No chunks created from source")
                return 0
            
            logger.info(f"Created {len(chunks)} chunks")
            
            # Step 4: Tag each chunk
            logger.debug(f"Step 4: Tagging {len(chunks)} chunks...")
            tagged_chunks = []
            for chunk_idx, chunk in enumerate(chunks, 1):
                try:
                    logger.debug(f"  Tagging chunk {chunk_idx}/{len(chunks)}...")
                    
                    tags = self.tagger.tag_chunk(
                        chunk['text'],
                        source_data
                    )
                    
                    chunk['tags'] = tags
                    chunk['entities'] = self.normalizer.extract_entities(chunk['text'])
                    chunk['sentiment'] = tags.get('sentiment', {})
                    chunk['leadership_polarity'] = tags.get('leadership_polarity', {})
                    
                    tagged_chunks.append(chunk)
                
                except Exception as e:
                    logger.error(f"Error tagging chunk {chunk_idx}: {e}")
                    self.stats["failed_chunks"] += 1
                    continue
            
            if not tagged_chunks:
                logger.warning("⚠️  No chunks successfully tagged")
                return 0
            
            # Step 5: Generate embeddings (if enabled)
            if self.embedder:
                logger.debug(f"Step 5: Generating embeddings for {len(tagged_chunks)} chunks...")
                try:
                    tagged_chunks = self.embedder.embed_chunks_batch(tagged_chunks)
                    embeddings_count = sum(1 for c in tagged_chunks if c.get('embedding_vector'))
                    self.stats["total_embeddings"] += embeddings_count
                    logger.info(f"Generated {embeddings_count} embeddings")
                except Exception as e:
                    logger.error(f"Error generating embeddings: {e}")
            
            # Step 6: Save chunks to database
            logger.debug(f"Step 6: Saving {len(tagged_chunks)} chunks to database...")
            saved_count = self.db_ops.save_chunks(tagged_chunks)
            self.stats["total_chunks"] += saved_count
            
            # Step 7: Log success
            self.db_ops.log_scraping(
                url=source_data['source_url'],
                scraper_type=scraper_type,
                status="success",
                items_scraped=saved_count
            )
            
            logger.info(f"✅ Successfully processed: {source_data['title'][:60]}...")
            logger.info(f"   Saved {saved_count} chunks")
            
            return saved_count
        
        except Exception as e:
            logger.error(f"❌ Error processing source: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            self.stats["failed_sources"] += 1
            
            # Log failure
            self.db_ops.log_scraping(
                url=source_data.get('source_url', 'unknown'),
                scraper_type=scraper_type,
                status="failed",
                error_message=str(e)
            )
            
            return None
    
    def _print_final_report(self):
        """Print final statistics report"""
        end_time = datetime.utcnow()
        duration = (end_time - self.stats['start_time']).total_seconds()
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📊 PIPELINE EXECUTION REPORT")
        logger.info(f"{'=' * 80}")
        logger.info(f"Start time:          {self.stats['start_time']}")
        logger.info(f"End time:            {end_time}")
        logger.info(f"Total duration:      {duration:.2f} seconds ({duration/60:.2f} minutes)")
        logger.info(f"{'─' * 80}")
        logger.info(f"✅ Total sources:     {self.stats['total_sources']}")
        logger.info(f"✅ Total chunks:      {self.stats['total_chunks']}")
        if self.embedder:
            logger.info(f"✅ Total embeddings:  {self.stats['total_embeddings']}")
        logger.info(f"❌ Failed sources:    {self.stats['failed_sources']}")
        logger.info(f"❌ Failed chunks:     {self.stats['failed_chunks']}")
        logger.info(f"{'─' * 80}")
        
        if self.stats['total_sources'] > 0:
            avg_chunks = self.stats['total_chunks'] / self.stats['total_sources']
            logger.info(f"📈 Average chunks per source: {avg_chunks:.2f}")
            
            success_rate = (self.stats['total_sources'] / 
                          (self.stats['total_sources'] + self.stats['failed_sources'])) * 100
            logger.info(f"📈 Success rate: {success_rate:.2f}%")
        
        logger.info(f"{'=' * 80}\n")
    
    def run_specific_url(self, url: str, source_type: str):
        """Process a specific URL"""
        logger.info(f"Processing specific URL: {url}")
        
        # Create a mock source_data structure
        source_data = {
            "source_url": url,
            "source_type": source_type,
            "domain": url.split('/')[2] if '/' in url else url
        }
        
        # Fetch and process
        if source_type == "government":
            scraper = self.scrapers["government"]
        elif source_type == "media":
            scraper = self.scrapers["media"]
        else:
            logger.error(f"Unsupported source type: {source_type}")
            return
        
        html = scraper.fetch_page(url)
        if not html:
            logger.error("Failed to fetch URL")
            return
        
        soup = scraper.parse_html(html)
        content = soup.get_text(separator='\n', strip=True)
        
        source_data['raw_content'] = content
        source_data['raw_html'] = html
        source_data['title'] = soup.find('title').get_text() if soup.find('title') else url
        
        self._process_single_source(source_data, source_type, 1, 1)
    
    def close(self):
        """Close database connection"""
        self.db.close()
        logger.info("Database connection closed")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Indore Political RAG Data Scraping Pipeline'
    )
    parser.add_argument(
        '--scrapers',
        type=str,
        help='Comma-separated list of scrapers to run (government,media,youtube,social)',
        default='government,media,youtube,social'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of sources per scraper',
        default=None
    )
    parser.add_argument(
        '--skip-embeddings',
        action='store_true',
        help='Skip embedding generation (faster for testing)'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Process a specific URL',
        default=None
    )
    parser.add_argument(
        '--url-type',
        type=str,
        help='Type of URL (government, media)',
        default='media'
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = DataScrapingOrchestrator(skip_embeddings=args.skip_embeddings)
    
    try:
        if args.url:
            # Process specific URL
            orchestrator.run_specific_url(args.url, args.url_type)
        else:
            # Run full pipeline
            scraper_types = [s.strip() for s in args.scrapers.split(',')]
            orchestrator.run_full_pipeline(
                scraper_types=scraper_types,
                limit_per_scraper=args.limit
            )
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
    
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        orchestrator.close()
        logger.info("👋 Pipeline shutdown complete")


if __name__ == "__main__":
    main()