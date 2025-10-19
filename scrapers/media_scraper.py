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
        visited_articles = set()
        pages_to_scrape = [config["url"]]
        
        while pages_to_scrape: 
            page_url = pages_to_scrape.pop(0)
            html = self.fetch_page(page_url)
            if not html:
                continue
            
            soup = self.parse_html(html)
            
            # Find articles (try multiple generic selectors)
            articles = soup.find_all(['article', 'div'], class_=re.compile(r'story|article|news|card'))[:15]

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
                    
                    if article_url in visited_articles:
                        continue
                    visited_articles.add(article_url)

                    # Fetch full article page
                    article_html = self.fetch_page(article_url)
                    if not article_html:
                        continue

                    article_soup = self.parse_html(article_html)
                    content_div = (article_soup.find('div', class_=re.compile(r'story|article|content')) or
                                   article_soup.find('article'))
                    if not content_div:
                        continue

                    content = content_div.get_text(separator='\n', strip=True)
                    if len(content) < 50:
                        continue

                    # Create source dict with existing structure
                    source = self.create_source_dict(
                        url=article_url,
                        title=title,
                        content=article_html,
                        source_type="media",
                        domain=config["domain"]
                    )
                    source["raw_content"] = content

                    # Enhanced metadata
                    source["metadata"] = {
                        "published_date": self.extract_published_date(article_soup),
                        "author": self.extract_author(article_soup),
                        "images": self.extract_images(article_soup, config["url"]),
                        "videos": self.extract_videos(article_soup),
                        "categories": self.extract_categories(article_soup),
                    }

                    sources.append(source)
                    logger.info(f"✅ Scraped: {title[:50]}...")

                except Exception as e:
                    logger.warning(f"Error scraping article from {source_name}: {e}")
                    continue

            # Optional: Add next page links for pagination
            next_links = self.extract_pagination_links(soup, config["url"])
            for link in next_links:
                if link not in pages_to_scrape:
                    pages_to_scrape.append(link)

        return sources