from typing import List, Dict
from loguru import logger
from scrapers.base_scraper import BaseScraper
from datetime import datetime
import re


class GovernmentScraper(BaseScraper):
    def __init__(self, max_depth=2, max_urls=100):
        super().__init__()
        self.base_url = "https://indore.nic.in"
        self.visited = set()
        self.max_depth = max_depth
        self.max_urls = max_urls

    def scrape(self) -> List[Dict]:
        logger.info("🏛️ Starting Government Portal Scraping")
        sources = []
        queue = [(f"{self.base_url}/en/", 0)]  # start URL and depth
        while queue and len(self.visited) < self.max_urls:
            url, depth = queue.pop(0)
            if url in self.visited or depth > self.max_depth:
                continue

            html = self.fetch_page(url)
            if not html:
                continue

            soup = self.parse_html(html)

            content_div = soup.find("div", class_="content") or soup.find("main")
            title_tag = soup.find("h1")
            title_text = (
                title_tag.get_text(strip=True) if title_tag else "Government Notice"
            )
            content_text = (
                content_div.get_text(separator="\n", strip=True) if content_div else ""
            )

            if len(content_text) > 100:
                source = self.create_source_dict(
                    url=url,
                    title=title_text,
                    content=html,
                    source_type="government",
                    domain="indore.nic.in",
                )
                source["raw_content"] = content_text

                # Optional: Add extra metadata without removing existing fields
                source["metadata"] = {}
                date_tag = soup.find("time")
                if date_tag:
                    source["metadata"]["published_date"] = date_tag.get_text(strip=True)

                sources.append(source)
                logger.info(f"✅ Scraped: {title_text[:50]}...")

            # Extract PDFs and other files
            files = self.extract_files(soup, self.base_url)
            for file_url, file_title, file_type in files:
                file_source = self.create_source_dict(
                    url=file_url,
                    title=file_title or "Government Document",
                    content=f"File: {file_title}",
                    source_type="government",
                    domain="indore.nic.in",
                )
                file_source["raw_blob_url"] = file_url
                file_source["metadata"] = {"file_type": file_type}
                sources.append(file_source)
                logger.info(f"📄 Found file: {file_title[:50]}...")

            self.visited.add(url)

            # Queue internal links
            links = self.get_internal_links(soup, "indore.nic.in")
            for link in links:
                if link not in self.visited:
                    queue.append((link, depth + 1))

        logger.info(f"✅ Government scraping complete. Found {len(sources)} items")
        return sources

    def get_internal_links(self, soup, base_domain):
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/") or base_domain in href:
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                links.add(full_url)
        return links

    def extract_files(self, soup, base_url):
        file_types = ["pdf", "doc", "docx", "xls", "xlsx"]
        files = []
        for ext in file_types:
            links = soup.find_all("a", href=re.compile(rf"\.{ext}$", re.I))
            for link in links:
                file_url = link["href"]
                if not file_url.startswith("http"):
                    file_url = f"{base_url}{file_url}"
                file_title = link.get_text(strip=True) or "Government Document"
                files.append((file_url, file_title, ext))
        return files

    def extract_contacts(self, content_text):
        contacts = {}
        emails = re.findall(r"[\w\.-]+@[\w\.-]+", content_text)
        if emails:
            contacts["emails"] = list(set(emails))
        phones = re.findall(r"\+?\d[\d\s\-]{7,}\d", content_text)
        if phones:
            contacts["phone_numbers"] = list(set(phones))
        return contacts

    def extract_tables(self, soup):
        tables_data = []
        tables = soup.find_all("table")
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            rows_data = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    row_dict = dict(zip(headers, cells)) if headers else {"row": cells}
                    rows_data.append(row_dict)
            if rows_data:
                tables_data.append(rows_data)
        return tables_data

    def extract_images(self, soup):
        images = []
        for img in soup.find_all("img", src=True):
            img_url = img["src"]
            if not img_url.startswith("http"):
                img_url = f"{self.base_url}{img_url}"
            images.append(img_url)
        return images

    def extract_breadcrumbs(self, soup):
        breadcrumbs = []
        for bc in soup.select("nav.breadcrumb a"):
            breadcrumbs.append(bc.get_text(strip=True))
        return breadcrumbs
