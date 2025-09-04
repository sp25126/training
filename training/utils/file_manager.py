"""
Enhanced file management utilities with audio, video, and URL processing support
"""

import json
import aiofiles
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Union
import logging
import aiohttp
from bs4 import BeautifulSoup

# Audio/Video processing imports
try:
    import moviepy.editor as mp
    import speech_recognition as sr
    from pydub import AudioSegment
    AUDIO_VIDEO_SUPPORT = True
except ImportError:
    AUDIO_VIDEO_SUPPORT = False
    logging.warning("Audio/video processing libraries not available. Install: pip install moviepy SpeechRecognition pydub")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileManager:
    """Enhanced file operations with audio, video, and web content support"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "training_temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def save_json(self, data: Dict, filepath: str):
        """Save data to JSON file asynchronously"""
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            
            logger.info(f"Saved JSON to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
    
    async def save_jsonl(self, data_list: List[Dict], filepath: str):
        """Save list of dictionaries to JSONL file asynchronously"""
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                for item in data_list:
                    await f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"Saved {len(data_list)} items to JSONL: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save JSONL to {filepath}: {e}")
    
    async def load_json(self, filepath: str) -> Dict:
        """Load JSON file asynchronously"""
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load JSON from {filepath}: {e}")
            return {}
    
    async def load_jsonl(self, filepath: str) -> List[Dict]:
        """Load JSONL file asynchronously"""
        try:
            items = []
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                async for line in f:
                    if line.strip():
                        items.append(json.loads(line))
            return items
        except Exception as e:
            logger.error(f"Failed to load JSONL from {filepath}: {e}")
            return []
    
    async def load_file(self, filepath: str) -> Dict:
        """Enhanced file loader with audio, video, and web URL support"""
        filepath_obj = Path(filepath) if not filepath.startswith(('http://', 'https://')) else None
        
        # Handle URLs
        if filepath.startswith(('http://', 'https://')):
            return await self._process_url(filepath)
        
        # Handle local files
        if not filepath_obj or not filepath_obj.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            file_extension = filepath_obj.suffix.lower()
            
            # Handle video files
            if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v']:
                content = await self._extract_video_content(filepath_obj)
            
            # Handle audio files
            elif file_extension in ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']:
                content = await self._extract_audio_content(filepath_obj)
            
            # Handle PDF files
            elif file_extension == '.pdf':
                content = await self._extract_pdf_text(filepath_obj)
            
            # Handle plain text files
            elif file_extension in ['.txt', '.md', '.csv']:
                async with aiofiles.open(filepath_obj, 'r', encoding='utf-8') as f:
                    content = await f.read()
            
            # Handle JSON files
            elif file_extension == '.json':
                data = await self.load_json(str(filepath_obj))
                content = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
            
            # Handle JSONL files
            elif file_extension == '.jsonl':
                data = await self.load_jsonl(str(filepath_obj))
                content = '\n'.join(json.dumps(item) for item in data)
            
            # Handle Word documents
            elif file_extension in ['.docx', '.doc']:
                content = await self._extract_docx_text(filepath_obj)
            
            # Handle other files with encoding fallback
            else:
                content = await self._load_with_encoding_fallback(filepath_obj)
            
            return {
                "content": content,
                "metadata": {
                    "source_type": "file",
                    "file_type": file_extension,
                    "file_name": filepath_obj.name,
                    "file_size": filepath_obj.stat().st_size,
                    "content_length": len(content),
                    "media_type": self._classify_media_type(file_extension)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to load file {filepath}: {e}")
            raise
    
    def _classify_media_type(self, file_extension: str) -> str:
        """Classify file by media type"""
        if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v']:
            return "video"
        elif file_extension in ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']:
            return "audio"
        elif file_extension in ['.pdf', '.docx', '.doc', '.txt', '.md']:
            return "document"
        elif file_extension in ['.json', '.jsonl', '.csv']:
            return "data"
        else:
            return "unknown"
    
    async def _process_url(self, url: str) -> Dict:
        """Process web URLs including media URLs"""
        try:
            # Check if URL points to media file
            if any(ext in url.lower() for ext in ['.mp4', '.avi', '.mov', '.mp3', '.wav', '.m4a']):
                return await self._download_and_process_media_url(url)
            
            # Process as web page
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    html_content = await response.text()
                    
                    # Parse HTML content
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract main content
                    content = self._extract_main_content_from_html(soup)
                    
                    # Get metadata
                    title = soup.find('title').text if soup.find('title') else "Unknown Title"
                    description = ""
                    desc_elem = soup.find('meta', attrs={'name': 'description'})
                    if desc_elem:
                        description = desc_elem.get('content', '')
                    
                    return {
                        "content": content,
                        "metadata": {
                            "source_type": "web",
                            "url": url,
                            "title": title,
                            "description": description,
                            "content_length": len(content),
                            "media_type": "webpage"
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            return {
                "content": f"Failed to process URL: {url}",
                "metadata": {
                    "source_type": "web",
                    "url": url,
                    "title": "Processing failed",
                    "error": str(e),
                    "media_type": "webpage"
                }
            }
    
    def _extract_main_content_from_html(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Try to find main content areas
        main_selectors = ['article', 'main', '.content', '.post', '#content', '.entry-content']
        content_parts = []
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = element.get_text()
                    if len(text) > 200:
                        content_parts.append(self._clean_text(text))
                        break
                if content_parts:
                    break
        
        # Fallback to paragraphs
        if not content_parts:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = self._clean_text(p.get_text())
                if len(text) > 50:
                    content_parts.append(text)
        
        # Final fallback to body
        if not content_parts:
            body = soup.find('body')
            if body:
                content_parts.append(self._clean_text(body.get_text()))
        
        return '\n\n'.join(content_parts)[:15000]  # Limit content length
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        import re
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', ' ', text)
        return text.strip()
    
    async def _download_and_process_media_url(self, url: str) -> Dict:
        """Download and process media from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    
                    # Determine file type from URL or content-type
                    content_type = response.headers.get('content-type', '')
                    if 'video' in content_type or any(ext in url for ext in ['.mp4', '.avi', '.mov']):
                        file_ext = '.mp4'
                        media_type = "video"
                    elif 'audio' in content_type or any(ext in url for ext in ['.mp3', '.wav', '.m4a']):
                        file_ext = '.mp3'
                        media_type = "audio"
                    else:
                        raise Exception("Unknown media type")
                    
                    # Download to temporary file
                    temp_file = self.temp_dir / f"temp_media{file_ext}"
                    
                    with open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    # Process the downloaded file
                    if media_type == "video":
                        content = await self._extract_video_content(temp_file)
                    else:
                        content = await self._extract_audio_content(temp_file)
                    
                    # Clean up
                    temp_file.unlink(missing_ok=True)
                    
                    return {
                        "content": content,
                        "metadata": {
                            "source_type": f"{media_type}_url",
                            "url": url,
                            "media_type": media_type,
                            "content_length": len(content)
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Failed to download/process media URL {url}: {e}")
            raise
    
    async def _extract_video_content(self, filepath: Path) -> str:
        """Extract speech content from video files"""
        if not AUDIO_VIDEO_SUPPORT:
            return f"[Video file: {filepath.name}. Audio/video processing not available - install moviepy and SpeechRecognition]"
        
        try:
            logger.info(f"Extracting audio from video: {filepath.name}")
            
            # Extract audio from video
            video = mp.VideoFileClip(str(filepath))
            
            # Create temporary audio file
            temp_audio = self.temp_dir / f"temp_audio_{filepath.stem}.wav"
            
            # Extract audio
            video.audio.write_audiofile(str(temp_audio), verbose=False, logger=None)
            video.close()
            
            # Extract text from audio
            content = await self._extract_audio_content(temp_audio)
            
            # Clean up
            temp_audio.unlink(missing_ok=True)
            
            if not content.strip():
                content = f"[Video processed: {filepath.name}. No clear speech detected in audio track]"
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to extract content from video {filepath}: {e}")
            return f"[Video processing error: {filepath.name} - {str(e)}]"
    
    async def _extract_audio_content(self, filepath: Path) -> str:
        """Extract speech content from audio files"""
        if not AUDIO_VIDEO_SUPPORT:
            return f"[Audio file: {filepath.name}. Audio processing not available - install SpeechRecognition]"
        
        try:
            logger.info(f"Extracting speech from audio: {filepath.name}")
            
            # Initialize speech recognizer
            r = sr.Recognizer()
            
            # Convert to WAV if necessary
            if filepath.suffix.lower() != '.wav':
                temp_wav = self.temp_dir / f"temp_converted_{filepath.stem}.wav"
                
                try:
                    # Convert using pydub
                    audio = AudioSegment.from_file(str(filepath))
                    audio.export(str(temp_wav), format="wav")
                    process_file = temp_wav
                except Exception:
                    # Fallback to original file
                    process_file = filepath
            else:
                process_file = filepath
            
            # Process audio file
            with sr.AudioFile(str(process_file)) as source:
                # Adjust for ambient noise
                r.adjust_for_ambient_noise(source)
                audio_data = r.record(source)
            
            # Recognize speech
            try:
                text = r.recognize_google(audio_data)
                logger.info(f"Successfully extracted {len(text)} characters of speech")
                return text
            except sr.UnknownValueError:
                return f"[Audio processed: {filepath.name}. Could not understand speech clearly]"
            except sr.RequestError as e:
                logger.warning(f"Speech recognition service error: {e}")
                return f"[Audio file: {filepath.name}. Speech recognition service unavailable]"
            
        except Exception as e:
            logger.error(f"Failed to extract speech from audio {filepath}: {e}")
            return f"[Audio processing error: {filepath.name} - {str(e)}]"
        finally:
            # Clean up temporary files
            temp_wav = self.temp_dir / f"temp_converted_{filepath.stem}.wav"
            temp_wav.unlink(missing_ok=True)
    
    async def _extract_pdf_text(self, filepath: Path) -> str:
        """Extract text from PDF files"""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(str(filepath))
            text_content = ""
            
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num} ---\n{page_text}\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    continue
            
            if not text_content.strip():
                text_content = f"[PDF file processed but no readable text found: {filepath.name}]"
            
            return text_content.strip()
            
        except ImportError:
            error_msg = "PyPDF2 library not installed. Install with: pip install PyPDF2"
            logger.error(error_msg)
            return f"[PDF processing error: {error_msg}]"
        except Exception as e:
            error_msg = f"Failed to extract text from PDF: {str(e)}"
            logger.error(error_msg)
            return f"[PDF processing error: {error_msg}]"
    
    async def _extract_docx_text(self, filepath: Path) -> str:
        """Extract text from Word documents"""
        try:
            from docx import Document
            
            doc = Document(filepath)
            text_content = ""
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content += paragraph.text + "\n"
            
            if not text_content.strip():
                text_content = f"[Word document processed but no readable text found: {filepath.name}]"
            
            return text_content.strip()
            
        except ImportError:
            error_msg = "python-docx library not installed. Install with: pip install python-docx"
            logger.warning(error_msg)
            return f"[Word document: {filepath.name}. {error_msg}]"
        except Exception as e:
            error_msg = f"Failed to extract text from Word document: {str(e)}"
            logger.warning(error_msg)
            return f"[Word document processing error: {error_msg}]"
    
    async def _load_with_encoding_fallback(self, filepath: Path) -> str:
        """Load file with multiple encoding fallbacks"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                async with aiofiles.open(filepath, 'r', encoding=encoding) as f:
                    content = await f.read()
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading file with {encoding}: {e}")
                continue
        
        # Final fallback - read as binary and represent as text
        try:
            async with aiofiles.open(filepath, 'rb') as f:
                binary_content = await f.read()
                return f"[Binary file: {filepath.name}, {len(binary_content)} bytes. First 500 chars as text: {str(binary_content[:500])}]"
        except Exception as e:
            return f"[Failed to read file {filepath.name}: {str(e)}]"
