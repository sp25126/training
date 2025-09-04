"""
Text processing utilities
"""

import re
from typing import List, Dict
import asyncio

class TextProcessor:
    def __init__(self):
        pass
    
    async def smart_chunk(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict]:
        """Smart text chunking with overlap"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if len(chunk_text.strip()) > 50:  # Skip very small chunks
                chunks.append({
                    "chunk_id": len(chunks),
                    "content": chunk_text,
                    "start_pos": i,
                    "end_pos": i + len(chunk_words)
                })
        
        return chunks
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', ' ', text)
        
        return text.strip()
    
    def extract_key_terms(self, text: str, max_terms: int = 10) -> List[str]:
        """Extract key terms from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
        
        # Filter common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return most frequent terms
        sorted_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [term[0] for term in sorted_terms[:max_terms]]
