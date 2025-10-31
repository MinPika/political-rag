from typing import List, Dict
from loguru import logger
from scrapers.base_scraper import BaseScraper
from datetime import datetime
import re


class GovernmentScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://indore.nic.in"

    def scrape(self) -> List[Dict]:
        """Scrape Indore district government website"""
        logger.info("🏛️ Starting Government Portal Scraping")
        sources = []

        # Main pages to scrape
        pages = [
            "/en/",
            "/en/about-district/whos-who/",
            "/en/past-notices/information/",
        ]

        for page in pages:
            url = f"{self.base_url}{page}"
            html = self.fetch_page(url)

            if not html:
                continue

            soup = self.parse_html(html)

            # Extract main content
            content_div = soup.find("div", class_="content") or soup.find("main")
            if content_div:
                title = soup.find("h1")
                title_text = (
                    title.get_text(strip=True) if title else "Government Notice"
                )

                content_text = content_div.get_text(separator="\n", strip=True)

                if len(content_text) > 100:  # Only save if substantial content
                    source = self.create_source_dict(
                        url=url,
                        title=title_text,
                        content=html,
                        source_type="government",
                        domain="indore.nic.in",
                    )
                    source["raw_content"] = content_text
                    sources.append(source)
                    logger.info(f"✅ Scraped: {title_text[:50]}...")

            # Extract PDF links for notices
            pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))
            for link in pdf_links[:5]:  # Limit to first 5 PDFs
                pdf_url = link.get("href")
                if not pdf_url.startswith("http"):
                    pdf_url = f"{self.base_url}{pdf_url}"

                pdf_title = link.get_text(strip=True) or "Government PDF Notice"

                source = self.create_source_dict(
                    url=pdf_url,
                    title=pdf_title,
                    content=f"PDF Document: {pdf_title}",
                    source_type="government",
                    domain="indore.nic.in",
                )
                source["raw_blob_url"] = pdf_url
                source["metadata"] = {"file_type": "pdf"}
                sources.append(source)
                logger.info(f"📄 Found PDF: {pdf_title[:50]}...")

        logger.info(f"✅ Government scraping complete. Found {len(sources)} items")
        return sources
