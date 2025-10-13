import hashlib
import re
from typing import Dict, List
from datetime import datetime
from langdetect import detect, LangDetectException

def generate_hash(text: str) -> str:
    """Generate SHA256 hash of text"""
    return hashlib.sha256(text.encode()).hexdigest()

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep Hindi characters
    text = re.sub(r'[^\w\s\u0900-\u097F.,!?-]', '', text)
    return text.strip()

def detect_language(text: str) -> str:
    """Detect language of text"""
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return "unknown"

def extract_geo_from_text(text: str) -> Dict:
    """Extract geographical information from text"""
    geo = {
        "country": "IN",
        "state": "MP",
        "district": None,
        "ward": None
    }
    
    # Simple pattern matching for Indore
    if re.search(r'indore|इंदौर', text, re.IGNORECASE):
        geo["district"] = "Indore"
    
    # Extract ward numbers
    ward_match = re.search(r'ward[:\s]*(\d+)|वार्ड[:\s]*(\d+)', text, re.IGNORECASE)
    if ward_match:
        geo["ward"] = f"Ward{ward_match.group(1) or ward_match.group(2)}"
    
    return geo

def calculate_trust_score(source_type: str, domain: str) -> float:
    """Calculate trust score based on source type and domain"""
    trust_scores = {
        "government": 1.0,
        "policy": 0.95,
        "media": 0.8,
        "social": 0.5,
        "voice": 0.6
    }
    
    base_score = trust_scores.get(source_type, 0.5)
    
    # Adjust based on domain
    if "nic.in" in domain or ".gov.in" in domain:
        return 1.0
    elif "bhaskar.com" in domain or "indianexpress.com" in domain:
        return 0.85
    elif "indiatoday.in" in domain or "freepressjournal.in" in domain:
        return 0.80
    
    return base_score