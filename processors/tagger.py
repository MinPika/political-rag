from typing import Dict, List
from loguru import logger
import google.generativeai as genai
from config.settings import settings
import json

class Tagger:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Tag taxonomy
        self.issue_tags = [
            "water_supply", "irrigation", "unemployment", "healthcare",
            "school_infrastructure", "road_damage", "electricity",
            "sanitation", "corruption", "law_and_order", "housing"
        ]
        
        self.cohort_tags = [
            "farmers", "labour", "students", "women", "smallholder",
            "tribal", "slum_residents", "teachers", "businessmen"
        ]
        
        self.frame_tags = [
            "development", "neglect", "infrastructure", "corruption",
            "identity", "populism", "rights", "service_delivery"
        ]
    
    def tag_chunk(self, chunk_text: str, source_metadata: Dict) -> Dict:
        """Generate tags for a chunk using Gemini"""
        try:
            prompt = self._create_tagging_prompt(chunk_text, source_metadata)
            response = self.model.generate_content(prompt)
            tags_data = self._parse_llm_response(response.text)
            
            # Add confidence scores
            tags_data["confidence"] = self._calculate_confidence(tags_data)
            
            logger.debug(f"Tagged chunk with {len(tags_data.get('tags', []))} tags")
            return tags_data
        
        except Exception as e:
            logger.error(f"Error tagging chunk: {e}")
            return self._get_default_tags()
    
    def _create_tagging_prompt(self, text: str, metadata: Dict) -> str:
        """Create prompt for LLM tagging"""
        return f"""Analyze this text from Indore, Madhya Pradesh political context and extract structured tags.

Text: {text[:1000]}

Source Type: {metadata.get('source_type', 'unknown')}
Location: {metadata.get('geo', {}).get('district', 'Indore')}

Extract the following as JSON:
{{
    "domain": "political|governance|legal",
    "issues": ["water_supply", "healthcare", etc],
    "cohorts": ["farmers", "students", etc],
    "actors": ["politician names", "organizations"],
    "leadership_polarity": {{
        "polarity": "positive|neutral|negative",
        "score": 0.0-1.0,
        "reasoning": "brief explanation"
    }},
    "frame": "development|neglect|corruption|infrastructure|etc",
    "sentiment": {{
        "polarity": "positive|neutral|negative",
        "score": 0.0-1.0
    }},
    "actionability": ["press_release", "field_visit", "policy_fix", etc]
}}

Available issue tags: {', '.join(self.issue_tags)}
Available cohort tags: {', '.join(self.cohort_tags)}
Available frame tags: {', '.join(self.frame_tags)}

Return ONLY valid JSON, no markdown or extra text."""
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM JSON response"""
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            tags_data = json.loads(response_text)
            return tags_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return self._get_default_tags()
    
    def _calculate_confidence(self, tags_data: Dict) -> float:
        """Calculate overall confidence score"""
        scores = []
        
        if 'leadership_polarity' in tags_data:
            scores.append(tags_data['leadership_polarity'].get('score', 0.5))
        
        if 'sentiment' in tags_data:
            scores.append(tags_data['sentiment'].get('score', 0.5))
        
        # More specific tags = higher confidence
        if tags_data.get('issues'):
            scores.append(0.8)
        if tags_data.get('cohorts'):
            scores.append(0.8)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _get_default_tags(self) -> Dict:
        """Return default tags when LLM fails"""
        return {
            "domain": "governance",
            "issues": [],
            "cohorts": [],
            "actors": [],
            "leadership_polarity": {
                "polarity": "neutral",
                "score": 0.5,
                "reasoning": "Unable to determine"
            },
            "frame": "service_delivery",
            "sentiment": {
                "polarity": "neutral",
                "score": 0.5
            },
            "actionability": [],
            "confidence": 0.3
        }