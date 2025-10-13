from typing import Dict, List
from loguru import logger
from utils.helpers import clean_text, extract_geo_from_text
import re

class Normalizer:
    def normalize_source(self, source: Dict) -> Dict:
        """Normalize source data"""
        logger.debug(f"Normalizing source: {source.get('title', 'Unknown')[:30]}...")
        
        # Clean title and content
        if 'title' in source:
            source['title'] = clean_text(source['title'])
        
        if 'raw_content' in source:
            source['raw_content'] = clean_text(source['raw_content'])
            
            # Extract geo information
            if not source.get('geo'):
                source['geo'] = extract_geo_from_text(source['raw_content'])
        
        # Ensure geo has default values
        if not source.get('geo'):
            source['geo'] = {
                "country": "IN",
                "state": "MP",
                "district": "Indore"
            }
        #hardcoded (indore ) 
        #llm layers (regex) 
        #brain scraped data --> useful content agentic brain (title, geo, politcal, issues etc)
        return source
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities (simple regex-based for MVP)"""
        entities = []
        
        # Common political entities in Indore context
        patterns = {
            "PERSON": [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b',  # English names
                r'\b(?:श्री|श्रीमती|डॉ\.?)\s*[\u0900-\u097F\s]+\b'  # Hindi names with titles
            ],
            "ORG": [
                r'\b(?:Nagar Nigam|Collectorate|Police)\b',
                r'\b(?:नगर निगम|कलेक्ट्रेट|पुलिस)\b'
            ],
            "LOC": [
                r'\bWard\s*\d+\b',
                r'\bवार्ड\s*\d+\b'
            ]
        }
        
        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "type": entity_type,
                        "text": match.group(0).strip(),
                        "start": match.start(),
                        "end": match.end()
                    })
        return entities