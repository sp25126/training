"""
Enhanced Telegram processor for handling file downloads
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional
from pathlib import Path
import tempfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramProcessor:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    async def process_message(self, message_data: Dict) -> Dict:
        """Process telegram message data with file download capability"""
        
        try:
            content = ""
            metadata = {
                "source_type": "telegram",
                "message_id": message_data.get("message_id"),
                "chat_id": message_data.get("chat", {}).get("id"),
                "date": message_data.get("date")
            }
            
            # Process text message
            if "text" in message_data:
                content = message_data["text"]
                metadata["content_type"] = "text"
            
            # Process document with actual download
            elif "document" in message_data:
                content = await self._download_and_process_document(message_data)
                metadata["content_type"] = "document"
                metadata["document_name"] = message_data["document"].get("file_name", "")
            
            # Process photo with caption
            elif "photo" in message_data:
                caption = message_data.get("caption", "")
                content = f"Photo message: {caption}" if caption else "Photo message (no caption)"
                metadata["content_type"] = "photo"
            
            else:
                content = "Unsupported message type"
                metadata["content_type"] = "unsupported"
            
            return {
                "content": content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to process telegram message: {e}")
            return {
                "content": "",
                "metadata": {
                    "source_type": "telegram",
                    "error": str(e),
                    "content_type": "error"
                }
            }
    
    async def _download_and_process_document(self, message_data: Dict) -> str:
        """Download and extract content from Telegram document"""
        
        if not self.bot_token:
            return "Document processing requires bot token configuration"
        
        document = message_data.get("document", {})
        file_id = document.get("file_id")
        file_name = document.get("file_name", "unknown_file")
        
        try:
            # Get file info from Telegram API
            get_file_url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
            
            async with aiohttp.ClientSession() as session:
                # Get file path
                async with session.post(get_file_url, json={"file_id": file_id}) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get file info: {resp.status}")
                    
                    result = await resp.json()
                    if not result.get("ok"):
                        raise Exception("Telegram API returned error")
                    
                    file_path = result["result"]["file_path"]
                
                # Download file content
                download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                
                async with session.get(download_url) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download file: {resp.status}")
                    
                    file_content = await resp.read()
            
            # Process file based on type
            if file_name.endswith(('.txt', '.md')):
                # Text file
                content = file_content.decode('utf-8', errors='ignore')
                
            elif file_name.endswith('.json'):
                # JSON file
                json_data = json.loads(file_content.decode('utf-8'))
                content = json.dumps(json_data, indent=2)
                
            elif file_name.endswith('.csv'):
                # CSV file
                content = file_content.decode('utf-8', errors='ignore')
                
            else:
                # Generic file
                content = f"File: {file_name} (Binary content, {len(file_content)} bytes)"
            
            caption = message_data.get("caption", "")
            if caption:
                content = f"Caption: {caption}\n\nFile Content:\n{content}"
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to download/process document: {e}")
            return f"Failed to process document: {file_name} - {str(e)}"
