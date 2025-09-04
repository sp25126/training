"""
Core resource processor for handling various input types
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
import hashlib

from integrations.web_scraper import WebScraper
from integrations.telegram_processor import TelegramProcessor
from utils.text_processor import TextProcessor
from utils.file_manager import FileManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceProcessor:
    def __init__(self):
        self.web_scraper = WebScraper()
        self.telegram_processor = TelegramProcessor()
        self.text_processor = TextProcessor()
        self.file_manager = FileManager()
        
    async def process_resource(self, resource: Union[str, Dict], resource_type: str = "auto") -> Dict:
        """
        Main method to process any resource type
        """
        logger.info(f"Processing resource: {str(resource)[:100]}...")
        
        # Auto-detect resource type
        if resource_type == "auto":
            resource_type = self._detect_resource_type(resource)
        
        # Create resource ID for tracking
        resource_id = self._generate_resource_id(resource, resource_type)
        
        try:
            # Process based on type
            if resource_type == "web":
                content_data = await self.web_scraper.scrape_url(resource)
            elif resource_type == "telegram":
                content_data = await self.telegram_processor.process_message(resource)
            elif resource_type == "file":
                content_data = await self.file_manager.load_file(resource)
            elif resource_type == "text":
                content_data = await self._process_text_resource(resource)
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
            
            # Add metadata
            processed_data = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "original_resource": str(resource),
                "content": content_data["content"],
                "metadata": {
                    **content_data.get("metadata", {}),
                    "processed_at": datetime.now().isoformat(),
                    "content_length": len(content_data["content"]),
                    "chunks_count": 0,
                    "processing_status": "success"
                }
            }
            
            logger.info(f"✅ Successfully processed resource: {resource_id}")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Failed to process resource: {e}")
            error_data = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "original_resource": str(resource),
                "content": "",
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "processing_status": "error",
                    "error_message": str(e)
                }
            }
            return error_data
    
    def _detect_resource_type(self, resource: Union[str, Dict]) -> str:
        """Auto-detect resource type"""
        
        if isinstance(resource, dict):
            if "message" in resource or "chat" in resource:
                return "telegram"
            return "text"
        
        if isinstance(resource, str):
            if resource.startswith(("http://", "https://")):
                return "web"
            elif Path(resource).exists():
                return "file"
            else:
                return "text"
        
        return "text"
    
    def _generate_resource_id(self, resource: Union[str, Dict], resource_type: str) -> str:
        """Generate unique resource ID"""
        
        resource_str = json.dumps(resource, sort_keys=True) if isinstance(resource, dict) else str(resource)
        hash_object = hashlib.md5(resource_str.encode())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{resource_type}_{timestamp}_{hash_object.hexdigest()[:8]}"
    
    async def _process_text_resource(self, text: str) -> Dict:
        """Process raw text"""
        return {
            "content": text,
            "metadata": {
                "source_type": "raw_text",
                "title": f"Text content ({len(text)} chars)",
                "length": len(text)
            }
        }
    
    async def chunk_content(self, processed_data: Dict) -> List[Dict]:
        """Chunk processed content for LLM processing"""
        
        content = processed_data["content"]
        
        if len(content) <= 800:
            chunks = [{
                "chunk_id": 0,
                "content": content,
                "start_pos": 0,
                "end_pos": len(content)
            }]
        else:
            chunks = await self.text_processor.smart_chunk(content, 800, 100)
        
        # Update metadata
        processed_data["metadata"]["chunks_count"] = len(chunks)
        
        # Add chunk metadata
        chunked_data = []
        for chunk in chunks:
            chunk_data = {
                "resource_id": processed_data["resource_id"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "metadata": {
                    **processed_data["metadata"],
                    "chunk_start": chunk["start_pos"],
                    "chunk_end": chunk["end_pos"],
                    "chunk_length": len(chunk["content"])
                }
            }
            chunked_data.append(chunk_data)
        
        logger.info(f"📄 Created {len(chunks)} chunks for {processed_data['resource_id']}")
        return chunked_data
