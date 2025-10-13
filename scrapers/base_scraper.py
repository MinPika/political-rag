import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import time
from loguru import logger
from config.settings import settings
from utils.helpers import clean_text, generate_hash, detect_language, calculate_trust_score

class BaseScraper(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': settings.USER_AGENT})
        self.delay = settings.SCRAPE_DELAY
        self.max_retries = settings.MAX_RETRIES
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL with retry logic"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay)
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                    return None
        return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content"""
        return BeautifulSoup(html, 'html.parser')
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """Main scraping method to be implemented by child classes"""
        pass
    
    def create_source_dict(self, url: str, title: str, content: str, 
                          source_type: str, domain: str, 
                          published_at: Optional[datetime] = None) -> Dict:
        """Create standardized source dictionary"""
        language = detect_language(content[:500])
        
        return {
            "source_url": url,
            "title": clean_text(title),
            "domain": domain,
            "source_type": source_type,
            "layer": self.get_layer(source_type),
            "published_at": published_at or datetime.utcnow(),
            "language": language,
            "trust_score": calculate_trust_score(source_type, domain),
            "raw_html": content,
            "parser_version": "v1.0"
        }
    
    def get_layer(self, source_type: str) -> int:
        """Map source type to layer"""
        layer_map = {
            "government": 2,
            "policy": 2,
            "media": 3,
            "social": 3,
            "voice": 4
        }
        return layer_map.get(source_type, 3)