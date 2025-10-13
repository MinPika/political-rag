from typing import List, Dict
from loguru import logger
from config.settings import settings

class Chunker:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    
    def chunk_text(self, text: str, source_id: str) -> List[Dict]:
        """Split text into chunks with overlap"""
        if not text or len(text.strip()) < 50:
            return []
        
        # Split by sentences (simple approach)
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        seq = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "source_id": source_id,
                    "seq": seq,
                    "text": chunk_text,
                    "word_count": len(chunk_text.split())
                })
                seq += 1
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "source_id": source_id,
                "seq": seq,
                "text": chunk_text,
                "word_count": len(chunk_text.split())
            })
        
        logger.debug(f"Created {len(chunks)} chunks from source {source_id}")
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Split on period, question mark, exclamation, or Hindi sentence endings
        sentences = re.split(r'[।.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]