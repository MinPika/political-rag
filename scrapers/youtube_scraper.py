from typing import List, Dict
from loguru import logger
from scrapers.base_scraper import BaseScraper
from datetime import datetime
import yt_dlp
import re
import json

class YouTubeScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.video_urls = [
            "https://www.youtube.com/watch?v=BkJTFxPL2d4",
        ]
    
    def scrape(self) -> List[Dict]:
        """Scrape YouTube videos with full transcripts"""
        logger.info("Starting YouTube Scraping")
        sources = []
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['hi', 'en'],
            'subtitlesformat': 'json3',
            'quiet': True,
            'no_warnings': True,
        }
        
        for video_url in self.video_urls:
            try:
                video_id = self.extract_video_id(video_url)
                if not video_id:
                    continue
                
                logger.info(f"Processing video: {video_id}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    
                    title = info.get('title', f'YouTube Video {video_id}')
                    description = info.get('description', '')
                    duration = info.get('duration', 0)
                    
                    # Extract subtitles/captions
                    subtitles = info.get('subtitles', {})
                    automatic_captions = info.get('automatic_captions', {})
                    
                    transcript_text = ""
                    subtitle_source = None
                    
                    # Try Hindi first, then English
                    for lang in ['hi', 'en']:
                        caption_data = None
                        
                        if lang in subtitles and subtitles[lang]:
                            caption_data = subtitles[lang]
                            subtitle_source = f"{lang} (manual)"
                        elif lang in automatic_captions and automatic_captions[lang]:
                            caption_data = automatic_captions[lang]
                            subtitle_source = f"{lang} (auto-generated)"
                        
                        if caption_data:
                            # Get json3 format subtitle
                            json3_subtitle = None
                            for fmt in caption_data:
                                if fmt.get('ext') == 'json3':
                                    json3_subtitle = fmt
                                    break
                            
                            if json3_subtitle and 'url' in json3_subtitle:
                                # Download and parse the subtitle
                                import requests
                                response = requests.get(json3_subtitle['url'])
                                if response.status_code == 200:
                                    subtitle_json = response.json()
                                    # Extract text from events
                                    events = subtitle_json.get('events', [])
                                    transcript_parts = []
                                    for event in events:
                                        if 'segs' in event:
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    transcript_parts.append(seg['utf8'])
                                    transcript_text = ' '.join(transcript_parts)
                                    logger.info(f"Extracted transcript: {len(transcript_text)} chars")
                                    break
                    
                    # Fallback to description if no transcript
                    if not transcript_text:
                        logger.warning(f"No subtitles found for {video_id}, using description")
                        transcript_text = description
                        subtitle_source = "description only"
                    
                    # Combine all content
                    full_content = f"{title}\n\n{description}\n\n{transcript_text}"
                    
                    source = self.create_source_dict(
                        url=video_url,
                        title=title,
                        content=full_content,
                        source_type="social",
                        domain="youtube.com"
                    )
                    source["raw_content"] = full_content
                    source["extra_metadata"] = {
                        "video_id": video_id,
                        "duration_seconds": duration,
                        "subtitle_source": subtitle_source,
                        "transcript_length": len(transcript_text),
                        "platform": "youtube"
                    }
                    
                    sources.append(source)
                    logger.info(f"Scraped: {title[:50]}... ({subtitle_source})")
            
            except Exception as e:
                logger.error(f"Error scraping YouTube video {video_url}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue
        
        logger.info(f"YouTube scraping complete. Found {len(sources)} videos")
        return sources
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None