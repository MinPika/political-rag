from typing import List, Dict
from loguru import logger
from scrapers.base_scraper import BaseScraper
from datetime import datetime
import re
from urllib.parse import urljoin

class MediaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.media_sources = {
            "dainik_bhaskar": {
                "url": "https://www.bhaskar.com/local/mp/indore/",
                "domain": "bhaskar.com",
                "selectors": {
                    "articles": "div._c3w6",
                    "title": "h3, h2",
                    "link": "a"
                }
            },
            "indian_express": {
                "url": "https://indianexpress.com/about/indore/",
                "domain": "indianexpress.com",
                "selectors": {
                    "articles": "div.articles",
                    "title": "h3, h2",
                    "link": "a"
                }
            },
            "free_press": {
                "url": "https://www.freepressjournal.in/indore",
                "domain": "freepressjournal.in",
                "selectors": {
                    "articles": "div.story-box, article",
                    "title": "h2, h3",
                    "link": "a"
                }
            },
            "times_of_india": {
                "url": "https://timesofindia.indiatimes.com/topic/indore/news",
                "domain": "timesofindia.indiatimes.com",
                "selectors": {
                    "articles": "div.uwU81",
                    "title": "span",
                    "link": "a"
                }
            },
            "india_today": {
                "url": "https://www.indiatoday.in/cities/indore-news",
                "domain": "indiatoday.in",
                "selectors": {
                    "articles": "div.story-card, article",
                    "title": "h2, h3",
                    "link": "a"
                }
            }
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape all media sources"""
        logger.info("📰 Starting Media Scraping")
        all_sources = []
        
        for source_name, config in self.media_sources.items():
            logger.info(f"Scraping {source_name}...")
            sources = self.scrape_media_source(source_name, config)
            all_sources.extend(sources)
        
        logger.info(f"✅ Media scraping complete. Found {len(all_sources)} articles")
        return all_sources
    
    def scrape_media_source(self, source_name: str, config: Dict) -> List[Dict]:
        """Scrape a single media source"""
        sources = []
        html = self.fetch_page(config["url"])
        
        if not html:
            return sources
        
        soup = self.parse_html(html)
        selectors = config["selectors"]
        
        # Find all article containers
        articles = soup.find_all(class_=re.compile(r'story|article|news'))[:10]  # Limit to 10 articles
        
        if not articles:
            # Fallback: try generic selectors
            articles = soup.find_all(['article', 'div'], class_=re.compile(r'.*'))[:10]
        
        for article in articles:
            try:
                # Extract title
                title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract link
                link_elem = article.find('a', href=True)
                if not link_elem:
                    continue
                
                article_url = link_elem['href']
                if not article_url.startswith('http'):
                    article_url = urljoin(config["url"], article_url)
                
                # Fetch full article
                article_html = self.fetch_page(article_url)
                if not article_html:
                    continue
                
                article_soup = self.parse_html(article_html)
                
                # Extract article body
                content_div = (article_soup.find('div', class_=re.compile(r'story|article|content')) or
                             article_soup.find('article'))
                
                if not content_div:
                    continue
                
                content = content_div.get_text(separator='\n', strip=True)
                
                if len(content) > 100:  # Only save substantial content
                    source = self.create_source_dict(
                        url=article_url,
                        title=title,
                        content=article_html,
                        source_type="media",
                        domain=config["domain"]
                    )
                    source["raw_content"] = content
                    sources.append(source)
                    logger.info(f"✅ Scraped: {title[:50]}...")
            
            except Exception as e:
                logger.warning(f"Error scraping article from {source_name}: {e}")
                continue
        
        return sources